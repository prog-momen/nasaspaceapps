"""Evaluate the retrieval relevance / evidence-sufficiency gate on answerable and unanswerable questions (REAL index, REAL embeddings, NO Gemini).

Run with the server STOPPED (local Qdrant allows one process):  .venv\\Scripts\\python.exe scripts\\eval_evidence_gate.py
An answerable question must keep >=1 supporting passage; an unanswerable one must keep none. Output: evidence/evidence_gate_eval.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.config import KNOWLEDGE_COLLECTION                      # noqa: E402
from app.rag.pipeline import unknown_identifiers                 # noqa: E402
from app.rag.service import RagService                           # noqa: E402

ANSWERABLE = [
    "Does FIRMS need a MAP_KEY?", "هل يحتاج FIRMS إلى مفتاح؟", "What is NASA POWER?", "ما هو NASA POWER؟", "What does T2M mean in NASA POWER?",
    "Which POWER parameter is bias-corrected precipitation?", "What is NASA GIBS used for?", "What is Earthdata Login used for?", "What temporal resolutions does NASA POWER provide?",
    "What are the MODIS land surface temperature products?", "What is the FIRMS area API day range limit?", "What is Copernicus Sentinel-2?", "ما هو GIBS؟", "كيف أحصل على بيانات MODIS؟",
]
UNANSWERABLE = [
    "What is the airspeed velocity of a swallow?", "Who won the 2022 World Cup?", "What is the price of Bitcoin today?", "How do I bake sourdough bread?", "What is the capital of Australia?",
    "ما عاصمة فرنسا؟", "What is the rate limit of the FIRMS XYZ-9000 sensor?", "Explain quantum chromodynamics.", "Recommend a good movie about space.", "كيف أطبخ الكبسة؟",
]


def main():
    svc = RagService()
    thr = svc.min_dense_score
    rows = []
    for label, qs in (("answerable", ANSWERABLE), ("unanswerable", UNANSWERABLE)):
        for q in qs:
            from app.rag.evidence import expand_query
            res = svc.retrievers[KNOWLEDGE_COLLECTION].retrieve(expand_query(q), top_k=5)
            old = svc.pipeline._select(res.items)
            new = svc.pipeline._select(res.items, q)
            unk = unknown_identifiers(q, [r.hit.text for r in res.items])
            accepted_old = bool(old) and res.best_dense >= thr
            accepted_new = bool(new) and res.best_dense >= thr and not unk
            from app.rag.evidence import directly_answers
            direct = [r for r in new if directly_answers(q, " ".join(str(r.hit.metadata.get(k) or "") for k in ("document_title", "section")) + " " + r.hit.text)]
            rows.append({"set": label, "direct_excerpts": len(direct), "q": q, "best_dense": round(res.best_dense, 3), "kept_before_gate": len(old), "kept_after_gate": len(new), "unknown_identifiers": unk,
                         "accepted_before": accepted_old, "accepted_after": accepted_new, "top": [r.hit.metadata.get("section") for r in new[:2]]})
    def stats(key):
        tp = sum(1 for r in rows if r["set"] == "answerable" and r[key]); fn = sum(1 for r in rows if r["set"] == "answerable" and not r[key])
        fp = sum(1 for r in rows if r["set"] == "unanswerable" and r[key]); tn = sum(1 for r in rows if r["set"] == "unanswerable" and not r[key])
        return {"answerable_accepted": tp, "answerable_rejected": fn, "unanswerable_accepted(false)": fp, "unanswerable_rejected": tn}
    out = {"threshold": thr, "embedder": svc.embedder.name, "before_gate": stats("accepted_before"), "after_gate": stats("accepted_after"), "rows": rows}
    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence" / "evidence_gate_eval.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("threshold", "embedder", "before_gate", "after_gate")}, ensure_ascii=False, indent=1))
    for r in rows:
        flag = "OK " if (r["accepted_after"] == (r["set"] == "answerable")) else "BAD"
        print(flag, r["set"][:6], "direct", r["direct_excerpts"], r["best_dense"], r["kept_before_gate"], "->", r["kept_after_gate"], r["q"][:70])


if __name__ == "__main__":
    main()
