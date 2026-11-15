"""Explicit, hand-maintained source registry.

Only sources listed here are ingested (corpus scope decision). Metadata here is
taken from the project's own reference file / the crawl sidecar JSON; nothing is
invented: fields not known are left out.
"""
from __future__ import annotations

from app.config import GEMINI_DOCS_COLLECTION, KNOWLEDGE_COLLECTION, REPO_ROOT, RESEARCH_DIR

K = KNOWLEDGE_COLLECTION
G = GEMINI_DOCS_COLLECTION

# variable tags use the project's four variables plus supporting ones
LST, FIRE, DROUGHT, PRECIP = "land_surface_temperature", "wildfires", "drought", "precipitation"

CORE_FILES = [
    REPO_ROOT / "EarthTrend_Explorer_2026_APIs_Tools_Reference_AR.md",
    REPO_ROOT / "Be_An_Earth_System_Trend_Detective_Reference_AR.md",
]

# crawled NASA / science docs: id -> metadata. Text is research/<id>.txt, sidecar research/<id>.json
CRAWLED_DOCS: dict[str, dict] = {
    "doc_appeears":   {"dataset": "AppEEARS API", "variables": [LST], "provider": "NASA LP DAAC"},
    "doc_arima":      {"dataset": "statsmodels ARIMA", "variables": [], "provider": "statsmodels"},
    "doc_sarimax":    {"dataset": "statsmodels SARIMAX", "variables": [], "provider": "statsmodels"},
    "doc_mk":         {"dataset": "pyMannKendall", "variables": [], "provider": "pyMannKendall"},
    "doc_asf":        {"dataset": "ASF Search API", "variables": [], "provider": "ASF DAAC"},
    "doc_earthaccess": {"dataset": "earthaccess", "variables": [], "provider": "NASA Earthdata"},
    "doc_ecostress":  {"dataset": "ECO_L2T_LSTE.002", "variables": [LST], "provider": "NASA LP DAAC"},
    "doc_firms":      {"dataset": "FIRMS API", "variables": [FIRE], "provider": "NASA LANCE FIRMS"},
    "doc_gic_notebook": {"dataset": "GES DISC Giovanni-in-the-Cloud tutorial", "variables": [], "provider": "NASA GES DISC"},
    "doc_gldas":      {"dataset": "GLDAS_NOAH025_M.2.1", "variables": [PRECIP, DROUGHT], "provider": "NASA GES DISC"},
    "doc_harmony":    {"dataset": "Harmony API", "variables": [], "provider": "NASA Earthdata"},
    "doc_hls":        {"dataset": "HLSL30/HLSS30", "variables": [], "provider": "NASA HLS"},
    "doc_hydrocron_examples": {"dataset": "Hydrocron (SWOT)", "variables": [], "provider": "NASA PO.DAAC"},
    "doc_hydrocron_query":    {"dataset": "Hydrocron (SWOT)", "variables": [], "provider": "NASA PO.DAAC"},
    "doc_imerg":      {"dataset": "GPM IMERG V07", "variables": [PRECIP], "provider": "NASA GPM / GES DISC"},
    "doc_merra":      {"dataset": "MERRA-2 M2TMNXSLV.5.12.4", "variables": [], "provider": "NASA GMAO"},
    "doc_mod11":      {"dataset": "MOD11C3.061", "variables": [LST], "provider": "NASA LP DAAC"},
    "doc_mod13":      {"dataset": "MOD13A3.061", "variables": [DROUGHT], "provider": "NASA LP DAAC"},
    "doc_nex":        {"dataset": "NEX-GDDP-CMIP6", "variables": [], "provider": "NASA NCCS"},
    "doc_noaa":       {"dataset": "NOAA CDO v2", "variables": [], "provider": "NOAA NCEI"},
    "doc_ntrs":       {"dataset": "SeaWiFS time-series paper (NTRS 20090042747)", "variables": [], "provider": "NASA NTRS"},
    "doc_smap":       {"dataset": "SPL3SMP.009", "variables": [DROUGHT], "provider": "NASA SMAP / NSIDC"},
    "doc_rasterio":   {"dataset": "rasterio reproject", "variables": [], "provider": "rasterio"},
    "doc_xarray":     {"dataset": "xarray IO guide", "variables": [], "provider": "xarray"},
    # challenge pages for Earth-science challenges only
    "challenge_earth-system-trend-detective":  {"dataset": "Challenge: Earth System Trend Detective", "variables": [], "provider": "NASA Space Apps 2026"},
    "challenge_modis-and-viirs-hot-spots":     {"dataset": "Challenge: MODIS and VIIRS Hot Spots", "variables": [FIRE], "provider": "NASA Space Apps 2026"},
    "challenge_the-earth-information-jukebox": {"dataset": "Challenge: Earth Information Jukebox", "variables": [], "provider": "NASA Space Apps 2026"},
    "challenge_adapting-farms-with-nasa-data": {"dataset": "Challenge: Adapting Farms with NASA Data", "variables": [DROUGHT, PRECIP], "provider": "NASA Space Apps 2026"},
}

# Gemini platform docs: kept in a separate collection
GEMINI_DOCS: dict[str, dict] = {
    "google_models":       {"dataset": "Gemini models", "provider": "Google"},
    "google_flash":        {"dataset": "Gemini Flash", "provider": "Google"},
    "google_pricing":      {"dataset": "Gemini API pricing", "provider": "Google"},
    "google_limits":       {"dataset": "Gemini rate limits", "provider": "Google"},
    "google_functions":    {"dataset": "Gemini function calling", "provider": "Google"},
    "google_key":          {"dataset": "Gemini API key", "provider": "Google"},
    "google_deprecations": {"dataset": "Gemini deprecations", "provider": "Google"},
    "google_terms":        {"dataset": "Gemini API terms", "provider": "Google"},
}

MIN_CRAWLED_CHARS = 300   # skip empty / error pages
RESEARCH = RESEARCH_DIR
