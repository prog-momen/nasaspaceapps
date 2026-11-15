"""Chat orchestration: message + controls + session memory -> structured Decision -> validation -> tool -> short answer + result panel.

Rules enforced here (and tested):
* Typed text and example buttons use the SAME request (message + controls); nothing else decides routing.
* Explicit message > map/date controls > session memory. A conflict between message and controls is NEVER resolved silently.
* Claude first interprets the question into a structured Decision (function `interpret_request`); the backend validates it against real
  capabilities before any tool runs. If Claude is unavailable, the deterministic router is used ONLY when it resolves the request safely,
  and the response says so (model_notice). A model failure is never reported as 'no NASA data'.
* Claude explanations are number-checked against the tool summary; otherwise a labelled template is returned.
* Tool results are never altered by the model; one tool per turn; sessions are isolated and bounded.
"""
from __future__ import annotations

import logging
import re
import time
from datetime import date
from typing import Any

from app.agent.trend_agent import period_is_ambiguous, reconcile_years, unsupported_numbers
from app.chat import decision as D
from app.chat import panel as P
from app.chat import glossary as GL
from app.chat import inline as IN
from app.chat import render, router, tools
from app.chat.location import bbox_center, candidate_place_names, far_apart
from app.chat.sessions import SessionStore
from app.config import get_settings, load_llm_key
from app.llm.base import LLMError
from app.reliability import remaining, request_budget
from app.retrieval.intent import wants_english


METHOD_LINKS = [
    "https://doi.org/10.2307/1907187",
    "https://doi.org/10.1080/01621459.1968.10480934",
    "https://doi.org/10.1016/S0022-1694(97)00125-X",
]


def trend_source_links(outcome: dict) -> list[str]:
    """The exact NASA POWER request behind a trend result (any place), plus the method references."""
    from urllib.parse import urlencode
    from app.analysis.catalog import VARIABLES as AV
    ua = outcome.get("used_args") or {}
    var = AV.get(ua.get("variable") or "air_temperature", {})
    lat, lon = ua.get("latitude"), ua.get("longitude")
    if lat is None or lon is None or not var.get("parameter"):
        return ["https://power.larc.nasa.gov/docs/services/api/temporal/monthly/"] + METHOD_LINKS
    q = urlencode({"parameters": var["parameter"], "community": "AG", "latitude": round(float(lat), 2), "longitude": round(float(lon), 2),
                   "start": ua.get("start_year"), "end": ua.get("end_year"), "format": "JSON"})
    return [f"https://power.larc.nasa.gov/api/temporal/monthly/point?{q}"] + METHOD_LINKS

log = logging.getLogger(__name__)
MAX_MESSAGE = 1500
CONTEXT_TOKENS = 64000           # budget for the conversation the model re-reads at EVERY message (estimated at ~2.5 characters per token to stay safe for Arabic)
CHARS_PER_TOKEN = 2.5
TASK_TOOL = {"trend": ("analyze_trend", {}), "weather_forecast": ("get_weather", {"mode": "forecast"}), "weather_historical": ("get_weather", {"mode": "historical"}),
             "fire_detections": ("get_fire_detections", {}), "fire_danger": ("list_fire_danger", {}), "satellite_scenes": ("search_satellite_scenes", {}),
             "datasets": ("search_earth_datasets", {}), "land_surface_temperature": ("get_lst", {}), "ndvi": ("get_ndvi", {}), "forecast_monthly": ("forecast_monthly", {}), "fire_outlook": ("forecast_fire_danger", {})}

INTERPRET_SYSTEM = """You are the request interpreter of EarthTrend Explorer (NASA / Earth-observation data). Call `interpret_request` exactly once.
- Understand the user's question and the CONTEXT (defaults from controls and earlier turns), then record intent, place, variable and period.
- A multi-year question ("between 2005 and 2025", "since 1990", "has it risen over the years") is intent=trend (NASA POWER), NEVER weather_historical.
- weather_forecast = coming days (<=16); weather_historical = one past period of at most a year; fire_detections = recent satellite fire detections (<=5 days).
- BE HELPFUL, INFER THE OBVIOUS. Users write casually (Arabic dialects, short, no dates). Pick the intent a sensible person would mean:
  "getting hotter/colder/drier, less rain, warming" -> trend (leave the years empty: the backend uses the last 25 complete years and says so);
  "weather/rain/temperature (now, today, tomorrow, this week)" -> weather_forecast; "vegetation/greenery/plants/crops" -> ndvi; "ground/surface heat" -> land_surface_temperature;
  "any fires near X / is there a fire" -> fire_detections; "fire risk" -> fire_danger. A place from CONTEXT or the recent turns is reused; a follow-up like "and Amman?" keeps the previous intent.
- READ THE WHOLE MESSAGE and fill every field it implies: intent, place, variable ("temp" = air_temperature, "rain" = precipitation), and the period or horizon.
- PLACE: if the message names a place, ALWAYS fill `place` with the name and its qualifier ("Florida in USA" -> "Florida, USA") AND fill latitude/longitude from your own geographic knowledge
  (city centre, or a representative central point for a state, country or region). A named place is never a reason to ask "which place?". Ask only when NO place is named anywhere.
- HORIZON: "next 2 years" -> horizon_months=24; "next 90 days" -> 3; "next year" -> 12. Forecast horizons are counted from today.
- Copy a PLACE the user wrote or CONTEXT supplies; never invent one. Never invent numbers. Use intent=clarify only when something essential cannot be inferred
  (no place anywhere in the message, CONTEXT or recent turns) - ONE short question in the user's language, never a list of questions.
- Questions about what a dataset/API/unit/limit is -> intent=knowledge. Burned area, calibrated fire probability, multi-year forecasts -> intent=unsupported
  (a question about the chance of a wildfire: intent=fire_danger with asks_probability=true, since only a danger INDEX exists).
- Set language to the language of the user's message, not of the interface.
- CONVERSATION SO FAR lists every earlier turn (numbered) with what was understood and the key result. If the new message refers to an earlier one ("the first question", "like before but for Amman",
  "that result", "compare with Nablus", "and the other one") resolve it from the conversation: copy that turn's intent/variable/period and change only what the user changed; set refers_to_turn."""
