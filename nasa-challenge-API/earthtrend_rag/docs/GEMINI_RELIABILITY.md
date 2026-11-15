# Gemini reliability (diagnosis of the 503/504 failures and what was changed)

## Evidence collected (2026-11-14, real calls, key never printed)

| Observation | Evidence |
|---|---|
| Key, endpoint and SDK are fine | `models.list` returns 20 Gemini models for the key; `google-genai 3.3.0`, base URL `generativelanguage.googleapis.com`, API `v1`; no proxy variables set; host reachable. Cheap models answered in 0.6 s. |
| Model ID is valid | `gemini-3.8-flash` is listed for the key and documented as Stable (function calling supported). |
| 503 "high demand" / 504 "deadline expired" | Returned by the service for `3.8-flash`, `3.7-flash`, sometimes `3.6-flash` and `3.5-flash`, **no Retry-After header**. Transient server-side overload; our code cannot fix it, only bound and absorb it. |
| 429 daily quota | Structured error: `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, **limit 20 per day per project per model** (`3.8-flash` and `3.6-flash` both confirmed), `retryDelay` ~45,500 s (midnight-Pacific reset). |
| Old client made it worse | It retried 429s and 5xx up to 4x with the SDK's own retry layer possible underneath, and its local cap (200/day) was 10x the real limit. Every failed attempt may count against a 20/day quota (probable, not proven). |

Not established: why `3.8-flash` was overloaded for hours (service-side; no evidence beyond the 503/504 bodies).

## Changes

* `app/llm/gemini_client.py` rewritten: SDK retries off (single retry layer); per-attempt timeout (30 s), max 3 attempts/model,
  **total deadline 75 s**; exponential backoff with full jitter for 500/502/503/504, network errors and timeouts; honours
  `Retry-After` / `RetryInfo`; never retries 400/401/403/404; **daily-quota 429 is not retried and is cached** (later calls skip the model with
  no network call); local per-model cap (default 18/day); optional free-tier fallback models; the explanation turn of a function call is pinned
  to the model that issued the call; errors carry `.kind` (`quota | overloaded | timeout | network | auth | invalid_request | ...`) and
  never contain the key.
* `app/config.py`: `GEMINI_MODEL`, `GEMINI_FALLBACK_MODELS`, `GEMINI_DAILY_CAP_PER_MODEL`, `GEMINI_REQUEST_TIMEOUT_S`,
  `GEMINI_TOTAL_DEADLINE_S`, `GEMINI_MAX_ATTEMPTS`. Defaults: primary `gemini-3.5-flash-lite`, fallbacks `gemini-3.1-flash-lite`, `gemini-3.8-flash`.
* `app/agent/trend_agent.py`: explicit years in the question override mis-extracted `start_year/end_year` (the model returned 2024 for "2005–2025" in two real runs);
  `95%` is accepted as the CI level; the prompt forbids leaking JSON field names. The tool runs once per question regardless of client retries.
* Deterministic template remains the fallback; it is reported as `answer_source = "template"` and is never counted as a Gemini success.

## Model comparison (real free-tier calls; all four document function-calling support and "free of charge")

| model | steps tried | Gemini success | latency | notes |
|---|---|---|---|---|
| `gemini-3.5-flash-lite` | 10 + 3 via API | 13/13 | 0.6–3.3 s | no 5xx seen; correct tool args; chosen |
| `gemini-3.1-flash-lite` | 10 | 10/10 | 0.8–6 s (one 47 s with 2 retries) | wrong `end_year` once (guard corrected it) |
| `gemini-3.6-flash` | 6 | 4/6 | 3–9 s with 503 retries | free quota exhausted mid-run |
| `gemini-3.8-flash` | many | 1 success in ~17 min of retries, then 429 | up to 1020 s | overloaded, then 20/day quota hit |
| `gemini-3.5-flash` | 10 | 0/10 | - | daily quota already exhausted |

Free tier note (official pricing page): free-tier prompts may be used to improve Google products.

## Follow-up audit (2026-11-14, later session) -- corrections and additions

* **Quota day**: Google resets daily free-tier quotas at *midnight Pacific time*; the first tracker used UTC days. `UsageTracker` now keys days by
  `America/Los_Angeles` (needs the `tzdata` package on Windows; falls back to fixed UTC-8), so the reset is 08:00 UTC in winter.
* **Exhausted marker** lasts until the reset the service announced (`RetryInfo.retryDelay`), or the next Pacific midnight when none was given;
  expired markers are purged on every write. A 429 is treated as *daily* only when the structured error says `...PerDay...`; a short
  `retryDelay` without that is a per-minute limit (retried once if <= 30 s and inside the deadline).
* **Concurrency/restarts**: counters live in `data/usage.json`, updated under a thread lock + cross-process file lock (`portalocker`) with an atomic
  replace; tests cover restart persistence, 6 threads and 3 spawned processes (no lost increments).
* **Do not generalise the "20/day" figure**: it was observed inside 429 responses for `gemini-3.8-flash` and `gemini-3.6-flash` only. The official
  rate-limits page publishes no free-tier table (it points to AI Studio and says limits vary by model/tier); `evidence/gemini_docs_check.json`
  records this. Limits for the other models are unknown until exceeded; the local cap (default 18) is only a safety net.
* **Deadlines**: one total deadline (`GEMINI_TOTAL_DEADLINE_S`) covers every model and attempt of a call; the whole trend question runs under
  `request_total_deadline_s`; NASA POWER has its own connect/read/total timeouts (`POWER_*`), independent of Gemini's.
* **Tool runs once**: retries live inside the Gemini client; the tool executes only after a response, and a failed explanation turn reuses the
  stored tool result (template, `answer_source = "template"`, `fallback_reason` set).
* **Period guard**: explicit years override the model's arguments only for one unambiguous period (`between A and B`, `from A to B`, `A-B`, `since A`);
  questions with several periods/years are answered with a clarification and no tool run.
* **Number guard**: `95%` is accepted only for `ci_level` / `alpha` / `coverage_fraction`; scientific notation, rescaled slopes and sign changes are rejected.
