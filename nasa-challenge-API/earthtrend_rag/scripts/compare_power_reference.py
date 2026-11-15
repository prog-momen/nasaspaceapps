"""Controlled comparison: independent reference statistics vs the project's analyze_trend path, on ONE saved NASA POWER payload.

  python scripts/compare_power_reference.py capture   # ONE direct HTTP request to NASA POWER; saves raw payload + request metadata
  python scripts/compare_power_reference.py compare   # offline: reference vs project on the saved payload (re-runnable)
  python scripts/compare_power_reference.py live-project   # ONE request through the project's own client (no cache), compared with the saved payload

The "reference" side here is an INDEPENDENT re-implementation using only numpy/scipy/pymannkendall (it is NOT the
user's attached script, which was not present in the workspace). Nothing is tuned to match historical numbers.
"""
from __future__ import annotations

import calendar
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pymannkendall as pmk
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
EVID = ROOT / "evidence" / "power_T2M_31.8_35.2_1981_2025"
RAW = EVID / "raw_response.json"
META = EVID / "request_metadata.json"
PARAMS = {"parameters": "T2M", "community": "AG", "longitude": "35.2000", "latitude": "31.8000",
          "start": "1981", "end": "2025", "format": "JSON"}
BASE = "https://power.larc.nasa.gov/api/temporal/monthly/point"
HISTORICAL = {"valid_months": 540, "ols_c_per_decade": 0.37, "ols_ci95": [0.28, 0.46], "theil_sen_c_per_decade": 0.35, "mk_p": 3.25e-9}


def capture() -> None:
    import httpx
    EVID.mkdir(parents=True, exist_ok=True)
    t0 = datetime.now(timezone.utc)
    r = httpx.get(BASE, params=PARAMS, timeout=httpx.Timeout(30, connect=5))
    raw_bytes = r.content
    META.write_text(json.dumps({
        "retrieved_at_utc": t0.isoformat(timespec="seconds"), "method": "GET", "url_base": BASE, "params": PARAMS,
        "http_status": r.status_code, "content_type": r.headers.get("content-type"), "bytes": len(raw_bytes),
        "sha256": hashlib.sha256(raw_bytes).hexdigest(), "elapsed_s": round(r.elapsed.total_seconds(), 2),
        "requests_made": 1, "note": "public endpoint, no credentials"}, indent=2), encoding="utf-8")
    if r.status_code == 200:
        RAW.write_bytes(raw_bytes)
    print("captured:", r.status_code, len(raw_bytes), "bytes")


# ----------------------------------------------------------------------------------- reference side
def ref_parse(payload: dict) -> dict:
    """year-month -> value (NaN for fill/non-finite), skipping the 13th pseudo-month."""
    fill = payload["header"].get("fill_value", -999.0)
    out, fills = {}, 0
    for k, v in payload["properties"]["parameter"]["T2M"].items():
        y, m = int(k[:4]), int(k[4:])
        if m == 13:
            continue
        if v is None or float(v) == fill or not math.isfinite(float(v)):
            out[(y, m)] = float("nan")
            fills += 1
        else:
            out[(y, m)] = float(v)
    return {"values": out, "fill_count": fills, "units": payload["parameters"]["T2M"]["units"]}


def ref_annual(values: dict, weighted: bool, min_months: int = 12):
    years = sorted({y for y, _ in values})
    ys, xs, dropped = [], [], []
    for y in years:
        pts = [(m, values[(y, m)]) for m in range(1, 13) if (y, m) in values and not math.isnan(values[(y, m)])]
        if len(pts) < min_months:
            dropped.append(y)
            continue
        if weighted:
            w = np.array([calendar.monthrange(y, m)[1] for m, _ in pts], float)
            xs.append(float(np.average([v for _, v in pts], weights=w)))
        else:
            xs.append(float(np.mean([v for _, v in pts])))
        ys.append(y)
    return np.array(ys, float), np.array(xs), dropped


def ref_stats(years, ann) -> dict:
    n = len(years)
    lr = stats.linregress(years, ann)
    tcrit = stats.t.ppf(0.975, n - 2)
    ts = stats.theilslopes(ann, years, 0.95)
    mk = pmk.original_test(ann)
    return {"n_years": n, "ols_c_per_decade": lr.slope * 10, "ols_ci95_c_per_decade": [(lr.slope - tcrit * lr.stderr) * 10, (lr.slope + tcrit * lr.stderr) * 10],
            "ols_p": lr.pvalue, "theil_sen_c_per_decade": ts.slope * 10, "theil_sen_ci95_c_per_decade": [ts.low_slope * 10, ts.high_slope * 10],
            "mk_original_p": mk.p, "mk_original_tau": mk.Tau, "mk_original_z": mk.z, "mk_S": mk.s}


