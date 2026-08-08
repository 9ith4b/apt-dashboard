from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class DiamondEntity(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    type: str = Field(min_length=1, max_length=100)
    confidence: int = Field(ge=0, le=100)
    evidence: str = Field(default="", max_length=5000)


class ReportSummary(BaseModel):
    id: UUID
    source_id: UUID
    source_name: str
    title: str
    canonical_url: str
    language: str
    summary: str
    relevance_score: int
    relevance_reasons: list[str]
    status: str
    published_at: datetime | None
    created_at: datetime
    extraction_status: str | None
    review_status: str | None
    confidence_auto: int | None


class AnalysisRead(BaseModel):
    extraction_status: str
    review_status: str
    content_text: str
    final_url: str | None
    content_type: str | None
    fetched_at: datetime | None
    extraction_error: str | None
    actors: list[DiamondEntity]
    capabilities: list[DiamondEntity]
    infrastructure: list[DiamondEntity]
    victims: list[DiamondEntity]
    evidence: list[dict[str, object]]
    reviewed_actors: list[DiamondEntity] | None
    reviewed_capabilities: list[DiamondEntity] | None
    reviewed_infrastructure: list[DiamondEntity] | None
    reviewed_victims: list[DiamondEntity] | None
    confidence_auto: int | None
    method_version: str
    analyst_note: str | None
    reviewed_at: datetime | None
    reviewed_by: str | None
    version: int
    updated_at: datetime


class ReportDetail(ReportSummary):
    analysis: AnalysisRead | None


class ReportTaskQueued(BaseModel):
    task_id: str
    report_id: UUID
    status: Literal["queued"] = "queued"


class ReviewDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    analyst_note: str | None = Field(default=None, max_length=5000)
    expected_version: int = Field(ge=1)
    reviewed_by: str = Field(default="local-analyst", min_length=1, max_length=100)
    actors: list[DiamondEntity] | None = None
    capabilities: list[DiamondEntity] | None = None
    infrastructure: list[DiamondEntity] | None = None
    victims: list[DiamondEntity] | None = None
    event_title: str | None = Field(default=None, min_length=1, max_length=500)
    confidence_analyst: int | None = Field(default=None, ge=0, le=100)


class AnalysisRevisionRead(BaseModel):
    id: UUID
    report_id: UUID
    review_version: int
    decision: Literal["approved", "rejected"]
    snapshot: dict[str, object]
    analyst_note: str | None
    reviewed_by: str
    created_at: datetime
