"""Conservative fallback for one explicit variable, catalog place and two years."""
import re
from app.analysis.catalog import REGIONS
from app.retrieval.intent import classify

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_VARIABLES = {
    "air_temperature": r"air temperature|\bt2m\b|حرارة الهواء|air_temperature",
    "land_surface_temperature": r"land surface temperature|\blst\b|حرارة سطح الأرض|land_surface_temperature",
    "precipitation": r"precipitation|rainfall|هطول|أمطار|الأمطار|prectotcorr",
    "wildfires": r"wildfires?|حرائق",
    "drought": r"drought|جفاف",
}


def explicit_trend_args(question: str) -> dict | None:
    q = question.translate(_DIGITS).lower()
    if classify(q).kind != "needs_analysis" or re.search(r"latitude|longitude|[،,]\s*-?\d|\d\.\d|alpha|aggregation|دلالة|سنوي|موسمي", q):
        return None
    years = re.findall(r"(?<!\d)(?:19\d{2}|20\d{2})(?!\d)", q)
    variables = [v for v, pattern in _VARIABLES.items() if re.search(pattern, q)]
    regions = [name for name, r in REGIONS.items() if any(re.search(r"(?<!\w)[وبلكف]?" + re.escape(a) + r"(?!\w)", q) for a in r["aliases"])]
    if len(years) != 2 or len(variables) != 1 or len(regions) != 1:
        return None
    if len(re.findall(r"\d+", q)) != 2:
        return None
    return {"variable": variables[0], "region": regions[0], "start_year": int(years[0]), "end_year": int(years[1])}
