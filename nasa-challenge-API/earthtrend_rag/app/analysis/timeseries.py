"""Monthly time-series container, quality screening and completeness accounting.

Policy (declared, never silent): invalid readings are excluded using the source's own rules; gaps are NOT filled;
a year enters the annual aggregate only if it has at least `min_months_per_year` valid months.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional

import numpy as np


@dataclass
class MonthlySeries:
    year: list[int]
    month: list[int]
    value: list[Optional[float]]
    units: str
    quality: Optional[list[Any]] = None          # per-reading source flag (optional)
    source: dict = field(default_factory=dict)   # provider, dataset, endpoint, retrieved_at, ...
    fetch_errors: int = 0                         # periods the source failed to deliver (not "missing")

    def __post_init__(self):
        n = len(self.year)
        if len(self.month) != n or len(self.value) != n:
            raise ValueError("year/month/value length mismatch")
        if self.quality is not None:
            if len(self.quality) != n:
                raise ValueError("quality length mismatch")


@dataclass
class ScreenedSeries:
    idx: np.ndarray            # month index = year*12 + (month-1)
    year: np.ndarray
    month: np.ndarray
    t: np.ndarray              # decimal year at mid-month
    value: np.ndarray          # NaN where not usable
    category: np.ndarray       # 'valid' | 'missing' | 'invalid' (aligned to expected calendar)
    units: str
    source: dict
    expected: int
    counts: dict
    invalid_reasons: dict


def screen(series: MonthlySeries, start_year: int | None = None, end_year: int | None = None,
           fill_values: Iterable[float] = (), valid_range: tuple[float, float] | None = None,
           valid_flags: Iterable[Any] | None = None, flag_predicate: Callable[[Any], bool] | None = None) -> ScreenedSeries:
    """Apply source QC and align to the complete monthly calendar of the requested period.

    valid_flags / flag_predicate: keep a reading only if its quality flag passes (source-specific rule).
    """
    fills = {float(f) for f in fill_values}
    dates = list(zip(series.year, series.month))
    if len(set(dates)) != len(dates):
        raise ValueError("duplicate monthly timestamps; explicit aggregation is required")
    if any(not 1 <= m <= 12 for m in series.month):
        raise ValueError("month must be in 1..12")
    vf = set(valid_flags) if valid_flags is not None else None
    y0 = start_year if start_year is not None else min(series.year)
    y1 = end_year if end_year is not None else max(series.year)
    lo, hi = y0 * 12, y1 * 12 + 11
    idx = np.arange(lo, hi + 1)
    value = np.full(len(idx), np.nan)
    cat = np.array(["missing"] * len(idx), dtype=object)
    reasons: dict[str, int] = {}
    for k in range(len(series.year)):
        i = series.year[k] * 12 + series.month[k] - 1
        if not (lo <= i <= hi) or not (1 <= series.month[k] <= 12):
            continue
        v = series.value[k]
        pos = i - lo
        if v is None or (isinstance(v, float) and np.isnan(v)):
            continue                                            # stays 'missing'
        bad = None
        if not np.isfinite(float(v)):
            bad = "non_finite"
        elif float(v) in fills:
            bad = "fill_value"
        elif valid_range and not (valid_range[0] <= float(v) <= valid_range[1]):
            bad = "out_of_valid_range"
        elif series.quality is not None and vf is not None and series.quality[k] not in vf:
            bad = "quality_flag"
        elif series.quality is not None and flag_predicate is not None and not flag_predicate(series.quality[k]):
            bad = "quality_flag"
        if bad:
            cat[pos] = "invalid"
            reasons[bad] = reasons.get(bad, 0) + 1
            continue
        value[pos] = float(v)
        cat[pos] = "valid"
    year = idx // 12
    month = idx % 12 + 1
    counts = {"valid": int((cat == "valid").sum()), "missing": int((cat == "missing").sum()),
              "invalid": int((cat == "invalid").sum())}
    return ScreenedSeries(idx, year, month, year + (month - 0.5) / 12.0, value, cat, series.units, series.source,
                          len(idx), counts, reasons)


def longest_gap(cat: np.ndarray) -> int:
    best = cur = 0
    for c in cat:
        cur = cur + 1 if c != "valid" else 0
        best = max(best, cur)
    return best


def annual_aggregate(s: ScreenedSeries, min_months: int = 9) -> dict:
    """Mean of valid months per year; years with fewer than `min_months` valid months are dropped (and listed)."""
    years, vals, ts, dropped = [], [], [], []
    for y in np.unique(s.year):
        m = (s.year == y) & (s.category == "valid")
        n = int(m.sum())
        if n >= min_months:
            years.append(int(y))
            vals.append(float(np.mean(s.value[m])))
            ts.append(float(np.mean(s.t[m])))
        else:
            dropped.append({"year": int(y), "valid_months": n})
    return {"year": np.array(years), "value": np.array(vals), "t": np.array(ts), "dropped": dropped}
