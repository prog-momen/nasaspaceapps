# Architecture

## Data flow

```
                         INGESTION (offline, idempotent)
 core .md files ─┐
 crawled NASA docs ├─> loaders ─> scrub secrets ─> structure-aware chunker ─> metadata extractor
 challenge resources┘   (registry allow-list)                                       │
                                                         embedder (local, multilingual)
                                                                                  ▼
                                                Qdrant local (persistent): earth_knowledge | gemini_platform

                         QUERY
 question ─> intent router ──┬─ needs_data / needs_analysis / needs_forecast ─> `requires_data_tool`
                             │       (no LLM call, no numbers; names the tools to run)
                             └─ knowledge ─> embed ─> dense search ┐
                                            BM25 keyword search   ├─> RRF fusion ─> relevance gate
                                            (+ soft metadata filters, fallback)    │
                                                       below gate ─> `insufficient_knowledge` (no LLM call)
                                                       above gate ─> numbered context ─> Gemini ─> citations validated
                                                                                           └─> `document_answer` + sources
```

## Separation of responsibilities

| Concern | Owner | In this repo |
|---|---|---|
| Scientific knowledge, API/dataset documentation | **RAG** | yes |
| Real observations (POWER, AppEEARS, FIRMS...) | NASA data clients | no — interface only (`required_tools`) |
| Trend statistics (Mann–Kendall, Sen's slope), validation | Statistical engine | no |
| Forecasting | Forecasting engine | no |
| Understanding questions + explaining retrieved text / tool outputs | Gemini | `app/llm`, `app/rag` |

Numerical data (e.g. `research/power_nablus_monthly_2005_2025.csv`, probe JSON responses) is **not** indexed.

## Decisions

**Scope (registry allow-list).** Indexed: the two core Arabic reference files; 24 Earth-science / statistics docs from the
crawl (`doc_*`); quality-gated resource pages linked from the four Earth-science challenges. Excluded: PDF/HTML renderings of the
core files (duplicates), JS bundles, images, `python_deps`, space-science docs (Horizons, PDS, Trek, SVS, OSDR), raw PDFs
(stored as unparsed bytes and truncated at 750 KB by the crawl) and challenge pages themselves (site chrome; the core reference
already summarises them). Gemini platform docs go to a **separate collection** (`gemini_platform`), reachable only with
`scope="gemini_platform"`, so Earth-science answers can never cite pricing pages.

**Chunking.** Heading-aware: one API card (`S01`–`S24`) or product-table row group is the unit. Target 1600 characters
(≈350–500 tokens for mixed Arabic/English), hard splits only for oversize blocks; code fences atomic; tables split by rows
with the header repeated; 200-character overlap (≈12 %) *within* a section only, never across headings; TOC removed. Rationale:
cards are 1–3 KB, so most stay whole; 1600 chars fits the 512-token input of the small multilingual model and leaves room
for 3–5 passages in the Gemini prompt; overlap preserves context when a long card has to be split without duplicating the
whole corpus. Every chunk is embedded with `document title + section path` prepended (contextual header) but the stored and
cited text is the original.

**Metadata** (per chunk, heuristic and only when found): source file/type/role, document title, section path, page (none for
md/text), `service_id` (S01–S24), `dataset_ids`, `variables` (the four project variables + air temperature), `units`, `urls`,
`api_endpoints`, language, geographic hint, temporal-start hint, provider, original URL + retrieval date for crawled pages.

**Retrieval.** Dense (Qdrant cosine) + BM25 (identifier-preserving tokenizer, Arabic normalisation) fused by Reciprocal Rank
Fusion — needed because queries contain exact identifiers (`MAP_KEY`, `PRECTOTCORR`, `S05`) that dense models blur. Variable /
service filters inferred from the question are *soft*: if they leave fewer than two results the search is repeated without them.
Explicit API filters are hard. A relevance gate on the best dense similarity prevents context padding and triggers the
"insufficient knowledge" answer without calling the LLM.

**Generation.** The model only sees numbered passages and must cite `[n]`; citations that don't match a passage are stripped and
reported in `warnings`; sources returned to the frontend come from retrieval metadata, never from model text. `INSUFFICIENT_CONTEXT`
from the model maps to `insufficient_knowledge`. Arabic by default, English when `language="en"` or the question asks for it;
identifiers/code stay verbatim (prompt rule 6).

**Gemini config.** Model ID only in `Settings.gemini_model` / `GEMINI_MODEL`; client has retry with backoff, 60 s timeout,
local daily request cap (`GEMINI_MAX_REQUESTS_PER_DAY`, counters in `data/usage.json`) and logs token counts. Keys are redacted
from every log record.

## Known limitations

- Intent routing is rule-based (place gazetteer + year/relative-time cues). Unlisted places can slip through as `knowledge`;
  an LLM-based classifier is a possible later upgrade.
- Crawled web text is cleaned heuristically; some navigation residue may remain.
- Local Qdrant allows one process per index directory (use one API worker, or move to Qdrant server for more).
- No reranker: not added because retrieval metrics on the evaluation set did not need one (see EVALUATION.md).
