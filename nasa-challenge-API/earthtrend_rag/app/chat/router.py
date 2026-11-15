"""Deterministic intent routing + argument extraction (Arabic/English). Used (a) as the fallback when Gemini is unavailable,
(b) to extract explicit places/periods for conflict detection. It never invents a place or a period."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.chat.location import candidate_place_names, extract_coords, find_known_place
from app.retrieval.intent import classify

_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
ISO = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
YEAR = re.compile(r"(?<!\d)(19[89]\d|20[0-4]\d)(?!\d)")


@dataclass
class Plan:
    tool: str | None                       # tool name or None (knowledge / RAG)
    args: dict = field(default_factory=dict)
    reason: str = ""
    unsupported: str | None = None         # honest refusal text key
    missing: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)


def parse_period(msg: str, today: date | None = None) -> dict | None:
    """Explicit period in the message: ISO dates, relative words, or years. Returns {start,end,kind} or None."""
    t = msg.translate(_AR_DIGITS).lower()
    today = today or date.today()
    iso = [date(int(a), int(b), int(c)) for a, b, c in ISO.findall(t) if 1 <= int(b) <= 12 and 1 <= int(c) <= 31]
    if len(iso) >= 2:
        return {"start": min(iso).isoformat(), "end": max(iso).isoformat(), "kind": "dates"}
    if len(iso) == 1:
        return {"start": iso[0].isoformat(), "end": iso[0].isoformat(), "kind": "date"}
    m = re.search(r"(?:last|past|آخر|اخر|الماضية|الأخيرة)\s*(\d{1,3})\s*(days?|أيام|ايام|يوم|weeks?|أسابيع|اسابيع|months?|أشهر|شهور)", t) or \
        re.search(r"(\d{1,3})\s*(days?|أيام|ايام)\s*(?:ago|الماضية|الأخيرة|الاخيرة)", t)
    if m:
        n = int(m.group(1)); unit = m.group(2)
        days = n * (7 if unit.startswith(("week", "أسابيع", "اسابيع")) else 30 if unit.startswith(("month", "أشهر", "شهور")) else 1)
        return {"start": (today - timedelta(days=days)).isoformat(), "end": today.isoformat(), "kind": "past_days", "days": days}
    m = re.search(r"(?:next|coming|القادمة|القادمه|المقبلة|القادم)\s*(\d{1,2})?\s*(days?|أيام|ايام|يوم)?", t)
    m2 = re.search(r"(?:next|coming)\s*(\d{1,2})\s*days?|(\d{1,2})\s*(?:أيام|ايام)\s*(?:القادمة|المقبلة)|الأيام القادمة|next days", t)
    if m2:
        n = int(next((g for g in m2.groups() if g), 3))
        return {"start": today.isoformat(), "end": (today + timedelta(days=n - 1)).isoformat(), "kind": "next_days", "days": n}
    if re.search(r"tomorrow|غدا|غداً|بكرة", t):
        d = today + timedelta(days=1)
        return {"start": d.isoformat(), "end": d.isoformat(), "kind": "tomorrow", "days": 2}
    if re.search(r"yesterday|أمس|امس", t):
        d = today - timedelta(days=1)
        return {"start": d.isoformat(), "end": d.isoformat(), "kind": "yesterday"}
    if re.search(r"last week|الأسبوع الماضي|الاسبوع الماضي", t):
        return {"start": (today - timedelta(days=7)).isoformat(), "end": today.isoformat(), "kind": "past_days", "days": 7}
    if re.search(r"next week|الأسبوع القادم|الاسبوع القادم", t):
        return {"start": today.isoformat(), "end": (today + timedelta(days=6)).isoformat(), "kind": "next_days", "days": 7}
    if re.search(r"\btoday\b|اليوم|الآن|now\b", t):
        return {"start": today.isoformat(), "end": today.isoformat(), "kind": "today", "days": 1}
    ys = sorted({int(y) for y in YEAR.findall(t)})
    if len(ys) >= 2:
        return {"start": f"{ys[0]}-01-01", "end": f"{ys[-1]}-12-31", "kind": "years", "start_year": ys[0], "end_year": ys[-1]}
    if len(ys) == 1:
        if re.search(r"(since|from|منذ)", t):
            return {"start": f"{ys[0]}-01-01", "end": today.isoformat(), "kind": "since_year", "start_year": ys[0], "end_year": today.year}
        return {"start": f"{ys[0]}-01-01", "end": f"{ys[0]}-12-31", "kind": "year", "start_year": ys[0], "end_year": ys[0]}
    return None


def explicit_place(msg: str) -> dict | None:
    """A place the user explicitly wrote (coordinates > gazetteer > None). Geocoding of free names happens in the agent."""
    c = extract_coords(msg.translate(_AR_DIGITS))
    if c:
        return {"name": f"point ({c[0]:.4f}, {c[1]:.4f})", "latitude": c[0], "longitude": c[1], "source": "coordinates in message"}
    return find_known_place(msg)


R = lambda p: re.compile(p, re.I)
RX = {
    "danger": R(r"fire danger|fire weather|\bfwi\b|danger index|خطر (?:ال)?(?:حرائق|حريق)|مؤشر (?:ال)?(?:حرائق|حريق|طقس الحرائق)|مؤشرات? خطر"),
    "fire_prob": R(r"(?:probability|chance|predict(?:ion)?|forecast)\s+(?:of\s+)?(?:a\s+)?(?:wild)?fires?|احتمال(?:ية)?\s+(?:ال)?(?:حرائق|حريق|اشتعال)|التنبؤ بال(?:حرائق|حريق)|هل سيحدث حريق"),
    "burned": R(r"burn(?:ed|t)\s+area|المساحة المحروقة|مساحة (?:ال)?(?:محروقة|حرائق)|عدد الحرائق|how many (?:wild)?fires"),
    "fire": R(r"fire|hotspot|detection|حرائق|حريق|بؤر|كشف"),
    "satellite": R(r"sentinel|satellite|scene|imagery|ndvi|landsat|صور (?:ال)?(?:أقمار|اقمار|فضائية)|مشاهد|قمر صناعي|أقمار صناعية|اقمار صناعية"),
    "datasets": R(r"dataset|data set|catalog|cmr|earth ?engine|earthdata|mod11|\bhls\b|مجموعات? (?:ال)?بيانات|كتالوج|منتجات? (?:ناسا|بيانات)"),
    "weather": R(r"weather|forecast|temperature|rain|wind|humidity|طقس|توقعات|درجة (?:ال)?حرارة|حرارة|أمطار|مطر|رياح|رطوبة|الجو"),
    "trend": R(r"trend|increas|decreas|ris(?:e|en|ing)|rose|fall(?:en|ing)?|fell|drop(?:ped)?|declin|chang(?:e|ed|ing)|warm(?:er|ing|ed)|cool(?:er|ing|ed)|hotter|colder|wetter|drier|getting|"
              r"ارتفع|انخفض|اتجاه|تزايد|تناقص|هل زاد|تغير|تغيّر|[بيت]ن?سخن|سخون|[بيت]ن?برد|بتزيد|بيزيد|بتقل|بيقل|بقل|بزيد|أصبح|اصبح|أكثر (?:حرارة|برودة|جفاف|مطر)|ازداد|قل(?:ت|ّت)"),
    "lst": R(r"land surface temp|\blst\b|حرارة سطح"),
}


_VAR_RX = [("land_surface_temperature", R(r"land surface temp|lst|حرارة سطح")), ("precipitation", R(r"rain|precip|snow|هطول|أمطار|امطار|مطر")),
           ("relative_humidity", R(r"humid|رطوبة")), ("wind_speed", R(r"wind|رياح")), ("air_temperature", R(r"temperature|temp|heat|hot|warm|cold|cool|حرار|دفء|برد|ساخن|بارد|سخن|سخون|حرb"))]


def infer_variable(msg: str) -> str | None:
    """Variable named in the message (most specific first); None when the message names none."""
    for vid, rx in _VAR_RX:
        if rx.search(msg):
            return vid
    return None


_FC_WORD = re.compile(r"forecast|predict|projection|will (?:it|the|be)|going to be|توقع|تنبأ|تنبؤ|سيكون|ستكون|سترتفع|سينخفض|المتوقع", re.I)
_DAYS_WORD = re.compile(r"\b\d{1,2}\s*days?\b|tomorrow|tonight|this week|next week|غد[اً]|بكرة|الأسبوع|ايام|أيام|اليوم|الليلة", re.I)


def parse_horizon_months(m: str, today: date) -> int | None:
    """Horizon in MONTHS named in the message ('two years', '18 months', 'next year', 'in 2027'); None when the message names none."""
    t = m.lower()
    if re.search(r"سنتين|سنتان|عامين|عامان|two years|2 years", t):
        return 24
    mm = re.search(r"(\d{1,2})\s*(?:months?|شهر|أشهر|اشهر|شهور)", t)
    if mm:
        return int(mm.group(1))
    my = re.search(r"(\d{1,2})\s*(?:years?|سنة|سنين|سنوات|أعوام|عام)", t)
    if my:
        return int(my.group(1)) * 12
    if re.search(r"next year|coming year|السنة القادمة|العام القادم|السنة الجاية|العام الجاي|للسنة القادمة|للعام القادم|سنة قادمة", t):
        return 12
    if re.search(r"next month|الشهر القادم|الشهر الجاي|الأشهر القادمة|الاشهر القادمة|الشهور القادمة|months? ahead", t):
        return 6 if re.search(r"الأشهر|الاشهر|الشهور|months", t) else 1
    ys = [int(y) for y in re.findall(r"(?<!\d)(20\d\d)(?!\d)", t)]
    if len(ys) == 1 and ys[0] > today.year:
        return (ys[0] - today.year) * 12 + (13 - today.month)
    return None


_OUTLOOK_TOPIC = re.compile(r"wild\s?fires?|fire\s+(?:danger|risk|weather|outlook|potential)|fires?\s+(?:danger|risk)|danger of fires?|خطر (?:ال)?(?:حرائق|حريق)|مخاطر (?:ال)?حرائق|احتمال(?:ية)? (?:حدوث |وقوع )?(?:ال)?(?:حرائق|حريق)|توقع(?:ات)? (?:ال)?حرائق", re.I)
_OUTLOOK_WINDOW = re.compile(r"next month|coming month|next 30 days|next thirty days|within (?:the )?(?:next )?month|الشهر (?:القادم|الجاي|المقبل)|(?:ال)?ثلاثين يوم|30 يوم|٣٠ يوم|شهر قادم", re.I)
_OUTLOOK_WORD = re.compile(r"outlook|توقعات? (?:ال)?(?:خطر|حرائق)", re.I)


def outlook_window(m: str) -> str | None:
    if re.search(r"next 30 days|next thirty days|(?:ال)?ثلاثين يوم|30 يوم|٣٠ يوم|within (?:the )?(?:next )?(?:30|thirty)", m, re.I):
        return "next_30_days"
    if _OUTLOOK_WINDOW.search(m) or _OUTLOOK_WORD.search(m):
        return "next_calendar_month"
    return None


def route(msg: str, memory: dict | None = None, today: date | None = None) -> Plan:
    """Message -> Plan. Place/period come from the message first, then session memory (follow-ups); controls are merged by the agent."""
    memory = memory or {}
    today = today or date.today()
    m = msg.translate(_AR_DIGITS)
    period = parse_period(m, today)
    if RX["burned"].search(m) and not RX["fire_prob"].search(m):
        return Plan(None, {}, "unsupported", unsupported="burned_area")
    if _OUTLOOK_TOPIC.search(m) and outlook_window(m) and not RX["lst"].search(m):
        flags = ["asks_probability"] if RX["fire_prob"].search(m) else []
        return Plan("forecast_fire_danger", {"window": outlook_window(m)}, "one-month wildfire danger outlook (official sources only)", flags=flags)
    if RX["fire_prob"].search(m):
        # never a percentage: the only honest answer is the danger INDEX/category when one exists for the place (see agent)
        return Plan("list_fire_danger", {}, "fire danger index (probability asked)", flags=["asks_probability"])
    intent = classify(m)
    hm = parse_horizon_months(m, today)
    var0 = infer_variable(m)
    if (_FC_WORD.search(m) or re.search(r"(?<!\d)20\d\d(?!\d)", m)) and hm and not _DAYS_WORD.search(m) and not RX["fire"].search(m) and not RX["lst"].search(m) and (var0 or RX["weather"].search(m)):
        if hm > 24:
            return Plan(None, {}, "unsupported", unsupported="forecast_too_long")
        return Plan("forecast_monthly", {"months": hm, **({"variable": var0} if var0 else {})}, "monthly statistical forecast (1-24 months)")
    if intent.kind == "needs_forecast" and period and period.get("end_year", 0) > today.year:
        return Plan(None, {}, "unsupported", unsupported="climate_forecast")
    if intent.kind == "needs_forecast" and not RX["weather"].search(m):
        return Plan(None, {}, "unsupported", unsupported="climate_forecast")
    if RX["danger"].search(m):
        return Plan("list_fire_danger", {}, "fire danger products")
    if re.search(r"ndvi|نبات(?:ي)?|vegetation index|مؤشر (?:ال)?(?:نباتي|اخضرار|اخضرار)", m, re.I) and not RX["fire"].search(m):
        return Plan("get_ndvi", {}, "Sentinel-2 NDVI statistics")
    if RX["datasets"].search(m) and not re.search(r"weather|forecast|طقس|توقعات|الجو", m, re.I):
        kw = re.search(r"(mod11\w*|hls\w*|ndvi|land surface temperature|precipitation|sea ice|\blst\b)", m, re.I)
        return Plan("search_earth_datasets", {"keyword": kw.group(1) if kw else "land surface temperature"}, "dataset discovery")
    if RX["satellite"].search(m):
        return Plan("search_satellite_scenes", {"collection": "sentinel-2-l2a"}, "satellite discovery")
    multi_year = bool(period and period.get("kind") in ("years", "since_year") and period.get("end_year", 0) - period.get("start_year", 0) >= 1) or         bool(period and period.get("kind") == "dates" and (date.fromisoformat(period["end"]) - date.fromisoformat(period["start"])).days > 366)
    var = infer_variable(m)
    climate_word = RX["weather"].search(m) or RX["trend"].search(m) or var
    if RX["lst"].search(m) and not multi_year and not RX["fire"].search(m):
        return Plan("get_lst", {}, "land surface temperature (satellite skin temperature, not air temperature)")
    if not RX["fire"].search(m) and (intent.kind == "needs_analysis" or (multi_year and climate_word)):
        # a multi-year period is ALWAYS the historical trend workflow (NASA POWER), never short-term/historical weather
        args = {"variable": var} if var else {}
        if multi_year and period.get("kind") in ("years", "since_year"):
            args.update(start_year=period["start_year"], end_year=period["end_year"])
        elif multi_year:
            args.update(start_year=int(period["start"][:4]), end_year=int(period["end"][:4]))
        return Plan("analyze_trend", args, "multi-year trend")
    if RX["trend"].search(m) and var and not period and not re.search(r"compare|versus|vs|مقارن|بالمقارنة", m, re.I) and not RX["fire"].search(m) and not re.search(r"tomorrow|today|tonight|this week|next|غدا|غداً|اليوم|الليلة|الأسبوع|القادم|الآن|حاليا", m, re.I):
        return Plan("analyze_trend", {"variable": var}, "trend question without a period: the backend assumes the last 25 complete years")
    if RX["fire"].search(m):
        return Plan("get_fire_detections", {}, "active fire detections")
    if RX["weather"].search(m):
        past = period and period["kind"] in ("yesterday", "past_days", "dates") and date.fromisoformat(period["end"]) < today
        past = past or (period and period["kind"] in ("year", "years") and period.get("end_year", today.year) < today.year)
        args = {"mode": "historical" if past else "forecast"}
        if past and period:
            args.update(start_date=period["start"], end_date=period["end"])
        elif period and period.get("days"):
            args["days"] = min(16, int(period["days"]))
        return Plan("get_weather", args, "weather")
    return Plan(None, {}, "knowledge")


UNSUPPORTED = {
    "fire_probability": {
        "ar": "لا أستطيع تقدير «احتمال حدوث حريق». مؤشرات خطر الحرائق (مثل FWI) تصف ظروفًا مواتية للاشتعال وليست احتمالًا معايَرًا، ولا تثبت وجود حريق أو سببه. يمكنني عرض منتجات خطر الحرائق المتاحة (GWIS عالميًا، USGS للولايات المتحدة) أو كشف بؤر الحرائق الفعلية من FIRMS.",
        "en": "I cannot estimate a 'probability of fire'. Fire danger indices (e.g. FWI) describe conditions favourable to fire; they are not calibrated probabilities and do not show that a fire exists or why. I can list the available fire danger products (GWIS globally, USGS for the US) or show actual FIRMS detections."},
    "burned_area": {
        "ar": "لا أستطيع تحويل عدد بؤر FIRMS إلى مساحة محروقة أو عدد حرائق: البؤر كشوف حرارية للأقمار، وقد تنتمي عدة بؤر إلى حريق واحد، ولا يوجد هنا منهج صالح للتحويل. يمكنني عرض البؤر نفسها (الوقت، الثقة، FRP).",
        "en": "I cannot turn FIRMS detections into burned area or an incident count: detections are satellite thermal anomalies, several can belong to one fire, and no valid conversion method is implemented. I can show the detections themselves (time, confidence, FRP)."},
    "forecast_too_long": {
        "ar": "في المحادثة أقصى أفق للتوقع الإحصائي الشهري المُتحقَّق منه هو 24 شهرًا. لأفق أطول افتح صفحة التنبؤ (Forecast): حتى 5 سنوات مختبر على آخر أشهر حقيقية، وحتى 10 سنوات امتداد للاتجاه غير مُتحقَّق منه، وما بعد ذلك حساب رياضي فقط وبثقة أقل بكثير. التوقعات المناخية بعيدة المدى (إسقاطات السيناريوهات) غير مبنية هنا.",
        "en": "In chat, the longest validated monthly statistical forecast is 24 months. For a longer horizon open the Forecast page: up to 5 years is checked against the last real months, up to 10 years is a trend extension that has not been validated, and beyond that it is computation only, with much lower confidence. Long-term climate projections (scenarios) are not implemented here."},
    "climate_forecast": {
        "ar": "التنبؤ المناخي بعيد المدى (إسقاطات السيناريوهات) غير مدعوم هنا. المتاح: توقعات جوية تشغيلية حتى 16 يومًا (Open-Meteo)، وتوقع إحصائي لمتوسطات شهرية حتى 24 شهرًا (مع اختبار رجعي ومجالات تنبؤ)، وتحليل الاتجاه التاريخي (NASA POWER).",
        "en": "Long-range climate projections (scenarios) are not supported. Available: operational weather forecasts up to 16 days (Open-Meteo), statistical monthly forecasts up to 24 months (with backtests and prediction intervals), and historical trends (NASA POWER)."},
    "unsupported_generic": {
        "ar": "هذا الطلب يحتاج قدرة غير متوفرة في هذا النموذج الأولي. أستطيع: اتجاهات تاريخية (NASA POWER)، توقعات حتى 16 يومًا، كشوف حرائق FIRMS، منتجات خطر الحرائق، اكتشاف مشاهد Sentinel، والبحث في الوثائق.",
        "en": "This request needs a capability the prototype does not have. I can do: historical trends (NASA POWER), forecasts up to 16 days, FIRMS fire detections, fire-danger products, Sentinel scene discovery, and documentation questions."},
}
