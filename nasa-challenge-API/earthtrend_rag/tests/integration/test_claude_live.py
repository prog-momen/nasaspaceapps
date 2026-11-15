"""LIVE tests against the RUNNING prototype (http://127.0.0.1:8000) and the real Anthropic API, model claude-haiku-5-5 only (bounded: ~8 requests).
They go through the HTTP API because the local Qdrant index allows a single process. Skipped when the server or the key is not available."""
import httpx
import pytest

from app.config import has_credential

pytestmark = pytest.mark.integration
BASE = "http://127.0.0.1:8000"
HAIKU = "claude-haiku-5-5"


def _up():
    try:
        return httpx.get(BASE + "/api/rag/health", timeout=5).status_code == 200
    except Exception:
        return False


pytestmark = [pytest.mark.integration, pytest.mark.skipif(not has_credential("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not configured"),
              pytest.mark.skipif(not _up(), reason="prototype server is not running")]


def chat(msg, **ctl):
    r = httpx.post(BASE + "/api/chat", json={"message": msg, "controls": {"language": "en", **ctl}}, timeout=150)
    assert r.status_code == 200
    return r.json()


def test_model_is_available_and_is_the_only_one_reported():
    from app.llm.claude_client import ClaudeClient
    assert ClaudeClient().check_model_available()["available"] is True
    h = httpx.get(BASE + "/api/rag/health").json()["components"]
    assert h["llm_model"] == HAIKU and h["llm_allowed_models"] == [HAIKU]


def test_simple_arabic_request_is_answered_in_arabic_by_haiku_with_tool_use():
    r = chat("ما توقع الطقس في القاهرة للأيام الثلاثة القادمة؟")
    assert r["language"] == "ar" and r["status"] == "ok"
    assert r["selected_by"] == "llm_tool_use" and r["decision"]["decided_by"] == "claude" and r["decision"]["intent"] == "weather_forecast"      # real Tool Use
    assert any("؀" <= ch <= "ۿ" for ch in r["answer"]) and r["answer_source"] in ("claude", "template")
    assert (r["model"] == HAIKU) if r["answer_source"] == "claude" else (r["fallback_reason"] == "explanation_validation")      # a rejected rounding/number in the prose falls back to the labelled template


def test_rag_question_returns_a_grounded_answer_with_sources_from_haiku():
    r = chat("What are the MODIS land surface temperature products?")
    assert r["status"] == "ok" and r["answer_source"] == "claude" and r["model"] == HAIKU
    import re
    assert r["citations"] and all(c.get("title") or c.get("source_file") for c in r["citations"])
    cited = {int(x) for x in re.findall(r"\[(\d+)\]", r["answer"])}
    assert cited and cited <= {c["index"] for c in r["citations"]}                      # every marker in the answer points at a real source


def test_real_tool_use_trend_analysis_runs_the_backend_tool_and_explains_only_its_numbers():
    r = chat("Has air temperature in Nablus risen between 2005 and 2025?")
    assert r["selected_by"] == "llm_tool_use" and r["decision"]["intent"] == "trend" and r["decision"]["start_year"] == 2005 and r["decision"]["end_year"] == 2025
    assert r["tools"][0]["name"] == "analyze_trend" and r["tools"][0]["provider"] == "NASA POWER"
    assert r["model"] in (HAIKU, None)                                    # None only if the number/wording check rejected the prose and the labelled template was used
    assert r["answer_source"] in ("claude", "template") and r["outcome"] == "answered"
    if r["answer_source"] == "template":
        assert r["fallback_reason"] == "explanation_validation"


def test_forecast_question_selects_the_monthly_forecast_tool_and_returns_validated_or_baseline_labelled_output():
    """LIVE: Haiku Tool Use + live/cached NASA POWER + the statistical forecast (about 20-30 s cold)."""
    r = chat("توقع متوسط الحرارة الشهري في نابلس للسنتين القادمتين")
    assert r["decision"]["intent"] == "forecast_monthly" and r["decision"]["horizon_months"] == 24 and r["tools"][0]["name"] == "forecast_monthly"
    assert r["status"] == "ok" and r["language"] == "ar" and r["selected_by"] == "llm_tool_use"
    p = r["panel"]
    assert any(a["type"] == "forecast_chart" for a in p["artifacts"]) and p["cutoff"]["data_cutoff_month"] and p["validation"]["overall"] in ("validated_model", "partially_validated", "baseline_only")
    rows = r["raw_result"]["data"]["forecast"]
    assert len(rows) >= 22 and all(x["status"] in ("validated_model", "baseline_only") for x in rows)
