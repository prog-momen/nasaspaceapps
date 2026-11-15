"""Chat, direct tool, diagnostics and preview endpoints for the local test UI. Backend-only credentials; nothing secret is returned."""
from __future__ import annotations

import logging
import platform
import re
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.chat import render, tools
from app.chat.agent import ChatAgent
from app.config import KNOWLEDGE_COLLECTION, PROJECT_DIR, _candidate_env_files, get_settings, has_credential, load_llm_key
from app.llm.base import LLMError, UsageTracker
from app.providers import copernicus, earthdata, fire_danger, fire_outlook, firms, gee, open_meteo, registry
from app.providers.base import strict

log = logging.getLogger("app.chat_api")
router = APIRouter()
STARTED = datetime.now(timezone.utc)


class Controls(BaseModel):
    point: Optional[dict] = Field(None, description="{lat, lon}")
    bbox: Optional[list[float]] = Field(None, description="[west, south, east, north]")
    start: Optional[str] = None
    end: Optional[str] = None
    task: str = "auto"
    variable: Optional[str] = None
    provider: str = "auto"
    answer_mode: str = "auto"          # auto | template (never call the model)
    language: Optional[str] = None


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=1500)
    session_id: Optional[str] = None
    controls: Controls = Controls()
    conflict_choice: Optional[str] = Field(None, pattern="^(message|controls)$")


def chat_agent(request: Request) -> ChatAgent:
    app = request.app
    if getattr(app.state, "chat", None) is None:
        svc = getattr(app.state, "rag", None)
        if svc is None:
            raise HTTPException(503, "service not initialised")
        app.state.chat = ChatAgent(svc)
    return app.state.chat


@router.post("/api/chat")
def chat(body: ChatIn, request: Request):
    c = body.controls.model_dump()
    if c["point"] and not (isinstance(c["point"].get("lat"), (int, float)) and isinstance(c["point"].get("lon"), (int, float))):
        raise HTTPException(422, "controls.point must be {lat, lon} numbers")
    if c["bbox"] and len(c["bbox"]) != 4:
        raise HTTPException(422, "controls.bbox must have 4 numbers")
    for k in ("start", "end"):
        if c[k] and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", c[k]):
            raise HTTPException(422, f"controls.{k} must be YYYY-MM-DD")
    if c["task"] not in ("auto", "rag", "trend", "weather_forecast", "weather_historical", "fire_detections", "fire_danger", "satellite_scenes", "datasets", "land_surface_temperature", "ndvi", "forecast_monthly", "fire_outlook"):
        raise HTTPException(422, "unknown task")
    return strict(chat_agent(request).handle({"message": body.message, "session_id": body.session_id, "controls": c, "conflict_choice": body.conflict_choice}))


class ResetIn(BaseModel):
    session_id: str


@router.post("/api/chat/reset")
def chat_reset(body: ResetIn, request: Request):
    return {"reset": chat_agent(request).reset(body.session_id), "session_id": body.session_id}


@router.get("/api/chat/history")
def chat_history(request: Request, session_id: str = Query(...)):
    return {"session_id": session_id, "history": chat_agent(request).history(session_id)}


class ToolIn(BaseModel):
    args: dict = {}
    controls: Controls = Controls()
    language: str = "en"


@router.post("/api/tools/{name}")
def run_tool_directly(name: str, body: ToolIn):
    """Direct data exploration: no Claude involved, no chat session."""
    if name not in tools.TOOL_NAMES:
        raise HTTPException(404, f"unknown tool; available: {tools.TOOL_NAMES}")
    c = body.controls
    defaults: dict[str, Any] = {}
    if c.point:
        defaults["location"] = {"name": f"point ({c.point['lat']:.4f}, {c.point['lon']:.4f})", "latitude": float(c.point["lat"]), "longitude": float(c.point["lon"]), "source": "arguments"}
    elif c.bbox and len(c.bbox) == 4:
        defaults["location"] = {"name": "bounding box", "latitude": (c.bbox[1] + c.bbox[3]) / 2, "longitude": (c.bbox[0] + c.bbox[2]) / 2, "bbox": c.bbox, "source": "arguments"}
    if c.start and c.end:
        defaults["period"] = {"start": c.start, "end": c.end, "kind": "dates", "start_year": int(c.start[:4]), "end_year": int(c.end[:4])}
    out = tools.execute(name, body.args, defaults)
    return strict({"tool": name, "status": out["status"], "answer": render.render(name, out, body.language), "answer_source": "template", "artifacts": out["artifacts"],
                   "result": {k: v for k, v in out["result"].items() if k != "artifacts"}, "duration_ms": out["duration_ms"]})


