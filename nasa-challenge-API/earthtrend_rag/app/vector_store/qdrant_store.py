"""Persistent Qdrant (local mode) store.

- One collection per knowledge scope (earth_knowledge, gemini_platform).
- Point id = uuid5(content hash) -> re-ingesting identical text is idempotent (duplicate prevention).
- Update by source: chunks of a source that vanished from the new version are deleted.
- Embedding model + dimension are written to the collection's meta file and checked on every open.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from qdrant_client import QdrantClient, models

from app.models import Chunk

log = logging.getLogger(__name__)
_NS = uuid.UUID("6f1b5a62-7d0c-4f3e-9a52-3c6a1f2b9e11")

FILTERABLE = ["source_id", "source_file", "source_type", "source_role", "service_id", "language",
              "variables", "dataset_ids", "provider"]


@dataclass
class SearchHit:
    id: str
    score: float
    text: str
    metadata: dict[str, Any]


class QdrantStore:
    def __init__(self, path: Path | str | None, embedding_name: str, dim: int):
        """path=None -> in-memory (tests)."""
        self.path = Path(path) if path else None
        self.embedding_name, self.dim = embedding_name, dim
        if self.path:
            self.path.mkdir(parents=True, exist_ok=True)
            self.client = QdrantClient(path=str(self.path))
        else:
            self.client = QdrantClient(":memory:")

    # ---- collection management -------------------------------------------------
    def _meta_file(self) -> Path | None:
        return self.path / "embedding_meta.json" if self.path else None

    def _read_meta(self) -> dict:
        f = self._meta_file()
        return json.loads(f.read_text(encoding="utf-8")) if f and f.exists() else {}

    def _write_meta(self, meta: dict) -> None:
        f = self._meta_file()
        if f:
            f.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def ensure_collection(self, name: str) -> None:
        meta = self._read_meta()
        existing = {c.name for c in self.client.get_collections().collections}
        if name in existing:
            m = meta.get(name)
            if m and (m["model"] != self.embedding_name or m["dim"] != self.dim):
                raise RuntimeError(
                    f"Collection '{name}' was built with {m['model']} (dim {m['dim']}), "
                    f"but the active embedder is {self.embedding_name} (dim {self.dim}). "
                    "Re-ingest with reset=True or switch EMBEDDING_MODEL back.")
            return
        self.client.create_collection(
            name, vectors_config=models.VectorParams(size=self.dim, distance=models.Distance.COSINE))
        for f in FILTERABLE:
            try:
                self.client.create_payload_index(name, f, models.PayloadSchemaType.KEYWORD)
            except Exception:  # local mode ignores payload indexes
                pass
        meta[name] = {"model": self.embedding_name, "dim": self.dim}
        self._write_meta(meta)

    def delete_collection(self, name: str) -> None:
        if name in {c.name for c in self.client.get_collections().collections}:
            self.client.delete_collection(name)
        meta = self._read_meta()
        meta.pop(name, None)
        self._write_meta(meta)

    def count(self, name: str) -> int:
        try:
            return self.client.count(name, exact=True).count
        except Exception:
            return 0

    def collections(self) -> dict[str, int]:
        return {c.name: self.count(c.name) for c in self.client.get_collections().collections}

    # ---- writes --------------------------------------------------------------
    @staticmethod
    def point_id(chunk: Chunk) -> str:
        return str(uuid.uuid5(_NS, f"{chunk.metadata.get('source_id', '')}|{chunk.content_hash}"))

    def upsert_source(self, collection: str, source_id: str, chunks: list[Chunk], vectors: np.ndarray) -> dict:
        """Replace everything stored for `source_id` with `chunks` (idempotent)."""
        self.ensure_collection(collection)
        new_ids = {}
        for c, v in zip(chunks, vectors):
            new_ids.setdefault(self.point_id(c), (c, v))   # drop exact duplicates inside the batch
        old = self._ids_for_source(collection, source_id)
        stale = [i for i in old if i not in new_ids]
        if stale:
            self.client.delete(collection, points_selector=models.PointIdsList(points=stale))
        fresh = [i for i in new_ids if i not in old]
        points = [models.PointStruct(
            id=i, vector=new_ids[i][1].tolist(),
            payload={**new_ids[i][0].metadata, "text": new_ids[i][0].text, "content_hash": new_ids[i][0].content_hash})
            for i in fresh]
        for i in range(0, len(points), 128):
            self.client.upsert(collection, points=points[i:i + 128])
        return {"added": len(fresh), "removed": len(stale), "unchanged": len(old) - len(stale),
                "duplicates_dropped": len(chunks) - len(new_ids)}

    def _ids_for_source(self, collection: str, source_id: str) -> set[str]:
        ids, offset = set(), None
        flt = models.Filter(must=[models.FieldCondition(key="source_id", match=models.MatchValue(value=source_id))])
        while True:
            pts, offset = self.client.scroll(collection, scroll_filter=flt, limit=256, offset=offset,
                                             with_payload=False, with_vectors=False)
            ids.update(str(p.id) for p in pts)
            if offset is None:
                return ids

    def delete_source(self, collection: str, source_id: str) -> int:
        ids = list(self._ids_for_source(collection, source_id))
        if ids:
            self.client.delete(collection, points_selector=models.PointIdsList(points=ids))
        return len(ids)

    # ---- reads ---------------------------------------------------------------
    @staticmethod
    def build_filter(filters: dict[str, Any] | None) -> models.Filter | None:
        if not filters:
            return None
        must = []
        for k, v in filters.items():
            if v is None or v == []:
                continue
            if isinstance(v, (list, tuple, set)):
                must.append(models.FieldCondition(key=k, match=models.MatchAny(any=list(v))))
            else:
                must.append(models.FieldCondition(key=k, match=models.MatchValue(value=v)))
        return models.Filter(must=must) if must else None

    def search(self, collection: str, vector: np.ndarray, limit: int,
               filters: dict[str, Any] | None = None) -> list[SearchHit]:
        if collection not in {c.name for c in self.client.get_collections().collections}:
            return []
        res = self.client.query_points(collection, query=vector.tolist(), limit=limit,
                                       query_filter=self.build_filter(filters), with_payload=True)
        return [self._hit(p) for p in res.points]

    def iter_all(self, collection: str, filters: dict[str, Any] | None = None) -> Iterable[SearchHit]:
        offset = None
        flt = self.build_filter(filters)
        while True:
            pts, offset = self.client.scroll(collection, scroll_filter=flt, limit=256, offset=offset,
                                             with_payload=True, with_vectors=False)
            for p in pts:
                yield self._hit(p)
            if offset is None:
                return

    @staticmethod
    def _hit(p) -> SearchHit:
        payload = dict(p.payload or {})
        text = payload.pop("text", "")
        return SearchHit(id=str(p.id), score=float(getattr(p, "score", 0.0) or 0.0), text=text, metadata=payload)

    def close(self) -> None:
        self.client.close()
