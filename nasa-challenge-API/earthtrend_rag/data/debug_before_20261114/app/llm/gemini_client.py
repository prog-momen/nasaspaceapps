"""Gemini client (google-genai) with a single, bounded retry layer.

Design rules (see docs/GEMINI_RELIABILITY.md)
- The SDK's own retries are disabled (attempts=1); this module is the only place that retries, so attempts never multiply.
- Errors are classified: only transient ones (500/502/503/504, network, timeout) are retried, with exponential backoff + full
  jitter, honouring Retry-After / RetryInfo. 400/401/403/404 and daily-quota 429s are never retried on the same model.
- Hard limits: per-attempt timeout, max attempts per model, and a TOTAL deadline for the whole call.
- A daily-quota 429 is remembered (until the reset the service announced), so later calls skip that model without a network call.
- Optional fallback models (GEMINI_FALLBACK_MODELS, free-tier only; never enabled implicitly). Function-calling turns are pinned
  to the model that produced the tool call.
- Keys never appear in messages or logs.
"""
from __future__ import annotations

import json
import logging
import random
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings, load_gemini_key

log = logging.getLogger(__name__)

TRANSIENT_CODES = {500, 502, 503, 504}


class LLMError(RuntimeError):
    """kind: auth | invalid_request | model_not_found | quota | overloaded | timeout | network | empty | not_configured | budget"""

    def __init__(self, message: str, status: int = 502, kind: str = "unknown", attempts: list | None = None):
        super().__init__(message)
        self.status, self.kind, self.attempts = status, kind, attempts or []


class BudgetExceeded(LLMError):
    def __init__(self, message: str):
        super().__init__(message, status=429, kind="budget")


@dataclass
class LLMResult:
    text: str
    model: str
    prompt_tokens: int | None
    output_tokens: int | None
    latency_s: float


class UsageTracker:
    """Per-model request counters per UTC day + 'exhausted until' markers, persisted in a small JSON file.

    Counts attempts that reached the service (conservative). The cap is a local safety net below the provider's free-tier limit.
    """

    def __init__(self, path: Path, cap_per_model_per_day: int):
        self.path, self.cap = path, cap_per_model_per_day
        self._lock = threading.Lock()

    def _load(self) -> dict:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self, data: dict) -> None:
        days = {k: v for k, v in data.items() if k != "_exhausted"}
        keep = dict(sorted(days.items())[-14:])
        if "_exhausted" in data:
            keep["_exhausted"] = data["_exhausted"]
        self.path.write_text(json.dumps(keep, indent=1), encoding="utf-8")

    @staticmethod
    def _day() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def today(self) -> dict:
        d = self._load().get(self._day(), {})
        models = {m: v for m, v in d.items() if isinstance(v, dict)}
        return {"date": self._day(), "requests": sum(v.get("requests", 0) for v in models.values()),
                "prompt_tokens": sum(v.get("prompt_tokens", 0) for v in models.values()),
                "output_tokens": sum(v.get("output_tokens", 0) for v in models.values()), "models": models}

    def exhausted_until(self, model: str) -> float:
        return float(self._load().get("_exhausted", {}).get(model, 0))

    def mark_exhausted(self, model: str, seconds: float) -> None:
        with self._lock:
            data = self._load()
            data.setdefault("_exhausted", {})[model] = time.time() + max(seconds, 60)
            self._save(data)

    def reserve(self, model: str) -> None:
        with self._lock:
            data = self._load()
            m = data.setdefault(self._day(), {}).setdefault(model, {"requests": 0, "prompt_tokens": 0, "output_tokens": 0})
            if self.cap and m["requests"] >= self.cap:
                raise BudgetExceeded(f"Local daily request cap for {model} reached ({self.cap}).")
            m["requests"] += 1
            self._save(data)

    def record(self, model: str, prompt_tokens: int | None, output_tokens: int | None) -> None:
        with self._lock:
            data = self._load()
            m = data.setdefault(self._day(), {}).setdefault(model, {"requests": 0, "prompt_tokens": 0, "output_tokens": 0})
            m["prompt_tokens"] += prompt_tokens or 0
            m["output_tokens"] += output_tokens or 0
            self._save(data)


def _parse_seconds(v) -> float | None:
    try:
        return float(str(v).rstrip("s"))
    except (TypeError, ValueError):
        return None


