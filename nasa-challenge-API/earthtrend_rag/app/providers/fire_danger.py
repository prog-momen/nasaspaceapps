"""Fire DANGER products: GWIS (global WMS) and USGS Fire Danger Forecast (CONUS WMS).

Capability: fire_danger + map_visualization. A fire danger index describes conditions favourable to fire; it is NOT a calibrated
probability of ignition, does not show that a fire exists and says nothing about the cause.

GWIS (verified 2026-11-14): the official GWIS page "Data and services" lists the products (e.g. Fire Danger Forecast 1 day,
ECMWF 8 km / NASA GEOS-5, FWI, FFMC, DMC, DC, ISI, BUI, KBDI, MARK-5, NFDRS) and references maps.effis.emergency.copernicus.eu.
That host answers an OGC WMS GetCapabilities (/gwis): product list, abstract, time dimension, global bbox. GetMap works (PNG). A
GetFeatureInfo numeric query was probed: `<product>.query` layers return only the grid-cell location, no value -> numeric point
queries are NOT available; the products are visualisation layers here.

USGS (verified 2026-11-14): the official "Data Services" page lists OGC WMS services (dmsdata.cr.usgs.gov/geoserver). Coverage is the
contiguous US. GetFeatureInfo returns a PALETTE_INDEX (colour class index), not a documented calibrated index value, so only that
class index is reported, with that caveat. Official docs pages on usgs.gov were blocked (HTTP 403 from CloudFront) for programmatic fetch.
"""
from __future__ import annotations

import re
import time

from app.providers.base import ProviderError, envelope, fail, http_json, strict, validate_point

GWIS_WMS = "https://maps.effis.emergency.copernicus.eu/gwis"
GWIS_LINKS = ["https://gwis.jrc.ec.europa.eu/applications/data-and-services", "https://gwis.jrc.ec.europa.eu/applications", "https://gwis.jrc.ec.europa.eu/about-gwis"]
USGS_LINKS = ["https://firedanger.cr.usgs.gov/apps/data-services-page", "https://www.usgs.gov/fire-danger-forecast/data", "https://www.usgs.gov/fire-danger-forecast"]
USGS_BASE = "https://dmsdata.cr.usgs.gov/geoserver"
USGS_BBOX = (-128.5434, 22.4763, -65.3919, 51.7788)   # from the WMS capabilities (west, south, east, north)
USGS_PRODUCTS = {"wfpi": ("Wildland Fire Potential Index forecast", "wfpi-forecast"), "wlfp": ("WFPI-based Large Fire Probability (class map)", "wlfp-forecast"),
                 "wfsp": ("WFPI-based Fire Spread Probability (class map)", "wfsp-forecast")}
FAMILY = re.compile(r"^(ecmwf|nasa_geos5|mf025|mf010)\.(fwi|ffmc|dmc|dc|isi|bui|anomaly|ranking|mark5\.\w+|nfdrs\.\w+)$")
CAVEAT = ("A fire danger index is not a calibrated probability of fire, does not show that a fire exists and does not establish a cause.")


def _gwis_layers() -> tuple[list[dict], dict]:
    xml, meta = http_json("gwis", "GET", GWIS_WMS, params={"service": "WMS", "request": "GetCapabilities"}, parse="text", ttl=6 * 3600)
    out = []
    for m in re.finditer(r"<Layer[^>]*>\s*<Name>([^<]+)</Name>(.*?)</Layer>", xml, re.S):
        name, body = m.group(1), m.group(2)
        if not FAMILY.match(name):
            continue
        ab = re.search(r"<Abstract>([^<]*)</Abstract>", body)
        dim = re.search(r'<Dimension name="time"([^>]*)>([^<]*)</Dimension>', body)
        dflt = re.search(r'default="([^"]*)"', dim.group(1)) if dim else None
        out.append({"layer": name, "abstract": (ab.group(1).strip() if ab else None), "time_range": dim.group(2).strip() if dim else None,
                    "default_valid_time": dflt.group(1) if dflt else None})
    return out, meta


