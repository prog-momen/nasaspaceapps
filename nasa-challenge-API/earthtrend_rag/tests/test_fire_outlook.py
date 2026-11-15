"""One-month wildfire DANGER outlook: windows, freshness, NIFC parsing/aggregation (mocked), EWDS request/credentials/NetCDF (synthetic), routing, panel/UI contract."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import numpy as np
import pytest

from app.providers import fire_outlook as fo

ROOT = Path(__file__).resolve().parents[1]
TODAY = date(2026, 11, 15)


# ---------------------------------------------------------------- windows
def test_next_calendar_month_vs_30_days():
    a, b, k = fo.resolve_window("next_calendar_month", None, None, TODAY)
    assert (a, b, k) == (date(2026, 12, 1), date(2026, 12, 31), "next_calendar_month")
    a, b, k = fo.resolve_window("next_30_days", None, None, TODAY)
    assert (a, b) == (date(2026, 11, 15), date(2026, 12, 14)) and k == "next_30_days"
    assert fo.resolve_window("next_calendar_month", None, None, date(2026, 12, 31))[0] == date(2027, 1, 1)         # year rollover


def test_window_months_counts_days_in_each_month():
    ms = fo.window_months(date(2026, 11, 15), date(2026, 12, 14))
    assert [(m["label"], m["days_in_request"]) for m in ms] == [("2026-11", 16), ("2026-12", 14)]


# ---------------------------------------------------------------- freshness
@pytest.mark.parametrize("label,today,current", [("November 2026", date(2026, 11, 15), True), ("October 2026", date(2026, 11, 5), True), ("October 2026", date(2026, 11, 15), False),
                                                  ("August 2026", date(2026, 11, 2), False), (None, date(2026, 11, 2), False)])
def test_freshness_flags_stale_issues(label, today, current):
    assert fo.freshness(fo.parse_issue_label(label), today)["current"] is current


# ---------------------------------------------------------------- region names
NAMES = {"gacc": ["Alaska Interagency Coordination Center", "Great Basin Coordination Center", "Northern California Geographic Area", "Southwest Coordination Center"],
         "psa": ["Sac Valley/Foothills", "Northern California Coastal"]}


@pytest.mark.parametrize("text,kind,name", [("wildfire danger outlook for northern California next month", "gacc", "Northern California Geographic Area"),
                                             ("fire danger in Alaska", "gacc", "Alaska Interagency"), ("great basin", "gacc", "Great Basin"),
                                             ("fire danger in Sac Valley/Foothills", "psa", "Sac Valley/Foothills")])
def test_region_names_match_official_names(text, kind, name):
    m = fo.match_region_text(text, NAMES)
    assert m and m["kind"] == kind and m["name"].startswith(name.split(" Coordination")[0])


@pytest.mark.parametrize("text", ["fire risk in southwest Idaho next month", "California", "wildfire danger in Nablus", "", None])
def test_region_names_never_guess(text):
    assert fo.match_region_text(text, NAMES) is None


# ---------------------------------------------------------------- NIFC (mocked service)
_SQ0 = {"type": "Polygon", "coordinates": [[[-123, 40], [-122, 40], [-122, 41], [-123, 41], [-123, 40]]]}


def _sq(x0, y0, x1, y1):
    return {"type": "Polygon", "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]}


def _feat(psa, cat, geom=_SQ0, label="November 2026", gacc="Northern California Geographic Area"):
    return {"properties": {"PSANAME": psa, "GACCName": gacc, "FirePotent": cat, "Updatetime": label, "PSANationa": None}, "geometry": geom}


@pytest.fixture
def nifc(monkeypatch):
    calls = []

    def install(layers, label="November 2026"):
        def fake(layer, **kw):
            calls.append((layer, kw))
            return [dict(f, properties={**f["properties"], "Updatetime": label}) for f in layers.get(layer, [])], {"live": True, "cache": None, "retrieved_at": "2026-11-15T00:00:00Z"}
        monkeypatch.setattr(fo, "_nifc_query", fake)
    install.calls = calls
    return install


def test_point_outlook_maps_month_to_layer_and_keeps_categories_not_probabilities(nifc):
    nifc({0: [_feat("Redding", "Normal")], 1: [_feat("Redding", "Above")]})
    r = fo.nifc_outlook(40.58, -122.39, None, None, date(2026, 12, 1), date(2026, 12, 31), TODAY)
    assert r["status"] == "ok"
    assert [c[0] for c in nifc.calls][-1] == 1                                                  # December is layer 1 of a November issue
    m = r["data"]["months"][0]
    assert m["headline"] == "Above" and not m["mixed"] and m["categories"]["Above"]["share"] == 1.0
    txt = json.dumps(r).lower()
    assert "not a numerical probability" in txt and fo.SKILL_STATEMENT["en"] in r["limitations"]
    strip = next(a for a in r["artifacts"] if a["type"] == "category_strip")
    assert strip["inline"] and {c["text"] for c in strip["cells"]} == {"Above normal"} and strip["legend"]       # text label, not colour alone
    assert next(a for a in r["artifacts"] if a["type"] == "map_polygons")["layer_role"] == "forecast"


def test_stale_issue_is_not_shown_as_current(nifc):
    nifc({0: [_feat("Redding", "Normal")]}, label="August 2026")
    r = fo.nifc_outlook(40.58, -122.39, None, None, date(2026, 12, 1), date(2026, 12, 31), TODAY)
    assert r["status"] == "no_data" and r["reason_code"] == "NO_CURRENT_FORECAST" and "August 2026" in r["message"]


def test_outside_us_is_unsupported_region_and_no_psa_assigned_is_excluded(nifc):
    nifc({0: [_feat("No PSA Assigned", "Normal")]})
    r = fo.nifc_outlook(32.22, 35.25, None, None, date(2026, 12, 1), date(2026, 12, 31), TODAY)
    assert r["status"] == "unsupported_region" and r["reason_code"] == "OUTSIDE_NIFC_COVERAGE"


def test_period_beyond_issue_plus_three_months_is_reported_as_gap(nifc):
    nifc({0: [_feat("Redding", "Normal")]})
    r = fo.nifc_outlook(40.58, -122.39, None, None, date(2027, 6, 1), date(2027, 6, 30), TODAY)
    assert r["status"] == "no_data" and r["reason_code"] == "MISSING_FORECAST_COVERAGE"


def test_bbox_aggregates_by_area_share_with_mixed_categories(nifc):
    # 3 x 1 degree box at the equator-ish latitude: the Above PSA covers 2/3 of the box, the Normal PSA 1/3
    feats = [_feat("A", "Above", _sq(0, 0, 2, 1)), _feat("B", "Normal", _sq(2, 0, 3, 1))]
    nifc({0: feats, 1: feats})
    r = fo.nifc_outlook(0.5, 1.5, [0, 0, 3, 1], None, date(2026, 12, 1), date(2026, 12, 31), TODAY)
    m = r["data"]["months"][0]
    assert r["status"] == "ok" and m["mixed"] and m["headline"] == "Above"
    assert m["categories"]["Above"]["share"] == pytest.approx(0.667, abs=0.01) and m["categories"]["Normal"]["share"] == pytest.approx(0.333, abs=0.01)


# ---------------------------------------------------------------- orchestrator
def test_orchestrator_rejects_past_and_beyond_horizon_and_never_substitutes(monkeypatch):
    r = fo.forecast_fire_danger(40, -122, None, None, "2020-01-01", "2020-01-31", "custom", "auto", "x", today=TODAY, with_observations=False)
    assert r["reason_code"] == "PAST_PERIOD"
    r = fo.forecast_fire_danger(40, -122, None, None, "2028-01-01", "2028-01-31", "custom", "auto", "x", today=TODAY, with_observations=False)
    assert r["reason_code"] == "BEYOND_HORIZON"
    assert fo.forecast_fire_danger(None, None, None, None, today=TODAY)["reason_code"] == "LOCATION_REQUIRED"


def test_non_us_without_ewds_access_is_needs_credentials_not_a_substitute(monkeypatch, nifc):
    nifc({0: []})
    monkeypatch.setattr(fo, "ewds_key", lambda: None)
    monkeypatch.setattr(fo, "ewds_availability", lambda use_cache=True: {"latest_start": "2026-11-01"})
    monkeypatch.setattr(fo, "ewds_process_schema", lambda use_cache=True: _SCHEMA)
    r = fo.forecast_fire_danger(32.22, 35.25, None, None, None, None, "next_calendar_month", "auto", "Nablus", today=TODAY, with_observations=False)
    assert r["status"] == "needs_credentials" and r["reason_code"] == "EWDS_API_KEY_MISSING"
    assert r["setup"]["env"].startswith("EWDS_API_KEY") and "ewds.climate.copernicus.eu" in r["setup"]["register"] and r["setup"]["licence"] and r["setup"]["token"]
    assert not r["artifacts"]                                                                   # no invented numbers / maps


def test_observed_fires_are_a_separate_layer_never_mixed_with_the_forecast(monkeypatch, nifc):
    from app.providers import firms
    nifc({0: [_feat("Redding", "Normal")], 1: [_feat("Redding", "Normal")]})
    monkeypatch.setattr(firms, "detections", lambda *a, **k: {"status": "ok", "product": "VIIRS", "actual": {"n_detections": 1, "period": "x"}, "data": {"detections": [
        {"latitude": 40.6, "longitude": -122.4, "acq_date": "2026-11-14", "acq_time": "1200", "confidence": "n", "frp_mw": 3.0}]}})
    r = fo.forecast_fire_danger(40.58, -122.39, None, None, None, None, "next_calendar_month", "nifc", "Redding", today=TODAY)
    roles = {a.get("layer_role"): a["type"] for a in r["artifacts"] if a.get("layer_role")}
    assert roles == {"forecast": "map_polygons", "observed": "map_points"}
    obs = next(a for a in r["artifacts"] if a.get("layer_role") == "observed")
    assert all(p["label"].startswith("OBSERVED") for p in obs["points"])
    assert r["data"]["months"][0]["headline"] == "Normal"                                        # observations did not change the forecast category


# ---------------------------------------------------------------- EWDS
_SCHEMA = {"variable": {"schema": {"type": "array", "items": {"enum": ["fire_weather_index", "danger_risk"]}}}, "release_version": {"schema": {"type": "array", "items": {"enum": ["5"]}}},
           "year": {"schema": {"type": "array", "items": {"enum": ["2026"]}}}, "month": {"schema": {"type": "array", "items": {"enum": ["11"]}}}, "day": {"schema": {"type": "array", "items": {"enum": ["01"]}}},
           "leadtime_hour": {"schema": {"type": "array", "items": {"enum": [str(h) for h in range(12, 5200, 24)]}}}, "data_format": {"schema": {"type": "string", "enum": ["netcdf", "grib"]}},
           "area": {"schema": {"type": "array", "items": {"type": "number"}}}}


def test_ewds_request_is_validated_against_the_schema_and_leads_are_hours_from_day_one():
    days = [date(2026, 12, 1), date(2026, 12, 2)]
    req = fo.build_ewds_request("fire_weather_index", [2026], 11, days, [33, 35, 32, 36], date(2026, 11, 1), _SCHEMA)
    assert req["leadtime_hour"] == ["732", "756"] and req["day"] == ["01"] and req["area"] == [33, 35, 32, 36]       # Dec 1 is 30 days after Nov 1: 30*24 + 12 = 732
    with pytest.raises(ValueError, match="outside the dataset's allowed set"):
        fo.build_ewds_request("not_a_variable", [2026], 11, days, [33, 35, 32, 36], date(2026, 11, 1), _SCHEMA)
    with pytest.raises(ValueError, match="north > south"):
        fo.build_ewds_request("fire_weather_index", [2026], 11, days, [32, 35, 33, 36], date(2026, 11, 1), _SCHEMA)


def _write_nc(path, members=6, ndays=5, nan_member=None, units="1"):
    import netCDF4
    ds = netCDF4.Dataset(str(path), "w")
    ds.createDimension("number", members); ds.createDimension("valid_time", ndays); ds.createDimension("latitude", 3); ds.createDimension("longitude", 3)
    ds.createVariable("number", "i4", ("number",))[:] = np.arange(members)
    tv = ds.createVariable("valid_time", "f8", ("valid_time",)); tv.units = "days since 2026-12-01"; tv[:] = np.arange(ndays)
    ds.createVariable("latitude", "f8", ("latitude",))[:] = [32.0, 32.5, 33.0]
    ds.createVariable("longitude", "f8", ("longitude",))[:] = [35.0, 35.5, 36.0]
    v = ds.createVariable("fwi", "f4", ("number", "valid_time", "latitude", "longitude"), fill_value=-999.0)
    if units:
        v.units = units
    data = np.ones((members, ndays, 3, 3), "f4") * (np.arange(members)[:, None, None, None] + 1.0)
    if nan_member is not None:
        data[nan_member] = np.nan
    v[:] = data
    ds.close()


def test_netcdf_ensemble_analysis_with_a_missing_member(tmp_path):
    p = tmp_path / "a.nc"; _write_nc(p, members=6, nan_member=2)
    cur = fo.read_netcdf(p)
    assert cur["n_members"] == 6 and cur["members_missing"] == [2] and cur["units"] == "1"
    ana = fo.analyze_ensemble(cur, None, (date(2026, 12, 1), date(2026, 12, 5)))
    assert ana["n_members_used"] == 5 and ana["window_mean"]["ensemble_min"] == 1.0 and ana["window_mean"]["ensemble_max"] == pytest.approx(6.0) and len(ana["dates"]) == 5
    assert "NOT a complete or calibrated" in ana["spread_note"]


def test_netcdf_without_units_is_refused_and_window_outside_file_is_an_error(tmp_path):
    p = tmp_path / "b.nc"; _write_nc(p, units=None)
    with pytest.raises(ValueError, match="units"):
        fo.read_netcdf(p)
    p2 = tmp_path / "c.nc"; _write_nc(p2)
    with pytest.raises(ValueError, match="no day inside"):
        fo.analyze_ensemble(fo.read_netcdf(p2), None, (date(2027, 3, 1), date(2027, 3, 2)))


def test_terciles_come_only_from_a_reference_distribution(tmp_path):
    p = tmp_path / "d.nc"; _write_nc(p, members=6)
    cur = fo.read_netcdf(p)
    ref = {"array": np.random.default_rng(0).uniform(0, 7, (40, 5, 3, 3)), "lat": cur["lat"], "lon": cur["lon"], "times": cur["times"]}
    ana = fo.analyze_ensemble(cur, ref, (date(2026, 12, 1), date(2026, 12, 5)))
    s = ana["category_shares"]
    assert pytest.approx(s["below_normal"] + s["near_normal"] + s["above_normal"]) == 1.0 and "relative frequency" in s["definition"]
    assert fo.analyze_ensemble(cur, None, (date(2026, 12, 1), date(2026, 12, 5))).get("category_shares") is None        # no reference -> no categories


def test_ewds_job_errors_and_secret_redaction(monkeypatch, tmp_path):
    from app.providers.base import sanitize
    assert "SECRETVALUE" not in sanitize("PRIVATE-TOKEN SECRETVALUE failed token=SECRETVALUE", "SECRETVALUE")
    from app.config import SecretRedactingFilter
    import logging
    rec = logging.LogRecord("x", logging.INFO, "f", 1, "headers {'PRIVATE-TOKEN': 'abcdef12-3456-7890-abcd-ef1234567890'} url?token=abcdef", None, None)
    SecretRedactingFilter().filter(rec)
    assert "abcdef12-3456" not in rec.getMessage()


# ---------------------------------------------------------------- routing
@pytest.mark.parametrize("msg,window", [("كيف خطر الحرائق في منطقة نابلس خلال الشهر القادم؟", "next_calendar_month"),
                                        ("What is the wildfire danger outlook for northern California next month?", "next_calendar_month"),
                                        ("wildfire danger in Redding for the next 30 days", "next_30_days"), ("مخاطر الحرائق خلال الثلاثين يوم القادمة في بويز", "next_30_days")])
def test_free_text_routes_to_the_outlook(msg, window):
    from app.chat import router
    p = router.route(msg, {}, TODAY)
    assert p.tool == "forecast_fire_danger" and p.args["window"] == window


def test_probability_question_keeps_the_outlook_tool_and_flags_it():
    from app.chat import router
    p = router.route("what's the probability of wildfire in Redding next month", {}, TODAY)
    assert p.tool == "forecast_fire_danger" and "asks_probability" in p.flags


def test_plain_current_danger_and_detections_are_not_hijacked():
    from app.chat import router
    assert router.route("show me fire detections near Redding today", {}, TODAY).tool != "forecast_fire_danger"
    assert router.route("fire danger map for the US today", {}, TODAY).tool != "forecast_fire_danger"


# ---------------------------------------------------------------- answer / panel / UI contract
def _outcome():
    from app.chat import render
    return render


def test_template_answer_is_concise_and_carries_the_mandatory_statement():
    from app.chat import render
    r = {"status": "ok"}
    out = {"result": r, "summary": {"source": "NIFC", "window_kind": "next_calendar_month", "months": [{"month": "2026-12", "category": "Normal", "mixed": False, "shares": {"Normal": 1.0}, "days_in_request": 31}], "observed": {"n_detections": 4}},
           "location": {"name": "Redding"}}
    en = render._outlook(out, "en", asks_probability=True)
    assert "official model outlook; local forecast skill has not been verified by this application." in en
    assert "no numerical probability" in en.lower() and "not a forecast" in en and len(en.splitlines()) <= 6
    assert "هذا توقع رسمي مبني على نموذج" in render._outlook(out, "ar")


def test_credentials_setup_text_gives_exact_links_and_never_claims_access():
    from app.chat import render
    setup = fo.EWDS_SETUP
    assert setup["token"].endswith("how-to-api") and "tab=download" in setup["licence"] and setup["register"].startswith("https://ewds.climate.copernicus.eu")


def test_frontend_renders_strip_legend_forecast_vs_observed_and_is_valid_js():
    js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    for token in ('a.type === "category_strip"', "mapLegend", 'a.layer_role === "observed"', "p.color", "q.region", "Observed detections (not a forecast)"):
        assert token in js, token
    assert ".cat-cell" in css and ".map-legend" in css
    import shutil, subprocess
    if shutil.which("node"):
        assert subprocess.run(["node", "--check", str(ROOT / "frontend" / "app.js")], capture_output=True).returncode == 0


def test_registry_lists_ewds_and_nifc_and_auth_is_a_separate_check():
    from app.providers import registry
    ids = {p["id"]: p for p in registry.status()}
    assert "ewds" in ids and "nifc" in ids and ids["ewds"]["auth"] == ["EWDS_API_KEY"] and ids["ewds"]["extra_tests"].keys() == {"ewds_auth", "ewds_data"}
    from app.api import chat_api
    t = chat_api._tests()
    assert {"ewds", "ewds_auth", "ewds_data", "nifc"} <= set(t)


def test_ewds_notice_is_surfaced_and_link_text_clean(monkeypatch):
    """The official catalogue warning (updates ceasing) is parsed into the availability facts and shown as a limitation without touching the forecast's own validity window."""
    cat = {"updated": "2026-11-05T00:00:00Z", "license": "CC-BY-4.0", "sci:doi": "x", "links": [{"rel": "constraints", "href": "https://x/c"}],
           "cads:message": {"severity": "warning", "date": "2026-11-12T00:00:00Z", "content": "Updates will cease. See [this page](https://example.org/p) for details."}}
    def fake(name, method, url, **kw):
        return (cat if name == "ewds-cat" else [{"year": ["2026"], "month": ["10"]}]), {"retrieved_at": "t", "live": True}
    monkeypatch.setattr(fo, "http_json", fake)
    monkeypatch.setattr(fo, "ewds_key", lambda: None)
    av = fo.ewds_availability(False)
    assert av["notice"]["severity"] == "warning" and "this page (https://example.org/p)" in av["notice"]["text"] and "\x01" not in av["notice"]["text"]
    monkeypatch.setattr(fo, "ewds_process_schema", lambda use_cache=True: {})
    monkeypatch.setattr(fo, "build_ewds_request", lambda *a, **k: {"variable": ["fire_weather_index"]})
    r = fo.ewds_outlook(32.2, 35.3, None, date(2026, 12, 1), date(2026, 12, 31), date(2026, 11, 15))
    assert r["status"] == "needs_credentials" and any("Official EWDS notice" in x for x in r["limitations"])


