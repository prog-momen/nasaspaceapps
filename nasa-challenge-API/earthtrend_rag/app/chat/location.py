"""Place resolution and bounding boxes. Local gazetteer first (fast, deterministic), Open-Meteo geocoding second (cached)."""
from __future__ import annotations

import re

from app.providers.base import haversine_km, validate_bbox, validate_point

# name -> (lat, lon, display); aliases are matched case-insensitively with optional Arabic prefixes (و/ب/ل/ف/ك/ال)
GAZETTEER = {
    "cairo": (30.0444, 31.2357, "Cairo, Egypt", ["cairo", "القاهرة"]),
    "alexandria": (31.2001, 29.9187, "Alexandria, Egypt", ["alexandria", "الإسكندرية", "الاسكندرية"]),
    "riyadh": (24.7136, 46.6753, "Riyadh, Saudi Arabia", ["riyadh", "الرياض"]),
    "jeddah": (21.4858, 39.1925, "Jeddah, Saudi Arabia", ["jeddah", "جدة"]),
    "amman": (31.9454, 35.9284, "Amman, Jordan", ["amman", "عمان"]),
    "jerusalem": (31.7683, 35.2137, "Jerusalem", ["jerusalem", "القدس"]),
    "nablus": (32.2211, 35.2544, "Nablus, Palestine", ["nablus", "نابلس"]),
    "ramallah": (31.9038, 35.2034, "Ramallah, Palestine", ["ramallah", "رام الله"]),
    "gaza": (31.5017, 34.4668, "Gaza", ["gaza", "غزة"]),
    "hebron": (31.5326, 35.0998, "Hebron, Palestine", ["hebron", "الخليل"]),
    "beirut": (33.8938, 35.5018, "Beirut, Lebanon", ["beirut", "بيروت"]),
    "damascus": (33.5138, 36.2765, "Damascus, Syria", ["damascus", "دمشق"]),
    "baghdad": (33.3152, 44.3661, "Baghdad, Iraq", ["baghdad", "بغداد"]),
    "dubai": (25.2048, 55.2708, "Dubai, UAE", ["dubai", "دبي"]),
    "doha": (25.2854, 51.531, "Doha, Qatar", ["doha", "الدوحة"]),
    "tunis": (36.8065, 10.1815, "Tunis, Tunisia", ["tunis", "تونس"]),
    "algiers": (36.7538, 3.0588, "Algiers, Algeria", ["algiers", "الجزائر"]),
    "rabat": (34.0209, -6.8416, "Rabat, Morocco", ["rabat", "الرباط"]),
    "khartoum": (15.5007, 32.5599, "Khartoum, Sudan", ["khartoum", "الخرطوم"]),
    "istanbul": (41.0082, 28.9784, "Istanbul, Turkey", ["istanbul", "إسطنبول", "اسطنبول"]),
    "athens": (37.9838, 23.7275, "Athens, Greece", ["athens", "أثينا"]),
    "london": (51.5074, -0.1278, "London, UK", ["london", "لندن"]),
    "paris": (48.8566, 2.3522, "Paris, France", ["paris", "باريس"]),
    "new york": (40.7128, -74.006, "New York, USA", ["new york", "نيويورك"]),
    "california": (36.7783, -119.4179, "California (central point), USA", ["california", "كاليفورنيا"]),
    "texas": (31.0, -100.0, "Texas (central point), USA", ["texas", "تكساس"]),
    "florida": (27.99, -81.76, "Florida (central point), USA", ["florida", "فلوريدا"]),
    "boise": (43.615, -116.2023, "Boise, Idaho, USA", ["boise", "بويزي"]),
    "amazon": (-3.4653, -62.2159, "Amazon basin (representative point)", ["amazon", "الأمازون", "الامازون"]),
    "sydney": (-33.8688, 151.2093, "Sydney, Australia", ["sydney", "سيدني"]),
}
_PREFIX = r"(?:(?<=\s)|^|(?<=[(،,]))[وبلكف]?(?:ال)?"


