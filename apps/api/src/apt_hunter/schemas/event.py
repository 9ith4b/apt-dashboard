from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from apt_hunter.schemas.report import DiamondEntity, ReportSummary


class EventDiamond(BaseModel):
    actors: list[DiamondEntity]
    capabilities: list[DiamondEntity]
    infrastructure: list[DiamondEntity]
    victims: list[DiamondEntity]


class ThreatEventSummary(BaseModel):
    id: UUID
    title: str
    summary: str
    status: str
    confidence_auto: int | None
    confidence_analyst: int | None
    first_seen: datetime | None
    last_seen: datetime | None
    report_count: int
    actor_names: list[str]
    observable_count: int
    technique_ids: list[str]
    superseded_by_id: UUID | None
    created_at: datetime
    updated_at: datetime


class EventObservableRead(BaseModel):
    id: UUID
    type: str
    value_original: str
    value_normalized: str
    scope: str
    confidence: int
    evidence_id: UUID
    evidence: str
    first_seen: datetime | None
    last_seen: datetime | None


class EventTechniqueRead(BaseModel):
    technique_id: str
    name: str
    tactic: str | None
    confidence: int
    evidence_id: UUID
    evidence: str


class ThreatEventDetail(ThreatEventSummary):
    diamond: EventDiamond
    reports: list[ReportSummary]
    observables: list[EventObservableRead]
    attack_techniques: list[EventTechniqueRead]


class MergeEventRef(BaseModel):
    id: UUID
    title: str
    first_seen: datetime | None
    report_count: int


class EventMergeCandidateRead(BaseModel):
    id: UUID
    source_event: MergeEventRef
    target_event: MergeEventRef
    score: int
    features: dict[str, object]
    status: str
    decision_reason: str | None
    moved_report_ids: list[str]
    reviewed_at: datetime | None
    version: int
    created_at: datetime


class EventMergeDecision(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    reason: str | None = Field(default=None, max_length=5000)
    expected_version: int = Field(ge=1)


class EventMergeUndo(BaseModel):
    expected_version: int = Field(ge=1)
