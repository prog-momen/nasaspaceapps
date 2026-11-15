"""Chat tools: validated arguments -> provider calls -> (result, artifacts, summary, resolved location/period).

Tool declarations double as the Gemini function declarations. Gemini never calls providers directly: the backend validates and runs them.
"""
from __future__ import annotations

import re
import time
from datetime import date, timedelta

from app.analysis.catalog import VARIABLES
from app.chat.location import bbox_around, bbox_center, geocode_name, find_known_place
from app.forecast.service import forecast_monthly as _forecast_monthly
from app.providers import copernicus, earthdata, fire_danger, fire_outlook, firms, gee, open_meteo
from app.providers.base import envelope, strict, validate_bbox
from app.tools.trend_tool import run_trend_analysis

_LOC = {
    "place": {"type": "string", "description": "Place name (city/region). Omit when latitude/longitude or bbox are given or already known from context."},
    "latitude": {"type": "number"}, "longitude": {"type": "number"},
    "bbox": {"type": "array", "items": {"type": "number"}, "description": "[west, south, east, north] in degrees"},
}
DECLARATIONS = [
    {"name": "analyze_trend", "description": "Mann-Kendall + Sen's slope trend of a NASA POWER monthly variable over several years at a place (historical description only; not a forecast). "
                                             "air_temperature is T2M AIR temperature, not land surface temperature.",
     "parameters": {"type": "object", "properties": {"variable": {"type": "string", "enum": list(VARIABLES)}, **_LOC, "start_year": {"type": "integer"}, "end_year": {"type": "integer"}},
                    "required": ["variable", "start_year", "end_year"]}},
    {"name": "get_weather", "description": "Operational weather FORECAST (mode=forecast, up to 16 days) or historical reanalysis weather (mode=historical, up to 366 days) from Open-Meteo: "
                                            "temperature, precipitation, humidity, wind.",
     "parameters": {"type": "object", "properties": {"mode": {"type": "string", "enum": ["forecast", "historical"]}, **_LOC, "days": {"type": "integer", "description": "forecast days 1-16"},
                                                      "start_date": {"type": "string", "description": "YYYY-MM-DD (historical)"}, "end_date": {"type": "string"}}, "required": ["mode"]}},
    {"name": "get_fire_detections", "description": "NASA FIRMS active-fire DETECTIONS (satellite thermal anomalies, not confirmed incidents) in an area, 1-5 days.",
     "parameters": {"type": "object", "properties": {**_LOC, "start_date": {"type": "string", "description": "YYYY-MM-DD; omit for the most recent days"}, "day_range": {"type": "integer", "description": "1-5"}}}},
    {"name": "list_fire_danger", "description": "Available fire DANGER products (GWIS global WMS layers; USGS WFPI for the contiguous US). Danger indices are not probabilities of fire.",
     "parameters": {"type": "object", "properties": {**_LOC, "keyword": {"type": "string", "description": "e.g. fwi"}}}},
    {"name": "search_satellite_scenes", "description": "Discover Sentinel scenes (Copernicus Data Space STAC) by area, dates and max cloud cover. Discovery only, no pixel processing.",
     "parameters": {"type": "object", "properties": {**_LOC, "start_date": {"type": "string"}, "end_date": {"type": "string"}, "collection": {"type": "string", "description": "e.g. sentinel-2-l2a"},
                                                      "max_cloud": {"type": "number"}}}},
    {"name": "get_lst", "description": "MODIS land SURFACE (skin) temperature MOD11A2.061 LST_Day_1km via NASA AppEEARS for ONE point and a period of at most a year (8-day composites, quality-filtered, "
                                       "converted K -> degC). This is NOT air temperature (T2M). Tasks run on NASA servers and can take minutes.",
     "parameters": {"type": "object", "properties": {**_LOC, "start_date": {"type": "string", "description": "YYYY-MM-DD"}, "end_date": {"type": "string"}}}},
    {"name": "forecast_fire_danger", "description": "One-month WILDFIRE DANGER OUTLOOK for a place or region from OFFICIAL sources only: NIFC significant wildland fire potential (US, categorical by predictive service area) and "
                                                    "the Copernicus CEMS seasonal fire danger ensemble (global, needs EWDS access). window = next_calendar_month | next_30_days. It is a danger outlook, NOT a probability of fire, NOT a daily "
                                                    "forecast and NOT observed fires (observed FIRMS detections are shown separately).",
     "parameters": {"type": "object", "properties": {**_LOC, "window": {"type": "string", "enum": ["next_calendar_month", "next_30_days"]}, "source": {"type": "string", "enum": ["auto", "nifc", "ewds"]}}}},
    {"name": "forecast_monthly", "description": "STATISTICAL forecast of MONTHLY mean air_temperature / precipitation / relative_humidity / wind_speed for 1-24 months ahead at a place (NASA POWER history, "
                                                 "validated by chronological rolling-origin backtests against named baselines; returns forecast, prediction intervals, backtest errors by lead, validation status). "
                                                 "Not a weather forecast and not a climate projection.",
     "parameters": {"type": "object", "properties": {"variable": {"type": "string", "enum": ["air_temperature", "precipitation", "relative_humidity", "wind_speed"]}, **_LOC,
                                                      "months": {"type": "integer", "description": "1-24"}, "train_start_year": {"type": "integer", "description": "optional first year of training history (>= 1981)"}},
                    "required": ["months"]}},
    {"name": "get_ndvi", "description": "Sentinel-2 L2A NDVI mean per 10-day interval for a SMALL area (<= 1 degree) from Copernicus Data Space Statistical API; clouds, shadows, snow and invalid reflectance are masked. "
                                        "Needs CDSE credentials. Not LST, not air temperature.",
     "parameters": {"type": "object", "properties": {**_LOC, "start_date": {"type": "string"}, "end_date": {"type": "string"}, "max_cloud": {"type": "number"}}}},
    {"name": "search_earth_datasets", "description": "Discover Earth science datasets in NASA CMR (and optionally the Earth Engine catalog) by keyword.",
     "parameters": {"type": "object", "properties": {"keyword": {"type": "string"}, "catalog": {"type": "string", "enum": ["cmr", "gee"]}}, "required": ["keyword"]}},
]
TOOL_NAMES = [d["name"] for d in DECLARATIONS]