def test_read_netcdf_real_ewds_layout_scalar_time_plus_valid_time_on_step(tmp_path):
    """Real EWDS NetCDF (cfgrib): scalar 'time' = forecast reference, 'step' axis, 'valid_time'(step) = the dates. valid_time must be used."""
    import netCDF4
    p = tmp_path / "x.nc"
    ds = netCDF4.Dataset(p, "w")
    for n, k in (("number", 3), ("step", 4), ("latitude", 2), ("longitude", 2)):
        ds.createDimension(n, k)
    ds.createVariable("number", "i8", ("number",))[:] = [0, 1, 2]
    t = ds.createVariable("time", "i8", ()); t.units = "seconds since 1970-01-01"; t[...] = 1790812800
    s = ds.createVariable("step", "f8", ("step",)); s.units = "hours"; s[:] = [1476, 1500, 1524, 1548]
    vt = ds.createVariable("valid_time", "i8", ("step",)); vt.units = "seconds since 1970-01-01T00:00:00"; vt[:] = [1796126400 + 86400 * i for i in range(4)]
    ds.createVariable("latitude", "f8", ("latitude",))[:] = [32.72, 31.72]
    ds.createVariable("longitude", "f8", ("longitude",))[:] = [34.75, 35.75]
    v = ds.createVariable("fwinx", "f4", ("number", "step", "latitude", "longitude")); v.units = "Numeric"
    a = np.random.rand(3, 4, 2, 2).astype("f4"); a[:, :, 0, 0] = np.nan; v[:] = a
    ds.close()
    c = fo.read_netcdf(p)
    assert c["array"].shape == (3, 4, 2, 2) and len(c["times"]) == 4 and c["times"][0].year == 2026 and c["times"][0].month == 12
    ana = fo.analyze_ensemble(c, None, (c["times"][0], c["times"][-1]))
    assert ana["n_members_used"] == 3 and np.isfinite(ana["window_mean"]["ensemble_median"])


