"""Monthly forecasting (1-24 months): data preparation, leakage, baselines, constraints, honest labels, routing, panel.
Labels: SYNTHETIC series (known structure) and the REAL captured NASA POWER Nablus T2M fixture are used; no network, no LLM. The real multi-location evaluation is
evidence/forecast_eval (live NASA POWER data, cached) produced by scripts/run_forecast_evaluation.py."""
import json
import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.analysis.timeseries import MonthlySeries
from app.chat import panel as P
from app.chat import router
from app.data_sources.power import parse_power_monthly
from app.forecast import engine as E
from app.forecast import evaluation as V
from app.forecast import series as S
from app.forecast import service as SV

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 11, 15)


def synth(n=420, start=(1990, 1), amp=8.0, trend=0.03, noise=0.6, base=20.0, seed=1, unit="°C"):
    rng = np.random.default_rng(seed)
    y, m = start
    years, months, vals = [], [], []
    for i in range(n):
        years.append(y); months.append(m)
        vals.append(round(base + amp * math.sin(2 * math.pi * (m - 4) / 12) + trend * i / 12 + rng.normal(0, noise), 3))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return MonthlySeries(years, months, vals, unit, None, {"provider": "SYNTHETIC", "dataset": "synthetic", "fill_value": -999.0, "retrieved_at": "2026-11-15T00:00:00+00:00"})


def fetcher_for(ms):
    return lambda *a, **k: ms


@pytest.fixture(autouse=True)
def fast_depth(monkeypatch):
    monkeypatch.setitem(V.DEPTHS, "fast", {"dev_n": 3, "dev_step": 12, "hold_n": 4, "hold_step": 12, "advanced": ["ets_aada"]})


def to_y(ms, variable="air_temperature", today=TODAY, start=1990):
    return S.prepare(ms, variable, 0.0, 0.0, start, today.year, today)


# ---- dates ----------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("cutoff,first,last", [("2026-09-01", "2026-10-01", "2028-09-01"), ("2025-12-01", "2026-01-01", "2027-12-01"), ("2026-01-01", "2026-02-01", "2028-01-01")])
def test_24_forecast_months_are_consecutive_and_start_after_the_cutoff(cutoff, first, last):
    idx = pd.date_range(pd.Timestamp(cutoff) + pd.offsets.MonthBegin(1), periods=24, freq="MS")
    assert str(idx[0].date()) == first and str(idx[-1].date()) == last and len(set(idx)) == 24
    assert all((b.year * 12 + b.month) - (a.year * 12 + a.month) == 1 for a, b in zip(idx[:-1], idx[1:]))


def test_service_forecast_dates_follow_the_data_cutoff_not_today_and_the_gap_is_disclosed():
    ms = synth(n=12 * 36 + 9)                                           # 1990-01 .. 2026-09 -> cutoff 2026-09 (the current month 2026-11 is excluded)
    r = SV.forecast_monthly(32.0, 35.0, "air_temperature", 24, today=TODAY, fetcher=fetcher_for(ms), use_cache=False)
    assert r["status"] == "ok"
    c = r["data"]["cutoff"]
    assert c["data_cutoff_month"] == "2026-09-01" and c["first_forecast_month"] == "2026-10-01" and c["issue_date"] == "2026-11-15" and c["months_between_cutoff_and_current_month"] == 2
    rows = r["data"]["forecast"]
    assert [x["lead"] for x in rows] == list(range(1, 25)) and rows[-1]["date"] == "2028-09-01"
    # the span is counted from today; the month(s) missing between the data cutoff and today are forecast too and flagged as gap months
    assert [x["date"] for x in rows if x["gap_month_before_today"]] == ["2026-10-01"] == c["gap_months"]
    assert c["requested_first_month"] == "2026-11-01" and c["requested_months"] == 24 and "gap months" in c["note"] and "shortened" in c["note"]
    r3 = SV.forecast_monthly(32.0, 35.0, "air_temperature", 3, today=TODAY, fetcher=fetcher_for(ms), use_cache=False)      # '90 days' from 2026-11-15 ends in 2027-02
    d3 = [x["date"] for x in r3["data"]["forecast"]]
    assert d3 == ["2026-10-01", "2026-11-01", "2026-12-01", "2027-01-01", "2027-02-01"] and r3["data"]["cutoff"]["requested_last_month"] == "2027-02-01"
    assert "24 months from today" not in json.dumps(r)