def gwis_products(keyword: str | None = None) -> dict:
    t0 = time.monotonic()
    try:
        layers, meta = _gwis_layers()
    except ProviderError as e:
        return fail("GWIS", "Fire Danger Forecast (WMS)", "fire_danger", e, source_links=GWIS_LINKS)
    if keyword:
        k = keyword.lower()
        layers = [x for x in layers if k in x["layer"].lower() or (x["abstract"] and k in x["abstract"].lower())]
    prods = [{"layer": x["layer"], "name": x["layer"], "definition": x["abstract"] or "definition not provided by the service",
              "valid_time_range": x["time_range"], "default_valid_time": x["default_valid_time"],
              "units": "index value (units not stated by the service)", "coverage": "global (service bounding box -180,-90,180,90)",
              "forecast_horizon": "portal lists 'Fire Danger Forecast (1 day forecast)'; per-layer horizon is not stated in the capabilities",
              "issue_time": None,
              "map": {"type": "wms_overlay", "url": GWIS_WMS, "layers": x["layer"], "version": "1.3.0", "format": "image/png", "transparent": True,
                      "attribution": "GWIS / Copernicus EMS (JRC)"}} for x in layers]
    return strict(envelope("GWIS", "Fire Danger Forecast (OGC WMS)", "fire_danger", "ok" if prods else "no_data", None if prods else "NO_MATCH",
                           None if prods else "No GWIS fire-danger layer matched.", variables=[p["layer"] for p in prods],
                           actual={"coverage": "global", "n_products": len(prods)}, live=meta["live"], cache=meta["cache"], retrieved_at=meta["retrieved_at"],
                           duration_ms=int((time.monotonic() - t0) * 1000), source_links=GWIS_LINKS + [f"{GWIS_WMS}?service=WMS&request=GetCapabilities"],
                           attribution="GWIS - Global Wildfire Information System (EC JRC / Copernicus EMS). Check the GWIS data licence before reuse.",
                           license="see https://gwis.jrc.ec.europa.eu/applications/data-and-services (terms of use link)",
                           limitations=[CAVEAT, "Map visualisation only: a GetFeatureInfo numeric query was tested and returns only the grid-cell location (no value).",
                                        "Issue time is not published by the WMS; the valid time is the TIME parameter (service default shown)."],
                           data={"products": prods}, artifacts=[{"type": "wms_overlay", **p["map"], "title": p["layer"]} for p in prods[:6]]
                           + [{"type": "table", "title": "GWIS fire danger layers", "columns": ["layer", "definition", "valid_time_range", "default_valid_time"],
                               "rows": [[p["layer"], (p["definition"] or "")[:200], p["valid_time_range"], p["default_valid_time"]] for p in prods]}]))


def usgs_products() -> list[dict]:
    out = []
    for key, (name, stem) in USGS_PRODUCTS.items():
        for day in range(1, 8):
            ws = f"firedanger_{stem}-{day}_conus_day_data"
            out.append({"product": key, "name": f"{name} - day {day}", "workspace_layer": f"{stem}-{day}_conus_day_data", "wms": f"{USGS_BASE}/{ws}/wms", "lead_day": day})
    return out


