"""Copernicus Data Space Ecosystem: STAC scene DISCOVERY (public, no credentials) and an optional NDVI processing path.

Verified 2026-11-14: https://stac.dataspace.copernicus.eu/v1/ (STAC 1.0, POST /search) answers without authentication; items carry
eo:cloud_cover, a `thumbnail` asset (publicly fetchable) and asset links (s3://eodata/... which need CDSE S3/OData credentials).

Capabilities: satellite_discovery = VERIFIED LIVE. satellite_processing (NDVI via the Sentinel Hub Statistical API on
sh.dataspace.copernicus.eu) = IMPLEMENTED, needs OAuth client credentials (CDSE_CLIENT_ID / CDSE_CLIENT_SECRET); not live-tested here.
"""
from __future__ import annotations

import time
from datetime import timedelta
from urllib.parse import quote

from app.config import load_credential
from app.providers.base import ProviderError, envelope, fail, http_json, parse_date, strict, validate_bbox

PROVIDER = "Copernicus Data Space"
STAC = "https://stac.dataspace.copernicus.eu/v1"
LINKS = ["https://documentation.dataspace.copernicus.eu/APIs/STAC.html", "https://dataspace.copernicus.eu/analyse/apis",
         "https://documentation.dataspace.copernicus.eu/APIs/SentinelHub.html", "https://documentation.dataspace.copernicus.eu/APIs/openEO.html"]
SETUP = {"env": "CDSE_CLIENT_ID, CDSE_CLIENT_SECRET", "register": "https://dataspace.copernicus.eu/ (free account)",
         "steps": "Create a free CDSE account, open Dashboard > User settings > OAuth clients, create a client, then set CDSE_CLIENT_ID / CDSE_CLIENT_SECRET in the backend .env.",
         "permissions": "Sentinel Hub Process/Statistical API quota of the free account (processing units apply)"}
DEFAULT_COLLECTIONS = ["sentinel-2-l2a", "sentinel-2-l1c", "sentinel-1-grd", "sentinel-3-olci-1-efr-ntc", "sentinel-3-slstr-lst-ntc", "landsat-ot-l2"]
MAX_BBOX_DEG, MAX_DAYS, MAX_ITEMS = 5.0, 366, 20

NDVI_EVALSCRIPT = """//VERSION=3
function setup(){return{input:[{bands:["B04","B08","SCL","dataMask"]}],output:[{id:"ndvi",bands:1},{id:"dataMask",bands:1}]};}
function evaluatePixel(s){
  // SCL classes excluded: 0 no data, 1 saturated/defective, 3 cloud shadow, 8/9 cloud medium/high prob, 10 thin cirrus, 11 snow/ice
  var bad=[0,1,3,8,9,10,11].indexOf(s.SCL)>=0;
  // invalid reflectance (zero-filled tile edges give B04=B08=0 -> NDVI exactly -1; values outside 0..1.5 are not valid L2A reflectance)
  var refl=s.B04>0&&s.B08>0&&s.B04<=1.5&&s.B08<=1.5;
  var ndvi=(s.B08-s.B04)/(s.B08+s.B04);   // L2A reflectance is already scaled to 0-1 by Sentinel Hub
  return{ndvi:[ndvi],dataMask:[(s.dataMask===1&&!bad&&refl&&isFinite(ndvi))?1:0]};}"""


def preview_url(thumb: str | None) -> str | None:
    return f"/api/preview?u={quote(thumb, safe='')}" if thumb else None