class Outcome(dict):
    """result, artifacts, summary, location, period, used_args, tool, status, duration_ms"""


def _resolve_location(args: dict, defaults: dict) -> tuple[dict | None, list[str]]:
    notes = []
    if args.get("latitude") is not None and args.get("longitude") is not None:
        la, lo = float(args["latitude"]), float(args["longitude"])
        if not args.get("place"):
            return {"name": f"point ({la:.4f}, {lo:.4f})", "latitude": la, "longitude": lo, "source": "arguments"}, notes
        k = find_known_place(str(args["place"]))                     # a place we know exactly beats coordinates recalled by the language model
        if k:
            return k, notes
        if -90 <= la <= 90 and -180 <= lo <= 180:
            notes.append(f"'{args['place']}' located at ({la:.2f}, {lo:.2f}) from the language model's geographic knowledge (a representative point, not a geocoder result or an area average).")
            return {"name": f"{args['place']} (representative point)", "latitude": la, "longitude": lo, "source": "language model geographic knowledge"}, notes
    if args.get("bbox"):
        la, lo = bbox_center([float(x) for x in args["bbox"]])
        return {"name": "bounding box", "latitude": la, "longitude": lo, "bbox": [float(x) for x in args["bbox"]], "source": "bbox"}, notes
    if args.get("place"):
        k = find_known_place(str(args["place"]))
        if k:
            return k, notes
        g = geocode_name(str(args["place"]), defaults.get("lang") or "en")
        if g and g.get("ambiguous"):
            notes.append("AMBIGUOUS:" + " | ".join(g["ambiguous"]))
            return None, notes
        if g:
            notes.append(f"'{args['place']}' resolved by Open-Meteo geocoding to {g['name']} ({g['latitude']:.3f}, {g['longitude']:.3f}); first match used.")
            return g, notes
        notes.append(f"Could not resolve the place '{args['place']}'.")
        return None, notes
    loc = defaults.get("location")
    if loc:
        return loc, notes
    return None, notes