def lag1_corr_calendar(series: np.ndarray) -> float:
    a, b = series[:-1], series[1:]
    ok = ~np.isnan(a) & ~np.isnan(b)
    return float(np.corrcoef(a[ok], b[ok])[0, 1])


def autocorr_demo(values: dict) -> dict:
    """Illustrates the concern about autocorrelating anomalies BEFORE removing the trend (on this dataset)."""
    ys = sorted({y for y, _ in values})
    cal = np.array([values.get((y, m), float("nan")) for y in ys for m in range(1, 13)])
    months = np.tile(np.arange(12), len(ys))
    anom = cal.copy()
    for m in range(12):
        anom[months == m] -= np.nanmean(cal[months == m])
    t = np.array([y + (m + 0.5) / 12 for y in ys for m in range(12)])
    ok = ~np.isnan(anom)
    slope = stats.theilslopes(anom[ok], t[ok])[0]
    resid = anom - slope * (t - t[ok].mean())
    return {"lag1_of_anomalies_trend_NOT_removed": lag1_corr_calendar(anom), "lag1_of_anomalies_after_removing_Sen_trend": lag1_corr_calendar(resid),
            "note": "difference shows how much of the 'autocorrelation' is just the trend"}


# ------------------------------------------------------------------------------------- project side
def project_side(payload: dict, meta: dict) -> dict:
    from app.agent.trend_agent import render_template  # noqa: F401  (import check only)
    from app.analysis import stats as pst
    from app.data_sources.power import parse_power_monthly
    from app.tools.trend_tool import run_trend_analysis
    ser = parse_power_monthly(payload, "T2M", meta["url_base"], meta["retrieved_at_utc"])
    f = lambda *a, **k: ser
    args = {"variable": "air_temperature", "latitude": 31.8, "longitude": 35.2, "start_year": 1981, "end_year": 2025}
    out = {}
    for agg in ("annual", "auto", "monthly_seasonal"):
        r = run_trend_analysis({**args, "aggregation": agg}, fetcher=f)
        out[agg] = r
    # apples-to-apples: the plain annual Mann-Kendall on the project's own annual means
    r = out["annual"]
    ann = np.array(r["chart"]["y"])
    t = np.array(r["chart"]["t_decimal_year"])
    plain = pst.mann_kendall(ann)
    out["_plain_annual_mk_on_project_annual_means"] = {"p": plain.p_value, "tau": plain.tau, "S": plain.S, "var_S": plain.var_S}
    out["_parsed_series"] = {"years": ser.year, "months": ser.month, "values": ser.value, "units": ser.units}
    return out


