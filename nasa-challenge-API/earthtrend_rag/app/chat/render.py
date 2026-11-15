"""Deterministic answer templates (Arabic / English), built ONLY from tool results and kept short: conclusion + essential numbers + one citation.
Full statistics, provenance and limitations live in the side panel. Used when Claude is unavailable, not requested, or its explanation failed
validation; the UI labels these 'template'. Output is Markdown (bold, short lists) rendered by the UI's sanitising renderer."""
from __future__ import annotations

T = lambda lang, ar, en: ar if lang == "ar" else en

INSUFFICIENT = {"ar": "الموارد غير كافية للإجابة بدقة.", "en": "Insufficient resources to answer this accurately."}
EMOJI = {"air_temperature": "🌡️", "land_surface_temperature": "🌡️", "precipitation": "🌧️", "relative_humidity": "💧", "wind_speed": "💨"}


def insufficient(lang: str, reason: str | None = None) -> str:
    return INSUFFICIENT[lang] + (f" {reason}" if reason else "")


def _missing(tool: str, lang: str, s: dict) -> str | None:
    if s.get("needs") == "location":
        if s.get("ambiguous"):
            opts = "\n".join(f"- {o}" for o in s["ambiguous"])
            return T(lang, f"الاسم يطابق أكثر من مكان، أيها تقصد؟\n{opts}\nاكتب الاسم الكامل أو الإحداثيات.", f"That name matches several places. Which one do you mean?\n{opts}\nReply with the full name or coordinates.")
        return T(lang, "في أي مكان؟ اكتب اسم مدينة أو إحداثيات، أو اختر نقطة على الخريطة.", "Which place? Name a city, give coordinates, or pick a point on the map.")
    if s.get("needs") == "period":
        return T(lang, "أي فترة تقصد؟ مثال: «بين 2005 و2025».", "Which period do you mean? For example 'between 2005 and 2025'.")
    return None


_STATUS_HEAD = {
    "needs_credentials": ("🔑", "هذه الميزة تحتاج إعدادًا", "This feature needs setup"),
    "unsupported_region": ("🗺️", "خارج التغطية", "Outside coverage"),
    "unsupported_request": ("🚫", "طلب غير مدعوم", "Unsupported request"),
    "invalid_request": ("❓", "الطلب غير مكتمل", "The request is incomplete"),
    "upstream_error": ("⚠️", "المزود غير متاح مؤقتًا", "The data provider is temporarily unavailable"),
    "blocked_provider": ("⚠️", "المزود غير متاح", "Provider unavailable"),
    "no_data": ("🔎", "لا توجد بيانات مطابقة", "No matching data"),
}


def _clean(msg: str | None) -> str:
    m = (msg or "").strip()
    return "" if m.lower() in ("none", "null") else m


def _not_ok(r: dict, lang: str, tool: str) -> str | None:
    st = r.get("status")
    if st == "ok":
        return None
    emo, ar, en = _STATUS_HEAD.get(st, ("⚠️", "تعذّر تنفيذ الطلب", "The request could not be completed"))
    prov = r.get("provider") or ""
    msg = _clean(r.get("message"))
    setup = r.get("setup")
    if setup and setup.get("steps") and tool == "forecast_fire_danger":
        extra_steps = T(lang, f"\nالخطوات: {setup['steps']}\nالروابط: {setup.get('register')} · الرخصة: {setup.get('licence')} · الرمز: {setup.get('token')}", f"\nSteps: {setup['steps']}\nLinks: {setup.get('register')} · licence: {setup.get('licence')} · token: {setup.get('token')}")
        msg_l = T(lang, "التوقع العالمي لشهر واحد يحتاج وصولًا إلى بيانات الخطر الموسمي لحرائق CEMS في Copernicus EWDS (حساب مجاني منفصل + قبول الرخصة + رمز وصول شخصي). لم يُستبدل بأي مصدر آخر.", msg)
        steps_ar = "1) أنشئ حسابًا مجانيًا أو سجّل الدخول في ewds.climate.copernicus.eu (حساب منفصل عن Earthdata وCopernicus Data Space). 2) اقبل رخصة المجموعة من تبويب Download. 3) انسخ الرمز الشخصي من صفحة how-to-api وضع EWDS_API_KEY=<الرمز> في ملف .env الخاص بالخادم (وليس في المحادثة) ثم أعد التشغيل."
        extra_steps = T(lang, chr(10) + "الخطوات: " + steps_ar + chr(10) + f"الروابط: {setup.get('register')} · الرخصة: {setup.get('licence')} · الرمز: {setup.get('token')}", extra_steps)
        return f"{emo} **{T(lang, ar, en)}**: {msg_l}" + extra_steps
    out = f"{emo} **{T(lang, ar, en)}**" + (f" ({prov})" if prov and st in ("upstream_error", "needs_credentials", "unsupported_region") else "") + (f": {msg}" if msg else ".")
    if st == "upstream_error":
        out += T(lang, " هذا لا يعني أن البيانات غير موجودة؛ حاول لاحقًا.", " This does not mean the data do not exist; try again later.")
    if setup:
        out += T(lang, f"\nالإعداد: سجّل من {setup.get('register')}، وضع `{setup.get('env')}` في ملف `.env` الخلفي (ليس في المحادثة) ثم أعد التشغيل.",
                 f"\nSetup: register at {setup.get('register')}, put `{setup.get('env')}` in the backend `.env` file (never in the chat), then restart.")
    return out


