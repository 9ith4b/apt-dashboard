from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class IndicatorSummary(BaseModel):
    id: UUID
    purpose: str
    valid_from: datetime
    valid_until: datetime
    confidence: int
    severity: str
    revoked: bool
    reviewed_by: str
    version: int


class ObservableSummary(BaseModel):
    id: UUID
    type: str
    value_original: str
    value_normalized: str
    scope: str
    validation_status: str
    first_seen: datetime | None
    last_seen: datetime | None
    report_count: int
    event_count: int
    evidence_count: int
    ai_disposition: Literal["malicious", "suspicious", "benign", "context"] | None = None
    ai_role: str | None = None
    ai_confidence: int | None = None
    ai_decision_reason: str | None = None
    ai_decided_at: datetime | None = None
    indicator: IndicatorSummary | None


class ObservableReportAppearance(BaseModel):
    report_id: UUID
    report_title: str
    source_name: str
    published_at: datetime | None
    confidence: int
    evidence_id: UUID
    evidence: str


class ObservableEventAppearance(BaseModel):
    event_id: UUID
    event_title: str
    first_seen: datetime | None
    confidence: int
    evidence_id: UUID
    evidence: str


class ObservableEnrichmentRead(BaseModel):
    id: UUID
    provider: str
    status: str
    queried_at: datetime
    expires_at: datetime
    result: dict[str, object]
    error: str | None


class ObservableDetail(ObservableSummary):
    reports: list[ObservableReportAppearance]
    events: list[ObservableEventAppearance]
    enrichments: list[ObservableEnrichmentRead]


class ObservablePromote(BaseModel):
    purpose: str = Field(min_length=3, max_length=500)
    valid_from: datetime
    valid_until: datetime
    confidence: int = Field(ge=0, le=100)
    severity: Literal["info", "low", "medium", "high", "critical"]
    evidence_ids: list[UUID] = Field(min_length=1)
    reviewed_by: str = Field(default="local-analyst", min_length=1, max_length=100)


class IndicatorRead(IndicatorSummary):
    observable_id: UUID
    observable_type: str
    value_normalized: str
    pattern: str
    reviewed_at: datetime
    evidence_ids: list[UUID]


class IndicatorUpdate(BaseModel):
    expected_version: int = Field(ge=1)
    purpose: str | None = Field(default=None, min_length=3, max_length=500)
    valid_until: datetime | None = None
    confidence: int | None = Field(default=None, ge=0, le=100)
    severity: Literal["info", "low", "medium", "high", "critical"] | None = None
    revoked: bool | None = None
    corrected_by: str = Field(default="local-analyst", min_length=1, max_length=100)
