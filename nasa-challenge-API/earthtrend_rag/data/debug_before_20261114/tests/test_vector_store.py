import pytest

from app.chunking.chunker import chunk_document
from app.models import Chunk
from app.vector_store.qdrant_store import QdrantStore

COL = "earth_knowledge"


def _ingest(store, embedder, doc):
    chunks = chunk_document(doc)
    return chunks, store.upsert_source(COL, doc.source_id, chunks, embedder.embed_documents([c.embed_text for c in chunks]))


def test_insert_and_similarity_search(mem_store, embedder, sample_doc):
    chunks, rep = _ingest(mem_store, embedder, sample_doc)
    assert rep["added"] == len(chunks) == mem_store.count(COL)
    hits = mem_store.search(COL, embedder.embed_query("MAP_KEY wildfire hotspots"), 3)
    assert hits and hits[0].metadata["service_id"] == "S06"
    assert hits[0].score >= hits[-1].score
    assert hits[0].text and "text" not in hits[0].metadata      # payload text is exposed as .text only


def test_metadata_filtering(mem_store, embedder, sample_doc):
    _ingest(mem_store, embedder, sample_doc)
    q = embedder.embed_query("NASA data")
    only_s05 = mem_store.search(COL, q, 10, {"service_id": "S05"})
    assert only_s05 and all(h.metadata["service_id"] == "S05" for h in only_s05)
    by_var = mem_store.search(COL, q, 10, {"variables": ["wildfires"]})
    assert by_var and all("wildfires" in h.metadata["variables"] for h in by_var)
    assert mem_store.search(COL, q, 10, {"service_id": "S99"}) == []


def test_duplicate_prevention_is_idempotent(mem_store, embedder, sample_doc):
    chunks, _ = _ingest(mem_store, embedder, sample_doc)
    n = mem_store.count(COL)
    _, rep = _ingest(mem_store, embedder, sample_doc)
    assert rep["added"] == 0 and rep["removed"] == 0 and mem_store.count(COL) == n


def test_duplicates_inside_one_batch_are_dropped(mem_store, embedder):
    c = Chunk("same text here", "same text here", {"source_id": "s1", "source_file": "a"})
    rep = mem_store.upsert_source(COL, "s1", [c, c], embedder.embed_documents(["same text here"] * 2))
    assert rep["added"] == 1 and rep["duplicates_dropped"] == 1 and mem_store.count(COL) == 1


def test_update_replaces_changed_source(mem_store, embedder, sample_doc):
    _ingest(mem_store, embedder, sample_doc)
    sample_doc.text = sample_doc.text.replace("MAP_KEY required", "MAP_KEY and a free account are required")
    _, rep = _ingest(mem_store, embedder, sample_doc)
    assert rep["added"] >= 1 and rep["removed"] >= 1
    texts = [h.text for h in mem_store.iter_all(COL)]
    assert any("free account" in t for t in texts) and not any("MAP_KEY required" in t for t in texts)


def test_delete_source_and_collection(mem_store, embedder, sample_doc):
    _ingest(mem_store, embedder, sample_doc)
    assert mem_store.delete_source(COL, sample_doc.source_id) > 0 and mem_store.count(COL) == 0
    _ingest(mem_store, embedder, sample_doc)
    mem_store.delete_collection(COL)
    assert COL not in mem_store.collections()


def test_persistence_across_restart(tmp_path, embedder, sample_doc):
    s1 = QdrantStore(tmp_path / "q", embedder.name, embedder.dim)
    chunks, _ = _ingest(s1, embedder, sample_doc)
    s1.close()
    s2 = QdrantStore(tmp_path / "q", embedder.name, embedder.dim)
    assert s2.count(COL) == len(chunks)
    assert s2.search(COL, embedder.embed_query("burned area"), 1)
    s2.close()


def test_embedding_model_mismatch_is_rejected(tmp_path, embedder, sample_doc):
    s1 = QdrantStore(tmp_path / "q", embedder.name, embedder.dim)
    _ingest(s1, embedder, sample_doc)
    s1.close()
    s2 = QdrantStore(tmp_path / "q", "other-model", 384)
    with pytest.raises(RuntimeError, match="was built with"):
        s2.ensure_collection(COL)
    s2.close()
