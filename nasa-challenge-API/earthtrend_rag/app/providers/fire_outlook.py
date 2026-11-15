"""One-month wildfire DANGER outlook for a place / region.

What is (and is not) produced
* NIFC Predictive Services "Significant Wildland Fire Potential" outlook (US only): an OFFICIAL, categorical (above / normal / below normal) monthly outlook per
  Predictive Service Area. Live, public ArcGIS REST service. It is NOT a probability of fire occurrence.
* Copernicus CEMS seasonal fire danger indices (global, GEFF driven by ECMWF SEAS5 ensembles, via the EWDS API): ensemble FORECAST FIRE-WEATHER DANGER INDEX
  (e.g. fire_weather_index). Needs an EWDS account, the dataset licence and a personal access token. Everything below the credential gate is implemented and
  tested with synthetic files; the live download is "blocked: credentials" until the token exists - a configured token alone is never reported as success.
* FIRMS detections are OBSERVATIONS (context only, never a forecast). Zero detections does not mean zero future danger.
* No short-range forecast is stretched to a month, no index is converted to a percentage, nothing is inferred from temperature alone.
"""
from __future__ import annotations

import calendar
import hashlib
import json
import math
import re
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from app.config import get_settings, load_credential
from app.providers.base import ProviderError, envelope, fail, http_json, sanitize, strict

NIFC_BASE = "https://fsapps.nwcg.gov/psp/arcgis/rest/services/npsg/Outlooks_Monthly_Extended/MapServer"
NIFC_LINKS = ["https://www.nifc.gov/nicc/predictive-services/outlooks", "https://fsapps.nwcg.gov/psp/npsg/forecast/home/downloads", NIFC_BASE]
EWDS_BASE = "https://ewds.climate.copernicus.eu/api/retrieve/v1"
EWDS_CAT = "https://ewds.climate.copernicus.eu/api/catalogue/v1/collections/cems-fire-seasonal"
EWDS_DATASET = "cems-fire-seasonal"
EWDS_LINKS = ["https://ewds.climate.copernicus.eu/datasets/cems-fire-seasonal?tab=overview", "https://www.ecmwf.int/en/forecasts/datasets/seasonal-forecast-fire-danger-indices-copernicus-emergency-management-service",
              "https://confluence.ecmwf.int/spaces/CEMS/pages/382667784/CEMS-Fire%2BData%2Baccess", "https://ewds.climate.copernicus.eu/how-to-api"]
EWDS_SETUP = {"env": "EWDS_API_KEY (optional EWDS_API_URL)", "register": "https://ewds.climate.copernicus.eu/", "licence": "https://ewds.climate.copernicus.eu/datasets/cems-fire-seasonal?tab=download#manage-licences",
              "token": "https://ewds.climate.copernicus.eu/how-to-api",
              "steps": "1) Create/log in to a free account at https://ewds.climate.copernicus.eu/ (this is a SEPARATE account from Earthdata and from Copernicus Data Space). 2) Accept the dataset licence on the "
                       "dataset's Download tab. 3) Copy your personal access token from https://ewds.climate.copernicus.eu/how-to-api and put EWDS_API_KEY=<token> in the backend .env (never in the chat), then restart.",
              "permissions": "free; licence acceptance required"}
HORIZON_DAYS_EWDS = 216
SKILL_STATEMENT = {"en": "This is an official model outlook; local forecast skill has not been verified by this application.",
                   "ar": "هذا توقع رسمي مبني على نموذج؛ ولم يتحقق هذا التطبيق من مهارة التوقع محليًا."}
NIFC_DEFINITION = {"en": "NIFC's monthly National Significant Wildland Fire Potential Outlook identifies areas, by month for the next four months, with above, below or near-normal significant fire potential "
                         "(wording from the NIFC outlooks page). It is a categorical assessment per Predictive Service Area relative to normal - not a numerical probability of any fire event.",
                   "ar": "توقع NIFC الشهري لإمكانية الحرائق البرية الكبيرة يحدد المناطق، شهرًا بشهر لأربعة أشهر قادمة، بإمكانية أعلى أو أقل أو قريبة من المعتاد (بحسب صياغة صفحة NIFC). هو تصنيف فئوي لكل منطقة خدمة تنبؤية "
                         "نسبةً إلى المعتاد، وليس احتمالًا رقميًا لأي حدث حريق."}
CATEGORY = {"Above": {"en": "Above normal", "ar": "أعلى من المعتاد", "tone": "hot", "color": "#b3261e"}, "Normal": {"en": "Normal", "ar": "قريبة من المعتاد", "tone": "neutral", "color": "#8a8f98"},
            "Below": {"en": "Below normal", "ar": "أقل من المعتاد", "tone": "good", "color": "#0b6e3f"}}
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]


# ---- windows ---------------------------------------------------------------------------------------------------------------------------------
def resolve_window(kind: str | None, start: str | None, end: str | None, today: date) -> tuple[date, date, str]:
    """'next_calendar_month' = the whole calendar month after the current one; 'next_30_days' = today .. today+29; explicit dates otherwise."""
    if kind == "next_calendar_month":
        y, m = (today.year + (today.month == 12), today.month % 12 + 1)
        return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1]), "next_calendar_month"
    if kind == "next_30_days":
        return today, today + timedelta(days=29), "next_30_days"
    if start and end:
        return date.fromisoformat(start), date.fromisoformat(end), "custom"
    return resolve_window("next_calendar_month", None, None, today)


def window_months(start: date, end: date) -> list[dict]:
    out, d = [], date(start.year, start.month, 1)
    while d <= end:
        last = calendar.monthrange(d.year, d.month)[1]
        a, b = max(start, d), min(end, date(d.year, d.month, last))
        out.append({"year": d.year, "month": d.month, "label": f"{d.year}-{d.month:02d}", "days_in_request": (b - a).days + 1, "days_in_month": last, "first": str(a), "last": str(b)})
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    return out


def parse_issue_label(label: str | None) -> tuple[int, int] | None:
    m = re.match(r"\s*([A-Za-z]+)\s+(\d{4})", label or "")
    if m and m.group(1).lower() in MONTHS:
        return int(m.group(2)), MONTHS.index(m.group(1).lower()) + 1
    return None