def _bbox(loc: dict, args: dict, defaults: dict, half: float) -> list[float]:
    if args.get("bbox"):
        return [float(x) for x in args["bbox"]]
    if loc.get("bbox"):
        return loc["bbox"]
    return bbox_around(loc["latitude"], loc["longitude"], half)


def _need_location(tool: str, notes: list[str]) -> Outcome:
    amb = next((n[len("AMBIGUOUS:"):].split(" | ") for n in notes if n.startswith("AMBIGUOUS:")), None)
    notes = [n for n in notes if not n.startswith("AMBIGUOUS:")]
    r = envelope("EarthTrend", tool, "map_visualization", "invalid_request", "LOCATION_AMBIGUOUS" if amb else "LOCATION_REQUIRED",
                 "The place name matches several places." if amb else "No location: say a place name, give coordinates, or pick a point/box on the map." + (" " + " ".join(notes) if notes else ""))
    return Outcome(result=r, artifacts=[], summary={"needs": "location", "ambiguous": amb} if amb else {"needs": "location"}, location=None, period=None, used_args={}, tool=tool,
                   status="invalid_request", duration_ms=0, notes=notes)


def _line_artifact_from_trend(res: dict) -> list[dict]:
    ch = res.get("chart")
    if not ch:
        return []
    x, y = ch["x_labels"], ch["y"]
    line = ch.get("sen_line")
    art = {"type": "line_chart", "title": ch["title"], "x": x, "series": [{"name": res["variable"]["name"], "unit": res["units"], "y": y, "kind": "line"}]}
    if line:
        art["trend_line"] = {"x": [x[0], x[-1]], "y": line["y"], "label": "Sen's slope line (historical estimate, not a forecast)"}
    t = res["test"]
    table = {"type": "table", "title": "Trend result", "columns": ["field", "value"], "rows": [
        ["variable", res["variable"]["name"]], ["region", res["region"]["name"]], ["period_actual", f"{res['period_actual']['first']} .. {res['period_actual']['last']}"],
        ["readings used", f"{t['n_used']} ({t['n_unit']})"], ["unit", res["units"]], ["aggregation", res["aggregation"]["chosen"]], ["test", t["test_name"]],
        ["kendall_tau", t["kendall_tau"]], ["p_value", t["p_value"]], ["alpha", t["alpha"]], ["significant", t["significant"]],
        ["sen_slope", f"{t['sen_slope']['value']} {t['sen_slope']['unit']}"], ["sen_slope_ci", f"[{t['sen_slope']['ci_low']}, {t['sen_slope']['ci_high']}]"],
        ["valid_months", res["data_quality"]["valid_months"]], ["missing_months", res["data_quality"]["missing_months"]], ["source", f"{res['source'].get('provider')} {res['source'].get('dataset')}"],
        ["retrieved_at", res["source"].get("retrieved_at")], ["cache_hit", res["source"].get("cache_hit")]]}
    return [art, table]


def execute(name: str, args: dict, defaults: dict | None = None) -> Outcome:
    defaults = defaults or {}
    t0 = time.monotonic()
    args = {k: v for k, v in (args or {}).items() if v not in (None, "", [])}
    out = _execute(name, args, defaults)
    out["duration_ms"] = int((time.monotonic() - t0) * 1000)
    out["tool"] = name
    out["status"] = out["result"].get("status")
    return strict(out) if False else out


