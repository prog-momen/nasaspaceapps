"""Shared provider plumbing: HTTP with bounded retries, a small response cache, the result envelope and sanitising.

Every provider function returns the same envelope (see `envelope`). Errors never raise to callers for expected conditions
(missing credentials, unsupported region, provider down): they come back as structured `status` + `reason_code`.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.config import get_settings
from app.reliability import bounded_call, remaining

log = logging.getLogger(__name__)
USER_AGENT = "EarthTrendExplorer-prototype/0.2 (personal local testing)"

STATUSES = {"ok", "no_data", "needs_credentials", "unsupported_region", "unsupported_request", "invalid_request",
            "upstream_error", "not_implemented", "blocked_provider"}
CAPABILITIES = ["active_fire_detection", "fire_danger", "weather_forecast", "historical_climate", "historical_weather",
                "satellite_discovery", "satellite_processing", "dataset_discovery", "map_visualization"]


class ProviderError(RuntimeError):
    def __init__(self, message: str, kind: str = "upstream_error", http_status: int | None = None, attempts: list | None = None):
        super().__init__(message)
        self.kind, self.http_status, self.attempts = kind, http_status, attempts or []


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sanitize(text: Any, *secrets: str) -> str:
    """Remove credentials (known values and key-looking path/query parts) from any string that may be logged or returned."""
    t = str(text)
    for sec in secrets:
        if sec:
            t = t.replace(sec, "[REDACTED]")
    t = re.sub(r"(?i)(map_?key|api[_-]?key|token|access_token|client_secret|password)=([^&\s]+)", r"\1=[REDACTED]", t)
    t = re.sub(r"/api/area/csv/[^/]+/", "/api/area/csv/[REDACTED]/", t)
    t = re.sub(r"/api/data_availability/csv/[^/]+/", "/api/data_availability/csv/[REDACTED]/", t)
    t = re.sub(r"(?i)bearer\s+[A-Za-z0-9._\-]{12,}", "Bearer [REDACTED]", t)
    return t[:600]


def finite(x):
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else x


def strict(o):
    """Make a structure strict-JSON safe (NaN/Infinity -> None, numpy -> python)."""
    if isinstance(o, dict):
        return {str(k): strict(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [strict(v) for v in o]
    if hasattr(o, "item") and not isinstance(o, (str, bytes)):
        try:
            o = o.item()
        except Exception:
            pass
    return finite(o) if isinstance(o, float) else o


def envelope(provider: str, product: str, capability: str, status: str = "ok", reason_code: str | None = None,
             message: str | None = None, **kw) -> dict:
    assert status in STATUSES, status
    out = {"provider": provider, "product": product, "capability": capability, "status": status, "reason_code": reason_code,
           "message": message, "variables": [], "request": {}, "actual": {}, "units": {}, "temporal_resolution": None,
           "retrieved_at": now_iso(), "live": None, "cache": None, "source_links": [], "attribution": None, "license": None,
           "quality": {}, "limitations": [], "setup": None, "data": None, "artifacts": [], "duration_ms": None}
    out.update(kw)
    return out


# ---- cache -----------------------------------------------------------------------------------------
def _cache_dir() -> Path:
    d = get_settings().data_dir / "cache" / "providers"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_key(provider: str, method: str, url: str, params: dict | None, body: Any) -> str:
    raw = json.dumps([provider, method, url, sorted((params or {}).items()), body], sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def cache_get(key: str, ttl: float) -> tuple[Any, str] | None:
    f = _cache_dir() / f"{key}.json"
    try:
        c = json.loads(f.read_text(encoding="utf-8"))
        if time.time() - c["stored_at"] <= ttl:
            return c["payload"], c["retrieved_at"]
    except Exception:
        pass
    return None


def cache_put(key: str, payload: Any) -> str:
    ts = now_iso()
    try:
        (_cache_dir() / f"{key}.json").write_text(json.dumps({"stored_at": time.time(), "retrieved_at": ts, "payload": payload}), encoding="utf-8")
    except Exception:
        log.warning("provider cache write failed")
    return ts


# ---- http ------------------------------------------------------------------------------------------
def http_json(provider: str, method: str, url: str, *, params: dict | None = None, json_body: Any = None,
              headers: dict | None = None, ttl: float = 0, parse: str = "json", secrets: tuple[str, ...] = (),
              cache_params: dict | None = None, use_cache: bool = True) -> tuple[Any, dict]:
    """Returns (payload, meta). parse: json | text | bytes. meta = {live, cache, retrieved_at, seconds, http_status, attempts}.

    One retry layer, bounded by settings.provider_*; transient 429/5xx and transport errors are retried with jitter, others never.
    `cache_params` lets the cache key exclude credentials that are part of params/headers.
    """
    import random
    s = get_settings()
    key = _cache_key(provider, method, url, cache_params if cache_params is not None else params, json_body)
    if ttl and use_cache:
        hit = cache_get(key, ttl)
        if hit:
            return hit[0], {"live": False, "cache": "hit", "retrieved_at": hit[1], "seconds": 0.0, "http_status": 200, "attempts": []}
    deadline = time.monotonic() + remaining(s.provider_total_deadline_s)
    attempts: list[dict] = []
    hdrs = {"User-Agent": USER_AGENT, **(headers or {})}
    last_kind, last_status = "upstream_error", None
    with httpx.Client(follow_redirects=True) as client:
        for attempt in range(s.provider_max_attempts):
            left = remaining(deadline - time.monotonic())
            if left <= 0.5:
                break
            t0 = time.monotonic()
            try:
                timeout = httpx.Timeout(min(left, s.provider_read_timeout_s), connect=min(left, s.provider_connect_timeout_s))
                r = bounded_call(lambda: client.request(method, url, params=params, json=json_body, headers=hdrs, timeout=timeout), left)
                attempts.append({"http_status": r.status_code, "seconds": round(time.monotonic() - t0, 2)})
                last_status = r.status_code
                if r.status_code in (429, 500, 502, 503, 504):
                    last_kind = "quota" if r.status_code == 429 else "service_error"
                    wait = None
                    ra = r.headers.get("retry-after")
                    try:
                        wait = float(ra) if ra else None
                    except ValueError:
                        wait = None
                    if attempt + 1 >= s.provider_max_attempts:
                        break
                    wait = wait if wait is not None else random.uniform(0.5, 2.0)
                    if wait >= remaining(deadline - time.monotonic()) - 0.5:
                        break
                    time.sleep(wait)
                    continue
                if r.status_code >= 400:
                    body = r.text[:300]
                    kind = "auth" if r.status_code in (401, 403) else ("invalid_request" if r.status_code in (400, 404, 422) else "upstream_error")
                    raise ProviderError(sanitize(f"HTTP {r.status_code}: {body}", *secrets), kind, r.status_code, attempts)
                payload = r.json() if parse == "json" else (r.text if parse == "text" else r.content)
                ts = now_iso()
                if ttl and parse != "bytes":
                    ts = cache_put(key, payload)
                return payload, {"live": True, "cache": "miss" if ttl else "none", "retrieved_at": ts, "seconds": round(time.monotonic() - t0, 2),
                                 "http_status": r.status_code, "attempts": attempts}
            except ProviderError:
                raise
            except ValueError as e:
                raise ProviderError("provider returned content that is not valid " + parse, "parsing", last_status, attempts) from None
            except (httpx.TimeoutException, TimeoutError) as e:
                last_kind = "timeout"
                attempts.append({"kind": "timeout", "error": type(e).__name__})
                if isinstance(e, TimeoutError):
                    break
            except httpx.TransportError as e:
                last_kind = "network"
                attempts.append({"kind": "network", "error": type(e).__name__})
            if attempt + 1 < s.provider_max_attempts:
                time.sleep(min(random.uniform(0.4, 1.5), max(0.0, remaining(deadline - time.monotonic()) - 0.5)))
    stale = cache_get(key, 10 ** 9) if ttl else None
    if stale and last_kind in ("timeout", "network", "service_error"):
        return stale[0], {"live": False, "cache": "stale", "retrieved_at": stale[1], "seconds": 0.0, "http_status": None, "attempts": attempts,
                          "warning": "provider unreachable; showing the last cached response"}
    raise ProviderError(f"provider unavailable ({last_kind})", last_kind, last_status, attempts)


def fail(provider: str, product: str, capability: str, e: ProviderError, **kw) -> dict:
    status = "upstream_error"
    code = e.kind
    if e.kind == "auth":
        status, code = "needs_credentials", "AUTH_REJECTED"
    elif e.kind == "invalid_request":
        status = "invalid_request"
    return envelope(provider, product, capability, status, code.upper() if code else "UPSTREAM_ERROR", sanitize(e), live=False,
                    quality={"attempts": e.attempts}, **kw)


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    p = math.pi / 180
    a = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(a))


def validate_point(lat, lon) -> str | None:
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return "latitude/longitude must be numbers"
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or not (math.isfinite(lat) and math.isfinite(lon)):
        return "latitude must be in [-90, 90] and longitude in [-180, 180]"
    return None


def validate_bbox(b, max_deg: float = 20.0) -> str | None:
    try:
        w, s_, e, n = [float(x) for x in b]
    except (TypeError, ValueError):
        return "bbox must be [west, south, east, north]"
    if not (-180 <= w < e <= 180 and -90 <= s_ < n <= 90):
        return "bbox must satisfy -180<=west<east<=180 and -90<=south<north<=90"
    if (e - w) > max_deg or (n - s_) > max_deg:
        return f"bbox is larger than the {max_deg:g} degree prototype limit"
    return None


def parse_date(s: str | None, name: str = "date"):
    from datetime import date
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        raise ProviderError(f"{name} must be YYYY-MM-DD", "invalid_request") from None