def freshness(issue_ym: tuple[int, int] | None, today: date) -> dict:
    """NIFC issues on the first (work) day of each month and says it is updated no later than the 5th. Current = issued this month, or last month while the new issue is still due."""
    if not issue_ym:
        return {"current": False, "reason": "issue month not provided by the service"}
    age = (today.year - issue_ym[0]) * 12 + today.month - issue_ym[1]
    if age == 0:
        return {"current": True, "age_months": 0}
    if age == 1 and today.day <= 7:
        return {"current": True, "age_months": 1, "note": "the new monthly issue is due (NIFC updates no later than the 5th of the month)"}
    return {"current": False, "age_months": age, "reason": f"latest issue is {age} month(s) old"}


# ---- NIFC ------------------------------------------------------------------------------------------------------------------------------------
def _nifc_query(layer: int, *, geometry=None, where: str | None = None, return_geometry: bool = False, use_cache: bool = True) -> list[dict]:
    p = {"f": "geojson" if return_geometry else "json", "outFields": "PSANAME,GACCName,FirePotent,Updatetime,PSANationa", "returnGeometry": "true" if return_geometry else "false"}
    if return_geometry:
        p.update(outSR=4326, maxAllowableOffset=0.02)
    if where:
        p["where"] = where
    if geometry:
        kind, g = geometry
        p.update(geometry=g, geometryType=kind, inSR=4326, spatialRel="esriSpatialRelIntersects")
    d, meta = http_json("nifc", "GET", f"{NIFC_BASE}/{layer}/query", params=p, ttl=6 * 3600, use_cache=use_cache)
    if isinstance(d, dict) and d.get("error"):
        raise ProviderError(f"NIFC query error: {d['error'].get('message')}", "upstream_error", d["error"].get("code"))
    feats = d.get("features", [])
    return [{"properties": f.get("properties") or f.get("attributes") or {}, "geometry": f.get("geometry")} for f in feats], meta


def nifc_region_names() -> dict:
    """PSA and GACC names served by NIFC (live, cached): used to recognise region names such as 'Northern California' without inventing any boundary."""
    feats, _ = _nifc_query(0)
    return {"gacc": sorted({f["properties"]["GACCName"] for f in feats if f["properties"].get("GACCName")}), "psa": sorted({f["properties"]["PSANAME"] for f in feats if f["properties"].get("PSANAME") and f["properties"]["PSANAME"] != "No PSA Assigned"})}


def match_region_text(text: str | None, names: dict) -> dict | None:
    """'northern california' -> GACC 'Northern California Geographic Area' (official name match); never a guess.
    Multi-word official names (e.g. 'northern california') may appear inside a longer phrase; a single word ('alaska', 'southwest') only when it IS the whole place phrase,
    so that 'southwest idaho' never selects the Southwest Coordination Center and 'California' alone never selects 'Northern California'."""
    if not text:
        return None
    t = re.sub(r"[^a-z0-9 ]+", " ", text.lower())
    t = re.sub(r"\b(the|region|of|in|for|fire|fires|wildfire|wildfires|danger|risk|potential|outlook|next|month|months|days|day|30|thirty|what|is|are|how|will|be|there|any|within|over|area|areas)\b", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) < 4:
        return None
    for g in sorted(names["gacc"], key=len, reverse=True):
        gn = re.sub(r"\b(geographic area|coordination center|interagency|area)\b", "", g.lower())
        gn = re.sub(r"\s+", " ", gn).strip()
        multi = len(gn.split()) >= 2
        if gn and ((multi and re.search(r"(?<![a-z])" + re.escape(gn) + r"(?![a-z])", t)) or t == gn):
            return {"kind": "gacc", "name": g.split(" Coordination Center")[0]}            # the service lists a GACC under two spellings: LIKE '<name>%' matches both
    for p in sorted(names["psa"], key=len, reverse=True):
        pn = re.sub(r"[^a-z0-9 ]+", " ", p.lower()).strip()
        if len(pn) >= 5 and re.search(r"(?<![a-z])" + re.escape(pn) + r"(?![a-z])", t):
            return {"kind": "psa", "name": p}
    return None


def _scaled_polygon(geom, lat_mid: float):
    from shapely.geometry import shape
    from shapely.ops import transform
    k = math.cos(math.radians(lat_mid))
    return transform(lambda x, y, z=None: (x * k, y), shape(geom))


