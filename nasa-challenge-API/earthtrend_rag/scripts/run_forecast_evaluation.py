"""Reproducible multi-location, multi-variable evaluation of the monthly forecasting pipeline (REAL NASA POWER data, cached; no LLM involved).

    .venv\\Scripts\\python.exe scripts\\run_forecast_evaluation.py            # 6 locations x 4 variables, depth=full, 7 processes
Writes evidence/forecast_eval/<location>__<variable>.json (config, windows, data hash, predictions + actuals, metrics, skill, coverage, failures, versions)
and evidence/forecast_eval/SUMMARY.json / SUMMARY.md."""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "evidence" / "forecast_eval"
LOCATIONS = {"Nablus (Mediterranean, semi-arid)": (32.2211, 35.2544), "Cairo (hot desert)": (30.0444, 31.2357), "Riyadh (arid)": (24.7136, 46.6753),
             "London (temperate oceanic)": (51.5074, -0.1278), "Manaus (tropical, humid)": (-3.119, -60.0217), "Sydney (southern hemisphere, subtropical)": (-33.8688, 151.2093)}
VARS = ["air_temperature", "precipitation", "relative_humidity", "wind_speed"]


def slug(s):
    return "".join(c if c.isalnum() else "_" for c in s.split(" (")[0]).lower()


def run_one(args):
    loc, (lat, lon), var = args
    import numpy as np
    from app.data_sources.power import fetch_power_monthly
    from app.forecast import engine as E, evaluation as V, series as S
    t0 = time.time()
    cfg = S.VARIABLES[var]
    ms = fetch_power_monthly(cfg["parameter"], lat, lon, 1981, date.today().year)
    p = S.prepare(ms, var, lat, lon, 1981, date.today().year)
    rec = {"location": loc, "latitude": lat, "longitude": lon, "variable": var, "unit": cfg["unit"], "provenance": p.provenance, "quality": p.quality, "warnings": p.warnings, "data_status": p.status}
    if p.status != "ok":
        rec["message"] = p.message
        return rec
    tf = E.Transform(cfg["transform"])
    rec["structural_break"] = S.structural_break_check(p.y)
    ev = V.evaluate(p.y, tf, "full", E.H_MAX, cfg["pct_ok"])
    if ev["status"] != "ok":
        return {**rec, **ev}
    hold = ev.pop("_hold"); dev = ev.pop("_dev")
    ex = {s: {"holdout_predictions": np.round(hold.models[s]["mean"], 4).tolist(), "holdout_lo95_nominal": np.round(hold.models[s]["lo95"], 4).tolist(), "holdout_hi95_nominal": np.round(hold.models[s]["hi95"], 4).tolist()}
          for s in (ev["selected"], ev["best_baseline"])}
    rec.update(ev)
    rec["holdout_actuals"] = np.round(hold.actual, 4).tolist()
    rec["predictions"] = ex
    rec["config"] = {"transform": cfg["transform"], "min_train_months": E.MIN_TRAIN_MONTHS, "horizon": E.H_MAX, "depth": "full", "bootstrap": "moving-block over forecast origins, 2000 resamples, seed 7",
                     "selection": "lowest mean MAE on development origins only", "ci_level": 0.95}
    rec["runtime_total_s"] = round(time.time() - t0, 1)
    return rec


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(l, c, v) for l, c in LOCATIONS.items() for v in VARS]
    t0 = time.time()
    results = []
    with ProcessPoolExecutor(max_workers=7) as ex:
        for r in ex.map(run_one, jobs):
            (OUT / f"{slug(r['location'])}__{r['variable']}.json").write_text(json.dumps(r, indent=1, default=str, allow_nan=False if False else True), encoding="utf-8")
            results.append(r)
            print(r["location"][:12], r["variable"], r.get("selected"), r.get("best_baseline"), {g: v["status"] for g, v in r.get("skill", {}).items()}, flush=True)
    summ = []
    for r in results:
        if "skill" not in r:
            summ.append({"location": r["location"], "variable": r["variable"], "status": r.get("data_status") if r.get("data_status") != "ok" else r.get("status"), "message": r.get("message")})
            continue
        row = {"location": r["location"], "variable": r["variable"], "unit": r["unit"], "n_months": r["quality"]["n_months"], "cutoff": r["quality"]["cutoff_month"], "selected": r["selected"], "best_baseline": r["best_baseline"],
               "holdout_origins": r["n_holdout_origins"], "dev_origins": r["n_dev_origins"], "holdout_obs": r["holdout_n_obs_total"]}
        for g, s in r["skill"].items():
            b = s["vs_best_baseline"]
            row[f"skill_{g}"] = {"status": s["status"], "ratio_mae_model_over_baseline": b["ratio"], "ci95": [b["lo"], b["hi"]], "mae_selected": s["mae_selected"]}
        m = r["holdout_metrics"][r["selected"]]
        row["selected_mae_by_lead"] = {str(k): round(v, 3) for k, v in zip(m["lead"], m["mae"]) if k in (1, 3, 6, 12, 18, 24) and v is not None}
        row["selected_rmse_by_lead"] = {str(k): round(v, 3) for k, v in zip(m["lead"], m["rmse"]) if k in (1, 3, 6, 12, 18, 24) and v is not None}
        row["selected_bias_by_lead"] = {str(k): round(v, 3) for k, v in zip(m["lead"], m["bias"]) if k in (1, 3, 6, 12, 18, 24) and v is not None}
        bm = r["holdout_metrics"][r["best_baseline"]]
        row["baseline_mae_by_lead"] = {str(k): round(v, 3) for k, v in zip(bm["lead"], bm["mae"]) if k in (1, 3, 6, 12, 18, 24) and v is not None}
        cal = r["interval_assessment"][r["selected"]]
        row["coverage95_holdout"] = {"nominal": {g: v["coverage"] for g, v in cal["nominal_95"].items()}, "calibrated": {g: v["coverage"] for g, v in cal["calibrated_95"].items()}}
        row["coverage80_holdout"] = {"nominal": {g: v["coverage"] for g, v in cal["nominal_80"].items()}, "calibrated": {g: v["coverage"] for g, v in cal["calibrated_80"].items()}}
        row["structural_break"] = r.get("structural_break")
        row["failures"] = {k: v for k, v in r["failures"].items() if v["dev"] or v["holdout"] or v["not_converged_dev"] or v["not_converged_holdout"]}
        summ.append(row)
    (OUT / "SUMMARY.json").write_text(json.dumps({"generated": date.today().isoformat(), "runtime_s": round(time.time() - t0, 1), "rows": summ}, indent=1, default=str), encoding="utf-8")
    print("done in", round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
