"""Model selection, holdout validation, skill testing and the final forecast for ONE monthly series.

Chronology (never random splits):
    |---- training history ----|---- development origins (model selection) ----|---- FINAL HOLDOUT origins (judged once) ----| cutoff
Development origins (o + H <= first holdout origin) choose the best advanced model and the best baseline. Holdout origins are only used to report skill,
coverage and errors. Interval calibration offsets come from development errors for the holdout assessment; the production forecast recalibrates on all
backtest errors (declared in the output)."""
from __future__ import annotations

import math
import platform
import time

import numpy as np
import pandas as pd

from app.forecast import engine as E

DEPTHS = {
    "fast": {"dev_n": 6, "dev_step": 12, "hold_n": 5, "hold_step": 12, "advanced": ["sarima_101_011", "ets_aada"]},                      # interactive: ~20 s
    "full": {"dev_n": 18, "dev_step": 12, "hold_n": 13, "hold_step": 6, "advanced": E.ADVANCED},                                        # research evaluation
}
MAX_FAIL_FRACTION = 0.3
MIN_PRACTICAL_GAIN = 0.03       # a model is called 'validated' only if its MAE is >= 3% lower than the best baseline AND the 95% block-bootstrap CI is below 1


def plan_origins(n: int, H: int, depth: dict) -> dict:
    hold = [n - H - depth["hold_step"] * k for k in range(depth["hold_n"])][::-1]
    hold = [o for o in hold if o >= E.MIN_TRAIN_MONTHS + 24]
    if not hold:
        return {"dev": [], "hold": []}
    last_dev = hold[0] - H
    dev = [last_dev - depth["dev_step"] * k for k in range(depth["dev_n"])][::-1]
    dev = [o for o in dev if o >= E.MIN_TRAIN_MONTHS]
    return {"dev": dev, "hold": hold}


def supported_horizon(n: int) -> int:
    """Longest horizon for which BOTH a development and a holdout evaluation with full-length windows are possible with this much history."""
    for H in (24, 18, 12, 6, 3, 1):
        pl = plan_origins(n, H, DEPTHS["fast"])
        if len(pl["dev"]) >= 3 and len(pl["hold"]) >= 3:
            return H
    return 0


def _mean_mae(run: E.OriginRun, name: str) -> float | None:
    e = np.abs(run.models[name]["mean"] - run.actual)
    e = e[np.isfinite(e)]
    return float(e.mean()) if len(e) else None


def _fail_frac(run: E.OriginRun, name: str) -> float:
    return run.models[name]["failed"] / max(1, len(run.origins))


