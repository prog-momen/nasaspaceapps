"""Anthropic Claude client (official `anthropic` SDK) - the ONLY language-model connection in this project.

Hard rules (tested in tests/test_claude_only.py)
* ALLOW-LIST: exactly one model id, `claude-haiku-5-5`, may ever be sent. The check lives in `_send`, the single choke point every request goes
  through, so it runs BEFORE any network call and cannot be bypassed by a caller passing `model=`/`pin_model=`, by configuration
  (`ANTHROPIC_MODEL`) or by a future code path. Anything else raises LLMError(kind="model_not_allowed").
* NO FALLBACK: there is no secondary model. A transient failure is retried on the same model a bounded number of times, then the error is returned
  to the caller, which uses a deterministic result where one is valid (and says so) or reports a clear error.
* The key is read from the environment / .env (never logged, never in messages); the SDK's own retries are disabled so attempts never multiply.
* Responses are exposed in a small neutral shape (`text`, `function_calls`, `candidates[0].content`, `usage_metadata`) so tool-use loops stay testable.
"""
from __future__ import annotations

import logging
import random
import time
from types import SimpleNamespace

from app.config import get_settings, load_credential
from app.llm.base import BudgetExceeded, LLMError, LLMResult, UsageTracker
from app.reliability import remaining as budget_remaining

log = logging.getLogger(__name__)

ALLOWED_MODELS = frozenset({"claude-haiku-5-5"})
DEFAULT_MODEL = "claude-haiku-5-5"
TRANSIENT_KINDS = {"overloaded", "service_error", "timeout", "network"}
_STATUS = {"auth": 502, "invalid_request": 502, "model_not_found": 502, "model_not_allowed": 403, "quota": 429, "overloaded": 503, "service_error": 503,
           "tool_protocol": 502, "budget": 429, "timeout": 503, "network": 503, "empty": 502, "not_configured": 503, "billing": 402, "unknown": 502}


def assert_model_allowed(model: str | None) -> str:
    """Reject anything but the allow-listed model, before any request is built or sent."""
    if model not in ALLOWED_MODELS:
        raise LLMError(f"Model {model!r} is not allowed. Only {sorted(ALLOWED_MODELS)} may be used; no other model is ever called.", 403, "model_not_allowed")
    return model


def classify_error(e: Exception) -> dict:
    """SDK exception -> {kind, retryable, retry_after}. Decides from the HTTP status / exception class, never from message text for 5xx."""
    import anthropic
    ra = None
    try:
        h = getattr(getattr(e, "response", None), "headers", None)
        if h is not None and h.get("retry-after") is not None:
            ra = float(h.get("retry-after"))
    except Exception:
        ra = None
    if isinstance(e, anthropic.APITimeoutError):
        return {"kind": "timeout", "retryable": True, "retry_after": None}
    if isinstance(e, anthropic.APIConnectionError):
        return {"kind": "network", "retryable": True, "retry_after": None}
    code = getattr(e, "status_code", None)
    if code == 429:
        return {"kind": "quota", "retryable": ra is not None and ra <= 10, "retry_after": ra}
    if code == 529:
        return {"kind": "overloaded", "retryable": True, "retry_after": ra}
    if code in (500, 502, 503, 504):
        return {"kind": "timeout" if code == 504 else "service_error", "retryable": True, "retry_after": ra}
    if code in (401, 403):
        return {"kind": "auth", "retryable": False, "retry_after": None}
    if code == 404:
        return {"kind": "model_not_found", "retryable": False, "retry_after": None}
    if code == 402 or (code == 400 and "credit balance" in str(getattr(e, "message", e)).lower()):
        return {"kind": "billing", "retryable": False, "retry_after": None}
    if code in (400, 413, 422):
        return {"kind": "invalid_request", "retryable": False, "retry_after": None}
    return {"kind": "unknown", "retryable": False, "retry_after": None}


