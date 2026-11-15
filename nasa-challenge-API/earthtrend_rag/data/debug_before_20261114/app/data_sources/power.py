"""NASA POWER monthly point client (https://power.larc.nasa.gov/api/temporal/monthly/point).

Documented in the project's reference (card S05): public, no key; monthly responses contain a 13th pseudo-month
(`YYYY13` = annual summary) which is NOT a calendar month and is skipped; fill value is -999.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.analysis.timeseries import MonthlySeries
from app.config import get_settings

log = logging.getLogger(__name__)
BASE = "https://power.larc.nasa.gov/api/temporal/monthly/point"


class SourceError(RuntimeError):
    pass


def parse_power_monthly(payload: dict, parameter: str, endpoint: str, retrieved_at: str | None = None) -> MonthlySeries:
    try:
        raw = payload["properties"]["parameter"][parameter]
        header = payload.get("header", {})
        units = payload.get("parameters", {}).get(parameter, {}).get("units", "")
    except (KeyError, TypeError) as e:
        raise SourceError(f"Unexpected POWER response shape (missing {e})") from None
    fill = header.get("fill_value", -999.0)
    years, months, vals = [], [], []
    for key, v in sorted(raw.items()):
        if len(key) != 6 or not key.isdigit():
            continue
        y, m = int(key[:4]), int(key[4:])
        if m == 13:                      # annual summary, not a month
            continue
        if not 1 <= m <= 12:
            continue
        years.append(y)
        months.append(m)
        vals.append(None if v is None else float(v))
    unit_norm = {"C": "°C"}.get(units, units)
    src = {"provider": "NASA POWER", "dataset": "/".join(header.get("sources", [])) or "POWER monthly",
           "api": header.get("api", {}), "endpoint": endpoint, "fill_value": fill, "time_standard": header.get("time_standard"),
           "title": header.get("title"), "parameter": parameter, "parameter_name": payload.get("parameters", {}).get(parameter, {}).get("longname"),
           "retrieved_at": retrieved_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "native_resolution_note": "MERRA-2 grid (about 0.5 x 0.625 degrees); value is for the grid cell containing the point"}
    return MonthlySeries(years, months, vals, unit_norm, None, src)


def fetch_power_monthly(parameter: str, lat: float, lon: float, start_year: int, end_year: int,
                        use_cache: bool = True, client: httpx.Client | None = None) -> MonthlySeries:
    params = {"parameters": parameter, "community": "AG", "longitude": f"{lon:.4f}", "latitude": f"{lat:.4f}",
              "start": str(start_year), "end": str(end_year), "format": "JSON"}
    cache_dir = get_settings().data_dir / "cache"
    key = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:24]
    cache_file = cache_dir / f"power_{key}.json"
    endpoint = f"{BASE}?" + "&".join(f"{k}={v}" for k, v in params.items())
    if use_cache and cache_file.exists():
        c = json.loads(cache_file.read_text(encoding="utf-8"))
        return parse_power_monthly(c["payload"], parameter, endpoint, c["retrieved_at"])
    own = client is None
    client = client or httpx.Client(timeout=60.0)
    last = None
    try:
        for attempt in range(3):
            try:
                r = client.get(BASE, params=params)
                if r.status_code in (429, 500, 502, 503, 504):
                    last = f"HTTP {r.status_code}"
                    continue
                if r.status_code != 200:
                    raise SourceError(f"NASA POWER returned HTTP {r.status_code}: {r.text[:200]}")
                payload = r.json()
                now = datetime.now(timezone.utc).isoformat(timespec="seconds")
                cache_dir.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(json.dumps({"retrieved_at": now, "payload": payload}), encoding="utf-8")
                return parse_power_monthly(payload, parameter, endpoint, now)
            except httpx.HTTPError as e:
                last = type(e).__name__
        raise SourceError(f"NASA POWER unavailable ({last})")
    finally:
        if own:
            client.close()
