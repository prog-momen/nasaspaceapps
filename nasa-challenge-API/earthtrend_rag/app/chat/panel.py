"""Builds what the UI shows beside the chat for ONE turn: result panel (title, metrics, artifacts, provenance), map description and the
outcome category. Everything is derived from the tool result; nothing is estimated here. Tones (hot/cold/warn/neutral/good/bad) are only
set from a stated rule that is also returned in `basis`, so the UI never colours a value without a documented reason."""
from __future__ import annotations

import math

T = lambda lang, ar, en: ar if lang == "ar" else en

OUTCOMES = ["answered", "zero_detections", "no_data", "unsupported", "needs_credentials", "provider_outage", "model_quota", "ambiguous", "insufficient_evidence", "pending", "error"]
QUOTA_KINDS = {"quota", "billing", "budget", "overloaded", "timeout", "network", "service_error", "empty", "unknown", "not_configured", "auth", "model_not_found", "model_not_allowed", "invalid_request", "tool_protocol"}   # any model-side failure


def classify_outcome(status: str, reason_code: str | None, fallback_reason: str | None, tool_ran: bool) -> str:
    """One of OUTCOMES. Claude failures only become `model_quota` when no tool result exists (otherwise the data answer is still valid)."""
    if reason_code == "ZERO_DETECTIONS":
        return "zero_detections"
    if reason_code == "TASK_PENDING":
        return "pending"
    if status == "ok":
        return "answered"
    if status in ("clarification", "conflict", "busy"):
        return "ambiguous"
    if status == "unsupported":
        return "unsupported"
    if status == "insufficient_knowledge":
        return "insufficient_evidence"
    if reason_code == "ZERO_DETECTIONS":
        return "zero_detections"
    if status == "needs_credentials":
        return "needs_credentials"
    if status in ("unsupported_request", "unsupported_region"):
        return "unsupported"
    if status in ("upstream_error", "blocked_provider"):
        return "provider_outage"
    if status == "invalid_request":
        return "ambiguous"
    if status == "no_data":
        return "no_data"
    if status == "model_unavailable" or (not tool_ran and fallback_reason in QUOTA_KINDS):
        return "model_quota"
    return "error"


# ---- map ---------------------------------------------------------------------------------------------------------------------
def power_cell(lat: float, lon: float) -> list[float]:
    """Approximate MERRA-2 cell (0.5 deg lat x 0.625 deg lon) containing the point, as [west, south, east, north]."""
    la = round((lat + 90) / 0.5) * 0.5 - 90
    lo = round((lon + 180) / 0.625) * 0.625 - 180
    return [round(lo - 0.3125, 4), round(la - 0.25, 4), round(lo + 0.3125, 4), round(la + 0.25, 4)]


