"""Trend pipeline / tool tests. Series are SYNTHETIC unless the test says it uses the real captured NASA POWER response."""
import json
from pathlib import Path

import numpy as np
import pymannkendall as pmk
import pytest

from app.analysis.timeseries import MonthlySeries
from app.analysis.trend import analyze_series
from app.data_sources.power import SourceError, parse_power_monthly
from app.tools.trend_tool import run_trend_analysis

SYN = {"provider": "SYNTHETIC test data (not NASA)", "dataset": "synthetic", "fill_value": -999.0}
VAR = {"id": "air_temperature", "name": "Synthetic variable"}
REG = {"name": "nowhere", "lat": 0.0, "lon": 0.0, "type": "point"}
FIXTURE = Path(__file__).parent / "fixtures" / "power_monthly_nablus_T2M_real_capture.json"


def make(y0=2005, y1=2024, slope=0.0, seasonal_amp=0.0, ar=0.0, noise=0.5, seed=0, missing=(), invalid=(), flags=None):
    r = np.random.default_rng(seed)
    years, months, vals = [], [], []
    e = 0.0
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            e = ar * e + r.normal(0, noise)
            v = 20 + slope * (y - y0 + m / 12) + seasonal_amp * np.sin(2 * np.pi * m / 12) + e
            years.append(y), months.append(m)
            vals.append(round(float(v), 3))
    vals = list(vals)
    for k in missing:
        vals[k] = None
    for k in invalid:
        vals[k] = -999.0
    return MonthlySeries(years, months, vals, "°C", flags, dict(SYN))


def run(series, y0=2005, y1=2024, **kw):
    return analyze_series(series, variable=VAR, region=REG, start_year=y0, end_year=y1, fill_values=[-999.0], **kw)


# ---- trend directions -------------------------------------------------------------------------------------

def test_rising_series_detected_with_magnitude_and_units():
    r = run(make(slope=0.05, seasonal_amp=6, seed=1))
    t = r["test"]
    assert r["status"] == "ok" and t["significant"] and t["direction"] == "increasing"
    assert t["sen_slope"]["unit"] == "°C/year" and abs(t["sen_slope"]["value"] - 0.05) < 0.02
    assert t["sen_slope"]["ci_low"] < 0.05 < t["sen_slope"]["ci_high"]
    assert r["interpretation"]["code"] == "SIGNIFICANT_INCREASE"


def test_falling_series_detected():
    r = run(make(slope=-0.06, seasonal_amp=4, seed=2))
    assert r["test"]["significant"] and r["test"]["direction"] == "decreasing" and r["interpretation"]["code"] == "SIGNIFICANT_DECREASE"


def test_flat_series_is_not_declared_a_trend_and_uses_mandated_wording():
    r = run(make(slope=0.0, seasonal_amp=5, seed=3))
    assert not r["test"]["significant"] and r["interpretation"]["code"] == "NOT_SIGNIFICANT"
    assert "البيانات الحالية لا تكفي لتأكيد وجود اتجاه" in r["interpretation"]["text_ar"]
    assert "لا يوجد تغيّر" not in r["interpretation"]["text_ar"] and "no change" not in r["interpretation"]["text_en"].lower()


def test_direction_magnitude_and_significance_are_separate_fields():
    r = run(make(slope=0.003, seasonal_amp=5, seed=4, noise=1.0))      # tiny slope, not significant but has a sign
    t = r["test"]
    assert {"direction", "sen_slope", "p_value", "significant", "alpha", "kendall_tau"} <= set(t)
    assert t["direction"] in ("increasing", "decreasing") and t["significant"] is False


def test_constant_series_does_not_crash():
    ser = make(slope=0.0, noise=0.0)
    r = run(ser)
    assert r["status"] == "ok" and r["test"]["p_value"] == 1.0 and r["test"]["kendall_tau"] == 0 and r["test"]["direction"] == "flat"
    assert any("no variation" in n for n in r["notes"])


# ---- required output contract --------------------------------------------------------------------------------