def nifc_outlook(lat: float | None, lon: float | None, bbox: list[float] | None, region_text: str | None, start: date, end: date, today: date, lang: str = "en") -> dict:
    prod = "Significant Wildland Fire Potential Outlook (monthly, by Predictive Service Area)"
    t0 = time.monotonic()
    try:
        names = nifc_region_names() if region_text else None
        region = match_region_text(region_text, names) if names else None
        if region:
            nm = region["name"].replace("'", "''")
            sel = {"where": f"GACCName LIKE '{nm}%'" if region["kind"] == "gacc" else f"PSANAME='{nm}'"}
            mode = "named_region"
        elif bbox:
            sel = {"geometry": ("esriGeometryEnvelope", ",".join(str(float(x)) for x in bbox))}
            mode = "bbox"
        elif lat is not None and lon is not None:
            sel = {"geometry": ("esriGeometryPoint", f"{float(lon)},{float(lat)}")}
            mode = "point"
        else:
            return envelope("NIFC Predictive Services", prod, "fire_danger_outlook", "invalid_request", "LOCATION_REQUIRED", "A place, point or box is required.", source_links=NIFC_LINKS)
        first, meta = _nifc_query(0, **sel)
    except ProviderError as e:
        return fail("NIFC Predictive Services", prod, "fire_danger_outlook", e, source_links=NIFC_LINKS)
    assigned = [f for f in first if f["properties"].get("PSANAME") != "No PSA Assigned"]
    if not assigned:
        return envelope("NIFC Predictive Services", prod, "fire_danger_outlook", "unsupported_region", "OUTSIDE_NIFC_COVERAGE",
                        "The NIFC outlook covers US Predictive Service Areas only; this location is outside them.", source_links=NIFC_LINKS, request={"mode": mode, "lat": lat, "lon": lon, "bbox": bbox})
    label = first[0]["properties"].get("Updatetime")
    issue_ym = parse_issue_label(label)
    fresh = freshness(issue_ym, today)
    base_env = dict(source_links=NIFC_LINKS, request={"mode": mode, "lat": lat, "lon": lon, "bbox": bbox, "region": region, "start": str(start), "end": str(end)})
    if not fresh["current"]:
        return envelope("NIFC Predictive Services", prod, "fire_danger_outlook", "no_data", "NO_CURRENT_FORECAST",
                        f"The latest NIFC outlook available is the {label} issue ({fresh.get('reason')}); it is not shown as a current outlook.", actual={"issue_label": label, "freshness": fresh}, **base_env)
    months = window_months(start, end)
    rows, polys, gaps = [], [], []
    try:
        for m in months:
            layer = (m["year"] - issue_ym[0]) * 12 + m["month"] - issue_ym[1]          # 0 = issue month ... 3 = three months later
            if not 0 <= layer <= 3:
                gaps.append(m["label"]); continue
            feats, _ = _nifc_query(layer, return_geometry=True, **sel) if mode in ("named_region", "bbox") or m is months[0] else _nifc_query(layer, **sel)
            feats = [f for f in feats if f["properties"].get("PSANAME") != "No PSA Assigned" and f["properties"].get("FirePotent") in CATEGORY]
            if not feats:
                gaps.append(m["label"]); continue
            cats: dict[str, dict] = {}
            if mode == "point":
                f = feats[0]
                cats[f["properties"]["FirePotent"]] = {"share": 1.0, "psas": [f["properties"]["PSANAME"]]}
            else:
                from shapely.geometry import box
                have_geom = all(f.get("geometry") for f in feats)
                if not have_geom:
                    feats, _ = _nifc_query(layer, return_geometry=True, **sel)
                    feats = [f for f in feats if f["properties"].get("PSANAME") != "No PSA Assigned" and f["properties"].get("FirePotent") in CATEGORY]
                from shapely.geometry import shape as _shape
                if bbox:
                    mid = (bbox[1] + bbox[3]) / 2
                else:
                    bs = [_shape(f["geometry"]).bounds for f in feats]
                    mid = sum((x[1] + x[3]) / 2 for x in bs) / len(bs)
                area_tot = 0.0
                for f in feats:
                    poly = _scaled_polygon(f["geometry"], mid)
                    if bbox:
                        k = math.cos(math.radians(mid))
                        poly = poly.intersection(box(bbox[0] * k, bbox[1], bbox[2] * k, bbox[3]))
                    a = float(poly.area)
                    if a > 0:
                        c = cats.setdefault(f["properties"]["FirePotent"], {"share": 0.0, "psas": []})
                        c["share"] += a; c["psas"].append(f["properties"]["PSANAME"]); area_tot += a
                for c in cats.values():
                    c["share"] = round(c["share"] / area_tot, 3) if area_tot else 0.0
            head = max(cats, key=lambda k: cats[k]["share"])
            rows.append({**m, "layer": layer + 1, "headline": head, "categories": {k: {"share": v["share"], "psas": sorted(set(v["psas"]))} for k, v in cats.items()}, "mixed": len(cats) > 1})
            if m is months[0] or mode != "point":
                for f in feats[:40]:
                    if f.get("geometry"):
                        polys.append({"geometry": f["geometry"], "label": f"{f['properties']['PSANAME']}: {CATEGORY[f['properties']['FirePotent']][lang]} ({m['label']})", "category": f["properties"]["FirePotent"], "color": CATEGORY[f["properties"]["FirePotent"]]["color"], "month": m["label"]})
                polys = [p for p in polys if p["month"] == rows[0]["label"]]
    except ProviderError as e:
        return fail("NIFC Predictive Services", prod, "fire_danger_outlook", e, source_links=NIFC_LINKS)
    if not rows:
        return envelope("NIFC Predictive Services", prod, "fire_danger_outlook", "no_data", "MISSING_FORECAST_COVERAGE",
                        f"The NIFC outlook ({label}) does not cover the requested period ({', '.join(gaps)}); it covers the issue month and the next three months where issued.", actual={"issue_label": label}, **base_env)
    psa_names = sorted({p for r in rows for c in r["categories"].values() for p in c["psas"]})
    arts = [{"type": "category_strip", "title": "Significant wildland fire potential by month (official NIFC categories, NOT probabilities)", "inline": True,
             "cells": [{"label": r["label"], "category": r["headline"], "text": CATEGORY[r["headline"]][lang], "color": CATEGORY[r["headline"]]["color"], "mixed": r["mixed"], "shares": {k: v["share"] for k, v in r["categories"].items()}} for r in rows],
             "legend": [{"category": k, "text": v[lang], "color": v["color"]} for k, v in CATEGORY.items()]}]
    if polys:
        arts.append({"type": "map_polygons", "title": f"Forecast layer: NIFC predictive service areas, {rows[0]['label']} outlook (official polygons)", "layer_role": "forecast", "polygons": polys,
                     "legend": [{"category": k, "text": v[lang], "color": v["color"]} for k, v in CATEGORY.items()]})
    lim = [NIFC_DEFINITION[lang], SKILL_STATEMENT[lang],
           "Monthly categories only: there is no daily detail and no exact rolling 30-day product." if lang == "en" else "تصنيفات شهرية فقط: لا تفاصيل يومية ولا منتج دقيق لثلاثين يومًا متحركة.",
           "NIFC issues these outlooks only when Geographic Areas are in fire season." if lang == "en" else "تصدر NIFC هذه التوقعات فقط عندما تكون المناطق الجغرافية في موسم الحرائق.",
           "No published verification statistics for this exact product were retrieved by this application." if lang == "en" else "لم يسترجع هذا التطبيق إحصاءات تحقق منشورة لهذا المنتج بالذات."]
    if mode != "point":
        lim.append("Shares are planar area fractions (longitude scaled by cos(latitude)) of the intersection with the official PSA polygons; 'No PSA Assigned' areas are excluded." if lang == "en" else "النسب مساحات مستوية تقريبية (مع تقييس خط الطول بجيب تمام العرض) لتقاطع المنطقة مع مضلعات PSA الرسمية؛ وتُستبعد مناطق «No PSA Assigned».")
    if gaps:
        lim.append(f"Not covered by the product: {', '.join(gaps)}.")
    return strict(envelope(
        "NIFC Predictive Services", prod, "fire_danger_outlook", "ok", variables=["significant_wildland_fire_potential"], units={"category": "categorical (above / normal / below normal)"},
        actual={"issue_label": label, "issue_date": None, "issue_date_note": "the service provides the issue month only (updated on the first work day of the month, no later than the 5th)", "freshness": fresh,
                "valid_months": [r["label"] for r in rows], "spatial_unit": "Predictive Service Area polygons", "mode": mode, "psas": psa_names, "coverage_gaps": gaps},
        temporal_resolution="monthly", live=meta["live"], cache=meta["cache"], retrieved_at=meta["retrieved_at"], duration_ms=int((time.monotonic() - t0) * 1000), source_links=NIFC_LINKS,
        attribution="National Interagency Fire Center - Predictive Services", license="US Government work (public)", limitations=lim, quality={"ensemble_size": None, "calibration": "categorical; no probabilities provided"},
        request=base_env["request"], data={"months": rows, "definition": NIFC_DEFINITION[lang]}, artifacts=arts))