def _execute(name: str, args: dict, defaults: dict) -> Outcome:
    today = date.today()
    per = defaults.get("period") or {}
    if name == "analyze_trend":
        loc, notes = _resolve_location(args, defaults)
        if not loc:
            return _need_location(name, notes)
        sy = args.get("start_year") or per.get("start_year")
        ey = args.get("end_year") or per.get("end_year")
        if not sy or not ey:
            r = envelope("NASA POWER", "monthly trend", "historical_climate", "invalid_request", "PERIOD_REQUIRED", "A trend needs a start and end year (e.g. 2005-2025).")
            return Outcome(result=r, artifacts=[], summary={"needs": "period"}, location=loc, period=None, used_args={}, tool=name)
        ta = {"variable": args.get("variable") or defaults.get("variable") or "air_temperature", "region": loc["name"], "latitude": loc["latitude"], "longitude": loc["longitude"], "start_year": int(sy), "end_year": int(ey)}
        res = run_trend_analysis(ta)
        res["__location_note"] = notes
        arts = _line_artifact_from_trend(res) if res.get("status") == "ok" else []
        return Outcome(result=res, artifacts=arts, summary=_trend_summary(res), location=loc, period={"start_year": ta["start_year"], "end_year": ta["end_year"]}, used_args=ta, notes=notes)
    if name == "get_weather":
        loc, notes = _resolve_location(args, defaults)
        if not loc:
            return _need_location(name, notes)
        mode = args.get("mode") or "forecast"
        if mode == "historical":
            s = args.get("start_date") or per.get("start")
            e = args.get("end_date") or per.get("end")
            res = open_meteo.historical(loc["latitude"], loc["longitude"], s, e)
            used = {"mode": mode, "start_date": s, "end_date": e}
        else:
            days = int(args.get("days") or per.get("days") or 3)
            res = open_meteo.forecast(loc["latitude"], loc["longitude"], days)
            used = {"mode": "forecast", "days": days}
        return Outcome(result=res, artifacts=res["artifacts"], summary=_weather_summary(res), location=loc, period={"start": used.get("start_date"), "end": used.get("end_date"), "days": used.get("days")},
                       used_args=used, notes=notes)
    if name == "get_fire_detections":
        loc, notes = _resolve_location(args, defaults)
        if not loc:
            return _need_location(name, notes)
        box = _bbox(loc, args, defaults, 0.5)
        start = args.get("start_date") or (per.get("start") if per.get("kind") in ("date", "dates", "yesterday", "past_days", "today") else None)
        dr = int(args.get("day_range") or 0)
        if not dr:
            span = (date.fromisoformat(per["end"]) - date.fromisoformat(per["start"])).days + 1 if per.get("start") and per.get("end") and per.get("kind") in ("dates", "past_days") else 2
            dr = max(1, min(5, span))
        extra = []
        if start and per.get("end") and per.get("kind") in ("dates", "past_days"):
            full = (date.fromisoformat(per["end"]) - date.fromisoformat(start)).days + 1
            if full > 5:
                start = (date.fromisoformat(per["end"]) - timedelta(days=4)).isoformat(); dr = 5
                extra.append("The FIRMS API allows 1-5 days per request; the most recent 5 days of your period were queried.")
        res = firms.detections(box, start, dr)
        if extra:
            res["limitations"] = extra + res["limitations"]
        return Outcome(result=res, artifacts=res["artifacts"], summary=_fire_summary(res), location=loc, period={"start": start, "day_range": dr}, used_args={"bbox": box, "start_date": start, "day_range": dr}, notes=notes)
    if name == "list_fire_danger":
        loc, notes = None, []
        if any(args.get(k) is not None for k in ("place", "latitude", "bbox")) or defaults.get("location"):
            loc, notes = _resolve_location(args, defaults)
        la, lo = (loc["latitude"], loc["longitude"]) if loc else (None, None)
        g = fire_danger.danger_for_location(la, lo)
        gw = g["gwis"]
        if gw["status"] != "ok" and not g["usgs"]:
            return Outcome(result=gw, artifacts=[], summary={}, location=loc, period=None, used_args={})
        merged = dict(gw)
        merged["routing"] = g["routing"]
        merged["usgs"] = g["usgs"]
        arts = list(gw["artifacts"])
        if g["usgs"] and g["usgs"]["status"] == "ok":
            arts = g["usgs"]["artifacts"] + arts
        merged["artifacts"] = arts
        return Outcome(result=merged, artifacts=arts, summary=_danger_summary(merged), location=loc, period=None, used_args={"keyword": args.get("keyword")}, notes=notes)
    if name == "search_satellite_scenes":
        loc, notes = _resolve_location(args, defaults)
        if not loc:
            return _need_location(name, notes)
        box = _bbox(loc, args, defaults, 0.15)
        end = args.get("end_date") or per.get("end") or today.isoformat()
        start = args.get("start_date") or per.get("start") or (date.fromisoformat(end) - timedelta(days=30)).isoformat()
        res = copernicus.search_scenes(box, start, end, args.get("collection") or "sentinel-2-l2a", args.get("max_cloud", 30))
        return Outcome(result=res, artifacts=res["artifacts"], summary=_scene_summary(res), location=loc, period={"start": start, "end": end},
                       used_args={"bbox": box, "start": start, "end": end, "collection": args.get("collection") or "sentinel-2-l2a"}, notes=notes)
    if name == "get_lst":
        loc, notes = _resolve_location(args, defaults)
        if not loc:
            return _need_location(name, notes)
        end = args.get("end_date") or (per.get("end") if per.get("kind") in ("date", "dates", "yesterday", "past_days", "year", "controls") else None) or (today - timedelta(days=10)).isoformat()
        start = args.get("start_date") or (per.get("start") if per.get("kind") in ("date", "dates", "yesterday", "past_days", "year", "controls") else None) or (date.fromisoformat(end) - timedelta(days=55)).isoformat()
        res = earthdata.lst_point(loc["latitude"], loc["longitude"], start, end)
        return Outcome(result=res, artifacts=res["artifacts"], summary=_lst_summary(res), location=loc, period={"start": start, "end": end}, used_args={"start": start, "end": end}, notes=notes)
    if name == "forecast_fire_danger":
        text = defaults.get("message") or args.get("place") or ""
        try:
            loc, notes = _resolve_location(args, defaults)
        except Exception:
            loc, notes = None, []
        hit = None
        try:
            hit = fire_outlook.match_region_text(text, fire_outlook.nifc_region_names()) if text else None
        except Exception:
            hit = None
        if not loc and not hit:
            return _need_location(name, notes)
        if loc and not hit and re.search(r"central point|representative", loc.get("name", "")):
            r = envelope("EarthTrend", "Wildfire danger outlook", "fire_danger_outlook", "invalid_request", "LOCATION_TOO_BROAD",
                         f"'{loc['name'].split(' (')[0]}' covers many Predictive Service Areas; naming it would give one arbitrary point. Name a smaller place or a region such as 'Northern California', or give coordinates.")
            return Outcome(result=r, artifacts=[], summary={"needs": "location", "too_broad": True}, location=None, period=None, used_args={}, tool=name, status="invalid_request", duration_ms=0, notes=notes)
        bbox = loc.get("bbox") if loc else None
        res = fire_outlook.forecast_fire_danger(loc["latitude"] if loc else None, loc["longitude"] if loc else None, bbox, text if hit else None, args.get("start_date"), args.get("end_date"),
                                                args.get("window") or "next_calendar_month", args.get("source") or "auto", loc["name"] if loc else None, lang=defaults.get("lang") or "en")
        if res.get("reason_code") == "LOCATION_REQUIRED":
            return _need_location(name, notes)
        map_loc = loc
        if res.get("status") == "ok" and (res.get("actual") or {}).get("mode") == "named_region":
            from shapely.geometry import shape as _shape
            polys = [_shape(p["geometry"]) for a in res["artifacts"] if a["type"] == "map_polygons" for p in a["polygons"]]
            if polys:
                bs = [g.bounds for g in polys]                       # per-polygon bounds: the official polygons can be self-touching, so no union is attempted
                b = (min(x[0] for x in bs), min(x[1] for x in bs), max(x[2] for x in bs), max(x[3] for x in bs))
                map_loc = {"name": hit["name"] + (" (NIFC region)" if hit else ""), "latitude": (b[1] + b[3]) / 2, "longitude": (b[0] + b[2]) / 2, "bbox": [b[0], b[1], b[2], b[3]], "region": True, "source": "NIFC region name"}
        win = (res.get("data") or {}).get("window") or {}
        summ = _outlook_summary(res)
        return Outcome(result=res, artifacts=res["artifacts"], summary=summ, location=map_loc, period={"start": win.get("start"), "end": win.get("end")}, used_args={"window": args.get("window") or "next_calendar_month"}, notes=notes)
    if name == "forecast_monthly":
        loc, notes = _resolve_location(args, defaults)
        if not loc:
            return _need_location(name, notes)
        res = _forecast_monthly(loc["latitude"], loc["longitude"], args.get("variable") or defaults.get("variable") or "air_temperature", int(args.get("months") or 12), args.get("train_start_year"), place=loc["name"])
        summ = (res.get("data") or {}).get("summary") if res.get("status") == "ok" else {"status": res["status"], "reason_code": res["reason_code"], "message": res["message"]}
        return Outcome(result=res, artifacts=res["artifacts"], summary=summ, location=loc, period={"start": (res.get("actual") or {}).get("period", {}).get("first"), "end": (res.get("actual") or {}).get("period", {}).get("last")},
                       used_args={"variable": res["request"].get("variable"), "months": res["request"].get("months")}, notes=notes)
    if name == "get_ndvi":
        loc, notes = _resolve_location(args, defaults)
        if not loc:
            return _need_location(name, notes)
        box = _bbox(loc, args, defaults, 0.05)
        end = args.get("end_date") or per.get("end") or today.isoformat()
        start = args.get("start_date") or per.get("start") or (date.fromisoformat(end) - timedelta(days=60)).isoformat()
        res = copernicus.ndvi_statistics(box, start, end, args.get("max_cloud", 30), 10)
        return Outcome(result=res, artifacts=res["artifacts"], summary=_ndvi_summary(res), location=loc, period={"start": start, "end": end}, used_args={"bbox": box, "start": start, "end": end}, notes=notes)
    if name == "search_earth_datasets":
        kw = str(args.get("keyword") or "").strip()
        res = gee.catalog_search(kw) if args.get("catalog") == "gee" else earthdata.search_collections(kw)
        return Outcome(result=res, artifacts=res["artifacts"], summary=_dataset_summary(res), location=None, period=None, used_args={"keyword": kw, "catalog": args.get("catalog") or "cmr"})
    r = envelope("EarthTrend", name, "map_visualization", "invalid_request", "UNKNOWN_TOOL", f"Unknown tool '{name}'.")
    return Outcome(result=r, artifacts=[], summary={}, location=None, period=None, used_args={})


