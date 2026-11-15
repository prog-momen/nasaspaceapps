"""Open-Meteo: operational weather forecast, ERA5-based historical weather, and place geocoding (all free, no key).

Terms (https://open-meteo.com/en/terms, checked 2026-11-14): free API is NON-COMMERCIAL, <10,000 calls/day, 5,000/h, 600/min,
data licensed CC BY 4.0 (attribution required). Forecast and archive are different products and are labelled differently here:
* forecast  -> operational numerical weather prediction (model blend `best_match` unless a model is requested); the service does
              NOT publish a model-run/issue time in the response, so `issue_time` is reported as unavailable.
* archive   -> historical REANALYSIS (ERA5-family), not station observations; ~5 day publication delay.
"""
from __future__ import annotations

import time
from datetime import date, timedelta

from app.providers.base import (ProviderError, envelope, fail, http_json, parse_date, strict, validate_point)

PROVIDER = "Open-Meteo"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0). Free API: non-commercial use only."
LINKS = ["https://open-meteo.com/en/docs", "https://open-meteo.com/en/docs/historical-weather-api", "https://open-meteo.com/en/terms"]

HOURLY = {"temperature": "temperature_2m", "humidity": "relative_humidity_2m", "precipitation": "precipitation", "wind": "wind_speed_10m"}
DAILY = {"temperature_max": "temperature_2m_max", "temperature_min": "temperature_2m_min", "precipitation": "precipitation_sum",
         "wind_max": "wind_speed_10m_max"}
VARIABLE_ALIASES = {"temperature": ["temperature", "temp", "حرارة", "درجة"], "humidity": ["humidity", "رطوبة"],
                    "precipitation": ["precip", "rain", "مطر", "أمطار", "هطول"], "wind": ["wind", "رياح", "ريح"]}
MAX_FORECAST_DAYS = 16
MAX_ARCHIVE_DAYS = 366
ARCHIVE_DELAY_DAYS = 5


def geocode(name: str, language: str = "en", count: int = 3) -> dict:
    """Place name -> coordinates (Open-Meteo geocoding; supports Arabic names)."""
    if not name or len(name.strip()) < 2:
        return envelope(PROVIDER, "geocoding", "map_visualization", "invalid_request", "EMPTY_NAME", "place name is empty")
    try:
        d, meta = http_json("open-meteo-geo", "GET", GEOCODE_URL, params={"name": name.strip(), "count": count, "language": language, "format": "json"}, ttl=86400)
    except ProviderError as e:
        return fail(PROVIDER, "geocoding", "map_visualization", e)
    res = (d or {}).get("results") or []
    if not res:
        return envelope(PROVIDER, "geocoding", "map_visualization", "no_data", "PLACE_NOT_FOUND", f"No place matched '{name}'.", live=meta["live"], cache=meta["cache"])
    places = [{"name": r.get("name"), "country": r.get("country"), "admin1": r.get("admin1"), "latitude": r["latitude"], "longitude": r["longitude"],
               "elevation": r.get("elevation"), "timezone": r.get("timezone"), "population": r.get("population")} for r in res]
    return envelope(PROVIDER, "geocoding", "map_visualization", "ok", data={"places": places}, live=meta["live"], cache=meta["cache"],
                    retrieved_at=meta["retrieved_at"], attribution=ATTRIBUTION, source_links=["https://open-meteo.com/en/docs/geocoding-api"],
                    limitations=["First match is used unless the user picks another; ambiguous names can resolve to the wrong city."])


def _series_artifact(title: str, times: list, series: list[dict]) -> dict:
    return {"type": "line_chart", "title": title, "x": times, "series": series}


def forecast(lat: float, lon: float, days: int = 3, variables: list[str] | None = None, model: str | None = None) -> dict:
    err = validate_point(lat, lon)
    if err:
        return envelope(PROVIDER, "forecast", "weather_forecast", "invalid_request", "INVALID_POINT", err)
    if not (1 <= int(days) <= MAX_FORECAST_DAYS):
        return envelope(PROVIDER, "forecast", "weather_forecast", "invalid_request", "INVALID_FORECAST_DAYS", f"days must be 1..{MAX_FORECAST_DAYS}")
    want = [v for v in (variables or list(HOURLY)) if v in HOURLY] or list(HOURLY)
    params = {"latitude": round(float(lat), 4), "longitude": round(float(lon), 4), "hourly": ",".join(HOURLY[v] for v in want),
              "daily": ",".join(DAILY.values()), "forecast_days": int(days), "timezone": "auto"}
    if model:
        params["models"] = model
    t0 = time.monotonic()
    try:
        d, meta = http_json("open-meteo", "GET", FORECAST_URL, params=params, ttl=900)
    except ProviderError as e:
        return fail(PROVIDER, "forecast", "weather_forecast", e, request={"latitude": lat, "longitude": lon, "days": days})
    h, dl = d["hourly"], d["daily"]
    arts = [
        _series_artifact("Hourly forecast", h["time"], [{"name": k, "unit": d["hourly_units"].get(HOURLY[k]), "y": h[HOURLY[k]],
                                                         "kind": "bar" if k == "precipitation" else "line"} for k in want]),
        _series_artifact("Daily extremes", dl["time"], [{"name": k, "unit": d["daily_units"].get(v), "y": dl[v], "kind": "bar" if k == "precipitation" else "line"}
                                                        for k, v in DAILY.items()]),
        {"type": "table", "title": "Daily forecast", "columns": ["date"] + list(DAILY), "rows": [[dl["time"][i]] + [dl[v][i] for v in DAILY.values()] for i in range(len(dl["time"]))]},
    ]
    return strict(envelope(
        PROVIDER, "Forecast API", "weather_forecast", "ok", variables=want + list(DAILY),
        request={"latitude": lat, "longitude": lon, "forecast_days": days, "model": model or "best_match (service default)"},
        actual={"grid": {"latitude": d["latitude"], "longitude": d["longitude"], "elevation_m": d.get("elevation")},
                "timezone": d["timezone"], "utc_offset_seconds": d["utc_offset_seconds"],
                "period": {"first": h["time"][0], "last": h["time"][-1]}, "issue_time": None,
                "model": model or "best_match (blend of national weather models chosen by the service; not reported per value)"},
        units={**d["hourly_units"], **d["daily_units"]}, temporal_resolution="hourly + daily", live=meta["live"], cache=meta["cache"],
        retrieved_at=meta["retrieved_at"], duration_ms=int((time.monotonic() - t0) * 1000), source_links=LINKS, attribution=ATTRIBUTION,
        license="CC BY 4.0 (non-commercial free API)",
        limitations=["Operational forecast, not observations. The service does not publish the model run/issue time in this response.",
                     "Times are local to the grid cell's timezone (see actual.timezone); values are for the nearest grid cell, not the exact point.",
                     "Forecast skill decreases with lead time; days beyond ~7 are low-confidence."],
        data={"hourly": h, "daily": dl}, artifacts=arts))