def build_map(tool: str | None, outcome: dict, decision: dict | None, ok: bool, lang: str) -> dict | None:
    loc = outcome.get("location")
    if not loc:
        return None
    src = loc.get("source") or ""
    approx = bool(loc.get("bbox") is None and ("central point" in loc["name"] or "representative" in loc["name"] or "map control" in src and False))
    m = {"requested": {"region": bool(loc.get("region")), "name": loc["name"], "lat": round(float(loc["latitude"]), 5), "lon": round(float(loc["longitude"]), 5), "source": src, "bbox": loc.get("bbox")},
         "scope": "area" if loc.get("bbox") else "point", "footprint": None, "approximate": approx, "notes": [], "ok": ok}
    if approx:
        m["notes"].append(T(lang, "نقطة تمثيلية لمنطقة كبيرة وليست حدودًا إدارية.", "Representative point of a large region, not its administrative boundary."))
    res = outcome.get("result") or {}
    if tool in ("analyze_trend", "forecast_monthly"):
        cell = power_cell(float(loc["latitude"]), float(loc["longitude"]))
        m["footprint"] = {"type": "grid_cell", "bbox": cell, "label": T(lang, "الخلية الشبكية التقريبية لبيانات NASA POWER (≈0.5°×0.625°)", "Approximate NASA POWER (MERRA-2) grid cell (≈0.5°×0.625°)")}
        m["notes"].append(T(lang, "التحليل لنقطة واحدة (خلية شبكية)، وليس متوسطًا للمدينة أو المنطقة.", "The analysis is for one grid cell at this point, not an average over the city or region."))
    elif tool == "get_weather":
        g = (res.get("actual") or {}).get("grid")
        if g:
            m["footprint"] = {"type": "model_point", "point": [g["latitude"], g["longitude"]], "label": T(lang, "نقطة الشبكة الأقرب في نموذج Open-Meteo", "Nearest Open-Meteo model grid point")}
        m["notes"].append(T(lang, "قيم نموذج لأقرب خلية شبكية، وليست قراءات محطة.", "Model values for the nearest grid cell, not station readings."))
    elif tool == "get_lst":
        m["footprint"] = {"type": "query_bbox", "bbox": [round(float(loc["longitude"]) - 0.005, 4), round(float(loc["latitude"]) - 0.005, 4), round(float(loc["longitude"]) + 0.005, 4), round(float(loc["latitude"]) + 0.005, 4)],
                          "label": T(lang, "بكسل MODIS بدقة ≈1 كم يحتوي النقطة (تقريبي)", "≈1 km MODIS pixel containing the point (approximate)")}
        m["notes"].append(T(lang, "حرارة سطح الأرض (جلد السطح) لبكسل واحد، وليست حرارة الهواء.", "Surface (skin) temperature of one pixel, not air temperature."))
    elif tool == "forecast_fire_danger":
        mode = (res.get("actual") or {}).get("mode")
        m["scope"] = "area" if mode in ("bbox", "named_region") or loc.get("bbox") else "point"
        if loc.get("bbox"):
            m["footprint"] = {"type": "query_bbox", "bbox": loc["bbox"], "label": T(lang, "حدود المنطقة (مضلعات NIFC الرسمية)" if loc.get("region") else "المربع المطلوب", "Region (official NIFC polygons)" if loc.get("region") else "Requested box")}
        if "EWDS" in str(res.get("provider")):
            m["notes"].append(T(lang, "توقع EWDS: متوسط خلايا الشبكة (≈0.25°) داخل الصندوق المعروض؛ الخلايا البحرية بلا قيم تُستبعد.", "EWDS outlook: area-weighted mean of the dataset grid cells in the box; cells without values (e.g. sea) are excluded."))
        else:
          m["notes"].append(T(lang, "توقع نقطة: فئة منطقة الخدمة التنبؤية التي تحوي النقطة، وليس تحليلًا لمنطقة كاملة." if mode == "point" else "توقع منطقة: مناطق الخدمة التنبؤية المتقاطعة؛ النسب مساحات مستوية تقريبية.",
                              "Point outlook: the category of the Predictive Service Area that contains the point, not a region-wide analysis." if mode == "point" else "Region outlook: the intersecting Predictive Service Areas; shares are approximate planar area fractions."))
    elif tool in ("get_fire_detections", "search_satellite_scenes", "get_ndvi"):
        box = (outcome.get("used_args") or {}).get("bbox")
        if box:
            m["footprint"] = {"type": "query_bbox", "bbox": box, "label": T(lang, "مربع الاستعلام", "Query box")}
        m["scope"] = "area"
        if not loc.get("bbox"):
            half = {"get_fire_detections": 0.5, "search_satellite_scenes": 0.15, "get_ndvi": 0.05}.get(tool)
            m["notes"].append(T(lang, f"المربع مُشتق من النقطة المطلوبة (±{half}°).", f"The box is derived from the requested point (±{half}°)."))
    return m


# ---- panel -------------------------------------------------------------------------------------------------------------------
def _metric(label, value, unit=None, tone="neutral", basis=None, hint=None):
    return {"label": label, "value": value, "unit": unit, "tone": tone, "basis": basis, "hint": hint}


def _fmt(v, nd=2):
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return None
    return round(v, nd) if isinstance(v, float) else v


def _links(res: dict) -> list[dict]:
    out = []
    for u in (res.get("source_links") or [])[:6]:
        out.append({"label": u.split("//")[-1].split("/")[0], "url": u})
    return out


