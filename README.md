# EarthTrend Explorer - Backend

NASA Space Apps 2026, challenge **Earth System Trend Detective**.
Next.js route handlers (`src/app/api`) + Supabase (Postgres). The AI Assistant
lives in a separate repo and talks to this backend through `/api/ai/context`.

## How it maps to the challenge

| Challenge objective | Where |
| --- | --- |
| Identify variables of interest, with simple definitions | `variables` table, `GET /api/variables` |
| Acquire data for a region | NASA POWER monthly point API (MERRA-2 / CERES), cached in `timeseries_cache` |
| Time series over a long period | `GET /api/timeseries`, `GET /api/analysis` (`series`) |
| Rate of change | OLS slope + Sen's slope per year, total and percent change |
| Significance | Regression t-test (autocorrelation-adjusted), Mann-Kendall, 95% CI, combined verdict |
| Demo examples | `demo_examples`, `GET /api/examples` |
| Forecasting | Linear trend on deseasonalized data + seasonal cycle, 95% prediction band, hold-out backtest |

Trend method: the seasonal cycle is removed first (per-month climatology). The
t-test runs on monthly anomalies with the effective sample size
`n(1-r1)/(1+r1)`. Mann-Kendall (tie-corrected) runs on annual mean anomalies to
avoid autocorrelation. Verdict: `significant` only if both tests agree at
alpha 0.05, `weak_evidence` if one does, otherwise `not_significant`.

## Setup

```bash
npm install
cp .env.example .env.local        # fill SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
supabase link --project-ref <ref>
supabase db push                  # applies supabase/migrations
npm run db:seed                   # variables, examples, ~250 countries
npm run dev
```

Without Supabase credentials the API still works (uncached, catalog from
`src/lib/catalog.ts`); only `/api/regions/browse` needs the database.
The service-role key is server-only. RLS blocks the anon key from everything
except `variables`, `regions` and `demo_examples` (read).

## API

All `GET`. Common params: `lat`, `lon`, `variable` (e.g. `T2M`), `start` (default 1990, min 1981), `end` (default current year), optional `name`.

| Endpoint | Purpose |
| --- | --- |
| `/api/regions/search?q=` | Search countries, cities, regions (home page search bar) |
| `/api/regions/browse?kind=country&filter=` | Browsable list from the database |
| `/api/regions/resolve?lat&lon[&name]` | Globe click or search pick: region record for the sidebar |
| `/api/variables` | Variable catalog (phenomenon picker) |
| `/api/examples` | Guided demo investigations |
| `/api/timeseries` | Raw monthly series |
| `/api/analysis` | Dashboard: series, trend, tests, summary, per-chart explanations |
| `/api/forecast?...&horizon=1..30` | Forecasting page: historical + forecast + backtest + summary |
| `/api/ai/context?...[&horizon]` | Compact grounded facts for the AI Assistant service |
| `/api/health` | Status and database connectivity |

Send an optional `x-session-id` header to log usage in `investigations`.
Set `AI_CONTEXT_TOKEN` to require `Authorization: Bearer <token>` on `/api/ai/context`.
Errors: `400 invalid_request`, `404 not_found`, `422 insufficient_data`, `502 upstream_unavailable`.

## Data sources

- NASA POWER (MERRA-2, CERES): https://power.larc.nasa.gov/
- Country list: github.com/mledoze/countries; geocoding: Open-Meteo; reverse geocoding: BigDataCloud