def search_scenes(bbox: list[float], start: str, end: str, collection: str = "sentinel-2-l2a", max_cloud: float | None = 30, limit: int = 8) -> dict:
    err = validate_bbox(bbox, MAX_BBOX_DEG)
    if err:
        return envelope(PROVIDER, collection, "satellite_discovery", "invalid_request", "INVALID_BBOX", err, source_links=LINKS)
    try:
        s, e = parse_date(start, "start"), parse_date(end, "end")
    except ProviderError as ex:
        return envelope(PROVIDER, collection, "satellite_discovery", "invalid_request", "INVALID_DATE", str(ex), source_links=LINKS)
    if not s or not e or e < s:
        return envelope(PROVIDER, collection, "satellite_discovery", "invalid_request", "INVALID_DATE_RANGE", "start and end are required (YYYY-MM-DD) and end >= start", source_links=LINKS)
    if (e - s).days > MAX_DAYS:
        return envelope(PROVIDER, collection, "satellite_discovery", "unsupported_request", "RANGE_TOO_LONG", f"Prototype limit is {MAX_DAYS} days per search.", source_links=LINKS)
    if max_cloud is not None and not (0 <= float(max_cloud) <= 100):
        return envelope(PROVIDER, collection, "satellite_discovery", "invalid_request", "INVALID_CLOUD", "max_cloud must be 0..100", source_links=LINKS)
    t0 = time.monotonic()
    try:
        import re as _re
        if not _re.fullmatch(r"[a-z0-9][a-z0-9_\-]{2,60}", collection):
            return envelope(PROVIDER, collection, "satellite_discovery", "invalid_request", "UNKNOWN_COLLECTION",
                            f"Invalid collection id. Examples: {', '.join(DEFAULT_COLLECTIONS)}", source_links=LINKS)
        body = {"collections": [collection], "bbox": [float(x) for x in bbox], "datetime": f"{s.isoformat()}T00:00:00Z/{e.isoformat()}T23:59:59Z",
                "limit": max(1, min(int(limit), MAX_ITEMS)), "sortby": [{"field": "properties.datetime", "direction": "desc"}]}
        if max_cloud is not None:
            body["query"] = {"eo:cloud_cover": {"lte": float(max_cloud)}}
        d, meta = http_json("cdse", "POST", f"{STAC}/search", json_body=body, ttl=1800)
    except ProviderError as ex:
        return fail(PROVIDER, collection, "satellite_discovery", ex, source_links=LINKS)
    scenes = []
    for f in d.get("features", []):
        p, a = f["properties"], f.get("assets", {})
        th = (a.get("thumbnail") or {}).get("href")
        scenes.append({"id": f["id"], "datetime": p.get("datetime"), "cloud_cover_percent": p.get("eo:cloud_cover"), "platform": p.get("platform"),
                       "collection": f.get("collection"), "bbox": f.get("bbox"), "geometry": f.get("geometry"), "thumbnail": th, "preview": preview_url(th),
                       "n_assets": len(a), "bands_available": sorted(k for k in a if k.startswith("B"))[:14],
                       "asset_access": "s3://eodata/... assets need CDSE credentials; the thumbnail is public",
                       "links": [l["href"] for l in f.get("links", []) if l.get("rel") in ("self",)]})
    arts = [{"type": "scenes", "title": f"{collection} scenes", "scenes": scenes},
            {"type": "map_polygons", "title": "Scene footprints", "polygons": [{"label": f"{x['id']} · {x['datetime']} · cloud {x['cloud_cover_percent']}%", "geometry": x["geometry"]} for x in scenes if x["geometry"]], "bbox": bbox},
            {"type": "table", "title": "Scenes", "columns": ["id", "datetime", "cloud_cover_percent", "platform"], "rows": [[x["id"], x["datetime"], x["cloud_cover_percent"], x["platform"]] for x in scenes]}]
    return strict(envelope(
        PROVIDER, collection, "satellite_discovery", "ok" if scenes else "no_data", None if scenes else "NO_SCENES",
        None if scenes else "No scenes matched (try a wider date range or a higher cloud-cover limit).", variables=["scene_metadata"],
        request={"bbox": bbox, "start": start, "end": end, "max_cloud": max_cloud}, actual={"n_scenes": len(scenes), "sorted": "newest first",
        "matched_total": d.get("numberMatched")}, temporal_resolution="per acquisition", live=meta["live"], cache=meta["cache"], retrieved_at=meta["retrieved_at"],
        duration_ms=int((time.monotonic() - t0) * 1000), source_links=LINKS,
        attribution="Contains modified Copernicus Sentinel data (ESA/Copernicus). Free, full and open access.", license="Copernicus Sentinel data terms (free, full, open)",
        quality={"cloud_cover_note": "eo:cloud_cover is a scene-level percentage from the product metadata, not a per-pixel mask"},
        limitations=["DISCOVERY ONLY: no pixel data were downloaded or analysed. Thumbnails are quick-look previews, not analysis products.",
                     "Downloading bands needs CDSE credentials; vegetation indices need correct bands, SCL masking and resolution handling (see satellite_processing)."],
        data={"scenes": scenes}, artifacts=arts))