def compare() -> dict:
    payload = json.loads(RAW.read_text(encoding="utf-8"))
    meta = json.loads(META.read_text(encoding="utf-8"))
    ref = ref_parse(payload)
    valid_ref = sum(1 for v in ref["values"].values() if not math.isnan(v))
    years, ann, dropped = ref_annual(ref["values"], weighted=False)
    yw, annw, _ = ref_annual(ref["values"], weighted=True)
    ref_u, ref_w = ref_stats(years, ann), ref_stats(yw, annw)
    proj = project_side(payload, meta)

    # --- data comparison (month by month, exact) -------------------------------------------------------
    ps = proj["_parsed_series"]
    pvals = {(y, m): (float("nan") if v is None else v) for y, m, v in zip(ps["years"], ps["months"], ps["values"])}
    mism = [(k, ref["values"][k], pvals.get(k)) for k in ref["values"] if k not in pvals or not (
        (math.isnan(ref["values"][k]) and math.isnan(pvals[k])) or ref["values"][k] == pvals[k])]
    data_cmp = {"reference_months": len(ref["values"]), "project_months": len(pvals), "reference_valid_months": valid_ref,
                "project_valid_months": proj["annual"]["data_quality"]["valid_months"], "fill_values_seen": ref["fill_count"],
                "month13_present_in_raw": any(k.endswith("13") for k in payload["properties"]["parameter"]["T2M"]),
                "month13_in_project_series": any(m == 13 for m in ps["months"]), "month_value_mismatches": len(mism),
                "first": min(pvals), "last": max(pvals), "units": ref["units"], "project_units": ps["units"]}

    # --- statistics comparison --------------------------------------------------------------------------
    pa, pauto = proj["annual"], proj["auto"]
    ann_proj = np.array(pa["chart"]["y"])
    same_annual = bool(len(ann_proj) == len(ann) and np.allclose(ann_proj, ann, atol=5e-4))   # project rounds chart values to 4 dp
    sen_proj = pa["test"]["sen_slope"]
    algo = {
        "annual_means_match_reference_unweighted": same_annual,
        "max_abs_diff_annual_means": float(np.max(np.abs(ann_proj - ann))) if len(ann_proj) == len(ann) else None,
        "project_annual_n": pa["test"]["n_used"], "reference_annual_n": ref_u["n_years"], "years_dropped_by_project": pa["data_quality"]["years_dropped"],
        "project_min_months_per_year": pa["data_quality"]["min_months_per_year"], "reference_min_months_per_year": 12,
        "project_theil_sen_c_per_decade": sen_proj["value"] * 10, "reference_theil_sen_c_per_decade": ref_u["theil_sen_c_per_decade"],
        "theil_sen_abs_diff": abs(sen_proj["value"] * 10 - ref_u["theil_sen_c_per_decade"]),
        "project_sen_note": "project Sen uses pairwise slopes on decimal-year mid-points of the valid months of each year (mean month centre); reference uses calendar years",
        "project_mk_test_name_annual": pa["test"]["test_name"], "project_mk_p_reported": pa["test"]["p_value"],
        "project_variance_correction_factor": pa["test"]["variance_correction_factor"],
        "project_plain_mk_p_on_project_annual_means": proj["_plain_annual_mk_on_project_annual_means"]["p"],
        "reference_mk_original_p": ref_u["mk_original_p"], "reference_mk_original_tau": ref_u["mk_original_tau"], "project_tau": pa["test"]["kendall_tau"],
        "project_auto_choice": pauto["aggregation"]["chosen"], "project_auto_reason": pauto["aggregation"]["reason"],
        "project_auto_test": pauto["test"]["test_name"], "project_auto_p": pauto["test"]["p_value"],
        "project_auto_sen_c_per_decade": pauto["test"]["sen_slope"]["value"] * 10,
        "project_monthly_seasonal_p": proj["monthly_seasonal"]["test"]["p_value"],
        "project_monthly_seasonal_sen_c_per_decade": proj["monthly_seasonal"]["test"]["sen_slope"]["value"] * 10,
        "project_diagnostics": pauto["diagnostics"],
    }
    wt = {"weighted_vs_unweighted_ols_diff_c_per_decade": ref_w["ols_c_per_decade"] - ref_u["ols_c_per_decade"],
          "weighted_vs_unweighted_sen_diff_c_per_decade": ref_w["theil_sen_c_per_decade"] - ref_u["theil_sen_c_per_decade"],
          "max_abs_annual_mean_diff": float(np.max(np.abs(annw - ann))), "weighted": ref_w, "note": "unweighted = mean of 12 monthly means (what both sides use)"}
    hist = {"historical_figures_supplied_by_user": HISTORICAL,
            "today_reference_unweighted": ref_u, "today_reference_valid_months": valid_ref,
            "consistent_with_historical": {
                "valid_months": valid_ref == HISTORICAL["valid_months"],
                "ols_within_0.05": bool(abs(ref_u["ols_c_per_decade"] - HISTORICAL["ols_c_per_decade"]) <= 0.05),
                "theil_sen_within_0.05": bool(abs(ref_u["theil_sen_c_per_decade"] - HISTORICAL["theil_sen_c_per_decade"]) <= 0.05),
                "mk_p_same_order_of_magnitude": bool(0.1 < ref_u["mk_original_p"] / HISTORICAL["mk_p"] < 10)}}
    result = {"request": meta, "data_comparison": data_cmp, "algorithm_comparison": algo, "annual_weighting": wt,
              "historical_comparison": hist, "autocorrelation_demo_reference": autocorr_demo(ref["values"]),
              "project_daily_support": "none (project path is monthly POWER only); daily/hot-day analysis is NOT comparable to annual means"}
    (EVID / "comparison_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str, allow_nan=False), encoding="utf-8")
    return result


def live_project() -> dict:
    """ONE request through the project's own client (cache bypassed) and a month-by-month comparison with the saved payload."""
    from app.data_sources.power import fetch_power_monthly
    saved = ref_parse(json.loads(RAW.read_text(encoding="utf-8")))["values"]
    s = fetch_power_monthly("T2M", 31.8, 35.2, 1981, 2025, use_cache=False)
    now = {(y, m): (float("nan") if v is None else v) for y, m, v in zip(s.year, s.month, s.value)}
    diffs = [(k, saved.get(k), now.get(k)) for k in set(saved) | set(now)
             if not ((k in saved and k in now) and ((math.isnan(saved[k]) and math.isnan(now[k])) or saved[k] == now[k]))]
    out = {"cache_hit": s.source.get("cache_hit"), "attempts": s.source.get("attempts"), "retrieved_at": s.source.get("retrieved_at"),
           "months": len(now), "months_different_from_direct_capture": len(diffs), "examples": sorted(diffs)[:5], "requests_made": 1}
    (EVID / "live_project_fetch.json").write_text(json.dumps(out, indent=2, default=str, allow_nan=False), encoding="utf-8")
    return out


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "compare"
    if mode == "capture":
        capture()
    elif mode == "compare":
        print(json.dumps(compare(), indent=2, ensure_ascii=False, default=str)[:9000])
    elif mode == "live-project":
        print(json.dumps(live_project(), indent=2, default=str))
