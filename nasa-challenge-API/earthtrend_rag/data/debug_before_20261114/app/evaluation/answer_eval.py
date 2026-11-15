"""End-to-end answer evaluation (REAL embeddings + REAL Gemini). Costs ~16 Gemini requests per run.

Run:  python -m app.evaluation.answer_eval --out data/answer_eval.json
Metrics
- retrieval_hit      a retrieved chunk contains the gold evidence string
- source_correct     a CITED source contains the gold evidence string
- fact_present       the answer states the expected fact (must_say)
- numbers_supported  every number in the answer appears in the cited passages (cheap faithfulness proxy)
- routing / refusal  data requests -> requires_data_tool; unanswerable -> insufficient_knowledge (no LLM call)
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from app.evaluation.retrieval_eval import load_eval

_NUM = re.compile(r"\d[\d,.]*")


def numbers_supported(answer: str, passages: list[str], question: str = "") -> tuple[bool, list[str]]:
    ctx = " ".join(passages) + " " + question
    ctx_nums = {n.strip(".,") for n in _NUM.findall(ctx)}
    missing = []
    for n in _NUM.findall(re.sub(r"\[\d{1,2}\]", "", answer)):
        n = n.strip(".,")
        if n and n not in ctx_nums:
            missing.append(n)
    return not missing, missing


def evaluate_answerable(svc, item: dict) -> dict:
    a = svc.answer(item["q"], language=item.get("lang"))
    texts = [s.snippet for s in a.sources]
    full = {s.index: s for s in a.sources}
    # snippets are truncated; use the retriever's full text for evidence checks
    res = svc.retrievers["earth_knowledge"].retrieve(item["q"], top_k=5, soft_filters=a.intent.filters)
    passages = [r.hit.text for r in res.items]
    evidence = item["evidence"]
    retrieval_hit = any(e in p for p in passages for e in evidence)
    cited_files = [s for s in a.sources if s.cited]
    cited_text = [r.hit.text for r in res.items if any(r.hit.metadata.get("source_file") == s.source_file and
                                                       r.hit.metadata.get("section") == s.section for s in cited_files)]
    source_correct = any(e in p for p in cited_text for e in evidence)
    fact = all(m in a.answer for m in item["must_say"])
    nums_ok, missing = numbers_supported(a.answer, cited_text or passages, item["q"])
    return {"id": item["id"], "answer_type": a.answer_type, "retrieval_hit": retrieval_hit, "source_correct": source_correct,
            "fact_present": fact, "numbers_supported": nums_ok, "unsupported_numbers": missing,
            "cited": len(cited_files), "answer": a.answer[:400]}


def run(svc, pause_s: float = 2.0) -> dict:
    ev = load_eval()
    out = {"answerable": [], "needs_tool": [], "conceptual": [], "insufficient": []}
    for it in ev["answerable"]:
        out["answerable"].append(evaluate_answerable(svc, it))
        time.sleep(pause_s)
    for it in ev["needs_tool"]:
        a = svc.answer(it["q"])
        out["needs_tool"].append({"id": it["id"], "ok": a.answer_type == "requires_data_tool" and a.intent.kind == it["expect_kind"]})
    for it in ev["insufficient"]:
        a = svc.answer(it["q"])
        out["insufficient"].append({"id": it["id"], "ok": a.answer_type == "insufficient_knowledge",
                                    "best_dense": a.retrieval.get("best_dense_score")})
    n = len(out["answerable"])
    summary = {
        "answerable_n": n,
        "answer_type_document": sum(r["answer_type"] == "document_answer" for r in out["answerable"]) / n,
        "retrieval_hit": sum(r["retrieval_hit"] for r in out["answerable"]) / n,
        "source_correct": sum(r["source_correct"] for r in out["answerable"]) / n,
        "fact_present": sum(r["fact_present"] for r in out["answerable"]) / n,
        "numbers_supported": sum(r["numbers_supported"] for r in out["answerable"]) / n,
        "routing_correct": sum(r["ok"] for r in out["needs_tool"]) / len(out["needs_tool"]),
        "refusal_correct": sum(r["ok"] for r in out["insufficient"]) / len(out["insufficient"]),
    }
    return {"summary": summary, "details": out}


if __name__ == "__main__":
    from app.config import setup_logging
    from app.rag.service import RagService
    setup_logging()
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    svc = RagService()
    if not svc.health()["index_ready"]:
        svc.ingest()
    rep = run(svc)
    txt = json.dumps(rep, indent=2, ensure_ascii=False)
    print(txt)
    if a.out:
        Path(a.out).write_text(txt, encoding="utf-8")
