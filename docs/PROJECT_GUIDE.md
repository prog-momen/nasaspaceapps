# Astro EARTH: project guide for the team

Use this file to prepare the presentation and the judges' Q&A. Everything here matches the code as it is now.

## 1. The dashboard page, section by section

Open a place with `/dashboard?lat=…&lon=…&name=…&variable=…&start=…&end=…`, or click **View Dashboard** on the globe.

| Area | What it shows | Why it is there |
|---|---|---|
| Header | Place name, coordinates, variable and period | Confirms what is being analysed |
| All 12 Variables & Period | Full variable list with definitions and a 5 / 10 / 20 / full-archive selector | Choose a variable in plain words |
| Compare 2 Regions | Two places on one chart with yearly means and each trend | Answers "where" and "does it differ?" |
| 3D Globe | Returns to the globe with the place selected | Navigation |
| Demo scenarios | Five ready investigations (Svalbard, Niamey, Manaus, Amman, Lhasa) | Fast demo and guided start |
| Chapter stepper (1–5) | Moves through the investigation | Story structure |
| Story card (left) | Plain-language text for the chapter, with the key number | For a non-expert reader |
| Stage (right) | The chart for the chapter | The evidence |
| Ask AI Detective | Opens the assistant | Explains the chapter in words |
| Sources for chapter | What the chapter relies on, and what this result used | Traceability (added this week) |
| Scientist View | Full statistics: Sen's slope, Mann-Kendall p, OLS slope and standard error, autocorrelation, effective n | For a scientist reviewing the method |

**The five chapters**

1. **Meet the Location & Data Trust.** The normal range of the place: mean, typical band, and data completeness.
2. **The Bumps & Extremes.** Is the variation steady or wild? The standard deviation and the six highest and six lowest months are marked.
3. **The Detective Verdict.** The trend per decade, total change, and the verdict. The verdict is *significant* only when the regression t-test and Mann-Kendall agree.
4. **The Rhythm of Seasons.** The 12-month cycle is removed so the long-term change is visible.
5. **The Future Horizon.** A forecast with a 95% prediction interval and a backtest against a seasonal baseline.

## 2. The method in one paragraph

NASA POWER gives monthly values for the grid cell that contains the chosen point (about 0.5° × 0.625°, roughly 50 km). We subtract each calendar month's mean to remove the seasons. A least-squares trend is fitted to the anomalies, and its t-test uses an effective sample size that accounts for month-to-month correlation. Mann-Kendall with Sen's slope runs on yearly means as a second, non-parametric check. The verdict is *significant* only when both agree at α = 0.05; one of them is *weak evidence*; neither is *not significant*.

## 3. Whole project, for the discussion

**Problem.** Earth data is public, but answering "is my region getting hotter, and is that real?" needs variable knowledge, data access and statistics. Students and the public cannot easily do this.

**Solution.** A web app: pick a place on a 3D globe, pick a variable, get a guided investigation with a tested verdict. An AI assistant answers in English or Arabic, uses real data, and cannot invent numbers.

**Architecture.**

```
Browser
  │
Next.js (UI, statistics in the browser, /api routes)  ──► NASA POWER, Supabase cache (optional)
  │
  └─ /api/assistant/* proxy ──► Python AI service ──► Claude Haiku (wording and request understanding only)
                                           ├─ RAG index of NASA documentation (local Qdrant)
                                           └─ FIRMS, Copernicus EWDS / Data Space, NIFC, Open-Meteo, AppEEARS
```

**What the AI does and does not do.** Claude reads the question and writes the answer. The data and the statistics come from code. Every number in an answer is checked against the tool result; a mismatch replaces the text with a labelled template.

**Limits we state openly.**
- One grid cell (about 50 km), not a country or city average.
- Reanalysis (MERRA-2 / CERES), not station measurements.
- Linear trends only; no tipping points or cycles such as El Niño.
- The forecast is a statistical extrapolation, not a climate model.
- Some variables are land-only; the app says so.
- The 3D globe layers marked "illustrative" are not data.

## 4. Likely judge questions and short answers

| Question | Answer |
|---|---|
| Why these 12 variables? | They cover heat, water, atmosphere and energy, all available as a monthly series since 1981 for any point. |
| Why both tests? | They rely on different assumptions. Agreement means the result does not depend on one assumption. |
| Why does Manaus say "not significant" when the line goes down? | Monthly values are correlated, so 420 months behave like about 26 independent ones. The test is honest about that. |
| Is the AI making up numbers? | No. It writes the wording; the numbers come from code and are checked against the tool output. |
| Is a 10-year forecast reliable? | We claim skill only where the backtest shows it. Beyond that it is an extrapolation and is labelled as one. |
| Is the result for the whole country? | No. It is for the grid cell at the point you chose. Area averages are the next step. |
| Where do the sources appear? | Under each chapter and under each assistant answer ("Sources" block). |

## 5. Known issues to mention before judges find them

- The forecast horizon is limited to 24 months after the last NASA data month.
- The Florida/state answers use a representative central point, not an area average.
- Some chapter-level text uses the older C unit where it comes from the stored catalog; the API now returns °C.
- The "Stop" button in the assistant is implemented but was not clicked end-to-end.
