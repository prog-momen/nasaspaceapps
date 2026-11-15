"""Explaining terms to an ordinary user: built-in glossary -> documentation (RAG) -> web (concepts only). Data values never come from the web.
FAKE Claude client (no network, no credits). Live behaviour is covered in tests/integration/test_claude_live.py."""
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.chat import glossary as GL
from app.chat import tools
from app.chat.agent import ChatAgent
from app.chat.sessions import SessionStore
from app.config import KNOWLEDGE_COLLECTION
from tests.test_free_text_regressions import FakeResp, FC, FakeRetriever, FakeSvc, NABLUS_Q, power_fixture, stub_weather  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
AR_RX = re.compile(r"[؀-ۿ]")
INSUFFICIENT = SimpleNamespace(answer_type="insufficient_knowledge", answer="", sources=[], warnings=[], llm={})


class WebLLM:
    """interpret_request -> `knowledge`; web_search tool call -> a plain explanation with sources; anything else -> empty text."""
    model = "claude-haiku-5-5"
    last_model_used = "claude-haiku-5-5"

    def __init__(self, web_text="## Moving average\n\n> [!info] A moving average smooths ups and downs by averaging nearby values.\n\nHypothetical example: averaging 3 days of values.", intent="knowledge"):
        self.calls, self.web_text, self.intent = [], web_text, intent

    def generate_raw(self, contents, system, tools=None, **kw):
        self.calls.append({"tools": [t.get("type") or t.get("name") for t in (tools or [])], "user": contents if isinstance(contents, str) else str(contents)})
        if tools and tools[0].get("type") == "web_search_20250305":
            return SimpleNamespace(text=self.web_text, function_calls=[], web_sources=[{"url": "https://en.wikipedia.org/wiki/Moving_average", "title": "Moving average - Wikipedia", "snippet": "smoothing"}],
                                   candidates=[SimpleNamespace(content=[])], usage_metadata=None)
        if tools and tools[0].get("name") == "interpret_request":
            return FakeResp([FC({"intent": self.intent})])
        return SimpleNamespace(text="", function_calls=[], web_sources=[], candidates=[], usage_metadata=None)


def agent(monkeypatch, llm=None, runner=None):
    monkeypatch.setattr("app.chat.agent.load_llm_key", (lambda: "k") if llm else (lambda: None))
    svc = FakeSvc(); svc._llm = llm
    svc.retrievers = {KNOWLEDGE_COLLECTION: FakeRetriever()}
    svc.pipeline = SimpleNamespace(llm=llm, min_dense_score=0.5, _select=lambda items, q=None: [], answer=lambda *a, **k: INSUFFICIENT)
    return ChatAgent(svc, SessionStore(), tool_runner=runner)


# ---- glossary --------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("q,term", [("شو يعني أنوميات؟", "anomaly"), ("what does anomaly mean?", "anomaly"), ("ما معنى قيمة p؟", "pvalue"), ("what is NDVI", "ndvi"), ("اشرح لي خط الأساس", "baseline"),
                                     ("what is a prediction interval", "interval"), ("ما هو الاختبار الرجعي", "backtest")])
def test_glossary_recognises_plain_requests_for_a_meaning(q, term):
    assert term in [g["id"] for g in GL.find_terms(q)] and GL.asks_for_meaning(q)


def test_glossary_answers_instantly_without_any_model_and_is_arabic_or_english_by_the_message(monkeypatch):
    a = agent(monkeypatch)
    ar = a.handle({"message": "شو يعني أنوميات؟", "controls": {"language": "en"}})
    assert ar["answer_source"] == "glossary" and ar["language"] == "ar" and AR_RX.search(ar["answer"]) and "> [!info]" in ar["answer"] and ar["outcome"] == "answered" and ar["tools"] == [] and ar["model"] is None
    en = a.handle({"message": "what does p-value mean?", "session_id": ar["session_id"], "controls": {"language": "ar"}})
    assert en["answer_source"] == "glossary" and en["language"] == "en" and "surprising" in en["answer"]


def test_glossary_entries_contain_no_place_specific_measurements():
    blob = " ".join(g["plain"]["en"] + g["app"]["en"] for g in GL.G)
    assert not re.search(r"Nablus|Cairo|Amman|Riyadh|20[0-3]\d", blob)


# ---- web: concepts only -------------------------------------------------------------------------------------------------------------------
def test_unknown_concept_is_explained_with_web_search_and_sources_but_labelled_as_general(monkeypatch):
    llm = WebLLM()
    a = agent(monkeypatch, llm)
    r = a.handle({"message": "what is a moving average?", "controls": {"language": "en"}})
    assert r["answer_source"] == "web" and r["status"] == "ok" and r["model"] == "claude-haiku-5-5"
    assert r["citations"][0]["kind"] == "web" and r["citations"][0]["url"].startswith("https://") and "not app data" in r["answer"] and "[1]" in r["answer"]
    web_calls = [c for c in llm.calls if "web_search_20250305" in c["tools"]]
    assert len(web_calls) == 1


