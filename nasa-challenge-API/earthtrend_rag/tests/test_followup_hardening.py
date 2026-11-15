"""Follow-up hardening tests (offline). Series are SYNTHETIC unless stated; no real API is used here."""
import json
import multiprocessing as mp
import time
from datetime import datetime, timezone
from types import SimpleNamespace

import numpy as np
import pytest
from google.genai import errors

from app.agent.trend_agent import TrendAgent, period_is_ambiguous, reconcile_years, unsupported_numbers
from app.analysis.timeseries import MonthlySeries
from app.analysis.trend import analyze_series

from app.llm.base import LLMError, UsageTracker, next_pacific_midnight, pacific_day
from app.tools.trend_tool import run_trend_analysis

SYN = {"provider": "SYNTHETIC test data (not NASA)", "dataset": "synthetic", "fill_value": -999.0}
VAR, REG = {"id": "air_temperature", "name": "Synthetic variable"}, {"name": "x", "lat": 0.0, "lon": 0.0, "type": "point"}


def series(y0=2000, y1=2024, slope=0.03, amp=5.0, seed=0, noise=0.4, drop_years=(), const=False):
    r = np.random.default_rng(seed)
    yy, mm, vv = [], [], []
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            yy.append(y), mm.append(m)
            if y in drop_years and m > 3:
                vv.append(None)
            else:
                vv.append(10.0 if const else round(float(15 + slope * (y - y0) + amp * np.sin(2 * np.pi * m / 12) + r.normal(0, noise)), 3))
    return MonthlySeries(yy, mm, vv, "°C", None, dict(SYN))


# ---- JSON strictness / dropped-year adjacency ------------------------------------------------------------------

@pytest.mark.parametrize("kw", [dict(const=True), dict(y0=2010, y1=2024), dict(drop_years=(2005, 2012)), dict(slope=0.0)])
def test_result_is_strict_json_for_edge_series(kw):
    r = analyze_series(series(**kw), variable=VAR, region=REG, start_year=kw.get("y0", 2000), end_year=kw.get("y1", 2024),
                       fill_values=[-999.0])
    json.dumps(r, allow_nan=False)                                   # raises on NaN / Infinity


def test_tool_output_is_strict_json_even_for_a_constant_series():
    r = run_trend_analysis({"variable": "air_temperature", "latitude": 1.0, "longitude": 1.0, "start_year": 2000, "end_year": 2024},
                           fetcher=lambda *a, **k: series(const=True))
    assert r["status"] == "ok" and r["test"]["p_value"] == 1.0
    json.dumps(r, allow_nan=False)


def test_dropped_years_disable_adjacency_based_diagnostics_and_say_so():
    r = analyze_series(series(drop_years=(2005, 2012), seed=3), variable=VAR, region=REG, start_year=2000, end_year=2024,
                       fill_values=[-999.0], aggregation="annual")
    d = r["diagnostics"]["autocorrelation_annual"]
    assert d["contiguous_years"] is False and d["ljung_box_p"] is None and d["hamed_rao_factor_applied"] == 1.0
    assert "skipped" in d["autocorrelation_check"]
    assert {x["year"] for x in r["data_quality"]["years_dropped"]} == {2005, 2012}
    assert "unweighted" in d["weighting"]


def test_contiguous_years_keep_the_full_check():
    d = analyze_series(series(seed=4), variable=VAR, region=REG, start_year=2000, end_year=2024, fill_values=[-999.0],
                       aggregation="annual")["diagnostics"]["autocorrelation_annual"]
    assert d["contiguous_years"] is True and d["ljung_box_p"] is not None


# ---- period reconciliation: only unambiguous periods are patched ----------------------------------------------------

@pytest.mark.parametrize("q,expected", [
    ("هل ارتفعت الحرارة في نابلس بين 2005 و2025؟", {"start_year": 2005, "end_year": 2025}),
    ("did rainfall in Texas fall from 2010 to 2020?", {"start_year": 2010, "end_year": 2020}),
    ("اتجاه الحرارة في القاهرة 2000-2020", {"start_year": 2000, "end_year": 2020}),
    ("هل ارتفعت الحرارة في الرياض منذ ٢٠٠٥؟", {"start_year": 2005}),
])
def test_clear_single_period_is_enforced(q, expected):
    assert not period_is_ambiguous(q)
    fixed, notes = reconcile_years(q, {"variable": "air_temperature", "start_year": 1999, "end_year": 2024})
    for k, v in expected.items():
        assert fixed[k] == v
    assert notes


@pytest.mark.parametrize("q", [
    "قارن الحرارة في نابلس بين 2005 و2015 وبين 2016 و2025",       # two periods
    "هل ارتفعت الحرارة بين 2005 و2025 وكانت 2010 الأشد حرًا؟",    # extra year
    "compare 2005 and 2025 temperature in Cairo",                    # two years, no period marker besides 'and'? still two boundaries
    "هل ارتفعت الحرارة في 2010 و 2020 و 2023؟",                     # three years
])
def test_ambiguous_questions_are_never_patched(q):
    args = {"start_year": 2001, "end_year": 2009}
    assert reconcile_years(q, args) == (args, []) or period_is_ambiguous(q)
    if period_is_ambiguous(q):
        assert reconcile_years(q, args) == (args, [])


