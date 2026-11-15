# Astro EARTH

NASA Space Apps Challenge 2026 - **Be an Earth System Trend Detective**

Astro EARTH turns NASA Earth-system data into a guided investigation anyone can follow. Spin a 3D globe, pick a place (or any 0.5 degree grid cell), choose one of 12 variables such as temperature, rainfall, soil wetness or solar radiation, and the app answers the four questions of the challenge: **what** is changing, **where**, **how much**, and whether the change is **statistically significant**. A five-chapter "detective" dashboard walks through the evidence, compares two regions side by side and projects the trend forward with an honest uncertainty band. A bilingual (Arabic / English) AI assistant, grounded in NASA documentation and real data tools, explains results and answers follow-up questions without inventing numbers.

## How it maps to the challenge

| Challenge objective | Where |
| --- | --- |
| **What** - identify variables of interest, with simple definitions | 12-variable catalog (`src/lib/catalog.ts`, `variables` table), `GET /api/variables`, plain-language definitions in the variable selector, AI variable suggester |
| **Where** - acquire data for a region | Globe click, search, or arbitrary grid cell; NASA POWER monthly point API (MERRA-2 / CERES), cached in `timeseries_cache` |
| Time series over a long period | `GET /api/timeseries`, `GET /api/analysis` (`series`), from 1981 onward |
| **How much** - rate of change | OLS slope + Sen's slope per year, total and percent change |
| **Significant?** | Regression t-test (autocorrelation-adjusted), Mann-Kendall, 95% CI, combined verdict |
| Demo examples | 5 guided investigations (`demo_examples`, `GET /api/examples`) |
| Forecasting | Linear trend on deseasonalized data + seasonal cycle, 95% prediction band, hold-out backtest |
| Audience: students and the public | Guided chapters, per-chart explanations, AI assistant in Arabic and English |

## Feature tour

- **Start screen** (`src/app/page.tsx`, `src/components/StarField.tsx`): the logo and name over a live starfield; a click flies into the Earth page. Links that carry a place (`?lat=&lon=`) skip it.
- **3D globe** (`/earth`, `src/app/earth/page.tsx`, `src/components/ThreeEarth.tsx`): Three.js Earth with atmosphere, borders and fly-to; click anywhere or search a country / city.
- **Guided detective dashboard** (`src/components/DashboardView.tsx`): five chapters, from "what is the variable" to evidence, significance and outlook, with a plain-language verdict.
- **12 variables**: air temperature (mean / max / min), surface temperature, precipitation, evaporation, root-zone soil wetness, humidity, wind, cloud amount, surface solar radiation and surface pressure (see `src/lib/catalog.ts`).
- **Two-region comparison**: the same variable and period for two places side by side, since a trend can go one way in one region and the opposite way in another.
- **Forecast** (`src/components/ForecastView.tsx` and the dashboard forecast chapter): trend + seasonal cycle, 95% prediction interval, backtest against a seasonal baseline.
  The requested span is counted from today; months between the last NASA data month and today are forecast too and flagged. Three confidence zones are shown: **Tested** (up to the backtest length, about 5 years), **Extrapolation** (to 10 years, not validated) and **Computation only** (beyond 10 years). Horizons of 1, 2, 5, 10 and 20 years can be selected.
- **Sources on every result**: each dashboard chapter, the forecast page and each assistant answer shows what the result relies on and what it used, with a link to the exact NASA POWER request and to the method papers.
- **5 demo investigations**: Svalbard (T2M), Niamey (rainfall), Manaus (root-zone soil wetness), Amman (max temperature), Lhasa (solar radiation).
- **AI assistant**: floating popup and a full `/chat` page; see "Use of AI" below.

## Architecture

```
 Browser
    |
    v
 Next.js 16 (UI + route handlers)  -----------------> NASA POWER (MERRA-2 / CERES)
    |   src/app, src/components, src/lib                (monthly point API)
    |-------------------------------------------------> Supabase (optional cache,
    |                                                    catalog, region lists)
    |
    |  /api/assistant/{chat,reset,health}  (server-side proxy, AI_SERVICE_URL)
    v
 Python FastAPI AI service (nasa-challenge-API/earthtrend_rag, separate repo)
    |-- Claude Haiku: question -> validated decision; tool result -> wording
    |-- RAG index: Qdrant (local) + multilingual-e5-small, dense + BM25, citations
    |-- Data tools: NASA POWER trend, statistical forecast, Open-Meteo, FIRMS,
        GWIS / USGS fire danger, NIFC / Copernicus CEMS outlook, MODIS LST
        (AppEEARS), Sentinel-2 NDVI + scene discovery (Copernicus Data Space),
        NASA CMR dataset search
```

