# Trend analysis (Mann–Kendall + Sen's slope)

## Where it lives

| Piece | File |
|---|---|
| Statistics (MK, seasonal MK, Hamed–Rao, Sen's slope, Ljung–Box, Kruskal–Wallis) | `app/analysis/stats.py` |
| Series container, quality screening, completeness, annual aggregation | `app/analysis/timeseries.py` |
| Method selection + structured result | `app/analysis/trend.py` |
| Variable / region catalog (what can be served today) | `app/analysis/catalog.py` |
| NASA POWER monthly client | `app/data_sources/power.py` |
| Tool (`analyze_trend`) + Gemini function declaration | `app/tools/trend_tool.py` |
| Gemini function-calling loop + number guard + template fallback | `app/agent/trend_agent.py` |
| HTTP | `POST /api/analysis/trend` (no LLM), `POST /api/analysis/trend/ask` (Gemini), and `POST /api/rag/query` (routes trend questions automatically, `answer_type = tool_analysis`) |

## Flow for "has X risen in place P between Y1 and Y2?"

1. Gemini receives the question + the `analyze_trend` declaration and must call it (it extracts variable, place or lat/lon, years).
   If place or period is missing it asks one clarifying question (no numbers allowed in that text).
2. Backend validates the arguments with Pydantic (variable enum, years ≥ 1981 and not in the future, alpha in (0, 0.5)).
3. Data: NASA POWER monthly point API (the only source verified in the project's reference). Source, endpoint, units, fill value,
   time standard and retrieval time are stored in the result.
4. Quality: `-999` fill values (and any per-reading flags a source supplies) are excluded; missing vs invalid vs fetch-error are
   counted separately; **no gap filling**. A year enters the annual mean only with ≥ 9 valid months (configurable); dropped years are listed.
5. Diagnostics: Kruskal–Wallis (seasonality, with effect size); Ljung–Box on the monthly series **after removing seasonality and
   the Sen trend**; the annual series is re-tested for autocorrelation (annual means are *not* assumed to remove it).
6. Test selection (reason always returned in `aggregation.reason`):
   * seasonal and not autocorrelated → **Seasonal Mann–Kendall** (Hirsch, Slack & Smith 1982), seasonal Sen's slope;
   * otherwise → **annual means + Mann–Kendall**, with the **Hamed & Rao (1998)** variance correction applied from the lags that
     are significant (`variance_correction_factor`; 1.0 means none were);
   * the other variant is returned under `sensitivity` with `agrees_with_primary`.
7. Sen's slope uses the **real time axis** (decimal years), so gaps and dropped years are respected; units are `<unit>/year`; the
   confidence interval uses the same (possibly corrected) variance as the test.
8. Gemini explains the result. Every number in its text is checked against the tool result (tolerant to rounding). If a number is
   unsupported, the mandated non-significance phrase is missing, it says "no change", or Gemini is unavailable, the deterministic
   template built from the tool result is returned instead (`answer_source = "template"`).

## Result fields

`status` (`ok | insufficient_data | unsupported_variable | data_source_unavailable | invalid_request | upstream_error`), `reason_code`,
`variable`, `region` (named regions are *representative points*, not area means), `period_requested`, `period_actual`, `units`,
`source`, `data_quality` (expected/valid/missing/invalid months, invalid reasons, coverage, longest gap, years used/dropped, gap policy,
aggregation rule), `aggregation{chosen, reason}`, `diagnostics`, `test{test_name, n_used, n_unit, S, var_S, z, kendall_tau, p_value, alpha,
significant, tails, variance_correction_factor, direction, sen_slope{value, unit, ci_low, ci_high, ci_level}}`, `interpretation{code,
text_ar, text_en}`, `approx_total_change_over_span`, `sensitivity`, `chart` (Plotly-ready spec), `caveats` (ar/en).

Direction (sign of Sen's slope), magnitude (Sen's slope + CI) and significance (p vs `alpha`, default **0.05**, configurable per request
via `significance_level` or globally via `Settings.trend_alpha`) are separate fields. When not significant the text is
"البيانات الحالية لا تكفي لتأكيد وجود اتجاه" — never "no change". The p-value is never described as a probability of the result being correct.
The test describes the historical trend only; it does not prove a cause and is not a forecast (forecasting stays a separate path).

## Honest limits

* **Land surface temperature is not available.** MOD11C3/MOD11A2 need an Earthdata Login (AppEEARS / CMR downloads) that is not configured.
  The tool returns `data_source_unavailable` and offers `air_temperature` (POWER T2M, MERRA-2 reanalysis) as an *explicit* alternative;
  it never substitutes silently. `TrendRequest`/`run_trend_analysis(series_override=...)` accepts an AppEEARS-built series when that client exists.
* Wildfires and drought return `unsupported_variable` (FIRMS needs a MAP_KEY and event-count aggregation design; no drought index yet).
* POWER values are grid-cell reanalysis values at a point; named regions use one representative point, not a regional average.
* Chart is a JSON spec (Plotly); no image is rendered server-side.
* No multiple-testing correction (single series per call) and no spatial trend maps.
