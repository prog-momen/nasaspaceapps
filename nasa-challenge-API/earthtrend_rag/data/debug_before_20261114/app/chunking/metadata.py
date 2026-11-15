"""Heuristic metadata extraction from chunk text. Fields that cannot be found stay absent."""
from __future__ import annotations

import re

# Product identifiers that appear in the project's own reference file.
DATASET_PATTERNS = [
    r"MOD11A2(?:\.0?61)?", r"MOD11C3(?:\.0?61)?", r"MOD13A3(?:\.0?61)?",
    r"GPM_3IMERGM(?:\s*/\s*07)?", r"IMERG(?:\s+V07)?", r"GLDAS_NOAH025_M(?:\s*/?\s*2\.1)?",
    r"M2TMNXSLV(?:\s*/?\s*5\.12\.4)?", r"M2TMNXFLX", r"SPL3SMP(?:\s*(?:v|/|\.)\s*0?9)?",
    r"ECO_L2T_LSTE(?:[./ ]+0?02)?", r"HLS[LS]30(?:\.0?20)?", r"SRTMGL1(?:\.0?03)?",
    r"GEDI02_A", r"SWOT_L2_HR_RiverSP_D", r"NEX-GDDP-CMIP6", r"AIRS3STM", r"OMNO2d",
    r"NASA POWER", r"FIRMS", r"VIIRS", r"MODIS",
]
_DATASET_RE = re.compile("|".join(f"(?:{p})" for p in DATASET_PATTERNS))

# keyword -> project variable
VARIABLE_KEYWORDS = {
    "land_surface_temperature": [r"\bLST\b", r"land surface temperature", r"درجة حرارة سطح", r"حرارة السطح", r"MOD11", r"LST_Day", r"ECO_L2T_LSTE"],
    "wildfires": [r"wildfire", r"FIRMS", r"hot ?spot", r"fire detection", r"FRP", r"حرائق", r"حريق"],
    "drought": [r"drought", r"soil[_ ]moisture", r"SPL3SMP", r"SMAP", r"NDVI", r"جفاف", r"رطوبة التربة"],
    "precipitation": [r"precipitation", r"\bIMERG\b", r"PRECTOTCORR", r"Rainf", r"rainfall", r"هطول", r"أمطار"],
    "air_temperature": [r"\bT2M\b", r"air temperature", r"حرارة الهواء"],
}

UNIT_PATTERNS = [r"°C", r"\bdegC\b", r"\bK\b(?=\s|[,;)،.])", r"mm/day", r"mm/hr", r"mm/month", r"m³/m³",
                 r"kg m-?⁻?2 s-?⁻?1", r"\bMW\b", r"m/m", r"molecules/cm²"]
_UNIT_RE = re.compile("|".join(f"(?:{p})" for p in UNIT_PATTERNS))

_URL_RE = re.compile(r"https?://[^\s)\]>\"'`،]+")
_ENDPOINT_RE = re.compile(r"\b(GET|POST|PUT)\s+(/[A-Za-z0-9_\-./{}:?=&<>]+|https?://[^\s)`]+)")
_SERVICE_RE = re.compile(r"\b(S\d{2})\b")
_YEAR_RE = re.compile(r"(?:from|since|منذ|من)\s+(19[89]\d|20[0-3]\d)")
_ARABIC_RE = re.compile(r"[؀-ۿ]")


def detect_language(text: str) -> str:
    letters = re.findall(r"[A-Za-z؀-ۿ]", text)
    if not letters:
        return "en"
    ar = sum(1 for c in letters if _ARABIC_RE.match(c))
    r = ar / len(letters)
    return "ar" if r > 0.5 else ("mixed" if r > 0.15 else "en")


def _uniq(seq):
    seen, out = set(), []
    for s in seq:
        s = s.strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def extract_metadata(text: str, heading: str = "") -> dict:
    hay = f"{heading}\n{text}"
    md: dict = {"language": detect_language(text)}
    ds = _uniq(m.group(0) for m in _DATASET_RE.finditer(hay))
    if ds:
        md["dataset_ids"] = ds[:8]
    vars_ = [v for v, pats in VARIABLE_KEYWORDS.items() if any(re.search(p, hay, re.I) for p in pats)]
    if vars_:
        md["variables"] = vars_
    units = _uniq(m.group(0) for m in _UNIT_RE.finditer(text))
    if units:
        md["units"] = units[:6]
    urls = _uniq(u.rstrip(".,;") for u in _URL_RE.findall(text))
    if urls:
        md["urls"] = urls[:5]
    eps = _uniq(f"{m.group(1)} {m.group(2).rstrip('.,;)')}" for m in _ENDPOINT_RE.finditer(text))
    if eps:
        md["api_endpoints"] = eps[:6]
    m = _SERVICE_RE.search(heading)
    if m:
        md["service_id"] = m.group(1)
    yrs = _YEAR_RE.findall(text)
    if yrs:
        md["temporal_start_hint"] = min(yrs)
    if re.search(r"\bglobal\b|عالمي", hay, re.I):
        md["geographic_coverage_hint"] = "global"
    return md
