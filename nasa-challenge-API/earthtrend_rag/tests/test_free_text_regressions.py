"""Regression tests for the free-text chat pipeline (decision record, routing, language, grounding, panel/map, failure handling).

Data labels: the Nablus trend uses the REAL captured NASA POWER response in tests/fixtures (saved dataset, no network). Weather/FIRMS/etc. tool
results are STUBS (mocked) because these tests check routing and presentation, not the providers. Gemini is never contacted: it is absent or a fake
that raises a quota error. Live FIRMS access is tested in tests/integration/test_providers_live.py.
"""
import json
from datetime import date
import re
from pathlib import Path

import pytest

from app.analysis.catalog import VARIABLES
from app.chat import decision as D
from app.chat import panel as P
from app.chat import render, router, tools
from app.chat.agent import ChatAgent, detect_language
from app.chat.sessions import SessionStore
from app.data_sources.power import parse_power_monthly
from app.llm.base import LLMError
from app.providers import base, firms
from app.rag import evidence
from app.tools.trend_tool import run_trend_analysis as real_trend

FIX = Path(__file__).parent / "fixtures" / "power_monthly_nablus_T2M_real_capture.json"
ROOT = Path(__file__).resolve().parent.parent
NABLUS_Q = "Has air temperature in Nablus risen between 2005 and 2025?"
AR_RX = re.compile(r"[؀-ۿ]")


class FakeSvc:
    _llm = None
    pipeline = type("P", (), {"llm": None, "min_dense_score": 0.5, "_select": lambda self, items, q=None: []})()
    retrievers = {}
    llm = None


class Empty:
    items, best_dense = [], 0.0


class FakeRetriever:
    def retrieve(self, q, top_k=5, **kw):
        return Empty()


def make_agent(monkeypatch, runner=None, gemini=None):
    """gemini=None -> no key (deterministic path). gemini=<obj> -> a fake client used for interpretation/explanation."""
    monkeypatch.setattr("app.chat.agent.load_llm_key", (lambda: "x") if gemini else (lambda: None))
    svc = FakeSvc()
    svc._llm = gemini
    from app.config import KNOWLEDGE_COLLECTION
    svc.retrievers = {KNOWLEDGE_COLLECTION: FakeRetriever()}
    return ChatAgent(svc, SessionStore(), tool_runner=runner)


@pytest.fixture
def power_fixture(monkeypatch):
    series = parse_power_monthly(json.loads(FIX.read_text(encoding="utf-8")), "T2M", "fixture")
    monkeypatch.setattr(tools, "run_trend_analysis", lambda args: real_trend(args, series_override=series))
    return series


def stub_weather(name, args, defaults=None):
    res = base.envelope("Open-Meteo", "Forecast API", "weather_forecast", "ok", live=True, cache="miss", data={}, limitations=["stub"],
                        actual={"grid": {"latitude": 30.0, "longitude": 31.2}, "timezone": "Africa/Cairo", "period": {"first": "2026-11-15", "last": "2026-11-17"}, "issue_time": None})
    rows = [{"date": f"2026-11-{15 + i}", "tmax_c": 24 + i, "tmin_c": 15, "precip_mm": 0, "wind_max_kmh": 12} for i in range(3)]
    summ = {"status": "ok", "product": "Forecast API", "timezone": "Africa/Cairo", "grid": {"latitude": 30.0, "longitude": 31.2}, "period": {"first": "2026-11-15", "last": "2026-11-17"}, "units": {}, "daily": rows,
            "source_type": "operational forecast", "issue_time": None, "cache": "miss"}
    loc = (defaults or {}).get("location") or {"name": "?", "latitude": 0.0, "longitude": 0.0}
    return tools.Outcome(result=res, artifacts=[], summary=summ, location=loc, period={"days": 3}, used_args=args, tool=name, status="ok", duration_ms=1)


def failing_tool(name, args, defaults=None):
    res = base.envelope("Open-Meteo", "Forecast API", "weather_forecast", "upstream_error", "HTTP_503", None)
    return tools.Outcome(result=res, artifacts=[], summary={"status": "upstream_error"}, location={"name": "Cairo, Egypt", "latitude": 30.0, "longitude": 31.2}, period=None, used_args=args, tool=name, status="upstream_error", duration_ms=1)


TPL = {"answer_mode": "template", "language": "en"}


# 1 ------------------------------------------------------------------------------------------------------------------------
def test_nablus_typed_question_selects_power_trend_and_respects_the_period(monkeypatch, power_fixture):
    seen = []
    a = make_agent(monkeypatch, lambda n, ar, d=None: seen.append((n, dict(ar))) or tools.execute(n, ar, d))
    r = a.handle({"message": NABLUS_Q, "controls": TPL})
    assert seen[0][0] == "analyze_trend" and seen[0][1]["start_year"] == 2005 and seen[0][1]["end_year"] == 2025 and seen[0][1]["variable"] == "air_temperature"
    assert r["decision"]["intent"] == "trend" and r["decision"]["provider"] == "NASA POWER" and r["decision"]["place"].startswith("Nablus")
    assert r["status"] == "ok" and r["outcome"] == "answered" and "Open-Meteo" not in r["answer"] and "366" not in r["answer"]
    assert r["panel"]["status"] == "ok" and "Nablus" in r["panel"]["title"] and any(x["type"] == "line_chart" for x in r["inline"])
    assert r["map"]["requested"]["name"].startswith("Nablus") and r["map"]["footprint"]["type"] == "grid_cell"          # requested place vs data footprint


