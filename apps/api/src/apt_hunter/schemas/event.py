from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

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
    created_at: datetime
    updated_at: datetime


class ThreatEventDetail(ThreatEventSummary):
    diamond: EventDiamond
    reports: list[ReportSummary]