# ---- EWDS (Copernicus seasonal fire danger) ---------------------------------------------------------------------------------------------------
def ewds_key() -> str | None:
    """EWDS personal access token: EWDS_API_KEY (env / backend .env), or ~/.cdsapirc whose url points at the EWDS (a token for another Copernicus store is NOT accepted)."""
    k = load_credential("EWDS_API_KEY")
    if k:
        return k.get_secret_value()
    rc = Path.home() / ".cdsapirc"
    try:
        txt = rc.read_text(encoding="utf-8")
        kv = dict(re.findall(r"^\s*(url|key)\s*:\s*(\S+)", txt, re.M))
        if "ewds.climate.copernicus.eu" in kv.get("url", "") and kv.get("key"):
            return kv["key"]
    except OSError:
        pass
    return None


def ewds_availability(use_cache: bool = True) -> dict:
    """PUBLIC catalogue facts (no credentials): latest forecast start month with data, horizon, last update. Never says anything about access rights."""
    c, meta = http_json("ewds-cat", "GET", EWDS_CAT, headers={"Accept": "application/json"}, ttl=3600, use_cache=use_cache)
    cons_url = next(l["href"] for l in c["links"] if l["rel"] == "constraints")
    cons, _ = http_json("ewds-cons", "GET", cons_url, ttl=3600, use_cache=use_cache)
    ym = sorted({(int(y), int(m)) for e in cons for y in e.get("year", []) for m in e.get("month", [])})
    latest = ym[-1]
    msg = c.get("cads:message") or {}
    notice = {"severity": msg.get("severity"), "date": (msg.get("date") or "")[:10], "text": re.sub(r"\s+", " ", re.sub(r"\[([^\]]*)\]\(([^)]*)\)", r"\1 (\2)", msg.get("content") or "")).strip()} if msg.get("content") else None
    return {"latest_start": f"{latest[0]}-{latest[1]:02d}-01", "notice": notice, "catalogue_updated": c.get("updated"), "horizon_days": HORIZON_DAYS_EWDS, "license": c.get("license"), "doi": c.get("sci:doi"), "retrieved_at": meta["retrieved_at"], "live": meta["live"]}


def ewds_process_schema(use_cache: bool = True) -> dict:
    d, _ = http_json("ewds-proc", "GET", f"{EWDS_BASE}/processes/{EWDS_DATASET}", headers={"Accept": "application/json"}, ttl=24 * 3600, use_cache=use_cache)
    return d["inputs"]


def build_ewds_request(variable: str, years: list[int], month: int, valid_days: list[date], area: list[float], start_day: date, schema: dict, data_format: str = "netcdf") -> dict:
    """The request body, validated against the dataset's CURRENT process schema (enums / area shape): nothing is invented. leadtime_hour = hours from 00:00 of the start date
    to 12:00 of each valid day (the product is daily at 12:00 local time, once a month, start day 01)."""
    leads = sorted({int((d - start_day).days * 24 + 12) for d in valid_days})
    req = {"variable": [variable], "release_version": ["5"], "year": [str(y) for y in years], "month": [f"{month:02d}"], "day": ["01"], "leadtime_hour": [str(h) for h in leads], "data_format": data_format,
           "area": [round(area[0], 2), round(area[1], 2), round(area[2], 2), round(area[3], 2)]}          # [north, west, south, east] as in the dataset form
    problems = []
    for k, v in req.items():
        sc = schema.get(k, {}).get("schema") if k in schema else None
        if not sc:
            problems.append(f"unknown input '{k}'"); continue
        items = sc.get("items", sc)
        enum = items.get("enum")
        vals = v if isinstance(v, list) else [v]
        if enum and any(str(x) not in enum for x in vals):
            problems.append(f"{k}: value(s) outside the dataset's allowed set: {[x for x in vals if str(x) not in enum][:4]}")
    n, w, s, e = req["area"]
    if not (n > s and e > w and -90 <= s and n <= 90 and -180 <= w and e <= 180):
        problems.append("area must be [north, west, south, east] with north > south, east > west")
    if problems:
        raise ValueError("; ".join(problems))
    return req


def ewds_run(request: dict, key: str, dest: Path, max_wait_s: int = 600, poll_s: int = 10) -> dict:
    """Asynchronous job: submit -> bounded polling -> download -> content validation. Returns {status, path|reason}. The key is only ever sent as the PRIVATE-TOKEN header."""
    import httpx
    h = {"PRIVATE-TOKEN": key, "Content-Type": "application/json", "Accept": "application/json"}
    with httpx.Client(timeout=60, follow_redirects=True) as c:
        r = c.post(f"{EWDS_BASE}/processes/{EWDS_DATASET}/execution", headers=h, json={"inputs": request})
        if r.status_code in (401, 403):
            txt = (r.text or "").lower()
            if "licen" in txt or "terms" in txt:
                return {"status": "terms_not_accepted", "reason": sanitize(r.text[:300], key)}
            return {"status": "auth_failed", "reason": f"HTTP {r.status_code}"}
        if r.status_code not in (200, 201, 202):
            return {"status": "submit_failed", "reason": f"HTTP {r.status_code}: {sanitize(r.text[:300], key)}"}
        job = r.json().get("jobID")
        if not job:
            return {"status": "submit_failed", "reason": "no jobID in the response"}
        t0, st = time.monotonic(), None
        while time.monotonic() - t0 < max_wait_s:
            jr = c.get(f"{EWDS_BASE}/jobs/{job}", headers=h)
            st = jr.json().get("status") if jr.status_code == 200 else None
            if st == "successful":
                break
            if st in ("failed", "rejected", "dismissed"):
                return {"status": "job_failed", "reason": sanitize(json.dumps(jr.json())[:300], key), "job": job}
            time.sleep(poll_s)
        else:
            return {"status": "timeout", "reason": f"job {job} still '{st}' after {max_wait_s}s", "job": job}
        res = c.get(f"{EWDS_BASE}/jobs/{job}/results", headers=h).json()
        href = (res.get("asset", {}).get("value", {}) or {}).get("href")
        if not href:
            return {"status": "job_failed", "reason": "no result asset", "job": job}
        dest.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        with c.stream("GET", href, headers={}) as dl, open(dest, "wb") as f:
            dl.raise_for_status()
            for ch in dl.iter_bytes(1 << 20):
                size += len(ch)
                if size > 200 << 20:
                    return {"status": "too_large", "reason": "download above 200 MB"}
                f.write(ch)
    head = dest.read_bytes()[:8]
    if not (head[:4] == b"\x89HDF" or head[:3] == b"CDF"):
        return {"status": "bad_file", "reason": "the downloaded file is not NetCDF (maybe GRIB or an error page)", "path": str(dest)}
    return {"status": "ok", "path": str(dest), "bytes": size, "job": job}


