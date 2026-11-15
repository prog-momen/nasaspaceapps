"""Reproductions of debug findings. Mock HTTP is explicitly NOT live access."""
import json
import time
from pathlib import Path
from types import SimpleNamespace

import httpx
import numpy as np
import pytest

from app.agent.deterministic import explicit_trend_args
from app.agent.trend_agent import TrendAgent, unsupported_numbers
from app.analysis import stats
from app.analysis.timeseries import MonthlySeries, screen
from app.config import get_settings
from app.data_sources.power import SourceError, fetch_power_monthly
from app.llm.base import LLMError, UsageTracker
from app.reliability import bounded_call, request_budget, retry_after
from app.tools.trend_tool import run_trend_analysis

ARGS = dict(variable="air_temperature", region="Nablus", start_year=2005, end_year=2025)
QUESTION = "هل ارتفعت حرارة الهواء في نابلس بين 2005 و2025؟"


@pytest.fixture
def settings(tmp_path, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "data_dir", tmp_path)
    return s


def test_duplicate_months_are_rejected_instead_of_last_write_wins():
    series = MonthlySeries([2024, 2024], [1, 1], [1., 9.], "C")
    with pytest.raises(ValueError, match="duplicate"):
        screen(series, 2024, 2024)
    r = run_trend_analysis(ARGS, series_override=series)
    assert r["status"] == "invalid_data" and "test" not in r


def test_screen_sorts_dates_and_accounts_for_nan_infinity():
    series = MonthlySeries([2024]*4, [4, 2, 1, 3], [4, np.nan, 1, np.inf], "C")
    s = screen(series, 2024, 2024)
    assert s.value[0] == 1 and s.value[3] == 4
    assert s.counts == dict(valid=2, missing=9, invalid=1)


@pytest.mark.parametrize("x", [[1], [], [1, np.nan, 3], [1, np.inf, 3]])
def test_raw_statistics_require_screened_finite_series(x):
    with pytest.raises(ValueError):
        stats.mann_kendall(x)


@pytest.mark.parametrize("t", [[2001, 2001, 2002], [2003, 2002, 2001]])
def test_raw_slope_rejects_duplicate_or_unordered_time(t):
    with pytest.raises(ValueError, match="time"):
        stats.sen_slope([1, 2, 3], t, 1.)


def power_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.mark.parametrize("response", [
    httpx.Response(200, text="<html>Login</html>", headers={"content-type":"text/html"}),
    httpx.Response(200, json={"error":"bad request"}),
    httpx.Response(200, json={"properties":{"parameter":{"T2M":{}}},"parameters":{"T2M":{"units":"C"}}}),
    httpx.Response(200, text="bad json", headers={"content-type":"application/json"}),
    httpx.Response(403, text="unauthorised"),
])
def test_power_does_not_retry_or_cache_bad_payload(response, settings):
    calls = []
    with power_client(lambda r: calls.append(r) or response) as c:
        with pytest.raises(SourceError):
            fetch_power_monthly("T2M", 32.22, 35.26, 2024, 2024, False, c)
    assert len(calls) == 1 and not list(settings.data_dir.glob("cache/*.json"))


def test_power_transient_backoff_then_validated_download(settings, monkeypatch):
    payload = json.loads((Path(__file__).parent / "fixtures/power_monthly_nablus_T2M_real_capture.json").read_text(encoding="utf-8"))
    responses = [httpx.Response(503, headers={"Retry-After":"2"}), httpx.Response(200, json=payload)]
    waits = []
    monkeypatch.setattr("app.data_sources.power.time.sleep", waits.append)
    with power_client(lambda r: responses.pop(0)) as c:
        s = fetch_power_monthly("T2M", 32.22, 35.26, 2005, 2025, False, c)
    assert waits == [2.] and len(s.value) == 252 and s.source["cache_hit"] is False


