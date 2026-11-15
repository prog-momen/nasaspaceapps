"""Google Earth Engine: OPTIONAL backend. Catalog discovery uses the public Earth Engine STAC catalog (no authentication);
computation needs the `earthengine-api` package AND an authorised Cloud project (registration/eligibility/quota are set by Google).

Nothing here creates cloud projects, enables billing or assumes free eligibility. The rest of the prototype works without it.
Verified 2026-11-14: https://earthengine-stac.storage.googleapis.com/catalog/catalog.json is public (133 child catalogs).
"""
from __future__ import annotations

import time

from app.config import load_credential
from app.providers.base import ProviderError, envelope, fail, http_json, strict

PROVIDER = "Google Earth Engine"
ROOT = "https://earthengine-stac.storage.googleapis.com/catalog/catalog.json"
LINKS = ["https://earthengine.google.com/", "https://developers.google.com/earth-engine/datasets", "https://developers.google.com/earth-engine/guides/python_install",
         "https://developers.google.com/earth-engine/guides/access"]
SETUP = {"env": "EE_PROJECT (+ EE_SERVICE_ACCOUNT_JSON path, optional)", "register": "https://developers.google.com/earth-engine/guides/access",
         "steps": "Register for Earth Engine access with a Google Cloud project that is eligible (non-commercial/commercial terms differ; check quotas/billing on that page). "
                  "pip install earthengine-api; authenticate with `earthengine authenticate` or a service-account JSON; set EE_PROJECT in the backend .env.",
         "permissions": "Earth Engine API enabled on the project; account registered for Earth Engine"}
GROUPS = ["MODIS", "COPERNICUS", "NASA", "LANDSAT", "ECMWF", "NOAA", "UCSB-CHG", "JAXA", "FIRMS", "TOMS", "CIESIN", "USGS"]


def catalog_search(keyword: str, limit: int = 8) -> dict:
    if not keyword or len(keyword.strip()) < 2:
        return envelope(PROVIDER, "Earth Engine catalog (STAC)", "dataset_discovery", "invalid_request", "EMPTY_KEYWORD", "keyword is required", source_links=LINKS)
    k = keyword.strip().lower()
    t0 = time.monotonic()
    try:
        root, meta = http_json("gee", "GET", ROOT, ttl=86400)
        kids = {l["title"]: l["href"] for l in root["links"] if l.get("rel") == "child"}
        hits = []
        for g in [g for g in GROUPS if g in kids]:
            cat, _ = http_json("gee", "GET", kids[g], ttl=86400)
            for l in cat["links"]:
                if l.get("rel") in ("child", "item") and k in (l.get("title") or "").lower():
                    hits.append(l["href"])
        out = []
        for h in hits[:limit]:
            c, _ = http_json("gee", "GET", h, ttl=86400)
            tint = (c.get("extent", {}).get("temporal", {}).get("interval") or [[None, None]])[0]
            out.append({"id": c.get("id"), "title": c.get("title"), "type": c.get("gee:type"), "start": tint[0], "end": tint[1], "license": c.get("license"),
                        "provider": (c.get("providers") or [{}])[0].get("name"), "deprecated": "deprecated" in (c.get("title") or "").lower() or c.get("gee:status") == "deprecated",
                        "doi": c.get("sci:doi"), "catalog_page": f"https://developers.google.com/earth-engine/datasets/catalog/{(c.get('id') or '').replace('/', '_')}"})
    except ProviderError as e:
        return fail(PROVIDER, "Earth Engine catalog (STAC)", "dataset_discovery", e, source_links=LINKS)
    return strict(envelope(PROVIDER, "Earth Engine catalog (STAC)", "dataset_discovery", "ok" if out else "no_data", None if out else "NO_MATCH",
                           None if out else f"No catalog entry matched '{keyword}' in the searched groups ({', '.join(GROUPS)}).", request={"keyword": keyword},
                           actual={"n_datasets": len(out)}, live=meta["live"], cache=meta["cache"], retrieved_at=meta["retrieved_at"], duration_ms=int((time.monotonic() - t0) * 1000),
                           source_links=LINKS, attribution="Google Earth Engine data catalog", limitations=["Catalog discovery only; running analyses needs authorised access."],
                           data={"datasets": out}, artifacts=[{"type": "table", "title": "Earth Engine datasets", "columns": ["id", "title", "type", "start", "end", "license", "deprecated"],
                                                                "rows": [[d["id"], d["title"], d["type"], d["start"], d["end"], d["license"], d["deprecated"]] for d in out]}]))


def availability() -> dict:
    """Is a computation backend configured? (no network)"""
    try:
        import ee  # noqa: F401
        have_pkg = True
    except ImportError:
        have_pkg = False
    proj = load_credential("EE_PROJECT")
    return {"package_installed": have_pkg, "project_configured": bool(proj)}


def region_mean(dataset_id: str, band: str, bbox: list[float], start: str, end: str, scale_m: int = 1000) -> dict:
    """Mean of one band of an image collection over a bbox and date range (small reduceRegion). Needs authorised Earth Engine access."""
    a = availability()
    if not a["package_installed"] or not a["project_configured"]:
        why = "package `earthengine-api` is not installed" if not a["package_installed"] else "EE_PROJECT is not set"
        return envelope(PROVIDER, dataset_id, "satellite_processing", "needs_credentials", "EARTH_ENGINE_NOT_CONFIGURED",
                        f"Earth Engine computation is optional and not configured ({why}). Everything else works without it.", setup=SETUP, source_links=LINKS,
                        limitations=["Adapter implemented; not live-tested because no authorised Earth Engine project is available. No billing/project was created."])
    try:
        import ee
        ee.Initialize(project=load_credential("EE_PROJECT").get_secret_value())
        geom = ee.Geometry.Rectangle([float(x) for x in bbox])
        col = ee.ImageCollection(dataset_id).filterDate(start, end).filterBounds(geom).select(band)
        n = col.size().getInfo()
        if not n:
            return envelope(PROVIDER, dataset_id, "satellite_processing", "no_data", "NO_IMAGES", "No images in this region/date range.", source_links=LINKS)
        val = col.mean().reduceRegion(ee.Reducer.mean(), geom, scale_m, maxPixels=10 ** 8).getInfo()
    except Exception as ex:
        return envelope(PROVIDER, dataset_id, "satellite_processing", "upstream_error", "EARTH_ENGINE_ERROR", type(ex).__name__ + ": " + str(ex)[:160], source_links=LINKS)
    return strict(envelope(PROVIDER, dataset_id, "satellite_processing", "ok", variables=[band], request={"bbox": bbox, "start": start, "end": end, "scale_m": scale_m},
                           actual={"n_images": n}, live=True, source_links=LINKS, limitations=["Unscaled band values: apply the dataset's scale/offset from the catalog before interpreting."],
                           data={"mean": val}))
