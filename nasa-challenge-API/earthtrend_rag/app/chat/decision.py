"""Structured request/decision record and capability validation.

Every chat turn produces ONE inspectable `Decision` (what the user asked, as understood) from either Claude (function-call arguments of
`interpret_request`) or the deterministic router. The backend then validates it against what the providers can really do BEFORE any tool
runs. This is a record of the request, not of the model's reasoning. Nothing here invents places, dates, variables or endpoints:
anything not stated by the user (or resolvable from the session context) is left empty and reported in `missing`.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta

from app.analysis.catalog import VARIABLES

TREND_MIN_YEAR = 1981            # NASA POWER monthly MERRA-2 start
HIST_WEATHER_MAX_DAYS = 366      # Open-Meteo historical window used by this prototype
FORECAST_MAX_DAYS = 16           # Open-Meteo forecast horizon
FIRMS_MAX_DAYS = 5               # FIRMS area API
TREND_VARS = [k for k, v in VARIABLES.items() if v.get("source") == "nasa_power"]

INTENTS = ["trend", "weather_forecast", "weather_historical", "fire_detections", "fire_danger", "satellite_scenes", "datasets", "land_surface_temperature", "ndvi", "forecast_monthly", "fire_outlook", "knowledge", "clarify", "unsupported"]
INTENT_TOOL = {"trend": "analyze_trend", "weather_forecast": "get_weather", "weather_historical": "get_weather", "fire_detections": "get_fire_detections",
               "fire_danger": "list_fire_danger", "satellite_scenes": "search_satellite_scenes", "datasets": "search_earth_datasets", "land_surface_temperature": "get_lst", "ndvi": "get_ndvi", "forecast_monthly": "forecast_monthly", "fire_outlook": "forecast_fire_danger"}
TOOL_INTENT = {"analyze_trend": "trend", "get_fire_detections": "fire_detections", "list_fire_danger": "fire_danger", "search_satellite_scenes": "satellite_scenes",
               "search_earth_datasets": "datasets", "get_lst": "land_surface_temperature", "get_ndvi": "ndvi", "forecast_monthly": "forecast_monthly", "forecast_fire_danger": "fire_outlook"}
INTENT_PROVIDER = {"trend": ("NASA POWER", "historical_climate"), "weather_forecast": ("Open-Meteo", "weather_forecast"), "weather_historical": ("Open-Meteo", "historical_weather"),
                   "fire_detections": ("NASA FIRMS", "active_fire_detection"), "fire_danger": ("GWIS / USGS", "fire_danger_map"), "satellite_scenes": ("Copernicus Data Space", "scene_discovery"),
                   "datasets": ("NASA CMR / Earth Engine catalog", "dataset_discovery"), "land_surface_temperature": ("NASA AppEEARS (MODIS MOD11A2)", "land_surface_temperature"), "ndvi": ("Copernicus Data Space (Sentinel-2 L2A)", "satellite_processing"), "forecast_monthly": ("NASA POWER + statistical model", "statistical_forecast"), "fire_outlook": ("NIFC outlook / Copernicus EWDS seasonal fire danger", "fire_danger_outlook"), "knowledge": ("Indexed official documentation", "documentation")}

# the Claude function: a structured request, not a tool call. The backend maps it to a tool after validation.
DECISION_DECLARATION = {
    "name": "interpret_request",
    "description": ("Record how you understand the user's request. Copy only what the user (or the CONTEXT) stated; never invent a place, date, variable or number. "
                    "intent: trend = multi-year historical change of a climate variable at a place (NASA POWER, years); weather_forecast = next 1-16 days; "
                    "weather_historical = a specific past period of at most one year; fire_detections = recent satellite fire detections (1-5 days); "
                    "land_surface_temperature = satellite SURFACE (skin) temperature MODIS LST at a point for a period of at most one year, NOT air temperature; ndvi = Sentinel-2 NDVI statistics for a small area (cloud-masked, vegetation index); forecast_monthly = STATISTICAL forecast of MONTHLY means (temperature, precipitation, humidity, wind) for 1-24 months ahead: use for requests to forecast or predict the next months, the next year or two years; weather_forecast is only for the next 16 days or less; set horizon_months; fire_outlook = official one-month WILDFIRE DANGER OUTLOOK for a place/region (next calendar month or next 30 days; set window; NOT a probability of fire; use for 'wildfire danger/risk next month'); fire_danger = fire danger/fire weather index products (current maps only); satellite_scenes = Sentinel scene discovery; datasets = dataset discovery by keyword; "
                    "knowledge = questions about what a dataset/API/unit/limit is (answered from documentation); clarify = something essential is missing or ambiguous; "
                    "unsupported = the request needs a capability that does not exist (burned area, calibrated fire probability, multi-year forecasts)."),
    "parameters": {"type": "object", "properties": {
        "intent": {"type": "string", "enum": INTENTS},
        "place": {"type": "string", "description": "Place name as the user wrote it, INCLUDING any state/country qualifier (e.g. 'Florida, USA', 'Nablus'). Always fill it when the message names a place."},
        "latitude": {"type": "number", "description": "Latitude of the named place. Fill it together with longitude whenever you know where the place is: the city centre for a city, a representative central point for a state, country or large region (Florida, Sahel, Amazon, Siberia)."},
        "longitude": {"type": "number", "description": "Longitude of the named place (see latitude)."},
        "spatial_scope": {"type": "string", "enum": ["point", "area", "global", "none"]},
        "variable": {"type": "string", "enum": TREND_VARS, "description": "air_temperature is 2 m AIR temperature; land_surface_temperature is a different variable."},
        "start_year": {"type": "integer"}, "end_year": {"type": "integer"},
        "start_date": {"type": "string", "description": "YYYY-MM-DD"}, "end_date": {"type": "string", "description": "YYYY-MM-DD"},
        "horizon_days": {"type": "integer", "description": "forecast days 1-16, or fire-detection window 1-5"},
        "horizon_months": {"type": "integer", "description": "forecast_monthly only: months ahead counted from TODAY, 1-24 ('two years' = 24, 'a year' = 12, '90 days' = 3, '60 days' = 2; convert days or weeks to months, rounding up)"},
        "keyword": {"type": "string", "description": "dataset search keyword (datasets intent)"},
        "collection": {"type": "string"}, "max_cloud": {"type": "number"},
        "asks_probability": {"type": "boolean", "description": "true when the user asks for a probability/chance of wildfire"},
        "missing": {"type": "array", "items": {"type": "string", "enum": ["location", "period", "variable"]}},
        "clarification_question": {"type": "string", "description": "ONE short question in the user's language when intent=clarify"},
        "language": {"type": "string", "enum": ["ar", "en"], "description": "language of the user's message"},
        "window": {"type": "string", "enum": ["next_calendar_month", "next_30_days"], "description": "fire_outlook only: the calendar month after the current one, or the next 30 days from today"},
        "refers_to_turn": {"type": "integer", "description": "number of an EARLIER turn (from the conversation) that this message refers to or continues; omit when it stands alone"},
    }, "required": ["intent"]},
}


@dataclass
class Decision:
    intent: str = "knowledge"
    place: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    spatial_scope: str = "none"            # point | area | global | none
    variable: str | None = None
    start_year: int | None = None
    end_year: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    horizon_days: int | None = None
    horizon_months: int | None = None
    refers_to_turn: int | None = None
    window: str | None = None
    source_pref: str | None = None
    keyword: str | None = None
    collection: str | None = None
    max_cloud: float | None = None
    asks_probability: bool = False
    provider: str | None = None
    data_type: str | None = None
    missing: list[str] = field(default_factory=list)
    clarification: str | None = None
    unsupported: str | None = None         # key into UNSUPPORTED texts
    decided_by: str = "router"             # gemini | router | controls | follow_up
    notes: list[str] = field(default_factory=list)   # corrections applied by validation, shown in diagnostics only
    assumptions: list[dict] = field(default_factory=list)   # defaults the system chose for a missing detail; always disclosed in the answer

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v not in (None, [], "", False) or k in ("intent", "decided_by")}

    @property
    def tool(self) -> str | None:
        return INTENT_TOOL.get(self.intent)

    def tool_args(self) -> dict:
        a: dict = {}
        for k in ("place", "latitude", "longitude", "variable", "start_year", "end_year", "start_date", "end_date", "keyword", "collection", "max_cloud"):
            v = getattr(self, k)
            if v not in (None, ""):
                a[k] = v
        if self.intent == "weather_forecast":
            a["mode"] = "forecast"
            if self.horizon_days:
                a["days"] = self.horizon_days
        elif self.intent == "weather_historical":
            a["mode"] = "historical"
        elif self.intent == "fire_detections" and self.horizon_days:
            a["day_range"] = self.horizon_days
        if self.intent == "fire_outlook":
            a["window"] = self.window or "next_calendar_month"
            a.pop("variable", None); a.pop("start_year", None); a.pop("end_year", None)
        elif self.intent == "forecast_monthly":
            a["months"] = self.horizon_months
            a.pop("start_year", None); a.pop("end_year", None)
        elif self.intent != "trend":
            a.pop("variable", None)
            a.pop("start_year", None); a.pop("end_year", None)
        if self.intent in ("trend", "weather_forecast", "weather_historical"):
            a.pop("keyword", None)
        return a

    def finish(self) -> "Decision":
        self.provider, self.data_type = INTENT_PROVIDER.get(self.intent, (None, None))
        return self


def from_tool(tool: str | None, args: dict, decided_by: str) -> Decision:
    """Build the record from a tool name + args (router, controls, follow-up)."""
    args = args or {}
    if tool == "get_weather":
        intent = "weather_historical" if args.get("mode") == "historical" else "weather_forecast"
    else:
        intent = TOOL_INTENT.get(tool or "", "knowledge")
    d = Decision(intent=intent, decided_by=decided_by)
    for k in ("place", "latitude", "longitude", "variable", "start_year", "end_year", "start_date", "end_date", "keyword", "collection", "max_cloud"):
        if args.get(k) not in (None, ""):
            setattr(d, k, args[k])
    d.horizon_days = args.get("days") or args.get("day_range")
    d.horizon_months = args.get("months")
    d.window = args.get("window")
    if d.latitude is not None or d.place:
        d.spatial_scope = "point"
    return d.finish()


def from_model(args: dict) -> Decision:
    """Build the record from `interpret_request` arguments. Unknown/ill-typed values are dropped, never coerced into guesses."""
    args = dict(args or {})
    intent = args.get("intent") if args.get("intent") in INTENTS else "clarify"
    d = Decision(intent=intent, decided_by="claude")
    for k in ("place", "keyword", "collection", "variable", "start_date", "end_date"):
        v = args.get(k)
        if isinstance(v, str) and v.strip():
            setattr(d, k, v.strip())
    for k in ("latitude", "longitude", "max_cloud"):
        try:
            if args.get(k) is not None:
                setattr(d, k, float(args[k]))
        except (TypeError, ValueError):
            pass
    for k in ("start_year", "end_year", "horizon_days", "horizon_months", "refers_to_turn"):
        try:
            if args.get(k) is not None:
                setattr(d, k, int(args[k]))
        except (TypeError, ValueError):
            pass
    d.spatial_scope = args.get("spatial_scope") if args.get("spatial_scope") in ("point", "area", "global", "none") else ("point" if d.place or d.latitude is not None else "none")
    d.asks_probability = bool(args.get("asks_probability"))
    d.window = args.get("window") if args.get("window") in ("next_calendar_month", "next_30_days") else None
    d.missing = [m for m in (args.get("missing") or []) if m in ("location", "period", "variable")]
    d.clarification = (args.get("clarification_question") or "").strip() or None
    if d.variable and d.variable not in VARIABLES:
        d.notes.append(f"unknown variable '{d.variable}' dropped"); d.variable = None
    return d.finish()


# ---- validation ---------------------------------------------------------------------------------------------------------------
@dataclass
class Verdict:
    action: str                     # proceed | clarify | unsupported
    decision: Decision
    text_key: str | None = None     # key into MSG / router.UNSUPPORTED
    params: dict = field(default_factory=dict)


MSG = {
    "need_location": {"ar": "في أي مكان؟ اكتب اسم مدينة أو إحداثيات، أو اختر نقطة على الخريطة.", "en": "Which place? Name a city, give coordinates, or pick a point on the map."},
    "need_period": {"ar": "أي فترة تقصد؟ مثال: «بين 2005 و2025».", "en": "Which period do you mean? For example 'between 2005 and 2025'."},
    "future_trend": {"ar": "لا أستطيع تحليل اتجاه لسنوات لم تحدث بعد. اذكر فترة تنتهي في {y} أو قبله.", "en": "I cannot analyse a trend for years that have not happened. Give a period ending in {y} or earlier."},
    "trend_too_early": {"ar": "بيانات NASA POWER الشهرية متاحة من {y0}. اختر فترة تبدأ من {y0} أو بعده.", "en": "NASA POWER monthly data start in {y0}. Choose a period starting in {y0} or later."},
    "trend_short": {"ar": "اختبار الاتجاه يحتاج فترة من سنتين على الأقل (يُفضّل 10 سنوات أو أكثر). ما الفترة التي تريدها؟", "en": "A trend test needs at least two years (ideally 10+). Which period do you want?"},
    "forecast_horizon": {"ar": "التوقعات التشغيلية المتاحة تصل إلى 16 يومًا فقط. أي أيام تريد؟", "en": "Operational forecasts only reach 16 days. Which days do you want?"},
    "hist_future": {"ar": "هذه الفترة في المستقبل؛ سأعرض التوقع بدلًا من الرصد.", "en": "That period is in the future; showing the forecast instead of observations."},
    "lst_span": {"ar": "مهمة حرارة سطح الأرض محدودة بسنة واحدة. أي فترة (حتى 12 شهرًا) تريد؟", "en": "A land-surface-temperature task is limited to one year here. Which period (up to 12 months) do you want?"},
    "var_unsupported": {"ar": "لا يوجد متغير مدعوم لهذا الطلب. المتغيرات المتاحة للاتجاهات: حرارة الهواء، الهطول، الرطوبة النسبية، سرعة الرياح.", "en": "No supported variable fits this request. Trend variables: air temperature, precipitation, relative humidity, wind speed."},
}


def validate(d: Decision, today: date | None = None, has_location: bool = False, has_period: bool = False, lang: str = "en") -> Verdict:
    """Check the record against real capabilities. May coerce a request to the capability that can answer it (recorded in notes) or ask ONE question."""
    today = today or date.today()
    d.finish()
    if d.intent == "unsupported":
        return Verdict("unsupported", d, d.unsupported or ("fire_probability" if d.asks_probability else "unsupported_generic"))
    if d.intent == "clarify":
        return Verdict("clarify", d, None, {"text": d.clarification})
    if d.intent == "knowledge":
        return Verdict("proceed", d)

    needs_loc = d.intent in ("trend", "weather_forecast", "weather_historical", "fire_detections", "satellite_scenes")
    loc_ok = bool(d.place or d.latitude is not None or has_location)

    # weather asked for a span longer than the historical-weather window: that is a multi-year/long-period climate question -> POWER trend
    if d.intent == "weather_historical" and d.start_date and d.end_date:
        try:
            span = (date.fromisoformat(d.end_date) - date.fromisoformat(d.start_date)).days + 1
        except ValueError:
            return Verdict("clarify", d, "need_period")
        if span > HIST_WEATHER_MAX_DAYS:
            d.intent = "trend"; d.start_year = d.start_year or int(d.start_date[:4]); d.end_year = d.end_year or int(d.end_date[:4])
            d.notes.append(f"period of {span} days exceeds the {HIST_WEATHER_MAX_DAYS}-day historical-weather window; the multi-year trend workflow (NASA POWER) is used instead")
            d.finish()
        elif date.fromisoformat(d.start_date) > today:
            d.intent = "weather_forecast"; d.notes.append("period is in the future: forecast workflow used")
            d.finish()

    if d.intent == "trend":
        if d.variable is None:
            d.variable = "air_temperature"; d.notes.append("variable not stated: air temperature (T2M) assumed")
        elif d.variable not in TREND_VARS:
            if d.variable in VARIABLES and VARIABLES[d.variable].get("alternative"):
                pass   # land_surface_temperature etc.: the trend tool reports the documented limitation itself
        if not loc_ok:
            return Verdict("clarify", d, "need_location")
        if d.start_year is None or d.end_year is None:
            if not has_period:
                # the obvious reading of "is it getting hotter?" is the recent climate record: last 25 COMPLETE years (assumption is shown to the user)
                d.end_year = today.year - 1
                d.start_year = max(TREND_MIN_YEAR, d.end_year - 24)
                d.assumptions.append({"field": "period", "value": f"{d.start_year}-{d.end_year}", "why": "no period given: the last 25 complete years"})
                d.notes.append(f"period assumed: {d.start_year}-{d.end_year}")
        if d.start_year and d.end_year:
            if d.start_year > d.end_year:
                d.start_year, d.end_year = d.end_year, d.start_year
            if d.end_year > today.year:
                return Verdict("clarify", d, "future_trend", {"y": today.year})
            if d.start_year < TREND_MIN_YEAR:
                return Verdict("clarify", d, "trend_too_early", {"y0": TREND_MIN_YEAR})
            if d.end_year - d.start_year < 1:
                return Verdict("clarify", d, "trend_short")
    elif d.intent == "weather_forecast":
        if not loc_ok:
            return Verdict("clarify", d, "need_location")
        if d.horizon_days is not None and not (1 <= d.horizon_days <= FORECAST_MAX_DAYS):
            if d.horizon_days > FORECAST_MAX_DAYS:
                return Verdict("clarify", d, "forecast_horizon")
            d.horizon_days = 1
        if d.start_date:
            try:
                if (date.fromisoformat(d.start_date) - today).days > FORECAST_MAX_DAYS:
                    return Verdict("clarify", d, "forecast_horizon")
            except ValueError:
                pass
    elif d.intent == "weather_historical":
        if not loc_ok:
            return Verdict("clarify", d, "need_location")
        if not (d.start_date and d.end_date) and not has_period:
            return Verdict("clarify", d, "need_period")
    elif d.intent == "fire_detections":
        if not loc_ok:
            return Verdict("clarify", d, "need_location")
        if d.horizon_days is not None:
            d.horizon_days = max(1, min(FIRMS_MAX_DAYS, d.horizon_days))
    elif d.intent == "fire_outlook":
        if d.window is None:
            d.window = "next_calendar_month"
            d.assumptions.append({"field": "window", "value": "next calendar month", "why": "no window given"})
        # the location may be a region NAME that the NIFC service recognises (checked by the tool), so a missing geocode is not decided here
    elif d.intent == "forecast_monthly":
        if not loc_ok:
            return Verdict("clarify", d, "need_location")
        if d.variable not in (None, "air_temperature", "precipitation", "relative_humidity", "wind_speed"):
            return Verdict("clarify", d, "var_unsupported")
        if d.variable is None:
            d.variable = "air_temperature"; d.notes.append("variable not stated: air temperature (T2M) assumed")
        if d.horizon_months is None:
            d.horizon_months = 12
            d.assumptions.append({"field": "horizon", "value": "12", "why": "no horizon given: 12 months"})
        if d.horizon_months > 24:
            return Verdict("unsupported", d, "forecast_too_long")
        if d.horizon_months < 1:
            d.horizon_months = 1
    elif d.intent == "land_surface_temperature":
        if not loc_ok:
            return Verdict("clarify", d, "need_location")
        if d.start_date and d.end_date:
            try:
                span = (date.fromisoformat(d.end_date) - date.fromisoformat(d.start_date)).days + 1
            except ValueError:
                return Verdict("clarify", d, "need_period")
            if span > 366:
                return Verdict("clarify", d, "lst_span")
    elif d.intent in ("satellite_scenes", "ndvi"):
        if not loc_ok:
            return Verdict("clarify", d, "need_location")
    elif d.intent == "datasets":
        if not d.keyword:
            d.keyword = "land surface temperature"; d.notes.append("no keyword stated: generic search")
    return Verdict("proceed", d)


def clarification_text(v: Verdict, lang: str) -> str:
    if v.text_key and v.text_key in MSG:
        return MSG[v.text_key][lang].format(**v.params)
    return (v.params.get("text") or MSG["need_location"][lang]).strip()
