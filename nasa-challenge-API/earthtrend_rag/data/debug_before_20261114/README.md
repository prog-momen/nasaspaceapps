# EarthTrend Explorer — RAG service

Knowledge-retrieval foundation of the AI Assistant. It answers **documentation / scientific-knowledge** questions
about NASA datasets and APIs from the project's own reference files, with source attribution, using
Gemini (`gemini-3.8-flash`) for grounded generation.

It deliberately does **not** answer from text: measurements, statistics (Mann–Kendall, Sen's slope) or forecasts.
Those questions are detected and returned as `requires_data_tool` with the tool names to call (see *Integration*).

## Layout

```
earthtrend_rag/
  app/
    config.py            settings, secret loading, log redaction (model IDs live here only)
    ingestion/           registry (allow-list of sources), loaders, secret scrubber, ingestion service
    chunking/            structure-aware chunker + metadata extraction
    embeddings/          embedder interface (sentence-transformers), offline test embedder
    vector_store/        Qdrant local (persistent) store
    retrieval/           intent routing, BM25, hybrid (dense + BM25, RRF) retriever
    llm/                 Gemini client (retries, usage cap, key never logged)
    rag/                 prompts, pipeline, service wiring
    api/                 FastAPI app + Pydantic schemas
    evaluation/          eval set + retrieval/answer evaluation scripts
  tests/                 offline unit/API tests; tests/integration = real model + real Gemini
  data/                  Qdrant index, manifest, usage counters (git-ignored)
```

## Setup (Windows, Python 3.14 verified)

```bash
cd earthtrend_rag
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
```

Secrets: put `GEMINI_API_KEY=...` in `earthtrend_rag/.env`, the repo-root `.env`, or `البروتوتايب/.env`
(see `.env.example`). The key is read from the environment first, then those files. It is never logged,
indexed or returned by the API. `.env`/`*.env` and `البروتوتايب/` are in `.gitignore`.

## Run

```bash
# 1) build the index (first run downloads the embedding model; later runs skip unchanged sources)
./.venv/Scripts/python.exe -c "from app.rag.service import RagService; print(RagService().ingest())"
# or, with the server running:  POST /api/rag/ingest

# 2) start the API
./.venv/Scripts/python.exe -m uvicorn app.api.main:app --port 8000
```

## API

```bash
curl -s localhost:8000/api/rag/health

curl -s localhost:8000/api/rag/query -H "Content-Type: application/json" \
  -d '{"question": "هل يحتاج FIRMS إلى مفتاح؟ وما اسمه؟", "top_k": 5}'

curl -s localhost:8000/api/rag/query -H "Content-Type: application/json" \
  -d '{"question": "What is the spatial resolution of SMAP SPL3SMP?", "language": "en"}'

curl -s -X POST localhost:8000/api/rag/ingest -H "Content-Type: application/json" -d '{"force": false}'
```

`POST /api/rag/query` request: `question`, `language` (`ar` default / `en`), `top_k` (1–10), `scope`
(`earth_knowledge` | `gemini_platform`), `filters` (keys: `variables`, `service_id`, `source_role`, `source_file`,
`dataset_ids`, `language`, `provider`), `debug`.

Response: `answer`, `answer_type`, `language`, `intent{kind, required_tools}`, `sources[]`
(`source_file`, `document_title`, `section`, `page`, `dataset_ids`, `dataset_name`, `service_id`, `original_url`,
`score`, `cited`, `snippet`), `retrieval`, `llm{model, tokens}`, `warnings`.

`answer_type` — the frontend must treat these differently:

| value | meaning |
|---|---|
| `document_answer` | grounded in retrieved documentation; `sources[].cited` marks the passages the answer cites |
| `insufficient_knowledge` | nothing relevant enough was found (or the model said so); no numbers or sources invented |
| `requires_data_tool` | needs observations / statistics / forecast; `intent.required_tools` lists the tools to run |

If `RAG_ADMIN_TOKEN` is set in the environment, `/api/rag/ingest` requires the header `X-Admin-Token`.
Ingestion only reads the allow-listed files in `app/ingestion/registry.py` (no arbitrary paths or URLs).

## Tests

```bash
./.venv/Scripts/python.exe -m pytest                    # offline: parsing, chunking, store, retrieval, routing, API (fake LLM)
./.venv/Scripts/python.exe -m pytest -m integration -v  # REAL embedding model + REAL Gemini calls (uses API quota)
./.venv/Scripts/python.exe -m app.evaluation.retrieval_eval --out data/embedding_comparison.json   # model comparison
./.venv/Scripts/python.exe -m app.evaluation.answer_eval --out data/answer_eval.json               # real end-to-end eval
```

## Integration with the rest of EarthTrend Explorer

The RAG module only retrieves knowledge. The calling agent should:

1. Call `POST /api/rag/query`.
2. If `answer_type == "requires_data_tool"`, run the listed tools from the project's tool contract
   (reference file §6.1: `search_datasets`, `fetch_timeseries`, `validate_timeseries`, `analyze_trend`,
   `forecast_timeseries`), then ask Gemini to explain the **tool output**. Numbers always come from the tools.
3. Show `sources` next to any `document_answer`.

Tool names live in `app/retrieval/intent.py::TOOL_MAP`; change them in one place if the contract changes
(the two reference files currently use different tool names, see *Known issues*).

## Trend analysis (Mann–Kendall + Sen's slope)

See `docs/TREND_ANALYSIS.md`. Quick use:

```bash
curl -s localhost:8000/api/analysis/trend -H "Content-Type: application/json" \
  -d '{"variable":"air_temperature","region":"Amazon","start_year":2005,"end_year":2025}'          # deterministic, no LLM

curl -s localhost:8000/api/analysis/trend/ask -H "Content-Type: application/json" \
  -d '{"question":"هل ارتفعت درجة حرارة الهواء في الأمازون بين 2005 و2025؟"}'                       # Gemini function calling
```

`POST /api/rag/query` routes trend questions to the same tool automatically (`answer_type: "tool_analysis"`, full result in `analysis`).
Land surface temperature, wildfires and drought currently return an explicit status (no data source wired), never a verdict.
Default significance threshold: 0.05 (`Settings.trend_alpha` or `significance_level` per request).

## Known issues

* `gemini-3.8-flash` returned 503/504 "high demand" for most of the build session; Gemini-dependent integration tests skip when a probe call fails.
* The two reference files name the tools differently (`search_datasets/fetch_timeseries/analyze_trend` vs `get_nasa_power_series/analyze_trend`); `TOOL_MAP` follows the first.
* The prototype key file is named `GEMINI_API_KEY=…​.env` (the key text is part of the filename). It is read correctly, but rename it to `.env`.
