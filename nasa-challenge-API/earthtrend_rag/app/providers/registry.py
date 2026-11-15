"""Provider registry: capabilities, authentication, coverage, licensing, setup and live configuration status (no secrets, no network)."""
from __future__ import annotations

import json
from pathlib import Path

from app.config import get_settings, has_credential

LAST_TEST_FILE = "diagnostics_last.json"

PROVIDERS: dict[str, dict] = {
    "power": {
        "name": "NASA POWER", "capabilities": ["historical_climate"], "auth": [], "tools": ["analyze_trend"],
        "coverage": "global, ~0.5 x 0.625 deg MERRA-2 grid; monthly from 1981; monthly T2M (degC), PRECTOTCORR (mm/day), RH2M (%), WS2M (m/s)",
        "license": "NASA open data; acknowledge NASA POWER", "links": ["https://power.larc.nasa.gov/docs/services/api/"],
        "limits": "T2M is AIR temperature at 2 m (reanalysis), NOT land surface temperature. No documented numeric quota; be polite.",
        "implementation": "implemented", "setup": None},
    "open_meteo": {
        "name": "Open-Meteo", "capabilities": ["weather_forecast", "historical_weather"], "auth": [], "tools": ["get_weather"],
        "coverage": "global; forecast up to 16 days; archive (ERA5-family reanalysis) from 1940 with ~5 day delay",
        "license": "CC BY 4.0, free API NON-COMMERCIAL only (<10,000 calls/day); attribution required", "links": ["https://open-meteo.com/en/docs", "https://open-meteo.com/en/terms"],
        "limits": "Forecast response has no model-run/issue time. Archive is reanalysis, not station observations.", "implementation": "implemented", "setup": None},
    "firms": {
        "name": "NASA FIRMS", "capabilities": ["active_fire_detection", "map_visualization"], "auth": ["FIRMS_MAP_KEY"], "tools": ["get_fire_detections"],
        "coverage": "global (LANDSAT_NRT: US/Canada only); 1-5 day windows per request; NRT recent days, SP standard processing for history",
        "license": "NASA open data", "links": ["https://firms.modaps.eosdis.nasa.gov/api/", "https://firms.modaps.eosdis.nasa.gov/api/map_key/"],
        "limits": "5,000 transactions / 10 min per key. Detections are thermal anomalies, not confirmed incidents or burned area.", "implementation": "implemented",
        "setup": {"register": "https://firms.modaps.eosdis.nasa.gov/api/map_key/", "env": "FIRMS_MAP_KEY", "permissions": "free key emailed after registration"}},
    "gwis": {
        "name": "GWIS (JRC/Copernicus EMS)", "capabilities": ["fire_danger", "map_visualization"], "auth": [], "tools": ["list_fire_danger"],
        "coverage": "global WMS layers (ECMWF 8 km, NASA GEOS-5 based FWI and sub-indices), valid time via TIME",
        "license": "see GWIS data licence page", "links": ["https://gwis.jrc.ec.europa.eu/applications/data-and-services", "https://gwis.jrc.ec.europa.eu/about-gwis"],
        "limits": "Map layers only: a numeric GetFeatureInfo query returned no values when tested. Issue time not published.", "implementation": "implemented", "setup": None},
    "usgs_fire": {
        "name": "USGS Fire Danger Forecast", "capabilities": ["fire_danger", "map_visualization"], "auth": [], "tools": ["list_fire_danger"],
        "coverage": "contiguous United States only; WFPI day 1-7, large-fire/spread probability class maps, greenness",
        "license": "USGS public domain", "links": ["https://firedanger.cr.usgs.gov/apps/data-services-page", "https://www.usgs.gov/fire-danger-forecast"],
        "limits": "Point query returns the map PALETTE class index only (not a documented calibrated value). usgs.gov doc pages returned HTTP 403 to programs.",
        "implementation": "implemented", "setup": None},
    "copernicus": {
        "name": "Copernicus Data Space", "capabilities": ["satellite_discovery", "satellite_processing"], "auth": ["CDSE_CLIENT_ID", "CDSE_CLIENT_SECRET"], "tools": ["search_satellite_scenes"],
        "coverage": "global Sentinel archive (STAC); discovery needs no credentials; NDVI processing needs a free OAuth client",
        "license": "Copernicus Sentinel data: free, full and open", "links": ["https://documentation.dataspace.copernicus.eu/APIs/STAC.html", "https://dataspace.copernicus.eu/analyse/apis"],
        "limits": "Discovery verified live; processing (Sentinel Hub Statistical API NDVI) implemented but needs credentials.", "implementation": "implemented",
        "setup": {"register": "https://dataspace.copernicus.eu/", "env": "CDSE_CLIENT_ID, CDSE_CLIENT_SECRET", "permissions": "OAuth client (Dashboard > User settings)"}},
    "earthdata": {
        "name": "NASA Earthdata (CMR, GIBS, AppEEARS)", "capabilities": ["dataset_discovery", "map_visualization", "historical_climate"], "auth": ["EARTHDATA_TOKEN", "EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"],
        "tools": ["search_earth_datasets"], "coverage": "global catalog (CMR); GIBS imagery daily; LST point sampling via AppEEARS (MOD11A2.061)",
        "license": "NASA open data", "links": ["https://www.earthdata.nasa.gov/data/tools/earthdata-search", "https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html"],
        "limits": "CMR + GIBS need no credentials. Downloads need EARTHDATA_TOKEN; AppEEARS needs username/password. GIBS is visualisation only.", "implementation": "implemented",
        "setup": {"register": "https://urs.earthdata.nasa.gov/users/new", "env": "EARTHDATA_TOKEN (downloads) / EARTHDATA_USERNAME + EARTHDATA_PASSWORD (AppEEARS)", "permissions": "approved DAAC applications; AppEEARS authorised"}},
    "ewds": {
        "name": "Copernicus EWDS - CEMS seasonal fire danger (global)", "capabilities": ["fire_danger_outlook"], "auth": ["EWDS_API_KEY"], "tools": ["forecast_fire_danger"],
        "coverage": "global, 36 km, up to 216 days ahead; monthly start (day 1) ensemble of daily fire danger indices; public catalogue/constraints need no account",
        "license": "Copernicus licence (accept on the dataset's Download tab)", "links": ["https://ewds.climate.copernicus.eu/datasets/cems-fire-seasonal", "https://ewds.climate.copernicus.eu/how-to-api"],
        "limits": "A SEPARATE account from Earthdata and Copernicus Data Space; needs the licence accepted and a personal access token. A configured token is never reported as working until the auth check passes. Danger index, not a probability of fire.",
        "implementation": "implemented", "setup": {"register": "https://ewds.climate.copernicus.eu/", "env": "EWDS_API_KEY", "permissions": "dataset licence accepted + personal access token (how-to-api page)"}},
    "nifc": {
        "name": "NIFC Predictive Services - monthly significant wildland fire potential (US)", "capabilities": ["fire_danger_outlook"], "auth": [], "tools": ["forecast_fire_danger"],
        "coverage": "United States by Predictive Service Area / GACC; issue month + 3 months; categorical Above/Normal/Below normal (NOT a probability)",
        "license": "US government public data", "links": ["https://www.nifc.gov/nifc/predictive-services/outlooks", "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services"],
        "limits": "Issued around the first of each month, only while Geographic Areas are in fire season; outlook skill is not verified by this application.", "implementation": "implemented", "setup": None},
    "gee": {
        "name": "Google Earth Engine (optional)", "capabilities": ["dataset_discovery", "satellite_processing"], "auth": ["EE_PROJECT"], "tools": ["search_earth_datasets"],
        "coverage": "catalog discovery public (STAC); computation only with an authorised Earth Engine project", "license": "per-dataset licences in the catalog",
        "links": ["https://developers.google.com/earth-engine/datasets", "https://developers.google.com/earth-engine/guides/access"],
        "limits": "Registration/eligibility/quotas/billing are decided by Google; this prototype never creates projects or enables billing.", "implementation": "implemented",
        "setup": {"register": "https://developers.google.com/earth-engine/guides/access", "env": "EE_PROJECT", "permissions": "registered Earth Engine project with API enabled"}},
}


