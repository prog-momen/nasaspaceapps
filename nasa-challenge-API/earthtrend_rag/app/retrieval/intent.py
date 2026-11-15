"""Deterministic intent routing.

RAG answers documentation/scientific-knowledge questions. Questions that need real observations,
statistics or forecasts must be handed to the data/analysis/forecast tools (named after the tool
contracts in section 6.1 of the project's reference file). Heuristic by design: cheap, testable,
no LLM call. Known limitation: place detection uses a small gazetteer + capitalised English words.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.chunking.metadata import VARIABLE_KEYWORDS

_YEAR = re.compile(r"\b(19[89]\d|20[0-9]\d)\b")
_REL_TIME = re.compile(
    r"(أمس|اليوم|الآن|حاليا|حالياً|الشهر (?:الماضي|القادم)|السنة (?:الماضية|القادمة)|العام (?:الماضي|القادم)|الأسبوع"
    r"|yesterday|today|right now|currently|last (?:month|year|week)|next (?:month|year|week|decade)|\bthis (?:month|year)\b)", re.I)
_COORDS = re.compile(r"-?\d{1,3}\.\d+\s*[,،°NSEW ]+\s*-?\d{1,3}\.\d+|\blat(?:itude)?\b.*\blon(?:gitude)?\b", re.I)
_EN_PLACE = re.compile(r"\b(?:in|at|for|over|near|across)\s+(?!NASA\b)[A-Z][a-z]{2,}")
_PLACES = (
    "نابلس|القاهرة|الرياض|دبي|عمان|بغداد|دمشق|بيروت|الخرطوم|تونس|الجزائر|الرباط|الدوحة|الكويت|مكة|جدة|غزة|القدس|"
    "فلسطين|مصر|السعودية|الأردن|العراق|سوريا|لبنان|السودان|المغرب|الإمارات|قطر|عمان|اليمن|ليبيا|تركيا|أمريكا|كاليفورنيا|"
    "أستراليا|البرازيل|الهند|الصين|اليابان|أوروبا|أفريقيا|إفريقيا|الأمازون|سيبيريا|"
    "nablus|cairo|riyadh|dubai|amman|baghdad|london|paris|egypt|palestine|saudi|jordan|california|amazon|australia|"
    "brazil|india|china|japan|europe|africa|siberia|texas|canada"
)
_PLACE_RE = re.compile(rf"(?:^|[\s،,(]|[وبلكف]?ال)(?:{_PLACES})", re.I)

_FORECAST = re.compile(
    r"(توقع|تنبأ|تنبؤ|سيرتفع|سينخفض|ستزداد|سيكون|ستكون|forecast|predict|projection|will (?:be|rise|increase|decrease|fall)|"
    r"in (?:20[3-9]\d|202[6-9]))", re.I)
_TREND = re.compile(
    r"(هل .*?(?:ترتفع|ارتفعت|ازدادت|زادت|انخفضت|تتزايد|تتناقص|تزداد)|اتجاه (?:صاعد|هابط)|ما (?:هو|هي) اتجاه|احسب|حلل (?:لي )?|"
    r"is .*?(?:increasing|decreasing|rising|falling|warming|getting)|(?:calculate|compute|run) .*?(?:trend|mann|sen|slope)|"
    r"what is the trend|how much (?:has|have) .*?(?:risen|increased|changed))", re.I)
_VALUE = re.compile(
    r"(كم (?:كانت|كان|هي|بلغت|عدد)|ما (?:هي |هو )?(?:قيمة|درجة|كمية|متوسط|معدل|مجموع)|أعطني|أعطيني|"
    r"what (?:was|is|were) the (?:temperature|rainfall|precipitation|average|mean|value|number)|average|how (?:hot|much rain|many fires)|"
    r"give me (?:the )?(?:data|values|series|time ?series))", re.I)
_CONCEPTUAL = re.compile(
    r"(^|\s)(ما (?:هو|هي) (?:تعريف|معنى|الفرق|مفهوم|وحدة|وحدات)|اشرح|عرّف|عرف|لماذا|كيف يعمل|كيف أحصل|كيف استخدم|ما معنى|"
    r"what is (?:a |an |the )?(?:difference|meaning|definition)|explain|define|why|how (?:does|do|can|to)|which (?:api|dataset|product))", re.I)

TOOL_MAP = {
    "needs_data": ["search_datasets", "fetch_timeseries"],
    "needs_analysis": ["fetch_timeseries", "validate_timeseries", "analyze_trend"],
    "needs_forecast": ["fetch_timeseries", "forecast_timeseries"],
}


@dataclass
class Intent:
    kind: str                                  # knowledge | needs_data | needs_analysis | needs_forecast
    required_tools: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    filters: dict = field(default_factory=dict)   # soft metadata filters inferred from the question
    language: str = "ar"


def wants_english(q: str) -> bool:
    return bool(re.search(r"(بالإنجليزي|بالانجليزي|بالإنكليزي|in english|answer in english|reply in english|english please)", q, re.I))


def infer_filters(q: str) -> dict:
    f: dict = {}
    vars_ = [v for v, pats in VARIABLE_KEYWORDS.items()
             if v != "air_temperature" and any(re.search(p, q, re.I) for p in pats)]
    if len(vars_) == 1:   # one clear variable only; ambiguous questions stay unfiltered
        f["variables"] = vars_
    m = re.search(r"\bS(\d{2})\b", q)
    if m:
        f["service_id"] = f"S{m.group(1)}"
    return f


def classify(question: str) -> Intent:
    q = question.strip()
    lang = "en" if wants_english(q) else "ar"
    filters = infer_filters(q)
    specific = bool(_YEAR.search(q) or _REL_TIME.search(q) or _COORDS.search(q) or _EN_PLACE.search(q) or _PLACE_RE.search(q))
    conceptual = bool(_CONCEPTUAL.search(q))

    if specific:
        if _FORECAST.search(q) and not re.search(r"\b(how does|what is)\b.*\b(arima|sarima|forecast)", q, re.I):
            return Intent("needs_forecast", TOOL_MAP["needs_forecast"], ["forecast request for a specific place/time"], filters, lang)
        if _TREND.search(q) and not conceptual:
            return Intent("needs_analysis", TOOL_MAP["needs_analysis"], ["trend/statistic for a specific place/period"], filters, lang)
        if _VALUE.search(q) and not conceptual:
            return Intent("needs_data", TOOL_MAP["needs_data"], ["measured value for a specific place/time"], filters, lang)
    return Intent("knowledge", [], ["documentation / scientific knowledge question"], filters, lang)