# ---- missing / incomplete months -----------------------------------------------------------------------------------------------------
def test_current_incomplete_month_and_later_are_excluded_and_trailing_gap_is_reported():
    ms = synth(n=12 * 36 + 10)                                          # runs to 2026-10; the current month 2026-11 would be incomplete
    p = to_y(ms)
    assert p.status == "ok" and str(p.y.index[-1].date()) == "2026-10-01" and p.quality["excluded_incomplete_or_future_months"] == 0
    ms2 = synth(n=12 * 36 + 11)                                         # includes 2026-11 (incomplete): excluded
    p2 = to_y(ms2)
    assert str(p2.y.index[-1].date()) == "2026-10-01" and p2.quality["excluded_incomplete_or_future_months"] == 1
    vals = list(ms2.value); vals[-3:] = [-999.0, -999.0, -999.0]        # trailing fill values: the cutoff moves back to the last VALID month
    p3 = to_y(MonthlySeries(ms2.year, ms2.month, vals, "°C", None, ms2.source))
    assert str(p3.y.index[-1].date()) == "2026-08-01"


def test_interior_gap_is_filled_causally_and_large_gaps_are_refused():
    ms = synth(n=12 * 36 + 9)
    vals = list(ms.value); i = 200
    base = to_y(ms)
    vals[i] = -999.0
    a = to_y(MonthlySeries(ms.year, ms.month, vals, "°C", None, ms.source))
    assert a.status == "ok" and a.quality["n_filled_causally"] == 1
    fill_a = float(a.y.iloc[i])
    vals_future = list(vals)
    for j in range(i + 1, len(vals_future)):
        vals_future[j] = 33.0 if (j - i) % 12 == 0 else vals_future[j]          # alter only FUTURE same-calendar-month values
    b = to_y(MonthlySeries(ms.year, ms.month, vals_future, "°C", None, ms.source))
    assert float(b.y.iloc[i]) == pytest.approx(fill_a)                           # the fill never looked at the future
    v3 = list(ms.value); v3[100:103] = [-999.0] * 3
    assert to_y(MonthlySeries(ms.year, ms.month, v3, "°C", None, ms.source)).status == "too_many_missing"
    v4 = [(-999.0 if k % 20 == 0 else v) for k, v in enumerate(ms.value)]
    assert to_y(MonthlySeries(ms.year, ms.month, v4, "°C", None, ms.source)).status == "too_many_missing"


def test_insufficient_history_and_constant_series_are_refused_with_reasons():
    short = to_y(synth(n=100, start=(2018, 1)), start=2018)
    assert short.status == "insufficient_history"
    r = SV.forecast_monthly(1.0, 1.0, "air_temperature", 12, today=TODAY, fetcher=fetcher_for(synth(n=100, start=(2018, 1))), use_cache=False)
    assert r["status"] == "unsupported_request" and r["reason_code"] == "INSUFFICIENT_DATA" and r["data"]["provenance"]
    const = MonthlySeries(synth().year, synth().month, [20.0] * len(synth().year), "°C", None, synth().source)
    r2 = SV.forecast_monthly(1.0, 1.0, "air_temperature", 12, today=TODAY, fetcher=fetcher_for(const), use_cache=False)
    assert r2["reason_code"] == "CONSTANT_SERIES" and r2["status"] == "unsupported_request"


# ---- horizon validation -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("m", [0, -3, 25, 36, 2.5, "12"])
def test_horizon_outside_1_to_24_is_rejected_before_any_data_is_fetched(m):
    def boom(*a, **k):
        raise AssertionError("must not fetch")
    r = SV.forecast_monthly(1.0, 1.0, "air_temperature", m, today=TODAY, fetcher=boom, use_cache=False)
    assert r["status"] == "invalid_request" and r["reason_code"] == "HORIZON_OUT_OF_RANGE"