def test_follow_up_what_does_that_mean_uses_the_previous_answer_as_context(monkeypatch, power_fixture):
    llm = WebLLM()
    llm.intent = "trend"
    a = agent(monkeypatch, llm, tools.execute)
    first = a.handle({"message": NABLUS_Q, "controls": {"language": "en", "answer_mode": "auto"}})
    llm.intent = "knowledge"
    r = a.handle({"message": "what does Sen's slope mean again?", "session_id": first["session_id"], "controls": {"language": "en"}})
    assert r["answer_source"] == "glossary"                           # known term: instant built-in explanation


def test_the_web_is_never_used_for_data_requests(monkeypatch):
    llm = WebLLM(intent="weather_forecast")
    llm.web_text = "Cairo will be 31 °C in 2027."
    a = agent(monkeypatch, llm, stub_weather)
    r = a.handle({"message": "What is the weather forecast for Cairo for the next 3 days?", "controls": {"language": "en"}})
    assert r["tools"][0]["name"] == "get_weather" and not [c for c in llm.calls if "web_search_20250305" in c["tools"]]


def test_a_web_answer_that_smuggles_in_data_about_a_place_or_year_is_refused(monkeypatch):
    for bad in ("The anomaly in Cairo was 2 °C in 2019.", "In 2020 it was warmer."):
        a = agent(monkeypatch, WebLLM(web_text=bad))
        r = a.handle({"message": "what is a moving average?", "controls": {"language": "en"}})
        assert r["answer_source"] != "web" and r["answer"].startswith("Insufficient resources")


def test_questions_that_name_a_place_or_period_are_not_treated_as_concepts(monkeypatch):
    llm = WebLLM()
    a = agent(monkeypatch, llm)
    r = a.handle({"message": "what is the average temperature in Cairo in 2019?", "controls": {"language": "en"}})
    assert not [c for c in llm.calls if "web_search_20250305" in c["tools"]] and r["answer_source"] != "web"


def test_when_claude_is_unavailable_there_is_no_web_and_no_other_model(monkeypatch):
    a = agent(monkeypatch)                                           # no key: glossary still works, unknown concepts get the honest message
    r = a.handle({"message": "what is a moving average?", "controls": {"language": "en", "answer_mode": "template"}})
    assert r["answer"].startswith("Insufficient resources") and r["answer_source"] == "template"


def test_server_tool_is_passed_through_the_central_client_unchanged_and_sources_are_extracted():
    from app.llm import claude_client as cc
    tool = {"type": "web_search_20250305", "name": "web_search", "max_uses": 2}
    assert cc.to_tools([tool]) == [tool]
    block_text = SimpleNamespace(type="text", text="hello", citations=[SimpleNamespace(url="https://a.example/x", title="A", cited_text="snip")])
    block_res = SimpleNamespace(type="web_search_tool_result", content=[SimpleNamespace(url="https://b.example/y", title="B")])
    resp = SimpleNamespace(content=[block_res, block_text], usage=SimpleNamespace(input_tokens=1, output_tokens=1), stop_reason="end_turn")
    w = cc._wrap(resp, "claude-haiku-5-5")
    assert w.text == "hello" and {s["url"] for s in w.web_sources} == {"https://a.example/x", "https://b.example/y"}


def test_the_explanation_prompt_asks_for_plain_language_and_the_web_prompt_forbids_data():
    from app.chat import agent as AG
    assert "ORDINARY reader" in AG.EXPLAIN_SYSTEM and "NEVER state measurements" in AG.WEB_SYSTEM


# ---- chat box layout ---------------------------------------------------------------------------------------------------------------------
def test_composer_lives_inside_the_chat_box_with_at_most_five_shortcuts_and_60_percent_width():
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    box = html[html.index('class="chat-box"'):html.index("</aside>")]
    assert 'id="composer"' in box.split('class="dock"')[1] and 'id="examples"' in box.split('class="dock"')[1] and box.index('id="messages"') < box.index('class="dock"')
    js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    import json as _j
    for lang in ("ar", "en"):
        seg = js[js.index(f"  {lang}: {{"):]
        arr = re.search(r"examples: (\[.*?\])[,}]", seg, re.S).group(1)
        assert len(_j.loads(arr)) <= 5
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    assert "grid-template-columns:minmax(0,2fr) minmax(0,3fr)" in css                      # chat = 3/5 = 60%
    assert ".chat-box .messages{" in css and "overflow:visible" in css and ".tablewrap{max-height:none" in css and "position:sticky;bottom:0" in css


