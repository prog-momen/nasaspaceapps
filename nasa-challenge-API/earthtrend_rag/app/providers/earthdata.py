"""NASA Earthdata: CMR dataset/granule DISCOVERY (public), GIBS imagery (VISUALISATION only), granule download and AppEEARS point LST
(both need Earthdata Login credentials).

Verified 2026-11-14 live without credentials: CMR /search/collections.json and /search/granules.json (e.g. MOD11C3 v061, C2565788897-LPCLOUD),
GIBS WMTS tiles (https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/...). Data links returned by CMR (data.lpdaac.earthdatacloud.nasa.gov)
need an Earthdata Login bearer token (EARTHDATA_TOKEN). AppEEARS (https://appeears.earthdatacloud.nasa.gov/api/) needs a username/password
login (EARTHDATA_USERNAME / EARTHDATA_PASSWORD) to create sample tasks; LST product MOD11A2.061 layer LST_Day_1km (scale 0.02 K).

A GIBS layer on the map is a rendered picture. It is never evidence that numbers were downloaded or analysed.
"""
from __future__ import annotations

import json
import re
import time
from datetime import date
from pathlib import Path

from app.config import get_settings, load_credential
from app.providers.base import ProviderError, envelope, fail, http_json, parse_date, sanitize, strict, validate_bbox, validate_point

PROVIDER = "NASA Earthdata"
CMR = "https://cmr.earthdata.nasa.gov/search"
APPEEARS = "https://appeears.earthdatacloud.nasa.gov/api"
LINKS = ["https://www.earthdata.nasa.gov/data/tools/earthdata-search", "https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html",
         "https://www.earthdata.nasa.gov/eosdis/science-system-description/eosdis-components/gibs", "https://urs.earthdata.nasa.gov/"]
SETUP_TOKEN = {"env": "EARTHDATA_TOKEN", "register": "https://urs.earthdata.nasa.gov/users/new",
               "steps": "Create a free Earthdata Login, approve the data-provider applications you need, then generate a User Token at https://urs.earthdata.nasa.gov/profile and set EARTHDATA_TOKEN in the backend .env.",
               "permissions": "read access to the DAAC (e.g. LP DAAC Data Pool) via an approved application"}
SETUP_APPEEARS = {"env": "EARTHDATA_USERNAME, EARTHDATA_PASSWORD", "register": "https://urs.earthdata.nasa.gov/users/new",
                  "steps": "Create a free Earthdata Login and authorise AppEEARS (https://appeears.earthdatacloud.nasa.gov/), then set EARTHDATA_USERNAME / EARTHDATA_PASSWORD in the backend .env.",
                  "permissions": "AppEEARS application authorised for the account"}
_GIBS = json.loads((Path(__file__).parent / "data" / "gibs_layers.json").read_text(encoding="utf-8"))
GIBS_RASTER = {k: v for k, v in _GIBS["layers"].items() if "mapbox" not in " ".join(v["formats"])}


