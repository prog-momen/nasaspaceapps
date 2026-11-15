"""Validated monthly statistical forecast tool (1-24 months). The language model only calls it and explains its result; it never produces the measurements,
intervals or error estimates. Honest outcomes: validated model forecast | clearly labelled baseline forecast | experimental (only on request) | insufficient
data / validation.

Separate capabilities (never mixed): historical trend detection (app.tools.trend_tool), STATISTICAL monthly forecasting (this module), operational weather
forecasting (Open-Meteo, <= 16 days), long-term climate projections (not implemented)."""
from __future__ import annotations

import hashlib
import json
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from app.config import get_settings
from app.data_sources.power import SourceError, fetch_power_monthly
from app.forecast import engine as E
from app.forecast import evaluation as V
from app.forecast import series as S
from app.providers.base import envelope, strict, validate_point

CODE_VERSION = "forecast-1"
PROVIDER = "NASA POWER + statistical model"
REF_FILE = Path(__file__).resolve().parent.parent.parent / "docs" / "research" / "forecast_references.json"
GROUP_ORDER = ["1-3", "4-6", "7-12", "13-24"]


def references() -> list[dict]:
    try:
        d = json.loads(REF_FILE.read_text(encoding="utf-8"))["references"]
    except Exception:
        return []
    use = {"A", "B", "C", "E", "F"}
    return [{"id": r["id"], "title": r["title"], "authors": r.get("authors"), "year": r.get("year"), "doi": r.get("doi"), "url": r["url"] if isinstance(r["url"], str) else r["url"][0],
             "role": "method reference only (not evidence for any forecast value)", "full_text_read": bool(r.get("full_text_available"))} for r in d if r["id"] in use]


def _group_of(lead: int) -> str:
    return next(g for g, (lo, hi) in E.GROUPS.items() if lo <= lead <= hi)


def _month_diff(a: pd.Timestamp, b: date) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month)


def _cache_path(key: str) -> Path:
    return get_settings().data_dir / "cache" / f"forecast_{key}.json"


def _core(y: pd.Series, cfg: dict, depth: str, H: int, lead_max: int) -> dict:
    """Evaluation + final fits for ONE series. Serializable (cached)."""
    tf = E.Transform(cfg["transform"])
    ev = V.evaluate(y, tf, depth, H, cfg["pct_ok"])
    if ev["status"] != "ok":
        return {"status": ev["status"], "message": ev["message"]}
    fin = V.final_forecast(y, tf, ev, lead_max)
    hold = ev.pop("_hold"); dev = ev.pop("_dev")
    sel, base = ev["selected"], ev["best_baseline"]
    methods = {}
    for name, f in fin.items():
        r = f["fit"]
        methods[name] = {"failed": r["failed"], "error": r.get("error"), "converged": r["converged"], "warnings": r["warnings"][:3], "mean": r["mean"].tolist(),
                         "nominal": {k: r[k].tolist() for k in ("lo80", "hi80", "lo95", "hi95")}, "empirical": ({k: v.tolist() for k, v in f["empirical"].items()} if f["empirical"] else None),
                         "empirical_n_per_lead": f["offsets"]["n"][:lead_max]}
    ev["methods"] = methods
    ev["holdout_actual_n"] = int(np.isfinite(hold.actual).sum())
    ev["dev_n"] = int(np.isfinite(dev.actual).sum())
    return {"status": "ok", "ev": ev}


def _json_safe(o):
    return json.loads(json.dumps(strict(o), default=str))