def _trend(out: dict, lang: str) -> str:
    r, s = out["result"], out["summary"]
    if r.get("status") != "ok":
        msg = _clean(r.get("message"))
        alt = r.get("suggested_alternative")
        return f"❓ **{T(lang, 'لا يمكن تحليل الاتجاه', 'No trend verdict could be issued')}**" + (f": {msg}" if msg else ".") + (T(lang, f" بديل متاح: {alt}.", f" Available alternative: {alt}.") if alt else "")
    v = r["variable"]
    vid = v.get("id") or "air_temperature"
    name = (v.get("name_ar") if lang == "ar" else None) or v["name"].split(" (")[0]
    place = r["region"]["name"]
    y0, y1 = s["period"]["first"][:4], s["period"]["last"][:4]
    sen = s["sen_slope"]
    emo = EMOJI.get(vid, "📈")
    cite = " [1]"
    if s["significant"]:
        verb_en = {"increasing": "increased", "decreasing": "decreased"}.get(s["direction"], "changed")
        verb_ar = {"increasing": "ارتفع", "decreasing": "انخفض"}.get(s["direction"], "تغيّر")
        sign = "+" if (sen["value"] or 0) > 0 else ""
        return T(lang, f"{emo} **{name} في {place} {verb_ar} بين {y0} و{y1}.** ميل Sen: **{sign}{sen['value']} {sen['unit']}** (p = {s['p_value']}؛ دالّ عند α = {s['alpha']}).{cite}\nهذا وصف للماضي وليس تنبؤًا.",
                 f"{emo} **{name} in {place} {verb_en} between {y0} and {y1}.** Sen's slope: **{sign}{sen['value']} {sen['unit']}** (p = {s['p_value']}; significant at α = {s['alpha']}).{cite}\nThis describes the past; it is not a forecast.")
    return T(lang, f"{emo} **البيانات الحالية لا تكفي لتأكيد وجود اتجاه** في {name} في {place} بين {y0} و{y1} عند مستوى دلالة α = {s['alpha']} (p = {s['p_value']}).{cite}",
             f"{emo} **The available data are not sufficient to confirm a trend** in {name} in {place} between {y0} and {y1} at α = {s['alpha']} (p = {s['p_value']}).{cite}")