WEB_SYSTEM = """You explain ONE concept to an ordinary, non-expert user in {language}. Plain words, at most 8 short sentences, one tiny HYPOTHETICAL example clearly labelled as hypothetical.
Use web search only to confirm the definition. NEVER state measurements, statistics, dates or facts about any real place, dataset, event or year, and never answer a request for data:
if the user is really asking for data, say that numbers come only from the app's data tools. Format: `## title`, then a callout line `> [!info] the key meaning`, then a short paragraph."""
EXPLAIN_SYSTEM = """You write the chat reply for a data result, in {language}. Use ONLY values in TOOL_RESULT.summary / limitations; never compute, estimate or add numbers.
Length: proportional to the question. A simple question gets 1-3 sentences: the conclusion in **bold**, the essential number(s) with units, and the citation marker [1].
Add at most one short list when several values are needed. Put method details elsewhere: the side panel already shows full statistics, charts and provenance.
Copy every number EXACTLY as it appears in TOOL_RESULT (same digits, no rounding, no unit conversion, no percentages or differences you derive) and write dates exactly as the ISO strings given (YYYY-MM-DD), never as month names or bare day numbers.
Write for an ORDINARY reader, not an expert: plain short sentences; if a technical term is unavoidable (anomaly, p-value, baseline, MAE, reanalysis ...) add a few plain words in brackets the first time. The user can ask what any term means.
Mention the place, period/horizon and the dataset only when needed to be correct. Use at most two emojis from: 🌡️ 🌧️ 🔥 🛰️ 💨 💧.
Capability rules: forecast = operational forecast, not observation; forecast_monthly = STATISTICAL monthly forecast (name the method and say whether it was validated against a baseline; give the typical backtest error in physical units, never a percentage for temperature; state the data cutoff; NOT a weather forecast for a day; never present baseline-only values as a validated model); historical weather = reanalysis, not station data; fire detections = satellite thermal anomalies, NOT
confirmed incidents, burned area or incident counts (zero detections does not prove no fire); fire danger = index, NOT a probability; scenes = discovery only;
trend = historical description, not a forecast, no causal claim. If significant=false say exactly "{not_sig}" and never "no change". No raw field names, no JSON, no HTML.
For forecast_fire_danger (official one-month wildfire danger OUTLOOK): state the category per month exactly as in TOOL_RESULT (above/near/below normal, relative to normal; area shares if mixed), the source and issue label, and say it is NOT a probability of fire and NOT a daily forecast. Observed FIRMS detections are context only, never a forecast. Keep it to 3 sentences plus the mandatory sentence 'This is an official model outlook; local forecast skill has not been verified by this application.' (Arabic: 'هذا توقع رسمي مبني على نموذج؛ ولم يتحقق هذا التطبيق من مهارة التوقع محليًا.').
For forecast_monthly: AT MOST 4 sentences and no list of all months (the full table and chart are in the side panel): the covered months, one or two example values with their interval, the validation status with the typical backtest error, and the main limitation.
FORMAT (the UI renders this Markdown): start with a short `## ` title; put the ONE key conclusion in a callout line `> [!key] ...` (use `> [!warn] ...` for the main limitation or when no skill was shown, `> [!good]`/`> [!hot]`/`> [!cold]` only when the data justify it);
then 1-3 short paragraphs; write `[[inline]]` on its own line where the chart/table the user needs should appear (right after the callout); finish with at most two small notes, each on its own line starting with `^ `.
Do not write tables or lists of many values yourself. Plain Markdown only (bold, short lists)."""


def _is_arabic(text: str) -> bool:
    letters = re.findall(r"[A-Za-z؀-ۿ]", text)
    return bool(letters) and sum(1 for c in letters if "؀" <= c <= "ۿ") / len(letters) > 0.5


def detect_language(msg: str, ui: str | None) -> str:
    """Language of the user's MESSAGE; the UI language is only the fallback for messages with no clear letters (e.g. '2005 2025')."""
    if wants_english(msg):
        return "en"
    letters = re.findall(r"[A-Za-z؀-ۿ]", msg)
    if len(letters) < 3:
        return ui if ui in ("ar", "en") else "en"
    return "ar" if _is_arabic(msg) else "en"


def T_(lang, ar, en):
    return ar if lang == "ar" else en