def find_known_place(text: str) -> dict | None:
    t = text.lower()
    best = None
    for key, (lat, lon, display, aliases) in GAZETTEER.items():
        for a in aliases:
            m = re.search(r"(?<![\wء-ي])[وبلكف]?" + re.escape(a) + r"(?![\wء-ي])", t)
            if m and (best is None or len(a) > best[0]):
                best = (len(a), {"name": display, "latitude": lat, "longitude": lon, "source": "gazetteer", "key": key})
    return best[1] if best else None


_COORD = re.compile(r"(-?\d{1,2}(?:\.\d+)?)\s*[,،;]\s*(-?\d{1,3}(?:\.\d+)?)")
_EN_IN = re.compile(r"\b(?:in|for|at|near|around|over)\s+([A-Z][A-Za-zÀ-ſ]+(?:\s+[A-Z][A-Za-zÀ-ſ]+){0,2})")
_AR_IN = re.compile(r"(?<![ء-ي])(?:في|ب|حول|قرب|منطقة)\s*([ء-ي]{3,}(?:\s[ء-ي]{3,}){0,1})")
_STOP_AR = {"آخر", "اخر", "الأيام", "الايام", "الأسبوع", "الاسبوع", "الشهر", "العام", "السنة", "هذا", "هذه", "أمس", "اليوم", "غدا", "غداً", "عام", "سنة", "منطقة", "الفترة"}


def extract_coords(text: str) -> tuple[float, float] | None:
    for m in _COORD.finditer(text):
        lat, lon = float(m.group(1)), float(m.group(2))
        if validate_point(lat, lon) is None and not re.fullmatch(r"(19|20)\d\d", m.group(1)):
            return lat, lon
    return None


def candidate_place_names(text: str) -> list[str]:
    out = [m.group(1).strip() for m in _EN_IN.finditer(text)]
    for m in _AR_IN.finditer(text):
        name = m.group(1).strip()
        if name.split()[0] not in _STOP_AR:
            out.append(name)
    return out


def bbox_around(lat: float, lon: float, half_deg: float = 0.5) -> list[float]:
    return [round(max(-180, lon - half_deg), 4), round(max(-90, lat - half_deg), 4), round(min(180, lon + half_deg), 4), round(min(90, lat + half_deg), 4)]


def bbox_center(b: list[float]) -> tuple[float, float]:
    return (b[1] + b[3]) / 2, (b[0] + b[2]) / 2


def far_apart(a: dict, b: dict, km: float = 50.0) -> bool:
    return haversine_km(a["latitude"], a["longitude"], b["latitude"], b["longitude"]) > km


def _disp(p: dict) -> str:
    return ", ".join(x for x in (p.get("name"), p.get("admin1"), p.get("country")) if x)


def geocode_name(name: str, language: str = "ar") -> dict | None:
    """Open-Meteo geocoding (cached 24 h by http_json). Returns the best match plus `ambiguous`: other comparable places with the SAME name
    in a different country/region. The caller must ask the user instead of guessing when `ambiguous` is non-empty."""
    from app.providers import open_meteo
    r = open_meteo.geocode(name, language, count=5)
    if r["status"] != "ok":
        return None
    places = r["data"]["places"]
    p = places[0]
    pop = p.get("population") or 0
    amb = [q for q in places[1:] if (q.get("name") or "").lower() == (p.get("name") or "").lower() and (q.get("country"), q.get("admin1")) != (p.get("country"), p.get("admin1"))
           and ((q.get("population") or 0) >= 0.3 * pop if pop else True)]
    return {"name": _disp(p), "latitude": p["latitude"], "longitude": p["longitude"], "source": "open-meteo geocoding", "timezone": p.get("timezone"),
            "ambiguous": [_disp(q) for q in amb] and [_disp(p)] + [_disp(q) for q in amb][:3] or []}
