"""`analyze_trend` tool: request validation -> data retrieval -> quality screening -> Mann-Kendall/Sen -> structured result.

This is the ONLY place trend numbers come from. Gemini calls it through function calling (see app/agent) and explains
its output; it never computes or estimates values itself.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, Literal, Optional

from pydantic import BaseModel, Field, ValidationError, model_validator

from app.analysis.catalog import VARIABLES, normalize_variable, resolve_region
from app.analysis.timeseries import MonthlySeries
from app.analysis.trend import analyze_series
from app.config import get_settings
from app.data_sources.power import SourceError, fetch_power_monthly

log = logging.getLogger(__name__)
POWER_FIRST_YEAR = 1981


class TrendRequest(BaseModel):
    variable: str = Field(..., description="air_temperature | precipitation | land_surface_temperature | wildfires | drought")
    region: Optional[str] = Field(None, description="Named region known to the catalog (e.g. Amazon, Nablus)")
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    start_year: int = Field(..., ge=POWER_FIRST_YEAR)
    end_year: int
    significance_level: Optional[float] = Field(None, gt=0, lt=0.5, description="alpha; default from settings (0.05)")
    aggregation: Literal["auto", "annual", "monthly_seasonal"] = "auto"

    @model_validator(mode="after")
    def _check(self):
        if self.end_year < self.start_year:
            raise ValueError("end_year must be >= start_year")
        if self.end_year > datetime.now(timezone.utc).year:
            raise ValueError("end_year is in the future")
        return self


def _strict_json(o):
    """Recursively convert numpy scalars and replace NaN/Infinity with None so the result is valid strict JSON."""
    import math
    import numpy as np
    if isinstance(o, dict):
        return {str(k): _strict_json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_strict_json(v) for v in o]
    if isinstance(o, np.generic):
        o = o.item()
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return o


def _status(status: str, code: str, message: str, **extra) -> dict:
    return {"status": status, "reason_code": code, "message": message, **extra}


def run_trend_analysis(raw_args: dict, fetcher: Callable[..., MonthlySeries] | None = None,
                       series_override: MonthlySeries | None = None) -> dict:
    """Never raises for user/data problems: always returns a result dict with an explicit `status`.

    `series_override` lets another source client (e.g. AppEEARS for LST) feed an already-fetched series through the
    same screening/statistics path.
    """
    s = get_settings()
    try:
        req = TrendRequest(**raw_args)
    except ValidationError as e:
        return _status("invalid_request", "INVALID_ARGUMENTS", "Invalid arguments: " +
                       "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()))
    except TypeError as e:
        return _status("invalid_request", "INVALID_ARGUMENTS", str(e))

    vid = normalize_variable(req.variable)
    if vid is None:
        return _status("unsupported_variable", "UNKNOWN_VARIABLE", f"Unknown variable '{req.variable}'.",
                       supported=[k for k, v in VARIABLES.items() if v["source"]])
    var = {"id": vid, **{k: v for k, v in VARIABLES[vid].items() if k in ("name", "name_ar", "note")}}
    if series_override is None and VARIABLES[vid]["source"] is None:
        return _status("data_source_unavailable" if VARIABLES[vid].get("alternative") else "unsupported_variable",
                       VARIABLES[vid]["reason_code"], VARIABLES[vid]["reason"], variable=var,
                       suggested_alternative=VARIABLES[vid].get("alternative"),
                       supported=[k for k, v in VARIABLES.items() if v["source"]])

    region = resolve_region(req.region, req.latitude, req.longitude)
    if region is None:
        return _status("invalid_request", "REGION_NOT_RESOLVED",
                       "Region not recognised. Provide latitude and longitude, or a region known to the catalog.",
                       variable=var, known_regions=sorted({r for r in ("Amazon", "Nablus", "Cairo", "Riyadh", "California", "Texas")}))

    alpha = req.significance_level or s.trend_alpha
    try:
        series = series_override or (fetcher or fetch_power_monthly)(
            VARIABLES[vid]["parameter"], region["lat"], region["lon"], req.start_year, req.end_year)
    except SourceError as e:
        return _status("upstream_error", "SOURCE_ERROR", f"Data source error: {e}", variable=var, region=region,
                       error_kind=e.kind, attempts=e.attempts)
    except Exception as e:  # network/parse problems must not become a verdict
        log.exception("unexpected data retrieval failure")
        return _status("upstream_error", "SOURCE_ERROR", f"Data retrieval failed ({type(e).__name__}).", variable=var, region=region)

    rng = VARIABLES[vid].get("valid_range")
    fills = [series.source.get("fill_value", -999.0)] if series.source else [-999.0]
    try:
        result = analyze_series(series, variable=var, region=region, start_year=req.start_year, end_year=req.end_year,
                            alpha=alpha, min_years=s.trend_min_years, min_months_per_year=s.trend_min_months_per_year,
                            min_coverage=s.trend_min_coverage, aggregation=req.aggregation, fill_values=fills, valid_range=rng)
    except ValueError as e:
        return _status("invalid_data", "INVALID_TIMESERIES", str(e), variable=var, region=region)
    result["tool"] = {"name": "analyze_trend", "version": "1.0", "arguments": req.model_dump()}
    return _strict_json(result)


# ---- Gemini function declaration (the model may only call this, with these arguments) -------------

FUNCTION_DECLARATION = {
    "name": "analyze_trend",
    "description": ("Runs a Mann-Kendall trend test with Sen's slope on a NASA monthly time series for one variable, one place "
                    "and a period of years. Returns direction, magnitude, significance, data-quality and source information. "
                    "Use it for any question about whether a variable rose, fell or changed over time somewhere. "
                    "It describes the historical trend only; it does not forecast and does not establish causes."),
    "parameters": {
        "type": "object",
        "properties": {
            "variable": {"type": "string", "enum": list(VARIABLES), "description": "Variable id. Do not substitute one variable for another."},
            "region": {"type": "string", "description": "Place name (e.g. 'Amazon'); omit if latitude/longitude are given."},
            "latitude": {"type": "number", "description": "Decimal degrees, -90..90"},
            "longitude": {"type": "number", "description": "Decimal degrees, -180..180"},
            "start_year": {"type": "integer", "description": "First year of the period (>= 1981)."},
            "end_year": {"type": "integer", "description": "Last year of the period."},
            "significance_level": {"type": "number", "description": "Optional alpha; leave unset to use the project default (0.05)."},
            "aggregation": {"type": "string", "enum": ["auto", "annual", "monthly_seasonal"], "description": "Leave 'auto' unless the user asks otherwise."},
        },
        "required": ["variable", "start_year", "end_year"],
    },
}