def test_result_contains_all_required_fields():
    r = run(make(slope=0.04, seasonal_amp=5, seed=5))
    for k in ("variable", "region", "period_actual", "units", "aggregation", "test", "data_quality", "source", "caveats", "chart"):
        assert k in r, k
    t = r["test"]
    for k in ("n_used", "n_unit", "test_name", "kendall_tau", "p_value", "alpha", "significant", "sen_slope", "tails"):
        assert k in t, k
    assert r["aggregation"]["chosen"] in ("annual", "monthly_seasonal") and r["aggregation"]["reason"]
    assert t["alpha"] == 0.05                                              # declared default threshold
    assert any("ليس" in c or "لا يثبت" in c for c in r["caveats"])         # not causal / not a forecast
    assert any("forecast" in c.lower() for c in r["caveats_en"])
    json.dumps(r)                                                         # JSON-serialisable


def test_alpha_is_configurable_and_reported():
    ser = make(slope=0.02, seasonal_amp=5, seed=6, noise=1.0)
    strict = run(ser, alpha=0.001)
    assert strict["test"]["alpha"] == 0.001 and strict["alpha"] == 0.001
    assert strict["test"]["sen_slope"]["ci_level"] == pytest.approx(0.999)


# ---- data quality, gaps, flags -----------------------------------------------------------------------------

def test_fill_values_are_excluded_and_counted_not_averaged():
    r = run(make(slope=0.05, seasonal_amp=5, seed=7, invalid=[3, 4, 5, 100]))
    dq = r["data_quality"]
    assert dq["invalid_months"] == 4 and dq["invalid_reasons"] == {"fill_value": 4} and dq["valid_months"] == 240 - 4
    assert min(r["chart"]["y"]) > 0                                         # -999 never reached the statistics


def test_source_quality_flags_exclude_readings():
    ser = make(slope=0.05, seasonal_amp=5, seed=8)
    flags = ["good"] * len(ser.value)
    for k in range(20, 30):
        flags[k] = "cloud"
    ser.quality = flags
    r = analyze_series(ser, variable=VAR, region=REG, start_year=2005, end_year=2024, valid_flags={"good"})
    assert r["data_quality"]["invalid_months"] == 10 and r["data_quality"]["invalid_reasons"] == {"quality_flag": 10}


def test_missing_values_are_documented_and_never_filled():
    miss = list(range(30, 42)) + [100, 101, 150]                          # one full-year gap + scattered
    r = run(make(slope=0.05, seasonal_amp=5, seed=9, missing=miss))
    dq = r["data_quality"]
    assert dq["missing_months"] == 15 and dq["longest_gap_months"] == 12 and "no imputation" in dq["gap_policy"]
    assert r["test"]["n_used"] <= 240 - 15
    assert r["chart"]["missing_months_not_drawn"] == 15                    # reported, never drawn or interpolated
    monthly = run(make(slope=0.05, seasonal_amp=5, seed=9, missing=miss), aggregation="monthly_seasonal")
    assert len(monthly["chart"]["y"]) == 240 - 15                          # monthly chart has exactly the valid readings
    assert dq["coverage_fraction"] == pytest.approx(225 / 240, abs=1e-3)


def test_years_with_too_few_months_are_dropped_and_listed():
    miss = list(range(12 * 3, 12 * 3 + 8))                                # year index 3 keeps only 4 valid months
    r = run(make(slope=0.05, seasonal_amp=5, seed=10, missing=miss), aggregation="annual")
    assert {"year": 2008, "valid_months": 4} in r["data_quality"]["years_dropped"]
    assert 2008 not in r["data_quality"]["years_used"] and r["test"]["n_used"] == 19


def test_too_few_years_returns_status_not_a_verdict():
    r = run(make(y0=2018, y1=2024, slope=0.5, seed=11), y0=2018, y1=2024)
    assert r["status"] == "insufficient_data" and r["reason_code"] == "TOO_FEW_YEARS" and "test" not in r


def test_low_coverage_returns_status():
    miss = [k for k in range(240) if k % 3 != 0]                          # only 1/3 of months valid
    r = run(make(seed=12, missing=miss), min_months_per_year=3)
    assert r["status"] == "insufficient_data" and r["reason_code"] == "LOW_COVERAGE"


