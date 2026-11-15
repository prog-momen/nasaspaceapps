"""Trend analysis of a monthly series: quality report -> diagnostics -> Mann-Kendall (+ Sen's slope) -> structured result.

Method selection (monthly input; every decision and its reason is returned in `method_selection`):
  1. Seasonality: Kruskal-Wallis across calendar months (+ effect size).
  2. Autocorrelation of the deseasonalised monthly series: Ljung-Box.
  3. seasonal & no significant autocorrelation  -> Seasonal Mann-Kendall (Hirsch et al. 1982), seasonal Sen slope.
     otherwise (autocorrelated, or not enough data per season) -> annual means (declared rule) then Mann-Kendall with the
     Hamed & Rao (1998) variance correction. Annual means are NOT assumed to remove autocorrelation: it is re-tested
     on the annual series and the correction is applied from the lags that are actually significant.
  The alternative variants are also computed and returned under `sensitivity`.
Insufficient / unsuitable data returns a status with a reason code instead of a verdict. No gap filling is done.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

from app.analysis import stats as st
from app.analysis.timeseries import MonthlySeries, ScreenedSeries, annual_aggregate, longest_gap, screen

DEFAULT_ALPHA = 0.05

PHRASES = {
    "not_significant": {
        "ar": "البيانات الحالية لا تكفي لتأكيد وجود اتجاه",
        "en": "The available data are not sufficient to confirm a trend",
    },
}

CAVEATS = {
    "ar": [
        "الاختبار يقيّم الاتجاه التاريخي في الفترة والبيانات المذكورة فقط؛ لا يثبت سبب التغيّر ولا يقدّم توقعًا مستقبليًا (التنبؤ مسار منفصل).",
        "قيمة p هي احتمال ملاحظة اتجاه بهذه القوة أو أكبر لو لم يكن هناك اتجاه فعلي؛ وليست احتمال صحة النتيجة ولا نسبة ثقة.",
        "عدم الدلالة الإحصائية لا يعني عدم وجود تغيّر؛ يعني أن البيانات الحالية لا تكفي لتأكيده.",
    ],
    "en": [
        "The test describes the historical trend over the stated period and data only; it does not establish a cause and is not a forecast.",
        "The p-value is the probability of seeing a trend this strong or stronger if there were no real trend; it is not the probability that the result is correct, nor a confidence level.",
        "A non-significant result does not mean there is no change; it means the current data cannot confirm one.",
    ],
}


def _r(x, nd=4):
    return None if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))) else round(float(x), nd)


def _p_fmt(p: float) -> float:
    return round(p, 4) if p >= 0.0001 else float(f"{p:.2e}")


def _insufficient(reason: str, message: str, base: dict, detail: dict | None = None) -> dict:
    return {**base, "status": "insufficient_data", "reason_code": reason, "message": message, **(detail or {}),
            "caveats": CAVEATS["ar"], "caveats_en": CAVEATS["en"]}


def _interpret(direction: str, significant: bool, alpha: float, slope: float, unit: str, test: str, p: float) -> dict:
    d_ar = {"increasing": "تصاعدي", "decreasing": "تنازلي", "flat": "مستقر"}[direction]
    d_en = direction
    if significant:
        code = "SIGNIFICANT_INCREASE" if direction == "increasing" else "SIGNIFICANT_DECREASE"
        ar = (f"رُصد اتجاه {d_ar} ذو دلالة إحصائية عند مستوى {alpha} (اختبار {test}، p = {_p_fmt(p)}). "
              f"تقدير معدل التغيّر (Sen's slope) = {_r(slope)} {unit}.")
        en = (f"A statistically significant {d_en} trend was detected at the {alpha} level ({test}, p = {_p_fmt(p)}). "
              f"Sen's slope estimate = {_r(slope)} {unit}.")
    else:
        code = "NOT_SIGNIFICANT"
        ar = (f"{PHRASES['not_significant']['ar']} (اختبار {test}، p = {_p_fmt(p)} وعتبة الدلالة {alpha}). "
              f"الاتجاه التقديري {d_ar} وبمعدل Sen's slope = {_r(slope)} {unit}، لكنه غير مؤكد إحصائيًا.")
        en = (f"{PHRASES['not_significant']['en']} ({test}, p = {_p_fmt(p)}, significance threshold {alpha}). "
              f"The estimated direction is {d_en} with Sen's slope = {_r(slope)} {unit}, but it is not statistically confirmed.")
    return {"code": code, "text_ar": ar, "text_en": en}


def _mk_block(res: st.MKResult, sen: dict, alpha: float, unit_per_year: str, name: str, n_label: str, n_used: int) -> dict:
    sig = bool(res.p_value < alpha)
    direction = "flat" if sen["slope"] == 0 or math.isnan(sen["slope"]) else ("increasing" if sen["slope"] > 0 else "decreasing")
    return {
        "test_name": name, "n_used": n_used, "n_unit": n_label, "S": _r(res.S, 1), "var_S": _r(res.var_S, 3),
        "z": _r(res.z), "kendall_tau": _r(res.tau), "p_value": _p_fmt(res.p_value), "alpha": alpha,
        "significant": sig, "tails": "two-sided", "variance_correction_factor": _r(res.variance_factor),
        "direction": direction,
        "sen_slope": {"value": _r(sen["slope"], 5), "unit": unit_per_year, "ci_low": _r(sen["ci_low"], 5),
                      "ci_high": _r(sen["ci_high"], 5), "ci_level": 1 - alpha, "n_pair_slopes": sen["n_slopes"]},
    }


def _run_annual(s: ScreenedSeries, ann: dict, alpha: float) -> tuple[dict, dict]:
    x, t = ann["value"], ann["t"]
    base = st.mann_kendall(x)
    sen0 = st.sen_slope(x, t, base.var_S, alpha)
    factor = st.hamed_rao_variance_factor(x, t, sen0["slope"], alpha)
    res = st.apply_variance_factor(base, factor)
    sen = st.sen_slope(x, t, res.var_S, alpha)
    name = "Mann-Kendall + Hamed-Rao (1998) variance correction" if abs(factor - 1.0) > 1e-9 else "Mann-Kendall (original)"
    block = _mk_block(res, sen, alpha, f"{s.units}/year", name, "annual means", len(x))
    # annual autocorrelation re-check (not assumed away by averaging)
    detr = x - sen0["slope"] * t
    q, p = st.ljung_box(detr, min(5, max(1, len(x) // 4))) if len(x) >= 8 else (float("nan"), float("nan"))
    r1 = st.pairwise_lag_corr(detr, 1) if len(x) >= 6 else float("nan")
    diag = {"series": "annual means (detrended by Sen slope)", "lag1_autocorrelation": _r(r1),
            "ljung_box_p": _r(p), "significant_autocorrelation": bool(not math.isnan(p) and p < alpha),
            "hamed_rao_factor_applied": _r(factor)}
    return block, diag


def _run_seasonal(s: ScreenedSeries, alpha: float) -> dict:
    ok = s.category == "valid"
    x, month, t = s.value[ok], s.month[ok], s.t[ok]
    res = st.seasonal_mann_kendall(x, month)
    sen = st.sen_slope(x, t, res.var_S, alpha, season=month)
    return _mk_block(res, sen, alpha, f"{s.units}/year", "Seasonal Mann-Kendall (Hirsch, Slack & Smith 1982)",
                     "monthly readings", res.n)


def _chart(s: ScreenedSeries, ann: dict, primary: dict, aggregation: str, variable_name: str, source: dict) -> dict:
    sen = primary["sen_slope"]["value"]
    if aggregation == "annual":
        x, t = ann["value"], ann["t"]
        xs = [str(int(round(v))) for v in ann["year"]]
        mode = "annual means"
    else:
        ok = s.category == "valid"
        x, t = s.value[ok], s.t[ok]
        xs = [f"{int(y)}-{int(m):02d}" for y, m in zip(s.year[ok], s.month[ok])]
        mode = "monthly values"
    icpt = float(np.median(x - sen * t)) if sen is not None else None
    line = None
    if icpt is not None:
        t0, t1 = float(t.min()), float(t.max())
        line = {"t": [round(t0, 3), round(t1, 3)], "y": [round(icpt + sen * t0, 4), round(icpt + sen * t1, 4)]}
    return {
        "library": "plotly", "type": "scatter", "title": f"{variable_name} — {mode}",
        "x_labels": xs, "t_decimal_year": [round(float(v), 3) for v in t], "y": [round(float(v), 4) for v in x],
        "y_unit": s.units, "sen_line": line, "sen_line_note": "Sen's slope line (historical estimate, not a forecast)",
        "missing_months_not_drawn": int(s.counts["missing"] + s.counts["invalid"]),
        "source_caption": f"{source.get('provider', '')} {source.get('dataset', '')}".strip(),
    }


def analyze_series(series: MonthlySeries, *, variable: dict, region: dict, start_year: int, end_year: int,
                   alpha: float = DEFAULT_ALPHA, min_years: int = 10, min_months_per_year: int = 9,
                   min_coverage: float = 0.6, aggregation: str = "auto",
                   fill_values=(), valid_range=None, valid_flags=None, flag_predicate=None) -> dict:
    """aggregation: 'auto' (diagnostic-driven), 'annual' or 'monthly_seasonal' (forced; diagnostics still reported)."""
    s = screen(series, start_year, end_year, fill_values, valid_range, valid_flags, flag_predicate)
    ann = annual_aggregate(s, min_months_per_year)
    vcount = s.counts["valid"]
    dq = {
        "expected_months": s.expected, "valid_months": vcount, "missing_months": s.counts["missing"],
        "invalid_months": s.counts["invalid"], "invalid_reasons": s.invalid_reasons,
        "fetch_error_months": series.fetch_errors, "coverage_fraction": _r(vcount / s.expected if s.expected else 0.0),
        "longest_gap_months": longest_gap(s.category), "years_used": [int(v) for v in ann["year"]],
        "years_dropped": ann["dropped"], "min_months_per_year": min_months_per_year,
        "gap_policy": "no imputation: gaps are left as gaps; invalid readings are excluded using the source's quality rules",
        "aggregation_rule": f"annual mean of valid months; years with < {min_months_per_year} valid months are dropped",
    }
    valid_idx = np.where(s.category == "valid")[0]
    actual = ({"first": f"{int(s.year[valid_idx[0]])}-{int(s.month[valid_idx[0]]):02d}",
               "last": f"{int(s.year[valid_idx[-1]])}-{int(s.month[valid_idx[-1]]):02d}"} if len(valid_idx) else None)
    base = {"variable": variable, "region": region, "period_requested": {"start_year": start_year, "end_year": end_year},
            "period_actual": actual, "source": series.source, "units": s.units, "data_quality": dq, "alpha": alpha,
            "notes": []}

    if series.fetch_errors:
        return _insufficient("FETCH_ERRORS", "تعذّر جلب جزء من البيانات من المصدر؛ لا يُعامل ذلك كقيم مفقودة ولا يصدر حكم.", base)
    if len(ann["year"]) < min_years:
        return _insufficient("TOO_FEW_YEARS",
                             f"عدد السنوات الصالحة ({len(ann['year'])}) أقل من الحد الأدنى ({min_years}) لتقييم الاتجاه.", base,
                             {"required_years": min_years})
    if dq["coverage_fraction"] < min_coverage:
        return _insufficient("LOW_COVERAGE", f"تغطية البيانات الصالحة ({dq['coverage_fraction']}) أقل من الحد الأدنى ({min_coverage}).",
                             base, {"required_coverage": min_coverage})
    if np.ptp(s.value[valid_idx]) == 0:
        base["notes"].append("all valid readings are identical (no variation)")

    # --- diagnostics on the monthly series -----------------------------------------------------
    ok = s.category == "valid"
    seas = st.seasonality_test(s.value[ok], s.month[ok], alpha)
    month_means = {m: float(np.mean(s.value[ok & (s.month == m)])) for m in np.unique(s.month[ok])}
    anomalies = np.full(len(s.value), np.nan)
    for m, mu in month_means.items():
        sel = ok & (s.month == m)
        anomalies[sel] = s.value[sel] - mu
    # autocorrelation must be judged on residuals AFTER removing the trend, otherwise a real trend looks like autocorrelation
    sen_anom = st.sen_slope(anomalies[ok], s.t[ok], 0.0, alpha)["slope"]
    resid = anomalies - sen_anom * (s.t - np.nanmean(s.t[ok]))
    lag1 = st.pairwise_lag_corr(resid, 1)
    valid_anom = resid[ok]
    q, p_lb = st.ljung_box(valid_anom, min(12, max(1, len(valid_anom) // 5))) if len(valid_anom) >= 24 else (float("nan"),) * 2
    autoc_monthly = bool(not math.isnan(p_lb) and p_lb < alpha)
    per_month_ok = all((ok & (s.month == m)).sum() >= 3 for m in range(1, 13))
    diagnostics = {
        "seasonality": {**{k: (_r(v) if isinstance(v, float) else v) for k, v in seas.items()}},
        "autocorrelation_monthly_deseasonalised": {"lag1": _r(lag1), "ljung_box_p": _r(p_lb), "significant": autoc_monthly},
    }

    # --- candidate analyses -----------------------------------------------------------------------
    annual_block, annual_diag = _run_annual(s, ann, alpha)
    diagnostics["autocorrelation_annual"] = annual_diag
    seasonal_block = _run_seasonal(s, alpha) if per_month_ok and seas["applicable"] else None

    if aggregation == "annual":
        choice, why = "annual", "forced by request (aggregation='annual')"
    elif aggregation == "monthly_seasonal":
        choice, why = ("monthly_seasonal", "forced by request (aggregation='monthly_seasonal')") if seasonal_block else \
            ("annual", "seasonal test requested but not applicable (fewer than 3 readings in some calendar month); annual used")
    elif seasonal_block and seas["significant"] and not autoc_monthly:
        choice, why = "monthly_seasonal", "significant seasonality and no significant autocorrelation in the deseasonalised monthly series"
    elif autoc_monthly:
        choice, why = "annual", ("significant autocorrelation in the deseasonalised monthly series (Ljung-Box p < alpha): "
                                 "monthly Mann-Kendall p-values would be too optimistic, so annual means are used (re-tested for autocorrelation; Hamed-Rao variance correction applies only where annual lags are significant)")
    elif seasonal_block and seas["significant"]:
        choice, why = "monthly_seasonal", "significant seasonality"
    else:
        choice, why = "annual", "no significant seasonality detected / seasonal test not applicable; annual means used"

    primary = seasonal_block if choice == "monthly_seasonal" else annual_block
    other = annual_block if choice == "monthly_seasonal" else seasonal_block
    sensitivity = None
    if other:
        sensitivity = {"variant": "annual" if other is annual_block else "monthly_seasonal", **other,
                       "agrees_with_primary": bool(other["direction"] == primary["direction"] and other["significant"] == primary["significant"])}
    unit = f"{s.units}/year"
    interp = _interpret(primary["direction"], primary["significant"], alpha, primary["sen_slope"]["value"], unit,
                        primary["test_name"], float(primary["p_value"]))
    span = float(s.t[ok].max() - s.t[ok].min())
    note_constant = "no variation in the data" in " ".join(base["notes"])
    out = {
        **base, "status": "ok", "reason_code": None,
        "aggregation": {"chosen": choice, "reason": why, "rule": dq["aggregation_rule"]},
        "diagnostics": diagnostics, "test": primary, "interpretation": interp,
        "approx_total_change_over_span": _r(primary["sen_slope"]["value"] * span, 3) if primary["sen_slope"]["value"] is not None else None,
        "span_years": _r(span, 2), "sensitivity": sensitivity,
        "chart": _chart(s, ann, primary, "annual" if choice == "annual" else "monthly", variable.get("name", ""), series.source),
        "caveats": CAVEATS["ar"], "caveats_en": CAVEATS["en"],
    }
    if note_constant:
        out["notes"].append("constant series: tau = 0, p = 1")
    return out