The browser only ever talks to Next.js. The assistant routes proxy to the Python service at `AI_SERVICE_URL` (default `http://127.0.0.1:8000`). If the service is down, the chat falls back to an offline grounded mode that answers from `/api/ai/context`. The dashboard, forecast and all statistics work without the AI service and without Supabase.

The AI service lives in its own repository: https://github.com/husambara/nasa-challenge-API (it is checked out under `nasa-challenge-API/` locally and is git-ignored here).

## Scientific method

1. **Data**: monthly values at the 0.5 degree grid cell containing the chosen point from NASA POWER (MERRA-2 reanalysis, CERES radiation).
2. **Deseasonalise**: subtract the per-calendar-month climatology to get monthly anomalies.
3. **Trend**: ordinary least squares on anomalies. The t-test uses an AR(1)-adjusted effective sample size `n(1-r1)/(1+r1)` so autocorrelation does not inflate significance.
4. **Mann-Kendall** (tie-corrected) on annual mean anomalies, with **Sen's slope** and a 95% confidence interval, as a non-parametric cross-check.
5. **Verdict**: `significant` only if both tests agree at alpha 0.05; `weak_evidence` if exactly one does; otherwise `not_significant`.
6. **Forecast**: linear trend on deseasonalised data plus the seasonal cycle, with a 95% prediction interval and a hold-out backtest compared with a seasonal baseline. The AI service has its own monthly forecaster (SARIMA / ETS versus seasonal-naive, climatology and climatology + trend baselines, rolling-origin backtests, 1-24 months).

### Limitations

- The data describe a **single 0.5 degree grid cell**, not a country or regional average.
- MERRA-2 is **reanalysis** (a model constrained by observations), not station measurements; local effects below the grid scale are not represented.
- The trend model is **linear**; nonlinear changes, breakpoints and multi-decadal variability are not modelled.
- Forecasts are **statistical extrapolation** of past behaviour, not physical climate projections.
- A non-significant result is not evidence of "no change"; a longer record may change the verdict.

## Setup and run

### 1. Next.js app

```bash
npm install
cp .env.example .env.local        # optional: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, AI_SERVICE_URL
supabase link --project-ref <ref> # optional
supabase db push                  # applies supabase/migrations
npm run db:seed                   # variables, examples, ~250 countries
npm run dev                       # http://localhost:3000
```

Without Supabase credentials the API still works (uncached, catalog from `src/lib/catalog.ts`); only `/api/regions/browse` needs the database. The service-role key is server-only. RLS blocks the anon key from everything except `variables`, `regions` and `demo_examples` (read).

Before a live demo, warm the cache so every example loads instantly:

```bash
node scripts/prewarm.mjs [http://localhost:3000]
```

### 2. Python AI service (optional but recommended)

Requires Python 3.13.

```powershell
cd nasa-challenge-API/earthtrend_rag
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt pandas statsmodels shapely netCDF4
```

Credentials go in `nasa-challenge-API/earthtrend_rag/.env` (never commit): `ANTHROPIC_API_KEY` is required for AI wording; optional `FIRMS_MAP_KEY`, `EARTHDATA_TOKEN`, `EARTHDATA_USERNAME` / `EARTHDATA_PASSWORD`, `CDSE_CLIENT_ID` / `CDSE_CLIENT_SECRET`, `EWDS_API_KEY` enable the corresponding data tools.

```powershell
.\.venv\Scripts\python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

**First run only**, build the knowledge index (about 3-4 minutes). A plain ingest skips everything because the committed manifest marks sources unchanged, so reset and force:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/rag/ingest -ContentType application/json -Body '{"reset":true,"force":true,"include_resources":true}'
```

Check status at `GET http://127.0.0.1:8000/api/rag/health`.

### 3. Both at once (Windows)

```powershell
npm run dev:all        # or: powershell -File scripts/dev-all.ps1
```

## API

All `GET` unless noted. Common params: `lat`, `lon`, `variable` (e.g. `T2M`), `start` (default 1990, min 1981), `end` (default last complete year), optional `name`.