def test_fetch_errors_are_not_treated_as_missing_data():
    ser = make(slope=0.05, seed=13)
    ser.fetch_errors = 3
    r = run(ser)
    assert r["status"] == "insufficient_data" and r["reason_code"] == "FETCH_ERRORS"


# ---- seasonality and autocorrelation handling ----------------------------------------------------------------

def test_seasonal_white_noise_uses_seasonal_mann_kendall():
    r = run(make(slope=0.05, seasonal_amp=8, ar=0.0, seed=14, noise=0.7))
    d = r["diagnostics"]
    assert d["seasonality"]["significant"] and not d["autocorrelation_monthly_deseasonalised"]["significant"]
    assert r["aggregation"]["chosen"] == "monthly_seasonal" and "Seasonal" in r["test"]["test_name"]
    assert r["test"]["n_unit"] == "monthly readings"


def test_autocorrelated_monthly_series_is_aggregated_and_reason_recorded():
    r = run(make(slope=0.0, seasonal_amp=8, ar=0.85, seed=15, noise=0.8))
    assert r["diagnostics"]["autocorrelation_monthly_deseasonalised"]["significant"]
    assert r["aggregation"]["chosen"] == "annual" and "autocorrelation" in r["aggregation"]["reason"]
    assert r["sensitivity"] is not None                                    # the seasonal variant is still reported for comparison


