"""Hybrid retrieval: dense (Qdrant) + BM25, fused with Reciprocal Rank Fusion, with metadata filters."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.embeddings.base import Embedder
from app.retrieval.keyword import KeywordIndex
from app.vector_store.qdrant_store import QdrantStore, SearchHit


@dataclass
class Retrieved:
    hit: SearchHit
    dense_score: float | None
    bm25_score: float | None
    fused: float


@dataclass
class RetrievalResult:
    items: list[Retrieved]
    best_dense: float                     # best cosine similarity among dense candidates (relevance gate)
    filters_applied: dict = field(default_factory=dict)
    filter_fallback: bool = False
    candidates: int = 0


class HybridRetriever:
    def __init__(self, store: QdrantStore, embedder: Embedder, collection: str,
                 candidate_k: int = 20, rrf_k: int = 60):
        self.store, self.embedder, self.collection = store, embedder, collection
        self.candidate_k, self.rrf_k = candidate_k, rrf_k
        self._kw: KeywordIndex | None = None

    def invalidate(self) -> None:
        self._kw = None

    def _keyword_index(self) -> KeywordIndex:
        if self._kw is None:
            self._kw = KeywordIndex(list(self.store.iter_all(self.collection)))
        return self._kw

    def _run(self, query: str, qvec, top_k: int, filters, use_keyword: bool) -> RetrievalResult:
        dense = self.store.search(self.collection, qvec, self.candidate_k, filters)
        kw = self._keyword_index().search(query, self.candidate_k, filters) if use_keyword else []
        fused: dict[str, Retrieved] = {}
        for rank, h in enumerate(dense):
            r = fused.setdefault(h.id, Retrieved(h, None, None, 0.0))
            r.dense_score = h.score
            r.fused += 1.0 / (self.rrf_k + rank + 1)
        for rank, (h, s) in enumerate(kw):
            r = fused.setdefault(h.id, Retrieved(h, None, None, 0.0))
            r.bm25_score = s
            r.fused += 1.0 / (self.rrf_k + rank + 1)
        items = sorted(fused.values(), key=lambda r: -r.fused)[:top_k]
        best = max((h.score for h in dense), default=0.0)
        return RetrievalResult(items, best, filters or {}, False, len(fused))

    def retrieve(self, query: str, top_k: int = 5, filters: dict[str, Any] | None = None,
                 soft_filters: dict[str, Any] | None = None, use_keyword: bool = True) -> RetrievalResult:
        qvec = self.embedder.embed_query(query)
        merged = {**(soft_filters or {}), **(filters or {})}
        res = self._run(query, qvec, top_k, merged or None, use_keyword)
        # inferred (soft) filters must never hide the answer: fall back if too few results
        if soft_filters and not filters and len(res.items) < 2:
            res = self._run(query, qvec, top_k, None, use_keyword)
            res.filter_fallback = True
        return res
