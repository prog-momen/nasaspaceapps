"""FastAPI app. Run:  uvicorn app.api.main:app --port 8000"""
from __future__ import annotations

import dataclasses
import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.schemas import (HealthResponse, IngestRequest, IngestResponse, IntentOut, QueryRequest,
                             QueryResponse, SourceOut, TrendAskRequest, TrendAskResponse)
from app.tools.trend_tool import TrendRequest, run_trend_analysis
from app.config import setup_logging
from app.llm.gemini_client import BudgetExceeded, LLMError
from app.rag.service import RagService

log = logging.getLogger("app.api")


def get_service(request: Request) -> RagService:
    svc = getattr(request.app.state, "rag", None)
    if svc is None:
        raise HTTPException(503, "RAG service is not initialised.")
    return svc


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    if not hasattr(app.state, "rag") or app.state.rag is None:
        app.state.rag = RagService()
    yield
    app.state.rag.store.close()


app = FastAPI(title="EarthTrend Explorer RAG", version="0.1.0", lifespan=lifespan)


@app.exception_handler(LLMError)
async def llm_error_handler(_: Request, exc: LLMError):
    return JSONResponse(status_code=exc.status, content={"detail": str(exc), "error": "llm_error"})


@app.exception_handler(RuntimeError)
async def runtime_handler(_: Request, exc: RuntimeError):
    log.error("runtime error: %s", exc)
    return JSONResponse(status_code=409, content={"detail": str(exc), "error": "index_error"})


@app.post("/api/rag/query", response_model=QueryResponse)
def query(req: QueryRequest, svc: RagService = Depends(get_service)):
    if not svc.health()["index_ready"] and req.scope == "earth_knowledge":
        raise HTTPException(409, "Knowledge index is empty. Call POST /api/rag/ingest first.")
    r = svc.answer(req.question, language=req.language, top_k=req.top_k, filters=req.filters, scope=req.scope)
    retrieval = r.retrieval if req.debug else {k: r.retrieval[k] for k in ("collection", "returned", "filters") if k in r.retrieval}
    return QueryResponse(
        answer=r.answer, answer_type=r.answer_type, language=r.language,
        intent=IntentOut(kind=r.intent.kind, required_tools=r.intent.required_tools, reasons=r.intent.reasons),
        sources=[SourceOut(**dataclasses.asdict(s)) for s in r.sources],
        retrieval=retrieval, llm=r.llm, warnings=r.warnings, analysis=r.analysis)


def _admin(x_admin_token: str | None = Header(default=None)):
    expected = os.environ.get("RAG_ADMIN_TOKEN")
    if expected and x_admin_token != expected:
        raise HTTPException(401, "Invalid admin token.")


@app.post("/api/rag/ingest", response_model=IngestResponse, dependencies=[Depends(_admin)])
def ingest(req: IngestRequest, svc: RagService = Depends(get_service)):
    """Ingests only the allow-listed project resources (see app/ingestion/registry.py); no arbitrary paths/URLs."""
    rep = svc.ingest(reset=req.reset, force=req.force, include_resources=req.include_resources,
                     collections=req.collections)
    return IngestResponse(report=rep)


@app.get("/api/rag/health", response_model=HealthResponse)
def health(svc: RagService = Depends(get_service)):
    h = svc.health()
    problems = []
    if not h["index_ready"]:
        problems.append("knowledge index is empty (run ingestion)")
    if not h["gemini_key_configured"]:
        problems.append("GEMINI_API_KEY is not configured")
    return HealthResponse(status="ok" if not problems else "degraded", components=h, problems=problems)


@app.post("/api/analysis/trend")
def trend(req: TrendRequest):
    """Deterministic Mann-Kendall / Sen's slope analysis (no LLM). Always returns a structured result with `status`."""
    return run_trend_analysis(req.model_dump())


@app.post("/api/analysis/trend/ask", response_model=TrendAskResponse)
def trend_ask(req: TrendAskRequest, svc: RagService = Depends(get_service)):
    """Gemini function calling: the model calls analyze_trend, the backend runs it, Gemini explains the result."""
    a = svc.trend_ask(req.question, req.language)
    return TrendAskResponse(answer=a.answer, answer_source=a.answer_source, status=a.status, analysis=a.analysis,
                            tool_calls=a.tool_calls, warnings=a.warnings, llm=a.llm)