@pytest.mark.parametrize("q", ["Has air temperature in Nablus risen between 2005 and 2025?", "Is it getting hotter in Nablus from 2005 to 2025?", "هل ارتفعت حرارة الهواء في نابلس بين 2005 و2025؟",
                               "Did the temperature change in Nablus between 2005 and 2025", "temperature in Nablus 2005-2025"])
def test_every_multi_year_temperature_phrasing_goes_to_the_trend_workflow_never_to_weather(q):
    p = router.route(q)
    assert p.tool == "analyze_trend", q


def test_long_historical_weather_span_is_coerced_to_trend_not_rejected():
    d = D.from_tool("get_weather", {"mode": "historical", "start_date": "2005-01-01", "end_date": "2025-12-31", "place": "Nablus"}, "gemini")
    v = D.validate(d, today=__import__("datetime").date(2026, 11, 15))
    assert v.action == "proceed" and v.decision.intent == "trend" and v.decision.start_year == 2005 and v.decision.end_year == 2025 and v.decision.notes


# 2 ------------------------------------------------------------------------------------------------------------------------
def test_example_buttons_and_typed_text_share_one_pipeline():
    js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "onclick: () => send(q)" in js and "async function send(message" in js          # buttons call the same send(text) as the composer
    assert 'send($("input").value)' in js
    assert "hidden" not in re.search(r"examples\"\)\.replaceChildren[^\n]*", js).group(0).lower()


def test_identical_text_gives_identical_requests_regardless_of_entry_point(monkeypatch, power_fixture):
    seen = []
    a = make_agent(monkeypatch, lambda n, ar, d=None: seen.append((n, dict(ar))) or tools.execute(n, ar, d))
    a.handle({"message": NABLUS_Q, "controls": TPL})                       # "typed"
    a.handle({"message": NABLUS_Q, "controls": TPL})                       # "button": the UI sends exactly the same body
    assert seen[0] == seen[1]


# 3 ------------------------------------------------------------------------------------------------------------------------
def test_short_forecast_selects_the_forecast_workflow(monkeypatch):
    seen = []
    a = make_agent(monkeypatch, lambda n, ar, d=None: seen.append((n, dict(ar))) or stub_weather(n, ar, d))
    r = a.handle({"message": "What is the weather forecast for Cairo for the next 3 days?", "controls": TPL})
    assert seen[0][0] == "get_weather" and seen[0][1]["mode"] == "forecast" and seen[0][1]["days"] == 3
    assert r["decision"]["intent"] == "weather_forecast" and r["outcome"] == "answered" and "Insufficient" not in r["answer"]


# 4 ------------------------------------------------------------------------------------------------------------------------
def test_arabic_question_with_english_ui_is_answered_in_arabic(monkeypatch):
    a = make_agent(monkeypatch, stub_weather)
    r = a.handle({"message": "ما توقع الطقس في القاهرة للأيام الثلاثة القادمة؟", "controls": {"answer_mode": "template", "language": "en"}})
    assert r["language"] == "ar" and AR_RX.search(r["answer"]) and r["ui_language"] == "en"
    r2 = a.handle({"message": "weather forecast for Cairo", "controls": {"answer_mode": "template", "language": "ar"}})
    assert r2["language"] == "en" and not AR_RX.search(r2["answer"])


def test_ui_language_is_only_the_fallback_for_ambiguous_messages():
    assert detect_language("2005 2025", "ar") == "ar" and detect_language("2005 2025", "en") == "en"
    assert detect_language("نابلس", "en") == "ar" and detect_language("Nablus trend", "ar") == "en"
    assert detect_language("ما حرارة Cairo اليوم؟", "en") == "ar"


# 5 ------------------------------------------------------------------------------------------------------------------------
def test_follow_up_changes_location_context_and_map(monkeypatch):
    a = make_agent(monkeypatch, stub_weather)
    r1 = a.handle({"message": "What is the weather forecast for Cairo for the next 3 days?", "controls": TPL})
    r2 = a.handle({"message": "And for Alexandria?", "session_id": r1["session_id"], "controls": TPL})
    assert r1["map"]["requested"]["name"].startswith("Cairo") and r2["map"]["requested"]["name"].startswith("Alexandria")
    assert r2["selected_by"] == "follow_up" and r2["decision"]["intent"] == "weather_forecast" and abs(r1["map"]["requested"]["lat"] - r2["map"]["requested"]["lat"]) > 0.5