def to_tools(declarations: list[dict] | None) -> list[dict] | None:
    """Neutral function declarations {name, description, parameters} -> Anthropic tools {name, description, input_schema}."""
    if not declarations:
        return None
    out = []
    for d in declarations:
        if d.get("type") and not (d.get("parameters") or d.get("input_schema")):          # Anthropic server tool (e.g. web_search_20250305): passed through unchanged
            out.append(d)
        else:
            out.append({"name": d["name"], "description": d.get("description", ""), "input_schema": d.get("parameters") or d.get("input_schema") or {"type": "object", "properties": {}}})
    return out


class LLMResponse(SimpleNamespace):
    """text, function_calls[SimpleNamespace(name,args,id)], candidates[0].content (blocks to echo back), usage_metadata, model, stop_reason"""


def _wrap(resp, model: str) -> LLMResponse:
    text, calls, blocks, sources = [], [], [], {}
    for b in getattr(resp, "content", []) or []:
        t = getattr(b, "type", None)
        if t == "text":
            text.append(b.text); blocks.append({"type": "text", "text": b.text})
            for c in (getattr(b, "citations", None) or []):
                u = getattr(c, "url", None)
                if u:
                    sources.setdefault(u, {"url": u, "title": getattr(c, "title", None), "snippet": (getattr(c, "cited_text", None) or "")[:300]})
        elif t == "web_search_tool_result":
            for x in (b.content if isinstance(getattr(b, "content", None), list) else []):
                u = getattr(x, "url", None)
                if u:
                    sources.setdefault(u, {"url": u, "title": getattr(x, "title", None), "snippet": ""})
        elif t == "tool_use":
            calls.append(SimpleNamespace(name=b.name, args=dict(b.input or {}), id=b.id)); blocks.append({"type": "tool_use", "id": b.id, "name": b.name, "input": dict(b.input or {})})
    u = getattr(resp, "usage", None)
    return LLMResponse(text="".join(text).strip(), web_sources=list(sources.values()), function_calls=calls, candidates=[SimpleNamespace(content=blocks)], model=model, stop_reason=getattr(resp, "stop_reason", None),
                       usage_metadata=SimpleNamespace(prompt_token_count=getattr(u, "input_tokens", None), candidates_token_count=getattr(u, "output_tokens", None)))


