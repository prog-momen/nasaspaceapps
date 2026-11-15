"""Variables and regions the trend tool can serve TODAY, with honest availability status.

Only sources actually verified/documented in the project's reference are wired. Anything else returns an explicit
status (never a substitute series).
"""
from __future__ import annotations

import re

# variable id -> metadata. `source` None => cannot be served now (reason given)
VARIABLES: dict[str, dict] = {
    "air_temperature": {
        "name": "Air temperature at 2 m (T2M)", "name_ar": "درجة حرارة الهواء على ارتفاع 2 م", "source": "nasa_power",
        "parameter": "T2M", "valid_range": (-90.0, 60.0),
        "note": "Reanalysis-based (MERRA-2) air temperature, NOT land surface temperature.",
    },
    "precipitation": {
        "name": "Precipitation, bias-corrected (PRECTOTCORR)", "name_ar": "الهطول المصحَّح (PRECTOTCORR)", "source": "nasa_power",
        "parameter": "PRECTOTCORR", "valid_range": (0.0, 2000.0),
        "note": "Monthly mean daily rate (mm/day), not a monthly total.",
    },
    "relative_humidity": {
        "name": "Relative humidity at 2 m (RH2M)", "name_ar": "الرطوبة النسبية على ارتفاع 2 م", "source": "nasa_power",
        "parameter": "RH2M", "valid_range": (0.0, 100.0),
        "note": "Reanalysis-based (MERRA-2) monthly mean, percent.",
    },
    "wind_speed": {
        "name": "Wind speed at 2 m (WS2M)", "name_ar": "سرعة الرياح على ارتفاع 2 م", "source": "nasa_power",
        "parameter": "WS2M", "valid_range": (0.0, 60.0),
        "note": "Reanalysis-based (MERRA-2) monthly mean, m/s.",
    },
    "land_surface_temperature": {
        "name": "Land surface temperature (MODIS MOD11C3.061)", "name_ar": "درجة حرارة سطح الأرض", "source": None,
        "reason_code": "SOURCE_REQUIRES_CREDENTIALS",
        "reason": ("MOD11C3.061 / MOD11A2.061 are served through AppEEARS or Earthdata downloads, which need an Earthdata Login "
                   "that is not configured. NASA POWER T2M is air temperature, not land surface temperature, so it is not substituted "
                   "automatically. Ask explicitly for variable='air_temperature' if that is acceptable, or supply a series from the "
                   "external source. An AppEEARS point-sampling adapter exists (EARTHDATA_USERNAME/EARTHDATA_PASSWORD) for direct LST exploration, "
                   "but its 8-day composites are not yet wired into the monthly trend test."),
        "alternative": "air_temperature",
    },
    "wildfires": {
        "name": "Wildfires (FIRMS active-fire detections)", "name_ar": "الحرائق", "source": None, "reason_code": "VARIABLE_NOT_TREND_READY",
        "reason": ("FIRMS detections are available through the fire-detection tool (needs FIRMS_MAP_KEY), but detection counts are event counts that need a documented "
                   "aggregation (and sensor-harmonisation) design before a trend test is meaningful."),
    },
    "drought": {
        "name": "Drought", "name_ar": "الجفاف", "source": None, "reason_code": "VARIABLE_NOT_TREND_READY",
        "reason": ("No drought index is wired yet. Candidate inputs (SMAP SPL3SMP soil moisture, MOD13A3 NDVI, precipitation) "
                   "need their own source clients and an index definition."),
    },
}

_ALIASES = {
    "relative_humidity": ["relative humidity", "humidity", "rh2m", "الرطوبة"],
    "wind_speed": ["wind speed", "wind", "ws2m", "الرياح", "سرعة الرياح"],
    "air_temperature": ["air temperature", "t2m", "حرارة الهواء", "درجة الحرارة", "temperature"],
    "precipitation": ["precipitation", "rainfall", "rain", "هطول", "أمطار", "مطر", "prectotcorr"],
    "land_surface_temperature": ["land surface temperature", "lst", "حرارة سطح الأرض", "درجة حرارة سطح"],
    "wildfires": ["wildfire", "fire", "حرائق", "حريق"],
    "drought": ["drought", "جفاف"],
}


def normalize_variable(name: str) -> str | None:
    n = name.strip().lower()
    if n in VARIABLES:
        return n
    # most specific alias first: "land surface temperature" must never fall through to the generic "temperature"
    pairs = sorted(((a, vid) for vid, al in _ALIASES.items() for a in al), key=lambda p: -len(p[0]))
    for a, vid in pairs:
        if a in n:
            return vid
    return None


# Representative points only (NOT area means). Coordinates are approximate and declared as such in the result.
REGIONS: dict[str, dict] = {
    "amazon": {"name": "Amazon basin (representative point)", "lat": -3.4653, "lon": -62.2159, "aliases": ["amazon", "الأمازون", "الامازون"]},
    "nablus": {"name": "Nablus", "lat": 32.22, "lon": 35.26, "aliases": ["nablus", "نابلس"]},
    "cairo": {"name": "Cairo", "lat": 30.0444, "lon": 31.2357, "aliases": ["cairo", "القاهرة"]},
    "riyadh": {"name": "Riyadh", "lat": 24.7136, "lon": 46.6753, "aliases": ["riyadh", "الرياض"]},
    "california": {"name": "California (central point)", "lat": 36.7783, "lon": -119.4179, "aliases": ["california", "كاليفورنيا"]},
    "texas": {"name": "Texas (central point)", "lat": 31.0, "lon": -100.0, "aliases": ["texas", "تكساس"]},
}


def resolve_region(name: str | None, lat: float | None, lon: float | None) -> dict | None:
    if lat is not None and lon is not None:
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return None
        return {"name": name or f"point ({lat:.3f}, {lon:.3f})", "lat": float(lat), "lon": float(lon), "type": "point"}
    if name:
        n = re.sub(r"\s+", " ", name.strip().lower())
        for r in REGIONS.values():
            if n == r["name"].lower() or any(a in n for a in r["aliases"]):
                return {"name": r["name"], "lat": r["lat"], "lon": r["lon"], "type": "representative_point"}
    return None
