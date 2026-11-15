import re

from app.chunking.chunker import MAX_CHARS, chunk_document
from app.ingestion.loaders import load_core_markdown
from app.models import Document


def test_sections_become_separate_chunks_with_path(sample_doc):
    chunks = chunk_document(sample_doc)
    sections = [c.metadata["section"] for c in chunks]
    assert any(s.endswith("S05 — NASA POWER") for s in sections)
    assert any(s.endswith("S06 — FIRMS") for s in sections)
    s05 = next(c for c in chunks if c.metadata["section"].endswith("S05"+" — NASA POWER"))
    assert "YYYY13" in s05.text and "FIRMS" not in s05.text      # card boundaries respected
    assert s05.metadata["service_id"] == "S05"
    assert s05.metadata["source_file"] == "sample.md" and s05.metadata.get("page") is None


def test_embed_text_has_context_but_text_is_original(sample_doc):
    c = next(c for c in chunk_document(sample_doc) if c.metadata.get("service_id") == "S06")
    assert "S06 — FIRMS" in c.embed_text and "Sample Reference" in c.embed_text
    assert "Sample Reference" not in c.text


def test_code_fence_never_split():
    code = "\n".join(f"line {i} " + "x" * 80 for i in range(40))
    doc = Document("t:1", "a.md", "markdown", "T", f"# T\n\n## S\n\n```text\n{code}\n```\n", "earth_knowledge")
    chunks = chunk_document(doc, target=500)
    # fences larger than target are hard-split but each piece stays below the limit
    assert all(len(c.text) <= 1200 for c in chunks)


def test_table_split_repeats_header():
    rows = "\n".join(f"| k{i} | {'v' * 60} |" for i in range(60))
    doc = Document("t:2", "a.md", "markdown", "T", f"# T\n\n## S\n\n| key | value |\n|---|---|\n{rows}\n", "earth_knowledge")
    chunks = chunk_document(doc, target=600)
    assert len(chunks) > 2
    for c in chunks:
        assert c.text.startswith("| key | value |\n|---|---|")
        assert all(l.startswith("|") for l in c.text.split("\n"))     # no broken rows


def test_overlap_only_within_a_section():
    para = "\n\n".join(f"Paragraph {i} " + "word " * 40 for i in range(12))
    doc = Document("t:3", "a.md", "markdown", "T", f"# T\n\n## A\n\n{para}\n\n## B\n\nUnique B content here, long enough to survive the minimum size filter of chunks.", "earth_knowledge")
    chunks = chunk_document(doc, target=700, overlap=250)
    a = [c for c in chunks if c.metadata["section"].endswith("A")]
    b = [c for c in chunks if c.metadata["section"].endswith("B")]
    assert len(a) > 1 and len(b) == 1
    assert "Paragraph" not in b[0].text                      # nothing from A leaks into B
    assert any(set(re.findall(r"Paragraph \d+", a[i].text)) & set(re.findall(r"Paragraph \d+", a[i + 1].text))
               for i in range(len(a) - 1))                   # consecutive chunks of A overlap


def test_toc_section_is_dropped():
    doc = Document("t:4", "a.md", "markdown", "T",
                   "# T\n\n## الفهرس\n\n1. [One](#one)\n2. [Two](#two)\n3. [Three](#three)\n\n## One\n\nReal content that is long enough to be kept as its own chunk in the index.\n", "earth_knowledge")
    texts = " ".join(c.text for c in chunk_document(doc))
    assert "[One](#one)" not in texts and "Real content" in texts


def test_plain_crawled_text_is_chunked_under_limit():
    text = "\n\n".join(f"Sentence block {i}. " + "Content words repeated. " * 30 for i in range(30))
    doc = Document("t:5", "doc_x.txt", "crawled_web_text", "Doc X", text, "earth_knowledge",
                   meta={"dataset": "X", "provider": "P", "variables": ["drought"], "original_url": "https://e.org"})
    chunks = chunk_document(doc)
    assert len(chunks) > 3 and all(len(c.text) <= MAX_CHARS for c in chunks)
    assert all(c.metadata["original_url"] == "https://e.org" and c.metadata["provider"] == "P" for c in chunks)
    assert all("drought" in c.metadata["variables"] for c in chunks)


def test_real_core_reference_keeps_every_service_card():
    core = next(d for d in load_core_markdown() if d.source_file.startswith("EarthTrend"))
    chunks = chunk_document(core)
    services = {c.metadata["service_id"] for c in chunks if c.metadata.get("service_id")}
    assert {f"S{i:02d}" for i in range(1, 25)} <= services
    assert max(len(c.text) for c in chunks) <= MAX_CHARS
    # the POWER card keeps its key facts together
    power = [c for c in chunks if c.metadata.get("service_id") == "S05"]
    assert any("YYYY13" in c.text for c in power)
    # every card chunk records its source
    assert all(c.metadata["source_file"] == core.source_file for c in chunks)