_PREVIEW_HOSTS = {"datahub.creodias.eu", "zipper.creodias.eu", "gibs.earthdata.nasa.gov", "dataspace.copernicus.eu"}


@router.get("/api/preview")
def preview(u: str = Query(..., max_length=600)):
    """Same-origin proxy for scene thumbnails (allow-listed hosts, https only, size and type checked, nothing secret forwarded)."""
    p = urlparse(u)
    if p.scheme != "https" or p.hostname not in _PREVIEW_HOSTS:
        raise HTTPException(400, "host not allowed")
    r = None
    try:
        url = u
        for _ in range(4):                                   # follow redirects manually, but only to allow-listed https hosts
            r = httpx.get(url, timeout=httpx.Timeout(15, connect=5), follow_redirects=False)
            if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
                nxt = urlparse(httpx.URL(url).join(r.headers["location"]).__str__())
                if nxt.scheme != "https" or nxt.hostname not in _PREVIEW_HOSTS:
                    raise HTTPException(502, "preview redirect target not allowed")
                url = nxt.geturl()
                continue
            break
    except httpx.HTTPError:
        raise HTTPException(502, "preview unavailable")
    if r.status_code != 200 or len(r.content) > 5_000_000:
        raise HTTPException(502, f"preview unavailable (HTTP {r.status_code})")
    b = r.content
    ctype = "image/jpeg" if b[:3] == b"\xff\xd8\xff" else "image/png" if b[:8] == b"\x89PNG\r\n\x1a\n" else None
    if not ctype:
        raise HTTPException(502, "provider returned a non-image")
    return Response(b, media_type=ctype, headers={"Cache-Control": "public, max-age=3600"})


# ---- diagnostics (never quota-consuming unless the user presses a test button) ------------------------------------------------
@router.get("/api/diagnostics")
def diagnostics(request: Request):
    s = get_settings()
    svc = getattr(request.app.state, "rag", None)
    ut = UsageTracker(s.usage_file, s.llm_daily_cap)
    today = ut.today()
    now = time.time()
    exhausted = {m: round(ut.exhausted_until(m) - now) for m in [s.anthropic_model] if ut.exhausted_until(m) > now}
    health = svc.health() if svc else {}
    return strict({
        "backend": {"status": "ok" if svc else "not_initialised", "started_utc": STARTED.isoformat(timespec="seconds"), "python": platform.python_version(), "sessions": len(request.app.state.chat.store) if getattr(request.app.state, "chat", None) else 0,
                    "project_dir": str(PROJECT_DIR), "data_dir": str(s.data_dir), "log_file": str(s.data_dir / "server.log"), "env_files_found": len(_candidate_env_files())},
        "model": {"provider": "anthropic", "configured": s.anthropic_model, "allowed_models": ["claude-haiku-5-5"], "fallbacks": [], "api_key_configured": bool(load_llm_key()), "daily_cap_per_model_local": s.llm_daily_cap,
                  "usage_today": today, "exhausted_for_seconds": exhausted,
                  "note": "No Claude request is made by this page. Only claude-haiku-5-5 can ever be called; there is no fallback model. The test button spends one tiny request."},
        "knowledge_index": {"ready": health.get("index_ready"), "collections": health.get("collections"), "embedding_model": health.get("embedding_model")},
        "providers": registry.status(),
        "credentials": {n: has_credential(n) for n in ("ANTHROPIC_API_KEY", "FIRMS_MAP_KEY", "EARTHDATA_TOKEN", "EARTHDATA_USERNAME", "EARTHDATA_PASSWORD", "CDSE_CLIENT_ID", "CDSE_CLIENT_SECRET", "EE_PROJECT")},
        "limits": {"provider_total_deadline_s": s.provider_total_deadline_s, "request_total_deadline_s": s.request_total_deadline_s, "llm_total_deadline_s": s.llm_total_deadline_s},
    })


