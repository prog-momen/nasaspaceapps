"""Central configuration. Model IDs, paths and secrets are resolved here only."""
from __future__ import annotations

import logging
import os
import re
from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_DIR = Path(__file__).resolve().parent.parent          # earthtrend_rag/
REPO_ROOT = PROJECT_DIR.parent                                 # C:\nasa challenge API
PROTOTYPE_DIR = REPO_ROOT / "البروتوتايب"
RESEARCH_DIR = REPO_ROOT / "research"

KNOWLEDGE_COLLECTION = "earth_knowledge"
GEMINI_DOCS_COLLECTION = "gemini_platform"

_KEY_NAME = "GEMINI_API_KEY"


def _candidate_env_files() -> list[Path]:
    files = [PROJECT_DIR / ".env", REPO_ROOT / ".env", PROTOTYPE_DIR / ".env"]
    if PROTOTYPE_DIR.is_dir():
        # Tolerate oddly named files such as "<something>.env" in the prototype folder.
        files += sorted(p for p in PROTOTYPE_DIR.iterdir() if p.is_file() and p.name.endswith(".env"))
    seen, out = set(), []
    for f in files:
        if f.is_file() and f not in seen:
            seen.add(f)
            out.append(f)
    return out


def load_gemini_key() -> SecretStr | None:
    """Environment variable first, then known .env locations. Never logs the value."""
    val = os.environ.get(_KEY_NAME)
    if val:
        return SecretStr(val.strip())
    for f in _candidate_env_files():
        try:
            v = dotenv_values(f).get(_KEY_NAME)
        except Exception:  # unreadable file: skip, do not echo its path contents
            continue
        if v:
            return SecretStr(v.strip().strip('"').strip("'"))
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    gemini_model: str = "gemini-3.8-flash"
    embedding_model: str = "intfloat/multilingual-e5-small"
    gemini_fallback_models: str = ""           # comma-separated, free-tier models only (e.g. "gemini-3.6-flash")
    gemini_daily_cap_per_model: int = 18       # local safety net; gemini-3.8-flash free tier allowed 20/day/project at test time
    gemini_request_timeout_s: float = 30.0     # per attempt
    gemini_total_deadline_s: float = 75.0      # whole call, all attempts and models
    gemini_max_attempts: int = 3               # per model (transient errors only)
    gemini_temperature: float = 0.1
    gemini_max_output_tokens: int = 2048
    log_level: str = "INFO"

    data_dir: Path = PROJECT_DIR / "data"

    # Trend analysis defaults (declared in every result; overridable per request)
    trend_alpha: float = 0.05
    trend_min_years: int = 10
    trend_min_months_per_year: int = 9
    trend_min_coverage: float = 0.6

    # Retrieval defaults
    top_k: int = 5
    candidate_k: int = 20
    min_dense_score: float = 0.35   # calibrated in evaluation (see docs)
    hybrid_rrf_k: int = 60

    @property
    def fallback_model_list(self) -> list[str]:
        return [m.strip() for m in self.gemini_fallback_models.split(',') if m.strip()]

    @property
    def qdrant_path(self) -> Path:
        return self.data_dir / "qdrant"

    @property
    def usage_file(self) -> Path:
        return self.data_dir / "usage.json"

    @property
    def manifest_file(self) -> Path:
        return self.data_dir / "manifest.json"


@lru_cache
def get_settings() -> Settings:
    names = {k.upper() for k in Settings.model_fields}
    for f in _candidate_env_files():
        # non-secret settings may live in the same files; the key is read separately
        try:
            for k, v in dotenv_values(f).items():
                if k and v and k.upper() in names:
                    os.environ.setdefault(k.upper(), v)
        except Exception:
            pass
    s = Settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    return s


class SecretRedactingFilter(logging.Filter):
    """Removes API keys from every log record."""

    _patterns = [
        re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
        re.compile(r"(?i)(api[_-]?key|map_key|token|authorization)(=|:\s*|\s+)(bearer\s+)?[A-Za-z0-9._\-]{16,}"),
        re.compile(r"AQ\.[A-Za-z0-9_\-]{10,}"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        key = load_gemini_key()
        if key and key.get_secret_value() and key.get_secret_value() in msg:
            msg = msg.replace(key.get_secret_value(), "[REDACTED]")
        for p in self._patterns:
            msg = p.sub("[REDACTED]", msg)
        record.msg, record.args = msg, ()
        return True


def setup_logging(level: str | None = None) -> None:
    root = logging.getLogger()
    if not any(isinstance(f, SecretRedactingFilter) for h in root.handlers for f in h.filters):
        logging.basicConfig(level=(level or get_settings().log_level),
                            format="%(asctime)s %(levelname)s %(name)s: %(message)s")
        for h in root.handlers:
            h.addFilter(SecretRedactingFilter())
