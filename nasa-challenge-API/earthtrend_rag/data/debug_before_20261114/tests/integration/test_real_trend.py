"""REAL NASA POWER API + REAL Gemini function calling. Data are real NASA POWER values (air temperature, NOT land surface temperature)."""
import numpy as np
import pymannkendall as pmk
import pytest

from app.agent.trend_agent import TrendAgent, unsupported_numbers
from app.config import get_settings
from app.llm.gemini_client import GeminiClient
from app.tools.trend_tool import run_trend_analysis

pytestmark = pytest.mark.integration
ARGS = {"variable": "air_temperature", "region": "Amazon", "start_year": 2005, "end_year": 2025}


@pytest.fixture(scope="module")
def real_result():
    return run_trend_analysis(ARGS)           # live HTTP call to power.larc.nasa.gov (cached in data/cache afterwards)


def test_real_power_download_and_analysis(real_result):
    r = real_result
    assert r["status"] == "ok", r
    assert r["source"]["provider"] == "NASA POWER" and r["source"]["endpoint"].startswith("https://power.larc.nasa.gov/api/")
    assert r["units"] == "°C" and r["data_quality"]["valid_months"] >= 240 and r["period_actual"]["first"] == "2005-01"
    assert r["test"]["alpha"] == 0.05 and r["test"]["sen_slope"]["unit"] == "°C/year"
    assert -0.5 < r["test"]["sen_slope"]["value"] < 0.5          # sanity range, not a scientific claim


def test_real_result_matches_reference_library(real_result):
    r = real_result
    if r["aggregation"]["chosen"] != "annual" or "original" not in r["test"]["test_name"]:
        pytest.skip("reference check only for the plain annual Mann-Kendall variant")
    ann = np.array(r["chart"]["y"])
    ref = pmk.original_test(ann)
    assert r["test"]["p_value"] == pytest.approx(ref.p, abs=1e-3) and r["test"]["kendall_tau"] == pytest.approx(ref.Tau, abs=1e-3)


def test_real_gemini_function_calling_runs_tool_and_explains(real_result):
    agent = TrendAgent(GeminiClient())
    a = agent.ask("هل ارتفعت درجة حرارة الهواء في الأمازون بين 2005 و2025؟")
    assert a.tool_calls and a.tool_calls[0]["name"] == "analyze_trend"
    args = a.tool_calls[0]["args"]
    assert args["variable"] == "air_temperature" and int(args["start_year"]) == 2005 and int(args["end_year"]) == 2025
    assert a.analysis["status"] == "ok"
    # whatever produced the text (gemini or template), every number must be traceable to the tool result
    assert unsupported_numbers(a.answer, a.analysis, "2005 2025") == []
    assert str(a.analysis["test"]["sen_slope"]["value"])[:5] in a.answer or a.answer_source == "gemini"
    if not a.analysis["test"]["significant"]:
        assert "البيانات الحالية لا تكفي لتأكيد وجود اتجاه" in a.answer


def test_real_gemini_lst_question_is_not_answered_with_a_verdict():
    a = TrendAgent(GeminiClient()).ask("هل ارتفعت حرارة سطح الأرض بالأمازون بين 2005 و2025؟")
    assert a.tool_calls and a.tool_calls[0]["args"]["variable"] == "land_surface_temperature"
    assert a.status == "data_source_unavailable" and a.analysis.get("test") is None
    assert "ارتفعت بمعدل" not in a.answer