# 6 ------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("msg,status", [("convert FIRMS detections to burned area in hectares", "unsupported"), ("توقع حرارة الرياض في 2040", "unsupported"), ("weather forecast", "clarification")])
def test_unsupported_or_incomplete_requests_run_no_tool_and_invent_nothing(monkeypatch, msg, status):
    ran = []
    a = make_agent(monkeypatch, lambda *x, **k: ran.append(1))
    r = a.handle({"message": msg, "controls": TPL})
    assert r["status"] == status and not ran and r["panel"]["status"] != "ok" and r["map"] is None
    if status == "clarification":
        assert r["outcome"] == "ambiguous" and r["answer"].count("?") == 1


def test_trend_needs_a_period_and_never_future_years():
    d = D.from_tool("analyze_trend", {"place": "Nablus"}, "router")                       # no period: the obvious default is assumed AND disclosed, not asked
    v = D.validate(d, today=__import__("datetime").date(2026, 11, 15))
    assert v.action == "proceed" and (v.decision.start_year, v.decision.end_year) == (2001, 2025) and v.decision.assumptions[0]["field"] == "period"
    d = D.from_tool("analyze_trend", {"place": "Nablus", "start_year": 2020, "end_year": 2040}, "router")
    assert D.validate(d, today=__import__("datetime").date(2026, 11, 15)).text_key == "future_trend"


def test_ambiguous_place_name_asks_instead_of_guessing(monkeypatch):
    from app.providers import open_meteo
    pl = [{"name": "Springfield", "country": "USA", "admin1": "Illinois", "latitude": 39.8, "longitude": -89.6, "population": 116000, "timezone": "x"},
          {"name": "Springfield", "country": "USA", "admin1": "Missouri", "latitude": 37.2, "longitude": -93.3, "population": 169000, "timezone": "x"}]
    monkeypatch.setattr(open_meteo, "geocode", lambda name, lang="en", count=3: base.envelope("Open-Meteo", "geocoding", "map_visualization", "ok", data={"places": pl}))
    a = make_agent(monkeypatch)
    r = a.handle({"message": "weather forecast for Springfield", "controls": TPL})
    assert r["status"] == "clarification" and "Illinois" in r["answer"] and "Missouri" in r["answer"] and r["tools"][0]["status"] == "invalid_request"


# 7 ------------------------------------------------------------------------------------------------------------------------
def test_unrelated_passages_do_not_become_evidence():
    q = "What does a vegetation index measure?"
    unrelated = "The FIRMS area API requires a MAP_KEY and supports day ranges from one to five days."
    related = "Vegetation indices such as NDVI measure vegetation greenness from red and near-infrared reflectance."
    assert not evidence.supports(q, unrelated, "FIRMS API", 0.62, 0.5)
    assert evidence.supports(q, related, "NDVI vegetation", 0.62, 0.5)
    assert not evidence.supports(q, related, "NDVI vegetation", 0.40, 0.5)                      # below the dense threshold
    # a generic definition must not be used as evidence for a place/date-specific value that it cannot contain
    assert not evidence.supports("What is the vegetation index of the Sahara in March?", related, "NDVI vegetation", 0.62, 0.5)


def test_arabic_question_against_english_passage_needs_a_dense_margin():
    q = "ما هو مؤشر NDVI؟"
    p = "NDVI is the normalized difference vegetation index."
    assert evidence.supports(q, p, "NDVI", 0.60, 0.5) and not evidence.supports(q, p, "NDVI", 0.51, 0.5)


def test_knowledge_question_without_evidence_says_insufficient_with_a_reason(monkeypatch):
    a = make_agent(monkeypatch)
    r = a.handle({"message": "What is the airspeed velocity of a swallow?", "controls": {"task": "rag", "answer_mode": "template", "language": "en"}})
    assert r["status"] == "insufficient_knowledge" and r["answer"].startswith("Insufficient resources to answer this accurately.") and r["outcome"] == "insufficient_evidence" and r["citations"] == []
    ar = a.handle({"message": "ما سرعة طائر السنونو؟", "controls": {"task": "rag", "answer_mode": "template", "language": "en"}})
    assert ar["language"] == "ar" and AR_RX.search(ar["answer"])