def _weather(out: dict, lang: str) -> str:
    r, s = out["result"], out["summary"]
    rows = s["daily"]
    place = (out.get("location") or {}).get("name", "")
    fc = r["capability"] == "weather_forecast"
    head = T(lang, f"🌤️ **{'توقع' if fc else 'إعادة تحليل'} الطقس — {place}**", f"🌤️ **{'Forecast' if fc else 'Historical reanalysis'} — {place}**")
    def line(x):
        return T(lang, f"- {x['date']}: عظمى **{x['tmax_c']}°C**، صغرى {x['tmin_c']}°C، هطول {x['precip_mm']} mm، رياح حتى {x['wind_max_kmh']} km/h",
                 f"- {x['date']}: max **{x['tmax_c']}°C**, min {x['tmin_c']}°C, precipitation {x['precip_mm']} mm, wind up to {x['wind_max_kmh']} km/h")
    ps = s.get("period_stats") or {}
    if (ps.get("n_days") or 0) > 16:
        return T(lang, f"{head} [1]\n- متوسط العظمى **{ps['mean_tmax_c']}°C**، متوسط الصغرى {ps['mean_tmin_c']}°C، مجموع الهطول {ps['total_precip_mm']} mm ({ps['n_days']} يومًا)\nإعادة تحليل ERA5 وليست قراءات محطة.",
                 f"{head} [1]\n- Mean max **{ps['mean_tmax_c']}°C**, mean min {ps['mean_tmin_c']}°C, total precipitation {ps['total_precip_mm']} mm ({ps['n_days']} days)\nERA5-type reanalysis, not station readings.")
    shown = rows[:3]
    body = "\n".join(line(x) for x in shown)
    more = T(lang, f"\nالأيام الباقية ({len(rows) - 3}) في اللوحة الجانبية.", f"\nThe remaining {len(rows) - 3} days are in the side panel.") if len(rows) > 3 else ""
    note = T(lang, "توقع تشغيلي وليس رصدًا؛ وقت الإصدار غير منشور." if fc else "إعادة تحليل ERA5 وليست قراءات محطة.", "Operational forecast, not observations; issue time not published." if fc else "ERA5-type reanalysis, not station readings.")
    return f"{head} [1]\n{body}{more}\n{note}"


def _fire(out: dict, lang: str) -> str:
    r, s = out["result"], out["summary"]
    place = (out.get("location") or {}).get("name", "")
    if r.get("reason_code") == "SENSOR_DATA_NOT_AVAILABLE":
        return "⚠️ " + T(lang, f"**لا توجد بيانات من هذا الحساس لهذه التواريخ.** {_clean(r.get('message'))}", f"**No data from this sensor for these dates.** {_clean(r.get('message'))}")
    n = s.get("n_detections", 0)
    if not n:
        return T(lang, f"🔥 **صفر كشف حراري** قرب {place} في الفترة المطلوبة (البيانات متاحة والطلب صالح) [1]. هذا لا يثبت عدم وجود حريق: الغيوم وتوقيت مرور القمر وحجم البكسل تحد من الكشف.",
                 f"🔥 **Zero thermal detections** near {place} in the requested window (valid request, sensor data available) [1]. This does not prove there was no fire: clouds, overpass timing and pixel size limit detection.")
    p = s["period"]
    return T(lang, f"🔥 **{n} كشفًا حراريًا** قرب {place} من {s['source']} بين {p['first']} و{p['last']} (UTC)؛ أعلى FRP = {s.get('frp_max_mw')} MW [1].\nهذه أنوميات حرارية التقطتها الأقمار وليست حرائق مؤكدة أو مساحة محروقة.",
             f"🔥 **{n} thermal detections** near {place} from {s['source']} between {p['first']} and {p['last']} (UTC); max FRP = {s.get('frp_max_mw')} MW [1].\nThese are satellite thermal anomalies, not confirmed fires, burned area or an incident count.")


def _danger(out: dict, lang: str, asks_probability: bool) -> str:
    s = out["summary"]
    place = (out.get("location") or {}).get("name", "")
    usgs = s.get("usgs_status") == "ok"
    idx = T(lang, f"فئة USGS WFPI لليوم الأول في {place}: **{s.get('usgs_palette_index')}** (فئة على خريطة وليست قيمة معايَرة) [1].", f"USGS WFPI class for day 1 at {place}: **{s.get('usgs_palette_index')}** (a map class, not a calibrated value) [1].")
    if asks_probability:
        head = T(lang, "🔥 **لا يوجد احتمال حدوث حريق متاح.** المتاح مؤشر خطر وليس احتمالًا.", "🔥 **No wildfire probability is available.** Only a fire-danger *index* exists, which is not a probability.")
        if usgs:
            return f"{head}\n{idx}"
        return f"{head}\n" + T(lang, f"وقيمة رقمية لمؤشر الخطر في {place or 'هذا الموقع'} غير متاحة (GWIS يوفّر طبقات خرائط فقط). {INSUFFICIENT['ar']}", f"A numeric danger value for {place or 'this location'} is not available either (GWIS offers map layers only). {INSUFFICIENT['en']}")
    lines = [T(lang, f"🔥 **منتجات خطر الحرائق:** {s['n_gwis_layers']} طبقة GWIS عالمية للعرض على الخريطة" + (" + USGS WFPI داخل الولايات المتحدة." if usgs else "."),
               f"🔥 **Fire-danger products:** {s['n_gwis_layers']} global GWIS map layers" + (" plus USGS WFPI inside the US." if usgs else "."))]
    if usgs:
        lines.append(idx)
    lines.append(T(lang, "مؤشر الخطر ليس احتمالًا ولا يثبت وجود حريق.", "A danger index is not a probability and does not show that a fire exists."))
    return "\n".join(lines)


