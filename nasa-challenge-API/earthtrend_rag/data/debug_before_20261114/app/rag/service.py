"""Process-wide wiring: embedder, Qdrant store, retrievers, Gemini client, pipeline."""
from __future__ import annotations

import logging
import threading

from app.config import GEMINI_DOCS_COLLECTION, KNOWLEDGE_COLLECTION, get_settings, load_gemini_key
from app.embeddings.base import Embedder, get_embedder
from app.ingestion.service import ingest_project_resources
from app.llm.gemini_client import GeminiClient, LLMError, UsageTracker
from app.agent.trend_agent import TrendAgent
from app.rag.pipeline import RagPipeline
from app.retrieval.retriever import HybridRetriever
from app.vector_store.qdrant_store import QdrantStore

log = logging.getLogger(__name__)

# Dense-similarity gate per embedding model, calibrated on the evaluation set (see docs/EVALUATION.md).
CALIBRATED_THRESHOLDS = {
    "BAAI/bge-m3": 0.45,
    "intfloat/multilingual-e5-small": 0.79,
}


class RagService:
    def __init__(self, embedder: Embedder | None = None, store: QdrantStore | None = None,
                 llm=None, min_dense_score: float | None = None):
        s = get_settings()
        self.settings = s
        self.embedder = embedder or get_embedder()
        self.store = store or QdrantStore(s.qdrant_path, self.embedder.name, self.embedder.dim)
        self.retrievers = {
            c: HybridRetriever(self.store, self.embedder, c, s.candidate_k, s.hybrid_rrf_k)
            for c in (KNOWLEDGE_COLLECTION, GEMINI_DOCS_COLLECTION)
        }
        self._llm = llm
        self._llm_error: str | None = None
        self.min_dense_score = min_dense_score if min_dense_score is not None else \
            CALIBRATED_THRESHOLDS.get(self.embedder.name, s.min_dense_score)
        self._lock = threading.Lock()
        self.pipeline = RagPipeline(self.retrievers, None, self.min_dense_score, s.top_k, trend_handler=self._trend)
        self.usage = UsageTracker(s.usage_file, s.gemini_daily_cap_per_model)

    @property
    def llm(self):
        if self._llm is None:
            try:
                self._llm = GeminiClient(usage=self.usage)
            except LLMError as e:
                self._llm_error = str(e)
                raise
        self.pipeline.llm = self._llm
        return self._llm

    def _trend(self, question: str, language: str):
        if self._llm is None and load_gemini_key():
            _ = self.llm
        if self._llm is None:
            raise LLMError("GEMINI_API_KEY is not configured.", status=503)
        return TrendAgent(self._llm).ask(question, language)

    def trend_ask(self, question: str, language: str = "ar"):
        return self._trend(question, language)

    def answer(self, question: str, **kw):
        if self._llm is None and load_gemini_key():
            _ = self.llm   # builds the Gemini client lazily; without a key the pipeline raises a 503 LLMError
        self.pipeline.llm = self._llm
        return self.pipeline.answer(question, **kw)

    def ingest(self, **kw) -> dict:
        with self._lock:
            rep = ingest_project_resources(self.store, self.embedder, self.settings.manifest_file, **kw)
            for r in self.retrievers.values():
                r.invalidate()
            return rep

    def health(self) -> dict:
        counts = self.store.collections()
        key = load_gemini_key()
        return {
            "embedding_model": self.embedder.name, "embedding_dim": self.embedder.dim,
            "collections": counts,
            "index_ready": counts.get(KNOWLEDGE_COLLECTION, 0) > 0,
            "gemini_model": self.settings.gemini_model,
            "gemini_key_configured": bool(key),
            "relevance_threshold": self.min_dense_score,
            "usage_today": self.usage.today(),
        }