def _brief(r: dict) -> dict:
    return {"status": r.get("status"), "reason_code": r.get("reason_code"), "message": (r.get("message") or "")[:200], "live": r.get("live"), "cache": r.get("cache"),
            "product": r.get("product"), "tested_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def _next_month():
    t = date.today(); a = (t.replace(day=1) + timedelta(days=32)).replace(day=1); b = (a + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    return a, b


def _ewds_public():
    """Public catalogue only: availability of the dataset, with NO claim about the user's access rights."""
    t = time.monotonic(); a = fire_outlook.ewds_availability(False)
    return {"status": "ok", "live": True, "cache": None, "product": "CEMS fire seasonal (catalogue + constraints)", "reason_code": None, "message": f"latest start {a['latest_start']}, horizon {a['horizon_days']} d, {time.monotonic() - t:.1f}s (public; not an access check)"}


def _tests():
    from app.data_sources.power import fetch_power_monthly
    def power():
        t = time.monotonic(); s = fetch_power_monthly("T2M", 31.8, 35.2, 2020, 2021, use_cache=False)
        return {"status": "ok", "live": not s.source.get("cache_hit"), "cache": None, "product": "POWER monthly T2M 2020-2021", "reason_code": None, "message": f"{len(s.year)} monthly values, {time.monotonic() - t:.1f}s"}
    return {
        "power": power,
        "open_meteo": lambda: _brief(open_meteo.forecast(31.8, 35.2, 1)),
        "firms": lambda: _brief(firms.detections([34.9, 31.7, 35.4, 32.2], None, 1)),
        "gwis": lambda: _brief(fire_danger.gwis_products("fwi")),
        "usgs_fire": lambda: _brief(fire_danger.usgs_point(43.6, -116.2)),
        "copernicus": lambda: _brief(copernicus.search_scenes([31.0, 29.9, 31.2, 30.1], datetime.now(timezone.utc).strftime("%Y-%m-01"), datetime.now(timezone.utc).strftime("%Y-%m-%d"), "sentinel-2-l2a", 80, 1)),
        "earthdata": lambda: _brief(earthdata.search_collections("MOD11C3", limit=1)),
        "gee": lambda: _brief(gee.catalog_search("MOD11", limit=2)),
        "nifc": lambda: _brief(fire_outlook.nifc_outlook(40.5865, -122.3917, None, None, *_next_month(), date.today(), "en")),
        "ewds": lambda: _ewds_public(),
        # authentication checks are reported separately from data/analysis success
        "earthdata_token": lambda: _brief(earthdata.check_token_download()),
        "appeears_auth": lambda: _brief(earthdata.check_appeears_auth()),
        "cdse_oauth": lambda: _brief(copernicus.check_oauth()),
        "ewds_auth": lambda: _brief(fire_outlook.ewds_auth_check()),
        "ewds_data": lambda: _brief(fire_outlook.ewds_outlook(40.5865, -122.3917, None, *_next_month(), date.today())),
    }


@router.post("/api/diagnostics/test/{provider}")
def diagnostics_test(provider: str, request: Request):
    """Runs ONE small live call for a provider (user-triggered). provider='claude' spends one claude-haiku-5-5 request."""
    if provider == "claude":
        svc = request.app.state.rag
        t = time.monotonic()
        try:
            llm = svc._llm if svc._llm is not None else svc.llm
            r = llm.generate("Answer in one word.", "Reply OK.", max_output_tokens=16, retries=0)
            res = {"status": "ok", "live": True, "model": r.model, "message": f"{time.monotonic() - t:.1f}s", "reason_code": None, "tested_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        except LLMError as e:
            res = {"status": "blocked_provider", "reason_code": e.kind, "live": False, "message": str(e)[:200], "tested_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        registry.save_last_test("claude", res)
        return strict(res)
    fn = _tests().get(provider)
    if not fn:
        raise HTTPException(404, f"unknown provider; available: {list(_tests())} + claude")
    t = time.monotonic()
    try:
        res = fn()
    except Exception as e:
        res = {"status": "upstream_error", "reason_code": type(e).__name__, "message": "test raised an exception", "live": False}
    res["seconds"] = round(time.monotonic() - t, 1)
    res.setdefault("tested_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    registry.save_last_test(provider, res)
    return strict(res)


@router.get("/api/gibs/layers")
def gibs_layers():
    return {"layers": earthdata.gibs_layers(), "note": "GIBS layers are VISUALISATION only (rendered imagery), not analytical measurements."}


@router.get("/api/gibs/overlay")
def gibs_overlay(layer: str = Query(...), date: str = Query(...)):
    r = earthdata.gibs_overlay(layer, date)
    if r["status"] != "ok":
        raise HTTPException(400, r["message"])
    return strict({"artifact": r["artifacts"][0], "limitations": r["limitations"], "attribution": r["attribution"]})
