"""LIVE wildfire-outlook checks. NIFC and the EWDS public catalogue need no credentials; EWDS DATA access needs EWDS_API_KEY and is reported honestly when it is missing
(this file never claims data access from the presence of a token: authentication, licence and data download are separate steps)."""
from datetime import date, timedelta

import pytest

from app.providers import fire_outlook as fo

pytestmark = pytest.mark.integration
TODAY = date.today()


def test_live_nifc_point_outlook_is_current_or_honestly_stale():
    a = (TODAY.replace(day=1) + timedelta(days=32)).replace(day=1)
    b = (a + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    r = fo.nifc_outlook(40.5865, -122.3917, None, None, a, b, TODAY)
    assert r["status"] in ("ok", "no_data"), r["message"]                         # no_data = the service's latest issue is stale or the month is not covered: never shown as current
    if r["status"] == "ok":
        assert r["data"]["months"][0]["headline"] in ("Above", "Normal", "Below") and r["actual"]["freshness"]["current"]
        assert any(x["type"] == "map_polygons" and x["layer_role"] == "forecast" for x in r["artifacts"])


def test_live_nifc_region_name_and_outside_us():
    names = fo.nifc_region_names()
    assert any("Northern California" in g for g in names["gacc"]) and len(names["psa"]) > 50
    assert fo.match_region_text("northern california", names)["kind"] == "gacc"
    a = (TODAY.replace(day=1) + timedelta(days=32)).replace(day=1)
    r = fo.nifc_outlook(32.2211, 35.2544, None, None, a, a + timedelta(days=27), TODAY)
    assert r["status"] == "unsupported_region"


def test_live_ewds_public_catalogue_and_schema_validate_the_request():
    av = fo.ewds_availability(False)
    assert av["latest_start"] and av["horizon_days"] == 216
    schema = fo.ewds_process_schema(False)
    start = date.fromisoformat(av["latest_start"])
    days = [start + timedelta(days=40 + i) for i in range(3)]
    req = fo.build_ewds_request("fire_weather_index", [start.year], start.month, days, [33, 35, 32, 36], start, schema)
    assert req["day"] == ["01"] and len(req["leadtime_hour"]) == 3


def test_live_ewds_without_a_token_is_needs_credentials(monkeypatch):
    monkeypatch.setattr(fo, "ewds_key", lambda: None)
    r = fo.forecast_fire_danger(32.2211, 35.2544, None, None, None, None, "next_calendar_month", "auto", "Nablus", with_observations=False)
    assert r["status"] == "needs_credentials" and r["setup"]["token"].endswith("how-to-api")


@pytest.mark.skipif(not fo.ewds_key(), reason="EWDS_API_KEY not configured: the EWDS data download is blocked until the user supplies a token (never faked)")
def test_live_ewds_auth_is_checked_separately_from_data():
    r = fo.ewds_auth_check()
    assert r["status"] in ("ok", "needs_credentials")