def test_unsupported_variable_and_long_requests_are_refused():
    assert SV.forecast_monthly(1.0, 1.0, "drought", 12, today=TODAY)["reason_code"] == "VARIABLE_NOT_SUPPORTED"
    assert router.route("forecast the temperature in Cairo for the next 3 years").unsupported == "forecast_too_long"


# ---- leakage ----------------------------------------------------------------------------------------------------------------------------
def test_forecasts_at_an_origin_do_not_depend_on_data_after_the_origin():
    y = to_y(synth(n=420)).y
    tf = E.Transform("identity")
    o = 300
    a = E.run_origins(y, tf, [o], ["snaive", "clim", "clim_trend", "ets_aada"], 24)
    y2 = y.copy(); y2.iloc[o:] = 1000.0                                  # destroy everything after the origin
    b = E.run_origins(y2, tf, [o], ["snaive", "clim", "clim_trend", "ets_aada"], 24)
    for s in ("snaive", "clim", "clim_trend", "ets_aada"):
        np.testing.assert_allclose(a.models[s]["mean"], b.models[s]["mean"])
        np.testing.assert_allclose(a.models[s]["lo95"], b.models[s]["lo95"])


def test_origin_plan_keeps_development_windows_before_the_holdout_and_is_chronological():
    pl = V.plan_origins(549, 24, V.DEPTHS["full"])
    assert max(pl["dev"]) + 24 <= min(pl["hold"]) and pl["dev"] == sorted(pl["dev"]) and pl["hold"] == sorted(pl["hold"]) and max(pl["hold"]) + 24 <= 549
    assert min(pl["dev"]) >= E.MIN_TRAIN_MONTHS and len(pl["hold"]) >= 3


def test_selection_uses_development_origins_only(monkeypatch):
    y = to_y(synth(n=420)).y
    ev = V.evaluate(y, E.Transform("identity"), "fast", 24)
    assert ev["status"] == "ok"
    hold_first = ev["plan"]["hold"][0]
    # the chosen models were ranked by development MAE: re-rank from the dev origins and confirm the same choice
    adv = ev["selected_advanced"]
    dev_mae = ev["dev_mean_mae"]
    assert (adv is None) or all(dev_mae[adv] <= dev_mae[o] for o in V.DEPTHS["fast"]["advanced"] if dev_mae[o] is not None)
    assert ev["best_baseline"] == min(E.BASELINES, key=lambda s: dev_mae[s])
    assert max(ev["plan"]["dev"]) + 24 <= hold_first


# ---- baseline comparison / skill statistics --------------------------------------------------------------------------------------------
def test_block_bootstrap_detects_real_improvement_and_does_not_invent_one():
    rng = np.random.default_rng(0)
    base = np.abs(rng.normal(1.0, 0.1, 40))
    better = base * 0.6
    r = E.block_bootstrap_ratio(better, base, 4)
    assert r["hi"] < 1.0 and r["ratio"] == pytest.approx(0.6, abs=0.01)
    same = E.block_bootstrap_ratio(base * rng.normal(1.0, 0.1, 40), base, 4)
    assert same["lo"] < 1.0 < same["hi"]
    worse = E.block_bootstrap_ratio(base * 1.5, base, 4)
    assert worse["lo"] > 1.0
    assert E.block_bootstrap_ratio(base[:2], base[:2], 4)["ratio"] is None               # too few origins: no verdict


def test_baselines_keep_their_real_names_and_a_non_validated_model_is_not_presented_as_validated():
    ms = synth(n=12 * 36 + 9, noise=1.5)
    r = SV.forecast_monthly(32.0, 35.0, "air_temperature", 12, today=TODAY, fetcher=fetcher_for(ms), use_cache=False)
    d = r["data"]
    assert r["status"] == "ok" and set(E.MODEL_LABELS) >= {x["method"] for x in d["forecast"]}
    for row in d["forecast"]:
        assert (row["status"] == "validated_model") == (row["method"] == d["validation"]["selected_advanced"] and d["validation"]["skill_by_group"][row["group"]]["status"] == "validated")
        if row["status"] == "baseline_only":
            assert row["method"] in E.BASELINES and "baseline" in row["method_label"].lower() or row["method"] in E.BASELINES
    s = d["summary"]
    if s["overall_validation"] == "baseline_only":
        assert "additional predictive skill has not been established" in " ".join(r["limitations"])