def usgs_point(lat: float, lon: float, product: str = "wfpi", day: int = 1) -> dict:
    err = validate_point(lat, lon)
    if err:
        return envelope("USGS Fire Danger Forecast", product, "fire_danger", "invalid_request", "INVALID_POINT", err)
    if product not in USGS_PRODUCTS or not (1 <= int(day) <= 7):
        return envelope("USGS Fire Danger Forecast", product, "fire_danger", "invalid_request", "INVALID_PRODUCT",
                        f"product must be one of {list(USGS_PRODUCTS)} and day 1..7")
    w, s, e, n = USGS_BBOX
    if not (w <= lon <= e and s <= lat <= n):
        return envelope("USGS Fire Danger Forecast", product, "fire_danger", "unsupported_region", "OUTSIDE_CONUS",
                        "The USGS Fire Danger Forecast covers the contiguous United States only; this point is outside. Use GWIS (global) layers instead.",
                        request={"latitude": lat, "longitude": lon}, actual={"coverage_bbox": list(USGS_BBOX)}, source_links=USGS_LINKS)
    name, stem = USGS_PRODUCTS[product]
    layer = f"{stem}-{int(day)}_conus_day_data"
    url = f"{USGS_BASE}/firedanger_{layer}/wms"
    d = 0.05
    params = {"service": "WMS", "version": "1.3.0", "request": "GetFeatureInfo", "layers": layer, "query_layers": layer, "crs": "EPSG:4326",
              "bbox": f"{lat - d},{lon - d},{lat + d},{lon + d}", "width": 101, "height": 101, "i": 50, "j": 50, "info_format": "application/json"}
    t0 = time.monotonic()
    try:
        j, meta = http_json("usgs", "GET", url, params=params, ttl=1800)
        caps, _ = http_json("usgs", "GET", url, params={"service": "wms", "version": "1.3.0", "request": "GetCapabilities"}, parse="text", ttl=3600)
    except ProviderError as ex:
        return fail("USGS Fire Danger Forecast", name, "fire_danger", ex, source_links=USGS_LINKS)
    feats = j.get("features") or []
    dm = re.search(r'<Dimension name="time"[^>]*default="([^"]+)"', caps)
    times = re.search(r'<Dimension name="time"[^>]*>([^<]+)</Dimension>', caps)
    valid = dm.group(1) if dm else (times.group(1).split(",")[-1].strip() if times else None)
    if not feats:
        return envelope("USGS Fire Danger Forecast", name, "fire_danger", "no_data", "NO_DATA_AT_POINT", "The service returned no value at this point (outside the data mask).",
                        live=meta["live"], source_links=USGS_LINKS)
    idx = feats[0]["properties"].get("PALETTE_INDEX")
    return strict(envelope("USGS Fire Danger Forecast", name, "fire_danger", "ok", variables=[f"{product}_palette_index"],
                           request={"latitude": lat, "longitude": lon, "day": day}, actual={"valid_time": valid, "issue_time": None, "lead_day": int(day), "coverage_bbox": list(USGS_BBOX)},
                           units={"palette_index": "colour-class index of the published map (not a calibrated index value)"}, temporal_resolution="daily forecast",
                           live=meta["live"], cache=meta["cache"], retrieved_at=meta["retrieved_at"], duration_ms=int((time.monotonic() - t0) * 1000),
                           source_links=USGS_LINKS + [url + "?service=wms&version=1.3.0&request=GetCapabilities"], attribution="USGS Fire Danger Forecast (public domain, USGS)",
                           limitations=[CAVEAT, "GetFeatureInfo returns only the map's palette class index; its mapping to index values/probability classes is in the USGS legend, "
                                        "which could not be fetched programmatically. Treat it as a map class, not a physical quantity.", "CONUS only."],
                           data={"palette_index": idx}, artifacts=[{"type": "wms_overlay", "url": url, "layers": layer, "version": "1.3.0", "format": "image/png", "transparent": True,
                                                                      "title": name, "attribution": "USGS Fire Danger Forecast"}]))


def danger_for_location(lat: float | None, lon: float | None) -> dict:
    """Route to the right fire-danger source(s) for a location and say why."""
    gw = gwis_products("fwi")
    res = {"gwis": gw, "usgs": None, "routing": []}
    if lat is not None and lon is not None:
        w, s, e, n = USGS_BBOX
        if w <= lon <= e and s <= lat <= n:
            res["usgs"] = usgs_point(lat, lon)
            res["routing"].append("Location is inside the contiguous US: USGS WFPI (class index) and GWIS FWI layers are both available.")
        else:
            res["routing"].append("Location is outside the contiguous US: USGS Fire Danger Forecast does not apply; GWIS (global) layers are used for visualisation.")
    return res
