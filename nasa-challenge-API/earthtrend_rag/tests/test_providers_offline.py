"""Provider adapters + chat layer, OFFLINE. All HTTP is replaced with saved/handwritten payloads and every such payload is labelled MOCK.

The FIRMS CSV below is MOCK data shaped like the official documented columns (no FIRMS key was available to capture a real response).
Real-network behaviour of the other providers is verified separately (see tests/integration/test_providers_live.py and evidence/).
"""
import json
from datetime import date, timedelta

import pytest

from app.chat import render, router, tools
from app.chat.agent import ChatAgent
from app.chat.sessions import SessionStore
from app.providers import base, copernicus, earthdata, fire_danger, firms, gee, open_meteo, registry
from app.providers.base import ProviderError

MOCK_FIRMS_CSV = ("latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight\n"
                  "32.10,35.20,330.5,0.4,0.4,2026-11-13,1034,N,VIIRS,n,2.0NRT,290.1,4.2,D\n"
                  "32.11,35.21,341.0,0.4,0.4,2026-11-13,1034,N,VIIRS,h,2.0NRT,291.3,11.8,D\n"
                  "32.50,35.00,310.0,0.4,0.4,2026-11-14,0012,N,VIIRS,l,2.0NRT,285.0,1.1,N\n")


@pytest.fixture(autouse=True)
def _tmp_cache(tmp_path, monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "data_dir", tmp_path)


def fake_http(routes: dict):
    """Replace base.http_json: routes maps a URL substring to a payload (or an exception)."""
    def _f(provider, method, url, **kw):
        for k, v in routes.items():
            if k in url:
                if isinstance(v, Exception):
                    raise v
                return v, {"live": True, "cache": "miss", "retrieved_at": base.now_iso(), "seconds": 0.01, "http_status": 200, "attempts": []}
        raise AssertionError(f"unexpected URL {url}")
    return _f


# ---- FIRMS ------------------------------------------------------------------------------------------------------------------
def test_firms_without_key_disables_only_itself_and_explains(monkeypatch):
    monkeypatch.setattr(firms, "load_credential", lambda n: None)
    r = firms.detections([34.9, 31.7, 35.4, 32.2], None, 1)
    assert r["status"] == "needs_credentials" and r["reason_code"] == "FIRMS_MAP_KEY_MISSING" and r["setup"]["env"] == "FIRMS_MAP_KEY"
    assert "register" in r["setup"] and r["data"] is None


def test_firms_parsing_summary_and_the_detection_caveat(monkeypatch):
    from pydantic import SecretStr
    monkeypatch.setattr(firms, "load_credential", lambda n: SecretStr("TESTKEY0123456789"))
    monkeypatch.setattr(firms, "http_json", fake_http({"/api/area/csv/": MOCK_FIRMS_CSV}))
    r = firms.detections([34.9, 31.7, 35.6, 32.7], "2026-11-13", 2, "VIIRS_SNPP_NRT")
    assert r["status"] == "ok" and r["actual"]["n_detections"] == 3 and r["quality"]["by_day"] == {"2026-11-13": 2, "2026-11-14": 1}
    assert r["quality"]["frp_max_mw"] == 11.8 and r["units"]["frp"] == "MW"
    assert any("not confirmed wildfire incidents" in x for x in r["limitations"])
    assert [a["type"] for a in r["artifacts"]] == ["map_points", "table", "line_chart"]
    assert "TESTKEY" not in json.dumps(r)                               # the key never reaches the result


