"""Structure-aware chunking.

Strategy
- Markdown: split on headings; one API card / product table row group stays together.
- Within a section, atomic blocks (paragraph, fenced code, table, list item group) are packed up to
  `target_chars`; oversized tables are split by rows with the header repeated; oversized paragraphs
  are split on sentence boundaries.
- Overlap (`overlap_chars`) is carried between chunks of the SAME section only, never across headings.
- Every chunk is embedded with its title + section path prepended (contextual header) but the
  stored/displayed text is the original.
Sizes are in characters (Arabic+English mixed text makes word counts unreliable). 1600 chars is roughly
350-500 tokens, which fits the 512-token limit of multilingual-e5 models and keeps an API card whole.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.chunking.metadata import extract_metadata
from app.models import Chunk, Document

TARGET_CHARS = 1600
MAX_CHARS = 2200
OVERLAP_CHARS = 200
MIN_CHARS = 120

_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_TOC_LINE = re.compile(r"^\s*\d+\.\s*\[.*\]\(#.*\)\s*$")


@dataclass
class Section:
    path: list[str]
    level: int
    lines: list[str]


def _split_sections(text: str) -> list[Section]:
    sections: list[Section] = []
    stack: list[tuple[int, str]] = []
    cur = Section([], 0, [])
    in_fence = False
    for line in text.split("\n"):
        if line.strip().startswith("```"):
            in_fence = not in_fence
        m = None if in_fence else _HEADING.match(line)
        if m:
            if cur.lines:
                sections.append(cur)
            level, title = len(m.group(1)), re.sub(r"<[^>]+>", "", m.group(2)).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
            cur = Section([t for _, t in stack], level, [])
        else:
            cur.lines.append(line)
    if cur.lines:
        sections.append(cur)
    return sections


def _blocks(lines: list[str]) -> list[str]:
    """Group lines into atomic blocks: fenced code, tables, paragraphs/lists."""
    blocks, buf, in_fence = [], [], False

    def flush():
        nonlocal buf
        if buf and any(l.strip() for l in buf):
            blocks.append("\n".join(buf).strip("\n"))
        buf = []

    prev_table = False
    for line in lines:
        s = line.strip()
        if s.startswith("```"):
            if not in_fence:
                flush()
            buf.append(line)
            in_fence = not in_fence
            if not in_fence:
                flush()
            continue
        if in_fence:
            buf.append(line)
            continue
        is_table = s.startswith("|")
        if is_table != prev_table:
            flush()
        prev_table = is_table
        if not s:
            flush()
        else:
            buf.append(line)
    flush()
    return blocks


def _split_table(block: str, limit: int) -> list[str]:
    rows = block.split("\n")
    if len(rows) < 3:
        return [block]
    header, rest = rows[:2], rows[2:]
    parts, cur = [], []
    size = sum(len(r) + 1 for r in header)
    for r in rest:
        if cur and size + len(r) + 1 > limit:
            parts.append("\n".join(header + cur))
            cur, size = [], sum(len(h) + 1 for h in header)
        cur.append(r)
        size += len(r) + 1
    if cur:
        parts.append("\n".join(header + cur))
    return parts


def _split_text(block: str, limit: int) -> list[str]:
    if len(block) <= limit:
        return [block]
    # list items first, then sentences, then hard cut
    units = [u for u in re.split(r"(?<=\n)(?=\s*[-*]\s)|(?<=[.!?؟。])\s+", block) if u and u.strip()]
    parts, cur = [], ""
    for u in units:
        if len(u) > limit:
            if cur:
                parts.append(cur)
                cur = ""
            parts.extend(u[i:i + limit] for i in range(0, len(u), limit))
            continue
        if cur and len(cur) + len(u) + 1 > limit:
            parts.append(cur)
            cur = u
        else:
            cur = f"{cur} {u}" if cur else u
    if cur:
        parts.append(cur)
    return parts


def _expand(blocks: list[str], limit: int) -> list[str]:
    out = []
    for b in blocks:
        if len(b) <= limit:
            out.append(b)
        elif b.lstrip().startswith("|"):
            out.extend(_split_table(b, limit))
        elif b.lstrip().startswith("```"):
            out.extend(b[i:i + limit] for i in range(0, len(b), limit))
        else:
            out.extend(_split_text(b, limit))
    return out


def _pack(blocks: list[str], target: int, overlap: int) -> list[str]:
    chunks, cur = [], []
    size = 0
    for b in blocks:
        if cur and size + len(b) + 2 > target:
            chunks.append("\n\n".join(cur))
            # carry overlap: trailing blocks totalling <= overlap chars
            carry, c = [], 0
            for prev in reversed(cur):
                if c + len(prev) > overlap:
                    break
                carry.insert(0, prev)
                c += len(prev)
            cur, size = carry, c
        cur.append(b)
        size += len(b) + 2
    if cur:
        chunks.append("\n\n".join(cur))
    # drop a final chunk that is entirely overlap of the previous one
    if len(chunks) > 1 and chunks[-1] in chunks[-2]:
        chunks.pop()
    return chunks


def _is_toc(lines: list[str]) -> bool:
    body = [l for l in lines if l.strip()]
    return bool(body) and sum(1 for l in body if _TOC_LINE.match(l)) / len(body) > 0.6


def chunk_document(doc: Document, target: int = TARGET_CHARS, max_chars: int = MAX_CHARS,
                   overlap: int = OVERLAP_CHARS) -> list[Chunk]:
    if doc.source_type == "markdown":
        sections = _split_sections(doc.text)
    else:  # plain crawled text: no reliable headings -> one section titled by the page title
        sections = [Section([doc.title], 1, doc.text.split("\n"))]

    chunks: list[Chunk] = []
    pending_prefix: list[str] = []   # tiny sections get merged into the next one
    for sec in sections:
        if _is_toc(sec.lines):
            continue
        body = "\n".join(sec.lines).strip()
        if not body:
            continue
        blocks = _expand(_blocks(sec.lines), target)
        if pending_prefix:
            blocks = pending_prefix + blocks
            pending_prefix = []
        if sum(len(b) for b in blocks) < MIN_CHARS and sec is not sections[-1]:
            pending_prefix = blocks  # merge forward
            continue
        heading = " > ".join(sec.path)
        pieces = [p for p in _pack(blocks, target, overlap) if len(p.strip()) >= 40]
        for i, piece in enumerate(pieces):
            md = extract_metadata(piece, heading)
            md.update({
                "source_id": doc.source_id,
                "source_file": doc.source_file,
                "source_type": doc.source_type,
                "document_title": doc.title,
                "section": heading or doc.title,
                "section_part": i,
                "page": None,                       # markdown / crawled text have no pages
                "collection": doc.collection,
                "source_role": doc.meta.get("source_role"),
            })
            for k in ("original_url", "retrieved_at"):
                if doc.meta.get(k):
                    md[k] = doc.meta[k]
            # registry metadata (explicit, from project files)
            if doc.meta.get("dataset"):
                md.setdefault("dataset_name", doc.meta["dataset"])
            if doc.meta.get("provider"):
                md["provider"] = doc.meta["provider"]
            reg_vars = doc.meta.get("variables") or []
            if reg_vars:
                md["variables"] = sorted(set(md.get("variables", [])) | set(reg_vars))
            md = {k: v for k, v in md.items() if v is not None}
            embed_text = f"{doc.title}\n{heading}\n{piece}" if heading and heading != doc.title else f"{doc.title}\n{piece}"
            chunks.append(Chunk(text=piece, embed_text=embed_text, metadata=md))
    # trailing merged-forward leftovers
    if pending_prefix:
        piece = "\n\n".join(pending_prefix)
        chunks.append(Chunk(text=piece, embed_text=f"{doc.title}\n{piece}",
                            metadata={"source_id": doc.source_id, "source_file": doc.source_file,
                                      "source_type": doc.source_type, "document_title": doc.title,
                                      "section": doc.title, "section_part": 0,
                                      "collection": doc.collection, **extract_metadata(piece)}))
    return chunks
