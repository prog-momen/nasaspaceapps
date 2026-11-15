from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Document:
    """A parsed source document before chunking."""
    source_id: str                 # stable id, e.g. "core:EarthTrend_Explorer_2026_APIs_Tools_Reference_AR.md"
    source_file: str               # filename for display
    source_type: str               # markdown | crawled_html_text | json | csv | ...
    title: str
    text: str
    collection: str
    meta: dict[str, Any] = field(default_factory=dict)  # registry metadata (dataset, variables, url...)


@dataclass
class Chunk:
    text: str                      # original text shown to the LLM and user
    embed_text: str                # text actually embedded (adds title/section context)
    metadata: dict[str, Any]

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()
