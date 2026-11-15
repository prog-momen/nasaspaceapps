"""NASA FIRMS active-fire DETECTIONS (area API). Requires a free MAP_KEY (env FIRMS_MAP_KEY).

Verified 2026-11-14 from the official pages: GET /api/area/csv/[MAP_KEY]/[SOURCE]/[west,south,east,north]/[DAY_RANGE 1..5]/[DATE],
limit 5,000 transactions / 10 min per key (larger requests count as several), sources LANDSAT_NRT (US/Canada), MODIS_NRT/SP,
VIIRS_SNPP_NRT/SP, VIIRS_NOAA20_NRT/SP, VIIRS_NOAA21_NRT/SP. A request with an invalid key returns HTTP 400 "Invalid MAP_KEY.".

A detection is a thermal anomaly in a satellite pixel, NOT a confirmed wildfire incident, burned area or an incident count.
"""
from __future__ import annotations

import csv
import io
import time
from collections import Counter
from datetime import date, timedelta

from app.config import load_credential
from app.providers.base import ProviderError, envelope, fail, http_json, parse_date, sanitize, strict, validate_bbox

PROVIDER = "NASA FIRMS"
BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
SOURCES = ["VIIRS_SNPP_NRT", "VIIRS_SNPP_SP", "VIIRS_NOAA20_NRT", "VIIRS_NOAA20_SP", "VIIRS_NOAA21_NRT", "VIIRS_NOAA21_SP",
           "MODIS_NRT", "MODIS_SP", "LANDSAT_NRT"]
LINKS = ["https://firms.modaps.eosdis.nasa.gov/api/area/", "https://firms.modaps.eosdis.nasa.gov/content/academy/data_api/firms_api_use.html",
         "https://firms.modaps.eosdis.nasa.gov/api/map_key/"]
SETUP = {"env": "FIRMS_MAP_KEY", "register": "https://firms.modaps.eosdis.nasa.gov/api/map_key/",
         "steps": "Enter your email at the link; the free MAP_KEY is emailed. Put FIRMS_MAP_KEY=<key> in the backend .env (never in the chat).",
         "permissions": "none beyond the key (free; 5000 transactions / 10 min)"}
CAVEAT = ("Detections are satellite thermal anomalies. They are not confirmed wildfire incidents, burned area or an incident count; "
          "several detections can belong to one fire, and non-fire heat sources (industrial flares, gas, volcanoes) can appear.")
MAX_BBOX_DEG = 10.0
MAX_ROWS = 5000


PREFERRED_NRT = ["VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT", "VIIRS_SNPP_NRT", "MODIS_NRT"]
PREFERRED_SP = ["VIIRS_NOAA20_SP", "VIIRS_SNPP_SP", "VIIRS_NOAA21_SP", "MODIS_SP"]


def default_source(day: date) -> str:
    """Static fallback when the availability endpoint cannot be read. NRT covers recent days; older dates need standard processing (SP)."""
    return "VIIRS_NOAA20_NRT" if (date.today() - day).days <= 7 else "VIIRS_NOAA20_SP"


def availability(key: str) -> dict[str, tuple[str, str]] | None:
    """Per-sensor [min_date, max_date] from the official data_availability endpoint (cached 1 h). None if it cannot be read.
    Needed because a sensor with no data for the requested dates returns a header-only CSV, which is NOT 'zero fires'
    (observed 2026-11-14: VIIRS_SNPP_NRT had no data after 2026-11-02)."""
    try:
        text, _ = http_json("firms", "GET", f"https://firms.modaps.eosdis.nasa.gov/api/data_availability/csv/{key}/ALL", parse="text", ttl=3600,
                            secrets=(key,), cache_params={"avail": "ALL"})
    except Exception:
        return None
    out = {}
    for r in csv.DictReader(io.StringIO(text)):
        if r.get("data_id") and r.get("min_date") and r.get("max_date"):
            out[r["data_id"]] = (r["min_date"], r["max_date"])
    return out or None


