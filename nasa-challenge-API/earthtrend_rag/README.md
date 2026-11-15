> **Local test prototype (chat UI + all data providers):** see `docs/PROTOTYPE_RUN.md` — start with `start_prototype.ps1`, open http://127.0.0.1:8000/.

# EarthTrend Explorer — RAG service

Knowledge-retrieval foundation of the AI Assistant. It answers **documentation / scientific-knowledge** questions
about NASA datasets and APIs from the project's own reference files, with source attribution, using
Gemini (default `gemini-3.5-flash-lite`, configurable; see `docs/GEMINI_RELIABILITY.md`) for grounded generation.

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

## Wildfire danger outlook (one month ahead)

A regional **danger** outlook for the next calendar month or the next 30 days. It answers "how does fire danger look relative to normal?", never "will a fire start?".
Ask in chat, e.g. `كيف خطر الحرائق في منطقة نابلس خلال الشهر القادم؟` or `What is the wildfire danger outlook for northern California next month?`
(task selector value: `fire_outlook`; the router sends explicit outlook phrasing to this tool even if the LLM picked another one).

### Rules the feature follows
* Official sources only: **NIFC** (US) and **Copernicus EWDS `cems-fire-seasonal`** (global). No short-range forecast is ever substituted for the monthly outlook.
* No probability conversion. Category shares are relative frequencies among ensemble members; a "70% chance of fire" question gets an explicit *no numerical probability* line.
* Mandatory wording in every successful answer: *"This is an official model outlook; local forecast skill has not been verified by this application."*
* Honest failure states (`needs_credentials`, `no_data`, `unsupported_region`, `unsupported_request`, `invalid_request`, `upstream_error`); a configured key is never reported as working until an authentication call succeeds.
* Observed FIRMS detections (last 5 days) are a **separate, labelled layer** ("observed, not a forecast") and never enter the computation.

### Sources and how each answer is produced
| Case | Source | Product | Computation |
|---|---|---|---|
| Inside the US | NIFC ArcGIS MapServer (Significant Wildland Fire Potential) | Above / Normal / Below per Predictive Service Area and GACC, one layer per month | A point gets the category of the area containing it; a region gets area shares (planar, lon scaled by cos lat). Freshness: the issue's `Updatetime` month must be the current month, or the previous month with day <= 7, otherwise the answer is marked stale/unavailable. |
| Rest of the world | EWDS `cems-fire-seasonal`, variable `fire_weather_index` (netCDF var `fwinx`) | 51-member ensemble, daily at 12:00 local time, issued once a month, horizon ~216 days | Request is validated against the live process schema; OGC async flow (submit, bounded poll, download) with the `PRIVATE-TOKEN` header; area-weighted regional mean per member (NaN cells such as sea are excluded); window mean per member. |
| Categories for EWDS | Same dataset, years 1981-2016 (re-forecast, 25 members x 36 years, same start month, same lead days, same area) | Reference distribution | Terciles of the reference window means are the only thresholds; each current member is counted below / near / above. These are member shares, not probabilities, and calibration is not verified. |

"Next month" is the next calendar month. "Next 30 days" is shown as the months that cover it with the number of days in each; it is not an exact rolling product.

### Files
| Path | Role |
|---|---|
| `app/providers/fire_outlook.py` | windows/freshness, NIFC client, EWDS client (availability, schema, request, run, NetCDF readers, ensemble analysis, reference), orchestrator `forecast_fire_danger` |
| `app/chat/{decision,router,agent,tools,render,panel,inline}.py` | intent routing, tool declaration, template answer, side panel (metrics, notes, legend data), inline category strip / ensemble chart |
| `frontend/app.js`, `styles.css` | map layers (forecast vs observed), colour+text legend, category strip, ensemble chart with p25-p75 and p10-p90 bands |
| `tests/test_fire_outlook.py`, `tests/integration/test_fire_outlook_live.py` | 42 offline tests (windows, matching, mocked NIFC, synthetic and real-layout NetCDF, reference terciles, routing, frontend checks) and live NIFC/EWDS checks |
| `presentation/` | demo script, explainer, judges Q&A, checklist (kept apart from the code) |

### Credentials (EWDS)
EWDS is a separate account from Earthdata and Copernicus Data Space.
1. Create/log in: https://ewds.climate.copernicus.eu/
2. Accept the dataset licence (CC-BY): https://ewds.climate.copernicus.eu/datasets/cems-fire-seasonal?tab=download#manage-licences
3. Copy the personal token: https://ewds.climate.copernicus.eu/how-to-api
4. Put `EWDS_API_KEY=<token>` in the backend `.env` (the one the loader reads, see *Known issues*), restart the server.

The key is redacted in logs, sent only as the `PRIVATE-TOKEN` header, and diagnostics keep three separate checks: public availability, authentication, data download.

### Official notice that affects the data (2026-11-12)
EWDS announced that **updates to this dataset cease on 2026-11-16 until further notice** while MARS is migrated to a new structure (data values stay identical; the dataset pages will be withdrawn for a few weeks while data is re-ingested, then return). No alternative dataset is named. Consequences handled by the app:
* The newest issue stays **2026-10-01** and remains valid for its own dates (until about May 2027). Issue date, issue age and valid period are reported separately.
* The notice text and the issue age appear in the answer limitations and the panel; nothing is replaced by another product.
* While the dataset is withdrawn, new downloads (including new reference downloads) may fail with an upstream error. Already cached files keep working.