def classify_api_error(e) -> dict:
    """Pure function: SDK APIError -> {kind, retryable, retry_after, daily_quota}. Never uses the message to decide for 5xx."""
    code = getattr(e, "code", None)
    details = e.details if isinstance(getattr(e, "details", None), dict) else {}
    err = details.get("error", details)
    retry_after = None
    daily = False
    for d in err.get("details", []) if isinstance(err, dict) else []:
        t = str(d.get("@type", ""))
        if t.endswith("RetryInfo"):
            retry_after = _parse_seconds(d.get("retryDelay"))
        if t.endswith("QuotaFailure"):
            for v in d.get("violations", []):
                if "PerDay" in str(v.get("quotaId", "")) or "PerDay" in str(v.get("quotaMetric", "")):
                    daily = True
    try:
        h = e.response.headers.get("retry-after")
        if h is not None and retry_after is None:
            retry_after = _parse_seconds(h)
    except Exception:
        pass
    if code == 429:
        return {"kind": "quota", "retryable": not daily and (retry_after is not None and retry_after <= 30),
                "retry_after": retry_after, "daily_quota": daily or (retry_after is not None and retry_after > 600)}
    if code in TRANSIENT_CODES:
        return {"kind": "timeout" if code == 504 else "overloaded", "retryable": True, "retry_after": retry_after, "daily_quota": False}
    if code in (401, 403):
        return {"kind": "auth", "retryable": False, "retry_after": None, "daily_quota": False}
    if code == 404:
        return {"kind": "model_not_found", "retryable": False, "retry_after": None, "daily_quota": False}
    if code == 400:
        return {"kind": "invalid_request", "retryable": False, "retry_after": None, "daily_quota": False}
    return {"kind": "unknown", "retryable": False, "retry_after": None, "daily_quota": False}


_STATUS = {"auth": 502, "invalid_request": 502, "model_not_found": 502, "quota": 429, "overloaded": 503,
           "timeout": 503, "network": 503, "empty": 502, "not_configured": 503, "unknown": 502}


