"""LIVE provider checks (real network, no credentials needed). Run: pytest -m integration tests/integration/test_providers_live.py

Credential-gated providers (FIRMS, Earthdata downloads/AppEEARS, CDSE processing, Earth Engine computation) are NOT live-tested here:
they are checked to fail closed with setup guidance (see tests/test_providers_offline.py)."""
import httpx
import pytest
from fastapi.testclient import TestClient

from app.providers import copernicus, earthdata, fire_danger, firms, gee, open_meteo

pytestmark = pytest.mark.integration


def test_live_open_meteo_forecast_and_geocoding():
    g = open_meteo.geocode("القاهرة", "ar")
    assert g["status"] == "ok" and abs(g["data"]["places"][0]["latitude"] - 30.04) < 0.5
    r = open_meteo.forecast(30.04, 31.24, 3)
    assert r["status"] == "ok" and r["live"] in (True, False) and r["actual"]["timezone"] == "Africa/Cairo" and len(r["data"]["daily"]["time"]) == 3
    assert r["units"]["temperature_2m_max"] == "°C" and r["actual"]["issue_time"] is None


def test_live_open_meteo_historical_reanalysis():
    r = open_meteo.historical(30.04, 31.24, "2024-06-01", "2024-06-05")
    assert r["status"] == "ok" and r["actual"]["period"]["first"] == "2024-06-01" and "reanalysis" in r["actual"]["source_type"]
    assert all(v is not None for v in r["data"]["daily"]["temperature_2m_max"])


def test_live_cmr_collections_and_granules():
    c = earthdata.search_collections("MOD11C3", limit=3)
    assert c["status"] == "ok" and any(x["short_name"] == "MOD11C3" and x["version"] == "061" for x in c["data"]["collections"])
    g = earthdata.search_granules("MOD11C3", "061", [34.9, 31.5, 35.5, 32.1], "2024-01-01", "2024-03-31", 3)
    assert g["status"] == "ok" and g["data"]["granules"][0]["requires_earthdata_login"] is True


def test_live_gibs_tile_exists():
    o = earthdata.gibs_overlay("MODIS_Terra_CorrectedReflectance_TrueColor", "2024-06-15")
    url = o["data"]["tile_url"].format(z=5, y=9, x=17)
    r = httpx.get(url, timeout=30)
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/")


def test_live_cdse_scenes_and_preview_proxy():
    r = copernicus.search_scenes([31.0, 29.9, 31.4, 30.2], "2024-06-01", "2024-06-30", "sentinel-2-l2a", 30, 3)
    assert r["status"] == "ok" and r["data"]["scenes"] and r["data"]["scenes"][0]["cloud_cover_percent"] <= 30
    from fastapi import FastAPI
    from app.api.chat_api import router
    mini = FastAPI()                                  # only the chat router: no Qdrant, so it works while the prototype server is running
    mini.include_router(router)
    with TestClient(mini) as c:
        p = c.get(r["data"]["scenes"][0]["preview"])
        assert p.status_code == 200 and p.headers["content-type"] in ("image/jpeg", "image/png") and len(p.content) > 1000
        assert c.get("/api/preview", params={"u": "https://example.com/x.jpg"}).status_code == 400          # host allow-list


def test_live_gwis_wms_products():
    r = fire_danger.gwis_products("fwi")
    assert r["status"] == "ok" and any(p["layer"] == "ecmwf.fwi" for p in r["data"]["products"])
    p = next(p for p in r["data"]["products"] if p["layer"] == "ecmwf.fwi")
    assert p["valid_time_range"].startswith("2018") and p["default_valid_time"]
    img = httpx.get("https://maps.effis.emergency.copernicus.eu/gwis", params={"service": "WMS", "version": "1.3.0", "request": "GetMap", "layers": "ecmwf.fwi", "styles": "", "crs": "EPSG:4326",
                                                                                 "bbox": "25,30,40,40", "width": 200, "height": 120, "format": "image/png", "transparent": "true"}, timeout=40)
    assert img.status_code == 200 and img.headers["content-type"].startswith("image/png")


def test_live_usgs_wms_point_inside_and_outside_conus():
    inside = fire_danger.usgs_point(43.6, -116.2)
    assert inside["status"] in ("ok", "no_data") and (inside["status"] == "no_data" or isinstance(inside["data"]["palette_index"], int))
    assert fire_danger.usgs_point(30.04, 31.24)["status"] == "unsupported_region"


def test_live_gee_public_catalog_discovery():
    r = gee.catalog_search("MOD11", limit=3)
    assert r["status"] == "ok" and any("MOD11" in (d["id"] or "") for d in r["data"]["datasets"])
    assert gee.region_mean("MODIS/061/MOD11A1", "LST_Day_1km", [34, 31, 35, 32], "2024-01-01", "2024-01-10")["status"] == "needs_credentials"


def test_firms_endpoint_rejects_a_placeholder_key_proving_the_key_requirement():
    r = httpx.get("https://firms.modaps.eosdis.nasa.gov/api/area/csv/PLACEHOLDER_NOT_A_KEY/VIIRS_SNPP_NRT/34,31,36,33/1", timeout=30)
    assert r.status_code == 400 and "Invalid MAP_KEY" in r.text
    from app.config import has_credential
    if not has_credential("FIRMS_MAP_KEY"):
        assert firms.detections([34, 31, 36, 33], None, 1)["status"] == "needs_credentials"


@pytest.mark.skipif(not __import__("app.config", fromlist=["has_credential"]).has_credential("FIRMS_MAP_KEY"), reason="FIRMS_MAP_KEY not configured")
def test_live_firms_with_the_configured_key_parses_and_never_leaks_the_key(caplog):
    """LIVE, uses the configured key (never printed). Mato Grosso is an active-fire region in Nov; sensor chosen from the availability endpoint."""
    import json, logging
    from app.config import load_credential
    secret = load_credential("FIRMS_MAP_KEY").get_secret_value()
    caplog.set_level(logging.DEBUG)
    import random
    r = firms.detections([-58, -14, -52, -9 + random.random() / 1000], None, 3)      # jittered edge: always a real (uncached) request
    assert r["status"] == "ok" and r["live"] in (True, False) and r["actual"]["n_detections"] > 0
    d = r["data"]["detections"][0]
    assert isinstance(d["latitude"], float) and isinstance(d["longitude"], float) and isinstance(d["frp_mw"], float) and len(d["acq_time"]) == 4
    assert d["acq_datetime_utc"].endswith("Z") and d["satellite"] and d["instrument"] and d["confidence"] in ("l", "n", "h") and d["daynight"] in ("D", "N")
    assert r["units"]["frp"] == "MW" and r["actual"]["time_standard"] == "UTC" and any(a["type"] == "map_points" and a["points"] for a in r["artifacts"])
    assert secret not in json.dumps(r, default=str) and secret not in caplog.text
    # valid request, region with (almost certainly) no fire: zero detections, still a successful authenticated call
    z = firms.detections([-5.0, 20.0, -4.5, 20.5], None, 1)                      # central Sahara
    assert z["status"] in ("ok", "no_data") and z["reason_code"] in (None, "ZERO_DETECTIONS") and z["reason_code"] != "FIRMS_MAP_KEY_INVALID"
    # an explicitly requested sensor with no data for the dates is a COVERAGE GAP, not zero fires
    gap = firms.detections([-58, -14, -52, -9], "2026-11-12", 1, "VIIRS_SNPP_NRT")
    assert gap["reason_code"] in ("SENSOR_DATA_NOT_AVAILABLE", None, "ZERO_DETECTIONS")