def _scenes(out: dict, lang: str) -> str:
    s = out["summary"]
    if not s.get("n_scenes"):
        return T(lang, "🛰️ لا توجد مشاهد مطابقة؛ وسّع المدى الزمني أو ارفع حد الغيوم.", "🛰️ No matching scenes; widen the date range or raise the cloud limit.")
    return T(lang, f"🛰️ **{s['n_scenes']} مشهدًا** من {s['collection']} (الأحدث {s['last'][:10]}؛ الغيوم {s['cloud_min']}–{s['cloud_max']}%) [1]. اكتشاف مشاهد فقط: لم تُعالَج بكسلات.",
             f"🛰️ **{s['n_scenes']} scenes** from {s['collection']} (latest {s['last'][:10]}; cloud {s['cloud_min']}–{s['cloud_max']}%) [1]. Discovery only: no pixels were processed.")


def _datasets(out: dict, lang: str) -> str:
    s = out["summary"]
    items = s.get("items", [])
    if not items:
        return T(lang, "لا توجد مجموعات بيانات مطابقة.", "No matching datasets.")
    lines = [T(lang, f"📚 **{s['n']} مجموعة بيانات مطابقة** [1]:", f"📚 **{s['n']} matching datasets** [1]:")] + [f"- {i['name']} {i.get('version') or ''} — {i.get('title')}".replace("  ", " ") for i in items[:5]]
    lines.append(T(lang, "اكتشاف فقط؛ التنزيل يحتاج حساب Earthdata.", "Discovery only; downloading needs an Earthdata account."))
    return "\n".join(lines)


def _lst(out: dict, lang: str) -> str:
    s = out["summary"]
    place = (out.get("location") or {}).get("name", "")
    p = s["period"]
    ar = (f"🌡️ **متوسط حرارة سطح الأرض (LST) قرب {place}: {s['mean_c']}°C** ({s['n_valid']} من {s['n_total']} مركّبًا صالحًا بين {p['first']} و{p['last']}؛ المدى {s['min_c']}–{s['max_c']}°C) [1].\n"
          "هذه حرارة سطح الأرض من MODIS لبكسل ≈1 كم وليست حرارة الهواء؛ أُزيلت المركّبات الغائمة أو ضعيفة الجودة.")
    en = (f"🌡️ **Mean land surface temperature (LST) near {place}: {s['mean_c']}°C** ({s['n_valid']} of {s['n_total']} valid composites between {p['first']} and {p['last']}; range {s['min_c']}–{s['max_c']}°C) [1].\n"
          "This is MODIS surface (skin) temperature for a ≈1 km pixel, not air temperature; cloudy or low-quality composites were removed.")
    return ar if lang == "ar" else en


def _ndvi(out: dict, lang: str) -> str:
    s = out["summary"]
    place = (out.get("location") or {}).get("name", "")
    if not s.get("n_usable"):
        return T(lang, "🛰️ لا توجد فترات NDVI صالحة بعد إزالة السحب والقيم غير الصالحة.", "🛰️ No usable NDVI intervals remain after cloud and invalid-value masking.")
    ar = (f"🛰️ **متوسط NDVI قرب {place}: {s['mean_ndvi']}** ({s['n_usable']} من {s['n_intervals']} فترة صالحة، {s['first']} → {s['last']}) [1].\n"
          "حُسب من Sentinel-2 L2A مع استبعاد السحب والظلال والثلج والقيم غير الصالحة؛ وهو مؤشر نباتي وليس حرارة.")
    en = (f"🛰️ **Mean NDVI near {place}: {s['mean_ndvi']}** ({s['n_usable']} of {s['n_intervals']} usable intervals, {s['first']} → {s['last']}) [1].\n"
          "Computed from Sentinel-2 L2A with clouds, shadows, snow and invalid values masked; a vegetation index, not a temperature.")
    return ar if lang == "ar" else en


def _fc_val(x, unit):
    return f"{x:.1f} {unit}"


