"""Gemini function-calling loop for trend questions.

Flow: question -> Gemini decides to call `analyze_trend` (arguments validated by the backend) -> backend runs the
tool -> Gemini explains ONLY the tool output. Every number in the explanation is checked against the tool result;
on mismatch (or when Gemini is unavailable) a deterministic template built from the tool result is returned instead.
Gemini never calls NASA directly and never computes statistics.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from app.llm.gemini_client import LLMError
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
- Keep official names, identifiers and units exactly as in the tool result. Write in {language}. Be concise.
"""


@dataclass
class TrendAnswer:
    answer: str
    answer_source: str                  # gemini | template
    status: str                         # tool status or 'clarification' / 'no_tool_call'
    analysis: dict | None = None
    tool_calls: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    llm: dict = field(default_factory=dict)


_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789.")
_NUM = re.compile(r"-?\d+(?:[.,]\d+)?(?:e-?\d+)?", re.I)


def _numbers_in(obj: Any, out: set[float]) -> None:
    if isinstance(obj, bool) or obj is None:
        return
    if isinstance(obj, (int, float)):
        out.add(float(obj))
        if 0 < abs(obj) <= 1:                 # 0.95 may legitimately be written as 95 (%)
            out.add(round(float(obj) * 100, 6))
    elif isinstance(obj, dict):
        for v in obj.values():
            _numbers_in(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _numbers_in(v, out)
    elif isinstance(obj, str):
        for m in _NUM.findall(obj.translate(_AR_DIGITS)):
            try:
                out.add(float(m.replace(",", "")))
            except ValueError:
                pass


def unsupported_numbers(text: str, result: dict, question: str = "") -> list[str]:
    """Numbers in `text` that appear neither in the tool result nor in the question (tolerant to rounding)."""
    allowed: set[float] = set()
    _numbers_in({k: v for k, v in result.items() if k != "chart"}, allowed)
    _numbers_in(question, allowed)
    bad = []
    for m in _NUM.findall(re.sub(r"\[\d+\]", "", text).translate(_AR_DIGITS)):
        try:
            v = float(m.replace(",", ""))
        except ValueError:
            continue
        if not any(abs(v - a) <= max(0.0051, 0.02 * abs(a)) or abs(abs(v) - abs(a)) < 1e-9 for a in allowed):
            bad.append(m)
    return bad


def compact_for_model(result: dict) -> dict:
    r = {k: v for k, v in result.items() if k not in ("chart", "tool")}
    r["chart"] = {"available": "chart is attached to the answer by the application"} if result.get("chart") else None
    return r


def render_template(result: dict, language: str = "ar") -> str:
    """Deterministic explanation built only from the tool result (used when Gemini is unavailable or fails validation)."""
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
    ] + (result["caveats"] if ar else result["caveats_en"])
    return "\n".join(lines)


class TrendAgent:
    def __init__(self, llm, tool: Callable[[dict], dict] = run_trend_analysis):
        self.llm, self.tool = llm, tool

    def ask(self, question: str, language: str = "ar") -> TrendAnswer:
        from google.genai import types

        not_sig = "البيانات الحالية لا تكفي لتأكيد وجود اتجاه" if language == "ar" else "The available data are not sufficient to confirm a trend"
        system = SYSTEM.format(not_sig=not_sig, language="Arabic (Modern Standard Arabic)" if language == "ar" else "English")
        tools = [types.Tool(function_declarations=[types.FunctionDeclaration(**FUNCTION_DECLARATION)])]
        contents = [types.Content(role="user", parts=[types.Part(text=question)])]
        calls: list[dict] = []
        warnings: list[str] = []
        analysis: dict | None = None
        try:
            resp = self.llm.generate_raw(contents, system, tools=tools)
            first_model = getattr(self.llm, "last_model_used", None)
            fcs = list(getattr(resp, "function_calls", None) or [])
            if not fcs:
                text = (resp.text or "").strip()
                if not text or unsupported_numbers(text, {}, question):
                    return TrendAnswer("لم أستطع تحديد المتغير والمنطقة والفترة. اذكر المتغير والمكان والسنوات (مثال: حرارة الهواء في نابلس 2005–2025)." if language == "ar"
                                       else "I could not identify the variable, place and period. Please state them (e.g. air temperature in Nablus 2005-2025).",
                                       "template", "no_tool_call", warnings=["model did not call the analysis tool"])
                return TrendAnswer(text, "gemini", "clarification", warnings=["clarification requested; no analysis was run"])
            contents.append(resp.candidates[0].content)
            parts = []
            for fc in fcs[:1]:                      # one analysis per question
                if fc.name != "analyze_trend":
                    warnings.append(f"model requested unknown function '{fc.name}'; ignored")
                    continue
                args = dict(fc.args or {})
                analysis = self.tool(args)
                calls.append({"name": fc.name, "args": args, "status": analysis.get("status")})
                parts.append(types.Part.from_function_response(name=fc.name, response={"result": compact_for_model(analysis)}))
            if analysis is None:
                raise LLMError("no valid tool call", status=502)
            contents.append(types.Content(role="user", parts=parts))
            # the explanation turn is pinned to the model that issued the tool call (thought signatures are model-specific)
            final = self.llm.generate_raw(contents, system, tools=None, pin_model=first_model)
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
                warnings.append(f"Gemini explanation rejected ({bad[:5] or 'empty'}); deterministic template used")
                return TrendAnswer(render_template(analysis, language), "template", analysis["status"], analysis, calls, warnings, llm_info)
            return TrendAnswer(text, "gemini", analysis["status"], analysis, calls, warnings, llm_info)
        except LLMError as e:
            if analysis is None:
                raise
            warnings.append(f"Gemini unavailable for the explanation ({e}); deterministic template used")
            return TrendAnswer(render_template(analysis, language), "template", analysis["status"], analysis, calls, warnings)
