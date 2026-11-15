"""NASA POWER monthly point client (https://power.larc.nasa.gov/api/temporal/monthly/point).

Documented in the project's reference (card S05): public, no key; monthly responses contain a 13th pseudo-month
(`YYYY13` = annual summary) which is NOT a calendar month and is skipped; fill value is -999.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.analysis.timeseries import MonthlySeries
from app.config import get_settings
from app.reliability import bounded_call, remaining, retry_after

log = logging.getLogger(__name__)
BASE = "https://power.larc.nasa.gov/api/temporal/monthly/point"


class SourceError(RuntimeError):
    def __init__(self, message, kind="invalid_data", attempts=None):
        super().__init__(message)
        self.kind, self.attempts = kind, attempts or []


def parse_power_monthly(payload: dict, parameter: str, endpoint: str, retrieved_at: str | None = None) -> MonthlySeries:
    if not isinstance(payload, dict):
        raise SourceError("POWER response is not an object")
    try:
        raw = payload["properties"]["parameter"][parameter]
        header = payload.get("header", {})
        units = payload.get("parameters", {}).get(parameter, {}).get("units", "")
    except (KeyError, TypeError, AttributeError) as e:
        raise SourceError(f"Unexpected POWER response shape (missing {e})") from None
    if not isinstance(raw, dict) or not raw or not isinstance(header, dict) or not units:
        raise SourceError("POWER response lacks observations or units")
    expected_units = {"T2M": {"C", "°C"}, "PRECTOTCORR": {"mm/day"}, "RH2M": {"%"}, "WS2M": {"m/s"}}
    if parameter in expected_units and units not in expected_units[parameter]:
        raise SourceError(f"Unexpected units for {parameter}")
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
        try:
            val = None if v is None else float(v)
        except (TypeError, ValueError):
            raise SourceError("POWER observation is not numeric") from None
        if val is not None and not math.isfinite(val):
            raise SourceError("POWER observation is not finite")
        vals.append(val)
    if not years:
        raise SourceError("POWER response has no calendar-month observations")
    unit_norm = {"C": "°C"}.get(units, units)
    src = {"provider": "NASA POWER", "dataset": "/".join(header.get("sources", [])) or "POWER monthly",
           "api": header.get("api", {}), "endpoint": endpoint, "fill_value": fill, "time_standard": header.get("time_standard"),
           "title": header.get("title"), "parameter": parameter, "parameter_name": payload.get("parameters", {}).get(parameter, {}).get("longname"),
           "retrieved_at": retrieved_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "time_standard_note": "LST in the POWER time-standard header means Local Solar Time, not land surface temperature",
           "native_resolution_note": "MERRA-2 grid (about 0.5 x 0.625 degrees); value is for the grid cell containing the point"}
    return MonthlySeries(years, months, vals, unit_norm, None, src)


def fetch_power_monthly(parameter: str, lat: float, lon: float, start_year: int, end_year: int,
                        use_cache: bool = True, client: httpx.Client | None = None,
                        total_deadline_s: float | None = None) -> MonthlySeries:
    s = get_settings()
    deadline = time.monotonic() + remaining(s.power_total_deadline_s if total_deadline_s is None else total_deadline_s)
    params = {"parameters": parameter, "community": "AG", "longitude": f"{lon:.4f}", "latitude": f"{lat:.4f}",
              "start": str(start_year), "end": str(end_year), "format": "JSON"}
    cache_dir = get_settings().data_dir / "cache"
    key = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:24]
    cache_file = cache_dir / f"power_{key}.json"
    endpoint = f"{BASE}?" + "&".join(f"{k}={v}" for k, v in params.items())
    if use_cache and cache_file.exists():
        try:
            c = json.loads(cache_file.read_text(encoding="utf-8"))
            series = parse_power_monthly(c["payload"], parameter, endpoint, c["retrieved_at"])
            series.source["cache_hit"] = True
            return series
        except (SourceError, ValueError, KeyError, TypeError):
            log.warning("Invalid POWER cache ignored")
    own = client is None
    client = client or httpx.Client(follow_redirects=False)
    history = []
    try:
        for attempt in range(s.power_max_attempts):
            left = remaining(deadline - time.monotonic())
            if left <= 0:
                raise SourceError("NASA POWER total deadline reached", "timeout", history)
            t0 = time.monotonic()
            wait = None
            try:
                timeout = httpx.Timeout(min(left, s.power_read_timeout_s), connect=min(left, s.power_connect_timeout_s))
                r = bounded_call(lambda: client.get(BASE, params=params, timeout=timeout), left)
                history.append({"http_status": r.status_code, "seconds": round(time.monotonic() - t0, 3)})
                if r.status_code in (429, 500, 502, 503, 504):
                    wait = retry_after(r.headers.get("retry-after"))
                    kind = "quota" if r.status_code == 429 else "service_error"
                else:
                    if r.status_code != 200:
                        raise SourceError(f"NASA POWER returned HTTP {r.status_code}", "auth" if r.status_code in (401, 403) else "invalid_request", history)
                    if "application/json" not in r.headers.get("content-type", "").lower():
                        raise SourceError("POWER returned non-JSON content", "parsing", history)
                    try:
                        payload = r.json()
                    except ValueError:
                        raise SourceError("POWER returned invalid JSON", "parsing", history) from None
                    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
                    series = parse_power_monthly(payload, parameter, endpoint, now)
                    if any(y < start_year or y > end_year for y in series.year):
                        raise SourceError("POWER observations outside requested period", attempts=history)
                    series.source.update(cache_hit=False, attempts=history, content_type=r.headers.get("content-type"))
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    cache_file.write_text(json.dumps({"retrieved_at": now, "payload": payload}), encoding="utf-8")
                    return series
            except (httpx.TimeoutException, TimeoutError) as e:
                kind = "timeout"
                history.append({"kind": kind, "error": type(e).__name__})
                if isinstance(e, TimeoutError):
                    break
            except httpx.TransportError as e:
                kind = "network"
                history.append({"kind": kind, "error": type(e).__name__})
            if attempt + 1 == s.power_max_attempts:
                break
            wait = wait if wait is not None else random.uniform(0.5, min(4, 1.5 * 2 ** attempt))
            if wait >= remaining(deadline - time.monotonic()):
                break
            time.sleep(wait)
        raise SourceError(f"NASA POWER unavailable ({kind})", kind, history)
    finally:
        if own:
            client.close()
