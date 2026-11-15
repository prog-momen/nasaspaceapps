"""Trend statistics implemented from the published definitions (numpy + scipy only).

- mann_kendall            Mann (1945) / Kendall (1975), tie-corrected variance, continuity-corrected Z
- seasonal_mann_kendall   Hirsch, Slack & Smith (1982): S and Var(S) summed over seasons
- hamed_rao_variance_factor  Hamed & Rao (1998) autocorrelation correction of Var(S)
- sen_slope               Sen (1968); slopes use the REAL time axis (decimal years), so gaps are respected;
                          seasonal variant pools within-season pairs (Hirsch et al. 1982)
Nothing here knows about NASA or Gemini: it is pure maths on arrays.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats as sps


def _validate_values(x):
    if x.ndim != 1 or len(x) < 2 or not np.isfinite(x).all():
        raise ValueError("statistics require at least two finite values; screen missing data first")


@dataclass
class MKResult:
    S: float
    var_S: float
    z: float
    p_value: float
    tau: float
    n: int
    n_pairs: int
    variance_factor: float = 1.0       # n/n* (1.0 = no autocorrelation correction applied)


def _tie_term(x: np.ndarray) -> float:
    _, counts = np.unique(x, return_counts=True)
    c = counts[counts > 1].astype(float)
    return float(np.sum(c * (c - 1) * (2 * c + 5)))


def _S(x: np.ndarray) -> float:
    n = len(x)
    if n < 2:
        return 0.0
    diff = x[None, :] - x[:, None]
    return float(np.sign(diff)[np.triu_indices(n, k=1)].sum())


def _z_p(S: float, var: float) -> tuple[float, float]:
    if var <= 0:
        return 0.0, 1.0
    z = (S - 1) / np.sqrt(var) if S > 0 else ((S + 1) / np.sqrt(var) if S < 0 else 0.0)
    return float(z), float(2 * sps.norm.sf(abs(z)))


def _tau(S: float, x: np.ndarray) -> float:
    """Kendall's tau-b against a strictly increasing time axis (no ties in time)."""
    n = len(x)
    n0 = n * (n - 1) / 2
    _, counts = np.unique(x, return_counts=True)
    n1 = float(np.sum(counts * (counts - 1) / 2))
    denom = np.sqrt((n0 - n1) * n0)
    return float(S / denom) if denom > 0 else 0.0