@pytest.mark.parametrize("bbox,days,src,code", [([0, 0, 50, 50], 2, None, "INVALID_BBOX"), ([34, 31, 35, 32], 9, None, "INVALID_DAY_RANGE"), ([34, 31, 35, 32], 2, "NOPE", "UNKNOWN_SOURCE")])
def test_firms_validates_before_any_request(bbox, days, src, code, monkeypatch):
    monkeypatch.setattr(firms, "http_json", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no request expected")))
    assert firms.detections(bbox, None, days, src)["reason_code"] == code


def test_firms_invalid_key_message_is_sanitised(monkeypatch):
    from pydantic import SecretStr
    monkeypatch.setattr(firms, "load_credential", lambda n: SecretStr("SECRETKEY987654321"))
    monkeypatch.setattr(firms, "http_json", fake_http({"/api/area/csv/": ProviderError("HTTP 400: Invalid MAP_KEY.", "invalid_request", 400)}))
    r = firms.detections([34.9, 31.7, 35.4, 32.2], None, 1)
    assert r["status"] == "needs_credentials" and r["reason_code"] == "FIRMS_MAP_KEY_INVALID" and "SECRETKEY" not in json.dumps(r)


def test_sanitize_removes_map_keys_from_urls():
    s = base.sanitize("https://firms.modaps.eosdis.nasa.gov/api/area/csv/ABCDEF1234567890/VIIRS_SNPP_NRT/1,2,3,4/1 token=xyz123456789012345")
    assert "ABCDEF" not in s and "xyz1234" not in s


# ---- Open-Meteo --------------------------------------------------------------------------------------------------------------
FORECAST = {"latitude": 30.03, "longitude": 31.22, "elevation": 29.0, "timezone": "Africa/Cairo", "utc_offset_seconds": 7200,
            "hourly_units": {"temperature_2m": "°C", "relative_humidity_2m": "%", "precipitation": "mm", "wind_speed_10m": "km/h"},
            "hourly": {"time": ["2026-11-14T00:00", "2026-11-14T01:00"], "temperature_2m": [20.1, 19.5], "relative_humidity_2m": [60, 62], "precipitation": [0, 0], "wind_speed_10m": [5.0, 4.0]},
            "daily_units": {"temperature_2m_max": "°C", "temperature_2m_min": "°C", "precipitation_sum": "mm", "wind_speed_10m_max": "km/h"},
            "daily": {"time": ["2026-11-14"], "temperature_2m_max": [28.5], "temperature_2m_min": [14.9], "precipitation_sum": [0.0], "wind_speed_10m_max": [9.3]}}


def test_forecast_keeps_timezone_units_grid_and_marks_issue_time_unavailable(monkeypatch):
    monkeypatch.setattr(open_meteo, "http_json", fake_http({"api.open-meteo.com/v1/forecast": FORECAST}))
    r = open_meteo.forecast(30.04, 31.24, 1)
    a = r["actual"]
    assert r["status"] == "ok" and a["timezone"] == "Africa/Cairo" and a["issue_time"] is None and a["grid"]["latitude"] == 30.03
    assert r["units"]["temperature_2m_max"] == "°C" and r["capability"] == "weather_forecast"
    assert any("issue time" in x for x in r["limitations"]) and "CC BY 4.0" in r["attribution"]


@pytest.mark.parametrize("args", [(95, 0, 3), (30, 31, 0), (30, 31, 99)])
def test_forecast_validation(args, monkeypatch):
    monkeypatch.setattr(open_meteo, "http_json", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no request")))
    assert open_meteo.forecast(*args)["status"] == "invalid_request"


def test_historical_is_labelled_reanalysis_and_limits_are_enforced(monkeypatch):
    monkeypatch.setattr(open_meteo, "http_json", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no request")))
    assert open_meteo.historical(30, 31, "2024-01-01", "2026-01-01")["reason_code"] == "RANGE_TOO_LONG"
    assert open_meteo.historical(30, 31, "1900-01-01", "1900-01-05")["reason_code"] == "BEFORE_COVERAGE"
    recent = (date.today() - timedelta(days=1)).isoformat()
    assert open_meteo.historical(30, 31, recent, recent)["reason_code"] == "TOO_RECENT"
    ok = {**FORECAST, "daily": {"time": ["2024-06-01"], "temperature_2m_max": [40.5], "temperature_2m_min": [25.0], "precipitation_sum": [0.0], "wind_speed_10m_max": [12.0]}}
    monkeypatch.setattr(open_meteo, "http_json", fake_http({"archive-api": ok}))
    r = open_meteo.historical(30.04, 31.24, "2024-06-01", "2024-06-01")
    assert r["capability"] == "historical_weather" and "reanalysis" in r["actual"]["source_type"] and any("not a measurement" in x or "station" in x for x in r["limitations"])


def test_provider_failure_is_structured_not_an_exception(monkeypatch):
    monkeypatch.setattr(open_meteo, "http_json", fake_http({"api.open-meteo.com": ProviderError("provider unavailable (timeout)", "timeout")}))
    r = open_meteo.forecast(30, 31, 2)
    assert r["status"] == "upstream_error" and r["reason_code"] == "TIMEOUT" and r["data"] is None


# ---- fire danger -------------------------------------------------------------------------------------------------------------
def test_usgs_outside_conus_is_unsupported_and_makes_no_request(monkeypatch):
    monkeypatch.setattr(fire_danger, "http_json", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no request")))
    r = fire_danger.usgs_point(30.04, 31.24)
    assert r["status"] == "unsupported_region" and r["reason_code"] == "OUTSIDE_CONUS" and "GWIS" in r["message"]


def test_usgs_point_reports_palette_index_not_a_probability(monkeypatch):
    caps = '<Dimension name="time" default="2026-11-14T00:00:00.000Z">2026-11-14T00:00:00.000Z</Dimension>'
    monkeypatch.setattr(fire_danger, "http_json", lambda p, m, url, **kw: (({"features": [{"properties": {"PALETTE_INDEX": 251}}]} if kw.get("parse") != "text" else caps),
                                                                          {"live": True, "cache": "miss", "retrieved_at": base.now_iso()}))
    r = fire_danger.usgs_point(43.6, -116.2)
    assert r["status"] == "ok" and r["data"]["palette_index"] == 251 and r["actual"]["valid_time"].startswith("2026-11-14")
    assert "not a calibrated" in r["units"]["palette_index"] and any("not a calibrated probability" in x for x in r["limitations"])


def test_gwis_products_preserve_definition_time_and_coverage(monkeypatch):
    xml = ("<Layer queryable='1'><Name>ecmwf.fwi</Name><Abstract>Fire Weather Index (FWI) from ECMWF reanalysis data.</Abstract>"
           "<Dimension name=\"time\" units=\"ISO8601\" default=\"2026-11-22\" nearestValue=\"0\">2018-01-01/2099-12-31</Dimension></Layer>"
           "<Layer><Name>other.layer</Name></Layer>")
    monkeypatch.setattr(fire_danger, "http_json", lambda *a, **k: (xml, {"live": True, "cache": "miss", "retrieved_at": base.now_iso()}))
    r = fire_danger.gwis_products("fwi")
    p = r["data"]["products"][0]
    assert r["status"] == "ok" and len(r["data"]["products"]) == 1 and p["layer"] == "ecmwf.fwi" and "Fire Weather Index" in p["definition"]
    assert p["valid_time_range"] == "2018-01-01/2099-12-31" and p["default_valid_time"] == "2026-11-22" and p["issue_time"] is None and "global" in p["coverage"]
    assert any("not a calibrated probability" in x for x in r["limitations"]) and any("only the grid-cell location" in x for x in r["limitations"])


def test_fire_danger_routing_explains_the_region_decision(monkeypatch):
    monkeypatch.setattr(fire_danger, "gwis_products", lambda kw=None: base.envelope("GWIS", "x", "fire_danger", "ok", data={"products": []}))
    out = fire_danger.danger_for_location(30.0, 31.0)
    assert out["usgs"] is None and "outside the contiguous US" in out["routing"][0]


# ---- Copernicus / Earthdata / GEE ---------------------------------------------------------------------------------------------
STAC = {"features": [{"id": "S2A_TEST", "collection": "sentinel-2-l2a", "bbox": [31, 29, 32, 30], "geometry": {"type": "Polygon", "coordinates": [[[31, 29], [32, 29], [32, 30], [31, 30], [31, 29]]]},
                      "properties": {"datetime": "2024-06-29T08:36:01Z", "eo:cloud_cover": 1.12, "platform": "sentinel-2a"},
                      "assets": {"thumbnail": {"href": "https://datahub.creodias.eu/odata/v1/Assets(x)/$value"}, "B04_10m": {"href": "s3://eodata/x"}}, "links": [{"rel": "self", "href": "https://s"}]}], "numberReturned": 1}


def test_scene_search_is_discovery_only_with_preview_proxy_and_cloud_metadata(monkeypatch):
    monkeypatch.setattr(copernicus, "http_json", fake_http({"/search": STAC}))
    r = copernicus.search_scenes([31.0, 29.9, 31.4, 30.2], "2024-06-01", "2024-06-30")
    s = r["data"]["scenes"][0]
    assert r["status"] == "ok" and s["cloud_cover_percent"] == 1.12 and s["preview"].startswith("/api/preview?u=") and "CDSE credentials" in s["asset_access"]
    assert any("DISCOVERY ONLY" in x for x in r["limitations"]) and r["capability"] == "satellite_discovery"


@pytest.mark.parametrize("kw,code", [(dict(bbox=[0, 0, 40, 40], start="2024-01-01", end="2024-02-01"), "INVALID_BBOX"), (dict(bbox=[31, 29, 32, 30], start="2024-03-01", end="2024-01-01"), "INVALID_DATE_RANGE"),
                                    (dict(bbox=[31, 29, 32, 30], start="2020-01-01", end="2024-01-01"), "RANGE_TOO_LONG"), (dict(bbox=[31, 29, 32, 30], start="2024-01-01", end="2024-02-01", max_cloud=300), "INVALID_CLOUD")])
def test_scene_search_validation(kw, code, monkeypatch):
    monkeypatch.setattr(copernicus, "http_json", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no request")))
    assert copernicus.search_scenes(**kw)["reason_code"] == code


def test_ndvi_processing_needs_credentials_and_documents_the_masking(monkeypatch):
    monkeypatch.setattr(copernicus, "load_credential", lambda n: None)
    r = copernicus.ndvi_statistics([31, 29, 31.1, 29.1], "2024-06-01", "2024-06-30")
    assert r["status"] == "needs_credentials" and r["capability"] == "satellite_processing" and "CDSE_CLIENT_ID" in r["setup"]["env"]
    assert "SCL" in copernicus.NDVI_EVALSCRIPT and "B08" in copernicus.NDVI_EVALSCRIPT and "dataMask" in copernicus.NDVI_EVALSCRIPT


def test_gibs_overlay_is_visualisation_only():
    r = earthdata.gibs_overlay("MODIS_Terra_CorrectedReflectance_TrueColor", "2024-06-15")
    assert r["status"] == "ok" and r["artifacts"][0]["analytical"] is False and "{z}/{y}/{x}" in r["artifacts"][0]["url"] and any("does NOT mean numerical data" in x for x in r["limitations"])
    assert earthdata.gibs_overlay("Not_A_Layer", "2024-06-15")["reason_code"] == "UNKNOWN_LAYER"
    assert earthdata.gibs_overlay("MODIS_Terra_CorrectedReflectance_TrueColor", "2999-01-01")["reason_code"] == "INVALID_DATE"


def test_earthdata_download_and_appeears_need_credentials_and_check_host(monkeypatch):
    monkeypatch.setattr(earthdata, "load_credential", lambda n: None)
    assert earthdata.download_granule("https://data.lpdaac.earthdatacloud.nasa.gov/x.hdf")["reason_code"] == "EARTHDATA_TOKEN_MISSING"
    r = earthdata.appeears_point_lst(31.8, 35.2, "2024-01-01", "2024-03-01")
    assert r["status"] == "needs_credentials" and "not substituted" in r["message"]
    from pydantic import SecretStr
    monkeypatch.setattr(earthdata, "load_credential", lambda n: SecretStr("tok"))
    assert earthdata.download_granule("https://evil.example.com/x.hdf")["reason_code"] == "HOST_NOT_ALLOWED"


def test_gee_is_optional_and_never_assumes_access(monkeypatch):
    monkeypatch.setattr(gee, "load_credential", lambda n: None)
    r = gee.region_mean("MODIS/061/MOD11A1", "LST_Day_1km", [34, 31, 35, 32], "2024-01-01", "2024-01-10")
    assert r["status"] == "needs_credentials" and r["reason_code"] == "EARTH_ENGINE_NOT_CONFIGURED" and "billing" in json.dumps(r["limitations"]).lower()


def test_registry_status_never_contains_secret_values(monkeypatch):
    monkeypatch.setenv("FIRMS_MAP_KEY", "SUPERSECRETVALUE123456")
    st = registry.status()
    assert "SUPERSECRETVALUE" not in json.dumps(st)
    f = next(p for p in st if p["id"] == "firms")
    assert f["credentials_present"] == {"FIRMS_MAP_KEY": True} and f["configuration"] == "ready"
    assert {p["id"] for p in st} == {"power", "open_meteo", "firms", "gwis", "usgs_fire", "copernicus", "earthdata", "gee", "ewds", "nifc"}


# ---- router / sessions / chat agent -------------------------------------------------------------------------------------------
@pytest.mark.parametrize("q,tool", [
    ("ما توقع الطقس في القاهرة للأيام الثلاثة القادمة؟", "get_weather"), ("weather forecast for Cairo tomorrow", "get_weather"),
    ("show fire detections in California for the last 2 days", "get_fire_detections"), ("ما منتجات خطر الحرائق المتاحة؟", "list_fire_danger"),
    ("find Sentinel-2 scenes near Cairo", "search_satellite_scenes"), ("search datasets for MOD11C3 land surface temperature", "search_earth_datasets"),
    ("هل ارتفعت حرارة الهواء في نابلس بين 2005 و2025؟", "analyze_trend"), ("هل يحتاج FIRMS إلى مفتاح؟", None)])
def test_router_selects_the_right_tool(q, tool):
    assert router.route(q).tool == tool


def test_fire_probability_question_routes_to_the_danger_index_never_to_a_percentage():
    p = router.route("What is the probability of a wildfire in Texas tomorrow?")
    assert p.tool == "list_fire_danger" and "asks_probability" in p.flags and p.unsupported is None


@pytest.mark.parametrize("q,key", [("حوّل بؤر FIRMS إلى مساحة محروقة", "burned_area"), ("توقع حرارة الرياض في 2040", "forecast_too_long")])
def test_unsupported_requests_are_refused_honestly(q, key):
    assert router.route(q).unsupported == key
    assert "FWI" in router.UNSUPPORTED["fire_probability"]["en"] or key != "fire_probability"


def test_period_parsing_relative_and_explicit():
    today = date(2026, 11, 14)
    assert router.parse_period("last 3 days", today)["start"] == "2026-11-11"
    assert router.parse_period("بين 2005 و2025", today)["kind"] == "years"
    assert router.parse_period("2026-11-01 to 2026-11-05", today)["end"] == "2026-11-05"
    assert router.parse_period("tomorrow", today)["kind"] == "tomorrow"


def test_sessions_are_isolated_bounded_and_resettable():
    st = SessionStore(max_sessions=2)
    a, b = st.get(None), st.get(None)
    a.memory["location"] = {"name": "A"}; a.add("user", "hello")
    assert "location" not in b.memory and b.history == []
    for i in range(40):
        a.add("user", f"m{i}")
    from app.chat.sessions import MAX_TURNS
    assert len(a.history) <= 2 * MAX_TURNS
    st.get(None)
    assert len(st) == 2                                               # oldest evicted
    a.reset()
    assert a.history == [] and a.memory == {}


class FakeSvc:
    _llm = None
    pipeline = type("P", (), {"llm": None, "min_dense_score": 0.5})()
    retrievers = {}

    @property
    def llm(self):
        raise AssertionError("LLM must not be used in template mode")


def agent(monkeypatch, runner=None):
    monkeypatch.setattr("app.chat.agent.load_llm_key", lambda: None)
    return ChatAgent(FakeSvc(), SessionStore(), tool_runner=runner)


def stub_tool(name, args, defaults=None):
    res = base.envelope("Open-Meteo", "Forecast API", "weather_forecast", "ok", live=True, cache="miss", data={}, limitations=["x"],
                        actual={"grid": {"latitude": 1.0, "longitude": 2.0}, "timezone": "UTC", "period": {"first": "a", "last": "b"}, "issue_time": None})
    d = (defaults or {}).get("location")
    summ = {"status": "ok", "product": "Forecast API", "timezone": "UTC", "grid": {"latitude": 1.0, "longitude": 2.0}, "period": {"first": "a", "last": "b"}, "units": {},
            "daily": [{"date": "2026-11-14", "tmax_c": 20, "tmin_c": 10, "precip_mm": 0, "wind_max_kmh": 5}], "source_type": "operational forecast", "issue_time": None, "cache": "miss"}
    return tools.Outcome(result=res, artifacts=[{"type": "table", "columns": ["a"], "rows": [[1]]}], summary=summ, location=d or args.get("loc"),
                         period={"start": "2026-11-14"}, used_args=args, tool=name, status="ok", duration_ms=3)


def test_followup_keeps_tool_but_replaces_place_and_resets_with_new_conversation(monkeypatch):
    calls = []
    def runner(name, args, defaults=None):
        calls.append((name, (defaults or {}).get("location", {}).get("name")))
        return stub_tool(name, args, defaults)
    a = agent(monkeypatch, runner)
    r1 = a.handle({"message": "ما توقع الطقس في القاهرة؟", "controls": {"answer_mode": "template"}})
    sid = r1["session_id"]
    r2 = a.handle({"message": "وماذا عن الإسكندرية؟", "session_id": sid, "controls": {"answer_mode": "template"}})
    assert calls[0][0] == "get_weather" and calls[1][0] == "get_weather" and "Cairo" in calls[0][1] and "Alexandria" in calls[1][1]   # new place, not the stale one
    assert r2["selected_by"] == "follow_up"
    assert a.reset(sid) and a.history(sid) == []
    r3 = a.handle({"message": "وماذا عن الإسكندرية؟", "session_id": sid, "controls": {"answer_mode": "template"}})
    assert r3["tools"] == []                                           # after reset the follow-up has no previous tool to reuse


def test_message_and_map_controls_conflict_is_visible_and_resolvable(monkeypatch):
    ran = []
    a = agent(monkeypatch, lambda n, ar, d=None: ran.append((n, d["location"]["name"])) or stub_tool(n, ar, d))
    ctl = {"answer_mode": "template", "point": {"lat": 40.7128, "lon": -74.006}}
    r = a.handle({"message": "weather forecast for Cairo", "controls": ctl})
    assert r["status"] == "conflict" and not ran and r["conflict"]["items"][0]["field"] == "location" and r["conflict"]["choices"] == ["message", "controls"]
    r2 = a.handle({"message": "weather forecast for Cairo", "session_id": r["session_id"], "controls": ctl, "conflict_choice": "message"})
    assert r2["status"] == "ok" and "Cairo" in ran[-1][1]
    r3 = a.handle({"message": "weather forecast for Cairo", "session_id": r["session_id"], "controls": ctl, "conflict_choice": "controls"})
    assert "map point" in ran[-1][1]


def test_period_conflict_between_message_and_controls(monkeypatch):
    a = agent(monkeypatch, stub_tool)
    r = a.handle({"message": "هل ارتفعت حرارة الهواء في نابلس بين 2005 و2025؟", "controls": {"answer_mode": "template", "start": "2010-01-01", "end": "2020-12-31"}})
    assert r["status"] == "conflict" and any(i["field"] == "period" for i in r["conflict"]["items"])


def test_template_mode_never_touches_gemini_and_labels_the_answer(monkeypatch):
    a = agent(monkeypatch, stub_tool)
    r = a.handle({"message": "weather forecast for Cairo", "controls": {"answer_mode": "template"}})
    assert r["answer_source"] == "template" and r["fallback_reason"] == "template_requested" and r["model"] is None


def test_unsupported_and_missing_location_are_handled_without_tools(monkeypatch):
    ran = []
    a = agent(monkeypatch, lambda *x, **k: ran.append(1))
    r = a.handle({"message": "convert FIRMS detections to burned area in hectares", "controls": {"answer_mode": "template"}})
    assert r["status"] == "unsupported" and not ran and "burned area" in r["answer"]
    a2 = agent(monkeypatch)
    r2 = a2.handle({"message": "weather forecast", "controls": {"answer_mode": "template", "language": "en"}})
    assert r2["status"] == "clarification" and r2["tools"] == [] and "place" in r2["answer"].lower()      # ONE question, no tool, no invented place


def test_duplicate_submit_is_rejected_while_a_turn_is_running(monkeypatch):
    import threading, time
    gate = threading.Event()
    def slow(n, a, d=None):
        gate.wait(2); return stub_tool(n, a, d)
    ag = agent(monkeypatch, slow)
    sid = ag.store.get(None).id
    out = {}
    th = threading.Thread(target=lambda: out.update(first=ag.handle({"message": "weather forecast for Cairo", "session_id": sid, "controls": {"answer_mode": "template"}})))
    th.start(); time.sleep(0.3)
    second = ag.handle({"message": "weather forecast for Cairo", "session_id": sid, "controls": {"answer_mode": "template"}})
    gate.set(); th.join()
    assert second["status"] == "busy" and out["first"]["status"] == "ok"
    assert len(ag.history(sid)) == 2                                   # the duplicate did not add history


def test_input_validation_and_internal_errors_are_recoverable(monkeypatch):
    a = agent(monkeypatch, lambda *x, **k: (_ for _ in ()).throw(KeyError("boom")))
    assert a.handle({"message": "   "})["status"] == "invalid_request"
    assert a.handle({"message": "x" * 2000})["status"] == "invalid_request"
    r = a.handle({"message": "weather forecast for Cairo", "controls": {"answer_mode": "template"}})
    assert r["status"] == "error" and "boom" not in r["answer"] and r["session_id"]


def test_provider_failure_is_shown_with_a_template_and_no_fake_data(monkeypatch):
    def failing(name, args, defaults=None):
        res = base.envelope("Open-Meteo", "Forecast API", "weather_forecast", "upstream_error", "TIMEOUT", "provider unavailable (timeout)")
        return tools.Outcome(result=res, artifacts=[], summary={"status": "upstream_error"}, location=(defaults or {}).get("location"), period=None, used_args={}, tool=name, status="upstream_error", duration_ms=1)
    r = agent(monkeypatch, failing).handle({"message": "weather forecast for Cairo", "controls": {"answer_mode": "template", "language": "en"}})
    assert r["status"] == "upstream_error" and r["artifacts"] == [] and "unavailable" in r["answer"].lower() and r["answer_source"] == "template"


def test_render_setup_guidance_for_missing_credentials():
    res = firms.detections([34.9, 31.7, 35.4, 32.2], None, 1) if False else base.envelope("NASA FIRMS", "x", "active_fire_detection", "needs_credentials", "FIRMS_MAP_KEY_MISSING", "FIRMS needs a free MAP_KEY.",
                                                                                           setup=firms.SETUP)
    out = {"result": res, "summary": {}}
    en, ar = render.render("get_fire_detections", out, "en"), render.render("get_fire_detections", out, "ar")
    assert "never in the chat" in en and "FIRMS_MAP_KEY" in en and "ليس في المحادثة" in ar
