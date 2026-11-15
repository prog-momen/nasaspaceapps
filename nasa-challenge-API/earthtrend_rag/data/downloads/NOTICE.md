# EWDS data files used by the demo

Contains modified Copernicus Emergency Management Service information (ECMWF / JRC).
Dataset: *Seasonal forecast of fire danger indices from the Copernicus Emergency Management Service* (`cems-fire-seasonal`), DOI 10.24381/cds.b9c753f1, licence CC-BY-4.0.
Variable `fire_weather_index` (netCDF `fwinx`), release version 5. Downloaded 2026-11-15 from https://ewds.climate.copernicus.eu/ (subset by area and lead time only; values unchanged).

| Place | Current forecast (start 2026-10-01, valid 2026-12-01..31, 51 members) | Reference (start month October, years 1981-2016, 25 members, same leads) |
|---|---|---|
| Nablus | `ewds_892debc5242a.nc` | `ewds_ref_6f4dcb2b5f0d.nc` |
| Gaza | `ewds_70a98f19e839.nc` | `ewds_ref_b2542c0c7128.nc` |
| Amman | `ewds_d7878496d78d.nc` | `ewds_ref_aaeff6199878.nc` |

File names are hashes of the exact request body, so the application finds them as a cache hit only for the same place, window and area rules. Everything else in this folder is git-ignored.
