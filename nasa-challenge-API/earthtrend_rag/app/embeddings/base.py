"""Embeddings are independent of the LLM. Model name and dimension are recorded with the index."""
from __future__ import annotations

import hashlib
import logging
import re
from abc import ABC, abstractmethod

import numpy as np

log = logging.getLogger(__name__)

# model-specific input prefixes (e5 models require them; bge-m3 does not)
_PREFIXES = {
    "intfloat/multilingual-e5-small": ("query: ", "passage: "),
    "intfloat/multilingual-e5-base": ("query: ", "passage: "),
    "intfloat/multilingual-e5-large": ("query: ", "passage: "),
}


class Embedder(ABC):
    name: str
    dim: int

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> np.ndarray: ...

    @abstractmethod
    def embed_query(self, text: str) -> np.ndarray: ...


class SentenceTransformerEmbedder(Embedder):
    def __init__(self, name: str, batch_size: int = 16, max_seq_length: int = 512):
        from sentence_transformers import SentenceTransformer  # heavy import, keep lazy

        self.name = name
        self._model = SentenceTransformer(name, device="cpu")
        self._model.max_seq_length = max_seq_length
        self.dim = int(self._model.get_sentence_embedding_dimension())
        self._q_prefix, self._d_prefix = _PREFIXES.get(name, ("", ""))
        self._batch = batch_size

    def _encode(self, texts: list[str]) -> np.ndarray:
        v = self._model.encode(texts, batch_size=self._batch, normalize_embeddings=True,
                               show_progress_bar=False, convert_to_numpy=True)
        return v.astype(np.float32)

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return self._encode([self._d_prefix + t for t in texts])

    def embed_query(self, text: str) -> np.ndarray:
        return self._encode([self._q_prefix + text])[0]


class HashingEmbedder(Embedder):
    """Deterministic offline embedder (hashed bag of words) used ONLY in unit tests.

    Not semantic: it lets store/filter/dedupe tests run without downloading a model.
    """

    def __init__(self, dim: int = 256):
        self.name = f"hashing-{dim}"
        self.dim = dim

    def _vec(self, text: str) -> np.ndarray:
        v = np.zeros(self.dim, dtype=np.float32)
        for tok in re.findall(r"\w+", text.lower()):
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            v[h % self.dim] += 1.0 if (h >> 8) % 2 == 0 else -1.0
        n = np.linalg.norm(v)
        return v / n if n else v

    def embed_documents(self, texts):
        return np.stack([self._vec(t) for t in texts]) if texts else np.zeros((0, self.dim), np.float32)

    def embed_query(self, text):
        return self._vec(text)


_cache: dict[str, Embedder] = {}


def get_embedder(name: str | None = None) -> Embedder:
    from app.config import get_settings

    name = name or get_settings().embedding_model
    if name not in _cache:
        log.info("loading embedding model %s", name)
        _cache[name] = SentenceTransformerEmbedder(name)
    return _cache[name]
