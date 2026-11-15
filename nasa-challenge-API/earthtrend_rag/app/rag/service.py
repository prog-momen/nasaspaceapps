"""Process-wide wiring: embedder, Qdrant store, retrievers, Claude (Anthropic) client, pipeline."""
from __future__ import annotations

import logging
import threading

from app.config import GEMINI_DOCS_COLLECTION, KNOWLEDGE_COLLECTION, get_settings, load_llm_key
from app.embeddings.base import Embedder, get_embedder
from app.ingestion.service import ingest_project_resources
from app.llm.base import LLMError, UsageTracker
from app.llm.claude_client import ClaudeClient
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
        self.usage = UsageTracker(s.usage_file, s.llm_daily_cap)

    @property
    def llm(self):
        if self._llm is None:
            try:
                self._llm = ClaudeClient(usage=self.usage)
            except LLMError as e:
                self._llm_error = str(e)
                raise
        self.pipeline.llm = self._llm
        return self._llm

    def _trend(self, question: str, language: str):
        if self._llm is None and load_llm_key():
            _ = self.llm
        return TrendAgent(self._llm).ask(question, language)

    def trend_ask(self, question: str, language: str = "ar"):
        return self._trend(question, language)

    def answer(self, question: str, **kw):
        if self._llm is None and load_llm_key():
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
        key = load_llm_key()
        blocks = {self.settings.anthropic_model: self.usage.block_reason(self.settings.anthropic_model)}
        generation = "not_configured" if not key else "blocked" if all(blocks.values()) else "configured_unprobed"
        return {
            "embedding_model": self.embedder.name, "embedding_dim": self.embedder.dim,
            "collections": counts,
            "index_ready": counts.get(KNOWLEDGE_COLLECTION, 0) > 0,
            "llm_provider": "anthropic", "llm_model": self.settings.anthropic_model, "llm_allowed_models": ["claude-haiku-5-5"],
            "llm_key_configured": bool(key),
            "llm_generation_status": generation,
            "llm_model_blocks": blocks,
            "live_probe_performed": False,
            "relevance_threshold": self.min_dense_score,
            "usage_today": self.usage.today(),
        }
