import re

from app.chunking.metadata import detect_language, extract_metadata
from app.config import GEMINI_DOCS_COLLECTION, KNOWLEDGE_COLLECTION, load_llm_key
from app.ingestion.loaders import clean_web_text, load_all
from app.ingestion.scrub import contains_secret, scrub_secrets


def test_scrub_removes_credentials():
    t = "key AIzaSyA1234567890abcdefghijklmnopqrstu and MAP_KEY=abcdef0123456789abcd and Bearer abcdefghijklmnopqrstuvwx"
    out = scrub_secrets(t)
    assert "AIza" not in out and "abcdef0123456789abcd" not in out and "Bearer abcdef" not in out
    assert out.count("[REDACTED]") == 3
    assert not contains_secret(out)


def test_scrub_keeps_placeholder_names():
    # documentation mentions MAP_KEY as a parameter name, not a value
    assert scrub_secrets("requires MAP_KEY free key") == "requires MAP_KEY free key"


def test_clean_web_text_drops_nav_menu_keeps_content():
    menu = "\n".join(["Home", "Data", "Projects", "Tools", "Worldview", "Giovanni", "Vertex", "News"])
    text = f"Skip to main content\n{menu}\nMODIS Land Surface Temperature\nThis product provides monthly LST at 0.05 degree resolution for the globe."
    out = clean_web_text(text)
    assert "Worldview" not in out and "Skip to main" not in out
    assert "monthly LST at 0.05 degree" in out


def test_metadata_extraction_from_card():
    md = extract_metadata("- **Units:** T2M °C, PRECTOTCORR mm/day. GET /temporal/monthly/point. https://power.larc.nasa.gov/api",
                          heading="S05 — NASA POWER")
    assert md["service_id"] == "S05"
    assert "NASA POWER" in md["dataset_ids"]
    assert "precipitation" in md["variables"] and "air_temperature" in md["variables"]
    assert "°C" in md["units"] and "mm/day" in md["units"]
    assert md["api_endpoints"] == ["GET /temporal/monthly/point"]
    assert md["urls"] == ["https://power.larc.nasa.gov/api"]


def test_variable_tagging_arabic_and_english():
    assert "wildfires" in extract_metadata("نقاط حرائق نشطة FIRMS")["variables"]
    assert "drought" in extract_metadata("SMAP soil moisture")["variables"]
    assert "land_surface_temperature" in extract_metadata("MOD11C3 LST_Day_CMG")["variables"]


def test_language_detection():
    assert detect_language("ما هو المنتج المناسب؟") == "ar"
    assert detect_language("What is the product?") == "en"
    assert detect_language("استخدم NASA POWER لجلب T2M بسرعة وسهولة") in ("mixed", "ar")


def test_real_corpus_loading_and_scope():
    docs = load_all()
    earth, gemini = docs[KNOWLEDGE_COLLECTION], docs[GEMINI_DOCS_COLLECTION]
    ids = {d.source_file for d in earth}
    assert "EarthTrend_Explorer_2026_APIs_Tools_Reference_AR.md" in ids
    assert "Be_An_Earth_System_Trend_Detective_Reference_AR.md" in ids
    assert any(i.startswith("doc_") for i in ids)
    # duplicates (pdf/html renderings) and non-Earth material must not be indexed
    assert not any(i.endswith((".pdf", ".html")) for i in ids)
    assert not {"doc_horizons.txt", "doc_pds.txt", "doc_svs.txt"} & ids
    # Gemini docs live in a separate collection
    assert gemini and all(d.collection == GEMINI_DOCS_COLLECTION for d in gemini)
    assert not any(d.source_file.startswith("google_") for d in earth)


def test_no_secret_reaches_any_document():
    key = load_llm_key()
    for docs in load_all().values():
        for d in docs:
            assert not contains_secret(d.text), d.source_file
            if key:
                assert key.get_secret_value() not in d.text