def search_collections(keyword: str, bbox: list[float] | None = None, start: str | None = None, end: str | None = None, limit: int = 8) -> dict:
    if not keyword or len(keyword.strip()) < 2:
        return envelope(PROVIDER, "CMR collections", "dataset_discovery", "invalid_request", "EMPTY_KEYWORD", "keyword is required", source_links=LINKS)
    params: dict = {"keyword": keyword.strip(), "page_size": max(1, min(int(limit), 20)), "sort_key": "-usage_score"}
    if bbox:
        err = validate_bbox(bbox, 360)
        if err:
            return envelope(PROVIDER, "CMR collections", "dataset_discovery", "invalid_request", "INVALID_BBOX", err, source_links=LINKS)
        params["bounding_box"] = ",".join(str(float(x)) for x in bbox)
    if start or end:
        params["temporal"] = f"{start + 'T00:00:00Z' if start else ''},{end + 'T23:59:59Z' if end else ''}"
    t0 = time.monotonic()
    try:
        d, meta = http_json("cmr", "GET", f"{CMR}/collections.json", params=params, ttl=3600)
    except ProviderError as e:
        return fail(PROVIDER, "CMR collections", "dataset_discovery", e, source_links=LINKS)
    cols = [{"concept_id": c.get("id"), "short_name": c.get("short_name"), "version": c.get("version_id"), "title": c.get("title"), "provider": c.get("data_center"),
             "time_start": c.get("time_start"), "time_end": c.get("time_end"), "cloud_hosted": c.get("cloud_hosted"),
             "doi": next((x for x in [c.get("doi")] if x), None), "landing": f"https://cmr.earthdata.nasa.gov/search/concepts/{c.get('id')}.html"}
            for c in d["feed"]["entry"]]
    return strict(envelope(PROVIDER, "CMR collections", "dataset_discovery", "ok" if cols else "no_data", None if cols else "NO_MATCH", None if cols else "No collection matched.",
                           request={"keyword": keyword, "bbox": bbox, "start": start, "end": end}, actual={"n_collections": len(cols)}, live=meta["live"], cache=meta["cache"],
                           retrieved_at=meta["retrieved_at"], duration_ms=int((time.monotonic() - t0) * 1000), source_links=LINKS,
                           attribution="NASA Earthdata CMR", license="NASA open data",
                           limitations=["Discovery only: no data were downloaded. Downloading usually needs Earthdata Login."],
                           data={"collections": cols}, artifacts=[{"type": "table", "title": "Earthdata collections", "columns": ["short_name", "version", "title", "provider", "time_start", "time_end", "concept_id"],
                                                                    "rows": [[c["short_name"], c["version"], c["title"], c["provider"], c["time_start"], c["time_end"], c["concept_id"]] for c in cols]}]))


def search_granules(short_name: str, version: str, bbox: list[float] | None, start: str, end: str, limit: int = 10) -> dict:
    if not short_name or not version:
        return envelope(PROVIDER, "CMR granules", "dataset_discovery", "invalid_request", "MISSING_PRODUCT", "short_name and version are required", source_links=LINKS)
    params = {"short_name": short_name, "version": version, "page_size": max(1, min(int(limit), 50)), "temporal": f"{start}T00:00:00Z,{end}T23:59:59Z"}
    if bbox:
        err = validate_bbox(bbox, 360)
        if err:
            return envelope(PROVIDER, "CMR granules", "dataset_discovery", "invalid_request", "INVALID_BBOX", err, source_links=LINKS)
        params["bounding_box"] = ",".join(str(float(x)) for x in bbox)
    try:
        d, meta = http_json("cmr", "GET", f"{CMR}/granules.json", params=params, ttl=3600)
    except ProviderError as e:
        return fail(PROVIDER, "CMR granules", "dataset_discovery", e, source_links=LINKS)
    gr = []
    for g in d["feed"]["entry"]:
        links = [l["href"] for l in g.get("links", []) if l.get("rel", "").endswith("/data#")]
        gr.append({"title": g.get("title"), "time_start": g.get("time_start"), "time_end": g.get("time_end"), "data_links": links[:3], "size_mb": g.get("granule_size"),
                   "requires_earthdata_login": True})
    return strict(envelope(PROVIDER, f"{short_name}.{version} granules", "dataset_discovery", "ok" if gr else "no_data", None if gr else "NO_GRANULES",
                           request={"short_name": short_name, "version": version, "bbox": bbox, "start": start, "end": end}, actual={"n_granules": len(gr)}, live=meta["live"], cache=meta["cache"],
                           retrieved_at=meta["retrieved_at"], source_links=LINKS, attribution="NASA Earthdata CMR", license="NASA open data",
                           limitations=["Discovery only. Download needs EARTHDATA_TOKEN; reading HDF4/HDF5 products needs extra libraries (not bundled)."],
                           data={"granules": gr}, artifacts=[{"type": "table", "title": "Granules", "columns": ["title", "time_start", "time_end", "size_mb"], "rows": [[g["title"], g["time_start"], g["time_end"], g["size_mb"]] for g in gr]}]))


def gibs_layers() -> dict:
    return {k: {"title": v["title"], "format": v["formats"][0], "tile_matrix_set": v["tile_matrix_set"][0]} for k, v in GIBS_RASTER.items()}


