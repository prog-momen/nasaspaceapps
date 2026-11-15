# EarthTrend Explorer — local test prototype

**Project folder:** `C:\nasa challenge API\earthtrend_rag`  (working directory for every command below)
**Launcher:** `C:\nasa challenge API\earthtrend_rag\start_prototype.ps1` (double-click alternative: `start_prototype.bat`)
**Browser URL:** `http://127.0.0.1:8000/` (the launcher moves to 8001… if 8000 is busy and prints the real URL). Bound to `127.0.0.1` only — no firewall change, not reachable from other machines.

## First-time setup (once)

```powershell
cd "C:\nasa challenge API\earthtrend_rag"
powershell -NoProfile -ExecutionPolicy Bypass -File start_prototype.ps1 -Install    # creates .venv if missing and installs requirements.txt
```

Put secrets only in a backend file, never in the chat or the browser: `C:\nasa challenge API\earthtrend_rag\.env` (template: `.env.example`).
The prototype also reads `C:\nasa challenge API\البروتوتايب\.env` (where the Gemini key currently lives). All of these are git-ignored.

## Normal start / stop

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\nasa challenge API\earthtrend_rag\start_prototype.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\nasa challenge API\earthtrend_rag\stop_prototype.ps1"
```

The start script uses `.venv`, checks the dependencies, picks a free port, starts the backend hidden, waits until `/api/rag/health` answers
(the embedding model takes ~30–60 s to load) and opens the browser. Add `-NoBrowser` to skip the browser. `stop_prototype.ps1` stops only the PID in `data\server.pid`.

* Logs: `data\server.log` (stdout), `data\server.err.log` (uvicorn/app log). Secrets are redacted from logs.
* State: `data\usage.json` (Gemini counters), `data\diagnostics_last.json` (last provider tests), `data\cache\` (response caches), `data\qdrant\` (knowledge index).
* The local Qdrant index allows ONE process at a time: stop the server before running scripts that open the index (e.g. evaluation).

## Using the chat

* Just type (Arabic or English, any wording). **Example buttons submit exactly the same text through the same `send(text)` path** - there is no hidden metadata.
* Each message becomes an inspectable **decision record** (intent, place, variable, period/horizon, provider, missing info) - Claude Haiku first (forced Tool Use of `interpret_request`), the deterministic router only as a labelled fallback. The record is validated against real capabilities before any tool runs (e.g. a multi-year question can never reach short-term weather; >16-day forecasts and future trends are refused). See "Technical details" under each answer.
* Answers are short (conclusion + essential numbers + citation) and written in the **language of your message** (UI language is only the fallback). Full statistics, charts, tables, provenance and limitations are in the **results panel** beside the chat (tabs on mobile). Click a message (or "Show analysis") to show *its* analysis; a failed/unsupported message never shows an older result.
* The map follows the resolved place: marker for the requested place, rectangle for the real data footprint (POWER ~0.5x0.625 deg cell, FIRMS query box), model grid point for Open-Meteo. Ambiguous names (e.g. Springfield) trigger one question instead of a guess; large regions are representative points and are labelled so.
* "Analysis settings" (collapsed) holds the optional controls (task, variable, dates, point/box, answer mode). If they differ from the message, the assistant asks which to use.
* Outcome chip categories: answered / valid query with zero detections / no matching data / unsupported / needs a key / provider unavailable / model unavailable (quota) / needs clarification / insufficient evidence. A Gemini quota failure is shown as a small notice and never as "no data".
* Documentation answers use only passages that pass the relevance gate (`app/rag/evidence.py`); otherwise: "Insufficient resources to answer this accurately." plus the reason.
* New conversation clears history and memory (sessions are isolated, last 8 turns).
* Markdown in answers is rendered by a small escape-by-construction renderer (no HTML injection, http(s) links only).
* Diagnostics panel (collapsed; loading it makes **no** Gemini request); the Gemini test button spends one request and asks first.

## Providers: capability, authentication, coverage, status (verified 2026-11-14)

| Source | Capability | Authentication | Coverage | Status |
|---|---|---|---|---|
| NASA POWER | historical climate (monthly T2M air temp, PRECTOTCORR, RH2M, WS2M) → Mann–Kendall + Sen | none | global, 1981+, ~0.5° grid | **verified live** (+ reference comparison, `evidence/`) |
| Open-Meteo | operational weather forecast (≤16 d) and ERA5-type historical weather | none (free API: non-commercial, CC BY 4.0 attribution) | global | **verified live** |
| NASA FIRMS | active-fire **detections** (not incidents/burned area) | free `FIRMS_MAP_KEY` | global, 1–5 day windows | **verified live with the configured key** (2026-11-15). Sensor is chosen from the official `data_availability` endpoint (VIIRS S-NPP NRT had no data after 2026-11-02, which returns a header-only CSV that must not be read as zero fires) |
| GWIS | fire danger products (FWI family, WMS map layers) | none | global | **verified live** for listing + GetMap; numeric point query **not available** (tested) |
| USGS Fire Danger Forecast | fire danger map classes (WFPI day 1–7) | none | contiguous US only | **verified live** (palette class index only, not a calibrated value); outside US → unsupported |
| Copernicus Data Space | Sentinel scene discovery (STAC) + previews; NDVI processing | none for discovery; `CDSE_CLIENT_ID/SECRET` for processing | global | discovery **verified live**; OAuth + NDVI (Sentinel-2 L2A, SCL/invalid-reflectance masked, <=1 deg) **verified live** |
| NASA Earthdata | CMR discovery, GIBS visualisation, granule download, AppEEARS LST point sampling | none for CMR/GIBS; `EARTHDATA_TOKEN` (download), `EARTHDATA_USERNAME/PASSWORD` (AppEEARS own token) | global | CMR + GIBS **verified live**; token download **verified live** (5.3 MB MOD11A2 HDF4 granule downloaded, signature + HDF-EOS grid metadata read; pixel decoding needs an HDF4 library, not installed); AppEEARS login **verified live**; LST task: see test report |
| Google Earth Engine (optional) | catalog discovery; small region/date mean | public STAC for discovery; authorised project (`EE_PROJECT`) for compute | global | catalog **verified live**; compute implemented, **blocked: no authorised project / package** |

### Credential setup (official links and required permissions)

* **FIRMS** — https://firms.modaps.eosdis.nasa.gov/api/map_key/ : enter your email, the free key is emailed. `FIRMS_MAP_KEY=<key>` in `.env`. Limit 5,000 transactions / 10 min.
* **Earthdata** — https://urs.earthdata.nasa.gov/users/new : create a free Earthdata Login; approve the data-provider applications you need; create a User Token at https://urs.earthdata.nasa.gov/profile → `EARTHDATA_TOKEN`.
  For AppEEARS also authorise https://appeears.earthdatacloud.nasa.gov/ and set `EARTHDATA_USERNAME` / `EARTHDATA_PASSWORD`.
* **Copernicus Data Space** — https://dataspace.copernicus.eu/ : free account → Dashboard → User settings → OAuth clients → `CDSE_CLIENT_ID` / `CDSE_CLIENT_SECRET` (Sentinel Hub processing units apply).
* **Earth Engine** — https://developers.google.com/earth-engine/guides/access : registration/eligibility/quota/billing rules are Google's. This prototype never creates projects or enables billing.
  `pip install -r requirements-optional.txt`, `earthengine authenticate`, set `EE_PROJECT`.
* **Language model: Anthropic `claude-haiku-5-5` ONLY** — `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` in `.env`. A hard allow-list in `app/llm/claude_client.py` rejects any other model before a request is sent; there is no fallback model (Gemini was removed). On failure the chat uses the labelled deterministic path or returns a clear error. Embeddings stay local (`multilingual-e5-small`).

Missing credentials only disable the dependent feature; the chat explains exactly what to set.

## Attribution / terms

Open-Meteo: "Weather data by Open-Meteo.com", CC BY 4.0, free API non-commercial only. NASA FIRMS/POWER/Earthdata/GIBS: acknowledge NASA. Copernicus: "Contains modified Copernicus Sentinel data".
GWIS: check the GWIS data licence. USGS: public domain. OpenStreetMap tiles: © OpenStreetMap contributors (personal testing only).

## Known limitations

* `.env` files accept `NAME=value` and `NAME: value` (the reader is tolerant); values are never printed.
* LST (MODIS MOD11A2, AppEEARS) is SURFACE temperature, quality-filtered (QC MODLAND=0, LST error <= 2 K, valid range, fill removed) and converted K -> degC; it is never mixed with air temperature T2M. AppEEARS tasks queue on NASA servers (minutes to an hour): the chat keeps the task and answers 'task running' until it is done.

* Gemini free-tier quota can be exhausted for hours; the model-led path was verified with a fake client + the real SDK schema, and live only when quota allows (see the test report). While blocked, only unambiguous requests are answered, via the labelled deterministic router.
* Evidence gate (real index, 14 answerable / 10 unanswerable questions): before 14/14 answerable accepted but 6/10 unanswerable wrongly accepted; after 13/14 and 0/10 (`scripts/eval_evidence_gate.py`, `evidence/evidence_gate_eval.json`). One valid English question against the Arabic reference is rejected (conservative by design).
* Logs: provider URLs are no longer logged by httpx and every configured credential value is redacted.

* T2M is air temperature, never land surface temperature; LST needs AppEEARS credentials and is not wired into the monthly trend test.
* Forecasts come only from Open-Meteo (≤16 days, no issue time published). Multi-year "forecasts" are refused; trends are historical descriptions.
* Fire detections are thermal anomalies; no conversion to burned area/incident counts. Fire danger indices are not probabilities.
* USGS point query = map palette class; GWIS = map layers only. GIBS/WMS layers are visualisation, not measurements.
* Scene discovery only (no pixel processing without CDSE credentials). OLS and daily hot-day analyses are future capabilities (the original reference script is absent).
* Gemini free tier: quota-limited; when blocked the app answers with labelled deterministic templates.
* The map needs internet for OpenStreetMap tiles and the Leaflet library (CDN); the rest of the UI works without it.
