"""Claude function-calling loop for trend questions.

Flow: question -> Claude decides to call `analyze_trend` (arguments validated by the backend) -> backend runs the
tool -> Claude explains ONLY the tool output. Every number in the explanation is checked against the tool result;
on mismatch (or when Claude is unavailable) a deterministic template built from the tool result is returned instead.
Claude never calls NASA directly and never computes statistics.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from app.llm.base import LLMError
from app.config import get_settings
from app.agent.deterministic import explicit_trend_args
from app.reliability import request_budget, remaining
from app.tools.trend_tool import FUNCTION_DECLARATION, run_trend_analysis

log = logging.getLogger(__name__)

SYSTEM = """You are the trend-analysis assistant of EarthTrend Explorer (NASA Earth-science data).

TOOL USE
- For ANY question about whether a variable increased, decreased or changed over a period in a place, you MUST call the function
  analyze_trend. Never answer such a question from memory.
- Extract variable, place (or latitude/longitude), start_year and end_year from the question. Pass the variable the user asked for;
  never substitute another variable yourself. If the place or the period is missing or ambiguous, ask ONE short clarifying
  question instead of calling the function, and include no numbers in it.

EXPLAINING THE RESULT (after the tool returns)
- Use ONLY values that appear in the tool result. Never compute, round differently, estimate or invent numbers, and never add
  figures from your own knowledge. If status is not "ok", explain the reason from `message`/`reason_code` and give NO verdict.