# ---- summaries (the ONLY numbers a model explanation may use) ----------------------------------------------
def _trend_summary(r: dict) -> dict:
    if r.get("status") != "ok":
        return {"status": r.get("status"), "reason_code": r.get("reason_code"), "message": r.get("message")}
    t = r["test"]
    return {"status": "ok", "variable": r["variable"]["name"], "region": r["region"]["name"], "period": r["period_actual"], "units": r["units"], "n_used": t["n_used"], "aggregation": r["aggregation"]["chosen"],
            "test": t["test_name"], "kendall_tau": t["kendall_tau"], "p_value": t["p_value"], "alpha": t["alpha"], "significant": t["significant"], "direction": t["direction"], "sen_slope": t["sen_slope"],
            "interpretation": r["interpretation"], "valid_months": r["data_quality"]["valid_months"], "missing_months": r["data_quality"]["missing_months"], "cache_hit": r["source"].get("cache_hit")}


def _weather_summary(r: dict) -> dict:
    if r["status"] != "ok":
        return {"status": r["status"], "reason_code": r["reason_code"], "message": r["message"]}
    d = r["data"]["daily"]
    rows = [{"date": d["time"][i], "tmax_c": d["temperature_2m_max"][i], "tmin_c": d["temperature_2m_min"][i], "precip_mm": d["precipitation_sum"][i], "wind_max_kmh": d["wind_speed_10m_max"][i]} for i in range(len(d["time"]))]
    def mean(k):
        v = [x[k] for x in rows if x[k] is not None]
        return round(sum(v) / len(v), 2) if v else None
    mid = [(x["tmax_c"] + x["tmin_c"]) / 2 for x in rows if x["tmax_c"] is not None and x["tmin_c"] is not None]
    pr = [x["precip_mm"] for x in rows if x["precip_mm"] is not None]
    # statistics over the WHOLE period (the daily list below is capped at 16 rows, so the model must never infer a period statistic from it)
    stats = {"n_days": len(rows), "daily_rows_shown": min(16, len(rows)), "mean_tmax_c": mean("tmax_c"), "mean_tmin_c": mean("tmin_c"), "mean_midrange_c": round(sum(mid) / len(mid), 2) if mid else None,
             "highest_tmax_c": max((x["tmax_c"] for x in rows if x["tmax_c"] is not None), default=None), "lowest_tmin_c": min((x["tmin_c"] for x in rows if x["tmin_c"] is not None), default=None),
             "total_precip_mm": round(sum(pr), 1) if pr else None, "midrange_note": "(max+min)/2 of each day, averaged; not a true daily mean"}
    return {"status": "ok", "product": r["product"], "timezone": r["actual"]["timezone"], "grid": r["actual"]["grid"], "period": r["actual"]["period"], "units": r["units"], "daily": rows[:16], "period_stats": stats,
            "source_type": r["actual"].get("source_type") or "operational forecast", "issue_time": r["actual"].get("issue_time"), "cache": r["cache"]}