def forecast_monthly(lat: float, lon: float, variable: str = "air_temperature", months: int = 12, train_start_year: int | None = None, depth: str = "fast",
                     allow_experimental: bool = False, place: str | None = None, today: date | None = None, fetcher=fetch_power_monthly, use_cache: bool = True) -> dict:
    t0 = time.monotonic()
    today = today or date.today()
    name = "Monthly statistical forecast"
    cap = "statistical_forecast"
    if variable not in S.VARIABLES:
        return envelope(PROVIDER, name, cap, "unsupported_request", "VARIABLE_NOT_SUPPORTED", f"Supported variables: {', '.join(S.VARIABLES)}. Others need suitable historical data and a justified method.")
    if not isinstance(months, (int, np.integer)) or not 1 <= int(months) <= E.H_MAX:
        return envelope(PROVIDER, name, cap, "invalid_request", "HORIZON_OUT_OF_RANGE", f"The horizon must be 1 to {E.H_MAX} months; longer requests are not supported (no skill is claimed beyond what is validated).")
    err = validate_point(lat, lon)
    if err:
        return envelope(PROVIDER, name, cap, "invalid_request", "INVALID_POINT", err)
    if depth not in V.DEPTHS:
        return envelope(PROVIDER, name, cap, "invalid_request", "INVALID_DEPTH", f"depth must be one of {list(V.DEPTHS)}")
    months = int(months)
    start_year = max(1981, int(train_start_year)) if train_start_year else 1981
    cfg = S.VARIABLES[variable]
    try:
        ms = fetcher(cfg["parameter"], lat, lon, start_year, today.year)
    except SourceError as e:
        return envelope(PROVIDER, name, cap, "upstream_error", "SOURCE_ERROR", f"NASA POWER did not deliver the data ({e.kind}).")
    p = S.prepare(ms, variable, lat, lon, start_year, today.year, today)
    prov = {**p.provenance, "data_period": f"{p.quality.get('first_month')} .. {p.quality.get('cutoff_month')}" if p.quality else None}
    if p.status == "no_data":
        return envelope(PROVIDER, name, cap, "no_data", "NO_VALID_DATA", p.message, data={"provenance": prov})
    if p.status in ("too_many_missing", "insufficient_history"):
        return envelope(PROVIDER, name, cap, "unsupported_request", "INSUFFICIENT_DATA" if p.status == "insufficient_history" else "TOO_MANY_MISSING", p.message,
                        data={"provenance": prov, "quality": p.quality}, limitations=["No forecast is produced: a validated forecast needs a long, nearly complete monthly record."])
    y = p.y
    if p.quality["constant_series"]:
        return envelope(PROVIDER, name, cap, "unsupported_request", "CONSTANT_SERIES", "The series is constant: there is no variability to forecast and no skill can be measured.", data={"provenance": prov})
    H = V.supported_horizon(len(y))
    if H == 0:
        return envelope(PROVIDER, name, cap, "unsupported_request", "INSUFFICIENT_HISTORY",
                        f"{len(y)} months are not enough to run a chronological validation (>= 3 development and >= 3 holdout origins); no validated forecast can be produced.", data={"provenance": prov, "quality": p.quality})
    cutoff = y.index[-1]
    d = _month_diff(cutoff, today)                                  # months from the cutoff to the current month (lead of the current month)
    # The requested span is counted from TODAY: the current month plus `months` ahead (today + N months falls in that last month).
    # The months between the data cutoff and the current month have no NASA data yet, so they are forecast too and flagged as gap months.
    lead_need = max(1, d + months)
    lead_max = min(H, lead_need)
    truncated = lead_need > lead_max
    key = hashlib.sha256(json.dumps([CODE_VERSION, variable, round(lat, 2), round(lon, 2), str(cutoff.date()), depth, start_year, H, lead_max, prov["values_sha256"]]).encode()).hexdigest()[:24]
    core, cache_state = None, "miss"
    if use_cache and _cache_path(key).exists():
        try:
            core, cache_state = json.loads(_cache_path(key).read_text(encoding="utf-8")), "hit"
        except Exception:
            core = None
    if core is None:
        core = _json_safe(_core(y, cfg, depth, H, lead_max))
        if core["status"] == "ok" and use_cache:
            _cache_path(key).parent.mkdir(parents=True, exist_ok=True)
            _cache_path(key).write_text(json.dumps(core), encoding="utf-8")
    if core["status"] != "ok":
        return envelope(PROVIDER, name, cap, "unsupported_request", "INSUFFICIENT_HISTORY", core["message"], data={"provenance": prov, "quality": p.quality})
    ev = core["ev"]
    tf = E.Transform(cfg["transform"])
    sel, base = ev["selected"], ev["best_baseline"]
    skill = ev["skill"]
    fidx = pd.date_range(cutoff + pd.offsets.MonthBegin(1), periods=lead_max, freq="MS")
    M = ev["methods"]
    rows = []
    for lead in range(1, lead_max + 1):
        g = _group_of(lead)
        st = skill.get(g, {}).get("status", "unavailable")
        use_model = sel != base and st == "validated" and not M[sel]["failed"]
        name_used = sel if use_model else base
        m = M[name_used]
        if m["failed"]:
            rows.append({"lead": lead, "date": str(fidx[lead - 1].date()), "value": None, "method": name_used, "status": "failed"})
            continue
        band = m["nominal"]                                         # model-based (nominal) intervals; their OBSERVED holdout coverage is reported next to them
        cov = ev["interval_assessment"][name_used]["nominal_95"].get(g, {}).get("coverage")
        calib = "unassessed" if cov is None else ("supported (observed 95%-interval coverage 90-99%)" if 0.90 <= cov <= 0.99 else "under-covers (observed coverage below 90%)" if cov < 0.90 else "over-covers (very wide; observed coverage above 99%)")
        basis = "nominal (model-based)"
        v = m["mean"][lead - 1]
        row = {"lead": lead, "date": str(fidx[lead - 1].date()), "value": v, "lo80": band["lo80"][lead - 1], "hi80": band["hi80"][lead - 1], "lo95": band["lo95"][lead - 1], "hi95": band["hi95"][lead - 1],
               "interval_basis": basis, "interval_coverage_95_holdout": cov, "interval_calibration": calib, "method": name_used, "method_label": E.MODEL_LABELS[name_used], "group": g,
               "status": "validated_model" if use_model else "baseline_only", "gap_month_before_today": bool(fidx[lead - 1] < pd.Timestamp(today.year, today.month, 1))}
        if variable == "precipitation":
            dim = fidx[lead - 1].days_in_month
            row["value_monthly_total_mm"] = v * dim
            row["monthly_total_note"] = "derived: mean daily rate x days in month"
        if allow_experimental and not use_model and sel != base and not M[sel]["failed"]:
            row["experimental_model_value"] = M[sel]["mean"][lead - 1]
        rows.append(row)
    n_val = sum(1 for r in rows if r.get("status") == "validated_model")
    overall = "validated_model" if rows and n_val == len(rows) else "partially_validated" if n_val else "baseline_only"
    hm = ev["holdout_metrics"]
    def lead_table(name):
        m = hm[name]
        return [{"lead": k, "n": m["n"][k - 1], "mae": m["mae"][k - 1], "rmse": m["rmse"][k - 1], "bias": m["bias"][k - 1], "mase": m["mase"][k - 1]} for k in range(1, lead_max + 1)]
    head = sel if sel != base else base
    error_estimate = {"unit": cfg["unit"], "basis": f"final chronological holdout: {ev['n_holdout_origins']} forecast origins, {ev['holdout_actual_n']} forecast-actual pairs in total (overlapping windows: not independent)",
                      "selected_model": {"name": head, "label": E.MODEL_LABELS[head], "by_lead": lead_table(head)}, "best_baseline": {"name": base, "label": E.MODEL_LABELS[base], "by_lead": lead_table(base)},
                      "mase_scale": ev["mase_scale"], "percentage_errors": ev["percentage_errors"], "percentage_note": None if cfg["pct_ok"] else "No percentage error is reported for Celsius temperature: its zero is arbitrary, so MAPE is not meaningful; use the errors in degC."}
    if ev["n_holdout_origins"] < 8:
        error_estimate["reliability_note"] = f"Only {ev['n_holdout_origins']} holdout origins in fast mode: the error estimate itself is uncertain. Run the full evaluation for stronger evidence."
    # short forecasts: every month is in the summary the language model may quote; long ones: a sample plus the last month (the full table is always shown)
    summary_leads = rows if len(rows) <= 6 else [r for r in rows if r["lead"] in (1, 3, 6, 12, 18, 24) or r is rows[-1]]
    hist_n = 120
    history = {"x": [str(i.date()) for i in y.index[-hist_n:]], "y": [round(float(v), 4) for v in y.values[-hist_n:]]}
    fc = {"x": [r["date"] for r in rows], "y": [r["value"] for r in rows], "lo80": [r.get("lo80") for r in rows], "hi80": [r.get("hi80") for r in rows], "lo95": [r.get("lo95") for r in rows], "hi95": [r.get("hi95") for r in rows],
          "status": [r["status"] for r in rows], "gap": [bool(r.get("gap_month_before_today")) for r in rows]}
    unit = cfg["unit"]
    arts = [{"type": "forecast_chart", "title": f"{cfg['name']} — history and monthly statistical forecast ({unit})", "unit": unit, "history": history, "forecast": fc, "cutoff": str(cutoff.date()), "issue_date": str(today), "requested_months": months,
             "legend": {"history": "NASA POWER (observed/reanalysis)", "forecast": "statistical forecast", "band80": "80% prediction interval", "band95": "95% prediction interval"}},
            {"type": "table", "title": "Forecast (monthly values)", "columns": ["date", "lead", f"value ({unit})", "80% interval", "95% interval", "method", "status", "interval basis", "observed 95% coverage (holdout)"],
             "rows": [[r["date"], r["lead"], None if r["value"] is None else round(r["value"], 3), None if r.get("lo80") is None else f"{r['lo80']:.2f} .. {r['hi80']:.2f}", None if r.get("lo95") is None else f"{r['lo95']:.2f} .. {r['hi95']:.2f}",
                      r["method_label"] if "method_label" in r else r["method"], r["status"], r.get("interval_basis"), None if r.get("interval_coverage_95_holdout") is None else round(r["interval_coverage_95_holdout"], 2)] for r in rows]},
            {"type": "table", "title": f"Backtest error by lead month (final holdout, {unit})", "columns": ["lead", "n", "MAE selected", "RMSE selected", "bias selected", "MAE baseline", "RMSE baseline"],
             "rows": [[a["lead"], a["n"], None if a["mae"] is None else round(a["mae"], 3), None if a["rmse"] is None else round(a["rmse"], 3), None if a["bias"] is None else round(a["bias"], 3),
                       None if b["mae"] is None else round(b["mae"], 3), None if b["rmse"] is None else round(b["rmse"], 3)] for a, b in zip(error_estimate["selected_model"]["by_lead"], error_estimate["best_baseline"]["by_lead"])]},
            {"type": "table", "title": "Skill versus the best baseline by horizon group (final holdout)", "columns": ["horizon (months)", "status", "MAE ratio model/baseline", "95% CI (block bootstrap over origins)", "origins"],
             "rows": [[g, skill[g]["status"], None if skill[g]["vs_best_baseline"]["ratio"] is None else round(skill[g]["vs_best_baseline"]["ratio"], 3),
                       None if skill[g]["vs_best_baseline"]["lo"] is None else f"{skill[g]['vs_best_baseline']['lo']:.2f} .. {skill[g]['vs_best_baseline']['hi']:.2f}", skill[g]["vs_best_baseline"]["n_origins"]] for g in GROUP_ORDER if g in skill]}]
    lim = ["Statistical monthly forecast, NOT an operational weather forecast and NOT a climate projection: it extends the seasonal cycle and recent behaviour of one reanalysis grid cell.",
           "Forecasts monthly means only; it says nothing about individual days, extremes, daily rain probability or wildfire.",
           "Intervals describe uncertainty of a future monthly value; they are not uncertainty of model parameters. They are the models' nominal intervals: a 95% interval is called calibrated only where its observed holdout coverage (shown per horizon) is 90-99%; empirical recalibration from development errors did not transfer to the holdout in the multi-location evaluation (see evidence/forecast_eval), so it is not used.",
           "Unusual anomalies are not predictable at these horizons: a good fit to the seasonal cycle alone does not show anomaly skill - compare with the climatology baseline."]
    if truncated:
        lim.append(f"Requested coverage ({months} months from the current month) would need {lead_need} months after the data cutoff; the forecast is limited to {lead_max} months after the cutoff ({fidx[-1].strftime('%Y-%m')}).")
    if H < E.H_MAX:
        lim.append(f"With {len(y)} months of history the longest validated horizon is {H} months.")
    if overall != "validated_model":
        lim.append("Where the selected model has not been shown to beat the best baseline, the forecast shown is that baseline under its real name; additional predictive skill has not been established.")
    if ev["n_holdout_origins"] < 8:
        lim.append("Fast mode uses few holdout origins; skill statements are limited-evidence.")
    brk = S.structural_break_check(y)
    if brk["flag"]:
        lim.append(f"The record shows a mean shift between its two halves ({brk['mean_shift_between_halves']:.2f} {unit}); trend extrapolation may not hold. {brk['note']}")
    lim += p.warnings
    gap_rows = [r["date"] for r in rows if r.get("gap_month_before_today")]
    req_rows = [r["date"] for r in rows if not r.get("gap_month_before_today")]
    cut_txt = f" (shortened: the longest supported span is {lead_max} months after the last data month)" if truncated else ""
    if gap_rows and req_rows:
        gap_note = (f"Asked: {months} month(s) from today ({today}). Forecast covers {req_rows[0][:7]} to {req_rows[-1][:7]}{cut_txt}. NASA data end {cutoff.strftime('%Y-%m')}, so the {len(gap_rows)} missing month(s) before today "
                    f"({', '.join(g[:7] for g in gap_rows)}) are forecast as well and marked as gap months.")
    elif req_rows:
        gap_note = f"Asked: {months} month(s) from today ({today}). Forecast covers {req_rows[0][:7]} to {req_rows[-1][:7]}{cut_txt}."
    else:
        gap_note = "Forecast months start right after the data cutoff."
    cutoff_gap = {"data_cutoff_month": str(cutoff.date()), "issue_date": str(today), "first_forecast_month": rows[0]["date"], "last_forecast_month": rows[-1]["date"], "months_between_cutoff_and_current_month": d,
                  "requested_months": months, "requested_first_month": req_rows[0] if req_rows else None, "requested_last_month": req_rows[-1] if req_rows else None, "gap_months": gap_rows, "note": gap_note}
    summary = {"status": "ok", "variable": cfg["name"], "unit": unit, "overall_validation": overall, "selected_model": E.MODEL_LABELS[sel], "baseline": E.MODEL_LABELS[base], "cutoff": cutoff_gap, "n_months": len(y),
               "horizon_months": lead_max, "prediction_interval_levels": [0.8, 0.95], "horizon_groups_months": ["1-3", "4-6", "7-12", "13-24"], "leads": [{"lead": r["lead"], "date": r["date"], "value": _r2(r["value"]), "lo80": _r2(r.get("lo80")), "hi80": _r2(r.get("hi80")), "lo95": _r2(r.get("lo95")), "hi95": _r2(r.get("hi95")), "status": r["status"]} for r in summary_leads],
               "mae_by_group": {g: _group_mae(error_estimate["selected_model" if (overall != "baseline_only") else "best_baseline"]["by_lead"], g, lead_max) for g in GROUP_ORDER if int(g.split("-")[0]) <= lead_max},
               "baseline_mae_by_group": {g: _group_mae(error_estimate["best_baseline"]["by_lead"], g, lead_max) for g in GROUP_ORDER if int(g.split("-")[0]) <= lead_max},
               "skill_status": {g: skill[g]["status"] for g in GROUP_ORDER if g in skill}, "n_holdout_origins": ev["n_holdout_origins"], "n_dev_origins": ev["n_dev_origins"], "interval_basis": rows[0].get("interval_basis"), "interval_calibration_by_group": {r["group"]: r.get("interval_calibration") for r in rows if r.get("group")},
               "coverage95_holdout_empirically_recalibrated(not used)": {g: v["coverage"] for g, v in ev["interval_assessment"][head]["calibrated_95"].items()}, "coverage95_holdout_nominal": {g: v["coverage"] for g, v in ev["interval_assessment"][head]["nominal_95"].items()},
               "limitations": lim[:4]}
    return strict(envelope(
        PROVIDER, f"{name} ({E.MODEL_LABELS[head]})", cap, "ok", variables=[variable], units={"value": unit}, request={"latitude": lat, "longitude": lon, "variable": variable, "months": months, "depth": depth, "place": place},
        actual={"data_cutoff_month": str(cutoff.date()), "period": {"first": rows[0]["date"], "last": rows[-1]["date"]}, "lead_months": lead_max}, temporal_resolution="monthly", live=cache_state == "miss" and not prov.get("cache_hit"),
        cache=cache_state, retrieved_at=prov.get("retrieved_at"), duration_ms=int((time.monotonic() - t0) * 1000), source_links=["https://power.larc.nasa.gov/docs/services/api/temporal/monthly/", "https://www.statsmodels.org/stable/index.html"],
        attribution="NASA POWER (MERRA-2) data; statistical model run by EarthTrend Explorer", license="NASA open data",
        quality={**p.quality, "structural_break": brk, "evaluation_depth": depth}, limitations=lim,
        data={"provenance": prov, "forecast": rows, "history_tail": history, "validation": {"overall": overall, "skill_by_group": {g: {k: v for k, v in s.items() if k != "vs_all"} for g, s in skill.items()},
              "interval_assessment": ev["interval_assessment"][head], "origin_dates": ev["origin_dates"], "dev_mean_mae": ev["dev_mean_mae"], "selected_advanced": ev["selected_advanced"], "best_baseline": base, "failures": ev["failures"],
              "environment": ev["environment"], "plan": {"dev_origins": ev["n_dev_origins"], "holdout_origins": ev["n_holdout_origins"], "horizon": H}},
              "error_estimate": error_estimate, "cutoff": cutoff_gap, "references": references(), "summary": summary},
        artifacts=arts))


def _r2(x):
    return None if x is None else round(float(x), 2)


def _group_mae(by_lead: list[dict], g: str, lead_max: int):
    lo, hi = E.GROUPS[g]
    v = [r["mae"] for r in by_lead if lo <= r["lead"] <= min(hi, lead_max) and r["mae"] is not None]
    return round(float(np.mean(v)), 2) if v else None