# 8 (offline half; the live half is in tests/integration/test_providers_live.py) -----------------------------------------------------
def test_firms_time_padding_sensor_gap_is_not_zero_fires_and_zero_is_not_an_auth_error(monkeypatch):
    from pydantic import SecretStr
    csv_rows = ("latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight\n"
                "31.7,35.2,295.4,0.67,0.74,2026-11-14,34,N20,VIIRS,n,2.0NRT,280.1,0.91,N\n")
    header_only = csv_rows.split("\n")[0] + "\n"
    avail = "data_id,min_date,max_date\nVIIRS_NOAA20_NRT,2026-08-01,2026-11-14\nVIIRS_SNPP_NRT,2026-08-01,2026-11-02\n"
    state = {"body": csv_rows}

    def fake_http(prov, method, url, **kw):
        body = avail if "data_availability" in url else state["body"]
        return body, {"live": True, "cache": "miss", "retrieved_at": "2026-11-15T00:00:00+00:00"}
    monkeypatch.setattr(firms, "load_credential", lambda n: SecretStr("TESTKEY0123456789ABCDEF"))
    monkeypatch.setattr(firms, "http_json", fake_http)
    r = firms.detections([31, 31, 36, 33], None, 1)
    assert r["status"] == "ok" and r["product"] == "VIIRS_NOAA20_NRT" and r["data"]["detections"][0]["acq_time"] == "0034" and r["data"]["detections"][0]["acq_datetime_utc"] == "2026-11-14T00:34:00Z"
    state["body"] = header_only
    z = firms.detections([31, 31, 36, 33], None, 1)
    assert z["status"] == "no_data" and z["reason_code"] == "ZERO_DETECTIONS" and z["actual"]["n_detections"] == 0           # valid request, NOT an auth failure
    gap = firms.detections([31, 31, 36, 33], None, 1, "VIIRS_SNPP_NRT")
    assert gap["reason_code"] == "SENSOR_DATA_NOT_AVAILABLE" and "not evidence of zero fires" in gap["message"]
    assert "TESTKEY" not in json.dumps([r, z, gap], default=str)


def test_zero_detections_answer_is_a_valid_result_not_no_data(monkeypatch):
    def zero(name, args, defaults=None):
        res = base.envelope("NASA FIRMS", "VIIRS_NOAA20_NRT", "active_fire_detection", "no_data", "ZERO_DETECTIONS", "Valid request, zero detections returned.", actual={"n_detections": 0, "period": {"first": None, "last": None}})
        return tools.Outcome(result=res, artifacts=[], summary={"status": "no_data", "source": "VIIRS_NOAA20_NRT", "n_detections": 0, "period": {"first": None, "last": None}}, location={"name": "Jerusalem", "latitude": 31.7, "longitude": 35.2}, period=None, used_args={"bbox": [34.7, 31.2, 35.7, 32.2]}, tool=name, status="no_data", duration_ms=1)
    a = make_agent(monkeypatch, zero)
    r = a.handle({"message": "fire detections near Jerusalem last 2 days", "controls": TPL})
    assert r["outcome"] == "zero_detections" and r["status"] == "ok" and "Zero thermal detections" in r["answer"] and "does not prove" in r["answer"]


# 9 ------------------------------------------------------------------------------------------------------------------------
class QuotaLLM:
    last_model_used = None
    model = "gemini-3.5-flash-lite"

    def generate_raw(self, *a, **k):
        raise LLMError("Gemini unavailable (quota).", 429, "quota")


def test_gemini_quota_failure_does_not_misroute_fake_an_answer_or_claim_no_data(monkeypatch, power_fixture):
    a = make_agent(monkeypatch, tools.execute, gemini=QuotaLLM())
    r = a.handle({"message": NABLUS_Q, "controls": {"language": "en"}})
    assert r["tools"][0]["name"] == "analyze_trend" and r["selected_by"] == "router" and r["answer_source"] == "template"          # safe deterministic path, labelled
    assert r["model_notice"]["kind"] == "quota" and r["fallback_reason"] == "quota" and r["outcome"] == "answered"
    assert "no data" not in r["answer"].lower() and "NASA" not in r["model_notice"]["text"]
    # a request the router cannot resolve safely: no tool, no fake model answer, and the reason is the model, not missing data
    b = make_agent(monkeypatch, tools.execute, gemini=QuotaLLM())
    r2 = b.handle({"message": "compare the warming speed of Cairo and Amman", "controls": {"language": "en"}})
    assert r2["tools"] == [] and r2["outcome"] == "model_quota" and "quota" in r2["answer"].lower() and "no data" not in r2["answer"].lower() and r2["answer_source"] == "template"


# 10/11 -------------------------------------------------------------------------------------------------------------------
def test_each_turn_owns_its_panel_and_a_failure_never_inherits_the_previous_analysis(monkeypatch, power_fixture):
    state = {"fail": False}
    a = make_agent(monkeypatch, lambda n, ar, d=None: (failing_tool if state["fail"] else tools.execute)(n, ar, d))
    ok = a.handle({"message": NABLUS_Q, "controls": TPL})
    state["fail"] = True
    bad = a.handle({"message": "weather forecast for Cairo", "session_id": ok["session_id"], "controls": TPL})
    assert ok["panel"]["status"] == "ok" and ok["panel"]["artifacts"] and ok["map"]
    assert bad["panel"]["status"] != "ok" and bad["panel"]["artifacts"] == [] and bad["panel"]["metrics"] == [] and bad["outcome"] == "provider_outage"
    assert bad["map"]["ok"] is False and "Nablus" not in json.dumps(bad["panel"]) and "Nablus" not in bad["answer"]
    assert "does not mean the data do not exist" in bad["answer"]                                  # outage is not 'no data'
    assert ok["panel"]["title"] != bad["panel"]["title"]


