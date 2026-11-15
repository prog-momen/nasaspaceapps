# Astro EARTH - NASA Space Apps 2026 submission text

Challenge: **Be an Earth System Trend Detective**. Copy each section into the matching field of the Project Page.
Items in [brackets] must be filled in by the team.

---

## 1. High-Level Summary

Astro EARTH turns anyone into an Earth data detective. People hear that the planet is changing, but very few can check a claim about their own region: there are hundreds of variables, the data is hard to reach, and a line that rises on a chart is not proof.

With Astro EARTH you spin a 3D globe, click any point on Earth, choose one of 12 variables explained in plain language (temperature, rainfall, soil moisture, wind, clouds, sunlight and more), and the tool pulls decades of monthly NASA data for that location. A five-chapter guided investigation then shows what is changing, where, how much (rate per decade and total change), and whether the change is statistically significant, using a regression t-test corrected for autocorrelation, the Mann-Kendall test, Sen's slope and a 95% confidence interval. You can compare two regions side by side, look ahead with a forecast, and ask an AI assistant in English or Arabic. The assistant is built so that it cannot invent numbers: every figure in its answer must come from a real data tool, and it cites its sources.

It matters because it replaces "I heard it is changing" with "I tested it myself", for students, teachers and the curious public.

## 2. Project Demo

7-slide deck: [paste the public link to the deck, or upload the exported PDF/PPTX]

## 3. Final Project Link

- Web app and backend: https://github.com/prog-momen/nasaspaceapps
- AI assistant service: https://github.com/husambara/nasa-challenge-API
- [Live demo URL, if deployed]

## 4. Project Details

**What it does**

1. **Choose where.** Interactive 3D Earth: click any point (0.5 degree grid cell), search for a place, or start from five ready-made investigations (Arctic warming in Svalbard, Sahel rainfall in Niamey, Amazon soil moisture in Manaus, summer heat in Amman, sunlight over Lhasa).
2. **Choose what.** 12 variables, each with a simple definition, why it matters and what "higher" means.
3. **See the record.** Monthly time series from 1981 onward, the seasonal cycle, the anomalies after the seasonal cycle is removed, and yearly averages. Every chart explains what it shows, why it matters and what to conclude.
4. **Get the verdict.** Rate of change per year and per decade, total change, and a verdict: *significant*, *weak evidence* or *not significant*. A "Scientist View" shows the full statistics.
5. **Go further.** Compare two regions for the same variable; forecast ahead with a prediction interval and an honest accuracy check; ask the AI assistant.

**How it works**

- *Data:* NASA POWER monthly point API (MERRA-2 and CERES), fetched live for the selected coordinates and cached.
- *Trend method:* the seasonal cycle is removed with a monthly climatology. A least-squares trend is fitted to the anomalies and tested with a t-test whose sample size is reduced for lag-1 autocorrelation, so significance is not overstated. A tie-corrected Mann-Kendall test and Sen's slope run on annual mean anomalies. The trend is called significant only when both tests agree at alpha = 0.05.
- *Forecast:* linear trend plus seasonal cycle with a 95% prediction interval, checked by a hold-out backtest against a seasonal baseline. The AI service adds a statistical monthly forecast up to 24 months (SARIMA / ETS against named baselines with rolling-origin backtests).
- *AI assistant:* a language model interprets the question into a structured request; ordinary code validates it, runs exactly one data tool and returns the result; the model words the answer and every number in it is checked against the tool output. If a number does not match, the model's text is discarded and a deterministic template is shown. Documentation questions are answered from an index of NASA documentation with citations.

**Example results produced by the app (1990-2024)**

| Place | Variable | Result |
|---|---|---|
| Svalbard | Air temperature | +0.73 C per decade, significant |
| Amman | Maximum air temperature | +0.58 C per decade, significant |
| Niamey (Sahel) | Precipitation | +0.11 mm/day per decade (+26%), significant |
| Manaus (Amazon) | Root zone soil wetness | downward slope, **not significant**: 420 monthly values behave like about 26 independent ones |

**Tools and technologies**

Next.js 16, React 19, TypeScript, Tailwind CSS, Three.js (3D globe), Supabase/PostgreSQL (cache); Python, FastAPI, NumPy, SciPy, pandas, statsmodels, Qdrant (local vector index), sentence-transformers (multilingual-e5-small), Anthropic Claude Haiku.

**Goals**

Make trend detection understandable to high-school and university students and the public; never present a slope without a significance test; be honest about limits (one grid cell rather than a country average, reanalysis rather than station data, linear trends only).