### What happens for a place or month that was not prepared
| Situation | Result |
|---|---|
| US location | NIFC answer immediately (no download) |
| Non-US place whose reference is cached | Full answer with categories immediately |
| Non-US place, current forecast not cached | The request downloads it (~1-2 min) and answers with the raw ensemble index |
| Non-US place, reference not cached | Answer with the raw index and the note that categories will appear on a later request; the reference downloads in a background thread (~6-7 min, EWDS queue time) |
| Target period before the issue or beyond ~216 days | `no_data` (`MISSING_FORECAST_COVERAGE`), nothing invented |
| No token or licence not accepted | `needs_credentials` with the exact steps |
| EWDS unreachable or dataset withdrawn | `upstream_error`, nothing substituted |

Prepared for the demo (December 2026, issue 2026-10-01): Nablus, Gaza, Amman. The demo cache files (3 current forecasts + 3 references, ~1.2 MB, with attribution in `data/downloads/NOTICE.md`) are committed; any other file in `data/downloads/` stays git-ignored.

### What would be needed to cover many more places
Measured on 2026-11-15 (the grid is 1 degree):
* A 1 x 1 degree reference request: ~350 KB, ~6-7 min. A 10 x 10 degree tile (27-37N, 30-40E): **8.3 MB, 7.3 min, accepted without a size error**. Time is dominated by the EWDS queue, not by size.
* Extrapolation (not measured): global ~65,000 cells -> up to ~4.5 GB per target month (less in practice, sea cells compress), ~7 target months from one issue -> ~20-30 GB. That is hundreds of 10-degree requests; larger tiles and parallel jobs were **not tested**.

Recommended path if the scope grows (not implemented; the current prototype is sufficient for the demo):
1. Tile-based reference cache, so any place inside a downloaded tile gets categories instantly (the Levant tile alone would cover Nablus, Gaza, Amman, Jerusalem, Damascus, Beirut).
2. Store only per-cell terciles after computing them (two numbers per cell and window) instead of raw reference files.
3. Prefetch priority regions first (Middle East, North Africa, southern Europe), for the months most likely to be asked (December to March).
4. Test a 30 x 30 degree tile and two concurrent jobs to learn the real cost.
5. Download while the dataset is still available: the migration may withdraw it for weeks.
6. After the migration, re-read the availability call; the new issue should appear without code changes (the code reads the latest start month from the public constraints).

### Limitations
* Forecast skill has **not** been verified locally; there is no comparison against a fire record. That is the stated validation gap.
* A one-month outlook of a weather-based danger index says nothing about ignition sources; zero observed detections do not mean zero danger.
* The grid is coarse (1 degree); a point is represented by the cells of a ~1 degree box (default +/-0.5 degree around the geocoded place, or the requested bbox).
* EWDS skill at 2-3 months lead is limited, and the member spread is not a calibrated uncertainty estimate.
* Downloads are cached per exact request; a different bbox means a different download.

### الخلاصة بالعربية
توقع شهري رسمي لـ**خطر** الحرائق (وليس احتمال حريق): NIFC لأمريكا، وCopernicus EWDS لبقية العالم. الفئات (أقل/قريب/أعلى من المعتاد) تأتي من أثلاث مرجع 1981–2016 وتُعرض كحصص أعضاء المجموعة. إصدار البيانات الحالي 2026-10-01 لأن EWDS أوقف التحديث من 16 نوفمبر 2026 بإشعار رسمي. المجهز للعرض: نابلس وغزة وعمّان لديسمبر 2026. أي مكان آخر يعمل لكن يحتاج تنزيل مرجع في الخلفية (6–7 دقائق) فيظهر المؤشر الخام أولًا. التوسع لأماكن كثيرة ممكن عبر بلاطات مخزنة، والخطوات والتقديرات أعلاه، ولم يُنفَّذ لأن الوضع الحالي يكفي للعرض.

## Known issues

* A live `gemini-3.8-flash` request on 2026-11-14 returned a structured daily-quota 429 (limit 20 for this project/model). Do not generalise that limit to every model/account. Integration service errors now fail instead of skipping; use the bounded diagnostic below before a full integration run.
* The two reference files name the tools differently (`search_datasets/fetch_timeseries/analyze_trend` vs `get_nasa_power_series/analyze_trend`); `TOOL_MAP` follows the first.
* The current key loader successfully reads `البروتوتايب/.env`; diagnostics report presence only.

## Repeatable diagnostics

Run from `earthtrend_rag` using the application's own Python:

```powershell
./.venv/Scripts/python.exe -m pytest -q
./.venv/Scripts/python.exe -m app.diagnose --out data/debug_offline.json
./.venv/Scripts/python.exe -m app.diagnose --live-power --out data/debug_power.json
./.venv/Scripts/python.exe -m app.diagnose --live-gemini --model gemini-3.8-flash --max-gemini-requests 3 --out data/debug_gemini.json
./.venv/Scripts/python.exe -m app.diagnose --live-gemini --real-rag --max-gemini-requests 8 --out data/debug_full.json
```

No network checks run by default. POWER uses at most four uncached HTTP requests.
Gemini diagnostic calls disable model fallback and retries and respect the existing local quota state.
The full check has an explicit maximum of eight model calls; a failed prerequisite blocks dependent checks.
Exit status: 0 for passing selected checks, 1 for failure, 2 for blocked checks.
Reports distinguish cache hits and `answer_source=template` from successful live generation.
No probe deletes usage counters or enables billing. See `docs/DEBUG_REPORT_AR.md` for findings and limitations.

`REQUEST_TOTAL_DEADLINE_S` defaults to 90 seconds across the API/agent request;
`POWER_TOTAL_DEADLINE_S=30`, `POWER_CONNECT_TIMEOUT_S=5`, `POWER_READ_TIMEOUT_S=15`,
`POWER_MAX_ATTEMPTS=2`. The Gemini per-call deadline is also capped by the remaining request budget.
Trend responses expose `answer_source` (`gemini` or `template`) and `fallback_reason`.
