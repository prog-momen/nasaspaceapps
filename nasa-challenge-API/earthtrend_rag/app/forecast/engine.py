"""Monthly statistical forecasting engine: candidate models, chronological rolling-origin backtesting, error metrics, interval calibration and
skill testing against NAMED baselines.

Scientific rules enforced here (tests in tests/test_forecast_engine.py)
* Everything that is estimated (model parameters, climatologies, trend, seasonal differences, interval calibration) is estimated from data BEFORE the forecast
  origin only. A final chronological holdout is never used for model selection or calibration.
* Models are compared with baselines under their real names: seasonal naive, monthly climatology, climatology + linear trend. A model that does not beat the
  best baseline is reported as such; skill is judged with a moving-block bootstrap over forecast origins (overlapping windows are dependent).
* Variables with physical bounds are modelled in a transformed space (sqrt: precipitation >= 0, log: wind > 0, logit: relative humidity in (0,100)) so
  forecasts and intervals respect the bounds by construction - no silent clipping of results.
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

H_MAX = 24
MIN_TRAIN_MONTHS = 120            # >= 10 complete seasonal cycles are needed to estimate a seasonal model at all
Z = {0.8: 1.2815515655446004, 0.95: 1.959963984540054}
BASELINES = ["snaive", "clim", "clim_trend"]
ADVANCED = ["sarima_101_011", "sarima_011_011", "sarima_200_100_ct", "ets_aada", "ets_ana"]
MODEL_LABELS = {
    "snaive": "Seasonal naive (same month last year)", "clim": "Monthly climatology (training mean per calendar month)",
    "clim_trend": "Monthly climatology + linear trend", "sarima_101_011": "SARIMA(1,0,1)(0,1,1)12", "sarima_011_011": "SARIMA(0,1,1)(0,1,1)12 (airline model)",
    "sarima_200_100_ct": "SARIMAX(2,0,0)(1,0,0)12 + linear trend", "ets_aada": "ETS(A,Ad,A) damped-trend Holt-Winters", "ets_ana": "ETS(A,N,A) seasonal Holt-Winters without trend"}


# ---- transforms (parameter-free, so nothing is 'fitted' on future data) -----------------------------------------------------------------------
class Transform:
    def __init__(self, kind: str):
        self.kind = kind

    def fwd(self, x):
        x = np.asarray(x, float)
        if self.kind == "identity":
            return x
        if self.kind == "sqrt":
            return np.sqrt(np.maximum(x, 0.0))
        if self.kind == "log":
            return np.log(np.maximum(x, 1e-3))
        if self.kind == "logit100":
            p = np.clip(x / 100.0, 0.005, 0.995)
            return np.log(p / (1 - p))
        raise ValueError(self.kind)

    def inv(self, z):
        z = np.asarray(z, float)
        if self.kind == "identity":
            return z
        if self.kind == "sqrt":
            return np.square(np.maximum(z, 0.0))
        if self.kind == "log":
            return np.exp(z)
        if self.kind == "logit100":
            return 100.0 / (1.0 + np.exp(-z))
        raise ValueError(self.kind)


def month_index(start: pd.Timestamp, n: int) -> pd.DatetimeIndex:
    return pd.date_range(start, periods=n, freq="MS")


# ---- candidate models: fit on the training Series (transformed space) -> mean + quantile bands for leads 1..h -----------------------------------
def _bands(mean, se, extra=None):
    out = {"mean": np.asarray(mean, float)}
    for lvl, z in Z.items():
        k = int(round((1 - lvl) * 100))
        out[f"lo{int(lvl*100)}"] = out["mean"] - z * se
        out[f"hi{int(lvl*100)}"] = out["mean"] + z * se
    return out


def f_snaive(zs: pd.Series, h: int) -> dict:
    z = zs.values
    sd = float(np.std(z[12:] - z[:-12], ddof=1))
    mean = np.array([z[len(z) - 12 + (k % 12)] for k in range(h)])
    se = sd * np.sqrt(np.array([k // 12 + 1 for k in range(h)]))                   # Hyndman & Athanasopoulos: var_h = sigma^2 (floor((h-1)/m) + 1)
    return {**_bands(mean, se), "converged": True, "warnings": []}


def f_clim(zs: pd.Series, h: int) -> dict:
    m = zs.index.month.values
    clim = np.array([zs.values[m == k].mean() for k in range(1, 13)])
    resid = zs.values - clim[m - 1]
    sd = float(np.std(resid, ddof=12))
    fut = month_index(zs.index[-1] + pd.offsets.MonthBegin(1), h)
    nyrs = len(zs) / 12
    mean = clim[fut.month.values - 1]
    return {**_bands(mean, np.full(h, sd * math.sqrt(1 + 1 / nyrs))), "converged": True, "warnings": []}


def f_clim_trend(zs: pd.Series, h: int) -> dict:
    import statsmodels.api as sm
    n = len(zs)
    def design(idx, t):
        d = np.zeros((len(idx), 13))
        d[np.arange(len(idx)), idx.month.values - 1] = 1.0
        d[:, 12] = t
        return d
    t0 = np.arange(n) / 120.0                                                      # decades since the first training month
    fit = sm.OLS(zs.values, design(zs.index, t0)).fit()
    fut = month_index(zs.index[-1] + pd.offsets.MonthBegin(1), h)
    Xf = design(fut, (n + np.arange(h)) / 120.0)
    pr = fit.get_prediction(Xf)
    out = {"mean": np.asarray(pr.predicted_mean)}
    for lvl in (0.8, 0.95):
        sf = pr.summary_frame(alpha=1 - lvl)                                         # observation intervals: parameter + residual uncertainty (iid residuals assumed)
        out[f"lo{int(lvl*100)}"], out[f"hi{int(lvl*100)}"] = sf["obs_ci_lower"].values, sf["obs_ci_upper"].values
    return {**out, "converged": True, "warnings": [], "trend_per_decade_transformed": float(fit.params[12])}


def f_ets(zs: pd.Series, h: int, trend: bool) -> dict:
    from statsmodels.tsa.exponential_smoothing.ets import ETSModel
    w: list[str] = []
    with warnings.catch_warnings(record=True) as cw:
        warnings.simplefilter("always")
        mod = ETSModel(zs, error="add", trend="add" if trend else None, damped_trend=trend, seasonal="add", seasonal_periods=12)
        res = mod.fit(disp=False, maxiter=200)
        conv = bool(getattr(res, "mle_retvals", None) is None or getattr(res.mle_retvals, "converged", True))
        w += [str(x.message)[:120] for x in cw]
    pr = res.get_prediction(start=len(zs), end=len(zs) + h - 1)
    out = {"mean": np.asarray(pr.predicted_mean)}
    for lvl in (0.8, 0.95):
        sf = pr.summary_frame(alpha=1 - lvl)
        out[f"lo{int(lvl*100)}"], out[f"hi{int(lvl*100)}"] = sf["pi_lower"].values, sf["pi_upper"].values
    if not np.isfinite(out["mean"]).all():
        raise FloatingPointError("non-finite ETS forecast")
    return {**out, "converged": conv, "warnings": w}


def f_sarima(zs: pd.Series, h: int, order, seasonal, trend) -> dict:
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    w: list[str] = []
    with warnings.catch_warnings(record=True) as cw:
        warnings.simplefilter("always")
        mod = SARIMAX(zs, order=order, seasonal_order=seasonal, trend=trend, enforce_stationarity=False, enforce_invertibility=False)
        res = mod.fit(disp=False, maxiter=100)
        conv = bool(res.mle_retvals.get("converged", True)) if hasattr(res, "mle_retvals") and res.mle_retvals else True
        w += [str(x.message)[:120] for x in cw]
    fc = res.get_forecast(h)
    out = {"mean": np.asarray(fc.predicted_mean)}
    for lvl in (0.8, 0.95):
        ci = np.asarray(fc.conf_int(alpha=1 - lvl))
        out[f"lo{int(lvl*100)}"], out[f"hi{int(lvl*100)}"] = ci[:, 0], ci[:, 1]
    if not np.isfinite(out["mean"]).all() or not np.isfinite(out["lo95"]).all():
        raise FloatingPointError("non-finite SARIMA forecast")
    return {**out, "converged": conv, "warnings": w}


SPECS = {
    "snaive": lambda z, h: f_snaive(z, h), "clim": lambda z, h: f_clim(z, h), "clim_trend": lambda z, h: f_clim_trend(z, h),
    "sarima_101_011": lambda z, h: f_sarima(z, h, (1, 0, 1), (0, 1, 1, 12), None),
    "sarima_011_011": lambda z, h: f_sarima(z, h, (0, 1, 1), (0, 1, 1, 12), None),
    "sarima_200_100_ct": lambda z, h: f_sarima(z, h, (2, 0, 0), (1, 0, 0, 12), "ct"),
    "ets_aada": lambda z, h: f_ets(z, h, True), "ets_ana": lambda z, h: f_ets(z, h, False),
}


def fit_forecast(name: str, y: pd.Series, tf: Transform, h: int) -> dict:
    """Fit on `y` (physical units, regular monthly index, no NaN) and forecast h months. Returns arrays in transformed AND physical space. A failure never
    falls back silently to another model: it is returned as converged=False / failed=True with the reason."""
    zs = pd.Series(tf.fwd(y.values), index=y.index)
    try:
        r = SPECS[name](zs, h)
    except Exception as e:                                                         # convergence / numerical failure is data, not an exception to hide
        nan = np.full(h, np.nan)
        return {"failed": True, "error": f"{type(e).__name__}: {str(e)[:120]}", "converged": False, "warnings": [], "z": {k: nan for k in ("mean", "lo80", "hi80", "lo95", "hi95")},
                **{k: nan for k in ("mean", "lo80", "hi80", "lo95", "hi95")}}
    phys = {k: tf.inv(r[k]) for k in ("mean", "lo80", "hi80", "lo95", "hi95")}
    return {"failed": False, "converged": r["converged"], "warnings": r["warnings"], "z": {k: r[k] for k in ("mean", "lo80", "hi80", "lo95", "hi95")}, **phys}


# ---- rolling-origin backtest ------------------------------------------------------------------------------------------------------------
@dataclass
class OriginRun:
    origins: list[int]
    actual: np.ndarray                  # [n_orig, H] physical units, NaN beyond the end of data
    z_actual: np.ndarray
    models: dict                        # name -> {"mean","lo80","hi80","lo95","hi95": [n_orig,H], "z_mean": [n_orig,H], "converged": [n_orig], "failed": int}


def run_origins(y: pd.Series, tf: Transform, origins: list[int], specs: list[str], H: int = H_MAX) -> OriginRun:
    """Chronological: for each origin o the models see y[:o] ONLY and forecast y[o:o+H]."""
    n, no = len(y), len(origins)
    yv, zv = y.values.astype(float), tf.fwd(y.values)
    actual, zact = np.full((no, H), np.nan), np.full((no, H), np.nan)
    for i, o in enumerate(origins):
        k = min(H, n - o)
        actual[i, :k], zact[i, :k] = yv[o:o + k], zv[o:o + k]
    models = {s: {k: np.full((no, H), np.nan) for k in ("mean", "lo80", "hi80", "lo95", "hi95", "z_mean")} | {"converged": np.zeros(no, bool), "failed": 0, "errors": []} for s in specs}
    for i, o in enumerate(origins):
        train = y.iloc[:o]
        for s in specs:
            r = fit_forecast(s, train, tf, H)
            m = models[s]
            for k in ("mean", "lo80", "hi80", "lo95", "hi95"):
                m[k][i] = r[k]
            m["z_mean"][i] = r["z"]["mean"]
            m["converged"][i] = r["converged"]
            if r["failed"]:
                m["failed"] += 1
                m["errors"].append({"origin": int(o), "error": r["error"]})
    return OriginRun(origins, actual, zact, models)


def lead_metrics(pred: np.ndarray, actual: np.ndarray, scale: float | None = None) -> dict:
    """Per-lead MAE, RMSE, mean error (bias = forecast - actual), n, and MASE where the seasonal-naive scale is valid (> 0)."""
    err = pred - actual
    H = err.shape[1]
    out = {"lead": list(range(1, H + 1)), "n": [], "mae": [], "rmse": [], "bias": [], "mase": []}
    for k in range(H):
        e = err[:, k][np.isfinite(err[:, k])]
        out["n"].append(int(len(e)))
        out["mae"].append(float(np.mean(np.abs(e))) if len(e) else None)
        out["rmse"].append(float(np.sqrt(np.mean(e ** 2))) if len(e) else None)
        out["bias"].append(float(np.mean(e)) if len(e) else None)
        out["mase"].append(float(np.mean(np.abs(e)) / scale) if (len(e) and scale and scale > 1e-9) else None)
    return out


def seasonal_naive_scale(y_train: np.ndarray) -> float | None:
    d = np.abs(y_train[12:] - y_train[:-12])
    s = float(np.mean(d)) if len(d) else None
    return s if (s is not None and s > 1e-9) else None


GROUPS = {"1-3": (1, 3), "4-6": (4, 6), "7-12": (7, 12), "13-24": (13, 24)}


def group_abs_error(pred, actual, lo, hi):
    e = np.abs(pred[:, lo - 1:hi] - actual[:, lo - 1:hi])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.where(np.isfinite(e).any(axis=1), np.nanmean(np.where(np.isfinite(e), e, np.nan), axis=1), np.nan)


def block_bootstrap_ratio(a: np.ndarray, b: np.ndarray, block: int, n_boot: int = 2000, seed: int = 7) -> dict:
    """Moving-block bootstrap over forecast ORIGINS of mean(a)/mean(b) (a = candidate MAE per origin, b = baseline MAE). Overlapping forecast windows make
    neighbouring origins dependent, so origins are resampled in blocks of `block` consecutive origins."""
    ok = np.isfinite(a) & np.isfinite(b)
    a, b = a[ok], b[ok]
    n = len(a)
    if n < 3 or np.mean(b) <= 1e-12:
        return {"ratio": None, "lo": None, "hi": None, "n_origins": int(n)}
    block = max(1, min(block, n))
    rng = np.random.default_rng(seed)
    nb = int(math.ceil(n / block))
    starts = np.arange(n - block + 1)
    rs = []
    for _ in range(n_boot):
        idx = np.concatenate([np.arange(s, s + block) for s in rng.choice(starts, nb)])[:n]
        rs.append(a[idx].mean() / max(b[idx].mean(), 1e-12))
    return {"ratio": float(a.mean() / b.mean()), "lo": float(np.percentile(rs, 2.5)), "hi": float(np.percentile(rs, 97.5)), "n_origins": int(n)}


def coverage(pred_lo, pred_hi, actual) -> dict:
    out = {}
    for g, (lo, hi) in GROUPS.items():
        a = actual[:, lo - 1:hi]; l = pred_lo[:, lo - 1:hi]; u = pred_hi[:, lo - 1:hi]
        ok = np.isfinite(a) & np.isfinite(l) & np.isfinite(u)
        out[g] = {"coverage": float(np.mean((a[ok] >= l[ok]) & (a[ok] <= u[ok]))) if ok.sum() else None, "mean_width": float(np.mean((u - l)[ok])) if ok.sum() else None, "n": int(ok.sum())}
    return out


def empirical_offsets(z_pred: np.ndarray, z_actual: np.ndarray, pool: int = 1) -> dict:
    """Interval calibration from BACKTEST errors (transformed space, per lead, pooled over +-`pool` neighbouring leads to get enough samples):
    returns quantile offsets q[level][lead] so that  band = z_forecast + offset  (no bound can be violated after back-transformation)."""
    err = z_actual - z_pred                                              # actual - forecast
    H = err.shape[1]
    out = {"lo80": [], "hi80": [], "lo95": [], "hi95": [], "n": []}
    for k in range(H):
        sl = err[:, max(0, k - pool):k + pool + 1].ravel()
        sl = sl[np.isfinite(sl)]
        out["n"].append(int(len(sl)))
        for key, q in (("lo80", 10), ("hi80", 90), ("lo95", 2.5), ("hi95", 97.5)):
            out[key].append(float(np.percentile(sl, q)) if len(sl) >= 8 else None)
    return out


def apply_offsets(tf: Transform, z_mean: np.ndarray, off: dict) -> dict | None:
    if any(v is None for key in ("lo80", "hi80", "lo95", "hi95") for v in off[key][:len(z_mean)]):
        return None
    h = len(z_mean)
    return {key: tf.inv(z_mean + np.array(off[key][:h])) for key in ("lo80", "hi80", "lo95", "hi95")}
