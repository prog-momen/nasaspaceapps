"""Provider-neutral LLM errors, result type and local usage tracker (shared by the Anthropic client; no vendor SDK imported here)."""
from __future__ import annotations

import json
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


class LLMError(RuntimeError):
    """kind: auth | invalid_request | model_not_found | quota | overloaded | timeout | network | empty | not_configured | budget"""

    def __init__(self, message: str, status: int = 502, kind: str = "unknown", attempts: list | None = None):
        super().__init__(message)
        self.status, self.kind, self.attempts = status, kind, attempts or []


class BudgetExceeded(LLMError):
    def __init__(self, message: str):
        super().__init__(message, status=429, kind="budget")


@dataclass
class LLMResult:
    text: str
    model: str
    prompt_tokens: int | None
    output_tokens: int | None
    latency_s: float


def _pacific():
    """Google resets free-tier daily quotas at midnight Pacific time (rate-limits docs); UTC days would drift by 7-8 h."""
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("America/Los_Angeles")
    except Exception:                                    # tz database missing: PST (UTC-8) is a conservative fixed fallback
        from datetime import timedelta
        return timezone(timedelta(hours=-8))


def pacific_day(now: float | None = None) -> str:
    return datetime.fromtimestamp(now if now is not None else time.time(), _pacific()).strftime("%Y-%m-%d")


def next_pacific_midnight(now: float | None = None) -> float:
    from datetime import timedelta
    tz = _pacific()
    d = datetime.fromtimestamp(now if now is not None else time.time(), tz)
    nxt = (d + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return nxt.timestamp()


class UsageTracker:
    """Per-model request counters per PACIFIC day + 'exhausted until' markers, persisted in a small JSON file.

    * Counts attempts that reached the service (conservative: a failed 5xx may or may not count at Google).
    * Read-modify-write happens under a thread lock AND a cross-process file lock, and the file is replaced atomically,
      so concurrent workers / restarts cannot lose increments or leave a half-written file.
    * An 'exhausted' marker lasts until the reset the service announced (retryDelay), or the next Pacific midnight when none
      was given; expired markers are purged on every write. The local cap is a safety net below the provider limit, which is
      per model and only visible when exceeded.
    """

    def __init__(self, path: Path, cap_per_model_per_day: int):
        self.path, self.cap = path, cap_per_model_per_day
        self._lock = threading.Lock()

    # -- storage --------------------------------------------------------------------------------------
    @contextmanager
    def _txn(self):
        import portalocker
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with portalocker.Lock(str(self.path) + ".lock", timeout=15):
                yield

    def _load(self) -> dict:
        try:
            d = json.loads(self.path.read_text(encoding="utf-8"))
            return d if isinstance(d, dict) else {}
        except Exception:
            return {}

    def _save(self, data: dict) -> None:
        now = time.time()
        ex = {m: u for m, u in data.get("_exhausted", {}).items() if float(u) > now}   # purge expired markers
        days = {k: v for k, v in data.items() if k != "_exhausted" and isinstance(v, dict)}
        keep = dict(sorted(days.items())[-14:])
        if ex:
            keep["_exhausted"] = ex
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(keep, indent=1), encoding="utf-8")
        os.replace(tmp, self.path)

    @staticmethod
    def _day() -> str:
        return pacific_day()

    # -- API ------------------------------------------------------------------------------------------
    def today(self) -> dict:
        d = self._load().get(self._day(), {})
        models = {m: v for m, v in d.items() if isinstance(v, dict)}
        return {"date": self._day(), "timezone": "America/Los_Angeles", "requests": sum(v.get("requests", 0) for v in models.values()),
                "prompt_tokens": sum(v.get("prompt_tokens", 0) for v in models.values()),
                "output_tokens": sum(v.get("output_tokens", 0) for v in models.values()), "models": models}

    def exhausted_until(self, model: str) -> float:
        return float(self._load().get("_exhausted", {}).get(model, 0))

    def block_reason(self, model: str) -> str | None:
        if self.exhausted_until(model) > time.time():
            return "daily quota exhausted (cached)"
        count = self.today()["models"].get(model, {}).get("requests", 0)
        if self.cap and count >= self.cap:
            return "local daily request cap reached"
        return None

    def mark_exhausted(self, model: str, seconds: float | None = None) -> None:
        with self._txn():
            data = self._load()
            until = time.time() + seconds if seconds and seconds > 0 else next_pacific_midnight()
            data.setdefault("_exhausted", {})[model] = until
            self._save(data)

    def reserve(self, model: str) -> None:
        with self._txn():
            data = self._load()
            m = data.setdefault(self._day(), {}).setdefault(model, {"requests": 0, "prompt_tokens": 0, "output_tokens": 0})
            if self.cap and m.get("requests", 0) >= self.cap:
                raise BudgetExceeded(f"Local daily request cap for {model} reached ({self.cap}).")
            m["requests"] = m.get("requests", 0) + 1
            self._save(data)

    def record(self, model: str, prompt_tokens: int | None, output_tokens: int | None) -> None:
        with self._txn():
            data = self._load()
            m = data.setdefault(self._day(), {}).setdefault(model, {"requests": 0, "prompt_tokens": 0, "output_tokens": 0})
            m["prompt_tokens"] = m.get("prompt_tokens", 0) + (prompt_tokens or 0)
            m["output_tokens"] = m.get("output_tokens", 0) + (output_tokens or 0)
            self._save(data)


