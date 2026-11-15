from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

ALLOWED_FILTERS = {"variables", "service_id", "source_role", "source_file", "dataset_ids", "language", "provider"}


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    language: Optional[Literal["ar", "en"]] = Field(
        None, description="Answer language. Default: Arabic; English only when requested here or in the question.")
    top_k: int = Field(5, ge=1, le=10)
    scope: Literal["earth_knowledge", "gemini_platform"] = "earth_knowledge"
    filters: Optional[dict] = Field(None, description=f"Metadata filters. Allowed keys: {sorted(ALLOWED_FILTERS)}")
    debug: bool = False

    @field_validator("filters")
    @classmethod
    def _check_filters(cls, v):
        if v:
            bad = set(v) - ALLOWED_FILTERS
            if bad:
                raise ValueError(f"unsupported filter keys: {sorted(bad)}")
        return v


class SourceOut(BaseModel):
    index: int
    source_file: str
    document_title: str
    section: str
    page: Optional[int] = None
    dataset_ids: list[str] = []
    dataset_name: Optional[str] = None
    service_id: Optional[str] = None
    original_url: Optional[str] = None
    provider: Optional[str] = None
    score: Optional[float] = None
    cited: bool
    snippet: str
    text: Optional[str] = None


class IntentOut(BaseModel):
    kind: str
    required_tools: list[str] = []
    reasons: list[str] = []


class QueryResponse(BaseModel):
    answer: str
    answer_type: Literal["document_answer", "insufficient_knowledge", "requires_data_tool", "tool_analysis"]
    language: Literal["ar", "en"]
    intent: IntentOut
    sources: list[SourceOut]
    retrieval: dict
    llm: dict = {}
    answer_source: Optional[Literal["claude", "template"]] = None
    fallback_reason: Optional[str] = None
    warnings: list[str] = []
    analysis: Optional[dict] = Field(None, description="Full analyze_trend result (incl. chart spec) when answer_type == 'tool_analysis'")


class TrendAskRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=1000)
    language: Literal["ar", "en"] = "ar"


class TrendAskResponse(BaseModel):
    answer: str
    answer_source: Literal["claude", "template"]
    fallback_reason: Optional[str] = None
    status: str
    analysis: Optional[dict] = None
    tool_calls: list[dict] = []
    warnings: list[str] = []
    llm: dict = {}


class IngestRequest(BaseModel):
    reset: bool = Field(False, description="Drop and rebuild the selected collections.")
    force: bool = Field(False, description="Re-embed even if a source is unchanged.")
    include_resources: bool = True
    collections: Optional[list[Literal["earth_knowledge", "gemini_platform"]]] = None


class IngestResponse(BaseModel):
    report: dict


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    components: dict
    problems: list[str] = []