def pick_source(avail: dict | None, d0: date | None, day_range: int) -> str:
    """Newest-covering sensor for the requested window; prefers VIIRS NOAA-20 > NOAA-21 > S-NPP > MODIS."""
    first = d0 or date.today()
    last = first + timedelta(days=int(day_range) - 1)
    if not avail:
        return default_source(first)
    order = PREFERRED_NRT + PREFERRED_SP if (date.today() - first).days <= 60 else PREFERRED_SP + PREFERRED_NRT
    wanted_last = min(last, date.today())
    for s in order:
        need = wanted_last if d0 else date.today() - timedelta(days=2)      # no date given: the newest days the sensor has must be recent
        if s in avail and avail[s][0] <= (first if d0 else need).isoformat() and avail[s][1] >= need.isoformat():
            return s
    return default_source(first)


def _num(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def parse_csv(text: str) -> list[dict]:
    rows = []
    for r in csv.DictReader(io.StringIO(text)):
        lat, lon = _num(r.get("latitude")), _num(r.get("longitude"))
        if lat is None or lon is None:
            continue
        hhmm = (r.get("acq_time") or "").strip().zfill(4)          # FIRMS drops leading zeros ("34" = 00:34 UTC)
        iso = f"{r.get('acq_date')}T{hhmm[:2]}:{hhmm[2:]}:00Z" if r.get("acq_date") and hhmm.isdigit() else None
        rows.append({"latitude": lat, "longitude": lon, "acq_date": r.get("acq_date"), "acq_time": hhmm, "acq_datetime_utc": iso,
                     "satellite": r.get("satellite"), "instrument": r.get("instrument"), "confidence": r.get("confidence"),
                     "frp_mw": _num(r.get("frp")), "daynight": r.get("daynight"),
                     "brightness_k": _num(r.get("bright_ti4") or r.get("brightness")), "scan": _num(r.get("scan")), "track": _num(r.get("track"))})
    return rows


def detections(bbox: list[float], start: str | None = None, day_range: int = 2, source: str | None = None) -> dict:
    err = validate_bbox(bbox, MAX_BBOX_DEG)
    if err:
        return envelope(PROVIDER, "area API", "active_fire_detection", "invalid_request", "INVALID_BBOX", err, source_links=LINKS)
    if not (1 <= int(day_range) <= 5):
        return envelope(PROVIDER, "area API", "active_fire_detection", "invalid_request", "INVALID_DAY_RANGE", "day_range must be 1..5 (API limit)", source_links=LINKS)
    try:
        d0 = parse_date(start, "start") if start else None
    except ProviderError as e:
        return envelope(PROVIDER, "area API", "active_fire_detection", "invalid_request", "INVALID_DATE", str(e), source_links=LINKS)
    if d0 and d0 > date.today():
        return envelope(PROVIDER, "area API", "active_fire_detection", "unsupported_request", "FUTURE_DATE", "Detections cannot exist for future dates.", source_links=LINKS)
    if source is not None and source not in SOURCES:
        return envelope(PROVIDER, "area API", "active_fire_detection", "invalid_request", "UNKNOWN_SOURCE", f"source must be one of {SOURCES}", source_links=LINKS)
    key = load_credential("FIRMS_MAP_KEY")
    if not key:
        src0 = source or default_source(d0 or date.today())
        return envelope(PROVIDER, src0, "active_fire_detection", "needs_credentials", "FIRMS_MAP_KEY_MISSING",
                        "FIRMS needs a free MAP_KEY. Add FIRMS_MAP_KEY to the backend .env and restart.", setup=SETUP, source_links=LINKS,
                        request={"bbox": bbox, "start": start, "day_range": day_range, "source": src0}, limitations=[CAVEAT])
    k = key.get_secret_value()
    avail = availability(k)
    src = source or pick_source(avail, d0, int(day_range))
    if avail and src in avail:
        first_req = (d0 or date.today() - timedelta(days=2)).isoformat()
        if avail[src][1] < first_req or (d0 and avail[src][0] > d0.isoformat()):
            return envelope(PROVIDER, src, "active_fire_detection", "no_data", "SENSOR_DATA_NOT_AVAILABLE",
                            f"FIRMS has no {src} data for these dates (available {avail[src][0]} .. {avail[src][1]}). This is a coverage gap, not evidence of zero fires.",
                            source_links=LINKS, request={"bbox": bbox, "start": start, "day_range": day_range, "source": src}, limitations=[CAVEAT])
    area = ",".join(f"{float(v):g}" for v in bbox)
    url = f"{BASE}/{k}/{src}/{area}/{int(day_range)}" + (f"/{d0.isoformat()}" if d0 else "")
    t0 = time.monotonic()
    try:
        text, meta = http_json("firms", "GET", url, parse="text", ttl=600, secrets=(k,), cache_params={"area": area, "src": src, "d": str(d0), "n": day_range})
    except ProviderError as e:
        if e.http_status == 400 and "map_key" in str(e).lower():
            return envelope(PROVIDER, src, "active_fire_detection", "needs_credentials", "FIRMS_MAP_KEY_INVALID",
                            "FIRMS rejected the MAP_KEY (Invalid MAP_KEY). Check FIRMS_MAP_KEY in the backend .env.", setup=SETUP, source_links=LINKS)
        return fail(PROVIDER, src, "active_fire_detection", e, source_links=LINKS)
    low = text.strip().lower()
    if low.startswith("invalid") or "exceeded" in low[:120]:
        return envelope(PROVIDER, src, "active_fire_detection", "upstream_error" if "exceed" in low else "needs_credentials",
                        "FIRMS_REJECTED", sanitize(text[:160], k), setup=SETUP, source_links=LINKS)
    rows = parse_csv(text)
    truncated = len(rows) > MAX_ROWS
    rows = rows[:MAX_ROWS]
    by_day = Counter(r["acq_date"] for r in rows)
    by_conf = Counter(str(r["confidence"]) for r in rows)
    frp = [r["frp_mw"] for r in rows if r["frp_mw"] is not None]
    first = min((r["acq_date"] for r in rows), default=None)
    last = max((r["acq_date"] for r in rows), default=None)
    end_req = (d0 + timedelta(days=int(day_range) - 1)).isoformat() if d0 else None
    arts = [{"type": "map_points", "title": f"{src} detections (thermal anomalies, not confirmed incidents)",
             "points": [{"lat": r["latitude"], "lon": r["longitude"], "label": f"{r['acq_date']} {r['acq_time']} UTC · {r['satellite']} · conf {r['confidence']} · FRP {r['frp_mw']} MW",
                         "frp": r["frp_mw"]} for r in rows[:2000]], "bbox": bbox},
            {"type": "table", "title": "Detections", "columns": ["acq_date", "acq_time_utc", "latitude", "longitude", "satellite", "instrument", "confidence", "frp_mw", "daynight", "brightness_k"],
             "rows": [[r["acq_date"], r["acq_time"], r["latitude"], r["longitude"], r["satellite"], r["instrument"], r["confidence"], r["frp_mw"], r["daynight"], r["brightness_k"]] for r in rows]},
            {"type": "line_chart", "title": "Detections per day", "x": sorted(by_day), "series": [{"name": "detections", "unit": "count", "kind": "bar", "y": [by_day[d] for d in sorted(by_day)]}]}]
    return strict(envelope(
        PROVIDER, src, "active_fire_detection", "ok" if rows else "no_data", None if rows else "ZERO_DETECTIONS",
        None if rows else "Valid request (sensor data available), zero detections returned. No detections in this area and period (this does not prove there was no fire: clouds, overpass timing and pixel size limit detection).",
        variables=["fire_detection"], request={"bbox": bbox, "start": start, "day_range": day_range, "source": src},
        actual={"period": {"first": first, "last": last, "requested_end": end_req}, "n_detections": len(rows), "time_standard": "UTC"},
        units={"frp": "MW", "brightness": "K", "acq_time": "HHMM UTC"}, temporal_resolution="per satellite overpass", live=meta["live"], cache=meta["cache"],
        retrieved_at=meta["retrieved_at"], duration_ms=int((time.monotonic() - t0) * 1000), source_links=LINKS,
        attribution="NASA FIRMS (LANCE/EOSDIS). Acknowledge NASA FIRMS when using the data.", license="NASA open data",
        quality={"sensor_available": (avail or {}).get(src), "by_day": dict(by_day), "by_confidence": dict(by_conf), "frp_total_mw": round(sum(frp), 2) if frp else None,
                 "frp_max_mw": max(frp) if frp else None, "truncated_at_rows": MAX_ROWS if truncated else None},
        limitations=[CAVEAT, "VIIRS confidence is categorical (l/n/h); MODIS confidence is 0-100. Pixel size: VIIRS ~375 m, MODIS ~1 km.",
                     "NRT products can be replaced by standard-processing (SP) products later."],
        data={"detections": rows[:MAX_ROWS]}, artifacts=arts))
