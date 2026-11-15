import pytest

from app.chunking.chunker import chunk_document
from app.evaluation.retrieval_eval import load_eval
from app.retrieval.intent import classify, wants_english
from app.retrieval.keyword import tokenize
from app.retrieval.retriever import HybridRetriever

COL = "earth_knowledge"
EVAL = load_eval()


def test_tokenizer_keeps_identifiers_and_normalises_arabic():
    t = tokenize("MOD11C3 PRECTOTCORR S05 والمنتجات المنتجات")
    assert "mod11c3" in t and "prectotcorr" in t and "s05" in t
    assert tokenize("المنتج")[0] == tokenize("منتج")[0]


@pytest.fixture
def retriever(mem_store, embedder, sample_doc):
    chunks = chunk_document(sample_doc)
    mem_store.upsert_source(COL, sample_doc.source_id, chunks, embedder.embed_documents([c.embed_text for c in chunks]))
    return HybridRetriever(mem_store, embedder, COL)


def test_keyword_finds_exact_identifier(retriever):
    res = retriever.retrieve("PRECTOTCORR units", top_k=2)
    assert res.items[0].hit.metadata["service_id"] == "S05"
    assert res.items[0].bm25_score is not None


def test_hybrid_fuses_both_signals(retriever):
    res = retriever.retrieve("MAP_KEY wildfire", top_k=3)
    top = res.items[0]
    assert top.dense_score is not None and top.bm25_score is not None
    assert top.hit.metadata["service_id"] == "S06"


def test_soft_filter_falls_back_when_it_would_hide_results(retriever):
    res = retriever.retrieve("MAP_KEY wildfire", top_k=3, soft_filters={"variables": ["precipitation"], "service_id": "S99"})
    assert res.filter_fallback and res.items


def test_explicit_filter_is_respected(retriever):
    res = retriever.retrieve("NASA data", top_k=5, filters={"service_id": "S05"})
    assert res.items and all(r.hit.metadata["service_id"] == "S05" for r in res.items)


@pytest.mark.parametrize("item", EVAL["needs_tool"], ids=lambda i: i["id"])
def test_intent_routes_data_requests_to_tools(item):
    it = classify(item["q"])
    assert it.kind == item["expect_kind"], item["q"]
    assert it.required_tools and "fetch_timeseries" in it.required_tools


@pytest.mark.parametrize("item", EVAL["answerable"] + EVAL["conceptual_not_tool"] + EVAL["insufficient"], ids=lambda i: i["id"])
def test_documentation_questions_stay_in_rag(item):
    assert classify(item["q"]).kind == "knowledge", item["q"]


def test_language_defaults():
    assert classify("ما هو FIRMS؟").language == "ar"
    assert classify("What is FIRMS? answer in English").language == "en"
    assert wants_english("اشرح لي بالإنجليزية") and not wants_english("اشرح لي")


def test_inferred_filters():
    assert classify("ما هي منتجات الحرائق في FIRMS؟").filters == {"variables": ["wildfires"]}
    assert classify("explain S05").filters == {"service_id": "S05"}
    assert classify("precipitation and drought").filters == {}   # ambiguous -> no filter