def read_netcdf(path: str | Path) -> dict:
    """Validated read of an EWDS NetCDF: finds the data variable, ensemble/time/lat/lon axes and units from the FILE (names are not assumed)."""
    import netCDF4
    ds = netCDF4.Dataset(str(path))
    try:
        coords = {}
        for name, v in ds.variables.items():
            ln = name.lower()
            if ln in ("latitude", "lat"):
                coords["lat"] = name
            elif ln in ("longitude", "lon"):
                coords["lon"] = name
            elif ln in ("number", "member", "ensemble", "realization"):
                coords["member"] = name
            elif ln == "valid_time" or (ln == "time" and v.ndim >= 1 and "time" not in coords):
                coords["time"] = name                                  # valid_time (one value per step) wins over the scalar forecast reference 'time'
        data_vars = [n for n, v in ds.variables.items() if v.ndim >= 3 and n not in coords.values()]
        if not data_vars or "lat" not in coords or "lon" not in coords or "time" not in coords:
            raise ValueError(f"unrecognised NetCDF layout: variables={list(ds.variables)[:12]}")
        name = data_vars[0]
        v = ds.variables[name]
        arr = np.ma.filled(v[:].astype("float64"), np.nan)
        dims = list(v.dimensions)
        tvar = ds.variables[coords["time"]]
        units = getattr(v, "units", None)
        if units is None:
            raise ValueError("the data variable has no units attribute; refusing to guess")
        # axes -> [member, time, lat, lon]
        def axis(dname_vars):
            for i, d in enumerate(dims):
                if d in dname_vars:
                    return i
            return None
        ax_lat = dims.index(ds.variables[coords["lat"]].dimensions[0]); ax_lon = dims.index(ds.variables[coords["lon"]].dimensions[0])
        ax_t = dims.index(tvar.dimensions[-1]) if tvar.ndim >= 1 else None
        ax_m = dims.index(ds.variables[coords["member"]].dimensions[0]) if "member" in coords else None
        others = [i for i in range(len(dims)) if i not in (ax_lat, ax_lon, ax_t, ax_m)]
        for o in sorted(others, reverse=True):
            if arr.shape[o] != 1:
                raise ValueError(f"unexpected extra axis '{dims[o]}' of length {arr.shape[o]}")
            arr = np.take(arr, 0, axis=o)
            dims.pop(o)
            ax_lat, ax_lon = [a - (a > o) for a in (ax_lat, ax_lon)]
            ax_t = ax_t - (ax_t > o) if ax_t is not None else None
            ax_m = ax_m - (ax_m is not None and ax_m > o) if ax_m is not None else None
        order = [a for a in (ax_m, ax_t, ax_lat, ax_lon) if a is not None]
        arr = np.transpose(arr, order)
        if ax_m is None:
            arr = arr[None, ...]
        lat = np.ma.filled(ds.variables[coords["lat"]][:], np.nan).astype(float)
        lon = np.ma.filled(ds.variables[coords["lon"]][:], np.nan).astype(float)
        tv = netCDF4.num2date(tvar[:], tvar.units, only_use_cftime_datetimes=False, only_use_python_datetimes=True) if hasattr(tvar, "units") else None
        times = [date(t.year, t.month, t.day) for t in tv] if tv is not None else []
        members_missing = [int(i) for i in range(arr.shape[0]) if not np.isfinite(arr[i]).any()]
        return {"array": arr, "lat": lat, "lon": lon, "times": times, "units": units, "variable": name, "long_name": getattr(v, "long_name", None), "n_members": int(arr.shape[0]), "members_missing": members_missing}
    finally:
        ds.close()


def read_reference_netcdf(path: str | Path) -> dict:
    """EWDS re-forecast file (many start years): [member, year, step, lat, lon] -> pooled [member*year, step, lat, lon]; each (member, year) is one reference realisation."""
    import netCDF4
    ds = netCDF4.Dataset(str(path))
    try:
        v = ds.variables["fwinx"] if "fwinx" in ds.variables else next(x for n, x in ds.variables.items() if x.ndim == 5)
        if v.ndim != 5 or v.dimensions[0] != "number" or v.dimensions[1] != "time" or not getattr(v, "units", None):
            raise ValueError(f"unexpected reference layout {v.dimensions}")
        arr = np.ma.filled(v[:].astype("float64"), np.nan)
        n, y, st, la, lo = arr.shape
        return {"array": arr.reshape(n * y, st, la, lo), "times": None, "lat": np.ma.filled(ds.variables["latitude"][:], np.nan).astype(float),
                "lon": np.ma.filled(ds.variables["longitude"][:], np.nan).astype(float), "n_members": int(n), "n_years": int(y), "units": v.units}
    finally:
        ds.close()


_REF_JOBS: dict = {}


def _ref_request(variable, start_day, valid_days, area, schema):
    return build_ewds_request(variable, list(range(1981, 2017)), start_day.month, valid_days, area, start_day, schema)          # 1981-2016 re-forecast years of the same dataset


def _ref_fetch_bg(req: dict, key: str, dest: Path) -> None:
    def run():
        try:
            ewds_run(req, key, dest, max_wait_s=2400, poll_s=15)
        finally:
            _REF_JOBS.pop(str(dest), None)
    if str(dest) not in _REF_JOBS:
        import threading
        t = threading.Thread(target=run, daemon=True); _REF_JOBS[str(dest)] = t; t.start()