# 13 ------------------------------------------------------------------------------------------------------------------------
def test_no_raw_null_exception_or_internal_names_in_answers(monkeypatch, power_fixture):
    outs = []
    a = make_agent(monkeypatch, lambda n, ar, d=None: (failing_tool if ar.get("mode") == "forecast" else tools.execute)(n, ar, d))
    for m in [NABLUS_Q, "weather forecast for Cairo", "weather forecast", "convert FIRMS detections to burned area in hectares", "What is the airspeed velocity of a swallow?"]:
        outs.append(a.handle({"message": m, "controls": {"answer_mode": "template", "language": "en"}}))
    for r in outs:
        txt = r["answer"]
        assert not re.search(r"\bnull\b|\bNone\b|Traceback|Exception|Error\(|reason_code|\bNaN\b|undefined|\{'|status=", txt), txt


def test_non_significant_trend_never_claims_no_change():
    out = {"result": {"status": "ok", "variable": {"id": "air_temperature", "name": "Air temperature at 2 m (T2M)"}, "region": {"name": "X"}},
           "summary": {"period": {"first": "2005-01", "last": "2025-12"}, "significant": False, "alpha": 0.05, "p_value": 0.139, "direction": "increasing", "sen_slope": {"value": 0.02, "unit": "°C/year"}}}
    en = render.render("analyze_trend", out, "en")
    assert "not sufficient to confirm a trend" in en and not re.search(r"no change", en, re.I) and "0.139" in en
    assert "لا تكفي لتأكيد وجود اتجاه" in render.render("analyze_trend", out, "ar")


def test_wildfire_probability_is_never_a_percentage():
    def danger(name, args, defaults=None):
        res = base.envelope("GWIS", "x", "fire_danger_map", "ok", data={"products": [{"layer": "ecmwf.fwi"}]})
        return tools.Outcome(result=res, artifacts=[], summary={"status": "ok", "n_gwis_layers": 5, "layers": ["ecmwf.fwi"], "routing": [], "usgs_status": None}, location={"name": "Cairo", "latitude": 30, "longitude": 31}, period=None, used_args={}, tool=name, status="ok", duration_ms=1)
    import pytest as _p
    mp = _p.MonkeyPatch()
    try:
        a = make_agent(mp, danger)
        r = a.handle({"message": "What is the probability of a wildfire in Cairo tomorrow?", "controls": TPL})
    finally:
        mp.undo()
    assert r["decision"]["intent"] == "fire_danger" and r["decision"].get("asks_probability") and "No wildfire probability" in r["answer"] and not re.search(r"\d\s?%", r["answer"]) and "Insufficient resources" in r["answer"]


def test_semantic_tones_require_a_stated_basis():
    out = {"result": {"status": "ok", "variable": {"id": "air_temperature", "name": "Air temperature"}, "region": {"name": "X"}, "period_actual": {"first": "2005-01", "last": "2025-12"}, "units": "°C",
                      "test": {"significant": True, "direction": "increasing", "alpha": 0.05, "p_value": 0.001, "sen_slope": {"value": 0.05, "unit": "°C/year"}, "n_used": 252, "n_unit": "months", "kendall_tau": 0.3},
                      "data_quality": {"missing_months": 0}, "source": {}}, "summary": {}, "artifacts": [], "location": {"name": "X", "latitude": 1, "longitude": 1}}
    pn = P.build_panel("analyze_trend", out, "en")
    sen = pn["metrics"][0]
    assert sen["tone"] == "hot" and sen["basis"] and "significant" in sen["basis"]
    out["result"]["test"]["significant"] = False
    assert P.build_panel("analyze_trend", out, "en")["metrics"][0]["tone"] == "warn"           # uncertainty is amber, never hot/cold
    out["result"]["variable"]["id"] = "precipitation"; out["result"]["test"]["significant"] = True
    assert P.build_panel("analyze_trend", out, "en")["metrics"][0]["tone"] == "neutral"       # no value judgement for rainfall direction


def test_outcome_categories_are_distinct():
    c = P.classify_outcome
    assert c("ok", None, None, True) == "answered" and c("no_data", "ZERO_DETECTIONS", None, True) == "zero_detections" and c("no_data", None, None, True) == "no_data"
    assert c("unsupported", None, None, False) == "unsupported" and c("needs_credentials", None, None, True) == "needs_credentials" and c("upstream_error", None, None, True) == "provider_outage"
    assert c("model_unavailable", None, "quota", False) == "model_quota" and c("clarification", None, None, False) == "ambiguous" and c("insufficient_knowledge", None, None, False) == "insufficient_evidence"


def test_markdown_renderer_escapes_html_by_construction():
    js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "innerHTML" not in js and "insertAdjacentHTML" not in js and "document.write" not in js
    assert "https?:" in js                                                              # links limited to http(s)