def test_power_long_retry_after_stops_without_sleep(settings, monkeypatch):
    calls = []
    monkeypatch.setattr("app.data_sources.power.time.sleep", lambda s: pytest.fail("deadline must prevent waiting"))
    with power_client(lambda r: calls.append(r) or httpx.Response(429, headers={"retry-after":"500"})) as c:
        with pytest.raises(SourceError) as exc:
            fetch_power_monthly("T2M", 0, 0, 2024, 2024, False, c, total_deadline_s=0.2)
    assert len(calls) == 1 and exc.value.kind == "quota"


def test_shared_deadline_bounds_slow_transport_and_late_success_is_discarded():
    t0 = time.monotonic()
    with request_budget(.04):
        with pytest.raises(TimeoutError):
            bounded_call(lambda: time.sleep(.2) or "late success", .04)
    assert time.monotonic() - t0 < .15


def test_retry_after_http_date():
    from datetime import datetime, timedelta, timezone
    from email.utils import format_datetime
    value = retry_after(format_datetime(datetime.now(timezone.utc) + timedelta(seconds=20)))
    assert 18 < value <= 20


def test_deterministic_fallback_keeps_real_tool_status_and_failure_reason():
    class Down:
        def generate_raw(self, *a, **kw):
            raise LLMError("provider quota", 429, "quota", [{"code":429}])
    seen = []
    def tool(args):
        seen.append(args)
        return {"status":"upstream_error", "reason_code":"SOURCE_ERROR", "message":"NASA is unavailable"}
    a = TrendAgent(Down(), tool).ask(QUESTION)
    assert seen == [dict(ARGS, region="nablus")]
    assert a.status == "upstream_error" and a.answer_source == "template" and a.fallback_reason == "quota"
    assert "test" not in a.analysis and "NASA is unavailable" in a.answer


@pytest.mark.parametrize("q", [
    "هل ارتفعت الحرارة في نابلس بين 2005 و2025؟",
    "هل ارتفعت حرارة الهواء بين 2005 و2025؟",
    "هل ارتفعت حرارة الهواء في نابلس والقاهرة بين 2005 و2025؟",
    "توقع حرارة الهواء في نابلس بين 2005 و2025؟",
    "هل ارتفعت حرارة الهواء في نابلس بين 2005 و2025 عند alpha 0.01؟",
])
def test_fallback_refuses_ambiguous_or_modified_questions(q):
    assert explicit_trend_args(q) is None


def test_lst_fallback_never_substitutes_t2m():
    args = explicit_trend_args("هل ارتفعت حرارة سطح الأرض في نابلس بين 2005 و2025؟")
    assert args["variable"] == "land_surface_temperature"
    assert run_trend_analysis(args)["status"] == "data_source_unavailable"


def test_multiple_tool_calls_are_explicitly_rejected_before_any_execution():
    fc = SimpleNamespace(name="analyze_trend", args=ARGS)
    class Multi:
        def generate_raw(self, *a, **k):
            return SimpleNamespace(function_calls=[fc, fc], candidates=[SimpleNamespace(content="model content")])
    ran = []
    with pytest.raises(LLMError, match="one analysis") as exc:
        TrendAgent(Multi(), lambda a: ran.append(a)).ask(QUESTION)
    assert exc.value.kind == "tool_protocol" and not ran


def test_numeric_guard_no_longer_accepts_sign_reversal_or_wrong_small_p():
    assert unsupported_numbers("slope = -0.0491", {"slope":.0491}) == ["-0.0491"]
    assert unsupported_numbers("p = 0.001", {"p":.006}) == ["0.001"]


def test_tool_result_preserves_tool_use_id_and_echoes_the_original_assistant_content():
    original_content = [{"type": "tool_use", "id": "toolu_123", "name": "analyze_trend", "input": dict(ARGS)}]
    fc = SimpleNamespace(name="analyze_trend", args=ARGS, id="toolu_123")
    seen = []
    class Fake:
        last_model_used = "claude-haiku-5-5"
        def generate_raw(self, contents, system, **kw):
            seen.append((list(contents), kw))
            if len(seen) == 1:
                return SimpleNamespace(function_calls=[fc], candidates=[SimpleNamespace(content=original_content)], text="")
            assert contents[1] == {"role": "assistant", "content": original_content}          # the model's own tool_use block is echoed back unchanged
            assert contents[2]["content"][0]["type"] == "tool_result" and contents[2]["content"][0]["tool_use_id"] == "toolu_123"
            assert "pin_model" not in kw and "model" not in kw                                 # the agent never selects a model
            return SimpleNamespace(text="No trend verdict could be issued.", function_calls=[], usage_metadata=None)
    a = TrendAgent(Fake(), lambda a: {"status":"insufficient_data", "reason_code":"SHORT", "message":"too short"}).ask(QUESTION)
    assert a.status == "insufficient_data" and len(seen) == 2