def load_last_tests() -> dict:
    try:
        return json.loads((get_settings().data_dir / LAST_TEST_FILE).read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_last_test(provider_id: str, result: dict) -> None:
    d = load_last_tests()
    d[provider_id] = result
    (get_settings().data_dir / LAST_TEST_FILE).write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")


def status() -> list[dict]:
    last = load_last_tests()
    out = []
    for pid, p in PROVIDERS.items():
        creds = {n: has_credential(n) for n in p["auth"]}
        required_ok = True if not p["auth"] else any(creds.values())
        if pid == "earthdata":
            configured = "partial: discovery+GIBS ready; downloads/AppEEARS " + ("configured" if creds["EARTHDATA_TOKEN"] or (creds["EARTHDATA_USERNAME"] and creds["EARTHDATA_PASSWORD"]) else "need credentials")
        elif pid == "copernicus":
            configured = "discovery ready; processing " + ("configured" if all(creds.values()) else "needs credentials")
        elif pid == "ewds":
            configured = "public availability ready; token " + ("present (verify with the auth check)" if creds["EWDS_API_KEY"] else "missing (needs credentials)")
        elif pid == "gee":
            from app.providers.gee import availability
            a = availability()
            configured = "catalog discovery ready; computation " + ("configured" if a["package_installed"] and a["project_configured"] else "not configured (optional)")
        else:
            configured = "ready" if required_ok else "needs credentials"
        extra = {"earthdata": ["earthdata_token", "appeears_auth"], "copernicus": ["cdse_oauth"], "ewds": ["ewds_auth", "ewds_data"]}.get(pid, [])
        out.append({"id": pid, "extra_tests": {t: last.get(t) for t in extra}, **{k: p[k] for k in ("name", "capabilities", "auth", "tools", "coverage", "license", "links", "limits", "implementation", "setup")},
                    "credentials_present": creds, "configuration": configured, "last_test": last.get(pid)})
    return out
