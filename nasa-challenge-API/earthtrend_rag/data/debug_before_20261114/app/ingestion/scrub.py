"""Removes credentials from text before it can reach chunks, embeddings or logs."""
import re

_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),                                  # Google API keys
    re.compile(r"AQ\.[A-Za-z0-9_\-]{10,}"),                                  # Google auth-style tokens
    re.compile(r"(?i)\b(api[_-]?key|map_key|access[_-]?token|secret)\s*[=:]\s*[\"']?[A-Za-z0-9._\-]{16,}[\"']?"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{16,}"),
]


def scrub_secrets(text: str) -> str:
    for p in _PATTERNS:
        text = p.sub("[REDACTED]", text)
    return text


def contains_secret(text: str) -> bool:
    return any(p.search(text) for p in _PATTERNS)