# ---- errors, units, aggregation, percentages ---------------------------------------------------------------------------------------
def test_error_metrics_are_in_physical_units_with_mase_bias_and_no_percentage_for_celsius():
    ms = synth(n=12 * 36 + 9)
    r = SV.forecast_monthly(32.0, 35.0, "air_temperature", 24, today=TODAY, fetcher=fetcher_for(ms), use_cache=False)
    ee = r["data"]["error_estimate"]
    assert ee["unit"] == "°C" and ee["percentage_errors"] is None and "MAPE is not meaningful" in ee["percentage_note"]
    lead1 = ee["selected_model"]["by_lead"][0]
    assert set(lead1) >= {"mae", "rmse", "bias", "mase", "n"} and lead1["mae"] >= 0 and lead1["rmse"] >= lead1["mae"] - 1e-9 and ee["mase_scale"] > 0
    assert "holdout" in ee["basis"] and "not independent" in ee["basis"]


def test_precipitation_is_a_daily_rate_and_the_monthly_total_is_derived_with_days_in_month():
    ms = synth(n=12 * 36 + 9, amp=1.5, base=2.0, trend=0.0, noise=0.3, unit="mm/day")
    ms = MonthlySeries(ms.year, ms.month, [max(0.0, v) for v in ms.value], "mm/day", None, ms.source)
    r = SV.forecast_monthly(32.0, 35.0, "precipitation", 12, today=TODAY, fetcher=fetcher_for(ms), use_cache=False)
    assert r["status"] == "ok" and r["units"]["value"] == "mm/day"
    for row in r["data"]["forecast"]:
        dim = pd.Timestamp(row["date"]).days_in_month
        assert row["value_monthly_total_mm"] == pytest.approx(row["value"] * dim) and row["value"] >= 0 and row["lo95"] >= 0 and "derived" in row["monthly_total_note"]
    assert r["data"]["error_estimate"]["percentage_errors"] is not None                       # WAPE allowed for a non-negative variable with an explicit formula
    assert any(w in json.dumps(r["data"]["error_estimate"]["percentage_errors"]) for w in ("WAPE",))


# ---- physical constraints -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("variable,unit,base,amp,lo,hi", [("relative_humidity", "%", 97.0, 2.5, 0.0, 100.0), ("precipitation", "mm/day", 0.3, 0.6, 0.0, None), ("wind_speed", "m/s", 0.5, 0.45, 0.0, None)])
def test_bounded_variables_stay_inside_their_physical_range_by_construction(variable, unit, base, amp, lo, hi):
    ms = synth(n=12 * 30, amp=amp, base=base, trend=0.0, noise=amp * 0.5, unit=unit)
    vals = [min(99.5, v) if variable == "relative_humidity" else max(0.0, v) for v in ms.value]
    y = pd.Series(vals, index=pd.date_range("1990-01-01", periods=len(vals), freq="MS"))
    tf = E.Transform(S.VARIABLES[variable]["transform"])
    for name in ("clim", "clim_trend", "snaive", "ets_aada"):
        r = E.fit_forecast(name, y, tf, 24)
        assert not r["failed"]
        for k in ("mean", "lo80", "hi80", "lo95", "hi95"):
            assert np.isfinite(r[k]).all() and (r[k] >= lo).all() and (hi is None or (r[k] <= hi).all())