class ClaudeClient:
    def __init__(self, api_key: str | None = None, model: str | None = None, usage: UsageTracker | None = None, sdk=None):
        s = get_settings()
        self.model = assert_model_allowed(model if model is not None else s.anthropic_model)               # a mis-set ANTHROPIC_MODEL fails here, loudly
        key = api_key or (load_credential("ANTHROPIC_API_KEY").get_secret_value() if load_credential("ANTHROPIC_API_KEY") else None)
        if not key and sdk is None:
            raise LLMError("ANTHROPIC_API_KEY is not configured.", 503, "not_configured")
        self._key, self.usage, self.settings = key, usage, s
        if sdk is None:
            import anthropic
            sdk = anthropic.Anthropic(api_key=key, max_retries=0, timeout=s.llm_request_timeout_s)
        self._sdk = sdk
        self.attempts_log: list[dict] = []

    @property
    def last_model_used(self) -> str:
        return self.model

    def _sanitize(self, msg: str) -> str:
        return msg.replace(self._key, "[REDACTED]") if self._key else msg

    @staticmethod
    def _sleep(seconds: float) -> None:
        time.sleep(seconds)

    # -- the single choke point -------------------------------------------------------------------------------------------------------
    def _send(self, params: dict, total_deadline_s: float | None = None, retries: int | None = None):
        assert_model_allowed(params.get("model"))                                       # before ANY network call, for every code path
        s = self.settings
        max_attempts = 1 + (s.llm_max_attempts - 1 if retries is None else retries)
        t_end = time.monotonic() + (total_deadline_s if total_deadline_s is not None else s.llm_total_deadline_s)
        last: dict = {"kind": "unknown"}
        self.attempts_log = []
        for attempt in range(1, max_attempts + 1):
            if self.usage:
                self.usage.reserve(params["model"])
            try:
                resp = self._sdk.messages.create(**params)
                if self.usage:
                    u = getattr(resp, "usage", None)
                    self.usage.record(params["model"], getattr(u, "input_tokens", None), getattr(u, "output_tokens", None))
                return resp
            except BudgetExceeded:
                raise
            except Exception as e:                                                      # SDK errors are classified; anything else is a local bug, not retried
                try:
                    import anthropic
                    is_api = isinstance(e, (anthropic.APIError,))
                except Exception:
                    is_api = False
                info = classify_error(e) if is_api else {"kind": "unknown", "retryable": False, "retry_after": None}
                last = info
                self.attempts_log.append({"attempt": attempt, "kind": info["kind"], "status": getattr(e, "status_code", None)})
                log.warning("claude %s attempt=%d/%d kind=%s status=%s", params["model"], attempt, max_attempts, info["kind"], getattr(e, "status_code", None))
                left = t_end - time.monotonic()
                if not info["retryable"] or attempt >= max_attempts or left <= 1:
                    break
                wait = min(info["retry_after"] if info["retry_after"] else random.uniform(0.5, 1.5 * 2 ** attempt), max(0.0, left - 1))
                self._sleep(wait)
        raise LLMError(f"Claude unavailable ({last['kind']}). Attempts: {self.attempts_log}", status=_STATUS.get(last["kind"], 502), kind=last["kind"], attempts=self.attempts_log)

    # -- public API ---------------------------------------------------------------------------------------------------------------------
    def generate_raw(self, contents, system: str, tools=None, max_output_tokens: int | None = None, temperature: float | None = None, tool_choice: dict | None = None,
                     total_deadline_s: float | None = None, retries: int | None = None, **kw) -> LLMResponse:
        for k in ("model", "pin_model"):                                                # a caller may only ever 'ask' for the allowed model
            if kw.get(k) is not None:
                assert_model_allowed(kw[k])
        messages = [{"role": "user", "content": contents}] if isinstance(contents, str) else list(contents)
        params: dict = {"model": self.model, "max_tokens": int(max_output_tokens or self.settings.llm_max_output_tokens), "messages": messages}
        if system:
            params["system"] = system
        params["thinking"] = {"type": "disabled"}            # structured/explanatory tasks need no hidden reasoning; thinking tokens were exhausting max_tokens and returning empty text
        if temperature is not None:
            params["temperature"] = temperature
        t = to_tools(tools)
        if t:
            params["tools"] = t
            if tool_choice:
                params["tool_choice"] = tool_choice
        resp = self._send(params, total_deadline_s, retries)
        out = _wrap(resp, self.model)
        if not out.text and not out.function_calls:
            raise LLMError("Claude returned an empty response.", 502, "empty")
        return out

    def generate(self, system: str, user: str, max_output_tokens: int | None = None, temperature: float | None = None, retries: int | None = None, **kw) -> LLMResult:
        t0 = time.monotonic()
        r = self.generate_raw(user, system, max_output_tokens=max_output_tokens, temperature=temperature, retries=retries, **kw)
        return LLMResult(r.text, r.model, r.usage_metadata.prompt_token_count, r.usage_metadata.candidates_token_count, time.monotonic() - t0)

    def check_model_available(self) -> dict:
        """Free metadata call (no tokens): is the allow-listed model visible to this account? Never substitutes another model."""
        assert_model_allowed(self.model)
        try:
            m = self._sdk.models.retrieve(self.model)
            return {"available": True, "id": getattr(m, "id", self.model), "display_name": getattr(m, "display_name", None)}
        except Exception as e:
            import anthropic
            info = classify_error(e) if isinstance(e, anthropic.APIError) else {"kind": "unknown"}
            return {"available": False, "reason": info["kind"], "status": getattr(e, "status_code", None)}