def _fire_summary(r: dict) -> dict:
    if r["status"] not in ("ok", "no_data"):
        return {"status": r["status"], "reason_code": r["reason_code"], "message": r["message"]}
    return {"status": r["status"], "source": r["product"], "n_detections": (r.get("actual") or {}).get("n_detections", 0), "period": (r.get("actual") or {}).get("period"),
            "by_day": r["quality"].get("by_day"), "by_confidence": r["quality"].get("by_confidence"), "frp_max_mw": r["quality"].get("frp_max_mw"), "frp_total_mw": r["quality"].get("frp_total_mw")}


def _danger_summary(r: dict) -> dict:
    prods = (r.get("data") or {}).get("products", [])
    return {"status": r["status"], "n_gwis_layers": len(prods), "layers": [p["layer"] for p in prods][:12], "routing": r.get("routing"),
            "usgs_status": (r.get("usgs") or {}).get("status"), "usgs_palette_index": ((r.get("usgs") or {}).get("data") or {}).get("palette_index"),
            "usgs_valid_time": ((r.get("usgs") or {}).get("actual") or {}).get("valid_time")}


def _scene_summary(r: dict) -> dict:
    if r["status"] not in ("ok", "no_data"):
        return {"status": r["status"], "reason_code": r["reason_code"], "message": r["message"]}
    sc = (r.get("data") or {}).get("scenes", [])
    cc = [s["cloud_cover_percent"] for s in sc if s["cloud_cover_percent"] is not None]
    return {"status": r["status"], "collection": r["product"], "n_scenes": len(sc), "first": sc[-1]["datetime"] if sc else None, "last": sc[0]["datetime"] if sc else None,
            "cloud_min": min(cc) if cc else None, "cloud_max": max(cc) if cc else None, "discovery_only": True}


