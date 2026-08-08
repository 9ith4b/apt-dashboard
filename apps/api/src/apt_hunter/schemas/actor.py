from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class ActorEventRead(BaseModel):
    id: UUID
    title: str
    summary: str
    status: str
    confidence: int | None
    first_seen: datetime | None
    last_seen: datetime | None
    reported_name: str


class ActorTimelineBucket(BaseModel):
    key: str
    label: str
    event_count: int


class ThreatActorSummary(BaseModel):
    id: UUID
    canonical_name: str
    aliases: list[str]
    origin_country: str | None
    event_count: int
    first_seen: datetime | None
    last_seen: datetime | None
    latest_event_id: UUID | None
    latest_event_title: str | None


class ThreatActorDetail(ThreatActorSummary):
    description: str
    events: list[ActorEventRead]
    timeline: list[ActorTimelineBucket]


class ActorTrackingPeriod(BaseModel):
    date_from: date
    date_to: date
    previous_from: date
    previous_to: date
    day_count: int
    bucket: Literal["day", "week", "month"]


class ActorTrackingComparison(BaseModel):
    current_event_count: int
    previous_event_count: int
    absolute_change: int
    percentage_change: float | None


class ActorTrackingChangeSet(BaseModel):
    category: Literal["malware", "infrastructure", "techniques", "targets"]
    current_values: list[str]
    previous_values: list[str]
    new_values: list[str]
    disappeared_values: list[str]


class ActorTrackingRead(BaseModel):
    actor_id: UUID
    canonical_name: str
    period: ActorTrackingPeriod
    comparison: ActorTrackingComparison
    trend: list[ActorTimelineBucket]
    changes: list[ActorTrackingChangeSet]
    events: list[ActorEventRead]


class ActorTrackingSummaryRead(BaseModel):
    actor_id: UUID
    status: Literal["draft"] = "draft"
    title: str
    summary: str
    highlights: list[str]
    caveats: list[str]
    supporting_event_ids: list[UUID]
    supporting_evidence_ids: list[UUID]
    generated_at: datetime
    method_version: str = "tracking-rules-v1"
