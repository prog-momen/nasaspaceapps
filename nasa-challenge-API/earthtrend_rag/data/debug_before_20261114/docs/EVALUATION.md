# Evaluation

All numbers below were produced by the scripts in `app/evaluation/` on the real project files. Dataset: 16 answerable questions
(gold evidence = exact substrings of the project files), 7 data/analysis/forecast requests, 3 conceptual questions that must stay in RAG,
4 unanswerable questions, 1 documented-gap question. It is small; treat the numbers as a smoke benchmark, not a statistical estimate.

## Embedding model comparison (retrieval only, 899 chunks, CPU)

| model | dim | dense hit@5 | hybrid hit@1 / hit@3 / hit@5 | hybrid MRR | index time |
|---|---|---|---|---|---|
| `BAAI/bge-m3` | 1024 | 0.625 | 0.31 / 0.75 / 0.875 | 0.52 | 1765 s |
| `intfloat/multilingual-e5-small` | 384 | 0.875 | 0.625 / 0.875 / **1.00** | **0.77** | **165 s** |

**Chosen: `intfloat/multilingual-e5-small`** (local, free, multilingual, 10x cheaper to index). bge-m3 is larger and not worse in general;
on this corpus (short exact-fact questions against long structured cards) it ranked worse and was 10x slower on CPU. Re-run
`python -m app.evaluation.retrieval_eval` before changing models; `EMBEDDING_MODEL` is checked against the index on every start.

## Relevance gate (calibrated on the production index)

Dense similarity alone does not separate answerable from unanswerable questions (answerable min 0.816, in-domain-but-absent 0.82).
Gate = dense ≥ 0.79 **and** every product/parameter code in the question (e.g. `VNP46A1`, `MCD64A1`) must occur in the retrieved passages.
Result on the eval set: 0/16 answerable questions rejected, 4/4 unanswerable rejected (no Gemini call is made for them).

## Not measured here

Answer faithfulness/quality with Gemini is only measured when `gemini-3.8-flash` is serving requests
(`python -m app.evaluation.answer_eval`, or `pytest -m integration`). See the final report for the status of the last run.