def analyze_ensemble(cur: dict, ref: dict | None, window: tuple[date, date]) -> dict:
    """Regional (cos-lat weighted) ensemble summary for the valid window. With a hindcast reference (same start month, same leads, 1981-2016 re-forecasts) the
    above/near/below-normal TERCILE categories are derived from the reference distribution only - never from invented thresholds."""
    A = cur["array"]
    w = np.cos(np.radians(cur["lat"]))[:, None] * np.ones((1, len(cur["lon"])))
    tmask = np.array([window[0] <= t <= window[1] for t in cur["times"]])
    if not tmask.any():
        raise ValueError("the file contains no day inside the requested window")
    def reg(a):                                                    # [member, time, lat, lon] -> [member, time] area-weighted mean ignoring NaN
        m = np.isfinite(a)
        num = np.nansum(np.where(m, a, 0) * w, axis=(-2, -1)); den = np.sum(m * w, axis=(-2, -1))
        return np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)
    daily = reg(A)[:, tmask]
    members_ok = [i for i in range(daily.shape[0]) if i not in cur["members_missing"]]
    daily = daily[members_ok]
    wmean = np.nanmean(daily, axis=1)
    out = {"n_members_used": int(len(members_ok)), "n_members_expected": cur["n_members"], "members_missing": cur["members_missing"], "units": cur["units"], "variable": cur["variable"], "window": [str(window[0]), str(window[1])],
           "dates": [str(t) for t, k in zip(cur["times"], tmask) if k],
           "daily": {"median": np.nanmedian(daily, axis=0).tolist(), "p10": np.nanpercentile(daily, 10, axis=0).tolist(), "p25": np.nanpercentile(daily, 25, axis=0).tolist(),
                     "p75": np.nanpercentile(daily, 75, axis=0).tolist(), "p90": np.nanpercentile(daily, 90, axis=0).tolist()},
           "window_mean": {"ensemble_median": float(np.nanmedian(wmean)), "ensemble_min": float(np.nanmin(wmean)), "ensemble_max": float(np.nanmax(wmean)), "ensemble_mean": float(np.nanmean(wmean))},
           "spread_note": "ensemble spread across members; it is NOT a complete or calibrated uncertainty estimate"}
    if ref is not None:
        R = reg(ref["array"])
        rmask = np.array([window[0].month == t.month and window[0].day <= t.day <= window[1].day or (t.month == window[1].month and t.day <= window[1].day) for t in ref["times"]]) if ref.get("times") else np.ones(R.shape[1], bool)
        rwm = np.nanmean(R[:, rmask], axis=1) if rmask.any() else np.nanmean(R, axis=1)
        rwm = rwm[np.isfinite(rwm)]
        if len(rwm) >= 30:
            t33, t67 = np.percentile(rwm, [100 / 3, 200 / 3])
            out["reference"] = {"n_values": int(len(rwm)), "tercile_33": float(t33), "tercile_67": float(t67), "definition": "terciles of the window-mean index over the 1981-2016 re-forecast ensemble (same start month and leads); a category is NOT a fire probability"}
            out["category_shares"] = {"below_normal": float(np.mean(wmean < t33)), "near_normal": float(np.mean((wmean >= t33) & (wmean <= t67))), "above_normal": float(np.mean(wmean > t67)),
                                      "definition": "fraction of ensemble members in each tercile of the reference distribution (relative frequency; calibration not verified)"}
        else:
            out["reference"] = None
            out["reference_note"] = "too few reference values to define terciles"
    return out