- Keep direction, magnitude and statistical significance separate:
  direction = the sign of Sen's slope; magnitude = Sen's slope with its unit (and confidence interval if given);
  significance = p-value compared with the declared significance threshold alpha (and Kendall's tau).
- If test.significant is false, say exactly: "{not_sig}" and never say that there is no change.
- A p-value is NOT the probability that the result is true and NOT a confidence level; do not describe it that way.
- State: variable, place (note if it is a representative point), actual period, number of readings used and their unit,
  aggregation method, test name/version, source and units, and any data-quality notes (missing/invalid months, years dropped).
- Always include the caveats: this describes the historical trend only, does not prove a cause, and is not a forecast
  (forecasting is a separate path). Mention that a chart accompanies the answer.
- Do not mention JSON field names (such as test.significant); describe them in plain words.
- Keep official names, identifiers and units exactly as in the tool result. Write in {language}. Be concise.
"""


_YEAR = re.compile(r"(?<!\d)(19[89]\d|20[0-4]\d)(?!\d)")


_Y = r"(19[89]\d|20[0-4]\d)"
_RANGE = re.compile(rf"(?:(?:بين|between)\s*(?<!\d){_Y}(?!\d)\s*(?:و|and)\s*(?<!\d){_Y}(?!\d)"
                    rf"|(?:من|from)\s*(?<!\d){_Y}(?!\d)\s*(?:إلى|الى|حتى|لغاية|to|until|through)\s*(?<!\d){_Y}(?!\d)"
                    rf"|(?<!\d){_Y}(?!\d)\s*[-–—]\s*(?<!\d){_Y}(?!\d))", re.I)
_SINCE = re.compile(rf"(?:منذ|من عام|من سنة|since|starting in)\s*(?<!\d){_Y}(?!\d)", re.I)


def _bounds(m) -> tuple[int, int]:
    g = [int(x) for x in m.groups() if x]
    return g[0], g[1]


def _years(question: str) -> list[int]:
    return [int(y) for y in _YEAR.findall(question.translate(_AR_DIGITS))]


def period_is_ambiguous(question: str) -> bool:
    """True when the question names years but NOT exactly one clear period (e.g. two ranges, three years, two unrelated years)."""
    q = question.translate(_AR_DIGITS)
    years = _years(q)
    if not years:
        return False
    ranges, since = list(_RANGE.finditer(q)), list(_SINCE.finditer(q))
    if len(ranges) == 1 and len(set(years)) == 2 and not since and _bounds(ranges[0])[0] < _bounds(ranges[0])[1]:
        return False
    if len(ranges) == 0 and len(since) == 1 and len(set(years)) == 1:
        return False
    if len(set(years)) == 1 and not ranges:
        return False                       # a single year that is not a period boundary: nothing to correct, nothing to reject
    return True


def reconcile_years(question: str, args: dict) -> tuple[dict, list[str]]:
    """Years the user wrote are authoritative ONLY when they form one unambiguous period ('between A and B', 'from A to B',
    'A-B', 'since A'). Real runs showed the model returning end_year=2024 for '2005-2025'. Ambiguous questions are never
    patched here (see period_is_ambiguous: the agent asks for clarification instead of guessing)."""
    q = question.translate(_AR_DIGITS)
    fixed, notes = dict(args), []
    if period_is_ambiguous(q):
        return fixed, notes
    m = _RANGE.search(q)
    want = dict(zip(("start_year", "end_year"), _bounds(m))) if m else {}
    if not want:
        sm = _SINCE.search(q)
        want = {"start_year": int(sm.group(1))} if sm else {}
    for k, v in want.items():
        try:
            have = int(fixed.get(k))
        except (TypeError, ValueError):
            have = None
        if have != v:
            notes.append(f"{k} taken from the question ({v})" if have is None else f"{k} corrected from {fixed.get(k)} to {v} (explicit in the question)")
            fixed[k] = v
    return fixed, notes


@dataclass
class TrendAnswer:
    answer: str
    answer_source: str                  # claude | template
    status: str                         # tool status or 'clarification' / 'no_tool_call'
    analysis: dict | None = None
    tool_calls: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    llm: dict = field(default_factory=dict)
    fallback_reason: str | None = None


_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789.")
_NUM = re.compile(r"-?\d+(?:[.,]\d+)?(?:e-?\d+)?", re.I)


_PCT_KEYS = {"ci_level", "alpha", "coverage_fraction", "prediction_interval_levels"}      # probabilities/fractions that may legitimately be written as percentages
_NUMP = re.compile(r"(-?\d+(?:[.,]\d+)?(?:e-?\d+)?)\s*([%٪])?", re.I)


def _numbers_in(obj: Any, out: set[float], pct: set[float] | None = None, key: str | None = None) -> None:
    if isinstance(obj, bool) or obj is None:
        return
    if isinstance(obj, (int, float)):
        out.add(float(obj))
        if pct is not None and key in _PCT_KEYS and 0 <= abs(obj) <= 1:
            pct.add(round(float(obj) * 100, 6))                # '95%' for ci_level 0.95 -- only for these keys, never for slopes/p
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _numbers_in(v, out, pct, k)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _numbers_in(v, out, pct, key)
    elif isinstance(obj, str):
        for m in _NUM.findall(obj.translate(_AR_DIGITS)):
            try:
                out.add(float(m.replace(",", "")))
            except ValueError:
                pass


def unsupported_numbers(text: str, result: dict, question: str = "") -> list[str]:
    """Numbers in `text` that appear neither in the tool result nor in the question (0.25% relative tolerance for rounding).
    A number followed by % must match a percentage form of ci_level / alpha / coverage_fraction only."""
    allowed: set[float] = set()
    pct_allowed: set[float] = set()
    _numbers_in({k: v for k, v in result.items() if k != "chart"}, allowed, pct_allowed)
    _numbers_in(question, allowed)
    close = lambda v, pool: any(abs(v - a) <= max(1e-9, 0.0025 * abs(a)) for a in pool)
    bad = []
    for num, pc in _NUMP.findall(re.sub(r"\[\d+\]", "", text).translate(_AR_DIGITS)):
        try:
            v = float(num.replace(",", ""))
        except ValueError:
            continue
        if not (close(v, pct_allowed) if pc else close(v, allowed)):
            bad.append(num + (pc or ""))
    return bad


def compact_for_model(result: dict) -> dict:
    r = {k: v for k, v in result.items() if k not in ("chart", "tool")}
    r["chart"] = {"available": "chart is attached to the answer by the application"} if result.get("chart") else None
    return r


def render_template(result: dict, language: str = "ar") -> str:
    """Deterministic explanation built only from the tool result (used when Claude is unavailable or fails validation)."""
    ar = language == "ar"
    if result.get("status") != "ok":
        head = "تعذّر إصدار حكم عن الاتجاه" if ar else "No trend verdict could be issued"
        extra = ""
        if result.get("suggested_alternative"):
            extra = (f"\nبديل متاح (يتطلب موافقتك): {result['suggested_alternative']}." if ar
                     else f"\nAvailable alternative (needs your agreement): {result['suggested_alternative']}.")
        return f"{head}: {result.get('message', '')}{extra}\n(status={result.get('status')}, reason={result.get('reason_code')})"
    v, rg, t, dq = result["variable"], result["region"], result["test"], result["data_quality"]
    pa, sen, units = result["period_actual"], t["sen_slope"], result["units"]
    interp = result["interpretation"]["text_ar" if ar else "text_en"]
    ci = f"[{sen['ci_low']}, {sen['ci_high']}]"
    lines = [
        (f"المتغير: {v.get('name_ar') or v['name']} ({v['name']}) — المنطقة: {rg['name']} "
         f"({'نقطة تمثيلية' if rg.get('type') == 'representative_point' else 'نقطة'} {rg['lat']}, {rg['lon']})") if ar else
        f"Variable: {v['name']} — Region: {rg['name']} ({rg.get('type')}: {rg['lat']}, {rg['lon']})",
        (f"الفترة الفعلية: {pa['first']} → {pa['last']} | القراءات المستخدمة: {t['n_used']} ({t['n_unit']}) | الوحدة: {units} | "
         f"التجميع: {result['aggregation']['chosen']}") if ar else
        f"Actual period: {pa['first']} → {pa['last']} | readings used: {t['n_used']} ({t['n_unit']}) | unit: {units} | aggregation: {result['aggregation']['chosen']}",
        (f"الاختبار: {t['test_name']} | Kendall's tau = {t['kendall_tau']} | p = {t['p_value']} | عتبة الدلالة = {t['alpha']}") if ar else
        f"Test: {t['test_name']} | Kendall's tau = {t['kendall_tau']} | p = {t['p_value']} | alpha = {t['alpha']}",
        (f"Sen's slope = {sen['value']} {sen['unit']} (مجال الثقة {int(sen['ci_level'] * 100)}%: {ci})") if ar else
        f"Sen's slope = {sen['value']} {sen['unit']} ({int(sen['ci_level'] * 100)}% CI: {ci})",
        interp,
        (f"جودة البيانات: صالحة {dq['valid_months']} من {dq['expected_months']} شهرًا؛ مفقودة {dq['missing_months']}؛ غير صالحة {dq['invalid_months']}؛ "
         f"{dq['gap_policy']}.") if ar else
        f"Data quality: {dq['valid_months']} of {dq['expected_months']} months valid; missing {dq['missing_months']}; invalid {dq['invalid_months']}; {dq['gap_policy']}.",
        f"{'المصدر' if ar else 'Source'}: {result['source'].get('provider')} {result['source'].get('dataset')} (retrieved {result['source'].get('retrieved_at')})",
    ] + (result["caveats"] if ar else result["caveats_en"]) + result.get("notes", [])
    return "\n".join(lines)


class TrendAgent:
    def __init__(self, llm, tool: Callable[[dict], dict] = run_trend_analysis):
        self.llm, self.tool = llm, tool

    def ask(self, question: str, language: str = "ar") -> TrendAnswer:
        with request_budget(get_settings().request_total_deadline_s):
            return self._ask(question, language)

    def _ask(self, question: str, language: str) -> TrendAnswer:
        not_sig = "البيانات الحالية لا تكفي لتأكيد وجود اتجاه" if language == "ar" else "The available data are not sufficient to confirm a trend"
        system = SYSTEM.format(not_sig=not_sig, language="Arabic (Modern Standard Arabic)" if language == "ar" else "English")
        tools = [FUNCTION_DECLARATION]
        contents = [{"role": "user", "content": question}]
        calls: list[dict] = []
        warnings: list[str] = []
        analysis: dict | None = None
        try:
            if self.llm is None:
                raise LLMError("ANTHROPIC_API_KEY is not configured", 503, "not_configured")
            resp = self.llm.generate_raw(contents, system, tools=tools,
                                         total_deadline_s=remaining(get_settings().llm_total_deadline_s))
            first_model = getattr(self.llm, "last_model_used", None)
            fcs = list(getattr(resp, "function_calls", None) or [])
            if not fcs:
                text = (resp.text or "").strip()
                if not text or unsupported_numbers(text, {}, question) or not re.search(r"[?؟]", text):
                    return TrendAnswer("لم أستطع تحديد المتغير والمنطقة والفترة. اذكر المتغير والمكان والسنوات (مثال: حرارة الهواء في نابلس 2005–2025)." if language == "ar"
                                       else "I could not identify the variable, place and period. Please state them (e.g. air temperature in Nablus 2005-2025).",
                                       "template", "no_tool_call", warnings=["model did not call the analysis tool"], fallback_reason="no_tool_call")
                return TrendAnswer(text, "claude", "clarification", warnings=["clarification requested; no analysis was run"])
            contents.append({"role": "assistant", "content": resp.candidates[0].content})        # echo the model's own tool_use block back, unchanged
            if len(fcs) > 1:
                raise LLMError("Only one analysis per question is supported; split this request.", 502, "tool_protocol")
            parts = []
            for fc in fcs:
                if fc.name != "analyze_trend":
                    raise LLMError("Model requested an unknown tool", 502, "tool_protocol")
                if not isinstance(fc.args, dict):
                    raise LLMError("Tool arguments must be an object", 502, "tool_protocol")
                if period_is_ambiguous(question):
                    warnings.append("period in the question is ambiguous; no analysis was run")
                    msg = ("السؤال يتضمن أكثر من فترة زمنية أو سنوات غير محددة بوضوح. حدّد فترة واحدة (مثال: بين 2005 و2025) وسأجري التحليل."
                           if language == "ar" else
                           "The question names more than one period or unclear years. Please give exactly one period (e.g. between 2005 and 2025).")
                    return TrendAnswer(msg, "template", "clarification", None, [], warnings, {"model": first_model},
                                       fallback_reason="ambiguous_period")
                args, notes = reconcile_years(question, dict(fc.args or {}))
                warnings.extend(notes)
                analysis = self.tool(args)
                calls.append({"name": fc.name, "args": args, "status": analysis.get("status")})
                parts.append({"type": "tool_result", "tool_use_id": getattr(fc, "id", None) or "toolu_local", "content": json.dumps({"result": compact_for_model(analysis)}, ensure_ascii=False, default=str)})
            if analysis is None:
                raise LLMError("no valid tool call", status=502)
            contents.append({"role": "user", "content": parts})
            final = self.llm.generate_raw(contents, system, tools=tools,                       # tools stay declared (the API requires it with tool_result blocks); a new call is rejected below

                                          total_deadline_s=remaining(get_settings().llm_total_deadline_s))
            if getattr(final, "function_calls", None):
                raise LLMError("Tool call in explanation turn; loop stopped", 502, "tool_protocol")
            text = (final.text or "").strip()
            um = getattr(final, "usage_metadata", None)
            llm_info = {"model": first_model or getattr(self.llm, "model", None), "prompt_tokens": getattr(um, "prompt_token_count", None),
                        "output_tokens": getattr(um, "candidates_token_count", None)}
            bad = unsupported_numbers(text, analysis, question)
            if analysis.get("status") == "ok":
                if analysis["interpretation"]["code"] == "NOT_SIGNIFICANT" and not_sig not in text:
                    bad.append("missing mandated non-significance phrase")
                if re.search(r"(لا يوجد تغي[ّ]?ر|no change)", text, re.I):
                    bad.append("claims 'no change'")
            if not text or bad:
                warnings.append(f"Claude explanation rejected ({bad[:5] or 'empty'}); deterministic template used")
                return TrendAnswer(render_template(analysis, language), "template", analysis["status"], analysis, calls, warnings, llm_info,
                                   fallback_reason="explanation_validation")
            return TrendAnswer(text, "claude", analysis["status"], analysis, calls, warnings, llm_info)
        except LLMError as e:
            if analysis is None:
                args = explicit_trend_args(question)
                if e.kind not in {"quota", "budget", "service_error", "overloaded", "network", "timeout", "not_configured"} or args is None:
                    raise
                analysis = self.tool(args)
                calls.append({"name": "analyze_trend", "args": args, "status": analysis.get("status")})
                warnings.append("Explicit arguments parsed deterministically; model function calling did not succeed")
            warnings.append(f"Claude unavailable for the explanation ({e}); deterministic template used")
            return TrendAnswer(render_template(analysis, language), "template", analysis["status"], analysis, calls, warnings,
                               {"error_kind": e.kind, "attempts": e.attempts}, fallback_reason=e.kind)