| Endpoint | Purpose |
| --- | --- |
| `/api/regions/search?q=` | Search countries, cities, regions (home page search bar) |
| `/api/regions/browse?kind=country&filter=` | Browsable list from the database |
| `/api/regions/resolve?lat&lon[&name]` | Globe click or search pick: region record for the sidebar |
| `/api/variables` | Variable catalog (phenomenon picker) |
| `/api/examples` | Guided demo investigations |
| `/api/timeseries` | Raw monthly series |
| `/api/analysis` | Dashboard: series, trend, tests, summary, per-chart explanations |
| `/api/forecast?...&horizon=1..30` | Forecasting: historical + forecast + backtest + summary |
| `/api/ai/context?...[&horizon]` | Compact grounded facts for the AI assistant (offline fallback and AI service) |
| `/api/health` | Status and database connectivity |
| `POST /api/assistant/chat` | Proxy to the Python AI service chat |
| `POST /api/assistant/reset` | Proxy: reset the conversation |
| `GET /api/assistant/health` | Proxy: AI service and knowledge-index health |

Send an optional `x-session-id` header to log usage in `investigations`. Set `AI_CONTEXT_TOKEN` to require `Authorization: Bearer <token>` on `/api/ai/context`. Errors: `400 invalid_request`, `404 not_found`, `422 insufficient_data`, `502 upstream_unavailable`.

## Use of AI

AI is used only in the assistant, never to compute statistics.

- **Claude Haiku (`claude-haiku-5-5`)** interprets each question into a structured decision, which is validated before anything runs. Exactly one data tool then executes, and Claude explains the result.
- **Numbers come from tools, not the model.** The explanation may only use numbers present in the tool result; answers that fail this check are replaced by a deterministic template.
- **Tools**: trend (NASA POWER, Mann-Kendall + Sen), monthly forecast, Open-Meteo weather (up to 16 days), NASA FIRMS fire detections, fire danger (GWIS / USGS), wildfire danger outlook (NIFC, Copernicus CEMS), MODIS land surface temperature (AppEEARS), Sentinel-2 NDVI and scene discovery (Copernicus Data Space), NASA CMR dataset search.
- **RAG over NASA documentation**: local Qdrant, multilingual-e5-small embeddings, hybrid dense + BM25 retrieval, an evidence gate (no sources, no answer) and citations.
- **Graceful degradation**: if the AI service is unreachable, the chat answers offline from `/api/ai/context` facts.
- Arabic and English are supported.

## Data sources and references

Data and services
- NASA POWER (monthly point API): https://power.larc.nasa.gov/docs/services/api/
- MERRA-2 reanalysis (NASA GMAO): https://gmao.gsfc.nasa.gov/reanalysis/MERRA-2/
- CERES (radiation, via POWER): https://ceres.larc.nasa.gov/
- NASA FIRMS active fire data: https://firms.modaps.eosdis.nasa.gov/api/
- NASA Earthdata CMR: https://cmr.earthdata.nasa.gov/search
- NASA AppEEARS (MODIS LST): https://appeears.earthdatacloud.nasa.gov/
- NASA GIBS: https://www.earthdata.nasa.gov/eosdis/science-system-description/eosdis-components/gibs
- Open-Meteo (weather and geocoding, CC BY 4.0): https://open-meteo.com/en/docs
- Copernicus Data Space Ecosystem (Sentinel-2): https://dataspace.copernicus.eu/
- Copernicus Emergency Management Service / GWIS: https://gwis.jrc.ec.europa.eu/
- NIFC outlooks: https://www.nifc.gov/
- USGS Fire Danger Forecast: https://www.usgs.gov/fire-danger-forecast
- Country list: https://github.com/mledoze/countries
- BigDataCloud reverse geocoding: https://www.bigdatacloud.com/

Software
- Next.js https://nextjs.org/ , Three.js https://threejs.org/ , Supabase https://supabase.com/
- Qdrant https://qdrant.tech/ , sentence-transformers https://www.sbert.net/ with `intfloat/multilingual-e5-small`
- statsmodels https://www.statsmodels.org/ , FastAPI https://fastapi.tiangolo.com/

Statistical references (from the challenge resources)
- Statistical test methods to detect trends in time series data: https://medium.com/@snp.kriss/statistical-test-methods-to-detect-trends-in-time-series-data-b361a0ec530b
- A comprehensive guide to statistical significance: https://www.statsig.com/perspectives/a-comprehensive-guide-to-statistical-significance
- Giovanni: https://giovanni.gsfc.nasa.gov/

## Team and credits

- Team name: Astro Crash

NASA does not endorse this project. Data are used under the terms of their providers.