def _lst_summary(r: dict) -> dict:
    if r["status"] != "ok":
        return {"status": r["status"], "reason_code": r["reason_code"], "message": r["message"]}
    q = r["quality"]
    return {"status": "ok", "product": r["product"], "n_valid": q["n_valid"], "n_total": q["n_total"], "n_filtered": q["n_filtered"], "filter_reasons": q["filter_reasons"], "period": r["actual"]["period"],
            "mean_c": q["mean_c"], "min_c": q["min_c"], "max_c": q["max_c"], "samples": r["data"]["samples"][:60], "units": r["units"], "task_id": r["request"].get("task_id")}


def _outlook_summary(r: dict) -> dict:
    d = r.get("data") or {}
    if r.get("status") != "ok":
        return {"status": r.get("status"), "reason_code": r.get("reason_code"), "message": r.get("message"), "sources": d.get("sources"), "window": (d.get("window") or {}).get("kind")}
    a = r.get("actual") or {}
    obs = d.get("observed") or {}
    out = {"status": "ok", "source": r.get("provider"), "product": r.get("product"), "window_kind": (d.get("window") or {}).get("kind"), "window_start": (d.get("window") or {}).get("start"), "window_end": (d.get("window") or {}).get("end"),
           "window_note": (d.get("window") or {}).get("note"), "issue_label": a.get("issue_label") or a.get("issue_date"), "valid_months": a.get("valid_months"), "spatial_mode": a.get("mode"), "psas": (a.get("psas") or [])[:12],
           "months": [{"month": m["label"], "category": m["headline"], "mixed": m["mixed"], "shares": {k: v["share"] for k, v in m["categories"].items()}, "days_in_request": m["days_in_request"]} for m in (d.get("months") or [])],
           "category_meaning": d.get("definition"), "limitations": (r.get("limitations") or [])[:5], "other_sources": d.get("sources"),
           "ensemble": ({"variable": d["analysis"].get("variable"), "units": d["analysis"].get("units"), "members": d["analysis"].get("n_members_used"), "median": d["analysis"]["window_mean"]["ensemble_median"], "min": d["analysis"]["window_mean"]["ensemble_min"],
                         "max": d["analysis"]["window_mean"]["ensemble_max"], "issue_date": d.get("issue_date"), "age_days": d.get("age_days"), "valid_window": d.get("valid_window"), "categories": bool(d["analysis"].get("reference")), "member_shares": d["analysis"].get("category_shares")} if d.get("analysis") else None),
           "observed": {"n_detections": obs.get("n_detections"), "label": obs.get("label"), "note": obs.get("note")} if obs else None}
    return out


