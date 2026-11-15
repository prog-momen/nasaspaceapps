"""Offline tests: hashing embedder + fake LLM. They prove the control flow, NOT answer quality."""
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.chunking.chunker import chunk_document
from app.llm.base import LLMError
from app.rag.pipeline import RagPipeline
from app.rag.service import RagService
from app.retrieval.retriever import HybridRetriever

COL = "earth_knowledge"


@pytest.fixture
def pipeline(mem_store, embedder, sample_doc, fake_llm):
    chunks = chunk_document(sample_doc)
    mem_store.upsert_source(COL, sample_doc.source_id, chunks, embedder.embed_documents([c.embed_text for c in chunks]))
    r = {COL: HybridRetriever(mem_store, embedder, COL), "gemini_platform": HybridRetriever(mem_store, embedder, "gemini_platform")}
    return RagPipeline(r, fake_llm, min_dense_score=0.05)


def test_grounded_answer_has_valid_sources(pipeline, fake_llm):
    a = pipeline.answer("Does FIRMS need MAP_KEY for wildfire hotspots?")
    assert a.answer_type == "document_answer" and a.language == "ar"
    assert len(fake_llm.calls) == 1
    cited = [s for s in a.sources if s.cited]
    assert cited and cited[0].index == 1
    assert cited[0].source_file == "sample.md" and cited[0].section.endswith("S06 — FIRMS")
    # the LLM only ever saw the retrieved passages, numbered
    _, user = fake_llm.calls[0]
    assert "[1] file=sample.md" in user and "QUESTION:" in user


def test_arabic_default_and_english_on_request(pipeline, fake_llm):
    pipeline.answer("Does FIRMS need MAP_KEY?")
    assert "Arabic" in fake_llm.calls[-1][0]
    pipeline.answer("Does FIRMS need MAP_KEY?", language="en")
    assert "written in English" in fake_llm.calls[-1][0] or "in English" in fake_llm.calls[-1][0]
    a = pipeline.answer("Does FIRMS need MAP_KEY? answer in English")
    assert a.language == "en"


def test_fabricated_citation_is_removed(pipeline, fake_llm):
    fake_llm.reply = "FIRMS needs MAP_KEY [1][7]."
    a = pipeline.answer("Does FIRMS need MAP_KEY?")
    assert "[7]" not in a.answer and "[1]" in a.answer
    assert any("Removed citations" in w for w in a.warnings)


def test_uncited_answer_is_flagged(pipeline, fake_llm):
    fake_llm.reply = "FIRMS needs MAP_KEY."
    a = pipeline.answer("Does FIRMS need MAP_KEY?")
    assert a.sources and not any(s.cited for s in a.sources)
    assert any("no citations" in w for w in a.warnings)


def test_model_can_declare_insufficient_context(pipeline, fake_llm):
    fake_llm.reply = "INSUFFICIENT_CONTEXT"
    a = pipeline.answer("Does FIRMS need MAP_KEY?")
    assert a.answer_type == "insufficient_knowledge" and a.sources == []


def test_irrelevant_question_never_calls_llm(mem_store, embedder, sample_doc, fake_llm):
    chunks = chunk_document(sample_doc)
    mem_store.upsert_source(COL, sample_doc.source_id, chunks, embedder.embed_documents([c.embed_text for c in chunks]))
    r = {COL: HybridRetriever(mem_store, embedder, COL)}
    p = RagPipeline(r, fake_llm, min_dense_score=0.9)         # strict gate
    a = p.answer("completely unrelated cooking recipe")
    assert a.answer_type == "insufficient_knowledge" and not fake_llm.calls and a.sources == []


@pytest.mark.parametrize("q,kind", [("ما درجة الحرارة في القاهرة أمس؟", "needs_data"),
                                    ("Is rainfall in Texas decreasing since 2010?", "needs_analysis"),
                                    ("توقع هطول الأمطار في الرياض عام 2027", "needs_forecast")])
def test_data_requests_do_not_call_llm_or_invent_numbers(pipeline, fake_llm, q, kind):
    a = pipeline.answer(q)
    assert a.answer_type == "requires_data_tool" and a.intent.kind == kind
    assert not fake_llm.calls
    assert a.intent.required_tools and a.warnings
    assert not any(ch.isdigit() for ch in a.answer.replace("2027", ""))   # no generated figures


# ---- API ----------------------------------------------------------------------------------------

@pytest.fixture
def client(mem_store, embedder, sample_doc, fake_llm):
    svc = RagService(embedder=embedder, store=mem_store, llm=fake_llm, min_dense_score=0.05)
    svc.pipeline.llm = fake_llm
    app.state.rag = svc
    with TestClient(app) as c:
        app.state.rag = svc          # lifespan keeps an injected service
        yield c, svc
    app.state.rag = None


def test_health_degraded_until_ingested(client):
    c, svc = client
    h = c.get("/api/rag/health").json()
    assert h["status"] == "degraded" and "knowledge index is empty (run ingestion)" in h["problems"]
    from app.config import get_settings
    assert h["components"]["llm_model"] == get_settings().anthropic_model == "claude-haiku-5-5"
    assert "api_key" not in str(h).lower()


def test_query_before_ingest_is_409(client):
    c, _ = client
    assert c.post("/api/rag/query", json={"question": "ما هو FIRMS؟"}).status_code == 409


def test_query_response_shape_and_validation(client, sample_doc, embedder):
    c, svc = client
    chunks = chunk_document(sample_doc)
    svc.store.upsert_source(COL, sample_doc.source_id, chunks, embedder.embed_documents([c_.embed_text for c_ in chunks]))
    r = c.post("/api/rag/query", json={"question": "Does FIRMS need MAP_KEY?", "debug": True})
    assert r.status_code == 200
    body = r.json()
    assert body["answer_type"] == "document_answer" and body["sources"][0]["source_file"] == "sample.md"
    assert {"index", "section", "page", "dataset_ids", "original_url", "cited", "snippet"} <= set(body["sources"][0])
    assert "best_dense_score" in body["retrieval"]
    assert c.post("/api/rag/query", json={"question": "x"}).status_code == 422
    assert c.post("/api/rag/query", json={"question": "valid question", "filters": {"text": "x"}}).status_code == 422
    assert c.post("/api/rag/query", json={"question": "valid question", "top_k": 50}).status_code == 422


def test_llm_failure_maps_to_http_error_without_leaking(client, sample_doc, embedder):
    c, svc = client
    chunks = chunk_document(sample_doc)
    svc.store.upsert_source(COL, sample_doc.source_id, chunks, embedder.embed_documents([x.embed_text for x in chunks]))

    def boom(*a, **k):
        raise LLMError("Gemini API error (429).", status=429)
    svc._llm.generate = boom
    r = c.post("/api/rag/query", json={"question": "Does FIRMS need MAP_KEY?"})
    assert r.status_code == 429 and r.json()["error"] == "llm_error"


def test_ingest_requires_admin_token_when_configured(client, monkeypatch):
    c, _ = client
    monkeypatch.setenv("RAG_ADMIN_TOKEN", "s3cret-test")
    assert c.post("/api/rag/ingest", json={}).status_code == 401
    # (a valid token would start a real ingestion; covered by the integration test)
