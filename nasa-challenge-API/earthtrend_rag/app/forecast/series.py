"""Monthly series preparation for forecasting: regular calendar, completeness policy, provenance. Variables, units and aggregation are explicit."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from app.analysis.timeseries import screen
from app.data_sources.power import fetch_power_monthly

# POWER monthly values are monthly MEANS of daily values. Precipitation is therefore a mean daily RATE (mm/day), not a monthly total:
# the monthly total is derived explicitly (rate x days in month) and always labelled as derived.
VARIABLES = {
    "air_temperature": {"parameter": "T2M", "unit": "°C", "transform": "identity", "valid": (-90.0, 60.0), "aggregation": "monthly mean of daily 2 m air temperature",
                        "pct_ok": False, "name": "Air temperature at 2 m (T2M)", "name_ar": "درجة حرارة الهواء على ارتفاع 2 م"},
    "precipitation": {"parameter": "PRECTOTCORR", "unit": "mm/day", "transform": "sqrt", "valid": (0.0, 2000.0), "aggregation": "monthly mean daily precipitation RATE (not a monthly total)",
                      "pct_ok": True, "name": "Precipitation, bias-corrected (PRECTOTCORR)", "name_ar": "الهطول المصحَّح (PRECTOTCORR)"},
    "relative_humidity": {"parameter": "RH2M", "unit": "%", "transform": "logit100", "valid": (0.0, 100.0), "aggregation": "monthly mean of daily 2 m relative humidity",
                          "pct_ok": True, "name": "Relative humidity at 2 m (RH2M)", "name_ar": "الرطوبة النسبية على ارتفاع 2 م"},
    "wind_speed": {"parameter": "WS2M", "unit": "m/s", "transform": "log", "valid": (0.0, 60.0), "aggregation": "monthly mean of daily 2 m wind speed",
                   "pct_ok": True, "name": "Wind speed at 2 m (WS2M)", "name_ar": "سرعة الرياح على ارتفاع 2 م"},
}
MAX_MISSING_FRACTION = 0.03        # more missing months than this -> the series is refused, never silently patched
MAX_GAP_FILL = 2                   # consecutive interior months that may be filled (causally, see below)


@dataclass
class Prepared:
    y: pd.Series                   # regular monthly (MS) index, no NaN, ends at the last COMPLETE valid month
    variable: str
    cfg: dict
    provenance: dict
    quality: dict
    warnings: list[str] = field(default_factory=list)
    status: str = "ok"             # ok | insufficient_history | too_many_missing | no_data
    message: str | None = None


def prepare(series, variable: str, lat: float, lon: float, start_year: int, end_year: int, today: date | None = None) -> Prepared:
    """MonthlySeries -> regular monthly pandas Series. Policy (declared in `quality`):
    * the current (incomplete) month and anything later is excluded; trailing months the source has not delivered/validated are excluded (cutoff = last valid month);
    * invalid readings (source fill value, outside the physical range) are NOT used;
    * interior gaps: at most MAX_GAP_FILL consecutive months and MAX_MISSING_FRACTION overall, filled CAUSALLY with the mean of earlier same-calendar-month
      values (never future data); otherwise the series is refused."""
    today = today or date.today()
    cfg = VARIABLES[variable]
    ss = screen(series, start_year, end_year, fill_values=[float(series.source.get("fill_value", -999.0))], valid_range=cfg["valid"])
    idx = pd.to_datetime([f"{int(y)}-{int(m):02d}-01" for y, m in zip(ss.year, ss.month)])
    s = pd.Series(ss.value.astype(float), index=idx)
    first_incomplete = pd.Timestamp(today.year, today.month, 1)
    n_future = int(((s.index >= first_incomplete) & s.notna()).sum())       # months WITH data that are excluded because they are incomplete/future
    s = s[s.index < first_incomplete]
    valid = s.notna()
    prov = {"provider": "NASA POWER", "dataset": series.source.get("dataset"), "parameter": cfg["parameter"], "latitude": lat, "longitude": lon, "units": cfg["unit"],
            "aggregation": cfg["aggregation"], "retrieved_at": series.source.get("retrieved_at"), "cache_hit": series.source.get("cache_hit"), "endpoint": series.source.get("endpoint"),
            "grid_footprint": "MERRA-2 cell ~0.5 x 0.625 degrees containing the point", "data_version": series.source.get("dataset")}
    if not valid.any():
        return Prepared(pd.Series(dtype=float), variable, cfg, prov, {}, status="no_data", message="No valid monthly values.")
    first, last = valid[valid].index[0], valid[valid].index[-1]
    s = s[first:last]                       # the record starts at the first valid month (the requested window may begin before the source does)
    trailing = int(((s.index.max() if len(s) else last) < first_incomplete - pd.offsets.MonthBegin(1)) and 0)
    n_missing = int(s.isna().sum())
    # causal gap fill
    warns, filled = [], 0
    if n_missing:
        if n_missing / len(s) > MAX_MISSING_FRACTION:
            return Prepared(s, variable, cfg, prov, {"n_months": len(s), "n_missing": n_missing}, status="too_many_missing",
                            message=f"{n_missing} of {len(s)} months are missing (> {MAX_MISSING_FRACTION:.0%}); the series is not used.")
        arr = s.values.copy()
        run = 0
        for i in range(len(arr)):
            if np.isnan(arr[i]):
                run += 1
                if run > MAX_GAP_FILL:
                    return Prepared(s, variable, cfg, prov, {"n_months": len(s), "n_missing": n_missing}, status="too_many_missing", message=f"A gap longer than {MAX_GAP_FILL} consecutive months.")
                prev = arr[:i][np.arange(i) % 12 == i % 12]
                prev = prev[np.isfinite(prev)]
                if not len(prev):
                    return Prepared(s, variable, cfg, prov, {"n_months": len(s), "n_missing": n_missing}, status="too_many_missing", message="A gap before any same-month history exists.")
                arr[i] = float(prev.mean()); filled += 1
            else:
                run = 0
        s = pd.Series(arr, index=s.index)
        warns.append(f"{filled} interior month(s) were filled causally with the earlier same-calendar-month mean.")
    s = s.asfreq("MS")
    vals = s.values
    quality = {"n_months": int(len(s)), "first_month": str(s.index[0].date()), "cutoff_month": str(s.index[-1].date()), "n_invalid_or_missing_before_fill": n_missing, "n_filled_causally": filled,
               "excluded_incomplete_or_future_months": n_future, "gap_months_cutoff_to_today": int((today.year - s.index[-1].year) * 12 + (today.month - s.index[-1].month) - 1),
               "policy": f"incomplete current month excluded; invalid readings not used; <= {MAX_MISSING_FRACTION:.0%} interior missing months, gaps <= {MAX_GAP_FILL} months filled causally; otherwise refused",
               "constant_series": bool(np.nanstd(vals) < 1e-9), "values_sha256": hashlib.sha256(json.dumps([round(float(v), 6) for v in vals]).encode()).hexdigest()[:16]}
    prov["values_sha256"] = quality["values_sha256"]
    if len(s) < 144:
        return Prepared(s, variable, cfg, prov, quality, warns, "insufficient_history", f"Only {len(s)} complete months are available; at least 144 (12 years) are required to fit and validate a seasonal model.")
    return Prepared(s, variable, cfg, prov, quality, warns)


def structural_break_check(y: pd.Series) -> dict:
    """Simple, declared diagnostic (not a proof): compares the mean of the first and second half after removing the calendar-month climatology; a large standardized
    difference is reported as a warning (it may reflect climate change, a data-definition change, or both)."""
    z = y - y.groupby(y.index.month).transform("mean")
    a, b = z.iloc[: len(z) // 2], z.iloc[len(z) // 2:]
    se = float(np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b)))
    d = float(b.mean() - a.mean())
    return {"mean_shift_between_halves": d, "standardized": d / se if se > 0 else None, "flag": bool(se > 0 and abs(d / se) > 4),
            "note": "A shift between the two halves of the record: climate change, a change in the POWER/MERRA-2 inputs, or both; it is not diagnosed further here."}
