"""Central configuration. Model IDs, paths and secrets are resolved here only."""
from __future__ import annotations

import logging
import os
import re
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_DIR = Path(__file__).resolve().parent.parent          # earthtrend_rag/
REPO_ROOT = PROJECT_DIR.parent                                 # C:\nasa challenge API
PROTOTYPE_DIR = REPO_ROOT / "البروتوتايب"
RESEARCH_DIR = REPO_ROOT / "research"

KNOWLEDGE_COLLECTION = "earth_knowledge"
GEMINI_DOCS_COLLECTION = "gemini_platform"

_KEY_NAME = "ANTHROPIC_API_KEY"


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


_ENV_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*[=:]\s*(.*?)\s*$")


def dotenv_values(path) -> dict[str, str]:
    """Tolerant .env reader: accepts NAME=value and NAME: value, optional quotes, # comments. Values are never logged."""
    out: dict[str, str] = {}
    try:
        text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return out
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        m = _ENV_LINE.match(line)
        if m and m.group(2):
            v = m.group(2)
            if v[:1] in "\"'" and v[-1:] == v[:1] and len(v) > 1:
                v = v[1:-1]
            out[m.group(1)] = v
    return out


def load_llm_key() -> SecretStr | None:
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


def load_credential(name: str) -> SecretStr | None:
    """Generic secret lookup: process environment first, then the known .env files. Values are never logged or returned."""
    val = os.environ.get(name)
    if val:
        return SecretStr(val.strip())
    for f in _candidate_env_files():
        try:
            v = dotenv_values(f).get(name)
        except Exception:
            continue
        if v:
            return SecretStr(v.strip().strip('"').strip("'"))
    return None


def has_credential(name: str) -> bool:
    c = load_credential(name)
    return bool(c and c.get_secret_value())


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    anthropic_model: str = "claude-haiku-5-5"      # the ONLY allowed model (enforced in app/llm/claude_client.py); ANTHROPIC_MODEL must equal it
    llm_allowed_models: str = "claude-haiku-5-5"   # LLM_ALLOWED_MODELS: informational; anything outside the hard allow-list is a configuration error
    embedding_model: str = "intfloat/multilingual-e5-small"
    llm_daily_cap: int = 400                   # local safety net on requests per day (counted per model id)
    llm_request_timeout_s: float = 30.0        # per attempt
    llm_total_deadline_s: float = 75.0         # whole call, all attempts (same model only)
    llm_max_attempts: int = 2                  # transient errors only, same model, never another model
    llm_max_output_tokens: int = 2048
    request_total_deadline_s: float = Field(default=90.0, gt=0)
    power_total_deadline_s: float = Field(default=30.0, gt=0)
    power_connect_timeout_s: float = Field(default=5.0, gt=0)
    power_read_timeout_s: float = Field(default=15.0, gt=0)
    power_max_attempts: int = Field(default=2, ge=1, le=3)
    provider_total_deadline_s: float = Field(default=30.0, gt=0)   # all non-POWER data providers (per request)
    provider_connect_timeout_s: float = Field(default=5.0, gt=0)
    provider_read_timeout_s: float = Field(default=20.0, gt=0)
    provider_max_attempts: int = Field(default=2, ge=1, le=3)
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


for _n in ("httpx", "httpx2", "httpcore"):          # these libraries log full request URLs (provider keys can sit in the path): never at INFO
    logging.getLogger(_n).setLevel(logging.WARNING)


class SecretRedactingFilter(logging.Filter):
    """Removes API keys from every log record."""

    _patterns = [
        re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
        re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}"),
        re.compile(r"(?i)(api[_-]?key|map_key|token|authorization)(=|:\s*|\s+)(bearer\s+)?[A-Za-z0-9._\-]{16,}"),
        re.compile(r"AQ\.[A-Za-z0-9_\-]{10,}"),
        re.compile(r"(?i)/(?:area|country|data_availability)/csv/[A-Za-z0-9]{16,}"),      # FIRMS keys travel in the URL path
        re.compile(r"(?i)MAP_KEY=[A-Za-z0-9]{8,}"),
        re.compile(r"(?i)PRIVATE-TOKEN['\"]?\s*[=:]?\s*['\"]?[A-Za-z0-9\-]{16,}"),
    ]
    _names = ("ANTHROPIC_API_KEY", "EWDS_API_KEY", "FIRMS_MAP_KEY", "EARTHDATA_TOKEN", "EARTHDATA_PASSWORD", "CDSE_CLIENT_SECRET")

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        key = load_llm_key()
        if key and key.get_secret_value() and key.get_secret_value() in msg:
            msg = msg.replace(key.get_secret_value(), "[REDACTED]")
        for n in self._names:                                    # every configured credential value, wherever it appears
            try:
                c = load_credential(n)
                v = c.get_secret_value() if c else ""
            except Exception:
                v = ""
            if v and len(v) >= 8 and v in msg:
                msg = msg.replace(v, "[REDACTED]")
        for p in self._patterns:
            msg = p.sub(lambda m: m.group(0)[: m.group(0).rfind("/") + 1] + "[REDACTED]" if m.group(0).lower().startswith("/") else "[REDACTED]", msg)
        record.msg, record.args = msg, ()
        return True


def setup_logging(level: str | None = None) -> None:
    root = logging.getLogger()
    if not any(isinstance(f, SecretRedactingFilter) for h in root.handlers for f in h.filters):
        logging.basicConfig(level=(level or get_settings().log_level),
                            format="%(asctime)s %(levelname)s %(name)s: %(message)s")
        for h in root.handlers:
            h.addFilter(SecretRedactingFilter())
        for noisy in ("httpx", "httpx2", "httpcore"):                      # these log full request URLs (provider keys can be in the path)
            logging.getLogger(noisy).setLevel(logging.WARNING)