def evaluate(y: pd.Series, tf: E.Transform, depth: str = "fast", H: int = E.H_MAX, pct_ok: bool = False) -> dict:
    t0 = time.time()
    dcfg = DEPTHS[depth]
    pl = plan_origins(len(y), H, dcfg)
    if len(pl["dev"]) < 3 or len(pl["hold"]) < 3:
        return {"status": "insufficient_history", "message": f"{len(y)} months of history do not allow >= 3 development and >= 3 holdout forecast origins at horizon {H}.", "horizon": H, "plan": pl}
    specs = E.BASELINES + list(dcfg["advanced"])
    dev = E.run_origins(y, tf, pl["dev"], specs, H)
    hold = E.run_origins(y, tf, pl["hold"], specs, H)
    # ---- selection on DEVELOPMENT data only ----
    dev_mae = {s: _mean_mae(dev, s) for s in specs}
    adv_ok = [s for s in dcfg["advanced"] if dev_mae[s] is not None and _fail_frac(dev, s) <= MAX_FAIL_FRACTION and _fail_frac(hold, s) <= MAX_FAIL_FRACTION]
    best_base = min(E.BASELINES, key=lambda s: dev_mae[s])
    best_adv = min(adv_ok, key=lambda s: dev_mae[s]) if adv_ok else None
    sel = best_adv or best_base
    scale = E.seasonal_naive_scale(y.values[: pl["hold"][0]])                     # MASE denominator from pre-holdout training data only
    # ---- holdout results (judged once) ----
    metrics = {s: E.lead_metrics(hold.models[s]["mean"], hold.actual, scale) for s in specs}
    off_dev = {s: E.empirical_offsets(dev.models[s]["z_mean"], dev.z_actual) for s in (sel, best_base)}
    block = max(1, math.ceil(H / dcfg["hold_step"]))
    skill = {}
    for g, (lo, hi) in E.GROUPS.items():
        if lo > H:
            continue
        hi = min(hi, H)
        a = E.group_abs_error(hold.models[sel]["mean"], hold.actual, lo, hi)
        row = {}
        for b in specs:
            if b == sel:
                continue
            r = E.block_bootstrap_ratio(a, E.group_abs_error(hold.models[b]["mean"], hold.actual, lo, hi), block)
            row[b] = r
        main = E.block_bootstrap_ratio(a, E.group_abs_error(hold.models[best_base]["mean"], hold.actual, lo, hi), block)
        if sel == best_base:
            status = "baseline_selected"
        elif main["ratio"] is None:
            status = "unavailable"
        elif main["n_origins"] < 5:
            status = "limited_evidence"
        elif main["hi"] < 1.0 and main["ratio"] <= 1.0 - MIN_PRACTICAL_GAIN:
            status = "validated"
        elif main["lo"] > 1.0:
            status = "worse_than_baseline"
        else:
            status = "not_distinguishable_from_baseline"
        skill[g] = {"vs_best_baseline": {**main, "baseline": best_base, "skill": (1 - main["ratio"]) if main["ratio"] is not None else None}, "status": status, "vs_all": row,
                    "mae_selected": float(np.nanmean(a)) if np.isfinite(a).any() else None}
    cal = {}
    for name in (sel, best_base):
        off = off_dev[name]
        zc = hold.models[name]["z_mean"]
        cal_bands = {}
        for key in ("lo80", "hi80", "lo95", "hi95"):
            cal_bands[key] = np.array([[tf.inv(zc[i, k] + off[key][k]) if off[key][k] is not None else np.nan for k in range(H)] for i in range(len(hold.origins))])
        cal[name] = {
            "nominal_80": E.coverage(hold.models[name]["lo80"], hold.models[name]["hi80"], hold.actual), "nominal_95": E.coverage(hold.models[name]["lo95"], hold.models[name]["hi95"], hold.actual),
            "calibrated_80": E.coverage(cal_bands["lo80"], cal_bands["hi80"], hold.actual), "calibrated_95": E.coverage(cal_bands["lo95"], cal_bands["hi95"], hold.actual)}
    pct = None
    if pct_ok:
        pct = {}
        for s in (sel, best_base):
            e = np.abs(hold.models[s]["mean"] - hold.actual)
            ok = np.isfinite(e)
            pct[s] = {"wape_percent": float(100 * e[ok].sum() / np.abs(hold.actual[ok]).sum()), "formula": "WAPE = 100 * sum|forecast - actual| / sum|actual| (robust to near-zero individual months)"}
    return {
        "status": "ok", "horizon": H, "depth": depth, "plan": {k: [int(o) for o in v] for k, v in pl.items()}, "n_dev_origins": len(pl["dev"]), "n_holdout_origins": len(pl["hold"]),
        "origin_dates": {"dev": [str(y.index[o].date()) for o in pl["dev"]], "holdout": [str(y.index[o].date()) for o in pl["hold"]]},
        "specs": specs, "dev_mean_mae": dev_mae, "selected_advanced": best_adv, "best_baseline": best_base, "selected": sel, "mase_scale": scale,
        "holdout_metrics": metrics, "holdout_n_obs_total": int(np.isfinite(hold.actual).sum()), "skill": skill, "interval_assessment": cal, "percentage_errors": pct,
        "failures": {s: {"dev": dev.models[s]["failed"], "holdout": hold.models[s]["failed"], "errors": (dev.models[s]["errors"] + hold.models[s]["errors"])[:5],
                         "not_converged_dev": int((~dev.models[s]["converged"]).sum() - dev.models[s]["failed"]), "not_converged_holdout": int((~hold.models[s]["converged"]).sum() - hold.models[s]["failed"])} for s in specs},
        "_dev": dev, "_hold": hold, "runtime_s": round(time.time() - t0, 1),
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "statsmodels": __import__("statsmodels").__version__, "scipy": __import__("scipy").__version__}}


def final_forecast(y: pd.Series, tf: E.Transform, ev: dict, lead_max: int) -> dict:
    """Refit on ALL data up to the cutoff; headline = selected model on leads whose horizon group is validated, otherwise the best baseline (named).
    Intervals: empirical offsets from ALL backtest errors (dev + holdout) of that method, pooled over neighbouring leads; nominal model bands are also returned."""
    sel, base = ev["selected"], ev["best_baseline"]
    out = {}
    for name in dict.fromkeys([sel, base]):
        r = E.fit_forecast(name, y, tf, lead_max)
        all_z = np.vstack([ev["_dev"].models[name]["z_mean"], ev["_hold"].models[name]["z_mean"]])
        all_a = np.vstack([ev["_dev"].z_actual, ev["_hold"].z_actual])
        off = E.empirical_offsets(all_z, all_a)
        out[name] = {"fit": r, "offsets": off, "empirical": E.apply_offsets(tf, r["z"]["mean"], off) if not r["failed"] else None}
    return out