def ewds_outlook(lat, lon, bbox, start: date, end: date, today: date, variable: str = "fire_weather_index", lang: str = "en", use_cache: bool = True) -> dict:
    prod = f"CEMS seasonal fire danger ({variable})"
    t0 = time.monotonic()
    try:
        av = ewds_availability(use_cache)
    except ProviderError as e:
        return fail("Copernicus EWDS", prod, "fire_danger_outlook", e, source_links=EWDS_LINKS)
    start_day = date.fromisoformat(av["latest_start"])
    age = (today - start_day).days
    bx = bbox or [lon - 0.5, lat - 0.5, lon + 0.5, lat + 0.5]              # [west, south, east, north]
    n, w, so, e = bx[3], bx[0], bx[1], bx[2]                                 # the dataset form wants [north, west, south, east]
    info = {"availability": av, "issue_date": av["latest_start"], "age_days": age, "valid_window": [str(start), str(end)], "horizon_days": HORIZON_DAYS_EWDS}
    if (end - start_day).days > HORIZON_DAYS_EWDS or start < start_day:
        return envelope("Copernicus EWDS", prod, "fire_danger_outlook", "no_data", "MISSING_FORECAST_COVERAGE", f"The latest EWDS forecast starts {av['latest_start']} and covers {HORIZON_DAYS_EWDS} days; the requested window is outside it.", data=info, source_links=EWDS_LINKS)
    valid_days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    try:
        schema = ewds_process_schema(use_cache)
        req = build_ewds_request(variable, [start_day.year], start_day.month, valid_days, [n, w, so, e], start_day, schema)
    except ValueError as ex:
        return envelope("Copernicus EWDS", prod, "fire_danger_outlook", "invalid_request", "INVALID_EWDS_REQUEST", str(ex), data=info, source_links=EWDS_LINKS)
    except ProviderError as e:
        return fail("Copernicus EWDS", prod, "fire_danger_outlook", e, source_links=EWDS_LINKS)
    info["request_preview"] = req                                   # the exact body that is (or would be) sent; contains no secret
    key = ewds_key()
    upd_note = (f"Official EWDS notice ({av['notice']['date']}): {av['notice']['text']} The forecast issue used here is unchanged and remains valid for its own dates; no newer monthly issue should be expected until the migration finishes." if av.get("notice") else None)
    stale_note = f"The latest EWDS forecast was issued {av['latest_start']} ({age} days ago); a newer monthly issue is published after the start of each month." if age > 20 else None
    if not key:
        return envelope("Copernicus EWDS", prod, "fire_danger_outlook", "needs_credentials", "EWDS_API_KEY_MISSING",
                        "The global one-month outlook needs access to the Copernicus EWDS seasonal fire danger dataset (a separate free account, the dataset licence and a personal access token). Nothing was substituted.",
                        data=info, setup=EWDS_SETUP, source_links=EWDS_LINKS, limitations=[x for x in (stale_note, upd_note) if x])
    dest = get_settings().data_dir / "downloads" / f"ewds_{hashlib.sha1(json.dumps(req, sort_keys=True).encode()).hexdigest()[:12]}.nc"
    cache_state = "hit" if dest.exists() else "miss"
    if not dest.exists():
        run = ewds_run(req, key, dest)
        if run["status"] != "ok":
            code = {"terms_not_accepted": ("needs_credentials", "EWDS_LICENCE_NOT_ACCEPTED"), "auth_failed": ("needs_credentials", "EWDS_TOKEN_REJECTED"), "timeout": ("upstream_error", "EWDS_JOB_TIMEOUT"),
                    "job_failed": ("upstream_error", "EWDS_JOB_FAILED"), "submit_failed": ("upstream_error", "EWDS_SUBMIT_FAILED")}.get(run["status"], ("upstream_error", "EWDS_DOWNLOAD_FAILED"))
            return envelope("Copernicus EWDS", prod, "fire_danger_outlook", code[0], code[1], sanitize(run.get("reason") or run["status"], key), data={**info, "job": run.get("job")}, setup=EWDS_SETUP if code[0] == "needs_credentials" else None, source_links=EWDS_LINKS)
    try:
        cur = read_netcdf(dest)
        ref, ref_state = None, "none"
        try:
            rreq = _ref_request(variable, start_day, valid_days, [n, w, so, e], schema)
            rdest = get_settings().data_dir / "downloads" / f"ewds_ref_{hashlib.sha1(json.dumps(rreq, sort_keys=True).encode()).hexdigest()[:12]}.nc"
            if rdest.exists():
                ref = read_reference_netcdf(rdest); ref_state = "cached"
            else:
                _ref_fetch_bg(rreq, key, rdest); ref_state = "preparing"
        except Exception as ex:
            ref_state = f"error:{type(ex).__name__}"
        ana = analyze_ensemble(cur, ref, (start, end))
    except Exception as ex:
        return envelope("Copernicus EWDS", prod, "fire_danger_outlook", "upstream_error", "EWDS_FILE_INVALID", f"The downloaded file could not be validated: {type(ex).__name__}: {str(ex)[:160]}", data=info, source_links=EWDS_LINKS)
    lim = [SKILL_STATEMENT[lang], "Ensemble forecast of a fire-weather DANGER index (GEFF driven by SEAS5); it is not a probability of fire occurrence and no fire-record verification is implied.",
           "Daily values at 12:00 local time from a forecast issued once a month; skill at 2-3 months lead is limited." if lang == "en" else "قيم يومية عند 12:00 بالتوقيت المحلي من توقع يصدر مرة شهريًا؛ والمهارة عند 2–3 أشهر محدودة."]
    if stale_note:
        lim.append(stale_note)
    if upd_note:
        lim.append(upd_note)
    if ana.get("reference") is None:
        why = {"preparing": " The reference is being downloaded in the background; categories will appear on a later request."}.get(ref_state, "")
        lim.append(("No reference (re-forecast) distribution was used: there are no above/near/below-normal categories, only the raw ensemble index." + why) if lang == "en" else "لم تُستخدم دالة مرجعية (إعادة التنبؤ): لا فئات أعلى/قريب/أقل من المعتاد، بل مؤشر المجموعة الخام فقط." + (" المرجع قيد التنزيل في الخلفية وستظهر الفئات في طلب لاحق." if why else ""))
    else:
        lim.append(f"Categories are terciles of the 1981-2016 re-forecast distribution ({ana['reference']['n_values']} member-year values, same start month and lead days); they are relative frequencies, not probabilities of fire." if lang == "en" else f"الفئات أثلاث توزيع إعادة التنبؤ 1981–2016 ({ana['reference']['n_values']} قيمة)؛ هي ترددات نسبية وليست احتمال حريق.")
    return strict(envelope("Copernicus EWDS", prod, "fire_danger_outlook", "ok", variables=[variable], units={"index": cur["units"]}, request=req,
                           actual={"issue_date": av["latest_start"], "age_days": age, "valid_window": [str(start), str(end)], "ensemble_size": ana["n_members_expected"], "members_used": ana["n_members_used"], "spatial_unit": "regional mean of the dataset grid"},
                           temporal_resolution="daily at 12:00 local time (forecast issued monthly)", live=cache_state == "miss", cache=cache_state, duration_ms=int((time.monotonic() - t0) * 1000), source_links=EWDS_LINKS,
                           attribution="Contains modified Copernicus Emergency Management Service information (ECMWF / JRC)", license="CC-BY-4.0", limitations=lim, quality={"ensemble_size": ana["n_members_expected"], "members_missing": ana["members_missing"]},
                           data={**info, "analysis": ana},
                           artifacts=[{"type": "ensemble_chart", "title": f"Ensemble forecast of {variable} (daily, regional mean): median and spread across {ana['n_members_used']} members", "unit": str(cur["units"]), "dates": ana["dates"],
                                       "daily": ana["daily"], "thresholds": ({"tercile_33": ana["reference"]["tercile_33"], "tercile_67": ana["reference"]["tercile_67"]} if ana.get("reference") else None),
                                       "note": "Danger index (not a probability). Spread is not a calibrated uncertainty estimate.", "inline": True}]))


def ewds_auth_check() -> dict:
    """Authentication ONLY (no data request): lists the caller's jobs with the PRIVATE-TOKEN header. A configured token alone is never reported as success."""
    key = ewds_key()
    if not key:
        return envelope("Copernicus EWDS", "EWDS authentication", "fire_danger_outlook", "needs_credentials", "EWDS_API_KEY_MISSING", "EWDS_API_KEY is not set.", setup=EWDS_SETUP, source_links=EWDS_LINKS)
    import httpx
    try:
        r = httpx.get(f"{EWDS_BASE}/jobs", headers={"PRIVATE-TOKEN": key, "Accept": "application/json"}, params={"limit": 1}, timeout=40)
    except Exception as ex:
        return envelope("Copernicus EWDS", "EWDS authentication", "fire_danger_outlook", "upstream_error", "EWDS_UNREACHABLE", type(ex).__name__, source_links=EWDS_LINKS)
    if r.status_code in (401, 403):
        return envelope("Copernicus EWDS", "EWDS authentication", "fire_danger_outlook", "needs_credentials", "EWDS_TOKEN_REJECTED", f"EWDS rejected the token (HTTP {r.status_code}).", setup=EWDS_SETUP, source_links=EWDS_LINKS)
    return envelope("Copernicus EWDS", "EWDS authentication", "fire_danger_outlook", "ok" if r.status_code == 200 else "upstream_error", None if r.status_code == 200 else f"HTTP_{r.status_code}",
                    message="Token accepted (authentication only; the dataset licence and a data request are separate steps).", live=True, source_links=EWDS_LINKS)