def _ndvi_summary(r: dict) -> dict:
    if r["status"] not in ("ok", "no_data"):
        return {"status": r["status"], "reason_code": r["reason_code"], "message": r["message"]}
    iv = (r.get("data") or {}).get("intervals", [])
    good = [x for x in iv if x.get("mean") is not None and x.get("valid_pixels", 0) >= 0.5 * (x.get("valid_pixels", 0) + (x.get("no_data_pixels") or 0))]   # >= half of the pixels valid after masking
    return {"status": r["status"], "n_intervals": len(iv), "n_usable": len(good), "first": iv[0]["from"] if iv else None, "last": iv[-1]["to"] if iv else None,
            "mean_ndvi": round(sum(x["mean"] for x in good) / len(good), 3) if good else None, "intervals": [{k: x[k] for k in ("from", "to", "mean", "valid_pixels", "no_data_pixels")} for x in iv]}


def _dataset_summary(r: dict) -> dict:
    if r["status"] not in ("ok", "no_data"):
        return {"status": r["status"], "reason_code": r["reason_code"], "message": r["message"]}
    d = (r.get("data") or {})
    items = d.get("collections") or d.get("datasets") or []
    return {"status": r["status"], "n": len(items), "items": [{"id": i.get("concept_id") or i.get("id"), "name": i.get("short_name") or i.get("title"), "version": i.get("version"), "title": i.get("title")} for i in items[:8]]}
