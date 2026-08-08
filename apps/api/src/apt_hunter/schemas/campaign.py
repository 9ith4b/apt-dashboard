from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

CampaignStatus = Literal["active", "inactive", "closed"]
CampaignStage = Literal[
    "unknown",
    "reconnaissance",
    "resource-development",
    "initial-access",
    "execution",
    "persistence",
    "privilege-escalation",
    "defense-evasion",
    "credential-access",
    "discovery",
    "lateral-movement",
    "collection",
    "command-and-control",
    "exfiltration",
    "impact",
]


class CampaignSummary(BaseModel):
    id: UUID
    name: str
    description: str
    first_seen: datetime | None
    last_seen: datetime | None
    status: CampaignStatus
    event_count: int
    actor_names: list[str]
    stages: list[str]
    version: int
    created_at: datetime
    updated_at: datetime


class CampaignEventRead(BaseModel):
    event_id: UUID
    event_title: str
    event_summary: str
    event_first_seen: datetime | None
    event_last_seen: datetime | None
    stage: str
    confidence: int
    evidence_note: str
    reviewed_at: datetime
    reviewed_by: str
    actor_names: list[str]


class CampaignDetail(CampaignSummary):
    events: list[CampaignEventRead]


class CampaignCreate(BaseModel):
    name: str = Field(min_length=3, max_length=300)
    description: str = Field(default="", max_length=10000)
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    status: CampaignStatus = "active"


class CampaignUpdate(BaseModel):
    expected_version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=3, max_length=300)
    description: str | None = Field(default=None, max_length=10000)
    status: CampaignStatus | None = None


class CampaignEventUpsert(BaseModel):
    event_id: UUID
    stage: CampaignStage = "unknown"
    confidence: int = Field(ge=0, le=100)
    evidence_note: str = Field(min_length=3, max_length=5000)
    expected_version: int = Field(ge=1)
    reviewed_by: str = Field(default="local-analyst", min_length=1, max_length=100)