class ChatAgent:
    def __init__(self, svc, store: SessionStore | None = None, tool_runner=None):
        self.svc, self.store = svc, store or SessionStore()
        self.run_tool = tool_runner or tools.execute

    # ------------------------------------------------------------------------------------------------
    def reset(self, sid: str) -> bool:
        s = self.store.get(sid, create=False)
        if s:
            s.reset()
            return True
        return False

    def history(self, sid: str) -> list[dict]:
        s = self.store.get(sid, create=False)
        return s.history if s else []

    # ------------------------------------------------------------------------------------------------
    def handle(self, req: dict) -> dict:
        t0 = time.monotonic()
        msg = (req.get("message") or "").strip()
        sess = self.store.get(req.get("session_id"))
        base = {"session_id": sess.id, "tools": [], "artifacts": [], "citations": [], "warnings": [], "conflict": None, "model": None, "selected_by": None,
                "fallback_reason": None, "answer_source": "none", "resolved": {}, "raw_result": None}
        if not msg:
            return {**base, "status": "invalid_request", "language": "en", "answer": "Message is empty.", "timing": {"total_ms": 0}}
        if len(msg) > MAX_MESSAGE:
            return {**base, "status": "invalid_request", "language": "en", "answer": f"Message is longer than {MAX_MESSAGE} characters.", "timing": {"total_ms": 0}}
        if not sess.lock.acquire(blocking=False):
            return {**base, "status": "busy", "language": "en", "answer": "The previous message in this conversation is still being processed.", "timing": {"total_ms": 0}}
        try:
            with request_budget(get_settings().request_total_deadline_s):
                out = self._handle(sess, msg, req, base)
        except Exception as e:                                   # never leak internals; keep the UI recoverable
            log.exception("chat turn failed")
            out = {**base, "status": "error", "language": "en", "answer": f"Internal error ({type(e).__name__}). The conversation is intact; try again.", "warnings": [type(e).__name__]}
        finally:
            sess.lock.release()
        out["timing"] = {"total_ms": int((time.monotonic() - t0) * 1000)}
        return out

    # ------------------------------------------------------------------------------------------------
    def _handle(self, sess, msg: str, req: dict, base: dict) -> dict:
        ctl = req.get("controls") or {}
        ui_lang = ctl.get("language") if ctl.get("language") in ("ar", "en") else None
        lang = detect_language(msg, ui_lang)
        answer_mode = ctl.get("answer_mode") or "auto"
        choice = req.get("conflict_choice")
        today = date.today()
        out = {**base, "language": lang, "ui_language": ui_lang}

        # --- 1. what the message says explicitly, what the controls say, what the session remembers --------------------------
        msg_place = router.explicit_place(msg)
        msg_period = router.parse_period(msg, today)
        ctl_loc = None
        if ctl.get("point"):
            ctl_loc = {"name": f"map point ({ctl['point']['lat']:.4f}, {ctl['point']['lon']:.4f})", "latitude": float(ctl["point"]["lat"]), "longitude": float(ctl["point"]["lon"]), "source": "map control"}
        elif ctl.get("bbox"):
            la, lo = bbox_center([float(x) for x in ctl["bbox"]])
            ctl_loc = {"name": "map box", "latitude": la, "longitude": lo, "bbox": [float(x) for x in ctl["bbox"]], "source": "map control"}
        ctl_period = {"start": ctl["start"], "end": ctl["end"], "kind": "controls"} if ctl.get("start") and ctl.get("end") else None
        if ctl_period:
            ctl_period.update(start_year=int(ctl["start"][:4]), end_year=int(ctl["end"][:4]))

        conflicts = []
        if msg_place and ctl_loc and far_apart(msg_place, ctl_loc) and choice is None:
            conflicts.append({"field": "location", "message_value": msg_place["name"], "controls_value": ctl_loc["name"]})
        if msg_period and ctl_period and choice is None and msg_period["kind"] not in ("today", "tomorrow", "next_days") and \
                (msg_period["start"][:10] != ctl_period["start"] or msg_period["end"][:10] != ctl_period["end"]):
            conflicts.append({"field": "period", "message_value": f"{msg_period['start']} .. {msg_period['end']}", "controls_value": f"{ctl_period['start']} .. {ctl_period['end']}"})
        if conflicts:
            ask = {"ar": "الرسالة تذكر قيمًا مختلفة عن إعدادات التحليل. أيهما تريد استخدامه؟ لن أحلل مكانًا أو فترة مختلفة دون اختيارك.",
                   "en": "The message names values that differ from the analysis settings. Which should I use? I will not silently analyse a different place or period."}[lang]
            sess.add("user", msg)
            return self._finish_text(out, "conflict", ask, "none", conflict={"items": conflicts, "choices": ["message", "controls"]})

        use_msg = choice != "controls"
        use_ctl = choice != "message"
        defaults = {"location": (msg_place if use_msg and msg_place else None) or (ctl_loc if use_ctl and ctl_loc else None) or sess.memory.get("location"),
                    "period": (msg_period if use_msg and msg_period else None) or (ctl_period if use_ctl and ctl_period else None) or sess.memory.get("period"),
                    "variable": ctl.get("variable") if use_ctl and ctl.get("variable") not in (None, "", "auto") else sess.memory.get("variable")}
        if msg_place and use_msg:                                    # a follow-up that names a NEW place must not inherit the old place
            defaults["location"] = msg_place
        defaults["lang"] = lang
        defaults["message"] = msg                                    # tools may recognise official region names (e.g. NIFC GACC) in the user's own words                                      # place names from the geocoder come back in the user's language

        # --- 2. interpret: structured Decision (Claude first; deterministic router as a labelled fallback) ---------------------
        llm_allowed = answer_mode != "template" and bool(load_llm_key())
        task = ctl.get("task") or "auto"
        provider_pref = ctl.get("provider") or "auto"
        dec, first_model, selected_by = None, None, None
        if task != "auto":
            if task == "rag":
                dec = D.Decision(intent="knowledge", decided_by="controls").finish()
            else:
                tname, targs = TASK_TOOL[task]
                dec = D.from_tool(tname, dict(targs), "controls")
                if task == "datasets":
                    dec.keyword = re.sub(r"\s+", " ", msg)[:60]
            selected_by = "controls"
        else:
            rp = router.route(msg, sess.memory, today)
            if rp.unsupported:
                sess.add("user", msg)
                txt = router.UNSUPPORTED[rp.unsupported][lang]
                sess.add("assistant", txt)
                return self._finish_text(out, "unsupported", txt, "template", selected_by="router", decision=D.Decision(intent="unsupported", unsupported=rp.unsupported, decided_by="router").finish().to_dict())
            if llm_allowed:
                try:
                    gdec, text_only, first_model = self._llm_interpret(sess, msg, defaults, ctl, lang)
                    if gdec is not None:
                        dec, selected_by = gdec, "llm_tool_use"
                        if dec.intent == "knowledge" and rp.tool == "analyze_trend" and msg_place and rp.args.get("start_year"):
                            dec, selected_by = D.from_tool(rp.tool, rp.args, "router"), "router"          # explicit place + multi-year period: the router is certain
                    elif text_only and re.search(r"[?؟]", text_only):
                        sess.add("user", msg); sess.add("assistant", text_only)
                        return self._finish_text(out, "clarification", text_only, "claude", selected_by="llm_tool_use", model=first_model)
                except LLMError as e:
                    out["fallback_reason"] = e.kind
                    out["warnings"].append(f"Claude interpretation unavailable ({e.kind}); deterministic router used.")
                    llm_allowed = False
            if dec is not None and rp.tool == "forecast_fire_danger" and dec.intent in ("fire_danger", "fire_detections", "knowledge", "forecast_monthly", "weather_forecast"):
                p_, keep = dec.asks_probability, {k: getattr(dec, k, None) for k in ("place", "latitude", "longitude", "bbox", "country")}
                dec, selected_by = D.from_tool(rp.tool, dict(rp.args), "router"), "router"
                for k, v in keep.items():
                    if v is not None and hasattr(dec, k):
                        setattr(dec, k, v)                                                  # the model's place reading is kept; only the tool is fixed          # an explicit wildfire-danger + next-month/30-day question is certain: the official outlook, not an index map
                dec.asks_probability = p_ or "asks_probability" in rp.flags
            elif dec is not None and dec.intent == "fire_outlook" and "asks_probability" in rp.flags:
                dec.asks_probability = True
            if dec is None:
                dec, selected_by = D.from_tool(rp.tool, dict(rp.args), "router"), "router"
                dec.asks_probability = "asks_probability" in rp.flags
                # follow-up: a short message that only names a new place/period re-uses the previous tool (never a stale place/period)
                if dec.intent == "knowledge" and sess.memory.get("last_tool") and (msg_place or msg_period) and len(msg.split()) <= 8 and not router.RX["lst"].search(msg):
                    dec, selected_by = D.from_tool(sess.memory["last_tool"], {}, "follow_up"), "follow_up"
                    if sess.memory.get("variable") and dec.intent == "trend":
                        dec.variable = sess.memory["variable"]
                    out["warnings"].append(f"Follow-up: re-using the previous analysis type ({dec.intent}) with the new place/period from your message.")
        self._enforce_explicit(dec, msg, msg_place, msg_period, use_msg)
        # the model left the place empty although the message names one ("... in Florida in USA"): take the name from the user's own words instead of asking
        if use_msg and not msg_place and not dec.place and dec.latitude is None and not defaults.get("location") and dec.intent not in ("knowledge", "datasets", "clarify", "unsupported"):
            names = candidate_place_names(msg)
            if names:
                dec.place, dec.spatial_scope = names[0], "point"
                dec.notes.append(f"place '{names[0]}' taken from the message text")

        # --- 3. validate against real capabilities BEFORE any tool runs -----------------------------------------------------
        per = defaults.get("period") or {}
        has_period = bool(per.get("start_year")) if dec.intent == "trend" else bool(per.get("start"))
        verdict = D.validate(dec, today, has_location=bool(defaults.get("location")), has_period=has_period, lang=lang)
        dec = verdict.decision
        out["decision"] = dec.to_dict()
        out["selected_by"] = selected_by
        if verdict.action == "unsupported":
            sess.add("user", msg)
            txt = router.UNSUPPORTED.get(verdict.text_key, router.UNSUPPORTED["fire_probability"])[lang]
            sess.add("assistant", txt)
            return self._finish_text(out, "unsupported", txt, "template", selected_by=selected_by)
        if verdict.action == "clarify":
            txt = D.clarification_text(verdict, lang)
            sess.add("user", msg); sess.add("assistant", txt)
            return self._finish_text(out, "clarification", txt, "claude" if dec.decided_by == "claude" and verdict.text_key is None else "template", selected_by=selected_by, model=first_model)

        plan_name, plan_args = dec.tool, dec.tool_args()
        if dec.intent == "knowledge":
            return self._rag(sess, msg, lang, out, llm_allowed and answer_mode != "template", selected_by or "router")

        # --- 4. trend arguments: explicit years in the question are authoritative; ambiguity is never guessed ----------------
        if plan_name == "analyze_trend":
            if period_is_ambiguous(msg) and dec.decided_by != "controls":
                txt = {"ar": "السؤال يتضمن أكثر من فترة زمنية أو سنوات غير واضحة. حدّد فترة واحدة (مثال: بين 2005 و2025).",
                       "en": "The question names more than one period or unclear years. Please give exactly one period (e.g. between 2005 and 2025)."}[lang]
                sess.add("user", msg); sess.add("assistant", txt)
                out["fallback_reason"] = out["fallback_reason"] or "ambiguous_period"
                return self._finish_text(out, "clarification", txt, "template", selected_by=selected_by)
            plan_args, notes = reconcile_years(msg, plan_args)
            out["warnings"].extend(notes)
            if defaults.get("variable") and not plan_args.get("variable"):
                plan_args["variable"] = defaults["variable"]
            if not plan_args.get("variable"):
                plan_args["variable"] = router.infer_variable(msg) or "air_temperature"
        if provider_pref not in ("auto", None) and plan_name == "search_earth_datasets":
            plan_args["catalog"] = "gee" if provider_pref == "gee" else "cmr"
        if plan_name == "search_earth_datasets" and re.search(r"earth ?engine|gee|ايرث|إيرث", msg, re.I):
            plan_args["catalog"] = "gee"

        # --- 5. conflict check on the location the TOOL would use (covers names resolved from free text / by the model) -------
        if ctl_loc and use_ctl and choice is None and (plan_args.get("place") or plan_args.get("latitude") is not None):
            loc, _ = tools._resolve_location(plan_args, {})
            if loc and far_apart(loc, ctl_loc):
                ask = {"ar": "الرسالة تشير إلى موقع مختلف عن الموقع المحدد على الخريطة. أيهما أستخدم؟", "en": "The message refers to a different place than the one selected on the map. Which should I use?"}[lang]
                sess.add("user", msg)
                return self._finish_text(out, "conflict", ask, "none", conflict={"items": [{"field": "location", "message_value": loc["name"], "controls_value": ctl_loc["name"]}], "choices": ["message", "controls"]})
        if choice == "controls":
            for k in ("place", "latitude", "longitude", "bbox", "start_date", "end_date", "start_year", "end_year"):
                plan_args.pop(k, None)

        # --- 6. run the tool ----------------------------------------------------------------------------------------------
        outcome = self.run_tool(plan_name, plan_args, defaults)
        res = outcome["result"]
        tool_row = {"name": plan_name, "args": outcome.get("used_args") or plan_args, "status": outcome["status"], "reason_code": res.get("reason_code"), "provider": res.get("provider"),
                    "product": res.get("product"), "live": res.get("live", (res.get("source") or {}).get("cache_hit") is False if plan_name == "analyze_trend" else None),
                    "cache": res.get("cache", "hit" if (res.get("source") or {}).get("cache_hit") else None), "retrieved_at": res.get("retrieved_at") or (res.get("source") or {}).get("retrieved_at"),
                    "duration_ms": outcome.get("duration_ms"), "selected_by": selected_by, "capability": res.get("capability")}
        if plan_name == "analyze_trend" and res.get("status") == "ok":
            tool_row.update(provider="NASA POWER", product=f"monthly {res['variable']['id']}", live=not res["source"].get("cache_hit"), cache="hit" if res["source"].get("cache_hit") else "miss", retrieved_at=res["source"].get("retrieved_at"))
        out["tools"] = [tool_row]
        out["warnings"].extend(outcome.get("notes") or [])
        out["resolved"] = {"location": outcome.get("location"), "period": outcome.get("period"), "variable": (outcome.get("used_args") or {}).get("variable")}
        out["raw_result"] = {k: v for k, v in res.items() if k not in ("artifacts",)}
        out["limitations"] = (res.get("limitations") or [])[:6]
        out["attribution"] = res.get("attribution")
        out["source_links"] = (res.get("source_links") or [])[:6]
        if plan_name == "analyze_trend" and not out["source_links"]:
            out["source_links"] = trend_source_links(outcome)

        # --- 7. answer ---------------------------------------------------------------------------------------------------------
        rc = res.get("reason_code")
        ok_status = outcome["status"] == "ok" or (outcome["status"] == "no_data" and plan_name == "get_fire_detections" and rc == "ZERO_DETECTIONS")
        text, source = None, "template"
        if llm_allowed and ok_status and not dec.asks_probability:
            try:
                text = self._llm_explain(msg, plan_name, outcome, lang, first_model, defaults)
                source = "claude" if text else "template"
                if not text:
                    out["fallback_reason"] = "explanation_validation"
                    out["warnings"].append("Claude explanation rejected by the number/wording check; deterministic template used.")
            except LLMError as e:
                out["fallback_reason"] = out["fallback_reason"] or e.kind
                out["warnings"].append(f"Claude unavailable for the explanation ({e.kind}); deterministic template used.")
        if not text:
            text = render.render(plan_name, outcome, lang, asks_probability=dec.asks_probability)
            if answer_mode == "template" and not out["fallback_reason"]:
                out["fallback_reason"] = "template_requested"
        if plan_name == "forecast_fire_danger" and ok_status:
            stmt = T_(lang, "هذا توقع رسمي مبني على نموذج؛ ولم يتحقق هذا التطبيق من مهارة التوقع محليًا.", "This is an official model outlook; local forecast skill has not been verified by this application.")
            if stmt not in text:
                text = text.rstrip() + chr(10) + chr(10) + "^ " + stmt                         # the skill statement is mandatory whatever wrote the answer
            if dec.asks_probability and not re.search(r"not a probability|ليس احتمال|لا يوجد احتمال|no (?:numerical )?probability", text, re.I):
                text = text.rstrip() + chr(10) + "^ " + T_(lang, "التصنيف رسمي نسبةً إلى المعتاد وليس احتمالًا لوقوع حريق.", "The category is relative to normal; it is not a probability of fire.")
        status = "ok" if ok_status else outcome["status"]
        if status == "invalid_request" and outcome["summary"].get("needs"):
            status = "clarification"
        out.update(answer=text, answer_source=source, model=self._model_used() if source == "claude" else None, status=status)
        if dec.assumptions and ok_status:
            a0 = dec.assumptions[0]
            note = T_(lang, f"ℹ️ افترضتُ الفترة {a0['value'].replace('-', '–')} (آخر 25 سنة كاملة). اذكر فترة أخرى إن أردت.", f"ℹ️ Assumed period {a0['value'].replace('-', '–')} (last 25 complete years). Name another period if you want.")
            out["assumptions"] = dec.assumptions
            text = text.rstrip() + chr(10) + note
            out["answer"] = text
        out["citations"] = self._data_citations(plan_name, res, outcome)
        out["outcome"] = P.classify_outcome(status, rc, out["fallback_reason"], True)
        if dec.asks_probability and ok_status and plan_name != "forecast_fire_danger" and outcome["summary"].get("usgs_status") != "ok":
            out["outcome"] = "insufficient_evidence"                  # asked for a probability; only danger-product listings exist, no value for this place
        out["panel"] = P.build_panel(plan_name, outcome, lang, dec.to_dict())
        inl = IN.build_inline(plan_name, outcome, msg, lang) if ok_status else []
        out["inline"] = inl
        out["panel"]["artifacts"] = IN.split_panel_artifacts(out["panel"]["artifacts"], inl)         # the requested table/chart lives in the chat; the rest stays in the side panel
        if ok_status and source == "claude" and "[!" not in text:
            out["answer"] = text = render.layout(plan_name, text, lang, outcome)
        out["panel"]["status"] = "ok" if ok_status else (res.get("status") or "error")
        out["map"] = P.build_map(plan_name, outcome, dec.to_dict(), ok_status, lang)
        self._notice(out)
        # --- 8. memory: only what this turn actually used ---------------------------------------------------------------
        if ok_status:
            if outcome.get("location"):
                sess.memory["location"] = outcome["location"]
            if plan_name == "analyze_trend" and outcome.get("period"):
                sess.memory["period"] = {**outcome["period"], "start": f"{outcome['period']['start_year']}-01-01", "end": f"{outcome['period']['end_year']}-12-31", "kind": "years"}
                sess.memory["variable"] = (outcome.get("used_args") or {}).get("variable")
            elif outcome.get("period") and outcome["period"].get("start"):
                sess.memory["period"] = {"start": outcome["period"]["start"], "end": outcome["period"].get("end") or outcome["period"]["start"], "kind": "memory"}
            sess.memory["last_tool"] = plan_name
        sess.add("user", msg)
        facts = {k: v for k, v in (outcome.get("summary") or {}).items() if isinstance(v, (int, float, str, bool)) and k not in ("status", "interpretation")}
        sess.add("assistant", text, {"tool": plan_name, "status": out["status"], "decision": dec.to_dict(), "facts": dict(list(facts.items())[:10])})
        return out

    # ------------------------------------------------------------------------------------------------
    def _finish_text(self, out: dict, status: str, text: str, source: str, selected_by: str | None = None, model: str | None = None, conflict: dict | None = None, decision: dict | None = None) -> dict:
        out = {**out, "status": status, "answer": text, "answer_source": source, "model": model, "conflict": conflict}
        if selected_by:
            out["selected_by"] = selected_by
        if decision:
            out["decision"] = decision
        out["outcome"] = P.classify_outcome(status, None, out.get("fallback_reason"), False)
        out["panel"] = {"kind": "none", "status": status, "title": "", "metrics": [], "artifacts": [], "source": {}, "limitations": [], "details": {}}
        out["map"] = None
        self._notice(out)
        return out

    @staticmethod
    def _notice(out: dict) -> None:
        """Claude availability is shown as a small notice, never inside the answer and never as 'no data'."""
        k = out.get("fallback_reason")
        if k in P.QUOTA_KINDS:
            ar = out.get("language") == "ar"
            what = {"quota": ("بلغ حدّ معدل/حصة Claude Haiku مؤقتًا", "Claude Haiku rate limit or quota reached"), "billing": ("رصيد حساب Anthropic غير كافٍ", "Anthropic account credit is insufficient"),
                    "model_not_found": ("النموذج claude-haiku-5-5 غير متاح لهذا الحساب", "claude-haiku-5-5 is not available to this account"),
                    "model_not_allowed": ("نموذج غير مسموح؛ يُسمح فقط بـ claude-haiku-5-5", "model not allowed; only claude-haiku-5-5 may be used"),
                    "budget": ("بلغ الحد المحلي اليومي لـ Claude", "Local daily Claude cap reached")}.get(k, ("Claude غير متاح مؤقتًا", "Claude is temporarily unavailable"))
            out["model_notice"] = {"kind": k, "text": what[0 if ar else 1] + (" — استُخدم مسار حتمي مُعلَّم." if ar else " — a labelled deterministic path was used.")}

    @staticmethod
    def _enforce_explicit(dec: "D.Decision", msg: str, msg_place: dict | None, msg_period: dict | None, use_msg: bool) -> None:
        """Parameters the user wrote win over anything the model or defaults supplied."""
        if not use_msg:
            return
        if msg_place and dec.intent not in ("knowledge", "datasets", "clarify", "unsupported"):
            if msg_place.get("source") == "coordinates in message":
                dec.latitude, dec.longitude, dec.place = msg_place["latitude"], msg_place["longitude"], None
            else:
                dec.place, dec.latitude, dec.longitude = msg_place["name"], None, None
            dec.spatial_scope = "point"
        if not msg_place and dec.decided_by in ("router", "follow_up") and not dec.place and dec.latitude is None and dec.intent in ("trend", "weather_forecast", "weather_historical", "fire_detections", "satellite_scenes", "land_surface_temperature", "ndvi"):
            names = candidate_place_names(msg)                       # a place the user wrote that is not in the gazetteer: geocoded (and disambiguated) by the tool
            if names:
                dec.place, dec.spatial_scope = names[0], "point"
        if dec.intent == "trend":
            v = router.infer_variable(msg)
            if v and v != dec.variable:
                if dec.variable:
                    dec.notes.append(f"variable corrected from {dec.variable} to {v} (explicit in the question)")
                dec.variable = v
            if msg_period and msg_period.get("kind") in ("years", "since_year"):
                dec.start_year, dec.end_year = msg_period["start_year"], msg_period["end_year"]
        elif dec.intent in ("weather_historical", "fire_detections", "land_surface_temperature") and msg_period and msg_period.get("kind") in ("date", "dates", "yesterday", "past_days", "year", "years"):
            if dec.intent in ("weather_historical", "land_surface_temperature"):
                dec.start_date, dec.end_date = msg_period["start"], msg_period["end"]
            elif msg_period["kind"] in ("date", "dates"):
                dec.start_date = msg_period["start"]
        elif dec.intent == "weather_forecast" and msg_period and msg_period.get("days") and not dec.horizon_days:
            dec.horizon_days = min(16, int(msg_period["days"]))

    @staticmethod
    def _data_citations(tool: str, res: dict, outcome: dict) -> list[dict]:
        if res.get("status") not in ("ok", "no_data"):
            return []
        src = res.get("source") or {}
        if tool == "forecast_monthly" and res.get("status") == "ok":
            d = res["data"]; sm = d["summary"]
            return [{"index": 1, "kind": "data", "title": f"NASA POWER monthly {d['provenance']['parameter']} to {sm['cutoff']['data_cutoff_month'][:7]} + model run: {sm['selected_model'] if sm['overall_validation'] != 'baseline_only' else sm['baseline']}",
                     "url": "https://power.larc.nasa.gov/docs/services/api/temporal/monthly/", "provider": "NASA POWER + statistical model", "text": f"Data retrieved {d['provenance'].get('retrieved_at')}; history {d['provenance'].get('data_period')}; values sha256 {d['provenance'].get('values_sha256')}; evaluation depth {res['quality'].get('evaluation_depth')}. Papers are method references only.",
                     "retrieved_at": d["provenance"].get("retrieved_at"), "cited": True}]
        prov = "NASA POWER" if tool == "analyze_trend" else res.get("provider")
        prod = f"monthly {res['variable']['id']}" if tool == "analyze_trend" and res.get("variable") else res.get("product")
        links = res.get("source_links") or (trend_source_links({"used_args": {"variable": "air_temperature"}}) if tool == "analyze_trend" else [])
        when = res.get("retrieved_at") or src.get("retrieved_at")
        return [{"index": 1, "kind": "data", "title": f"{prov} — {prod}" if prod else prov, "url": links[0] if links else None, "provider": prov,
                 "text": f"Tool result retrieved {when}." if when else "Tool result.", "retrieved_at": when, "cited": True}]

    # ------------------------------------------------------------------------------------------------
    def _llm(self):
        return self.svc._llm if self.svc._llm is not None else self.svc.llm

    def _model_used(self):
        try:
            return getattr(self._llm(), "last_model_used", None) or self._llm().model
        except Exception:
            return None

    def _context_text(self, sess, defaults: dict, ctl: dict) -> str:
        parts = []
        if defaults.get("location"):
            l = defaults["location"]; parts.append(f"default location: {l['name']} ({l['latitude']:.4f}, {l['longitude']:.4f})")
        if defaults.get("period"):
            p = defaults["period"]; parts.append(f"default period: {p.get('start')} .. {p.get('end')}")
        if defaults.get("variable"):
            parts.append(f"default variable: {defaults['variable']}")
        parts.append(f"today: {date.today().isoformat()}; interface language: {ctl.get('language') or 'unknown'} (answer language follows the user's message)")
        return "CONTEXT: " + "; ".join(parts) + self._conversation_block(sess)

    @staticmethod
    def _turn_facts(meta: dict) -> str:
        d = meta.get("decision") or {}
        bits = [f"intent={d['intent']}" for _ in [0] if d.get("intent")]
        for k in ("place", "variable", "start_year", "end_year", "start_date", "end_date", "horizon_months"):
            if d.get(k) not in (None, ""):
                bits.append(f"{k}={d[k]}")
        f = meta.get("facts")
        if f:
            bits.append("result: " + ", ".join(f"{k}={v}" for k, v in list(f.items())[:10]))
        return "; ".join(bits)

    def _conversation_block(self, sess) -> str:
        """The WHOLE conversation (oldest -> newest) within CONTEXT_TOKENS, numbered, with each turn's understood request and key result facts. If it does not fit, the
        oldest MIDDLE turns are dropped (the first two and the most recent turns are always kept) and the omission is stated."""
        hist = sess.history
        turns = []
        for i in range(0, len(hist) - 1, 2):
            u, a = hist[i], hist[i + 1]
            facts = self._turn_facts(a.get("meta") or {})
            turns.append(f"[turn {i // 2 + 1}] user: {u['text'][:900]}\n  assistant: {a['text'][:1200]}" + (f"\n  (understood: {facts})" if facts else ""))
        if not turns:
            return ""
        budget = int(CONTEXT_TOKENS * CHARS_PER_TOKEN)
        total = sum(len(t) for t in turns)
        omitted = 0
        keep_head = 2
        while total > budget and len(turns) > keep_head + 2:
            total -= len(turns.pop(keep_head)); omitted += 1
        note = f"\n[... {omitted} earlier turn(s) omitted to fit the context budget ...]" if omitted else ""
        head, tail = turns[:keep_head], turns[keep_head:]
        return "\nCONVERSATION SO FAR (oldest first):\n" + "\n".join(head) + note + ("\n" + "\n".join(tail) if tail else "")

    def _llm_interpret(self, sess, msg: str, defaults: dict, ctl: dict, lang: str):
        llm = self._llm()
        user = self._context_text(sess, defaults, ctl) + "\n\nUSER MESSAGE:\n" + msg
        # real Tool Use: the model MUST answer by calling `interpret_request` (forced tool choice); the backend validates the arguments before any data tool runs
        resp = llm.generate_raw(user, INTERPRET_SYSTEM, tools=[D.DECISION_DECLARATION], tool_choice={"type": "tool", "name": D.DECISION_DECLARATION["name"]},
                                total_deadline_s=remaining(get_settings().llm_total_deadline_s))
        fcs = list(getattr(resp, "function_calls", None) or [])
        model = getattr(llm, "last_model_used", None)
        if not fcs:
            return None, (resp.text or "").strip(), model
        fc = fcs[0]
        if fc.name != D.DECISION_DECLARATION["name"] or not isinstance(fc.args, dict):
            raise LLMError("Model returned an unknown function", 502, "tool_protocol")
        return D.from_model(dict(fc.args)), None, model

    def _llm_explain(self, msg: str, tool: str, outcome: dict, lang: str, pin_model: str | None, defaults: dict) -> str | None:
        llm = self._llm()
        res = outcome["result"]
        compact = {"tool": tool, "status": outcome["status"], "provider": res.get("provider"), "product": res.get("product"), "live_call": res.get("live", (res.get("source") or {}).get("cache_hit") is False if tool == "analyze_trend" else None),
                   "cache": res.get("cache"), "retrieved_at": res.get("retrieved_at") or (res.get("source") or {}).get("retrieved_at"), "summary": outcome.get("summary"), "limitations": (res.get("limitations") or [])[:5],
                   "attribution": res.get("attribution")}
        not_sig = "البيانات الحالية لا تكفي لتأكيد وجود اتجاه" if lang == "ar" else "The available data are not sufficient to confirm a trend"
        system = EXPLAIN_SYSTEM.format(language="Arabic (Modern Standard Arabic)" if lang == "ar" else "English", not_sig=not_sig)
        user = f"USER QUESTION:\n{msg}\n\nTOOL_RESULT (JSON):\n{__import__('json').dumps(compact, ensure_ascii=False, default=str)[:9000]}"
        resp = llm.generate_raw(user, system, total_deadline_s=remaining(get_settings().llm_total_deadline_s))
        text = (resp.text or "").strip()
        if not text:
            return None
        allowed = {"summary": compact["summary"], "limitations": compact["limitations"], "retrieved_at": compact["retrieved_at"]}
        bad = unsupported_numbers(text, allowed, msg + " " + str(defaults.get("period") or "") + " " + str(outcome.get("used_args") or ""))
        if tool == "analyze_trend" and outcome["status"] == "ok":
            if outcome["summary"].get("significant") is False and not_sig not in text:
                bad.append("missing mandated phrase")
            if re.search(r"(لا يوجد تغي[ّ]?ر|no change)", text, re.I):
                bad.append("claims no change")
        if tool == "get_fire_detections" and re.search(r"confirmed (?:fires?|incidents?)|حرائق مؤكدة", text, re.I) and not re.search(r"not|ليست|لا ", text, re.I):
            bad.append("claims confirmed incidents")
        if bad:
            log.info("explanation rejected: %s", bad[:4])
            return None
        return text

    # ------------------------------------------------------------------------------------------------
    def _rag(self, sess, msg: str, lang: str, out: dict, llm_ok: bool, selected_by: str) -> dict:
        """Documentation questions: only passages that pass the relevance/evidence gate may support an answer; otherwise 'Insufficient resources...'."""
        svc = self.svc
        # 0) questions ABOUT THE CONVERSATION itself ("what was my second question?", "what did you tell me about Nablus?"): answered from the conversation only
        if self._about_conversation(msg) and sess.history:
            ctext = self._conversation_answer(sess, msg, lang, llm_ok)
            sess.add("user", msg); sess.add("assistant", ctext)
            o = {**out, "status": "ok", "answer": ctext, "answer_source": "claude" if llm_ok else "template", "citations": [], "selected_by": selected_by, "model": self._model_used() if llm_ok else None}
            o["outcome"] = "answered"; o["panel"] = {"kind": "none", "status": "none", "title": "", "metrics": [], "artifacts": [], "source": {}, "limitations": [], "details": {}}; o["map"] = None; o["inline"] = []
            return o
        # 1) built-in glossary: instant, offline, no data in it
        gtxt = GL.explain(msg, lang)
        if gtxt:
            sess.add("user", msg); sess.add("assistant", gtxt)
            o = {**out, "status": "ok", "answer": gtxt, "answer_source": "glossary", "citations": [], "selected_by": selected_by, "model": None}
            o["outcome"] = "answered"; o["panel"] = {"kind": "none", "status": "none", "title": "", "metrics": [], "artifacts": [], "source": {}, "limitations": [], "details": {}}; o["map"] = None; o["inline"] = []
            self._notice(o)
            return o
        a = None
        if llm_ok:
            try:
                a = svc.pipeline.answer(msg, language=lang, top_k=5) if svc._llm is not None or load_llm_key() else None
                if a is not None and svc.pipeline.llm is None:
                    svc.pipeline.llm = self._llm()
            except LLMError as e:
                out["fallback_reason"] = e.kind
                out["warnings"].append(f"Claude unavailable for the documentation answer ({e.kind}); retrieved excerpts shown instead.")
                a = None

        def web_or(status, txt, source, cites=None, **kw):
            """Concept questions only: when the documentation cannot answer, Claude Haiku may use web search to EXPLAIN the concept (never to supply data)."""
            if status == "insufficient_knowledge" and llm_ok and self._is_conceptual(msg):
                try:
                    w = self._web_explain(sess, msg, lang)
                except LLMError as e:
                    out["fallback_reason"] = out.get("fallback_reason") or e.kind
                    w = None
                if w:
                    return done("ok", w[0], "web", w[1], model=self._model_used())
            return done(status, txt, source, cites, **kw)

        def done(status, txt, source, cites=None, **kw):
            sess.add("user", msg); sess.add("assistant", txt)
            o = {**out, "status": status, "answer": txt, "answer_source": source, "citations": cites or [], "selected_by": selected_by, **kw}
            o["outcome"] = P.classify_outcome(status, None, o.get("fallback_reason"), False)
            o["inline"] = []
            o["panel"] = P.docs_panel(cites or [], lang) if (cites and source != "web") else {"kind": "none", "status": status, "title": "", "metrics": [], "artifacts": [], "source": {}, "limitations": [], "details": {}}
            o["map"] = None
            self._notice(o)
            return o

        if a is None:
            svc.pipeline.llm = svc.pipeline.llm or (svc._llm if svc._llm is not None else None)
            from app.config import KNOWLEDGE_COLLECTION
            from app.rag.pipeline import unknown_identifiers
            from app.rag.evidence import expand_query
            res = svc.retrievers[KNOWLEDGE_COLLECTION].retrieve(expand_query(msg), top_k=5)
            prio = {"core_reference": 0, "nasa_documentation": 1}
            from app.rag.evidence import directly_answers
            passages = sorted(svc.pipeline._select(res.items, msg), key=lambda r: prio.get(r.hit.metadata.get("source_role"), 2))
            passages = [r for r in passages if directly_answers(msg, " ".join(str(r.hit.metadata.get(k) or "") for k in ("document_title", "section")) + " " + r.hit.text)][:2]   # never show a passage that does not itself answer
            if res.best_dense < svc.pipeline.min_dense_score or not passages or unknown_identifiers(msg, [r.hit.text for r in res.items]):
                looks_like_data_request = bool(router.explicit_place(msg) or router.parse_period(msg) or any(router.RX[k].search(msg) for k in ("trend", "weather", "fire", "satellite", "danger")))
                if out.get("fallback_reason") in P.QUOTA_KINDS and looks_like_data_request:
                    txt = {"ar": "⚠️ نموذج اللغة غير متاح مؤقتًا (الحصة)، ولم أستطع تفسير هذا الطلب بأمان دونه. أعد الصياغة بمكان وفترة (مثال: «درجة الحرارة في نابلس بين 2005 و2025») أو حاول لاحقًا.",
                           "en": "⚠️ The language model is temporarily unavailable (quota), and I could not interpret this request safely without it. Rephrase with a place and a period (e.g. 'temperature in Nablus between 2005 and 2025') or try again later."}[lang]
                    return done("model_unavailable", txt, "template")
                reason = {"ar": "لا توجد في الوثائق الرسمية المفهرسة فقرة تجيب السؤال مباشرة" + (" ونموذج اللغة غير متاح لصياغة إجابة من مقتطفات جزئية." if out.get("fallback_reason") in P.QUOTA_KINDS or not llm_ok else "."),
                          "en": "No indexed official documentation passage answers this directly" + (", and the language model is unavailable to compose an answer from partial excerpts." if out.get("fallback_reason") in P.QUOTA_KINDS or not llm_ok else ".")}[lang]
                return web_or("insufficient_knowledge", render.insufficient(lang, reason), "template")
            cites = [self._cite(i + 1, r.hit.metadata, r.hit.text, r.dense_score) for i, r in enumerate(passages)]
            head = {"ar": "📄 **مقتطفات ذات صلة من الوثائق المفهرسة** (استرجاع حتمي، بدون صياغة من Claude):", "en": "📄 **Relevant excerpts from the indexed documentation** (deterministic retrieval, no Claude wording):"}[lang]
            def excerpt(c):
                t = re.sub(r"\s+", " ", c["text"]).strip()
                cut = t[:420]
                end = max(cut.rfind(". "), cut.rfind("؟ "))
                cut = cut[: end + 1] if end > 150 else cut.rsplit(" ", 1)[0] + "…"
                return f"**{(c.get('title') or c.get('source_file') or '')[:70]}**\n{cut} [{c['index']}]"
            txt = head + "\n\n" + "\n\n".join(excerpt(c) for c in cites[:2])
            return done("ok", txt, "rag_excerpts", cites, fallback_reason=out.get("fallback_reason") or ("template_requested" if not llm_ok else None))
        cites = [self._cite(s.index, {"source_file": s.source_file, "section": s.section, "document_title": s.document_title, "original_url": s.original_url,
                                       "service_id": s.service_id, "dataset_name": s.dataset_name, "provider": s.provider}, s.text if hasattr(s, "text") else s.snippet, s.score, s.cited, s.snippet) for s in a.sources]
        status = "ok" if a.answer_type in ("document_answer", "requires_data_tool") else a.answer_type
        src = "claude" if a.answer_type == "document_answer" else "template"
        txt = a.answer
        if a.answer_type == "insufficient_knowledge":
            txt = render.insufficient(lang, {"ar": "لا توجد في الوثائق الرسمية المفهرسة فقرة ذات صلة تدعم إجابة.", "en": "No indexed official documentation passage supports an answer."}[lang])
            cites = []
        return web_or(status, txt, src, [c for c in cites if c.get("cited")] or cites if a.answer_type == "document_answer" else cites, model=(a.llm or {}).get("model"),
                    warnings=out["warnings"] + list(a.warnings), rag_answer_type=a.answer_type)

    _META = re.compile(r"my (?:first|second|third|last|previous|earlier) (?:question|message)|what (?:did|was) (?:i|my)|what did you (?:tell|say|answer)|what have (?:i|we) (?:asked|discussed)|"
                       r"نتيجة (?:أول|اول|الأول|الاول|آخر|اخر) (?:سؤال|رسالة)|شو (?:كانت|كان) (?:نتيجة|جواب) (?:أول|اول)|سؤالي (?:الأول|الاول|الثاني|الثالث|الأخير|السابق)|ما (?:هو )?سؤالي|شو (?:كان )?سؤالي|ماذا (?:سألت|قلت|أجبت)|شو (?:سألت|قلت|جاوبت)|(?:اللي|ما) سألتك|لخّص(?:ي)? (?:لي )?(?:محادثتنا|المحادثة)|ملخص المحادثة|summari[sz]e (?:our|the) (?:chat|conversation)", re.I)

    def _about_conversation(self, msg: str) -> bool:
        return bool(self._META.search(msg))

    def _conversation_answer(self, sess, msg: str, lang: str, llm_ok: bool) -> str:
        block = self._conversation_block(sess)
        if llm_ok:
            try:
                system = ("Answer the user's question ABOUT THIS CONVERSATION using only the conversation below, in " + ("Arabic" if lang == "ar" else "English") + ". Be brief and exact (quote the question or result as written). "
                          "Do not use outside knowledge and do not add data. If the conversation does not contain the answer, say so. Markdown: a `> [!info]` callout line for the answer.")
                r = self._llm().generate_raw(block + "\n\nUSER QUESTION: " + msg, system, max_output_tokens=900, total_deadline_s=remaining(get_settings().llm_total_deadline_s))
                if r.text:
                    return r.text
            except LLMError:
                pass
        users = [m["text"] for m in sess.history if m["role"] == "user"]
        head = "أسئلتك في هذه المحادثة:" if lang == "ar" else "Your questions in this conversation:"
        return "> [!info] " + head + chr(10) + chr(10) + chr(10).join(f"{i + 1}. {u[:200]}" for i, u in enumerate(users))

    @staticmethod
    def _is_conceptual(msg: str) -> bool:
        """A request to EXPLAIN a concept (not to fetch data): asks for a meaning, names no place and no year/date."""
        return GL.asks_for_meaning(msg) and not router.explicit_place(msg) and not re.search(r"(?<!\d)(19|20)\d\d(?!\d)", msg) and not router.candidate_place_names(msg)

    def _web_explain(self, sess, msg: str, lang: str):
        recent = " | ".join(f"{m['role']}: {m['text'][:500]}" for m in sess.history[-2:])
        system = WEB_SYSTEM.format(language="Arabic" if lang == "ar" else "English")
        user = (f"RECENT CONVERSATION (for context only): {recent}\n\n" if recent else "") + f"USER QUESTION: {msg}"
        resp = self._llm().generate_raw(user, system, tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 2}], max_output_tokens=1500,
                                        total_deadline_s=remaining(get_settings().llm_total_deadline_s))
        text = (resp.text or "").strip()
        names = [n for n in (g[3] for g in __import__("app.chat.location", fromlist=["GAZETTEER"]).GAZETTEER.values())]
        if not text or re.search(r"(?<!\d)(19|20)\d\d(?!\d)", text) or any(a.lower() in text.lower() for n in names for a in n):
            return None                                           # a real place/year in a 'concept' answer means data slipped in: refuse it
        srcs = (getattr(resp, "web_sources", None) or [])[:4]
        cites = [{"index": i + 1, "kind": "web", "title": s.get("title") or s["url"], "url": s["url"], "text": s.get("snippet") or "", "cited": True} for i, s in enumerate(srcs)]
        if "[!" not in text:
            text = "> [!info] " + text
        note = ("^ شرح عام من الويب لتوضيح المفهوم فقط (ليس بيانات التطبيق). المصادر: " if lang == "ar" else "^ General explanation from the web to clarify the concept only (not app data). Sources: ") + " ".join(f"[{c['index']}]" for c in cites)
        return text + (chr(10) * 2 + note if cites else ""), cites

    @staticmethod
    def _cite(idx, md, text, score, cited=True, snippet=None) -> dict:
        return {"index": idx, "kind": "doc", "source_file": md.get("source_file"), "section": md.get("section"), "title": md.get("document_title"), "url": md.get("original_url"),
                "service_id": md.get("service_id"), "dataset": md.get("dataset_name"), "provider": md.get("provider"), "score": round(float(score), 3) if score is not None else None,
                "cited": cited, "text": (text or snippet or "")[:1800]}