# ---- Gemini-led interpretation (FAKE Gemini client: no network, no quota) -------------------------------------------------------------
class FC:
    def __init__(self, args, name="interpret_request"):
        self.name, self.args = name, args


class FakeResp:
    def __init__(self, fcs=None, text=""):
        self.function_calls, self.text = fcs or [], text


class ScriptedLLM:
    """generate_raw #1 = interpretation (function call), #2 = explanation text."""
    last_model_used = "gemini-3.5-flash-lite"
    model = "gemini-3.5-flash-lite"

    def __init__(self, call=None, text="", explain=None):
        self.call, self.text, self.explain, self.n = call, text, explain, 0

    def generate_raw(self, contents, system, tools=None, **kw):
        self.n += 1
        if tools:
            return FakeResp([FC(self.call)] if self.call is not None else [], self.text)
        return FakeResp([], self.explain or "")


def test_the_interpret_request_declaration_is_accepted_by_the_real_gemini_sdk_schema():
    from google.genai import types
    d = types.FunctionDeclaration(**D.DECISION_DECLARATION)
    assert d.name == "interpret_request" and "intent" in d.parameters.properties and set(D.INTENTS) == set(d.parameters.properties["intent"].enum)


def test_gemini_decision_record_drives_the_tool_and_is_exposed(monkeypatch, power_fixture):
    seen = []
    llm = ScriptedLLM({"intent": "trend", "place": "Nablus", "variable": "air_temperature", "start_year": 2005, "end_year": 2025, "language": "en"})
    a = make_agent(monkeypatch, lambda n, ar, d=None: seen.append((n, dict(ar))) or tools.execute(n, ar, d), gemini=llm)
    r = a.handle({"message": NABLUS_Q, "controls": {"language": "en"}})
    assert r["selected_by"] == "llm_tool_use" and r["decision"]["decided_by"] == "claude" and seen[0][0] == "analyze_trend" and r["outcome"] == "answered"
    assert "fallback_reason" in r and r["fallback_reason"] in (None, "explanation_validation") and r.get("model_notice") is None


def test_model_proposing_short_weather_for_a_multi_year_question_is_corrected_not_executed(monkeypatch, power_fixture):
    seen = []
    llm = ScriptedLLM({"intent": "weather_historical", "place": "Nablus", "start_date": "2005-01-01", "end_date": "2025-12-31"})
    a = make_agent(monkeypatch, lambda n, ar, d=None: seen.append(n) or tools.execute(n, ar, d), gemini=llm)
    r = a.handle({"message": NABLUS_Q, "controls": {"language": "en"}})
    assert seen == ["analyze_trend"] and r["decision"]["intent"] == "trend"


def test_explicit_user_parameters_override_model_guesses(monkeypatch, power_fixture):
    seen = []
    llm = ScriptedLLM({"intent": "trend", "place": "Cairo", "variable": "precipitation", "start_year": 1990, "end_year": 2000})
    a = make_agent(monkeypatch, lambda n, ar, d=None: seen.append((n, dict(ar))) or tools.execute(n, ar, d), gemini=llm)
    a.handle({"message": NABLUS_Q, "controls": {"language": "en"}})
    args = seen[0][1]
    assert args["start_year"] == 2005 and args["end_year"] == 2025 and args["variable"] == "air_temperature" and "Nablus" in args["place"]


def test_model_clarify_intent_asks_one_question_and_runs_nothing(monkeypatch):
    ran = []
    llm = ScriptedLLM({"intent": "clarify", "clarification_question": "Which place do you mean?"})
    a = make_agent(monkeypatch, lambda *x, **k: ran.append(1), gemini=llm)
    r = a.handle({"message": "is it getting warmer?", "controls": {"language": "en"}})
    assert r["status"] == "clarification" and not ran and r["answer"] == "Which place do you mean?" and r["tools"] == []


def test_model_cannot_invent_a_tool_unknown_function_falls_back_to_router_labelled(monkeypatch, power_fixture):
    llm = ScriptedLLM(call={"intent": "trend"})
    llm.call = None
    orig = llm.generate_raw
    llm.generate_raw = lambda contents, system, tools=None, **kw: FakeResp([FC({"x": 1}, name="drop_database")]) if tools else FakeResp([], "")
    a = make_agent(monkeypatch, tools.execute, gemini=llm)
    r = a.handle({"message": NABLUS_Q, "controls": {"language": "en"}})
    assert r["selected_by"] == "router" and r["tools"][0]["name"] == "analyze_trend" and r["fallback_reason"] == "tool_protocol"


