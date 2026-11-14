# 🚀 NASA Space Apps - Backend & AI Pre-Delivery Roadmap & TODO
**File Path:** `c:\Users\97056\Desktop\nasaspaceapps\TODO_BACKEND_AI.md`  
**Status:** Preserved intact as requested (No modifications made to backend or AI models)  
**Created Date:** November 2026

---

## 📌 1. Background & Guardrail Notice
In accordance with user instructions:
> *"دون لمس ما يخص الباك اند او ال AI - ادا في اشي بيخص الباك اند او الAI ما تعدلهم حطهم بملف TODO مهم واعطيني الباث تبعه"*

All backend data pipelines, API routes (`/api/analysis`, `/api/forecast`, `/api/ai/*`), database schemas, and external AI calls have been preserved with zero breaking changes. This document outlines the critical recommendations, performance optimizations, and integration tasks for the backend and AI systems before final challenge submission.

---

## 🧩 2. Backend Architecture: High Priority Tasks

### 2.1. Caching & Rate-Limit Shield for NASA POWER API
* **Current State:** Direct fetch in `src/lib/services/data.ts` queries the NASA POWER API on every analysis request.
* **Risk:** During judging or live demonstrations, simultaneous requests for the same coordinates or date range can trigger NASA POWER HTTP 429 (Too Many Requests) or long wait times (~1.5s - 3s).
* **Action Required:**
  1. Add an in-memory or Redis LRU cache layer (TTL: 24h) keyed by `hash(lat, lon, variable, start, end)`.
  2. For common challenge locations (Amman, Svalbard, Niamey, Manaus, Lhasa), pre-warm the cache during deployment.
  3. Ensure stale-while-revalidate strategy so users experience sub-100ms response times.

### 2.2. Supabase / PostgreSQL Schema & Query Indexing
* **Current State:** Uses table upserts (`analyses`, `forecasts`, `events`, `logs`).
* **Action Required:**
  1. Ensure the composite index exists on:
     ```sql
     CREATE INDEX IF NOT EXISTS idx_analyses_lookup 
     ON analyses (region_key, variable_key, start_year, end_year);
     
     CREATE INDEX IF NOT EXISTS idx_forecasts_lookup 
     ON forecasts (region_key, variable_key, start_year, end_year, horizon_years);
     ```
  2. Implement RLS (Row Level Security) policies allowing anonymous public reads for verified analyses while restricting writes to server-role key.

### 2.3. Batch Comparative Analysis Endpoint (`/api/compare`)
* **Current State:** Frontend fetches Region A and Region B using two independent parallel `/api/analysis` queries.
* **Action Required:**
  - Introduce an optimized endpoint `GET /api/compare?lat1=...&lon1=...&lat2=...&lon2=...&variable=...&start=...&end=...` that executes both NASA POWER queries concurrently via `Promise.all` on the server and returns unified differential statistics (e.g., $\Delta \text{Slope}$, relative variance ratio).

### 2.4. Global Arbitrary Coordinate & Grid Cell Resolution
* **Current State:** Coordinates are snapped to 0.5° NASA grid cells (`resolveRegion` in `src/lib/services/data.ts`).
* **Action Required:**
  - When clicking uninhabited open ocean or remote desert, maintain the "Point / Grid Cell (lat, lon)" nomenclature.
  - Optional enhancement: Add offline coarse land/ocean masking or lightweight reverse-geocoding (e.g., country boundaries GeoJSON polygon check) without relying on third-party external network calls.

---

## 🤖 3. AI Assistant & RAG Pipeline Tasks

### 3.1. `/api/ai/context` Enrichment & Payload Structure
* **Current State:** Basic context generation based on query parameters.
* **Action Required:**
  1. Enrich context payload to automatically include:
     - Full 5-point summary: Baseline Normal Range, Anomaly Frequency, Sen's Slope per decade, Mann-Kendall $p$-value verdict, and 12-Month Outlook.
     - Relevant NASA satellite missions observing the variable (e.g. MODIS, CERES, MERRA-2, GRACE-FO).
  2. Ensure fallback coordinates default to baseline (e.g., Amman/Palestine: `31.95, 35.23`) rather than failing or returning `0,0` Gulf of Guinea.

### 3.2. AI System Prompt & Persona Tuning
* **Target Audience:** High school / university students and curious public ("NASA Earth System Trend Detective").
* **Recommended System Prompt Updates in `src/lib/services/ai.ts`:**
  - Tone: Engaging, scientifically accurate, encouraging curiosity, avoiding dry statistical dump unless user asks in "Scientist Mode".
  - Always explain the real-world consequence:
    - If `T2M` (Temperature): Urban heat, agriculture impact, crop growing seasons.
    - If `PRECTOTCORR` (Precipitation): Drought frequency, flood resilience.
    - If `GWETROOT` (Root-zone soil moisture): Groundwater depletion, vegetation stress.

### 3.3. AI Tool / Action Calling (Interactive Earth Driving)
* **Action Required:**
  - Allow the AI to return structured UI actions alongside chat responses:
    ```json
    {
      "action": "SET_SELECTION",
      "payload": { "lat": 78.2, "lon": 15.6, "variable": "T2M", "name": "Svalbard" }
    }
    ```
  - This lets the AI directly fly the 3D Globe to the region it is discussing!

---

## 📊 4. Scientific & Statistical Verification

| Module | File | Recommended Audit |
| :--- | :--- | :--- |
| **OLS & Sen's Slope** | `src/lib/stats/trend.ts` | Verify Kendall Tau tie handling for discrete integer precip readings |
| **Autocorrelation** | `src/lib/stats/trend.ts` | Verify AR(1) lag-1 serial correlation calculation across monthly deseasonalized residuals |
| **Forecast Model** | `src/lib/stats/forecast.ts` | Check holdout backtest (MAE & RMSE) verification metric for 10-year horizon |
| **Data Integrity** | `src/lib/services/data.ts` | Validate missing month interpolation (-999.0 fill values in NASA POWER data) |

---

## 📁 5. Relevant Backend & AI Files Reference
- `src/lib/services/data.ts` - NASA POWER fetch, region resolution, cache & storage.
- `src/lib/services/ai.ts` - RAG pipeline, context synthesis, LLM stream handler.
- `src/lib/stats/trend.ts` - Mann-Kendall, Sen's slope, deseasonalization, OLS regression.
- `src/lib/stats/forecast.ts` - 1-10 year projection engine & confidence envelopes.
- `src/app/api/analysis/route.ts` - Endpoint for full trend analysis.
- `src/app/api/forecast/route.ts` - Endpoint for predictive modeling.
- `src/app/api/ai/context/route.ts` - Location & trend semantic context endpoint.
- `src/app/api/ai/chat/route.ts` - Streaming chat response endpoint.