def test_final_tool_call_cannot_start_an_infinite_loop():
    fc = SimpleNamespace(name="analyze_trend", args=ARGS)
    class Repeats:
        count = 0
        def generate_raw(self, *a, **kw):
            self.count += 1
            return SimpleNamespace(function_calls=[fc], candidates=[SimpleNamespace(content="model")])
    model = Repeats()
    a = TrendAgent(model, lambda a: {"status":"insufficient_data", "reason_code":"SHORT", "message":"too short"}).ask(QUESTION)
    assert model.count == 2 and a.answer_source == "template" and a.fallback_reason == "tool_protocol"


def test_slope_and_ci_are_cross_checked_against_scipy():
    from scipy.stats import theilslopes
    t = np.arange(30.)
    x = .5*t + np.random.default_rng(1).normal(0, 1, 30)
    ours = stats.sen_slope(x, t, stats.mann_kendall(x).var_S)
    ref = theilslopes(x, t)
    assert ours["slope"] == pytest.approx(ref.slope)
    # Project interpolates order-statistic ranks; SciPy rounds them. Difference
    # is documented, bounded here by the adjacent pair-slope order statistics.
    slopes = np.sort([(x[j]-x[i])/(t[j]-t[i]) for i in range(30) for j in range(i+1, 30)])
    for actual, reference in [(ours["ci_low"],ref.low_slope),(ours["ci_high"],ref.high_slope)]:
        i = int(np.searchsorted(slopes, reference))
        assert slopes[max(0,i-1)] <= actual <= slopes[min(len(slopes)-1,i+1)]


def test_model_cannot_give_a_numberless_trend_verdict_without_a_tool():
    class Ungrounded:
        def generate_raw(self, *a, **k):
            return SimpleNamespace(function_calls=[],text="The temperature is increasing.")
    a = TrendAgent(Ungrounded(),lambda a: pytest.fail("no call requested")).ask(QUESTION)
    assert a.status=="no_tool_call" and a.answer_source=="template"


def test_api_exposes_fallback_source_reason_and_computed_data(mem_store,embedder,sample_doc,monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.main import app
    from app.chunking.chunker import chunk_document
    from app.rag.service import RagService
    from app.data_sources.power import parse_power_monthly
    from app.tools import trend_tool
    class Down:
        model="blocked-test-model"
        def generate_raw(self,*a,**kw):
            raise LLMError("quota",429,"quota",[{"code":429}])
    svc=RagService(embedder=embedder,store=mem_store,llm=Down(),min_dense_score=.05)
    chunks=chunk_document(sample_doc)
    mem_store.upsert_source("earth_knowledge",sample_doc.source_id,chunks,embedder.embed_documents([c.embed_text for c in chunks]))
    payload=json.loads((Path(__file__).parent / "fixtures/power_monthly_nablus_T2M_real_capture.json").read_text(encoding="utf-8"))
    series=parse_power_monthly(payload,"T2M","RECORDED_FIXTURE_NOT_LIVE")
    monkeypatch.setattr(trend_tool,"fetch_power_monthly",lambda *a,**k:series)
    monkeypatch.setattr(app.state,"rag",svc,raising=False)
    with TestClient(app) as client:
        for endpoint in ["/api/analysis/trend/ask","/api/rag/query"]:
            response=client.post(endpoint,json={"question":QUESTION})
            assert response.status_code==200
            body=response.json()
            assert body["answer_source"]=="template" and body["fallback_reason"]=="quota"
            assert body["analysis"]["status"]=="ok" and body["analysis"]["data_quality"]["valid_months"]==252