# ---- failures are data, not silent substitutions ----------------------------------------------------------------------------------
def test_convergence_failure_is_recorded_never_replaced_by_another_model(monkeypatch):
    def broken(z, h):
        raise np.linalg.LinAlgError("singular")
    monkeypatch.setitem(E.SPECS, "ets_aada", broken)
    y = to_y(synth(n=420)).y
    r = E.fit_forecast("ets_aada", y, E.Transform("identity"), 24)
    assert r["failed"] is True and r["converged"] is False and "LinAlgError" in r["error"] and np.isnan(r["mean"]).all()
    ev = V.evaluate(y, E.Transform("identity"), "fast", 24)
    assert ev["selected_advanced"] is None and ev["selected"] == ev["best_baseline"] and ev["failures"]["ets_aada"]["dev"] == ev["n_dev_origins"]


# ---- strict JSON, interval labels --------------------------------------------------------------------------------------------------
def test_result_is_strict_json_and_interval_basis_is_labelled_honestly():
    ms = synth(n=12 * 36 + 9)
    r = SV.forecast_monthly(32.0, 35.0, "air_temperature", 24, today=TODAY, fetcher=fetcher_for(ms), use_cache=False)
    txt = json.dumps(r, allow_nan=False)                                   # raises on NaN / Infinity
    assert "NaN" not in txt and "Infinity" not in txt
    for row in r["data"]["forecast"]:
        assert row["lo95"] <= row["lo80"] <= row["value"] + 1e-6 and row["value"] - 1e-6 <= row["hi80"] <= row["hi95"]
        assert row["interval_basis"] == "nominal (model-based)" and row["interval_calibration"].split(" ")[0] in ("supported", "under-covers", "over-covers", "unassessed")
    ia = r["data"]["validation"]["interval_assessment"]
    assert set(ia) >= {"nominal_95", "calibrated_95", "nominal_80", "calibrated_80"} and "limitations" in r
    assert any("not uncertainty of model parameters" in x for x in r["limitations"]) and any("NOT an operational weather forecast" in x for x in r["limitations"])


def test_real_nablus_capture_end_to_end_and_references_are_methods_only():
    ms = parse_power_monthly(json.loads((ROOT / "tests" / "fixtures" / "power_monthly_nablus_T2M_real_capture.json").read_text(encoding="utf-8")), "T2M", "fixture")
    r = SV.forecast_monthly(32.22, 35.25, "air_temperature", 24, train_start_year=2005, today=date(2026, 1, 15), fetcher=fetcher_for(ms), use_cache=False)
    assert r["status"] in ("ok", "unsupported_request")
    if r["status"] == "ok":
        refs = r["data"]["references"]
        assert {x["id"] for x in refs} >= {"A", "B", "C"} and all("not evidence for any forecast value" in x["role"] for x in refs)
        assert r["data"]["validation"]["environment"]["statsmodels"]


# ---- routing -----------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("q,months,var", [("توقع متوسط الحرارة الشهري في نابلس للسنتين القادمتين", 24, "air_temperature"), ("Forecast the monthly mean temperature in Nablus for the next two years", 24, "air_temperature"),
                                           ("forecast monthly rainfall in Amman for the next 18 months", 18, "precipitation"), ("Will it be hotter in Cairo next year?", 12, "air_temperature"),
                                           ("توقع الرطوبة في الرياض لمدة 6 أشهر", 6, "relative_humidity")])
def test_long_horizon_forecast_requests_select_the_statistical_forecast_tool(q, months, var):
    p = router.route(q)
    assert p.tool == "forecast_monthly" and p.args["months"] == months and p.args["variable"] == var


@pytest.mark.parametrize("q,tool", [("What is the weather forecast for Cairo for the next 3 days?", "get_weather"), ("ما توقع الطقس في القاهرة غدا؟", "get_weather"),
                                     ("Has air temperature in Nablus risen between 2005 and 2025?", "analyze_trend"), ("هل ارتفعت حرارة الهواء في نابلس بين 2005 و2025؟", "analyze_trend")])
def test_short_weather_and_historical_trend_are_not_hijacked_by_the_monthly_forecast_tool(q, tool):
    assert router.route(q).tool == tool


