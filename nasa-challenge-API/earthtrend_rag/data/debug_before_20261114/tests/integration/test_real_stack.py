"""Integration tests: REAL embedding model, REAL Qdrant index, REAL Gemini API calls.

Run:  pytest -m integration -v
Gemini calls count against your project quota (free tier is rate limited).
"""
import time

import numpy as np
import pytest

from app.config import get_settings
from app.evaluation.answer_eval import numbers_supported
from app.evaluation.retrieval_eval import load_eval
from app.llm.gemini_client import GeminiClient

pytestmark = pytest.mark.integration
EVAL = load_eval()


def test_real_embedding_model_is_multilingual_and_consistent(real_service):
    e = real_service.embedder
    q_ar = e.embed_query("ما هو مفتاح FIRMS المطلوب؟")
    d_en = e.embed_documents(["FIRMS requires a free MAP_KEY to download fire detections.",
                              "The capital of France is Paris and it has many museums."])
    assert q_ar.shape[0] == e.dim == d_en.shape[1]
    assert np.isclose(np.linalg.norm(q_ar), 1.0, atol=1e-3)          # normalised
    assert float(q_ar @ d_en[0]) > float(q_ar @ d_en[1])             # Arabic query -> English passage, cross-lingual
    assert np.allclose(q_ar, e.embed_query("ما هو مفتاح FIRMS المطلوب؟"), atol=1e-5)   # deterministic


def test_index_matches_embedder(real_service):
    h = real_service.health()
    assert h["collections"]["earth_knowledge"] > 500
    assert h["collections"]["gemini_platform"] > 50
    assert h["embedding_model"] == get_settings().embedding_model


def test_retrieval_filters_and_scope_isolation(real_service):
    r = real_service.retrievers["earth_knowledge"].retrieve("FIRMS MAP_KEY", top_k=5, filters={"variables": ["wildfires"]})
    assert r.items and all("wildfires" in x.hit.metadata["variables"] for x in r.items)
    # Gemini platform docs must never be served from the Earth collection
    r2 = real_service.retrievers["earth_knowledge"].retrieve("gemini-3.8-flash pricing per million tokens", top_k=5)
    assert not any(x.hit.metadata["source_file"].startswith("google_") for x in r2.items)


def test_real_gemini_model_id_and_call(need_key):
    c = GeminiClient()
    assert c.model == "gemini-3.8-flash"
    res = c.generate("Answer in one short sentence.", "Reply with the word OK.", max_output_tokens=64)
    assert res.text and res.prompt_tokens and res.latency_s > 0


def test_real_gemini_respects_insufficient_context(need_key):
    from app.rag.prompts import SYSTEM_PROMPT, build_user_prompt
    c = GeminiClient()
    ctx = [{"source_file": "x.md", "section": "S", "text": "MOD11C3 is a monthly 0.05 degree land surface temperature product."}]
    res = c.generate(SYSTEM_PROMPT.format(language_name="English"),
                     build_user_prompt("What is the resolution of the VNP46A1 night lights product?", ctx))
    assert res.text.strip().startswith("INSUFFICIENT_CONTEXT")


@pytest.mark.parametrize("item", EVAL["answerable"], ids=lambda i: i["id"])
def test_end_to_end_answerable(real_service, need_key, item):
    time.sleep(2)
    a = real_service.answer(item["q"], language=item.get("lang"))
    assert a.answer_type == "document_answer", (a.answer, a.retrieval)
    assert all(m in a.answer for m in item["must_say"]), a.answer
    cited = [s for s in a.sources if s.cited]
    assert cited, "answer must carry citations"
    res = real_service.retrievers["earth_knowledge"].retrieve(item["q"], top_k=5, soft_filters=a.intent.filters)
    cited_texts = [r.hit.text for r in res.items
                   if any(r.hit.metadata["source_file"] == s.source_file and r.hit.metadata["section"] == s.section for s in cited)]
    assert any(e in t for t in cited_texts for e in item["evidence"]), "a cited source must contain the evidence"
    ok, missing = numbers_supported(a.answer, cited_texts, item["q"])
    assert ok, f"numbers not in cited sources: {missing}"
    assert a.llm["model"] == "gemini-3.8-flash"


@pytest.mark.parametrize("item", [i for i in EVAL["needs_tool"] if i["expect_kind"] != "needs_analysis"], ids=lambda i: i["id"])
def test_end_to_end_data_and_forecast_requests_are_not_answered_from_text(real_service, item):
    a = real_service.answer(item["q"])
    assert a.answer_type == "requires_data_tool" and a.intent.kind == item["expect_kind"] and a.llm == {}


@pytest.mark.parametrize("item", [i for i in EVAL["needs_tool"] if i["expect_kind"] == "needs_analysis"], ids=lambda i: i["id"])
def test_end_to_end_trend_questions_go_through_the_tool(real_service, need_key, item):
    a = real_service.answer(item["q"])
    assert a.intent.kind == "needs_analysis"
    # either the tool ran (tool_analysis) or the model asked for a missing period/place; never a number from text
    assert a.answer_type in ("tool_analysis", "requires_data_tool")
    if a.answer_type == "tool_analysis":
        assert a.analysis["status"] in ("ok", "insufficient_data", "unsupported_variable", "data_source_unavailable", "invalid_request", "upstream_error")


def test_documented_gap_is_not_filled_with_an_invented_number(real_service, need_key):
    item = EVAL["documented_gap"][0]
    a = real_service.answer(item["q"])
    assert a.answer_type in ("document_answer", "insufficient_knowledge")
    ok, missing = numbers_supported(a.answer, [], item["q"])
    assert ok, f"invented numbers: {missing}"


@pytest.mark.parametrize("item", EVAL["insufficient"], ids=lambda i: i["id"])
def test_end_to_end_admits_missing_knowledge(real_service, item):
    a = real_service.answer(item["q"])
    assert a.answer_type == "insufficient_knowledge" and not a.sources


def test_english_on_request_and_arabic_default(real_service, need_key):
    ar = real_service.answer("ما الدقة المكانية لمنتج SMAP SPL3SMP؟")
    en = real_service.answer("What is the spatial resolution of SMAP SPL3SMP? Answer in English.")
    arabic = lambda t: sum("؀" <= ch <= "ۿ" for ch in t) / max(len(t), 1)
    assert arabic(ar.answer) > 0.3 and arabic(en.answer) < 0.1
    assert "SPL3SMP" in ar.answer or "36" in ar.answer     # identifiers/numbers preserved


def test_gemini_platform_scope_uses_separate_collection(real_service, need_key):
    a = real_service.answer("What is the stable model code for Gemini 3.8 Flash?", scope="gemini_platform", language="en")
    assert a.answer_type == "document_answer"
    assert all(s.source_file.startswith("google_") for s in a.sources)
    assert "gemini-3.8-flash" in a.answer


def test_no_secret_in_any_response(real_service, need_key):
    from app.config import load_gemini_key
    a = real_service.answer("هل يحتاج FIRMS إلى مفتاح؟")
    blob = repr(a)
    assert load_gemini_key().get_secret_value() not in blob and "AIza" not in blob
