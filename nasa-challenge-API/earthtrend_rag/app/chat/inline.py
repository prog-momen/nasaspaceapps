"""What goes INSIDE the chat bubble (the one table / chart the user needs) versus what stays in the side panel (statistics, secondary tables, provenance).

Rules: at most one primary visual per answer (a chart for time series, a compact table for short lists); an explicit request ("table/جدول", "chart/رسم/مخطط")
selects that form; everything else (metrics, full tables, backtests, provenance, maps) stays in the side panel. Built only from tool results; nothing is invented."""
from __future__ import annotations

import re

WANT_TABLE = re.compile(r"table|tabular|جدول|جداول", re.I)
WANT_CHART = re.compile(r"chart|graph|plot|رسم|مخطط|بياني|منحنى", re.I)
CHART_TYPES = ("line_chart", "forecast_chart")


def _compact_table(title: str, columns: list[str], rows: list[list], note: str | None = None) -> dict:
    return {"type": "table", "title": title, "columns": columns, "rows": rows, "inline": True, "compact": True, **({"note": note} if note else {})}


def build_inline(tool: str, outcome: dict, question: str, lang: str) -> list[dict]:
    res, s = outcome["result"], outcome.get("summary") or {}
    if res.get("status") not in ("ok", "no_data"):
        return []
    arts = outcome.get("artifacts") or []
    want_t, want_c = bool(WANT_TABLE.search(question)), bool(WANT_CHART.search(question))
    first_chart = next((a for a in arts if a.get("type") in CHART_TYPES), None)
    out: list[dict] = []
    T = lambda ar, en: ar if lang == "ar" else en
    if tool == "analyze_trend":
        if first_chart:
            out.append({**first_chart, "inline": True})
        if want_t and res.get("status") == "ok":
            t = res["test"]
            out.append(_compact_table(T("نتيجة الاتجاه", "Trend result"), [T("البند", "Item"), T("القيمة", "Value")], [
                [T("ميل Sen", "Sen's slope"), f"{t['sen_slope']['value']} {t['sen_slope']['unit']}"], ["p", t["p_value"]], ["Kendall τ", t["kendall_tau"]],
                [T("الدلالة", "Significant"), T("نعم", "yes") if t["significant"] else T("لا", "no")], [T("قراءات", "Readings"), f"{t['n_used']} ({t['n_unit']})"]]))
    elif tool == "get_weather" and res.get("status") == "ok":
        rows = s.get("daily") or []
        stats = s.get("period_stats") or {}
        if (stats.get("n_days") or 0) > 16:
            d = (res.get("data") or {}).get("daily") or {}
            by: dict = {}
            for i, day in enumerate(d.get("time", [])):
                m = by.setdefault(day[:7], {"tx": [], "tn": [], "p": []})
                for key, arr in (("tx", "temperature_2m_max"), ("tn", "temperature_2m_min"), ("p", "precipitation_sum")):
                    v = (d.get(arr) or [None] * (i + 1))[i]
                    if v is not None:
                        m[key].append(v)
            mean = lambda v: round(sum(v) / len(v), 1) if v else None
            out.append(_compact_table(T("ملخص شهري للفترة المطلوبة", "Monthly summary of the requested period"), [T("الشهر", "Month"), T("متوسط العظمى °C", "Mean max °C"), T("متوسط الصغرى °C", "Mean min °C"), T("مجموع الهطول mm", "Total precip mm")],
                                      [[k, mean(v["tx"]), mean(v["tn"]), round(sum(v["p"]), 1) if v["p"] else None] for k, v in sorted(by.items())],
                                      note=T("قيم نموذج إعادة تحليل وليست قراءات محطة", "Reanalysis model values, not station readings")))
            return out
        cols = [T("التاريخ", "Date"), T("عظمى °C", "Max °C"), T("صغرى °C", "Min °C"), T("هطول mm", "Precip mm"), T("رياح km/h", "Wind km/h")]
        out.append(_compact_table(T("الأيام القادمة" if res.get("capability") == "weather_forecast" else "الفترة المطلوبة", "Daily values"), cols,
                                  [[r["date"], r["tmax_c"], r["tmin_c"], r["precip_mm"], r["wind_max_kmh"]] for r in rows[:10]]))
        if want_c and rows:
            out.append({"type": "line_chart", "title": T("الحرارة اليومية °C", "Daily temperature °C"), "x": [r["date"] for r in rows], "inline": True,
                        "series": [{"name": T("عظمى", "max"), "unit": "°C", "y": [r["tmax_c"] for r in rows], "kind": "line"}, {"name": T("صغرى", "min"), "unit": "°C", "y": [r["tmin_c"] for r in rows], "kind": "line"}]})
    elif tool == "get_fire_detections" and res.get("status") == "ok":
        det = sorted((res.get("data") or {}).get("detections") or [], key=lambda d: -(d.get("frp_mw") or 0))[:8]
        if det:
            out.append(_compact_table(T("أقوى الكشوف (حسب FRP)", "Strongest detections (by FRP)"), [T("وقت UTC", "Time UTC"), "lat", "lon", T("ثقة", "conf."), "FRP MW", T("قمر", "sat.")],
                                      [[d.get("acq_datetime_utc") or f"{d.get('acq_date')} {d.get('acq_time')}", d["latitude"], d["longitude"], d.get("confidence"), d.get("frp_mw"), d.get("satellite")] for d in det],
                                      note=T("القائمة الكاملة والخريطة في اللوحة الجانبية", "Full list and map in the side panel")))
    elif tool in ("get_ndvi", "get_lst") and first_chart:
        out.append({**first_chart, "inline": True})
    elif tool == "forecast_monthly" and res.get("status") == "ok":
        if first_chart:
            out.append({**first_chart, "inline": True})
        leads = s.get("leads") or []
        u = s.get("unit", "")
        if leads:
            out.append(_compact_table(T("قيم مختارة من التوقع", "Selected forecast values"), [T("الشهر", "Month"), f"{T('القيمة', 'Value')} ({u})", T("مجال 80%", "80% interval"), T("مجال 95%", "95% interval"), T("الحالة", "Status")],
                                      [[x["date"][:7], x["value"], f"{x['lo80']} – {x['hi80']}" if x.get("lo80") is not None else None, f"{x['lo95']} – {x['hi95']}" if x.get("lo95") is not None else None,
                                        T("نموذج مُتحقَّق", "validated model") if x["status"] == "validated_model" else T("خط أساس", "baseline")] for x in leads],
                                      note=T("الجدول الكامل وأخطاء الاختبار الرجعي في اللوحة الجانبية", "Full table and backtest errors in the side panel")))
    elif tool == "forecast_fire_danger" and res.get("status") == "ok":
        out += [{**a, "inline": True} for a in arts if a.get("type") in ("category_strip", "ensemble_chart")]
    elif tool == "search_earth_datasets":
        items = s.get("items") or []
        if items:
            out.append(_compact_table(T("مجموعات البيانات", "Datasets"), [T("الاسم", "Name"), T("الإصدار", "Version"), T("العنوان", "Title")], [[i["name"], i.get("version"), i.get("title")] for i in items[:6]]))
    return out


def split_panel_artifacts(artifacts: list[dict], inline: list[dict]) -> list[dict]:
    """Artifacts shown inline are removed from the side panel (no duplicates); everything else stays there."""
    taken = {(a.get("type"), a.get("title")) for a in inline}
    return [a for a in artifacts if (a.get("type"), a.get("title")) not in taken]