def mann_kendall(x) -> MKResult:
    x = np.asarray(x, float)
    _validate_values(x)
    n = len(x)
    S = _S(x)
    var = (n * (n - 1) * (2 * n + 5) - _tie_term(x)) / 18.0 if n >= 2 else 0.0
    z, p = _z_p(S, var)
    return MKResult(S, var, z, p, _tau(S, x), n, n * (n - 1) // 2)


def seasonal_mann_kendall(x, season, min_per_season: int = 3) -> MKResult:
    """x ordered in time; season = integer label (e.g. month 1..12) per value."""
    x, season = np.asarray(x, float), np.asarray(season)
    _validate_values(x)
    if season.shape != x.shape:
        raise ValueError("season/value length mismatch")
    S_tot = var_tot = 0.0
    denom = 0.0
    n_used = pairs = 0
    for s in np.unique(season):
        xs = x[season == s]
        n = len(xs)
        if n < min_per_season:
            continue
        S_tot += _S(xs)
        var_tot += (n * (n - 1) * (2 * n + 5) - _tie_term(xs)) / 18.0
        _, counts = np.unique(xs, return_counts=True)
        n0 = n * (n - 1) / 2
        denom += np.sqrt((n0 - np.sum(counts * (counts - 1) / 2)) * n0)
        n_used += n
        pairs += n * (n - 1) // 2
    z, p = _z_p(S_tot, var_tot)
    return MKResult(S_tot, var_tot, z, p, float(S_tot / denom) if denom > 0 else 0.0, n_used, pairs)


def _acf(v: np.ndarray, max_lag: int) -> np.ndarray:
    v = v - v.mean()
    c0 = np.sum(v * v)
    if c0 == 0:
        return np.zeros(max_lag)
    return np.array([np.sum(v[:-k] * v[k:]) / c0 for k in range(1, max_lag + 1)])


def hamed_rao_variance_factor(x, t, slope: float, alpha: float = 0.05) -> float:
    """n/n*: factor multiplying Var(S). Uses only autocorrelation lags that are significant at `alpha`."""
    x, t = np.asarray(x, float), np.asarray(t, float)
    n = len(x)
    if n < 4:
        return 1.0
    ranks = sps.rankdata(x - slope * t)
    rho = _acf(ranks, n - 1)
    z = sps.norm.isf(alpha / 2)
    hi, lo = (-1 + z * np.sqrt(n - 2)) / (n - 1), (-1 - z * np.sqrt(n - 2)) / (n - 1)
    k = np.arange(1, n)
    mask = (rho > hi) | (rho < lo)
    if not mask.any():
        return 1.0
    s = np.sum((n - k[mask]) * (n - k[mask] - 1) * (n - k[mask] - 2) * rho[mask])
    return float(1 + 2 / (n * (n - 1) * (n - 2)) * s)


def apply_variance_factor(res: MKResult, factor: float) -> MKResult:
    if not np.isfinite(factor) or factor <= 0:
        raise ValueError("non-positive Hamed-Rao variance factor; inference is not supported")
    var = res.var_S * factor
    z, p = _z_p(res.S, var)
    return MKResult(res.S, var, z, p, res.tau, res.n, res.n_pairs, factor)


def _pair_slopes(x, t) -> np.ndarray:
    n = len(x)
    i, j = np.triu_indices(n, k=1)
    dt = t[j] - t[i]
    ok = dt > 0
    return (x[j] - x[i])[ok] / dt[ok]


def _interp_rank(sorted_vals: np.ndarray, rank_1based: float) -> float:
    N = len(sorted_vals)
    r = min(max(rank_1based, 1.0), float(N))
    lo = int(np.floor(r))
    hi = min(lo + 1, N)
    frac = r - lo
    return float(sorted_vals[lo - 1] * (1 - frac) + sorted_vals[hi - 1] * frac)


def sen_slope(x, t, var_S: float, alpha: float = 0.05, season=None) -> dict:
    """Sen's slope in value-units per unit of t (t in decimal years -> units/year) and its (1-alpha) CI.

    `var_S` is the (possibly corrected) variance of S, so the CI is consistent with the test used.
    With `season` given, only within-season pairs are used (seasonal Sen slope).
    """
    x, t = np.asarray(x, float), np.asarray(t, float)
    _validate_values(x)
    if t.shape != x.shape or not np.isfinite(t).all() or np.any(np.diff(t) <= 0):
        raise ValueError("time must be finite, unique and strictly increasing")
    if not 0 < alpha < 1 or not np.isfinite(var_S) or var_S < 0:
        raise ValueError("invalid alpha or variance")
    if season is None:
        slopes = _pair_slopes(x, t)
    else:
        season = np.asarray(season)
        if season.shape != x.shape:
            raise ValueError("season/value length mismatch")
        slopes = np.concatenate([_pair_slopes(x[season == s], t[season == s]) for s in np.unique(season)
                                 if (season == s).sum() >= 2] or [np.array([])])
    if len(slopes) == 0:
        return {"slope": float("nan"), "ci_low": float("nan"), "ci_high": float("nan"), "n_slopes": 0}
    slopes.sort()
    N = len(slopes)
    C = sps.norm.isf(alpha / 2) * np.sqrt(max(var_S, 0.0))
    m1, m2 = (N - C) / 2.0, (N + C) / 2.0
    return {"slope": float(np.median(slopes)),
            "ci_low": _interp_rank(slopes, m1),
            "ci_high": _interp_rank(slopes, m2 + 1),
            "n_slopes": int(N)}


# ---- diagnostics --------------------------------------------------------------------------------

def ljung_box(v: np.ndarray, lags: int) -> tuple[float, float]:
    v = np.asarray(v, float)
    n = len(v)
    lags = max(1, min(lags, n - 2))
    r = _acf(v, lags)
    q = n * (n + 2) * np.sum(r ** 2 / (n - np.arange(1, lags + 1)))
    return float(q), float(sps.chi2.sf(q, lags))


def pairwise_lag_corr(values: np.ndarray, lag: int) -> float:
    """Lag-k correlation on a regular calendar array that may contain NaN (pairs where both exist)."""
    a, b = values[:-lag], values[lag:]
    ok = ~np.isnan(a) & ~np.isnan(b)
    if ok.sum() < 5 or np.std(a[ok]) == 0 or np.std(b[ok]) == 0:
        return float("nan")
    return float(np.corrcoef(a[ok], b[ok])[0, 1])


def seasonality_test(x, season, alpha: float = 0.05) -> dict:
    """Kruskal-Wallis across seasons (+ epsilon-squared effect size)."""
    x, season = np.asarray(x, float), np.asarray(season)
    groups = [x[season == s] for s in np.unique(season) if (season == s).sum() >= 3]
    n = sum(len(g) for g in groups)
    if len(groups) < 3 or n <= len(groups) or np.ptp(x) == 0:
        return {"test": "kruskal_wallis", "applicable": False, "significant": False, "p_value": None, "epsilon_squared": None}
    H, p = sps.kruskal(*groups)
    eps2 = float(max((H - len(groups) + 1) / (n - len(groups)), 0.0))
    return {"test": "kruskal_wallis", "applicable": True, "H": float(H), "p_value": float(p),
            "epsilon_squared": eps2, "significant": bool(p < alpha and eps2 >= 0.05), "n_seasons": len(groups)}
