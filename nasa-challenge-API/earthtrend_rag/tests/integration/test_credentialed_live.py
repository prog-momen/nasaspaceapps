"""LIVE tests that use the configured Earthdata / AppEEARS / CDSE credentials (never printed). Each test is skipped when its credential is absent.
Authentication success and data/analysis success are asserted SEPARATELY. Run: pytest -m integration tests/integration/test_credentialed_live.py"""
import json
import struct

import pytest

from app.config import has_credential
from app.providers import copernicus, earthdata

pytestmark = pytest.mark.integration
HDF4_MAGIC = bytes([0x0E, 0x03, 0x13, 0x01])


@pytest.mark.skipif(not has_credential("EARTHDATA_TOKEN"), reason="EARTHDATA_TOKEN not configured")
def test_earthdata_token_downloads_and_opens_a_real_granule(tmp_path):
    import httpx
    d = httpx.get(f"{earthdata.CMR}/granules.json", params={"short_name": "MOD11A2", "version": "061", "bounding_box": "35.2,32.2,35.3,32.3", "page_size": 1, "sort_key": "-start_date"}, timeout=30).json()
    href = next(l["href"] for l in d["feed"]["entry"][0]["links"] if l.get("rel", "").endswith("/data#") and l["href"].endswith(".hdf"))
    r = earthdata.download_granule(href, tmp_path)                      # a CMR hit alone proves nothing: this really downloads with the bearer token
    assert r["status"] == "ok" and r["actual"]["bytes"] > 1_000_000
    b = (tmp_path / r["actual"]["file"].rsplit("\\", 1)[-1].rsplit("/", 1)[-1]).read_bytes()
    assert b[:4] == HDF4_MAGIC
    off, n_dd = 4, 0                                                     # walk the HDF4 data-descriptor blocks: the file structure is really readable
    while off:
        n, nxt = struct.unpack(">HI", b[off:off + 6]); off += 6 + 12 * n; n_dd += n
        off = nxt
    assert n_dd > 1000 and b.find(b"MODIS_Grid_8Day_1km_LST") > 0 and b.find(b"LST_Day_1km") > 0
    assert earthdata.check_token_download()["status"] == "ok"


@pytest.mark.skipif(not (has_credential("EARTHDATA_USERNAME") and has_credential("EARTHDATA_PASSWORD")), reason="Earthdata login not configured")
def test_appeears_has_its_own_token_authentication_only():
    tok, err = earthdata.appeears_login()
    assert err is None and tok and tok != (earthdata.load_credential("EARTHDATA_TOKEN").get_secret_value() if has_credential("EARTHDATA_TOKEN") else None)
    assert earthdata.check_appeears_auth()["status"] == "ok"


@pytest.mark.skipif(not (has_credential("CDSE_CLIENT_ID") and has_credential("CDSE_CLIENT_SECRET")), reason="CDSE OAuth client not configured")
def test_cdse_oauth_then_small_area_ndvi_with_masking():
    assert copernicus.check_oauth()["status"] == "ok"                    # authentication only
    r = copernicus.ndvi_statistics([35.20, 32.18, 35.30, 32.28], "2026-09-01", "2026-10-31", 30, 10)
    assert r["status"] == "ok"                                           # analysis
    iv = r["data"]["intervals"]
    assert len(iv) >= 5 and all(-1.0 <= x["mean"] <= 1.0 for x in iv if x["mean"] is not None)
    assert all(x["valid_pixels"] + (x["no_data_pixels"] or 0) <= 250000 + 1 for x in iv)
    assert any((x["no_data_pixels"] or 0) > 0 for x in iv)                # clouds / invalid values really were masked
