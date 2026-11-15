# Evidence (redacted; no secrets) -- 2026-11-14

| File | What it proves | Re-run |
|---|---|---|
| `power_T2M_31.8_35.2_1981_2025/raw_response.json` + `request_metadata.json` | ONE direct NASA POWER response (params, UTC time, status, sha256) used for the comparison | `python scripts/compare_power_reference.py capture` (new request) |
| `power_T2M_31.8_35.2_1981_2025/comparison_result.json` | independent reference (numpy/scipy/pymannkendall) vs project on the same bytes; weighting; historical figures | `python scripts/compare_power_reference.py compare` (offline) |
| `power_T2M_31.8_35.2_1981_2025/live_project_fetch.json` | project's own client, cache bypassed, 1 request: 540/540 months identical to the direct capture | `... live-project` (1 request) |
| `prior_run_reconstruction.txt` | how the earlier p=0.139 / Sen 0.038 result is reconstructed from stored evidence | `python scripts/reconstruct_prior_run.py` |
| `gemini_docs_check.json` | configured models vs current official docs + account model list (no quota spent) | `python scripts/verify_gemini_docs.py` |
| `live_gemini_final.json` | the declared small live Gemini check (requests, tool executions, answer source) | `python scripts/live_gemini_final_check.py` (spends <= 3 requests) |

The user's attached reference script was NOT present in the workspace, so "reference" above is an independent re-implementation
(scipy.stats.linregress / theilslopes, pymannkendall.original_test), not that script.