def historical(lat: float, lon: float, start: str, end: str, variables: list[str] | None = None) -> dict:
    err = validate_point(lat, lon)
    if err:
        return envelope(PROVIDER, "archive", "historical_weather", "invalid_request", "INVALID_POINT", err)
    try:
        s, e = parse_date(start, "start_date"), parse_date(end, "end_date")
    except ProviderError as ex:
        return envelope(PROVIDER, "archive", "historical_weather", "invalid_request", "INVALID_DATE", str(ex))
    if not s or not e or e < s:
        return envelope(PROVIDER, "archive", "historical_weather", "invalid_request", "INVALID_DATE_RANGE", "start_date/end_date required and end >= start")
    if s < date(1940, 1, 1):
        return envelope(PROVIDER, "archive", "historical_weather", "unsupported_request", "BEFORE_COVERAGE", "Archive coverage starts in 1940.")
    if (e - s).days + 1 > MAX_ARCHIVE_DAYS:
        return envelope(PROVIDER, "archive", "historical_weather", "unsupported_request", "RANGE_TOO_LONG",
                        f"Prototype limit: {MAX_ARCHIVE_DAYS} days per request (requested {(e - s).days + 1}). Use the POWER trend tool for multi-year climate.")
    latest = date.today() - timedelta(days=ARCHIVE_DELAY_DAYS)
    notes = []
    if e > latest:
        notes.append(f"end_date was after the archive's ~{ARCHIVE_DELAY_DAYS}-day delay; clipped to {latest.isoformat()}.")
        e = latest
        if e < s:
            return envelope(PROVIDER, "archive", "historical_weather", "unsupported_request", "TOO_RECENT",
                            "Requested dates are within the archive delay; use the forecast tool for recent/ongoing days.")
    params = {"latitude": round(float(lat), 4), "longitude": round(float(lon), 4), "start_date": s.isoformat(), "end_date": e.isoformat(),
              "daily": ",".join(DAILY.values()), "timezone": "auto"}
    t0 = time.monotonic()
    try:
        d, meta = http_json("open-meteo", "GET", ARCHIVE_URL, params=params, ttl=86400)
    except ProviderError as ex:
        return fail(PROVIDER, "archive", "historical_weather", ex, request={"latitude": lat, "longitude": lon, "start": str(s), "end": str(e)})
    dl = d["daily"]
    miss = sum(1 for v in DAILY.values() for x in dl[v] if x is None)
    arts = [_series_artifact("Historical daily weather (reanalysis)", dl["time"], [{"name": k, "unit": d["daily_units"].get(v), "y": dl[v], "kind": "bar" if k == "precipitation" else "line"} for k, v in DAILY.items()]),
            {"type": "table", "title": "Daily historical weather", "columns": ["date"] + list(DAILY), "rows": [[dl["time"][i]] + [dl[v][i] for v in DAILY.values()] for i in range(len(dl["time"]))]}]
    return strict(envelope(
        PROVIDER, "Historical Weather API (reanalysis)", "historical_weather", "ok", variables=list(DAILY),
        request={"latitude": lat, "longitude": lon, "start": start, "end": end},
        actual={"grid": {"latitude": d["latitude"], "longitude": d["longitude"], "elevation_m": d.get("elevation")}, "timezone": d["timezone"],
                "period": {"first": dl["time"][0], "last": dl["time"][-1]}, "source_type": "reanalysis (ERA5-family), not station observations"},
        units=d["daily_units"], temporal_resolution="daily", live=meta["live"], cache=meta["cache"], retrieved_at=meta["retrieved_at"],
        duration_ms=int((time.monotonic() - t0) * 1000), source_links=LINKS, attribution=ATTRIBUTION, license="CC BY 4.0 (non-commercial free API)",
        quality={"missing_values": miss, "notes": notes},
        limitations=["Reanalysis is a model-assimilation product, not a measurement at the point; coastal/mountain cells can differ from stations.",
                     "~5 day publication delay; the free API is non-commercial only."],
        data={"daily": dl}, artifacts=arts))