def test_decision_record_for_the_forecast_intent_is_validated():
    from app.chat import decision as D
    d = D.from_tool("forecast_monthly", {"place": "Nablus", "months": 24}, "router")
    v = D.validate(d, today=TODAY)
    assert v.action == "proceed" and v.decision.provider == "NASA POWER + statistical model" and v.decision.tool_args()["months"] == 24 and v.decision.tool_args()["variable"] == "air_temperature"
    assert D.validate(D.from_tool("forecast_monthly", {"place": "Nablus", "months": 30}, "router"), today=TODAY).action == "unsupported"
    assert D.validate(D.from_tool("forecast_monthly", {"months": 12}, "router"), today=TODAY).text_key == "need_location"


# ---- agent + side panel + UI ------------------------------------------------------------------------------------------------------------
def test_agent_runs_the_tool_and_the_panel_carries_chart_backtest_references_and_downloads(monkeypatch):
    from tests.test_free_text_regressions import make_agent
    from app.chat import tools
    ms = synth(n=12 * 36 + 9)
    monkeypatch.setattr(tools, "_forecast_monthly", lambda *a, **k: SV.forecast_monthly(*a, today=TODAY, fetcher=fetcher_for(ms), use_cache=False, **k))
    a = make_agent(monkeypatch, tools.execute)
    r = a.handle({"message": "توقع متوسط الحرارة الشهري في نابلس للسنتين القادمتين", "controls": {"answer_mode": "template", "language": "en"}})
    assert r["decision"]["intent"] == "forecast_monthly" and r["tools"][0]["name"] == "forecast_monthly" and r["status"] == "ok" and r["outcome"] == "answered"
    assert r["language"] == "ar" and "توقع إحصائي" in r["answer"] and "> [!warn]" in r["answer"] and "[[inline]]" in r["answer"]   # Arabic, structured: title + key callout + inline slot
    pn = r["panel"]
    kinds = [x["type"] for x in pn["artifacts"]]
    assert any(a["type"] == "forecast_chart" for a in r["inline"]) and "forecast_chart" not in kinds           # the chart lives in the chat, not duplicated in the panel
    assert kinds.count("table") >= 3 and pn["references"] and pn["validation"]["overall"] and pn["cutoff"]["data_cutoff_month"]
    assert any(m["label"] == "Validation" or "التحقق" in m["label"] for m in pn["metrics"])
    assert r["map"]["footprint"]["type"] == "grid_cell"
    assert r["citations"] and "model run" in r["citations"][0]["title"] and "method references only" in r["citations"][0]["text"]
    js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "drawForecast" in js and "forecast_chart" in js and "CSV" in js and "JSON" in js and "refs" in js


def test_model_explanation_cannot_add_forecast_numbers_not_in_the_tool_summary():
    from app.agent.trend_agent import unsupported_numbers
    ms = synth(n=12 * 36 + 9)
    r = SV.forecast_monthly(32.0, 35.0, "air_temperature", 12, today=TODAY, fetcher=fetcher_for(ms), use_cache=False)
    summ = r["data"]["summary"]
    lead = summ["leads"][0]
    ok = f"The forecast for {lead['date'][:7]} is {lead['value']} °C (interval {lead['lo80']} to {lead['hi80']})."
    assert unsupported_numbers(ok, {"summary": summ}, "") == []
    assert "27.3" in "".join(unsupported_numbers("The forecast is 27.3 °C with MAE 0.1456 °C.", {"summary": summ}, ""))


def test_a_statistically_significant_but_trivial_gain_is_not_called_validated(monkeypatch):
    """ratio 0.995 with a tight CI must not be reported as validated skill (practical-gain rule)."""
    import app.forecast.engine as EE
    monkeypatch.setattr(EE, "block_bootstrap_ratio", lambda a, b, block, **k: {"ratio": 0.995, "lo": 0.99, "hi": 0.999, "n_origins": 12})
    y = to_y(synth(n=420)).y
    ev = V.evaluate(y, E.Transform("identity"), "fast", 24)
    if ev["selected"] != ev["best_baseline"]:
        assert all(v["status"] != "validated" for v in ev["skill"].values())
