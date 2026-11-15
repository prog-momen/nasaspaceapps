"""The language model is Anthropic claude-haiku-5-5 ONLY: allow-list, no fallback, no other vendor in the code, secrets never logged.
All tests use a FAKE SDK object (mocked, no network, no credits). Live calls are in tests/integration/test_claude_live.py."""
import logging
import re
from pathlib import Path
from types import SimpleNamespace

import anthropic
import httpx
import pytest

from app.llm import claude_client as cc
from app.llm.base import LLMError

ROOT = Path(__file__).resolve().parent.parent
HAIKU = "claude-haiku-5-5"


def api_error(cls, status, message="x"):
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return cls(message, response=httpx.Response(status, request=req, headers={"retry-after": "0"}), body=None)


class FakeSDK:
    def __init__(self, script):
        self.script, self.calls = list(script), []
        self.messages = SimpleNamespace(create=self._create)
        self.models = SimpleNamespace(retrieve=lambda m: SimpleNamespace(id=m, display_name="Claude Haiku"))

    def _create(self, **params):
        self.calls.append(params)
        r = self.script.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def text_resp(t="OK"):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=t)], usage=SimpleNamespace(input_tokens=5, output_tokens=2), stop_reason="end_turn")


def tool_resp(name, args, tid="toolu_1"):
    return SimpleNamespace(content=[SimpleNamespace(type="tool_use", id=tid, name=name, input=args)], usage=SimpleNamespace(input_tokens=9, output_tokens=4), stop_reason="tool_use")


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(cc.ClaudeClient, "_sleep", staticmethod(lambda s: None))


# ---- allow-list -----------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("bad", ["claude-sonnet-5-5", "claude-opus-5-5", "claude-fable-5-2", "claude-haiku-4-5", "gemini-3.5-flash-lite", "", "claude-haiku-5-5-latest", "CLAUDE-HAIKU-5-5"])
def test_any_model_other_than_haiku_is_rejected_at_construction_and_before_any_request(bad):
    with pytest.raises(LLMError) as e:
        cc.ClaudeClient(api_key="k", model=bad, sdk=FakeSDK([]))
    assert e.value.kind == "model_not_allowed"
    sdk = FakeSDK([text_resp()])
    c = cc.ClaudeClient(api_key="k", sdk=sdk)
    assert c.model == HAIKU
    for kw in ({"model": bad}, {"pin_model": bad}):
        with pytest.raises(LLMError) as e2:
            c.generate_raw("hi", "sys", **kw)
        assert e2.value.kind == "model_not_allowed"
    with pytest.raises(LLMError):
        c._send({"model": bad, "max_tokens": 5, "messages": []})                       # even a direct call to the choke point
    assert sdk.calls == []                                                             # NOTHING was sent to the service


def test_misconfigured_env_model_fails_loudly_instead_of_switching(monkeypatch):
    from app.config import get_settings
    s = get_settings()
    monkeypatch.setattr(s, "anthropic_model", "claude-sonnet-5-5")
    with pytest.raises(LLMError) as e:
        cc.ClaudeClient(api_key="k", sdk=FakeSDK([]))
    assert e.value.kind == "model_not_allowed"


def test_every_request_uses_exactly_the_allowed_model():
    sdk = FakeSDK([text_resp("a"), text_resp("b")])
    c = cc.ClaudeClient(api_key="k", sdk=sdk)
    c.generate("sys", "user")
    c.generate_raw("hi", "sys", max_output_tokens=10)
    assert [p["model"] for p in sdk.calls] == [HAIKU, HAIKU]


# ---- no fallback ----------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("exc,kind", [(api_error(anthropic.InternalServerError, 529, "overloaded"), "overloaded"), (api_error(anthropic.InternalServerError, 500), "service_error"),
                                      (api_error(anthropic.RateLimitError, 429), "quota"), (api_error(anthropic.AuthenticationError, 401), "auth"),
                                      (api_error(anthropic.NotFoundError, 404), "model_not_found")])
def test_failure_never_switches_model_retries_only_the_same_model_then_raises(exc, kind):
    sdk = FakeSDK([exc, exc, exc, exc])
    c = cc.ClaudeClient(api_key="k", sdk=sdk)
    with pytest.raises(LLMError) as e:
        c.generate("sys", "user")
    assert e.value.kind == kind
    assert {p["model"] for p in sdk.calls} == {HAIKU} and len(sdk.calls) <= c.settings.llm_max_attempts          # bounded, same model only


def test_transient_error_is_retried_once_on_the_same_model_and_can_succeed():
    sdk = FakeSDK([api_error(anthropic.InternalServerError, 529), text_resp("done")])
    r = cc.ClaudeClient(api_key="k", sdk=sdk).generate("sys", "user")
    assert r.text == "done" and r.model == HAIKU and len(sdk.calls) == 2


def test_non_retryable_errors_are_not_retried():
    sdk = FakeSDK([api_error(anthropic.AuthenticationError, 401)])
    with pytest.raises(LLMError):
        cc.ClaudeClient(api_key="k", sdk=sdk).generate("sys", "user")
    assert len(sdk.calls) == 1


def test_billing_error_is_distinguished_from_quota():
    e = api_error(anthropic.BadRequestError, 400, "Your credit balance is too low to access the Anthropic API")
    with pytest.raises(LLMError) as ex:
        cc.ClaudeClient(api_key="k", sdk=FakeSDK([e])).generate("s", "u")
    assert ex.value.kind == "billing"