class GeminiClient:
    def __init__(self, api_key: str | None = None, model: str | None = None, usage: UsageTracker | None = None,
                 thinking_level: str | None = "low", fallback_models: list[str] | None = None):
        s = get_settings()
        key = api_key or (load_gemini_key().get_secret_value() if load_gemini_key() else None)
        if not key:
            raise LLMError("GEMINI_API_KEY is not configured.", status=503, kind="not_configured")
        from google import genai  # lazy
        from google.genai import types

        self._key = key
        # SDK-level retries OFF: this class is the only retry layer
        self._client = genai.Client(api_key=key, http_options=types.HttpOptions(
            timeout=int(s.gemini_request_timeout_s * 1000), retry_options=types.HttpRetryOptions(attempts=1)))
        self.model = model or s.gemini_model
        fb = fallback_models if fallback_models is not None else s.fallback_model_list
        self.models = list(dict.fromkeys([self.model] + [m for m in fb if m]))
        self.usage = usage or UsageTracker(s.usage_file, s.gemini_daily_cap_per_model)
        self.thinking_level = thinking_level
        self._local = threading.local()
        self._unhealthy_until: dict[str, float] = {}

    # ---- helpers -------------------------------------------------------------------------------
    @property
    def last_model_used(self) -> str | None:
        return getattr(self._local, "model", None)

    def _sanitize(self, msg: str) -> str:
        return str(msg).replace(self._key, "[REDACTED]")[:300]

    @staticmethod
    def _sleep(seconds: float) -> None:
        time.sleep(max(0.0, seconds))

    def _usable(self, model: str) -> str | None:
        """Returns the reason a model must be skipped right now, else None."""
        if self.usage.exhausted_until(model) > time.time():
            return "daily quota exhausted (cached)"
        if self._unhealthy_until.get(model, 0) > time.time():
            return "recently unavailable (circuit open)"
        return None

    def _config(self, system, tools, max_output_tokens, temperature, timeout_s, thinking: bool):
        from google.genai import types
        s = get_settings()
        cfg = dict(system_instruction=system, temperature=s.gemini_temperature if temperature is None else temperature,
                   max_output_tokens=max_output_tokens or s.gemini_max_output_tokens,
                   http_options=types.HttpOptions(timeout=int(timeout_s * 1000)))
        if tools:
            cfg["tools"] = tools
            cfg["automatic_function_calling"] = types.AutomaticFunctionCallingConfig(disable=True)  # backend executes tools
        if thinking and self.thinking_level:
            cfg["thinking_config"] = types.ThinkingConfig(thinking_level=self.thinking_level)
        return types.GenerateContentConfig(**cfg)

    # ---- core call -----------------------------------------------------------------------------
    def generate_raw(self, contents, system: str, tools=None, max_output_tokens: int | None = None,
                     temperature: float | None = None, pin_model: str | None = None, retries: int | None = None,
                     total_deadline_s: float | None = None):
        """Returns the SDK response; `last_model_used` tells which model produced it. Raises LLMError (with .kind/.attempts)."""
        from google.genai import errors

        s = get_settings()
        max_attempts = (retries + 1) if retries is not None else s.gemini_max_attempts
        deadline = time.monotonic() + (total_deadline_s or s.gemini_total_deadline_s)
        models = [pin_model] if pin_model else self.models
        history: list[dict] = []
        last_kind = "unknown"
        for model in models:
            why = self._usable(model)
            if why:
                history.append({"model": model, "skipped": why})
                last_kind = "quota" if "quota" in why else "overloaded"
                continue
            thinking = True
            for attempt in range(max_attempts):
                remaining = deadline - time.monotonic()
                if remaining <= 1.0:
                    history.append({"model": model, "stopped": "total deadline reached"})
                    raise self._final(history, "timeout")
                self.usage.reserve(model)
                t0 = time.monotonic()
                try:
                    resp = self._client.models.generate_content(
                        model=model, contents=contents,
                        config=self._config(system, tools, max_output_tokens, temperature,
                                            min(s.gemini_request_timeout_s, remaining), thinking))
                    um = getattr(resp, "usage_metadata", None)
                    self.usage.record(model, getattr(um, "prompt_token_count", None), getattr(um, "candidates_token_count", None))
                    self._local.model = model
                    self._unhealthy_until.pop(model, None)
                    history.append({"model": model, "ok": True, "seconds": round(time.monotonic() - t0, 1)})
                    log.info("gemini ok model=%s attempts=%d %.1fs", model, attempt + 1, time.monotonic() - t0)
                    return resp
                except errors.APIError as e:
                    info = classify_api_error(e)
                    last_kind = info["kind"]
                    history.append({"model": model, "code": getattr(e, "code", None), "kind": info["kind"],
                                    "seconds": round(time.monotonic() - t0, 1)})
                    log.warning("gemini %s code=%s kind=%s attempt=%d/%d: %s", model, getattr(e, "code", None), info["kind"],
                                attempt + 1, max_attempts, self._sanitize(getattr(e, "message", "")))
                    if info["kind"] == "invalid_request" and thinking and "thinking" in str(getattr(e, "message", "")).lower():
                        thinking = False               # fix the cause (unsupported thinking level), do not blindly retry
                        continue
                    if info["daily_quota"]:
                        self.usage.mark_exhausted(model, info["retry_after"] or 3600)
                        break                          # next model; never hammer an exhausted daily quota
                    if not info["retryable"]:
                        if info["kind"] in ("auth", "invalid_request"):
                            raise self._final(history, info["kind"]) from None   # fallback models cannot fix these
                        break
                    if attempt + 1 >= max_attempts:
                        self._unhealthy_until[model] = time.time() + 60
                        break
                    wait = info["retry_after"] if info["retry_after"] is not None else \
                        random.uniform(0.5, min(8.0, 1.5 * 2 ** attempt))          # exponential backoff, full jitter
                    if wait >= deadline - time.monotonic() - 1.0:
                        history.append({"model": model, "stopped": "wait would exceed total deadline"})
                        break
                    self._sleep(wait)
                except Exception as e:                  # httpx timeouts / connection errors
                    kind = "timeout" if "timeout" in type(e).__name__.lower() else "network"
                    last_kind = kind
                    history.append({"model": model, "kind": kind, "error": type(e).__name__,
                                    "seconds": round(time.monotonic() - t0, 1)})
                    log.warning("gemini %s %s attempt=%d/%d", model, type(e).__name__, attempt + 1, max_attempts)
                    if attempt + 1 >= max_attempts:
                        self._unhealthy_until[model] = time.time() + 60
                        break
                    wait = random.uniform(0.5, min(8.0, 1.5 * 2 ** attempt))
                    if wait >= deadline - time.monotonic() - 1.0:
                        break
                    self._sleep(wait)
        raise self._final(history, last_kind)

    def _final(self, history: list[dict], kind: str) -> LLMError:
        summary = "; ".join(f"{h['model']}: " + (h.get("skipped") or h.get("stopped") or (f"HTTP {h['code']}" if h.get("code") else h.get("kind", "ok")))
                            for h in history)
        return LLMError(f"Gemini unavailable ({kind}). Attempts: {summary}", status=_STATUS.get(kind, 502), kind=kind, attempts=history)

    # ---- plain text ----------------------------------------------------------------------------
    def generate(self, system: str, user: str, max_output_tokens: int | None = None, temperature: float | None = None,
                 retries: int | None = None) -> LLMResult:
        t0 = time.monotonic()
        resp = self.generate_raw(user, system, None, max_output_tokens, temperature, retries=retries)
        text = (resp.text or "").strip()
        if not text:
            raise LLMError("Gemini returned an empty response (possibly blocked or truncated).", kind="empty")
        um = getattr(resp, "usage_metadata", None)
        return LLMResult(text, self.last_model_used or self.model, getattr(um, "prompt_token_count", None),
                         getattr(um, "candidates_token_count", None), time.monotonic() - t0)
