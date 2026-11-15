# Forecast evaluation summary (depth=full, 13 holdout origins, 312 forecast-actual pairs per series)
V = model validated (95% block-bootstrap CI of MAE ratio < 1 AND >=3% lower MAE than best baseline); = not distinguishable; W = worse; number = MAE ratio model/baseline.

| Location | Variable | Selected (dev) | Best baseline (dev) | 1-3 | 4-6 | 7-12 | 13-24 | MAE sel @1/12/24 | MAE base @1/12/24 | 95% cov nominal (13-24) |
|---|---|---|---|---|---|---|---|---|---|---|
| Nablus | air_temperature | ets_ana | clim_trend | = 1.11 | = 1.12 | W 1.18 | W 1.19 | 0.911/0.942/0.98 | 0.83/0.829/0.883 | 0.99 |
| Nablus | precipitation | ets_aada | clim_trend | = 1.06 | = 0.99 | = 1.01 | = 1.02 | 0.779/0.553/0.527 | 0.681/0.525/0.472 | 0.85 |
| Nablus | relative_humidity | sarima_101_011 | clim | = 0.92 | W 1.03 | W 1.00 | = 1.00 | 2.437/2.838/2.385 | 3.151/2.826/2.374 | 0.9 |
| Nablus | wind_speed | ets_aada | clim | = 0.99 | = 0.97 | = 1.01 | = 1.00 | 0.119/0.099/0.096 | 0.116/0.103/0.1 | 0.99 |
| Cairo | air_temperature | sarima_011_011 | clim_trend | = 1.09 | = 1.08 | W 1.09 | W 1.13 | 0.964/1.135/1.198 | 0.906/1.062/1.054 | 0.97 |
| Cairo | precipitation | sarima_011_011 | clim_trend | W 1.37 | = 1.03 | W 1.11 | W 1.16 | 0.535/0.587/0.478 | 0.434/0.59/0.43 | 0.83 |
| Cairo | relative_humidity | sarima_101_011 | clim | V 0.91 | = 1.05 | = 0.99 | = 1.01 | 2.498/3.716/3.245 | 3.466/3.601/3.016 | 0.86 |
| Cairo | wind_speed | sarima_101_011 | clim | = 0.96 | = 1.01 | = 1.00 | = 1.01 | 0.149/0.182/0.183 | 0.16/0.173/0.167 | 0.96 |
| Riyadh | air_temperature | ets_ana | clim_trend | = 1.01 | = 1.00 | W 1.05 | W 1.03 | 1.191/0.674/0.783 | 1.2/0.683/0.777 | 0.97 |
| Riyadh | precipitation | sarima_200_100_ct | clim_trend | = 0.96 | = 1.04 | = 1.06 | W 1.05 | 0.259/0.167/0.261 | 0.287/0.186/0.25 | 0.85 |
| Riyadh | relative_humidity | sarima_011_011 | clim_trend | = 0.86 | = 0.99 | = 1.04 | W 1.13 | 4.521/4.312/5.628 | 6.27/5.26/6.058 | 0.94 |
| Riyadh | wind_speed | ets_aada | clim | = 1.00 | = 1.00 | = 1.00 | = 1.00 | 0.198/0.149/0.154 | 0.198/0.149/0.153 | 0.95 |
| London | air_temperature | ets_ana | clim_trend | = 1.02 | W 1.06 | W 1.05 | = 0.98 | 0.905/0.701/0.838 | 0.863/0.618/0.801 | 0.96 |
| London | precipitation | sarima_101_011 | clim | = 1.00 | = 1.00 | = 1.00 | = 1.00 | 0.924/0.597/0.642 | 0.934/0.599/0.644 | 0.89 |
| London | relative_humidity | sarima_101_011 | clim | = 0.95 | = 0.98 | = 1.00 | = 1.00 | 1.586/2.313/2.571 | 1.878/2.338/2.571 | 0.9 |
| London | wind_speed | ets_ana | clim | = 1.00 | = 1.00 | = 1.00 | = 1.00 | 0.307/0.411/0.338 | 0.307/0.411/0.338 | 0.96 |
| Manaus | air_temperature | sarima_101_011 | clim_trend | V 0.53 | = 0.92 | = 0.97 | = 1.00 | 0.688/1.029/1.322 | 1.279/1.094/1.353 | 0.86 |
| Manaus | precipitation | sarima_101_011 | clim_trend | V 0.79 | = 0.89 | = 0.96 | = 1.03 | 1.469/1.271/1.359 | 1.895/1.469/1.311 | 0.94 |
| Manaus | relative_humidity | sarima_101_011 | clim | V 0.62 | = 0.96 | = 1.00 | = 1.00 | 3.598/5.807/7.241 | 6.539/6.043/7.598 | 0.78 |
| Manaus | wind_speed | sarima_101_011 | clim | = 0.96 | = 1.05 | = 1.04 | = 1.04 | 0.027/0.035/0.038 | 0.031/0.033/0.036 | 0.9 |
| Sydney | air_temperature | ets_ana | clim_trend | V 0.77 | = 1.04 | = 1.00 | = 1.02 | 0.388/0.699/0.848 | 0.477/0.754/0.766 | 0.97 |
| Sydney | precipitation | ets_ana | clim_trend | = 1.01 | W 1.03 | = 0.99 | = 1.00 | 1.554/2.29/2.048 | 1.541/2.277/2.054 | 0.96 |
| Sydney | relative_humidity | sarima_101_011 | clim | = 0.96 | = 0.98 | W 1.03 | = 1.02 | 3.098/3.479/3.355 | 3.923/3.616/3.614 | 0.97 |
| Sydney | wind_speed | sarima_101_011 | clim | = 1.00 | = 1.00 | = 1.00 | = 1.00 | 0.234/0.273/0.276 | 0.234/0.273/0.276 | 0.91 |
