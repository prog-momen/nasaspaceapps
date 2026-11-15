"""Retry/classification logic with a FAKE SDK transport (offline). These prove the policy, not Google's availability."""
import time
from types import SimpleNamespace

import pytest
from google.genai import errors

from app.llm.gemini_client import GeminiClient, LLMError, UsageTracker, classify_api_error


def api_error(code, status="X", details=None, retry_after_header=None):
    body = {"error": {"code": code, "status": status, "message": "boom", "details": details or []}}
    e = errors.APIError(code, body)
    if retry_after_header is not None:
        e.response = SimpleNamespace(headers={"retry-after": str(retry_after_header)})
    return e


DAILY = [{"@type": "type.googleapis.com/google.rpc.QuotaFailure",
          "violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]},
         {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "45812s"}]
PER_MIN = [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "7s"}]


class FakeModels:
    def __init__(self, script):
        self.script, self.calls = script, []

    def generate_content(self, model, contents, config):
        self.calls.append(model)
        step = self.script[model].pop(0) if isinstance(self.script, dict) else self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return SimpleNamespace(text=step, usage_metadata=SimpleNamespace(prompt_token_count=5, candidates_token_count=2))


@pytest.fixture
def make(tmp_path):
    import itertools
    n = itertools.count()

    def _make(script, fallbacks=(), cap=100, **kw):
        c = GeminiClient(api_key="test-key-not-real", model="m-primary", fallback_models=list(fallbacks),
                         usage=UsageTracker(tmp_path / f"u{next(n)}.json", cap), **kw)
        c._client = SimpleNamespace(models=FakeModels(script))
        c.waits = []
        c._sleep = lambda s: c.waits.append(s)
        return c
    return _make


def test_classification_table():
    assert classify_api_error(api_error(503))["kind"] == "overloaded" and classify_api_error(api_error(503))["retryable"]
    assert classify_api_error(api_error(504))["kind"] == "timeout"
    assert classify_api_error(api_error(403))["kind"] == "auth" and not classify_api_error(api_error(403))["retryable"]
    assert classify_api_error(api_error(404))["kind"] == "model_not_found"
    assert classify_api_error(api_error(400))["kind"] == "invalid_request"
    daily = classify_api_error(api_error(429, details=DAILY))
    assert daily["daily_quota"] and not daily["retryable"] and daily["retry_after"] == 45812
    minute = classify_api_error(api_error(429, details=PER_MIN))
    assert minute["retryable"] and minute["retry_after"] == 7 and not minute["daily_quota"]
    assert classify_api_error(api_error(503, retry_after_header=4))["retry_after"] == 4


def test_transient_errors_retry_with_backoff_then_succeed(make):
    c = make([api_error(503), api_error(504), "ok"])
    r = c.generate("s", "u")
    assert r.text == "ok" and len(c._client.models.calls) == 3 and len(c.waits) == 2
    assert all(0.5 <= w <= 8 for w in c.waits)                      # jittered, bounded


def test_retry_after_is_honoured(make):
    c = make([api_error(503, retry_after_header=3), "ok"])
    c.generate("s", "u")
    assert c.waits == [3.0]


def test_attempts_are_bounded_and_error_is_classified(make):
    c = make([api_error(503)] * 10)
    with pytest.raises(LLMError) as ei:
        c.generate("s", "u")
    assert len(c._client.models.calls) == 3 and ei.value.kind == "overloaded" and ei.value.status == 503


@pytest.mark.parametrize("code,kind", [(400, "invalid_request"), (403, "auth"), (401, "auth")])
def test_non_transient_errors_are_not_retried(make, code, kind):
    c = make([api_error(code)] * 5, fallbacks=["m-fallback"])
    with pytest.raises(LLMError) as ei:
        c.generate("s", "u")
    assert len(c._client.models.calls) == 1 and ei.value.kind == kind      # a fallback model cannot fix a bad key/request


def test_daily_quota_is_not_retried_and_is_remembered(make):
    c = make([api_error(429, details=DAILY)] * 5)
    with pytest.raises(LLMError) as ei:
        c.generate("s", "u")
    assert len(c._client.models.calls) == 1 and ei.value.kind == "quota" and ei.value.status == 429
    with pytest.raises(LLMError):
        c.generate("s", "u")
    assert len(c._client.models.calls) == 1                             # second call made NO network request
    assert c.usage.exhausted_until("m-primary") > time.time() + 40000


def test_fallback_model_used_only_when_primary_fails(make):
    c = make({"m-primary": [api_error(429, details=DAILY)], "m-fallback": ["from fallback"]}, fallbacks=["m-fallback"])
    r = c.generate("s", "u")
    assert r.text == "from fallback" and r.model == "m-fallback" and c._client.models.calls == ["m-primary", "m-fallback"]
    c2 = make({"m-primary": ["primary ok"], "m-fallback": ["x"]}, fallbacks=["m-fallback"])
    assert c2.generate("s", "u").model == "m-primary" and c2._client.models.calls == ["m-primary"]


def test_pinned_model_never_falls_back(make):
    c = make({"m-primary": [api_error(503)] * 3, "m-fallback": ["x"]}, fallbacks=["m-fallback"])
    with pytest.raises(LLMError):
        c.generate_raw("u", "s", pin_model="m-primary")
    assert "m-fallback" not in c._client.models.calls


def test_total_deadline_stops_waiting(make):
    c = make([api_error(503, retry_after_header=500)] * 3)
    t0 = time.monotonic()
    with pytest.raises(LLMError):
        c.generate("s", "u")
    assert time.monotonic() - t0 < 5 and len(c._client.models.calls) == 1 and c.waits == []   # would not wait 500 s


def test_network_errors_are_transient(make):
    import httpx
    c = make([httpx.ConnectTimeout("t"), "ok"])
    assert c.generate("s", "u").text == "ok" and len(c.waits) == 1


def test_local_cap_prevents_requests(make):
    c = make(["a", "b", "c"], cap=2)
    c.generate("s", "u"), c.generate("s", "u")
    with pytest.raises(LLMError) as ei:
        c.generate("s", "u")
    assert ei.value.kind == "budget" and len(c._client.models.calls) == 2
    assert c.usage.today()["models"]["m-primary"]["requests"] == 2


def test_sdk_level_retries_are_disabled():
    c = GeminiClient(api_key="test-key-not-real", usage=None)
    assert c._client._api_client._http_options.retry_options.attempts == 1


def test_key_never_appears_in_errors(make):
    e = api_error(503)
    e.message = "failure for key test-key-not-real"
    c = make([e] * 3)
    with pytest.raises(LLMError) as ei:
        c.generate("s", "u")
    assert "test-key-not-real" not in str(ei.value) and "test-key-not-real" not in repr(ei.value.attempts)
    assert "test-key-not-real" not in c._sanitize("x test-key-not-real y")
