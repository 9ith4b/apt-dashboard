from datetime import datetime
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
