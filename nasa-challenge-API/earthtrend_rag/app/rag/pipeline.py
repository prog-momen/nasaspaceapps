"""Question -> intent -> retrieval -> grounded Claude answer with source attribution.

answer_type values (the frontend must treat them differently):
  document_answer     grounded in retrieved documentation (sources attached)
  insufficient_knowledge  nothing relevant enough in the knowledge base; no LLM call, nothing invented
  tool_analysis       trend question answered by the analyze_trend tool (numbers come from the tool result only)
  requires_data_tool  needs real observations / statistics / forecast; routed to tools, never answered from text
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.config import GEMINI_DOCS_COLLECTION, KNOWLEDGE_COLLECTION
from app.llm.base import LLMError
from app.rag.prompts import LANGUAGE_NAMES, MESSAGES, SYSTEM_PROMPT, build_user_prompt
from app.retrieval.intent import Intent, classify
from app.retrieval.retriever import HybridRetriever, Retrieved

log = logging.getLogger(__name__)


_ID_RE = re.compile(r"\b(?=[A-Za-z0-9_]*\d)[A-Z][A-Za-z0-9_]{4,}\b|\b[A-Z][A-Z_]{5,}\b")


def unknown_identifiers(question: str, passages: list[str]) -> list[str]:
    """Product/parameter codes in the question (e.g. VNP46A1) that appear in none of the retrieved passages.

    A dense model happily returns "nearby" documentation for an unknown product code; if the exact code is absent
    from every retrieved passage, the knowledge base does not cover it.
    """
    blob = "\n".join(passages).lower()
    return [t for t in dict.fromkeys(_ID_RE.findall(question)) if t.lower() not in blob]


class LLM(Protocol):
    model: str

    def generate(self, system: str, user: str, **kw): ...


@dataclass
class SourceRef:
    index: int
    source_file: str
    document_title: str
    section: str
    page: int | None
    dataset_ids: list[str]
    dataset_name: str | None
    service_id: str | None
    original_url: str | None
    provider: str | None
    score: float | None
    cited: bool
    snippet: str
    text: str = ""


@dataclass
class RagAnswer:
    answer: str
    answer_type: str
    language: str
    intent: Intent
    sources: list[SourceRef] = field(default_factory=list)
    retrieval: dict[str, Any] = field(default_factory=dict)
    llm: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    analysis: dict | None = None
    answer_source: str | None = None
    fallback_reason: str | None = None


def _source_ref(i: int, r: Retrieved, cited: bool) -> SourceRef:
    md = r.hit.metadata
    return SourceRef(
        index=i, source_file=md.get("source_file", ""), document_title=md.get("document_title", ""),
        section=md.get("section", ""), page=md.get("page"), dataset_ids=md.get("dataset_ids", []),
        dataset_name=md.get("dataset_name"), service_id=md.get("service_id"),
        original_url=md.get("original_url") or (md.get("urls") or [None])[0],
        provider=md.get("provider"), score=r.dense_score, cited=cited,
        snippet=re.sub(r"\s+", " ", r.hit.text)[:240], text=r.hit.text[:1800])


class RagPipeline:
    def __init__(self, retrievers: dict[str, HybridRetriever], llm: LLM | None, min_dense_score: float,
                 top_k: int = 5, trend_handler=None):
        self.retrievers, self.llm = retrievers, llm
        self.trend_handler = trend_handler      # callable(question, language) -> TrendAnswer, or None
        self.min_dense_score, self.top_k = min_dense_score, top_k

    # -- helpers ---------------------------------------------------------------
    def _select(self, items: list[Retrieved], question: str | None = None) -> list[Retrieved]:
        """Do not pad the context: keep only passages that are individually relevant (dense threshold + lexical support, see app.rag.evidence)."""
        from app.rag.evidence import supports
        keep = []
        codes = []
        if question is not None:
            from app.rag.evidence import expand_query
            codes = [c for c in expand_query(question)[len(question):].split() if c]     # official parameter codes the question implies (e.g. PRECTOTCORR)
        for pos, r in enumerate(items):
            if codes and r.bm25_score is not None and pos < 3 and any(c in r.hit.text for c in codes):
                keep.append(r)                       # keyword hit on the exact official parameter code of the variable asked about
                continue
            dense_ok = r.dense_score is not None and r.dense_score >= self.min_dense_score
            kw_ok = r.bm25_score is not None and pos < 3 and (r.dense_score or 0) >= self.min_dense_score * 0.9
            if not (dense_ok or kw_ok):
                continue
            if question is not None:
                md = r.hit.metadata
                meta = " ".join(str(md.get(k) or "") for k in ("document_title", "section", "dataset_name", "service_id"))
                if not supports(question, r.hit.text, meta, r.dense_score if r.dense_score is not None else self.min_dense_score, self.min_dense_score):
                    continue
            keep.append(r)
        return keep

    @staticmethod
    def _cited_indices(text: str, n: int) -> set[int]:
        return {int(x) for x in re.findall(r"\[(\d{1,2})\]", text) if 1 <= int(x) <= n}

    # -- main ------------------------------------------------------------------
    def answer(self, question: str, *, language: str | None = None, top_k: int | None = None,
               filters: dict | None = None, scope: str = KNOWLEDGE_COLLECTION) -> RagAnswer:
        intent = classify(question)
        lang = language or intent.language
        intent.language = lang
        k = top_k or self.top_k
        retriever = self.retrievers[scope]
        from app.rag.evidence import expand_query
        res = retriever.retrieve(expand_query(question), top_k=k, filters=filters, soft_filters=intent.filters)
        info = {"collection": scope, "best_dense_score": round(res.best_dense, 4), "threshold": self.min_dense_score,
                "candidates": res.candidates, "filters": res.filters_applied, "filter_fallback": res.filter_fallback,
                "returned": len(res.items)}

        # RAG must not answer measurement / statistics / forecast requests from text
        if intent.kind != "knowledge":
            related = self._select(res.items, question)[:3]
            if intent.kind == "needs_analysis" and self.trend_handler is not None:
                try:
                    ta = self.trend_handler(question, lang)
                    return RagAnswer(ta.answer, "tool_analysis" if ta.analysis is not None else "requires_data_tool", lang, intent,
                                     [_source_ref(i, r, False) for i, r in enumerate(related, 1)], info, ta.llm,
                                     ta.warnings + [f"answer_source={ta.answer_source}", f"tool_status={ta.status}"] +
                                     [f"tool_call:{c['name']}" for c in ta.tool_calls], analysis=ta.analysis,
                                     answer_source=ta.answer_source, fallback_reason=ta.fallback_reason)
                except LLMError as e:
                    log.warning("trend handler unavailable: %s", e)
            msg = MESSAGES[intent.kind][lang].format(tools=", ".join(intent.required_tools))
            if related:
                msg += MESSAGES["docs_hint"][lang]
            return RagAnswer(msg, "requires_data_tool", lang, intent,
                             [_source_ref(i, r, False) for i, r in enumerate(related, 1)], info,
                             warnings=["No numeric value was generated; tools must supply it."])

        passages = self._select(res.items, question)
        if res.best_dense < self.min_dense_score or not passages:
            return RagAnswer(MESSAGES["insufficient"][lang], "insufficient_knowledge", lang, intent, [], info)
        missing = unknown_identifiers(question, [r.hit.text for r in res.items])
        if missing:
            info["unknown_identifiers"] = missing
            return RagAnswer(MESSAGES["insufficient"][lang], "insufficient_knowledge", lang, intent, [], info,
                             warnings=[f"identifier(s) not found in any retrieved passage: {', '.join(missing)}"])

        if self.llm is None:
            raise LLMError("GEMINI_API_KEY is not configured.", status=503)
        ctx = [{"source_file": r.hit.metadata.get("source_file", ""), "section": r.hit.metadata.get("section", ""),
                "original_url": r.hit.metadata.get("original_url"), "text": r.hit.text} for r in passages]
        llm_res = self.llm.generate(SYSTEM_PROMPT.format(language_name=LANGUAGE_NAMES[lang]),
                                    build_user_prompt(question, ctx))
        text = llm_res.text.strip()
        llm_info = {"model": llm_res.model, "prompt_tokens": llm_res.prompt_tokens,
                    "output_tokens": llm_res.output_tokens, "latency_s": round(llm_res.latency_s, 2)}
        if text.startswith("INSUFFICIENT_CONTEXT"):
            return RagAnswer(MESSAGES["insufficient"][lang], "insufficient_knowledge", lang, intent, [], info, llm_info)

        cited = self._cited_indices(text, len(passages))
        warnings = []
        bad = {int(x) for x in re.findall(r"\[(\d{1,2})\]", text)} - set(range(1, len(passages) + 1))
        if bad:  # never keep a fabricated citation
            text = re.sub(r"\[(%s)\]" % "|".join(map(str, sorted(bad))), "", text)
            warnings.append("Removed citations that do not match any retrieved passage.")
        if not cited:
            warnings.append("Answer contains no citations; all retrieved passages are listed as context only.")
        sources = [_source_ref(i, r, i in cited) for i, r in enumerate(passages, 1)]
        return RagAnswer(text, "document_answer", lang, intent, sources, info, llm_info, warnings, answer_source="claude")


__all__ = ["RagPipeline", "RagAnswer", "SourceRef", "GEMINI_DOCS_COLLECTION", "KNOWLEDGE_COLLECTION"]
