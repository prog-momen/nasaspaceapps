"""Function-calling flow with a FAKE Gemini (offline). Proves the control flow and the guards, not model quality."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.agent.trend_agent import TrendAgent, render_template, unsupported_numbers
from app.api.main import app
from app.data_sources.power import parse_power_monthly
from app.llm.gemini_client import LLMError
from app.rag.service import RagService
from app.tools import trend_tool

FIXTURE = Path(__file__).parent / "fixtures" / "power_monthly_nablus_T2M_real_capture.json"
ARGS = {"variable": "air_temperature", "region": "Nablus", "start_year": 2005, "end_year": 2025}


@pytest.fixture
def real_series():
    return parse_power_monthly(json.loads(FIXTURE.read_text(encoding="utf-8")), "T2M", "fixture")


@pytest.fixture
def tool(real_series):
    return lambda args: trend_tool.run_trend_analysis(args, fetcher=lambda *a, **k: real_series)


def response(text=None, call=None):
    content = SimpleNamespace(role="model", parts=[])
    fcs = [SimpleNamespace(name=call[0], args=call[1])] if call else []
    return SimpleNamespace(text=text, function_calls=fcs, candidates=[SimpleNamespace(content=content)],
                           usage_metadata=SimpleNamespace(prompt_token_count=11, candidates_token_count=7))


class FakeGemini:
    model = "fake-gemini"

    def __init__(self, first, second=None, second_error=None):
        self.queue = [first] + ([second] if second else [])
        self.second_error = second_error
        self.calls = []

    def generate_raw(self, contents, system, tools=None, **kw):
        self.calls.append({"n_contents": len(contents), "tools": bool(tools), "system": system})
        if len(self.calls) == 2 and self.second_error:
            raise self.second_error
        return self.queue[len(self.calls) - 1]


def good_text(result):
    t = result["test"]
    return (f"تم تحليل درجة حرارة الهواء في Nablus للفترة 2005-01 إلى 2025-12 باستخدام {t['n_used']} متوسطًا سنويًا. "
            f"رُصد اتجاه تصاعدي ذو دلالة إحصائية عند مستوى {t['alpha']} (p = {t['p_value']})، وSen's slope = {t['sen_slope']['value']} °C/year، "
            f"وKendall's tau = {t['kendall_tau']}. هذا يصف الاتجاه التاريخي فقط ولا يثبت السبب ولا يتنبأ بالمستقبل.")


def test_gemini_calls_tool_then_explains_only_tool_output(tool):
    expected = tool(ARGS)
    fake = FakeGemini(response(call=("analyze_trend", dict(ARGS))), response(text=good_text(expected)))
    a = TrendAgent(fake, tool).ask("هل ارتفعت حرارة الهواء في نابلس بين 2005 و2025؟")
    assert a.answer_source == "gemini" and a.status == "ok" and not a.warnings
    assert a.tool_calls == [{"name": "analyze_trend", "args": ARGS, "status": "ok"}]
    assert fake.calls[0]["tools"] is True and fake.calls[1]["tools"] is False       # second turn: no tools, explain only
    assert a.analysis["test"]["sen_slope"]["unit"] == "°C/year" and a.analysis["chart"]["y"]
    assert a.answer == good_text(a.analysis)


def test_fabricated_number_in_explanation_is_rejected_and_template_used(tool):
    expected = tool(ARGS)
    lie = good_text(expected) + " ومن المتوقع أن ترتفع الحرارة 3.7 درجة بحلول 2050."
    a = TrendAgent(FakeGemini(response(call=("analyze_trend", dict(ARGS))), response(text=lie)), tool).ask("اتجاه الحرارة في نابلس 2005-2025")
    assert a.answer_source == "template" and "3.7" not in a.answer
    assert any("rejected" in w for w in a.warnings)
    assert str(expected["test"]["sen_slope"]["value"]) in a.answer           # template numbers come from the tool


def test_non_significant_result_must_use_mandated_phrase(real_series):
    flat = trend_tool.run_trend_analysis(ARGS, fetcher=lambda *a, **k: _flatten(real_series))
    assert flat["interpretation"]["code"] == "NOT_SIGNIFICANT"
    tool = lambda args: flat
    bad = "لا يوجد تغيّر في درجة الحرارة."
    a = TrendAgent(FakeGemini(response(call=("analyze_trend", dict(ARGS))), response(text=bad)), tool).ask("هل ارتفعت الحرارة في نابلس؟")
    assert a.answer_source == "template" and "البيانات الحالية لا تكفي لتأكيد وجود اتجاه" in a.answer
    assert "لا يوجد تغيّر" not in a.answer


def _flatten(series):
    import numpy as np
    r = np.random.default_rng(1)
    series.value = [round(15 + 5 * np.sin(2 * np.pi * m / 12) + float(r.normal(0, 0.8)), 3) for m in series.month]
    return series


def test_gemini_failure_after_tool_run_keeps_the_computed_result(tool):
    fake = FakeGemini(response(call=("analyze_trend", dict(ARGS))), second_error=LLMError("Gemini API error (503).", 503))
    a = TrendAgent(fake, tool).ask("اتجاه الحرارة في نابلس 2005-2025")
    assert a.answer_source == "template" and a.status == "ok" and a.analysis["test"]["significant"] is True
    assert any("unavailable" in w for w in a.warnings) and "Sen's slope" in a.answer


def test_gemini_failure_before_tool_call_propagates(tool):
    class Down:
        model = "x"
        def generate_raw(self, *a, **k):
            raise LLMError("Gemini API error (503).", 503)
    with pytest.raises(LLMError):
        TrendAgent(Down(), tool).ask("اتجاه الحرارة في نابلس 2005-2025")


def test_unavailable_variable_is_explained_without_verdict(tool):
    args = {"variable": "land_surface_temperature", "region": "Amazon", "start_year": 2005, "end_year": 2025}
    fake = FakeGemini(response(call=("analyze_trend", args)), response(text="لا يتوفر مصدر بيانات حرارة سطح الأرض حاليًا لأنه يتطلب Earthdata Login."))
    a = TrendAgent(fake, tool).ask("هل ارتفعت حرارة سطح الأرض بالأمازون بين 2005 و2025؟")
    assert a.status == "data_source_unavailable" and a.analysis["reason_code"] == "SOURCE_REQUIRES_CREDENTIALS"
    assert "test" not in a.analysis
    t = render_template(a.analysis)
    assert "تعذّر إصدار حكم" in t and "air_temperature" in t


def test_model_that_skips_the_tool_cannot_produce_numbers(tool):
    a = TrendAgent(FakeGemini(response(text="ارتفعت الحرارة 1.5 درجة.")), tool).ask("هل ارتفعت الحرارة؟")
    assert a.status == "no_tool_call" and a.analysis is None and "1.5" not in a.answer


def test_clarifying_question_is_allowed_without_numbers(tool):
    a = TrendAgent(FakeGemini(response(text="ما هي المنطقة والفترة الزمنية التي تقصدها؟")), tool).ask("هل ارتفعت الحرارة؟")
    assert a.status == "clarification" and a.analysis is None


def test_unknown_function_is_never_executed(tool):
    ran = []
    t = lambda args: ran.append(args) or {}
    with pytest.raises(LLMError):
        TrendAgent(FakeGemini(response(call=("delete_everything", {"x": 1}))), t).ask("اتجاه الحرارة في نابلس 2005-2025")
    assert not ran


def test_unsupported_number_checker():
    res = {"test": {"p_value": 0.006, "sen_slope": {"value": 0.0491}}, "span": 21}
    assert unsupported_numbers("p = 0.006 و Sen 0.049 خلال 21 سنة [1]", res) == []
    assert unsupported_numbers("الارتفاع 2.5 درجة", res) == ["2.5"]
    assert unsupported_numbers("الفترة 2005", res, question="2005 إلى 2025") == []


def test_function_declaration_is_restricted():
    d = trend_tool.FUNCTION_DECLARATION
    assert d["name"] == "analyze_trend" and set(d["parameters"]["required"]) == {"variable", "start_year", "end_year"}
    assert "air_temperature" in d["parameters"]["properties"]["variable"]["enum"]
    assert "forecast" in d["description"].lower() and "not" in d["description"].lower()


# ---- API + pipeline routing -----------------------------------------------------------------------------------

@pytest.fixture
def client(mem_store, embedder, sample_doc, fake_llm, real_series, monkeypatch):
    from app.chunking.chunker import chunk_document
    svc = RagService(embedder=embedder, store=mem_store, llm=fake_llm, min_dense_score=0.05)
    chunks = chunk_document(sample_doc)
    mem_store.upsert_source("earth_knowledge", sample_doc.source_id, chunks, embedder.embed_documents([c.embed_text for c in chunks]))
    monkeypatch.setattr(trend_tool, "fetch_power_monthly", lambda *a, **k: real_series)
    app.state.rag = svc
    with TestClient(app) as c:
        app.state.rag = svc
        yield c, svc
    app.state.rag = None


def test_direct_trend_endpoint_is_deterministic_and_complete(client):
    c, _ = client
    r = c.post("/api/analysis/trend", json=ARGS).json()
    assert r["status"] == "ok" and r["test"]["alpha"] == 0.05 and r["chart"]["sen_line"]
    r2 = c.post("/api/analysis/trend", json={**ARGS, "significance_level": 0.01}).json()
    assert r2["test"]["alpha"] == 0.01
    assert c.post("/api/analysis/trend", json={**ARGS, "end_year": 1990}).status_code == 422


def test_query_trend_question_is_routed_to_tool_analysis(client, monkeypatch):
    c, svc = client
    expected = trend_tool.run_trend_analysis(ARGS)
    fake = FakeGemini(response(call=("analyze_trend", dict(ARGS))), response(text=good_text(expected)))
    svc._llm = fake
    r = c.post("/api/rag/query", json={"question": "هل ارتفعت حرارة الهواء في نابلس بين 2005 و2025؟"}).json()
    assert r["answer_type"] == "tool_analysis" and r["analysis"]["status"] == "ok" and r["analysis"]["chart"]
    assert r["intent"]["kind"] == "needs_analysis" and "answer_source=gemini" in r["warnings"]


def test_query_trend_falls_back_to_requires_data_tool_when_gemini_is_down(client):
    c, svc = client

    class Down:
        model = "x"
        def generate_raw(self, *a, **k):
            raise LLMError("Gemini API error (503).", 503)
    svc._llm = Down()
    r = c.post("/api/rag/query", json={"question": "هل ارتفعت حرارة الهواء في نابلس بين 2005 و2025؟"}).json()
    assert r["answer_type"] == "requires_data_tool" and r["analysis"] is None
    assert "analyze_trend" in r["intent"]["required_tools"] or "fetch_timeseries" in r["intent"]["required_tools"]


def test_forecast_questions_never_reach_the_trend_tool(client):
    c, svc = client
    called = []
    svc.pipeline.trend_handler = lambda *a: called.append(a)
    r = c.post("/api/rag/query", json={"question": "توقع هطول الأمطار في الرياض عام 2027"}).json()
    assert r["answer_type"] == "requires_data_tool" and r["intent"]["kind"] == "needs_forecast" and not called