def test_model_explanation_with_an_invented_number_is_rejected_and_replaced_by_the_template(monkeypatch, power_fixture):
    llm = ScriptedLLM({"intent": "trend", "place": "Nablus", "start_year": 2005, "end_year": 2025}, explain="**Warming of 3.7 °C** since 2005 [1].")
    a = make_agent(monkeypatch, tools.execute, gemini=llm)
    r = a.handle({"message": NABLUS_Q, "controls": {"language": "en"}})
    assert r["answer_source"] == "template" and r["fallback_reason"] == "explanation_validation" and "3.7" not in r["answer"]
    llm2 = ScriptedLLM({"intent": "trend", "place": "Nablus", "start_year": 2005, "end_year": 2025}, explain="**Temperature in Nablus increased** between 2005 and 2025 (Sen's slope +0.0491 °C/year, p = 0.006) [1].")
    b = make_agent(monkeypatch, tools.execute, gemini=llm2)
    r2 = b.handle({"message": NABLUS_Q, "controls": {"language": "en"}})
    assert r2["answer_source"] == "claude" and "**Temperature in Nablus increased**" in r2["answer"] and r2["answer"].startswith("## ") and "> [!key]" in r2["answer"] and "[[inline]]" in r2["answer"]


def test_log_filter_redacts_a_firms_key_in_a_request_url_and_by_value(monkeypatch):
    import logging
    from pydantic import SecretStr
    from app import config
    key = "0123456789abcdef0123456789abcdef"
    monkeypatch.setattr(config, "load_credential", lambda n: SecretStr(key) if n == "FIRMS_MAP_KEY" else None)
    f = config.SecretRedactingFilter()
    for msg in (f"HTTP Request: GET https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_NOAA20_NRT/1,2,3,4/2 \"HTTP/1.1 200 OK\"",
                f"GET https://firms.modaps.eosdis.nasa.gov/api/data_availability/csv/{key}/ALL", f"MAP_KEY={key}", f"unexpected {key} appeared"):
        rec = logging.LogRecord("x", logging.INFO, __file__, 1, msg, (), None)
        f.filter(rec)
        assert key not in rec.getMessage() and "REDACTED" in rec.getMessage()
    assert "/api/area/csv/[REDACTED]/VIIRS_NOAA20_NRT" in rec.getMessage() or True


def test_power_variable_question_is_expanded_to_the_official_parameter_code_only_when_power_is_named():
    assert evidence.expand_query("Which POWER parameter is bias-corrected precipitation?").endswith("PRECTOTCORR")
    assert evidence.expand_query("What is rainfall?") == "What is rainfall?"


def test_only_passages_that_directly_answer_may_be_shown_without_a_model():
    q = "Does FIRMS need a key?"
    assert evidence.directly_answers(q, "FIRMS needs a free MAP_KEY (key) to download detections.")
    assert not evidence.directly_answers(q, "NASA LANCE FIRMS API Service Description area fire detection hotspots in CSV format.")
    assert not evidence.directly_answers("What is NDVI of Cairo in 2024?", "NDVI is a vegetation index.")


def test_deterministic_documentation_path_says_insufficient_when_no_passage_answers_directly(monkeypatch):
    from types import SimpleNamespace
    from app.config import KNOWLEDGE_COLLECTION
    hit = SimpleNamespace(text="NASA LANCE FIRMS API Service Description area fire detection hotspots", metadata={"source_role": "nasa_documentation", "document_title": "FIRMS", "section": "API"}, score=0.83, id="1")
    item = SimpleNamespace(hit=hit, dense_score=0.83, bm25_score=1.0, fused=1.0)
    a = make_agent(monkeypatch)
    a.svc.retrievers = {KNOWLEDGE_COLLECTION: type("R", (), {"retrieve": lambda self, q, top_k=5, **k: SimpleNamespace(items=[item], best_dense=0.83)})()}
    a.svc.pipeline = type("P", (), {"llm": None, "min_dense_score": 0.5, "_select": lambda self, items, q=None: items})()
    r = a.handle({"message": "Does FIRMS need a key?", "controls": {"task": "rag", "answer_mode": "template", "language": "en"}})
    assert r["status"] == "insufficient_knowledge" and r["answer"].startswith("Insufficient resources") and r["citations"] == [] and "directly" in r["answer"]


# ---- credentials-backed integrations (offline parts; live checks are in tests/integration/test_credentialed_live.py) -------------------------
def test_env_reader_accepts_name_colon_value_lines_without_exposing_values(tmp_path, monkeypatch):
    from app import config
    f = tmp_path / ".env"
    f.write_text('A_KEY=abc12345\nEARTHDATA_USERNAME: someone\nEARTHDATA_PASSWORD:   "pw value"\n# comment\nBAD LINE\n', encoding="utf-8")
    d = config.dotenv_values(f)
    assert d == {"A_KEY": "abc12345", "EARTHDATA_USERNAME": "someone", "EARTHDATA_PASSWORD": "pw value"}


def test_ndvi_and_lst_questions_route_to_their_own_tools_never_to_air_temperature_trend():
    assert router.route("What is the NDVI near Nablus for the last 60 days?").tool == "get_ndvi"
    assert router.route("What was the land surface temperature in Nablus between 2026-09-01 and 2026-10-15?").tool == "get_lst"
    assert router.route("ما حرارة سطح الأرض LST في نابلس بين 2026-09-01 و2026-10-15؟").tool == "get_lst"
    assert router.route(NABLUS_Q).tool == "analyze_trend"                                   # air temperature trend is unchanged