def ndvi_statistics(bbox: list[float], start: str, end: str, max_cloud: float = 30, interval_days: int = 10) -> dict:
    """NDVI mean per interval from Sentinel-2 L2A via the Sentinel Hub Statistical API (CDSE). Needs OAuth client credentials."""
    cid, sec = load_credential("CDSE_CLIENT_ID"), load_credential("CDSE_CLIENT_SECRET")
    if not cid or not sec:
        return envelope(PROVIDER, "Sentinel-2 L2A NDVI (Statistical API)", "satellite_processing", "needs_credentials", "CDSE_CLIENT_CREDENTIALS_MISSING",
                        "NDVI processing needs a CDSE OAuth client (free). Scene discovery works without it.", setup=SETUP, source_links=LINKS,
                        limitations=["Implemented but not live-tested: requires credentials."])
    err = validate_bbox(bbox, 1.0)
    if err:
        return envelope(PROVIDER, "NDVI", "satellite_processing", "invalid_request", "INVALID_BBOX", err + " (processing limit 1 degree)", source_links=LINKS)
    s, e = parse_date(start), parse_date(end)
    token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    try:
        import httpx
        tok = httpx.post(token_url, data={"grant_type": "client_credentials", "client_id": cid.get_secret_value(), "client_secret": sec.get_secret_value()}, timeout=20)
        if tok.status_code != 200:
            return envelope(PROVIDER, "NDVI", "satellite_processing", "needs_credentials", "CDSE_TOKEN_REJECTED", f"CDSE rejected the OAuth client (HTTP {tok.status_code}).", setup=SETUP)
        token = tok.json()["access_token"]
        body = {"input": {"bounds": {"bbox": bbox, "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}},
                          "data": [{"type": "sentinel-2-l2a", "dataFilter": {"mosaickingOrder": "leastCC", "maxCloudCoverage": max_cloud}}]},
                "aggregation": {"timeRange": {"from": f"{s}T00:00:00Z", "to": f"{e}T23:59:59Z"}, "aggregationInterval": {"of": f"P{int(interval_days)}D"},
                                "evalscript": NDVI_EVALSCRIPT, "resx": 0.0002, "resy": 0.0002}, "calculations": {"default": {}}}
        r = httpx.post("https://sh.dataspace.copernicus.eu/api/v1/statistics", json=body, headers={"Authorization": f"Bearer {token}"}, timeout=60)
        if r.status_code != 200:
            return envelope(PROVIDER, "NDVI", "satellite_processing", "upstream_error", f"HTTP_{r.status_code}", r.text[:200], source_links=LINKS)
        rows = []
        for item in r.json().get("data", []):
            st = item["outputs"]["ndvi"]["bands"]["B0"]["stats"]
            rows.append({"from": item["interval"]["from"][:10], "to": item["interval"]["to"][:10], "mean": st.get("mean"), "min": st.get("min"), "max": st.get("max"),
                         "valid_pixels": st.get("sampleCount", 0) - st.get("noDataCount", 0), "no_data_pixels": st.get("noDataCount")})
    except Exception as ex:
        return envelope(PROVIDER, "NDVI", "satellite_processing", "upstream_error", "PROCESSING_FAILED", f"{type(ex).__name__}", source_links=LINKS)
    return strict(envelope(PROVIDER, "Sentinel-2 L2A NDVI (Statistical API)", "satellite_processing", "ok" if rows else "no_data", variables=["NDVI"], units={"ndvi": "unitless (-1..1)"},
                           request={"bbox": bbox, "start": start, "end": end}, live=True, source_links=LINKS, attribution="Contains modified Copernicus Sentinel data",
                           limitations=["NDVI = (B08-B04)/(B08+B04) on L2A reflectance; SCL-masked (clouds, shadows, cirrus, snow, defective); resolution 0.0002 deg (~20 m).",
                                        "Cloud-free pixel counts vary by interval; intervals with few valid pixels are unreliable."],
                           data={"intervals": rows}, artifacts=[{"type": "line_chart", "title": "NDVI mean per interval", "x": [x["from"] for x in rows],
                                                                  "series": [{"name": "NDVI", "unit": "", "y": [x["mean"] for x in rows], "kind": "line"}]}]))


def check_oauth() -> dict:
    """OAuth client-credentials check only (authentication, not processing)."""
    cid, sec = load_credential("CDSE_CLIENT_ID"), load_credential("CDSE_CLIENT_SECRET")
    if not cid or not sec:
        return envelope(PROVIDER, "CDSE OAuth", "satellite_processing", "needs_credentials", "CDSE_CLIENT_CREDENTIALS_MISSING", "CDSE_CLIENT_ID / CDSE_CLIENT_SECRET are not set.", setup=SETUP, source_links=LINKS)
    import httpx
    try:
        tok = httpx.post("https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
                         data={"grant_type": "client_credentials", "client_id": cid.get_secret_value(), "client_secret": sec.get_secret_value()}, timeout=20)
    except Exception as ex:
        return envelope(PROVIDER, "CDSE OAuth", "satellite_processing", "upstream_error", "CDSE_UNREACHABLE", type(ex).__name__, source_links=LINKS)
    ok = tok.status_code == 200 and "access_token" in tok.json()
    return envelope(PROVIDER, "CDSE OAuth", "satellite_processing", "ok" if ok else "needs_credentials", None if ok else "CDSE_TOKEN_REJECTED",
                    message="OAuth token obtained (authentication only; no processing was run)." if ok else f"CDSE rejected the OAuth client (HTTP {tok.status_code}).", live=True, source_links=LINKS)