def gibs_overlay(layer: str, day: str) -> dict:
    """Leaflet XYZ template for a GIBS raster layer. VISUALISATION ONLY."""
    if layer not in GIBS_RASTER:
        return envelope(PROVIDER, "GIBS", "map_visualization", "invalid_request", "UNKNOWN_LAYER", f"layer must be one of {sorted(GIBS_RASTER)}", source_links=LINKS)
    try:
        d = parse_date(day, "date")
    except ProviderError as e:
        return envelope(PROVIDER, "GIBS", "map_visualization", "invalid_request", "INVALID_DATE", str(e), source_links=LINKS)
    if not d or d > date.today():
        return envelope(PROVIDER, "GIBS", "map_visualization", "invalid_request", "INVALID_DATE", "date must be a valid past/today date", source_links=LINKS)
    v = GIBS_RASTER[layer]
    ext = "jpg" if "jpeg" in v["formats"][0] else "png"
    level = int(re.search(r"Level(\d+)", v["tile_matrix_set"][0]).group(1))
    url = f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/{layer}/default/{d.isoformat()}/{v['tile_matrix_set'][0]}/{{z}}/{{y}}/{{x}}.{ext}"
    return envelope(PROVIDER, f"GIBS {layer}", "map_visualization", "ok", request={"layer": layer, "date": day}, source_links=LINKS,
                    attribution="Imagery provided by NASA GIBS / EOSDIS", live=None,
                    limitations=["Visualisation only. A displayed GIBS layer does NOT mean numerical data were downloaded or analysed."],
                    data={"tile_url": url, "max_zoom": level}, artifacts=[{"type": "tile_overlay", "title": v["title"], "url": url, "max_zoom": level, "attribution": "NASA GIBS", "analytical": False}])


def download_granule(url: str, dest_dir: Path | None = None, max_mb: int = 200) -> dict:
    """Real download of a CMR data link using the Earthdata bearer token (streamed to disk, size-capped)."""
    tok = load_credential("EARTHDATA_TOKEN")
    if not tok:
        return envelope(PROVIDER, "granule download", "dataset_discovery", "needs_credentials", "EARTHDATA_TOKEN_MISSING", "Downloading Earthdata granules needs EARTHDATA_TOKEN.", setup=SETUP_TOKEN, source_links=LINKS)
    if not re.match(r"^https://[a-z0-9.\-]*(earthdata\.nasa\.gov|earthdatacloud\.nasa\.gov|nasa\.gov)/", url):
        return envelope(PROVIDER, "granule download", "dataset_discovery", "invalid_request", "HOST_NOT_ALLOWED", "Only https NASA Earthdata hosts are allowed.", source_links=LINKS)
    import httpx
    dest = (dest_dir or get_settings().data_dir / "downloads"); dest.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9_.\-]", "_", url.rsplit("/", 1)[-1])[:120] or "granule.bin"
    t = tok.get_secret_value()
    try:
        with httpx.stream("GET", url, headers={"Authorization": f"Bearer {t}"}, follow_redirects=True, timeout=httpx.Timeout(60, connect=10)) as r:
            if r.status_code in (401, 403):
                return envelope(PROVIDER, "granule download", "dataset_discovery", "needs_credentials", "EARTHDATA_TOKEN_REJECTED",
                                f"Earthdata rejected the token (HTTP {r.status_code}); the DAAC application may need approval.", setup=SETUP_TOKEN, source_links=LINKS)
            r.raise_for_status()
            size = 0
            with open(dest / name, "wb") as f:
                for chunk in r.iter_bytes(1 << 20):
                    size += len(chunk)
                    if size > max_mb << 20:
                        f.close(); (dest / name).unlink(missing_ok=True)
                        return envelope(PROVIDER, "granule download", "dataset_discovery", "unsupported_request", "TOO_LARGE", f"Download exceeds {max_mb} MB.", source_links=LINKS)
                    f.write(chunk)
    except Exception as e:
        return envelope(PROVIDER, "granule download", "dataset_discovery", "upstream_error", "DOWNLOAD_FAILED", sanitize(type(e).__name__, t), source_links=LINKS)
    return envelope(PROVIDER, "granule download", "dataset_discovery", "ok", actual={"file": str(dest / name), "bytes": size}, live=True, source_links=LINKS,
                    limitations=["Downloaded the file only; HDF4/HDF5 decoding requires optional libraries (pyhdf/h5py/GDAL)."])


