"""Retrieval evaluation + embedding model comparison.

Run:  python -m app.evaluation.retrieval_eval --models BAAI/bge-m3 intfloat/multilingual-e5-small
Each model gets its own throw-away Qdrant directory, so the production index is never touched.
"""
from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
from pathlib import Path

from app.chunking.chunker import chunk_document
from app.config import KNOWLEDGE_COLLECTION
from app.embeddings.base import SentenceTransformerEmbedder
from app.ingestion.loaders import load_all
from app.retrieval.retriever import HybridRetriever
from app.vector_store.qdrant_store import QdrantStore

EVAL_PATH = Path(__file__).with_name("eval_set.json")


def load_eval() -> dict:
    return json.loads(EVAL_PATH.read_text(encoding="utf-8"))


def first_hit_rank(items, evidence: list[str]) -> int | None:
    for i, r in enumerate(items, 1):
        if any(e in r.hit.text for e in evidence):
            return i
    return None


def validate_evidence(chunks_text: list[str], eval_set: dict) -> list[str]:
    """Every evidence string must exist in the corpus, otherwise the eval item is invalid."""
    missing = []
    for item in eval_set["answerable"]:
        if not any(e in t for t in chunks_text for e in item["evidence"]):
            missing.append(item["id"])
    return missing


def evaluate(retriever: HybridRetriever, eval_set: dict, k: int = 5) -> dict:
    out = {"dense": {}, "hybrid": {}}
    for mode, use_kw in (("dense", False), ("hybrid", True)):
        ranks, prec = [], []
        for item in eval_set["answerable"]:
            res = retriever.retrieve(item["q"], top_k=k, use_keyword=use_kw)
            ranks.append(first_hit_rank(res.items, item["evidence"]))
            rel = sum(1 for r in res.items if any(e in r.hit.text for e in item["evidence"]))
            prec.append(rel / max(len(res.items), 1))
        n = len(ranks)
        out[mode] = {
            "hit@1": sum(1 for r in ranks if r == 1) / n,
            "hit@3": sum(1 for r in ranks if r and r <= 3) / n,
            "hit@5": sum(1 for r in ranks if r and r <= 5) / n,
            "mrr": statistics.mean(1 / r if r else 0 for r in ranks),
            "precision@5": statistics.mean(prec),
            "misses": [it["id"] for it, r in zip(eval_set["answerable"], ranks) if not r],
        }
    ans = [retriever.retrieve(i["q"], top_k=1).best_dense for i in eval_set["answerable"]]
    uns = [retriever.retrieve(i["q"], top_k=1).best_dense for i in eval_set["insufficient"]]
    out["dense_score_answerable"] = {"min": min(ans), "median": statistics.median(ans)}
    out["dense_score_insufficient"] = {"max": max(uns), "median": statistics.median(uns)}
    gap = min(ans) - max(uns)
    out["threshold_midpoint"] = (min(ans) + max(uns)) / 2
    out["separable"] = gap > 0
    return out


def run(models: list[str], k: int = 5) -> dict:
    eval_set = load_eval()
    docs = load_all()[KNOWLEDGE_COLLECTION]
    chunks = [(d, c) for d in docs for c in chunk_document(d)]
    bad = validate_evidence([c.text for _, c in chunks], eval_set)
    report = {"invalid_eval_items": bad, "chunks": len(chunks), "models": {}}
    for m in models:
        t0 = time.time()
        emb = SentenceTransformerEmbedder(m)
        t_load = time.time() - t0
        with tempfile.TemporaryDirectory() as tmp:
            store = QdrantStore(Path(tmp), emb.name, emb.dim)
            store.ensure_collection(KNOWLEDGE_COLLECTION)
            t0 = time.time()
            by_source: dict[str, list] = {}
            for d, c in chunks:
                by_source.setdefault(d.source_id, []).append(c)
            for sid, cs in by_source.items():
                store.upsert_source(KNOWLEDGE_COLLECTION, sid, cs, emb.embed_documents([c.embed_text for c in cs]))
            t_index = time.time() - t0
            r = HybridRetriever(store, emb, KNOWLEDGE_COLLECTION)
            t0 = time.time()
            res = evaluate(r, eval_set, k)
            res.update(dim=emb.dim, load_seconds=round(t_load, 1), index_seconds=round(t_index, 1),
                       eval_seconds=round(time.time() - t0, 1))
            store.close()
        report["models"][m] = res
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["BAAI/bge-m3", "intfloat/multilingual-e5-small"])
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rep = run(a.models)
    txt = json.dumps(rep, indent=2, ensure_ascii=False)
    print(txt)
    if a.out:
        Path(a.out).write_text(txt, encoding="utf-8")