def test_when_haiku_fails_the_chat_uses_the_labelled_deterministic_path_and_calls_no_other_model(monkeypatch):
    from tests.test_free_text_regressions import NABLUS_Q, make_agent, power_fixture   # noqa: F401  (fixture reuse)
    from app.chat import tools
    sdk = FakeSDK([api_error(anthropic.RateLimitError, 429)] * 6)
    client = cc.ClaudeClient(api_key="k", sdk=sdk)
    monkeypatch.setattr("app.chat.agent.load_llm_key", lambda: "k")
    from app.chat.agent import ChatAgent
    from app.chat.sessions import SessionStore
    from tests.test_free_text_regressions import FakeSvc, FakeRetriever
    from app.config import KNOWLEDGE_COLLECTION
    svc = FakeSvc(); svc._llm = client; svc.retrievers = {KNOWLEDGE_COLLECTION: FakeRetriever()}
    import json
    from app.data_sources.power import parse_power_monthly
    from app.tools.trend_tool import run_trend_analysis as real_trend
    series = parse_power_monthly(json.loads((ROOT / "tests" / "fixtures" / "power_monthly_nablus_T2M_real_capture.json").read_text(encoding="utf-8")), "T2M", "fixture")
    monkeypatch.setattr(tools, "run_trend_analysis", lambda args: real_trend(args, series_override=series))
    r = ChatAgent(svc, SessionStore(), tool_runner=tools.execute).handle({"message": NABLUS_Q, "controls": {"language": "en"}})
    assert r["tools"][0]["name"] == "analyze_trend" and r["answer_source"] == "template" and r["selected_by"] == "router" and r["model_notice"]["kind"] == "quota"
    assert "Claude" in r["model_notice"]["text"] and {p["model"] for p in sdk.calls} == {HAIKU}


# ---- Tool Use + response shape ----------------------------------------------------------------------------------------------------------
def test_tool_use_request_forces_the_tool_and_parses_the_call():
    from app.chat import decision as D
    sdk = FakeSDK([tool_resp("interpret_request", {"intent": "trend", "place": "Nablus", "start_year": 2005, "end_year": 2025})])
    c = cc.ClaudeClient(api_key="k", sdk=sdk)
    r = c.generate_raw("Has air temperature in Nablus risen?", "sys", tools=[D.DECISION_DECLARATION], tool_choice={"type": "tool", "name": "interpret_request"})
    p = sdk.calls[0]
    assert p["tools"][0]["name"] == "interpret_request" and p["tools"][0]["input_schema"]["properties"]["intent"]["enum"] and p["tool_choice"] == {"type": "tool", "name": "interpret_request"}
    assert r.function_calls[0].name == "interpret_request" and r.function_calls[0].args["start_year"] == 2005 and r.function_calls[0].id == "toolu_1"
    assert r.candidates[0].content[0]["type"] == "tool_use" and r.usage_metadata.prompt_token_count == 9


def test_neutral_declarations_become_valid_anthropic_tools():
    from app.tools.trend_tool import FUNCTION_DECLARATION
    t = cc.to_tools([FUNCTION_DECLARATION])[0]
    assert set(t) == {"name", "description", "input_schema"} and t["input_schema"]["type"] == "object"


# ---- secrets ----------------------------------------------------------------------------------------------------------------------------
def test_api_key_never_appears_in_errors_or_logs(caplog):
    key = "sk-ant-api03-SECRETSECRETSECRETSECRET"
    caplog.set_level(logging.DEBUG)
    sdk = FakeSDK([api_error(anthropic.AuthenticationError, 401, f"invalid x-api-key {key}")])
    with pytest.raises(LLMError) as e:
        cc.ClaudeClient(api_key=key, sdk=sdk).generate("s", "u")
    assert key not in str(e.value) and key not in caplog.text
    from app.config import SecretRedactingFilter
    rec = logging.LogRecord("x", logging.INFO, __file__, 1, f"header x-api-key: {key}", (), None)
    SecretRedactingFilter().filter(rec)
    assert key not in rec.getMessage()


def test_env_files_are_ignored_by_git_and_never_indexed():
    gi = (ROOT.parent / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gi and "*.env" in gi and "البروتوتايب/" in gi
    from app.ingestion import registry, loaders
    blob = (Path(registry.__file__).read_text(encoding="utf-8") + Path(loaders.__file__).read_text(encoding="utf-8")).lower()
    assert ".env" not in blob


# ---- the code base: no other model vendor, one connection layer -------------------------------------------------------------------------
def test_no_gemini_or_other_llm_sdk_is_imported_or_called_anywhere_in_the_app():
    offenders = []
    for p in (ROOT / "app").rglob("*.py"):
        t = p.read_text(encoding="utf-8")
        if re.search(r"google\.genai|from google import genai|generativeai|import openai|GeminiClient|generate_content|\bgemini-\d", t):
            offenders.append(p.name)
        if "messages.create" in t and p.name != "claude_client.py":
            offenders.append(p.name + " (bypasses the central client)")
        if re.search(r"^\s*(?:import anthropic|from anthropic)", t, re.M) and p.name != "claude_client.py":
            offenders.append(p.name + " (imports the SDK outside the central client)")
    assert offenders == []


def test_embeddings_stay_local_multilingual_e5_small():
    from app.config import get_settings
    assert get_settings().embedding_model == "intfloat/multilingual-e5-small"


def test_requests_disable_hidden_thinking_so_text_is_never_starved_of_tokens():
    sdk = FakeSDK([text_resp("x")])
    cc.ClaudeClient(api_key="k", sdk=sdk).generate("s", "u")
    assert sdk.calls[0]["thinking"] == {"type": "disabled"} and sdk.calls[0]["max_tokens"] >= 2048