LST_PRODUCT, LST_LAYER, QC_LAYER = "MOD11A2.061", "LST_Day_1km", "QC_Day"
LST_VALID_K = (150.0, 1310.7)         # AppEEARS /product metadata: ValidMin/ValidMax (Kelvin, after the 0.02 scale factor); fill value 0
LST_MAX_ERROR_CLASS = 1               # MODIS LST error class 0: <=1 K, 1: <=2 K, 2: <=3 K, 3: >3 K -> keep <=2 K
LST_FIRST_DATE = date(2000, 2, 18)


def _task_cache_path() -> Path:
    return get_settings().data_dir / "cache" / "appeears_tasks.json"


def _task_cache() -> dict:
    try:
        return json.loads(_task_cache_path().read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_task_cache(d: dict) -> None:
    p = _task_cache_path(); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, indent=1), encoding="utf-8")


def parse_lst_csv(csv_text: str) -> dict:
    """AppEEARS point CSV -> samples with QUALITY FILTERING and unit handling. Pure function (tested offline with a real captured CSV)."""
    import csv, io, statistics
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    if not rows:
        return {"samples": [], "n_total": 0, "n_valid": 0, "filter_reasons": {}, "mean_c": None, "min_c": None, "max_c": None, "scale_factor_applied_by_source": True}
    cols = rows[0].keys()
    col = lambda suffix: next((k for k in cols if k.endswith(suffix)), None)
    c_lst, c_modland, c_err = col("_LST_Day_1km"), col("_QC_Day_MODLAND"), col("_QC_Day_LST_Error")

    def num(r):
        try:
            return float(r[c_lst]) if c_lst and r.get(c_lst) not in (None, "", "nan", "NaN") else None
        except ValueError:
            return None
    raw_vals = [v for v in (num(r) for r in rows) if v is not None]
    scale_applied = not raw_vals or statistics.median(raw_vals) < 1000          # raw DN values are ~7500-65535; scaled Kelvin ~200-350
    reasons: dict[str, int] = {}
    samples = []
    for r in rows:
        v = num(r)
        k = v if (v is None or scale_applied) else v * 0.02
        reason = None
        if k is None or k == 0:
            reason = "fill_value_or_missing"
        elif not (LST_VALID_K[0] <= k <= LST_VALID_K[1]):
            reason = "outside_valid_range"
        else:
            ml = (r.get(c_modland) or "").strip() if c_modland else ""
            er = (r.get(c_err) or "").strip() if c_err else ""
            if ml and ml not in ("0", "00", "0.0"):
                reason = "qc_not_good_quality(MODLAND!=0: cloud/other)"
            elif er and er not in ("0", "00", "1", "01", "0.0", "1.0"):
                reason = "qc_lst_error_above_2K"
        reasons[reason or "kept"] = reasons.get(reason or "kept", 0) + 1
        samples.append({"date": r.get("Date"), "lst_kelvin": None if k is None else round(k, 2), "lst_celsius": None if (k is None or k == 0) else round(k - 273.15, 2),
                        "qc_modland": (r.get(c_modland) if c_modland else None), "qc_lst_error_class": (r.get(c_err) if c_err else None), "used": reason is None, "excluded_because": reason})
    good = [x["lst_celsius"] for x in samples if x["used"]]
    return {"samples": samples, "n_total": len(samples), "n_valid": len(good), "filter_reasons": reasons, "scale_factor_applied_by_source": scale_applied,
            "mean_c": round(sum(good) / len(good), 2) if good else None, "min_c": min(good) if good else None, "max_c": max(good) if good else None}