def _forecast(out: dict, lang: str) -> str:
    s = out["summary"]
    place = (out.get("location") or {}).get("name", "")
    u = s["unit"]
    c = s["cutoff"]
    ov = s["overall_validation"]
    leads = [x for x in s["leads"] if x["value"] is not None]
    ex = leads[min(len(leads) - 1, 1)] if leads else None
    method = s["selected_model"] if ov != "baseline_only" else s["baseline"]
    var = s["variable"].split(" (")[0]
    mae = [v for v in s["mae_by_group"].values() if v is not None]
    rng = f"{min(mae):.1f}–{max(mae):.1f}" if mae else None
    head_ar = f"📈 **توقع إحصائي شهري ({var} — {place}) من {c['first_forecast_month'][:7]} إلى {c['last_forecast_month'][:7]}** بالطريقة: {method}."
    head_en = f"📈 **Monthly statistical forecast ({var} — {place}), {c['first_forecast_month'][:7]} to {c['last_forecast_month'][:7]}** using: {method}."
    exv_ar = f" مثال: {ex['date'][:7]} ≈ **{_fc_val(ex['value'], u)}** (مجال 80%: {ex['lo80']:.1f}–{ex['hi80']:.1f})." if ex and ex.get("lo80") is not None else ""
    exv_en = f" Example: {ex['date'][:7]} ≈ **{_fc_val(ex['value'], u)}** (80% interval {ex['lo80']:.1f}–{ex['hi80']:.1f})." if ex and ex.get("lo80") is not None else ""
    if ov == "validated_model":
        val_ar = f"تفوّق النموذج على خط الأساس في الاختبار الرجعي؛ الخطأ المطلق النموذجي {rng} {u}." if rng else ""
        val_en = f"The model beat the baseline in the backtest; typical absolute error {rng} {u}." if rng else ""
    elif ov == "partially_validated":
        val_ar = f"التفوق على خط الأساس مُثبت لبعض الآفاق فقط؛ الخطأ المطلق النموذجي {rng} {u}." if rng else ""
        val_en = f"Skill over the baseline is shown for some horizons only; typical absolute error {rng} {u}." if rng else ""
    else:
        val_ar = f"**لم تُثبَت مهارة إضافية فوق خط الأساس**، فالقيم هي خط الأساس بالاسم الحقيقي؛ الخطأ المطلق النموذجي في الاختبار الرجعي {rng} {u}." if rng else "**لم تُثبَت مهارة إضافية فوق خط الأساس.**"
        val_en = f"**No additional skill over the baseline was shown**, so the values are the baseline under its real name; typical backtest absolute error {rng} {u}." if rng else "**No additional skill over the baseline was shown.**"
    lim_ar = f"هذا توقع إحصائي لمتوسطات شهرية وليس طقسًا ليوم بعينه؛ آخر بيانات {c['data_cutoff_month'][:7]} وعدد نقاط الاحتجاز {s['n_holdout_origins']} فقط. [1]"
    lim_en = f"A statistical forecast of monthly means, not the weather of a given day; data end {c['data_cutoff_month'][:7]} and only {s['n_holdout_origins']} holdout origins were used. [1]"
    return (head_ar + exv_ar + chr(10) + val_ar + chr(10) + lim_ar) if lang == "ar" else (head_en + exv_en + chr(10) + val_en + chr(10) + lim_en)


