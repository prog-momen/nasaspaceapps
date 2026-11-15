"""BM25 keyword index with Arabic/English normalisation (keeps identifiers like MOD11C3, S05, PRECTOTCORR)."""
from __future__ import annotations

import re
from typing import Any

import math
from collections import Counter

_DIACRITICS = re.compile(r"[ً-ٰٟـ]")
_TOKEN = re.compile(r"[A-Za-z0-9_]+|[؀-ۿ]+")
_STOP = {"the", "a", "an", "of", "and", "or", "to", "in", "is", "for", "on", "with", "what", "how",
         "في", "من", "على", "عن", "إلى", "الى", "ما", "هو", "هي", "هل", "كيف", "أن", "ان", "مع", "او", "أو", "و"}


def _norm_ar(tok: str) -> str:
    tok = _DIACRITICS.sub("", tok)
    tok = re.sub("[إأآ]", "ا", tok).replace("ى", "ي").replace("ة", "ه")
    for p in ("وال", "بال", "لل", "ال"):
        if tok.startswith(p) and len(tok) - len(p) >= 3:
            tok = tok[len(p):]
            break
    return tok


def tokenize(text: str) -> list[str]:
    out = []
    for t in _TOKEN.findall(text):
        t = t.lower() if t.isascii() else _norm_ar(t)
        if t and t not in _STOP and len(t) > 1:
            out.append(t)
    return out


class KeywordIndex:
    """Okapi BM25 with the always-positive (Lucene-style) IDF, so tiny corpora still score correctly."""

    def __init__(self, hits: list, k1: float = 1.5, b: float = 0.75):
        self.hits, self.k1, self.b = hits, k1, b
        self.docs = [Counter(tokenize(h.metadata.get("section", "") + " " + h.text)) for h in hits]
        self.lens = [sum(d.values()) for d in self.docs]
        self.avg = (sum(self.lens) / len(self.lens)) if self.lens else 0.0
        df: Counter = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def _scores(self, toks: list[str]) -> list[float]:
        out = []
        for d, ln in zip(self.docs, self.lens):
            s = 0.0
            for t in toks:
                f = d.get(t)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * ln / (self.avg or 1)))
            out.append(s)
        return out

    def search(self, query: str, limit: int, filters: dict[str, Any] | None = None) -> list[tuple[Any, float]]:
        toks = tokenize(query)
        if not self.hits or not toks:
            return []
        scores = self._scores(toks)
        order = sorted(range(len(scores)), key=lambda i: -scores[i])
        out = []
        for i in order:
            if scores[i] <= 0:
                break
            h = self.hits[i]
            if filters and not _match(h.metadata, filters):
                continue
            out.append((h, float(scores[i])))
            if len(out) >= limit:
                break
        return out


def _match(md: dict, filters: dict) -> bool:
    for k, want in filters.items():
        if want is None or want == []:
            continue
        have = md.get(k)
        wants = want if isinstance(want, (list, tuple, set)) else [want]
        haves = have if isinstance(have, list) else [have]
        if not any(w in haves for w in wants):
            return False
    return True