def lst_point(lat: float, lon: float, start: str, end: str, wait_s: int = 75, poll_s: int = 15) -> dict:
    """MODIS MOD11A2.061 LST_Day_1km point sample through AppEEARS (documented task API): own AppEEARS token from the Earthdata username/password,
    task submitted, polled for a bounded time, results downloaded, QUALITY-FILTERED (QC_Day) and converted K -> degC. LST is a SURFACE (skin)
    temperature and is never mixed with air temperature (T2M). A task that is still queued returns TASK_PENDING and is re-used on the next call."""
    name = "AppEEARS MOD11A2.061 LST_Day_1km"
    err = validate_point(lat, lon)
    if err:
        return envelope(PROVIDER, name, "historical_climate", "invalid_request", "INVALID_POINT", err)
    try:
        s, e = parse_date(start, "start"), parse_date(end, "end")
    except ProviderError as ex:
        return envelope(PROVIDER, name, "historical_climate", "invalid_request", "INVALID_DATE", str(ex))
    if not s or not e or s > e or (e - s).days > 366 or s < LST_FIRST_DATE or e > date.today():
        return envelope(PROVIDER, name, "historical_climate", "invalid_request", "INVALID_PERIOD", f"LST period must be a past range of at most 366 days starting {LST_FIRST_DATE} or later.", source_links=LINKS)
    import hashlib
    key = f"{lat:.4f},{lon:.4f},{s},{e}"
    h8 = hashlib.sha1(key.encode()).hexdigest()[:10]
    dest = get_settings().data_dir / "downloads"; dest.mkdir(parents=True, exist_ok=True)
    csv_path = dest / f"appeears_lst_{h8}.csv"
    t0 = time.monotonic(); cache_state = "hit"
    tid = (_task_cache().get(key) or {}).get("task_id")
    if not csv_path.exists():
        cache_state = "miss"
        tok, err_env = appeears_login()
        if err_env:
            return err_env
        import httpx
        hd = {"Authorization": f"Bearer {tok}"}
        try:
            with httpx.Client(timeout=60, follow_redirects=True) as c:
                if tid:
                    stt = c.get(f"{APPEEARS}/task/{tid}", headers=hd)
                    if stt.status_code != 200 or stt.json().get("status") == "error":
                        tid = None
                if not tid:
                    body = {"task_type": "point", "task_name": f"earthtrend-lst-{h8}", "params": {
                        "dates": [{"startDate": s.strftime("%m-%d-%Y"), "endDate": e.strftime("%m-%d-%Y")}],
                        "layers": [{"product": LST_PRODUCT, "layer": LST_LAYER}, {"product": LST_PRODUCT, "layer": QC_LAYER}],
                        "coordinates": [{"id": "p1", "longitude": float(lon), "latitude": float(lat), "category": "earthtrend"}]}}
                    r = c.post(f"{APPEEARS}/task", json=body, headers=hd)
                    if r.status_code not in (200, 202):
                        return envelope(PROVIDER, name, "historical_climate", "upstream_error", "TASK_SUBMIT_FAILED", f"AppEEARS refused the task (HTTP {r.status_code}).", source_links=LINKS)
                    tid = r.json()["task_id"]
                    cache = _task_cache(); cache[key] = {"task_id": tid, "submitted": time.time()}; _save_task_cache(cache)
                waited, status = 0, None
                while True:
                    status = c.get(f"{APPEEARS}/task/{tid}", headers=hd).json().get("status")
                    if status in ("done", "error") or waited >= wait_s:
                        break
                    time.sleep(poll_s); waited += poll_s
                if status == "error":
                    cache = _task_cache(); cache.pop(key, None); _save_task_cache(cache)
                    return envelope(PROVIDER, name, "historical_climate", "upstream_error", "TASK_ERROR", "The AppEEARS task failed on the server.", source_links=LINKS)
                if status != "done":
                    return envelope(PROVIDER, name, "historical_climate", "upstream_error", "TASK_PENDING",
                                    f"The AppEEARS task is queued or running on NASA servers (status: {status}). It was kept; ask again in a few minutes to fetch the result.",
                                    source_links=LINKS, request={"task_id": tid, "status": status, "waited_s": waited}, live=True)
                files = c.get(f"{APPEEARS}/bundle/{tid}", headers=hd).json()["files"]
                fid = next(f["file_id"] for f in files if f["file_name"].endswith("-Results.csv"))
                csv_path.write_bytes(c.get(f"{APPEEARS}/bundle/{tid}/{fid}", headers=hd).content)
        except Exception as ex:
            return envelope(PROVIDER, name, "historical_climate", "upstream_error", "APPEEARS_FAILED", sanitize(type(ex).__name__), source_links=LINKS)
    parsed = parse_lst_csv(csv_path.read_text(encoding="utf-8", errors="replace"))
    used = [x for x in parsed["samples"] if x["used"]]
    arts = []
    if used:
        arts = [{"type": "line_chart", "title": "MODIS land SURFACE temperature (8-day composites, quality-filtered, °C)", "x": [x["date"] for x in used],
                 "series": [{"name": "LST day (surface skin temperature, not air temperature)", "unit": "°C", "y": [x["lst_celsius"] for x in used], "kind": "line"}]}]
    arts.append({"type": "table", "title": "LST composites (excluded ones are listed with the reason)", "columns": ["date", "lst_celsius", "lst_kelvin", "qc_modland", "qc_lst_error_class", "used", "excluded_because"],
                 "rows": [[x["date"], x["lst_celsius"], x["lst_kelvin"], x["qc_modland"], x["qc_lst_error_class"], x["used"], x["excluded_because"]] for x in parsed["samples"]]})
    return strict(envelope(
        PROVIDER, name, "historical_climate", "ok" if used else "no_data", None if used else "NO_VALID_LST", None if used else "All composites were removed by the quality filter (clouds / poor quality).",
        variables=["LST_Day_1km"], units={"lst": "°C (= K - 273.15). Source unit Kelvin; MOD11A2 scale factor 0.02 " + ("already applied by AppEEARS" if parsed.get("scale_factor_applied_by_source", True) else "applied here")},
        request={"latitude": lat, "longitude": lon, "start": str(s), "end": str(e), "task_id": tid, "product": LST_PRODUCT, "layer": LST_LAYER},
        actual={"period": {"first": used[0]["date"] if used else None, "last": used[-1]["date"] if used else None}, "pixel": "1 km MODIS pixel containing the point"},
        temporal_resolution="8-day composite", live=cache_state == "miss", cache=cache_state, duration_ms=int((time.monotonic() - t0) * 1000), source_links=LINKS + ["https://lpdaac.usgs.gov/products/mod11a2v061/", "https://appeears.earthdatacloud.nasa.gov/"],
        attribution="MODIS MOD11A2 v061 (NASA LP DAAC) via AppEEARS", license="NASA open data",
        quality={"n_total": parsed["n_total"], "n_valid": parsed["n_valid"], "n_filtered": parsed["n_total"] - parsed["n_valid"], "filter_reasons": parsed["filter_reasons"], "mean_c": parsed["mean_c"], "min_c": parsed["min_c"], "max_c": parsed["max_c"],
                 "rule": f"kept only: QC MODLAND = 0 (LST produced, good quality), LST error class <= {LST_MAX_ERROR_CLASS} (<= 2 K), value inside the product valid range {LST_VALID_K[0]}-{LST_VALID_K[1]} K, fill value 0 removed"},
        limitations=["LST is the radiometric SURFACE (skin) temperature of a 1 km pixel (clear-sky only), NOT air temperature; it is never substituted for T2M.",
                     "Cloudy composites are removed by the quality filter, so the series can have gaps and a clear-sky bias.", "8-day composites, daytime overpass (about 10:30 local) only."],
        data={"samples": parsed["samples"]}, artifacts=arts))