def _outlook(out: dict, lang: str, asks_probability: bool = False) -> str:
    s = out["summary"]
    place = (out.get("location") or {}).get("name", "")
    CAT = {"Above": T(lang, "أعلى من المعتاد", "above normal"), "Normal": T(lang, "قريبة من المعتاد", "near normal"), "Below": T(lang, "أقل من المعتاد", "below normal")}
    src = s.get("source") or ""
    lines = []
    if s.get("months"):
        def line(m):
            cat = CAT[m["category"]]
            if m["mixed"]:
                cat = " / ".join(f"{CAT[k]} {round(v * 100)}%" for k, v in sorted(m["shares"].items(), key=lambda kv: -kv[1])) + T(lang, " (حصص المساحة)", " (area shares)")
            return (cat, m["month"], m["days_in_request"])
        ms = [line(m) for m in s["months"]]
        if len(ms) == 1:
            head_ar = f"🔥 **توقع {src} لـ {place} ({ms[0][1]}): إمكانية حرائق برية كبيرة {ms[0][0]}** [1]"
            head_en = f"🔥 **{src} outlook for {place} ({ms[0][1]}): {ms[0][0]} significant wildland fire potential** [1]"
        else:
            head_ar = f"🔥 **توقع {src} لـ {place}** [1]"
            head_en = f"🔥 **{src} outlook for {place}** [1]"
            lines = [T(lang, f"- {mth} ({d} يومًا ضمن الفترة): {c}", f"- {mth} ({d} days in the window): {c}") for c, mth, d in ms]
        first = T(lang, head_ar, head_en)
    else:
        e = s.get("ensemble") or {}
        first = T(lang, f"🔥 **توقع المؤشر لـ {place} من {src}**", f"🔥 **Danger index outlook for {place} from {src}**") + " [1]"
        if e:
            vw = e.get("valid_window") or ["?", "?"]
            lines = [T(lang, f"- الفترة المتوقعة: {vw[0]} → {vw[1]} (إصدار التوقع {e['issue_date']}، عمره {e['age_days']} يومًا)",
                       f"- Valid period: {vw[0]} → {vw[1]} (forecast issued {e['issue_date']}, {e['age_days']} days old)"),
                     T(lang, f"- مؤشر الطقس الحريقي (FWI) متوسط الفترة: وسيط المجموعة {e['median']:.1f}، ومدى الأعضاء {e['min']:.1f}–{e['max']:.1f} ({e['members']} عضوًا)",
                       f"- Fire Weather Index, period mean: ensemble median {e['median']:.1f}, member range {e['min']:.1f}–{e['max']:.1f} ({e['members']} members)"),
                     (lambda sh: T(lang, f"- نسبة أعضاء المجموعة نسبةً إلى توزيع 1981–2016: أقل من المعتاد {sh['below_normal']*100:.0f}% · قريب {sh['near_normal']*100:.0f}% · أعلى {sh['above_normal']*100:.0f}% (ترددات نسبية بين الأعضاء، وليست احتمال حريق)",
                                    f"- Share of ensemble members vs the 1981-2016 reference: below normal {sh['below_normal']*100:.0f}% · near {sh['near_normal']*100:.0f}% · above {sh['above_normal']*100:.0f}% (relative frequencies among members, not a fire probability)"))(e["member_shares"])
                     if e.get("member_shares") else
                     T(lang, "- هذا مؤشر خطر طقسي وليس احتمال اشتعال، ولا توجد فئات أعلى/أقل من المعتاد لأن دالة المرجع غير مُحمَّلة.",
                       "- This is a weather danger index, not an ignition probability; there are no above/below-normal categories because no reference distribution is loaded.")]
    body = [first] + lines
    if asks_probability:
        body.append(T(lang, "لا يوجد احتمال رقمي لوقوع حريق: التصنيف رسمي نسبةً إلى المعتاد وليس نسبة مئوية.", "There is no numerical probability of a fire: the category is an official classification relative to normal, not a percentage."))
    if s.get("window_kind") == "next_30_days":
        body.append(T(lang, "المنتج شهري: تُعرض الأشهر التي تغطي الثلاثين يومًا، وليس توقعًا دقيقًا لثلاثين يومًا متحركة.", "The product is monthly: the months covering the 30 days are shown; it is not an exact rolling 30-day outlook."))
    ob = s.get("observed")
    if ob and ob.get("n_detections") is not None:
        body.append(T(lang, f"للسياق فقط (رصد وليس توقعًا): {ob['n_detections']} كشفًا حراريًا في آخر 5 أيام قرب المنطقة؛ وغياب الكشوف لا يعني انعدام الخطر مستقبلًا.",
                      f"For context only (observed, not a forecast): {ob['n_detections']} thermal detections in the last 5 days near the area; zero detections would not mean zero future danger."))
    body.append(T(lang, "هذا توقع رسمي مبني على نموذج؛ ولم يتحقق هذا التطبيق من مهارة التوقع محليًا.", "This is an official model outlook; local forecast skill has not been verified by this application."))
    return chr(10).join(body)