def test_agent_asks_for_clarification_instead_of_running_on_an_ambiguous_period():
    runs = []
    fc = SimpleNamespace(name="analyze_trend", args={"variable": "air_temperature", "region": "Nablus", "start_year": 2005, "end_year": 2025}, id=None)
    resp = SimpleNamespace(text=None, function_calls=[fc], candidates=[SimpleNamespace(content=SimpleNamespace(role="model", parts=[]))],
                           usage_metadata=None)

    class LLM:
        model = "fake"
        last_model_used = "fake"
        def generate_raw(self, *a, **k):
            return resp
    a = TrendAgent(LLM(), lambda args: runs.append(args) or {}).ask("قارن الحرارة في نابلس بين 2005 و2015 وبين 2016 و2025")
    assert a.status == "clarification" and not runs and a.analysis is None and a.fallback_reason == "ambiguous_period"


# ---- number guard ------------------------------------------------------------------------------------------------------

RES = {"test": {"p_value": 0.139, "alpha": 0.05, "kendall_tau": 0.2381, "sen_slope": {"value": 0.038, "ci_level": 0.95, "ci_low": -0.0137, "ci_high": 0.0798}}}


def test_percent_ci_level_is_accepted():
    assert unsupported_numbers("مجال الثقة 95% ، p = 0.139 وعتبة الدلالة 0.05", RES) == []


@pytest.mark.parametrize("text", ["p = 3.25e-9", "الميل 0.38 درجة لكل سنة", "p = 1e-5", "الميل -0.038", "ثقة 99%", "الميل 3.8"])
def test_invented_or_distorted_numbers_are_rejected(text):
    assert unsupported_numbers(text, RES) != []


# ---- quota bookkeeping ------------------------------------------------------------------------------------------------

def test_pacific_day_boundary_and_reset_marker_default():
    t = datetime(2026, 11, 14, 19, 41, tzinfo=timezone.utc).timestamp()          # 11:41 PST on the 14th
    assert pacific_day(t) == "2026-11-14"
    assert pacific_day(datetime(2026, 11, 15, 7, 59, tzinfo=timezone.utc).timestamp()) == "2026-11-14"   # still the 14th in Pacific
    assert pacific_day(datetime(2026, 11, 15, 8, 1, tzinfo=timezone.utc).timestamp()) == "2026-11-15"    # new Pacific day at 08:00 UTC
    assert next_pacific_midnight(t) == datetime(2026, 11, 15, 8, 0, tzinfo=timezone.utc).timestamp()


def test_exhausted_marker_expires_and_is_purged(tmp_path):
    u = UsageTracker(tmp_path / "u.json", 10)
    u.mark_exhausted("m", 3600)
    assert u.exhausted_until("m") > time.time() + 3500
    data = json.loads((tmp_path / "u.json").read_text())
    data["_exhausted"]["m"] = time.time() - 5                                    # simulate an expired marker
    (tmp_path / "u.json").write_text(json.dumps(data))
    assert u.exhausted_until("m") < time.time()                                  # expired -> model usable again
    u.reserve("other")                                                           # any write purges expired markers
    assert "_exhausted" not in json.loads((tmp_path / "u.json").read_text())


def test_marker_without_retry_delay_lasts_until_pacific_midnight(tmp_path):
    u = UsageTracker(tmp_path / "u.json", 10)
    u.mark_exhausted("m", None)
    assert abs(u.exhausted_until("m") - next_pacific_midnight()) < 2


def test_counters_survive_restart_and_cap_applies(tmp_path):
    p = tmp_path / "u.json"
    a = UsageTracker(p, 3)
    a.reserve("m"), a.reserve("m")
    b = UsageTracker(p, 3)                                                       # "restart": new object, same file
    b.reserve("m")
    from app.llm.base import BudgetExceeded
    with pytest.raises(BudgetExceeded):
        UsageTracker(p, 3).reserve("m")
    assert b.today()["models"]["m"]["requests"] == 3


def _hammer(args):
    path, n = args
    t = UsageTracker(__import__("pathlib").Path(path), 0)
    for _ in range(n):
        t.reserve("m")


def test_concurrent_threads_and_processes_do_not_lose_increments(tmp_path):
    import concurrent.futures as cf
    p = tmp_path / "u.json"
    with cf.ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda _: UsageTracker(p, 0).reserve("m"), range(30)))
    assert UsageTracker(p, 0).today()["models"]["m"]["requests"] == 30
    with mp.get_context("spawn").Pool(3) as pool:
        pool.map(_hammer, [(str(p), 8)] * 3)
    assert UsageTracker(p, 0).today()["models"]["m"]["requests"] == 30 + 24
    json.loads(p.read_text())                                                    # file is always complete JSON


# ---- deadline across fallback models, and tool-once under client retries --------------------------------------------

def api_error(code, retry_after=None):
    e = errors.APIError(code, {"error": {"code": code, "status": "X", "message": "boom", "details": []}})
    if retry_after is not None:
        e.response = SimpleNamespace(headers={"retry-after": str(retry_after)})
    return e


class Scripted:
    def __init__(self, script):
        self.script, self.calls = script, []

    def generate_content(self, model, contents, config):
        self.calls.append(model)
        step = self.script[model].pop(0) if isinstance(self.script, dict) else self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def mk(tmp_path, script, fallbacks=()):
    c = GeminiClient(api_key="test-key-not-real", model="m1", fallback_models=list(fallbacks), usage=UsageTracker(tmp_path / "u.json", 0))
    c._client = SimpleNamespace(models=Scripted(script))
    return c


def good(text=None, call=None):
    fcs = [SimpleNamespace(name=call[0], args=call[1], id="call-1")] if call else []
    return SimpleNamespace(text=text, function_calls=fcs, usage_metadata=SimpleNamespace(prompt_token_count=3, candidates_token_count=2),
                           candidates=[SimpleNamespace(content=SimpleNamespace(role="model", parts=[]))])