def test_annual_autocorrelation_is_rechecked_and_variance_corrected():
    # persistent annual series: annual means do NOT remove autocorrelation, so the Hamed-Rao correction must engage
    r = np.random.default_rng(21)
    x = np.zeros(45)
    for i in range(1, 45):
        x[i] = 0.8 * x[i - 1] + r.normal()
    years = list(range(1980, 2025))
    ser = MonthlySeries([y for y in years for _ in range(12)], [m for _ in years for m in range(1, 13)],
                        [round(float(x[i // 12]), 4) for i in range(45 * 12)], "°C", None, dict(SYN))
    res = run(ser, 1980, 2024, aggregation="annual")
    t = res["test"]
    assert t["variance_correction_factor"] > 1.0 and "Hamed" in t["test_name"]
    assert res["diagnostics"]["autocorrelation_annual"]["hamed_rao_factor_applied"] == t["variance_correction_factor"]


def test_annual_result_matches_reference_library():
    ser = make(slope=0.04, seasonal_amp=5, seed=16, noise=1.0)
    r = run(ser, aggregation="annual")
    ann = np.array([np.mean(ser.value[i * 12:(i + 1) * 12]) for i in range(20)])
    ref = pmk.original_test(ann)
    t = r["test"]
    if "original" in t["test_name"]:
        assert t["p_value"] == pytest.approx(ref.p, abs=5e-4) and t["kendall_tau"] == pytest.approx(ref.Tau, abs=5e-4)
        assert t["sen_slope"]["value"] == pytest.approx(ref.slope, rel=0.02)     # month-centred times ~ annual steps


# ---- tool layer ---------------------------------------------------------------------------------------------

def fetcher_for(series):
    return lambda *a, **k: series


def test_tool_runs_end_to_end_on_synthetic_series():
    r = run_trend_analysis({"variable": "air_temperature", "region": "Nablus", "start_year": 2005, "end_year": 2024},
                           fetcher=fetcher_for(make(slope=0.05, seasonal_amp=6, seed=17)))
    assert r["status"] == "ok" and r["tool"]["name"] == "analyze_trend" and r["region"]["lat"] == 32.22


def test_land_surface_temperature_is_not_silently_replaced_by_air_temperature():
    called = []
    r = run_trend_analysis({"variable": "land surface temperature", "region": "Amazon", "start_year": 2005, "end_year": 2025},
                           fetcher=lambda *a, **k: called.append(1))
    assert r["status"] == "data_source_unavailable" and r["reason_code"] == "SOURCE_REQUIRES_CREDENTIALS"
    assert r["suggested_alternative"] == "air_temperature" and not called and "test" not in r


@pytest.mark.parametrize("var", ["wildfires", "drought"])
def test_variables_without_a_ready_source_return_status(var):
    r = run_trend_analysis({"variable": var, "region": "Amazon", "start_year": 2005, "end_year": 2025}, fetcher=lambda *a, **k: 1 / 0)
    assert r["status"] == "unsupported_variable" and "test" not in r


@pytest.mark.parametrize("args,code", [
    ({"variable": "air_temperature", "region": "Atlantis", "start_year": 2005, "end_year": 2020}, "REGION_NOT_RESOLVED"),
    ({"variable": "air_temperature", "region": "Amazon", "start_year": 2020, "end_year": 2005}, "INVALID_ARGUMENTS"),
    ({"variable": "air_temperature", "region": "Amazon", "start_year": 1950, "end_year": 2005}, "INVALID_ARGUMENTS"),
    ({"variable": "air_temperature", "region": "Amazon", "start_year": 2005, "end_year": 2999}, "INVALID_ARGUMENTS"),
    ({"variable": "air_temperature", "latitude": 95, "longitude": 0, "start_year": 2005, "end_year": 2020}, "INVALID_ARGUMENTS"),
    ({"variable": "banana", "region": "Amazon", "start_year": 2005, "end_year": 2020}, "UNKNOWN_VARIABLE"),
])
def test_invalid_requests_return_status_not_exceptions(args, code):
    r = run_trend_analysis(args, fetcher=fetcher_for(make()))
    assert r["status"] in ("invalid_request", "unsupported_variable") and r["reason_code"] == code


def test_upstream_failure_is_reported_not_turned_into_a_verdict():
    def boom(*a, **k):
        raise SourceError("NASA POWER unavailable (ConnectError)")
    r = run_trend_analysis({"variable": "air_temperature", "region": "Amazon", "start_year": 2005, "end_year": 2024}, fetcher=boom)
    assert r["status"] == "upstream_error" and "test" not in r and "interpretation" not in r


def test_explicit_coordinates_are_accepted():
    r = run_trend_analysis({"variable": "air_temperature", "latitude": 10.5, "longitude": -60.25, "start_year": 2005, "end_year": 2024},
                           fetcher=fetcher_for(make(slope=0.05, seasonal_amp=5, seed=18)))
    assert r["status"] == "ok" and r["region"]["type"] == "point"


# ---- real NASA POWER capture (recorded 2026-11-14), offline -------------------------------------------------

def test_power_parser_skips_annual_summary_and_fill_values():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    s = parse_power_monthly(payload, "T2M", "fixture")
    assert len(s.year) == 252 and 13 not in s.month and s.units == "°C" and s.source["provider"] == "NASA POWER"
    payload["properties"]["parameter"]["T2M"]["200503"] = -999.0
    s2 = parse_power_monthly(payload, "T2M", "fixture")
    r = analyze_series(s2, variable=VAR, region=REG, start_year=2005, end_year=2025, fill_values=[s2.source["fill_value"]])
    assert r["data_quality"]["invalid_months"] == 1 and r["data_quality"]["invalid_reasons"] == {"fill_value": 1}


def test_real_nasa_power_capture_end_to_end_matches_reference_library():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    ser = parse_power_monthly(payload, "T2M", "fixture")
    r = run_trend_analysis({"variable": "air_temperature", "region": "Nablus", "start_year": 2005, "end_year": 2025}, fetcher=fetcher_for(ser))
    assert r["status"] == "ok" and r["data_quality"]["valid_months"] == 252 and r["source"]["dataset"] == "MERRA2"
    ann = np.array([np.mean(ser.value[i * 12:(i + 1) * 12]) for i in range(21)])
    ref = pmk.original_test(ann)
    assert r["aggregation"]["chosen"] == "annual" and r["test"]["n_used"] == 21
    assert r["test"]["kendall_tau"] == pytest.approx(ref.Tau, abs=1e-3) and r["test"]["p_value"] == pytest.approx(ref.p, abs=1e-3)
    assert r["test"]["sen_slope"]["value"] == pytest.approx(ref.slope, rel=0.05)