def appeears_point_lst(lat, lon, start, end, **kw):          # backwards-compatible name
    return lst_point(lat, lon, start, end, **kw)


# ---- authentication checks (separate from data/analysis success) ---------------------------------------------------------------------
def appeears_login() -> tuple[str | None, dict | None]:
    """AppEEARS has its OWN token: obtained with the Earthdata username/password (never the personal Earthdata token). Returns (token, error_envelope)."""
    u, p = load_credential("EARTHDATA_USERNAME"), load_credential("EARTHDATA_PASSWORD")
    if not u or not p:
        return None, envelope(PROVIDER, "AppEEARS login", "historical_climate", "needs_credentials", "EARTHDATA_LOGIN_MISSING", "Land surface temperature needs an Earthdata Login (EARTHDATA_USERNAME / EARTHDATA_PASSWORD). NASA POWER T2M is AIR temperature and is not substituted automatically.", setup=SETUP_APPEEARS, source_links=LINKS)
    import httpx
    try:
        lg = httpx.post(f"{APPEEARS}/login", auth=(u.get_secret_value(), p.get_secret_value()), data={"grant_type": "client_credentials"}, timeout=40)
    except Exception as ex:
        return None, envelope(PROVIDER, "AppEEARS login", "historical_climate", "upstream_error", "APPEEARS_UNREACHABLE", type(ex).__name__, source_links=LINKS)
    if lg.status_code != 200 or "token" not in lg.json():
        return None, envelope(PROVIDER, "AppEEARS login", "historical_climate", "needs_credentials", "EARTHDATA_LOGIN_REJECTED", f"AppEEARS login rejected (HTTP {lg.status_code}).", setup=SETUP_APPEEARS, source_links=LINKS)
    return lg.json()["token"], None