def build_panel(tool: str, outcome: dict, lang: str, decision: dict | None = None) -> dict:
    res, s = outcome["result"], outcome.get("summary") or {}
    loc = outcome.get("location") or {}
    place = loc.get("name") or ""
    st = res.get("status")
    src = {"provider": res.get("provider"), "product": res.get("product"), "capability": res.get("capability"), "live": res.get("live"), "cache": res.get("cache"),
           "retrieved_at": res.get("retrieved_at"), "attribution": res.get("attribution"), "license": res.get("license"), "links": _links(res)}
    p = {"kind": tool, "status": st, "title": place, "subtitle": "", "metrics": [], "artifacts": outcome.get("artifacts") or [], "source": src,
         "limitations": (res.get("limitations") or [])[:6], "details": s}
    if tool == "analyze_trend":
        src.update(provider="NASA POWER", product=f"monthly {res.get('variable', {}).get('id', '')}".strip(), retrieved_at=(res.get("source") or {}).get("retrieved_at"),
                   live=not (res.get("source") or {}).get("cache_hit"), cache="hit" if (res.get("source") or {}).get("cache_hit") else "miss",
                   links=[{"label": "POWER API", "url": "https://power.larc.nasa.gov/docs/services/api/temporal/monthly/"}])
        if st == "ok":
            v = res["variable"]
            t = res["test"]; sen = t["sen_slope"]
            vname = (v.get("name_ar") if lang == "ar" else None) or v["name"]
            pa = res["period_actual"]
            p["title"] = f"{vname} — {place}"
            p["subtitle"] = f"{pa['first'][:4]}–{pa['last'][:4]} · NASA POWER · {res['units']}"
            sig, direc = t["significant"], t["direction"]
            tone, basis = "warn", T(lang, f"غير دالّ عند α={t['alpha']}", f"not significant at α={t['alpha']}")
            if sig:
                basis = T(lang, f"دالّ عند α={t['alpha']}؛ الاتجاه من إشارة ميل Sen", f"significant at α={t['alpha']}; direction from the sign of Sen's slope")
                if v.get("id") == "air_temperature":
                    tone = "hot" if direc == "increasing" else "cold" if direc == "decreasing" else "neutral"
                else:
                    tone = "neutral"
            p["metrics"] = [
                _metric(T(lang, "ميل Sen", "Sen's slope"), _fmt(sen["value"], 4), sen["unit"], tone, basis),
                _metric("p", _fmt(t["p_value"], 4), None, "good" if sig and False else ("neutral" if sig else "warn"), basis),
                _metric(T(lang, "الدلالة", "Significance"), T(lang, "دالّ" if sig else "غير دالّ", "significant" if sig else "not significant"), f"α={t['alpha']}", "neutral" if sig else "warn", basis),
                _metric(T(lang, "قراءات مستخدمة", "Readings used"), t["n_used"], t["n_unit"]),
                _metric("Kendall τ", _fmt(t["kendall_tau"], 3)),
                _metric(T(lang, "أشهر مفقودة", "Missing months"), res["data_quality"]["missing_months"], None, "warn" if res["data_quality"]["missing_months"] else "neutral",
                        T(lang, "هناك أشهر مفقودة", "some months are missing") if res["data_quality"]["missing_months"] else None)]
    elif tool == "get_weather" and st == "ok":
        a = res["actual"]; rows = s["daily"]
        fc = res["capability"] == "weather_forecast"
        p["title"] = f"{T(lang, 'توقع الطقس' if fc else 'طقس تاريخي (إعادة تحليل)', 'Weather forecast' if fc else 'Historical weather (reanalysis)')} — {place}"
        p["subtitle"] = f"{rows[0]['date']} → {rows[-1]['date']} · Open-Meteo · {a['timezone']}"
        tmax = [r["tmax_c"] for r in rows if r["tmax_c"] is not None]; tmin = [r["tmin_c"] for r in rows if r["tmin_c"] is not None]
        pr = [r["precip_mm"] for r in rows if r["precip_mm"] is not None]; wd = [r["wind_max_kmh"] for r in rows if r["wind_max_kmh"] is not None]
        if tmax:
            hot = max(tmax) >= 40
            p["metrics"].append(_metric(T(lang, "أعلى عظمى", "Highest max"), max(tmax), "°C", "hot" if hot else "neutral", T(lang, "≥ 40 °C حدّ حرارة شديدة (معرَّف هنا)", "≥ 40 °C counted as extreme heat (threshold defined here)") if hot else None))
        if tmin:
            frz = min(tmin) <= 0
            p["metrics"].append(_metric(T(lang, "أدنى صغرى", "Lowest min"), min(tmin), "°C", "cold" if frz else "neutral", T(lang, "≤ 0 °C تجمّد", "≤ 0 °C freezing") if frz else None))
        if pr:
            p["metrics"].append(_metric(T(lang, "مجموع الهطول", "Total precipitation"), round(sum(pr), 1), "mm"))
        if wd:
            p["metrics"].append(_metric(T(lang, "أقصى رياح", "Max wind"), max(wd), "km/h"))
    elif tool == "get_fire_detections":
        n = s.get("n_detections", 0)
        p["title"] = f"{T(lang, 'كشوف الحرائق', 'Fire detections')} — {place}"
        per = s.get("period") or {}
        req = res.get("request") or {}
        p["subtitle"] = f"{res.get('product') or ''} · {per.get('first') or req.get('start') or T(lang, 'أحدث الأيام', 'latest days')}" + (f" → {per.get('last')}" if per.get("last") and per.get("last") != per.get("first") else "")
        if st in ("ok", "no_data"):
            if res.get("reason_code") == "SENSOR_DATA_NOT_AVAILABLE":
                p["metrics"].append(_metric(T(lang, "الحالة", "Status"), T(lang, "لا بيانات للحساس", "Sensor has no data"), None, "warn", res.get("message")))
            else:
                p["metrics"].append(_metric(T(lang, "عدد الكشوف", "Detections"), n, None, "neutral"))
                if n:
                    p["metrics"].append(_metric(T(lang, "أعلى FRP", "Max FRP"), s.get("frp_max_mw"), "MW"))
                    for k, v in (s.get("by_confidence") or {}).items():
                        p["metrics"].append(_metric(T(lang, f"ثقة {k}", f"confidence {k}"), v, None, "neutral", T(lang, "فئة من المصدر (VIIRS: l/n/h)", "category from the source (VIIRS: l/n/h)")))
    elif tool == "list_fire_danger":
        p["title"] = f"{T(lang, 'خطر الحرائق', 'Fire danger')}{' — ' + place if place else ''}"
        p["subtitle"] = "GWIS · USGS WFPI"
        if s.get("usgs_status") == "ok":
            p["metrics"].append(_metric(T(lang, "فئة USGS (يوم 1)", "USGS WFPI class (day 1)"), s.get("usgs_palette_index"), None, "neutral", T(lang, "فئة لوحة الخريطة وليست قيمة معايَرة", "map palette class, not a calibrated value")))
        p["metrics"].append(_metric(T(lang, "طبقات GWIS", "GWIS layers"), s.get("n_gwis_layers"), None))
    elif tool == "search_satellite_scenes":
        p["title"] = f"{T(lang, 'مشاهد Sentinel', 'Sentinel scenes')} — {place}"
        p["subtitle"] = f"{s.get('collection') or ''}"
        if s.get("n_scenes") is not None:
            p["metrics"].append(_metric(T(lang, "المشاهد", "Scenes"), s["n_scenes"]))
            if s.get("cloud_min") is not None:
                p["metrics"].append(_metric(T(lang, "الغيوم", "Cloud"), f"{s['cloud_min']}–{s['cloud_max']}", "%"))
    elif tool == "get_lst":
        p["title"] = f"{T(lang, 'حرارة سطح الأرض LST (ليست حرارة الهواء)', 'Land surface temperature LST (not air temperature)')} — {place}"
        per = s.get("period") or {}
        p["subtitle"] = f"{per.get('first') or ''} → {per.get('last') or ''} · MODIS MOD11A2 · {T(lang, 'مركّبات 8 أيام، مفلترة الجودة', '8-day composites, quality-filtered')}"
        src.update(provider="NASA AppEEARS (MODIS MOD11A2.061)", product="LST_Day_1km")
        if st == "ok":
            p["metrics"] = [_metric(T(lang, "المتوسط", "Mean"), s.get("mean_c"), "°C"), _metric(T(lang, "الأدنى", "Min"), s.get("min_c"), "°C"), _metric(T(lang, "الأعلى", "Max"), s.get("max_c"), "°C"),
                            _metric(T(lang, "مركّبات مستخدمة", "Composites used"), f"{s.get('n_valid')} / {s.get('n_total')}"),
                            _metric(T(lang, "مستبعدة بالجودة", "Removed by quality"), s.get("n_filtered"), None, "warn" if s.get("n_filtered") else "neutral",
                                    T(lang, "سحب أو جودة ضعيفة أو قيم غير صالحة", "clouds, poor quality or invalid values") if s.get("n_filtered") else None)]
    elif tool == "forecast_monthly":
        d = res.get("data") or {}
        if st == "ok":
            sm = d["summary"]; ee = d["error_estimate"]; cut = sm["cutoff"]
            ov = sm["overall_validation"]
            p["title"] = f"{T(lang, 'توقع إحصائي شهري', 'Monthly statistical forecast')} — {sm['variable'].split(' (')[0]} — {place}"
            p["subtitle"] = f"{T(lang, 'آخر شهر بيانات', 'data cutoff')} {cut['data_cutoff_month'][:7]} · {T(lang, 'التوقع', 'forecast')} {cut['first_forecast_month'][:7]} → {cut['last_forecast_month'][:7]} · {sm['selected_model'] if ov != 'baseline_only' else sm['baseline']}"
            tone = {"validated_model": "good", "partially_validated": "warn", "baseline_only": "warn"}[ov]
            lab = {"validated_model": T(lang, "نموذج مُتحقَّق", "validated model"), "partially_validated": T(lang, "تحقق جزئي", "partially validated"), "baseline_only": T(lang, "خط أساس فقط (لا مهارة إضافية مُثبتة)", "baseline only (no added skill shown)")}[ov]
            p["metrics"] = [_metric(T(lang, "حالة التحقق", "Validation"), lab, None, tone, T(lang, "من اختبار رجعي زمني على فترة احتجاز نهائية", "from a chronological backtest on a final holdout"))]
            for g, v in sm["mae_by_group"].items():
                p["metrics"].append(_metric(f"MAE {g} {T(lang, 'شهر', 'mo')}", v, ee["unit"], "neutral", None))
            p["metrics"].append(_metric(T(lang, "أصول التوقع", "Forecast origins"), f"{sm['n_holdout_origins']} {T(lang, 'احتجاز', 'holdout')}", None, "warn" if sm["n_holdout_origins"] < 8 else "neutral",
                                        T(lang, "عدد قليل من نقاط البدء: التقدير نفسه غير يقيني", "few forecast origins: the estimate itself is uncertain") if sm["n_holdout_origins"] < 8 else None))
            p["references"] = d.get("references", [])
            p["validation"] = d.get("validation")
            p["cutoff"] = cut
    elif tool == "forecast_fire_danger":
        d = res.get("data") or {}
        win = d.get("window") or {}
        p["title"] = f"{T(lang, 'توقع خطر الحرائق', 'Wildfire danger outlook')} — {place}"
        if st == "ok":
            a = res["actual"]
            p["subtitle"] = f"{T(lang, 'أُصدر', 'issued')} {a.get('issue_label') or a.get('issue_date')} · {T(lang, 'صالح', 'valid')} {win.get('start')} → {win.get('end')} · {res.get('provider')}"
            CAT = {"Above": ("hot", T(lang, "أعلى من المعتاد", "Above normal")), "Normal": ("neutral", T(lang, "قريبة من المعتاد", "Normal")), "Below": ("good", T(lang, "أقل من المعتاد", "Below normal"))}
            for mth in (d.get("months") or []):
                tone, txt = CAT[mth["headline"]]
                shares = " · ".join(f"{CAT[k][1]} {round(v['share'] * 100)}%" for k, v in mth["categories"].items()) if mth["mixed"] else None
                p["metrics"].append(_metric(f"{T(lang, 'توقع شهر', 'Outlook')} {mth['label']}", txt + (f" ({shares})" if shares else ""), None, tone,
                                            T(lang, "فئة رسمية من المصدر نسبةً إلى المعتاد؛ ليست احتمالًا", "official source category relative to normal; not a probability")))
            an = d.get("analysis")
            if an and an.get("window_mean"):
                wm = an["window_mean"]
                p["metrics"].append(_metric(T(lang, "مؤشر الطقس الحريقي FWI (وسيط المجموعة)", "Fire Weather Index (ensemble median)"), round(wm["ensemble_median"], 1), None, "neutral",
                                            T(lang, f"مدى الأعضاء {wm['ensemble_min']:.1f}–{wm['ensemble_max']:.1f} · {an['n_members_used']} عضوًا · مؤشر خطر وليس احتمالًا", f"member range {wm['ensemble_min']:.1f}–{wm['ensemble_max']:.1f} · {an['n_members_used']} members · danger index, not a probability")))
                sh = an.get("category_shares")
                if sh:
                    p["metrics"].append(_metric(T(lang, "أعضاء المجموعة نسبةً إلى 1981–2016", "Members vs 1981-2016 reference"), f"{sh['below_normal']*100:.0f}% / {sh['near_normal']*100:.0f}% / {sh['above_normal']*100:.0f}%", None, "neutral",
                                                T(lang, "أقل / قريب / أعلى من المعتاد · ترددات نسبية وليست احتمال حريق", "below / near / above normal · relative frequencies, not a fire probability")))
                p["metrics"].append(_metric(T(lang, "إصدار التوقع", "Forecast issue"), f"{d.get('issue_date')} ({d.get('age_days')} {T(lang, 'يومًا', 'days')})", None, "neutral",
                                            T(lang, "التحديثات تتوقف بعد 16 نوفمبر 2026 (إشعار رسمي)", "updates cease after 16 Nov 2026 (official notice)")))
            obs = d.get("observed")
            if obs:
                p["metrics"].append(_metric(T(lang, "كشوف مرصودة (FIRMS، آخر 5 أيام)", "Observed detections (FIRMS, last 5 days)"), obs.get("n_detections"), None, "neutral", T(lang, "رصد وليس توقعًا", "observation, not a forecast")))
            p["validation"] = {"skill_verified": False, "statement": {"en": "This is an official model outlook; local forecast skill has not been verified by this application.", "ar": "هذا توقع رسمي مبني على نموذج؛ ولم يتحقق هذا التطبيق من مهارة التوقع محليًا."}[lang]}
            p["window"] = win
            p["sources_other"] = d.get("sources")
    elif tool == "get_ndvi":
        p["title"] = f"{T(lang, 'مؤشر NDVI (Sentinel-2)', 'NDVI (Sentinel-2)')} — {place}"
        p["subtitle"] = f"{s.get('first') or ''} → {s.get('last') or ''} · Copernicus Data Space · {T(lang, 'مُقنَّع للسحب والقيم غير الصالحة', 'cloud- and invalid-value-masked')}"
        src.update(provider="Copernicus Data Space (Sentinel Hub Statistical API)", product="Sentinel-2 L2A NDVI")
        if st in ("ok", "no_data"):
            p["metrics"] = [_metric(T(lang, "متوسط NDVI", "Mean NDVI"), s.get("mean_ndvi")), _metric(T(lang, "فترات صالحة", "Usable intervals"), f"{s.get('n_usable')} / {s.get('n_intervals')}")]
    elif tool == "search_earth_datasets":
        p["title"] = T(lang, "مجموعات البيانات", "Datasets")
        p["metrics"].append(_metric(T(lang, "نتائج", "Results"), s.get("n")))
    if st not in ("ok", "no_data"):
        p["metrics"] = []
    return p


def docs_panel(cites: list[dict], lang: str) -> dict:
    return {"kind": "docs", "status": "ok", "title": T(lang, "المصادر الموثّقة", "Documentation sources"), "subtitle": "", "metrics": [], "artifacts": [],
            "source": {"provider": "Indexed official documentation"}, "limitations": [], "details": {}, "citations": cites}