def test_reference_reader_pools_member_year_and_terciles_come_only_from_it(tmp_path):
    import netCDF4
    p = tmp_path / "ref.nc"
    ds = netCDF4.Dataset(p, "w")
    for n, k in (("number", 5), ("time", 10), ("step", 3), ("latitude", 2), ("longitude", 2)):
        ds.createDimension(n, k)
    ds.createVariable("number", "i8", ("number",))[:] = range(5)
    ds.createVariable("time", "i8", ("time",))[:] = range(10)
    ds.createVariable("step", "f8", ("step",))[:] = [0, 24, 48]
    ds.createVariable("latitude", "f8", ("latitude",))[:] = [1, 0]
    ds.createVariable("longitude", "f8", ("longitude",))[:] = [0, 1]
    v = ds.createVariable("fwinx", "f4", ("number", "time", "step", "latitude", "longitude")); v.units = "Numeric"
    v[:] = np.tile(np.arange(50, dtype="f4").reshape(5, 10, 1, 1, 1), (1, 1, 3, 2, 2))
    ds.close()
    ref = fo.read_reference_netcdf(p)
    assert ref["array"].shape == (50, 3, 2, 2) and ref["n_years"] == 10
    cur = {"array": np.full((4, 3, 2, 2), 40.0), "lat": np.array([1.0, 0.0]), "lon": np.array([0.0, 1.0]), "times": [date(2026, 12, 1), date(2026, 12, 2), date(2026, 12, 3)], "units": "Numeric", "variable": "fwinx", "n_members": 4, "members_missing": []}
    a = fo.analyze_ensemble(cur, ref, (date(2026, 12, 1), date(2026, 12, 3)))
    assert a["reference"]["n_values"] == 50 and a["category_shares"]["above_normal"] == 1.0          # 40 > upper tercile (~33) of 0..49
    assert abs(sum(a["category_shares"][k] for k in ("below_normal", "near_normal", "above_normal")) - 1.0) < 1e-9