def test_frontend_script_is_syntactically_valid_javascript():
    import shutil, subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    r = subprocess.run([node, "--check", str(ROOT / "frontend" / "app.js")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_long_historical_weather_gives_whole_period_statistics_not_just_the_first_16_days():
    from app.providers import base
    n = 365
    days = [f"2019-{(i // 31) % 12 + 1:02d}-{i % 28 + 1:02d}" for i in range(n)]
    d = {"time": days, "temperature_2m_max": [20.0 + (i % 10) for i in range(n)], "temperature_2m_min": [10.0 + (i % 5) for i in range(n)], "precipitation_sum": [1.0] * n, "wind_speed_10m_max": [12.0] * n}
    res = base.envelope("Open-Meteo", "Archive", "historical_weather", "ok", data={"daily": d}, units={}, actual={"grid": {"latitude": 1, "longitude": 2}, "timezone": "UTC", "period": {"first": days[0], "last": days[-1]}, "source_type": "reanalysis"}, cache="miss", artifacts=[])
    s = tools._weather_summary(res)
    ps = s["period_stats"]
    assert len(s["daily"]) == 16 and ps["n_days"] == 365 and ps["total_precip_mm"] == 365.0 and ps["mean_tmax_c"] == pytest.approx(24.5, abs=0.05) and "not a true daily mean" in ps["midrange_note"]
    from app.chat import inline as IN
    out = IN.build_inline("get_weather", {"result": res, "summary": s, "artifacts": []}, "average temperature in Cairo in 2019", "en")
    assert out and out[0]["compact"] and out[0]["columns"][0] == "Month" and len(out[0]["rows"]) >= 6                # a monthly summary, not 16 raw days


# ---- long conversation context (64K-token budget) -----------------------------------------------------------------------------------------------
def _fill(sess, n, long_text=""):
    for i in range(n):
        sess.add("user", f"question number {i} {long_text}")
        sess.add("assistant", f"answer number {i} {long_text}", {"decision": {"intent": "trend", "place": f"Place{i}", "variable": "air_temperature", "start_year": 2005, "end_year": 2025}, "facts": {"p_value": 0.006, "n_used": 21}})


def test_the_model_re_reads_the_whole_conversation_with_numbered_turns_and_what_was_understood(monkeypatch):
    a = agent(monkeypatch)
    s = a.store.get(None)
    _fill(s, 30)
    block = a._conversation_block(s)
    assert block.count("[turn ") == 30 and "[turn 1]" in block and "[turn 30]" in block and "place=Place0" in block and "result: p_value=0.006" in block and "omitted" not in block


def test_over_budget_the_middle_is_dropped_but_first_and_latest_turns_are_kept_and_the_omission_is_stated(monkeypatch):
    from app.chat import agent as AG
    a = agent(monkeypatch)
    s = a.store.get(None)
    _fill(s, 90, long_text="x" * 900)
    block = a._conversation_block(s)
    assert len(block) <= AG.CONTEXT_TOKENS * AG.CHARS_PER_TOKEN + 2000
    assert "[turn 1]" in block and "[turn 2]" in block and "[turn 90]" in block and "earlier turn(s) omitted" in block and "[turn 3]" not in block and block.count("[turn ") < 90


def test_the_interpretation_request_carries_an_old_turn_so_a_reference_to_it_can_be_resolved(monkeypatch, power_fixture):
    llm = WebLLM(intent="trend")
    a = agent(monkeypatch, llm, tools.execute)
    first = a.handle({"message": NABLUS_Q, "controls": {"language": "en"}})
    for i in range(6):                                                    # six unrelated turns in between
        a.handle({"message": f"what does p-value mean? {i}", "session_id": first["session_id"], "controls": {"language": "en"}})
    llm.calls.clear()
    a.handle({"message": "do the first analysis again but for Amman", "session_id": first["session_id"], "controls": {"language": "en"}})
    sent = next(c["user"] for c in llm.calls if "interpret_request" in c["tools"])
    assert "[turn 1]" in sent and "Has air temperature in Nablus risen between 2005 and 2025?" in sent and "intent=trend" in sent and "start_year=2005" in sent


def test_the_decision_can_record_which_earlier_turn_it_refers_to():
    from app.chat import decision as D
    d = D.from_model({"intent": "trend", "place": "Amman", "refers_to_turn": 1, "start_year": 2005, "end_year": 2025})
    assert d.refers_to_turn == 1 and d.to_dict()["refers_to_turn"] == 1


def test_questions_about_the_conversation_itself_are_answered_from_it_without_tools_or_web(monkeypatch, power_fixture):
    llm = WebLLM(intent="trend")
    a = agent(monkeypatch, llm, tools.execute)
    first = a.handle({"message": NABLUS_Q, "controls": {"language": "en", "answer_mode": "auto"}})
    llm.intent = "knowledge"
    r = a.handle({"message": "what was my first question?", "session_id": first["session_id"], "controls": {"language": "en"}})
    assert r["status"] == "ok" and r["tools"] == [] and not [c for c in llm.calls if "web_search_20250305" in c["tools"]]
    sent = [c["user"] for c in llm.calls][-1]
    assert "[turn 1]" in sent and NABLUS_Q in sent                                              # the model was given the conversation and nothing else to answer from
    nokey = agent(monkeypatch)
    r1 = nokey.handle({"message": "هل ارتفعت حرارة الهواء في نابلس بين 2005 و2025؟", "controls": {"answer_mode": "template", "language": "en"}})
    r2 = nokey.handle({"message": "شو كان سؤالي الأول؟", "session_id": r1["session_id"], "controls": {"answer_mode": "template", "language": "en"}})
    assert "1. هل ارتفعت" in r2["answer"] and r2["answer_source"] == "template"                 # deterministic fallback: lists the user's own questions