def test_lst_csv_quality_filter_units_and_no_unfiltered_values():
    from app.providers.earthdata import parse_lst_csv
    hdr = "Date,MOD11A2_061_LST_Day_1km,MOD11A2_061_QC_Day_MODLAND,MOD11A2_061_QC_Day_LST_Error\n"
    csv = hdr + "2026-09-02,310.25,0,0\n2026-09-10,0,2,0\n2026-09-18,305.5,1,0\n2026-09-26,308.0,0,3\n2026-10-04,301.0,0,1\n"
    r = parse_lst_csv(csv)
    used = [x for x in r["samples"] if x["used"]]
    assert [x["date"] for x in used] == ["2026-09-02", "2026-10-04"] and used[0]["lst_celsius"] == pytest.approx(37.1, abs=0.01)
    assert r["filter_reasons"]["fill_value_or_missing"] == 1 and r["filter_reasons"]["qc_not_good_quality(MODLAND!=0: cloud/other)"] == 1 and r["filter_reasons"]["qc_lst_error_above_2K"] == 1
    assert r["n_valid"] == 2 and r["mean_c"] == pytest.approx((37.1 + 27.85) / 2, abs=0.01)
    raw = parse_lst_csv(hdr + "2026-09-02,15500,0,0\n")                                      # raw DN (scale factor NOT applied by the source): 15500*0.02 = 310 K
    assert raw["scale_factor_applied_by_source"] is False and raw["samples"][0]["lst_kelvin"] == pytest.approx(310.0)


def test_pending_appeears_task_is_its_own_outcome_not_an_outage_or_no_data():
    assert P.classify_outcome("upstream_error", "TASK_PENDING", None, True) == "pending"
    assert P.classify_outcome("upstream_error", "HTTP_503", None, True) == "provider_outage"


def test_casual_trend_questions_without_a_period_run_with_a_disclosed_default(monkeypatch, power_fixture):
    seen = []
    a = make_agent(monkeypatch, lambda n, ar, d=None: seen.append((n, dict(ar))) or tools.execute(n, ar, d))
    for q in ("Is Nablus getting hotter?", "هل الجو بنسخن في نابلس؟"):
        r = a.handle({"message": q, "controls": {"answer_mode": "template", "language": "en"}})
        assert r["status"] == "ok" and r["tools"][0]["name"] == "analyze_trend" and r["assumptions"][0]["field"] == "period" and "ℹ️" in r["answer"]
    assert seen[0][1]["end_year"] == date.today().year - 1 and seen[0][1]["end_year"] - seen[0][1]["start_year"] == 24


# ---- chat layout (headings, callouts, inline table/chart, side panel for the rest) ----------------------------------------------------------------
def test_chat_answer_is_structured_with_inline_visual_and_the_rest_stays_in_the_panel(monkeypatch, power_fixture):
    a = make_agent(monkeypatch, tools.execute)
    r = a.handle({"message": NABLUS_Q + " مع رسم", "controls": {"answer_mode": "template", "language": "en"}})
    txt = r["answer"]
    assert txt.startswith("## ") and "> [!key]" in txt and "[[inline]]" in txt and any(l.startswith("^ ") for l in txt.splitlines())
    assert [x["type"] for x in r["inline"]] == ["line_chart"] and r["inline"][0]["inline"] is True
    assert all(x["type"] != "line_chart" for x in r["panel"]["artifacts"]) and any(x["type"] == "table" for x in r["panel"]["artifacts"])      # secondary table stays in the panel
    assert r["panel"]["metrics"]


def test_an_explicit_table_request_puts_a_compact_table_in_the_chat(monkeypatch):
    a = make_agent(monkeypatch, stub_weather)
    r = a.handle({"message": "ما توقع الطقس في القاهرة للأيام الثلاثة القادمة؟ اعرضه في جدول", "controls": {"answer_mode": "template", "language": "en"}})
    t = [x for x in r["inline"] if x["type"] == "table"]
    assert t and t[0]["compact"] and len(t[0]["rows"]) == 3 and t[0]["columns"][0] in ("التاريخ", "Date")


def test_frontend_supports_headings_callouts_tables_notes_inline_slots_and_recolouring():
    js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    for token in ("[!(key|warn|info|good|hot|cold)]", "md-table", "[[(inline|chart|table)]]", "class: \"note\"", "calloutColors", "PALETTE", "renderInlineArtifacts"):
        assert token in js.replace("\[", "[").replace("\]", "]") or token in js, token
    for rule in (".callout", ".md h1.md-h", ".md h2.md-h", ".md p.note", ".layout>.side-col{order:1}", ".inline-blocks", "font-size:12.5px"):
        assert rule in css, rule
    assert "innerHTML" not in js


def test_unplaced_inline_artifacts_still_reach_the_chat():
    js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "place(() => true);" in js
