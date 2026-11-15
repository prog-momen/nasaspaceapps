# Monthly statistical forecasting (1-24 months)

Code: `app/forecast/{series,engine,evaluation,service}.py` · tool `forecast_monthly` · references `docs/research/forecast_references.json` ·
evidence `evidence/forecast_eval/` (24 series, produced by `scripts/run_forecast_evaluation.py`) · tests `tests/test_forecast_engine.py`.

**What it is:** a statistical forecast of MONTHLY means (T2M, precipitation rate, RH2M, WS2M) from NASA POWER history, validated by chronological
rolling-origin backtests. **What it is not:** an operational weather forecast (Open-Meteo, <= 16 days), a trend test (Mann-Kendall/Sen), or a climate projection.

* Candidates: seasonal naive, monthly climatology, climatology + linear trend (baselines, real names); SARIMA x3, ETS x2. No LSTM/hybrid (data volume and validation do not justify it; paper D not available).
* Selection on development origins only; the final holdout (13 origins in the full evaluation, 5 in interactive mode) is judged once.
* Skill status per horizon group: `validated` only if the 95% moving-block-bootstrap CI of MAE(model)/MAE(best baseline) is below 1 AND the gain is >= 3%.
  Otherwise the baseline is shown under its own name ("additional predictive skill has not been established").
* Errors: MAE/RMSE/bias/MASE in physical units; WAPE only for non-negative variables; no MAPE on Celsius.
* Intervals: models' nominal 80/95% intervals; observed holdout coverage is shown beside them. Empirical recalibration from development errors was tested and did NOT transfer to the holdout
  (mean 95% coverage 0.86, min 0.33 vs nominal 0.92, min 0.78), so it is not used.
* Cutoff: forecasts start after the last complete valid data month; the gap to today is disclosed.
* Papers (A, B, C full texts, indexed for methodology) are method references only, never evidence for a forecast value.
