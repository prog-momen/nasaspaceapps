"""Source loaders. Each source format gets its own strategy (not one-size-fits-all)."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from urllib.parse import urlparse

from app.config import GEMINI_DOCS_COLLECTION, KNOWLEDGE_COLLECTION
from app.ingestion import registry as R
from app.ingestion.scrub import scrub_secrets
from app.models import Document

log = logging.getLogger(__name__)

_BOILERPLATE = re.compile(
    r"(?i)^(skip to main content|see the alert|home|menu|search|log ?in|sign ?in|share|cookie|accept|privacy policy|"
    r"contact us|follow us|back to top|earthdata forum is down.*|suomi npp is no longer.*|.*third[- ]party site.*)$"
)


def clean_web_text(text: str) -> str:
    """Remove navigation boilerplate from crawled page text.

    Heuristic: runs of >=6 consecutive short, unpunctuated lines are menus and are dropped.
    Headings (short lines followed by a long line) are kept.
    """
    lines = [l.rstrip() for l in text.replace("\r", "").split("\n")]
    out: list[str] = []
    run: list[str] = []

    def is_short(l: str) -> bool:
        s = l.strip()
        return 0 < len(s) <= 40 and not re.search(r"[.:;,!?()=/{}\[\]]", s)

    def flush(next_line: str | None):
        nonlocal run
        if len(run) >= 6:
            keep = [run[-1]] if next_line and len(next_line.strip()) > 60 else []  # last short line = heading
            out.extend(keep)
        else:
            out.extend(run)
        run = []

    for i, l in enumerate(lines):
        if _BOILERPLATE.match(l.strip()):
            continue
        if is_short(l):
            run.append(l)
            continue
        flush(l)
        out.append(l)
    flush(None)
    txt = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", txt).strip()


def load_core_markdown() -> list[Document]:
    docs = []
    for path in R.CORE_FILES:
        if not path.is_file():
            log.warning("core file missing: %s", path.name)
            continue
        raw = path.read_text(encoding="utf-8")
        title = next((l[2:].strip() for l in raw.splitlines() if l.startswith("# ")), path.stem)
        docs.append(Document(
            source_id=f"core:{path.name}", source_file=path.name, source_type="markdown",
            title=title, text=scrub_secrets(raw), collection=KNOWLEDGE_COLLECTION,
            meta={"source_role": "core_reference", "language_hint": "ar"},
        ))
    return docs


def _load_crawled(doc_id: str, meta: dict, collection: str, role: str) -> Document | None:
    txt = R.RESEARCH / f"{doc_id}.txt"
    side = R.RESEARCH / f"{doc_id}.json"
    if not txt.is_file() or not side.is_file():
        log.warning("crawled doc missing: %s", doc_id)
        return None
    info = json.loads(side.read_text(encoding="utf-8"))
    if str(info.get("status")) != "200":
        return None
    ctype = (info.get("content_type") or "").split(";")[0]
    if ctype not in ("text/html", "text/plain", "text/markdown"):
        return None
    raw = txt.read_text(encoding="utf-8", errors="replace")
    text = scrub_secrets(clean_web_text(raw))
    if len(text) < R.MIN_CRAWLED_CHARS:
        log.info("skip %s: too little text after cleaning (%d chars)", doc_id, len(text))
        return None
    title = next((l.strip() for l in text.splitlines() if l.strip()), doc_id)
    return Document(
        source_id=f"crawl:{doc_id}", source_file=f"{doc_id}.txt", source_type="crawled_web_text",
        title=title[:160], text=text, collection=collection,
        meta={**meta, "source_role": role, "original_url": info.get("url"),
              "retrieved_at": info.get("checked_at"), "language_hint": "en"},
    )


def load_crawled_science_docs() -> list[Document]:
    docs = []
    for doc_id, meta in R.CRAWLED_DOCS.items():
        if doc_id.startswith("challenge_"):
            continue  # challenge pages are mostly site chrome; the core reference summarises them
        d = _load_crawled(doc_id, meta, KNOWLEDGE_COLLECTION, "nasa_documentation")
        if d:
            docs.append(d)
    return docs


EARTH_CHALLENGES = {2, 6, 8, 14}  # trend detective, farms, hot spots, earth information jukebox


def load_challenge_resources(min_clean_chars: int = 1500) -> list[Document]:
    """Resource pages linked from Earth-science challenges, quality-gated."""
    inv_path = R.RESEARCH / "inventory_normalized.json"
    if not inv_path.is_file():
        return []
    inv = json.loads(inv_path.read_text(encoding="utf-8"))
    docs = []
    for item in inv:
        if not EARTH_CHALLENGES.intersection(item.get("challenges", [])):
            continue
        rid = f"resource_{item['id']}"
        meta = {"dataset": (item.get("labels") or [rid])[0],
                "variables": [], "provider": urlparse(item["url"]).netloc}
        d = _load_crawled(rid, meta, KNOWLEDGE_COLLECTION, "challenge_resource")
        if d and len(d.text) >= min_clean_chars:
            docs.append(d)
    return docs


def load_gemini_platform_docs() -> list[Document]:
    docs = []
    for doc_id, meta in R.GEMINI_DOCS.items():
        d = _load_crawled(doc_id, {**meta, "variables": []}, GEMINI_DOCS_COLLECTION, "gemini_platform_docs")
        if d:
            docs.append(d)
    return docs


def load_research_papers() -> list[Document]:
    """Full texts of the forecasting-method papers that exist locally (docs/research/forecast_references.json). Paper D has no local text and is NOT indexed.
    Role 'research_paper': usable for METHODOLOGY explanations and citations only, never as evidence for a forecast value."""
    ref_file = R.PROJECT_DIR / "docs" / "research" / "forecast_references.json" if hasattr(R, "PROJECT_DIR") else Path(__file__).resolve().parent.parent.parent / "docs" / "research" / "forecast_references.json"
    if not ref_file.is_file():
        return []
    docs = []
    for ref in json.loads(ref_file.read_text(encoding="utf-8")).get("references", []):
        tp = ref.get("extracted_text")
        if not tp or not ref.get("full_text_available"):
            continue
        path = ref_file.parent.parent.parent.parent / tp
        if not path.is_file():
            continue
        text = re.sub(r"[ 	]+", " ", path.read_text(encoding="utf-8", errors="replace"))
        text = re.sub(r"[\n]{3,}", chr(10) * 2, text).strip()
        authors = ", ".join(ref.get("authors") or [])
        header = f"{ref['title']} ({authors}, {ref.get('year')}). DOI {ref.get('doi')}. Method paper; not evidence for any forecast value." + chr(10) * 2
        docs.append(Document(source_id=f"paper:{ref['id']}", source_file=path.name, source_type="research_paper", title=ref["title"], text=scrub_secrets(header + text), collection=KNOWLEDGE_COLLECTION,
                             meta={"source_role": "research_paper", "dataset": "forecasting methodology", "provider": ref.get("venue"), "variables": [], "original_url": f"https://doi.org/{ref['doi']}" if ref.get("doi") else None, "language_hint": "en"}))
    return docs


def load_all(include_resources: bool = True) -> dict[str, list[Document]]:
    knowledge = load_core_markdown() + load_crawled_science_docs() + load_research_papers()
    if include_resources:
        knowledge += load_challenge_resources()
    return {KNOWLEDGE_COLLECTION: knowledge, GEMINI_DOCS_COLLECTION: load_gemini_platform_docs()}