def check_appeears_auth() -> dict:
    t0 = time.monotonic()
    tok, err = appeears_login()
    if err:
        return err
    return envelope(PROVIDER, "AppEEARS login", "historical_climate", "ok", message="AppEEARS token obtained from the Earthdata username/password (authentication only; no task was run).", live=True,
                    duration_ms=int((time.monotonic() - t0) * 1000), source_links=LINKS)


def check_token_download() -> dict:
    """Authentication + access check on a real DAAC file: a 1 KiB ranged GET of a small MOD11A2 granule with the Earthdata bearer token, verifying the HDF4 signature."""
    tok = load_credential("EARTHDATA_TOKEN")
    if not tok:
        return envelope(PROVIDER, "token download check", "dataset_discovery", "needs_credentials", "EARTHDATA_TOKEN_MISSING", "EARTHDATA_TOKEN is not set.", setup=SETUP_TOKEN, source_links=LINKS)
    import httpx
    t = tok.get_secret_value(); t0 = time.monotonic()
    try:
        d = httpx.get(f"{CMR}/granules.json", params={"short_name": "MOD11A2", "version": "061", "bounding_box": "35.2,32.2,35.3,32.3", "page_size": 1, "sort_key": "-start_date"}, timeout=30).json()
        href = next(l["href"] for l in d["feed"]["entry"][0]["links"] if l.get("rel", "").endswith("/data#") and l["href"].endswith(".hdf"))
        r = httpx.get(href, headers={"Authorization": f"Bearer {t}", "Range": "bytes=0-1023"}, follow_redirects=True, timeout=40)
    except Exception as ex:
        return envelope(PROVIDER, "token download check", "dataset_discovery", "upstream_error", "CHECK_FAILED", sanitize(type(ex).__name__, t), source_links=LINKS)
    if r.status_code in (401, 403):
        return envelope(PROVIDER, "token download check", "dataset_discovery", "needs_credentials", "EARTHDATA_TOKEN_REJECTED", f"The DAAC rejected the token (HTTP {r.status_code}).", setup=SETUP_TOKEN, source_links=LINKS)
    magic = r.content[:4] == bytes([0x0E, 0x03, 0x13, 0x01])
    return envelope(PROVIDER, "token download check", "dataset_discovery", "ok" if r.status_code in (200, 206) and magic else "upstream_error", None if magic else "NOT_HDF",
                    message=f"HTTP {r.status_code}; {len(r.content)} bytes read; HDF4 signature {'valid' if magic else 'MISSING'} (authentication and file access only).", live=True,
                    duration_ms=int((time.monotonic() - t0) * 1000), source_links=LINKS)
