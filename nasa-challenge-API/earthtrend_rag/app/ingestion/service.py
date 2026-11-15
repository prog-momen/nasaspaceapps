"""Ingestion orchestration: load -> chunk -> embed -> upsert, with a manifest to skip unchanged sources."""
from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path

from app.chunking.chunker import chunk_document
from app.config import GEMINI_DOCS_COLLECTION, KNOWLEDGE_COLLECTION
from app.embeddings.base import Embedder
from app.ingestion.loaders import load_all
from app.models import Document
from app.vector_store.qdrant_store import QdrantStore

log = logging.getLogger(__name__)


def _doc_fingerprint(doc: Document, embedder_name: str) -> str:
    return hashlib.sha256(f"{embedder_name}|{doc.text}".encode("utf-8")).hexdigest()


def ingest_documents(store: QdrantStore, embedder: Embedder, docs_by_collection: dict[str, list[Document]],
                     manifest_path: Path | None = None, reset: bool = False, force: bool = False) -> dict:
    manifest = {}
    if manifest_path and manifest_path.exists() and not reset:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report: dict = {"collections": {}, "started": time.time()}
    for collection, docs in docs_by_collection.items():
        if reset:
            store.delete_collection(collection)
            manifest = {k: v for k, v in manifest.items() if not k.startswith(f"{collection}|")}
        store.ensure_collection(collection)
        stats = {"sources": 0, "skipped_unchanged": 0, "chunks_added": 0, "chunks_removed": 0, "duplicates_dropped": 0}
        for doc in docs:
            key = f"{collection}|{doc.source_id}"
            fp = _doc_fingerprint(doc, embedder.name)
            if not force and manifest.get(key) == fp:
                stats["skipped_unchanged"] += 1
                continue
            chunks = chunk_document(doc)
            vectors = embedder.embed_documents([c.embed_text for c in chunks]) if chunks else None
            r = store.upsert_source(collection, doc.source_id, chunks, vectors) if chunks else \
                {"added": 0, "removed": store.delete_source(collection, doc.source_id), "duplicates_dropped": 0}
            manifest[key] = fp
            stats["sources"] += 1
            stats["chunks_added"] += r["added"]
            stats["chunks_removed"] += r["removed"]
            stats["duplicates_dropped"] += r["duplicates_dropped"]
            log.info("ingested %s: %s", doc.source_file, r)
        stats["total_chunks"] = store.count(collection)
        report["collections"][collection] = stats
    if manifest_path:
        manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    report["seconds"] = round(time.time() - report["started"], 1)
    return report


def ingest_project_resources(store: QdrantStore, embedder: Embedder, manifest_path: Path | None,
                             reset: bool = False, force: bool = False, include_resources: bool = True,
                             collections: list[str] | None = None) -> dict:
    docs = load_all(include_resources=include_resources)
    if collections:
        docs = {k: v for k, v in docs.items() if k in collections}
    return ingest_documents(store, embedder, docs, manifest_path, reset=reset, force=force)


__all__ = ["ingest_documents", "ingest_project_resources", "KNOWLEDGE_COLLECTION", "GEMINI_DOCS_COLLECTION"]