**Benefits and next steps**

Classroom use, checking local claims, Arabic-language access. Next: area averages for countries and basins, more missions as trend variables (GPM, MODIS vegetation, GLDAS), shareable investigations.

**Forecast with stated confidence.** The forecast is counted from today. Months between the last NASA data month and today are forecast too and marked as missing months. Each forecast shows three confidence zones: *Tested* (up to the length of the backtest, about 5 years), *Extrapolation* (to 10 years, not validated) and *Computation only* (beyond 10 years, mathematics without evidence of skill).

**Sources on every result.** Each dashboard chapter and each assistant answer shows two lines under it: *Relies on* (the datasets and methods the result is built on) and *Used in this result* (the place, the grid cell, the period, the records and the citations this particular result used).

## 5. Use of Artificial Intelligence

- **Inside the product:** Anthropic Claude Haiku is used for two language tasks only: understanding the user's question and wording the explanation. It never produces data. All numbers come from NASA and partner data tools, and each AI-worded answer is automatically checked against the tool output; answers that fail the check are replaced by a clearly labelled template. Embeddings for the documentation search run locally (multilingual-e5-small). AI-generated answers are labelled in the interface with the model name.
- **During development:** AI coding assistants (Claude) were used to help write and review code, documentation and the presentation. [Add any other AI tools the team used, e.g. for the logo or images, and state that no NASA branding was generated.]

## 6. Use of NASA Data

- **NASA POWER** (Prediction Of Worldwide Energy Resources), monthly point API: the core of the product. Variables from **MERRA-2** (air temperature, max/min temperature, surface temperature, precipitation corrected with GPCP, evaporation, root zone soil wetness, humidity, wind, pressure) and **CERES SYN1deg** (cloud amount, surface solar radiation). Every trend, comparison and forecast is computed from these time series.
- **NASA FIRMS**: active-fire detections (assistant tool).
- **NASA Earthdata**: CMR dataset search, AppEEARS point sampling of MODIS MOD11A2 land surface temperature, GIBS imagery (assistant tools).
- The challenge resources (Giovanni, the statistical testing references) guided the choice of methods.

## 7. Space Agency Partner and Other Data

- Copernicus Data Space Ecosystem: Sentinel-2 scene discovery and NDVI statistics. Contains modified Copernicus Sentinel data.
- Copernicus Emergency Management Service (CEMS) seasonal fire danger forecast via EWDS.
- NIFC wildland fire potential outlooks, GWIS and USGS fire danger products.
- Open-Meteo weather forecast and reanalysis (CC BY 4.0, "Weather data by Open-Meteo.com").

## 8. References

**Data**
- NASA POWER: https://power.larc.nasa.gov/ (API docs: https://power.larc.nasa.gov/docs/services/api/temporal/monthly/)
- MERRA-2: https://gmao.gsfc.nasa.gov/reanalysis/MERRA-2/
- CERES: https://ceres.larc.nasa.gov/
- NASA FIRMS: https://firms.modaps.eosdis.nasa.gov/
- NASA Earthdata (CMR, AppEEARS, GIBS): https://www.earthdata.nasa.gov/
- Giovanni: https://giovanni.gsfc.nasa.gov/
- Copernicus Data Space: https://dataspace.copernicus.eu/
- Copernicus EWDS (CEMS fire seasonal): https://ewds.climate.copernicus.eu/
- NIFC Predictive Services: https://www.nifc.gov/
- GWIS: https://gwis.jrc.ec.europa.eu/
- Open-Meteo: https://open-meteo.com/
- BigDataCloud reverse geocoding: https://www.bigdatacloud.com/
- Country list: https://github.com/mledoze/countries

**Methods**
- Mann, H. B. (1945). Nonparametric tests against trend. Econometrica 13.
- Kendall, M. G. (1975). Rank Correlation Methods.
- Sen, P. K. (1968). Estimates of the regression coefficient based on Kendall's tau. JASA 63.
- Hamed, K. H. and Rao, A. R. (1998). A modified Mann-Kendall trend test for autocorrelated data. J. Hydrology 204.
- Challenge resources: "Statistical test methods to detect trends in time series data" and "A Comprehensive Guide to Statistical Significance".

**Software (open source)**
Next.js, React, Three.js, Tailwind CSS, Supabase, Zod, FastAPI, NumPy, SciPy, pandas, statsmodels, Qdrant, sentence-transformers, httpx, shapely, netCDF4.

**AI**
Anthropic Claude Haiku (in-product assistant); Claude (development assistance).

---

## Team

Astro Crash - [members and roles] - [local event]