# ---- orchestrator ---------------------------------------------------------------------------------------------------------------------------------
def forecast_fire_danger(lat: float | None = None, lon: float | None = None, bbox: list[float] | None = None, region_text: str | None = None, start_date: str | None = None,
                         end_date: str | None = None, window: str | None = "next_calendar_month", source: str = "auto", place: str | None = None, today: date | None = None,
                         lang: str = "en", with_observations: bool = True) -> dict:
    """Validated one-month wildfire DANGER outlook. source: auto | nifc | ewds. auto = NIFC (official US regional) where it covers the location, plus EWDS where access exists;
    outside the US the global EWDS product is required - if it is blocked the outlook is reported UNAVAILABLE (no silent substitution by a short-range forecast)."""
    today = today or date.today()
    name = "Wildfire danger outlook"
    cap = "fire_danger_outlook"
    if source not in ("auto", "nifc", "ewds"):
        return envelope("EarthTrend", name, cap, "invalid_request", "INVALID_SOURCE", "source must be auto, nifc or ewds")
    if lat is None and not bbox and not region_text:
        return envelope("EarthTrend", name, cap, "invalid_request", "LOCATION_REQUIRED", "A place, coordinates or a box is required.")
    try:
        start, end, kind = resolve_window(window, start_date, end_date, today)
    except ValueError:
        return envelope("EarthTrend", name, cap, "invalid_request", "INVALID_DATE", "Dates must be YYYY-MM-DD.")
    if end < today:
        return envelope("EarthTrend", name, cap, "unsupported_request", "PAST_PERIOD", "That period has already ended: a past forecast is not shown as a current outlook.")
    if (end - today).days > HORIZON_DAYS_EWDS:
        return envelope("EarthTrend", name, cap, "unsupported_request", "BEYOND_HORIZON", f"The longest outlook available is about {HORIZON_DAYS_EWDS} days ahead.")
    if lat is None and bbox:
        lat, lon = (bbox[1] + bbox[3]) / 2, (bbox[0] + bbox[2]) / 2
    sub = {}
    if source in ("auto", "nifc"):
        sub["nifc"] = nifc_outlook(lat, lon, bbox, region_text, start, end, today, lang)
    if source == "ewds" or (source == "auto" and (sub.get("nifc", {}).get("status") != "ok")) or (source == "auto" and ewds_key() and lat is not None):
        if lat is not None:
            sub["ewds"] = ewds_outlook(lat, lon, bbox, start, end, today, lang=lang)
    primary_key = next((k for k in ("nifc", "ewds") if sub.get(k, {}).get("status") == "ok"), None)
    if bbox is None and primary_key == "nifc" and (sub["nifc"].get("actual") or {}).get("mode") == "named_region":
        from shapely.geometry import shape as _shape                                  # a named region: the observed layer must cover the REGION, not a geocoded point
        bs = [_shape(p_["geometry"]).bounds for a_ in sub["nifc"]["artifacts"] if a_["type"] == "map_polygons" for p_ in a_["polygons"]]
        if bs:
            bbox = [round(min(b[0] for b in bs), 3), round(min(b[1] for b in bs), 3), round(max(b[2] for b in bs), 3), round(max(b[3] for b in bs), 3)]
            lat, lon = (bbox[1] + bbox[3]) / 2, (bbox[0] + bbox[2]) / 2
    obs = None
    if with_observations and lat is not None:
        try:
            from app.providers import firms
            box = bbox or [lon - 0.5, lat - 0.5, lon + 0.5, lat + 0.5]
            f = firms.detections(box, None, 5)
            if f.get("status") in ("ok", "no_data"):
                obs = {"role": "observed", "label": "Observed active-fire detections (FIRMS), last days - NOT a forecast", "source": f.get("product"), "n_detections": (f.get("actual") or {}).get("n_detections", 0),
                       "period": (f.get("actual") or {}).get("period"), "points": [{"lat": r["latitude"], "lon": r["longitude"], "label": f"OBSERVED {r['acq_date']} {r['acq_time']} UTC conf {r['confidence']} FRP {r['frp_mw']} MW", "frp": r["frp_mw"]}
                                                                              for r in ((f.get("data") or {}).get("detections") or [])[:300]],
                       "note": "Zero detections does not mean zero future fire danger; detections are not a forecast." if not (f.get("actual") or {}).get("n_detections") else "Detections are observations, not a forecast."}
        except Exception:
            obs = None
    window_info = {"kind": kind, "start": str(start), "end": str(end), "lead_days_to_start": max(0, (start - today).days), "issue_date": today.isoformat(),
                   "note": "Next calendar month" if kind == "next_calendar_month" else "Next 30 days: the sources are monthly products, so the covering calendar months are shown with the days of each month inside the window; this is not an exact rolling 30-day product." if kind == "next_30_days" else "Custom period"}
    if primary_key is None:
        # nothing usable: report the most informative failure honestly (blocked beats 'unsupported')
        order = ["needs_credentials", "no_data", "upstream_error", "unsupported_region", "invalid_request"]
        best = sorted(sub.values(), key=lambda r: order.index(r["status"]) if r["status"] in order else 9)[0]
        msg = best["message"]
        if best["status"] == "unsupported_region" and "ewds" not in sub:
            msg += " Use source='auto' to try the global Copernicus product."
        res = {**best, "data": {**(best.get("data") or {}), "window": window_info, "sources": {k: {"status": v["status"], "reason_code": v["reason_code"], "message": v["message"]} for k, v in sub.items()}, "observed": obs}}
        res["message"] = msg
        return strict(res)
    p = sub[primary_key]
    others = {k: {"status": v["status"], "reason_code": v["reason_code"], "message": v["message"]} for k, v in sub.items() if k != primary_key}
    lim = list(p["limitations"])
    if primary_key == "nifc" and "ewds" in sub and sub["ewds"]["status"] != "ok":
        lim.append("The global Copernicus seasonal source was not used: " + sub["ewds"]["message"])
    arts = list(p["artifacts"])
    if obs and obs["points"]:
        arts.append({"type": "map_points", "title": "OBSERVED active-fire detections (FIRMS) - not a forecast", "layer_role": "observed", "points": obs["points"], "bbox": bbox})
    out = {**p, "limitations": lim, "artifacts": arts, "data": {**p["data"], "window": window_info, "primary_source": primary_key, "sources": others, "observed": obs, "region": {"place": place, "region_text": region_text, "lat": lat, "lon": lon, "bbox": bbox}}}
    return strict(out)