def _render_plain(tool: str, out: dict, lang: str, asks_probability: bool = False) -> str:
    r, s = out["result"], out.get("summary", {})
    if r.get("reason_code") == "TASK_PENDING":
        return T(lang, "⏳ **مهمة AppEEARS قيد التنفيذ على خوادم NASA.** حُفظت المهمة؛ أعد السؤال بعد دقائق لجلب النتيجة.", "⏳ **The AppEEARS task is still running on NASA servers.** It was kept; ask again in a few minutes to fetch the result.")
    m = _missing(tool, lang, s)
    if m:
        return m
    if tool == "analyze_trend":
        return _trend(out, lang)
    if tool == "forecast_fire_danger" and r.get("status") == "ok":
        return _outlook(out, lang, asks_probability)
    bad = _not_ok(r, lang, tool)
    if bad and not (r.get("status") == "no_data" and tool in ("get_fire_detections",) and r.get("reason_code") in ("ZERO_DETECTIONS", "SENSOR_DATA_NOT_AVAILABLE")):
        return bad
    fn = {"forecast_monthly": _forecast, "get_ndvi": _ndvi, "get_lst": _lst, "get_weather": _weather, "get_fire_detections": _fire, "search_satellite_scenes": _scenes, "search_earth_datasets": _datasets}.get(tool)
    if fn:
        return fn(out, lang)
    if tool == "list_fire_danger":
        return _danger(out, lang, asks_probability)
    return T(lang, "تم تنفيذ الأداة.", "Tool executed.")


# ---- chat layout (ChatGPT-like): heading, one key callout, [[inline]] visual, paragraphs, small notes -------------------------------------------------------------
import re as _re

_LIMIT = _re.compile(r"not a forecast|not (?:a|an) |not air temperature|does not prove|cannot|no pixels|discovery only|وليس|وليست|لا يثبت|لا تثبت|لا يعني|اكتشاف فقط|لم تُعالَج|غير|ليست", _re.I)


def _title(tool: str, out: dict, lang: str) -> str | None:
    place = (out.get("location") or {}).get("name", "")
    s = out.get("summary") or {}
    r = out.get("result") or {}
    sfx = f" — {place}" if place else ""
    if tool == "analyze_trend" and r.get("status") == "ok":
        v = r["variable"]
        name = (v.get("name_ar") if lang == "ar" else None) or v["name"].split(" (")[0]
        return T(lang, f"اتجاه {name}{sfx}", f"{name} trend{sfx}") + f" · {s['period']['first'][:4]}–{s['period']['last'][:4]}"
    return {"forecast_fire_danger": T(lang, "توقع خطر الحرائق", "Wildfire danger outlook"), "get_weather": T(lang, "الطقس", "Weather"), "get_fire_detections": T(lang, "كشوف الحرائق", "Fire detections"), "get_ndvi": "NDVI", "get_lst": T(lang, "حرارة سطح الأرض (LST)", "Land surface temperature (LST)"),
            "forecast_monthly": T(lang, "توقع إحصائي شهري", "Monthly statistical forecast"), "list_fire_danger": T(lang, "خطر الحرائق", "Fire danger"), "search_satellite_scenes": T(lang, "مشاهد Sentinel", "Sentinel scenes"),
            "search_earth_datasets": T(lang, "مجموعات البيانات", "Datasets")}.get(tool, "") + (sfx if tool != "search_earth_datasets" else "") or None


def layout(tool: str, text: str, lang: str, out: dict, tone: str = "key") -> str:
    """Plain template text -> structured Markdown: ## title, a key callout (first line), [[inline]] (where the table/chart goes), paragraphs, ^ small notes."""
    lines = [l.rstrip() for l in text.split(chr(10)) if l.strip()]
    if not lines:
        return text
    title = _title(tool, out, lang)
    first, rest = lines[0], lines[1:]
    paras, notes = [], []
    for l in rest:
        is_list = _re.match(r"^\s*(?:[-•*]|\d+[.)])\s", l)
        if not is_list and _LIMIT.search(l):
            notes.append("^ " + l)
        else:
            paras.append(l)
    blocks = ([f"## {title}"] if title else []) + [f"> [!{tone}] {first}", "[[inline]]"] + paras + notes
    return (chr(10) * 2).join(blocks)


def render(tool: str, out: dict, lang: str, asks_probability: bool = False) -> str:
    text = _render_plain(tool, out, lang, asks_probability)
    r = out["result"]
    ok = r.get("status") == "ok" or (tool == "get_fire_detections" and r.get("reason_code") == "ZERO_DETECTIONS")
    if not ok or (out.get("summary") or {}).get("needs") or r.get("reason_code") == "TASK_PENDING":
        return text
    tone = "warn" if (tool == "forecast_monthly" and (out.get("summary") or {}).get("overall_validation") == "baseline_only") else "key"
    return layout(tool, text, lang, out, tone)
