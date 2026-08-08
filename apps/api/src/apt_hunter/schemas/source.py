from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class SourceCreate(BaseModel):
    type: Literal["rss"] = "rss"
    name: str = Field(min_length=2, max_length=200)
    url: AnyHttpUrl
    enabled: bool = True
    poll_interval_minutes: int = Field(default=60, ge=5, le=1440)


class SourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    url: AnyHttpUrl | None = None
    enabled: bool | None = None
    poll_interval_minutes: int | None = Field(default=None, ge=5, le=1440)


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    name: str
    url: str | None
    enabled: bool
    health_status: str
    poll_interval_minutes: int
    last_checked_at: datetime | None
    last_success_at: datetime | None
    next_poll_at: datetime | None
    last_error: str | None
    consecutive_failures: int
    report_count: int = 0
    created_at: datetime
    updated_at: datetime


class TaskQueued(BaseModel):
    task_id: str
    source_id: UUID
    status: Literal["queued"] = "queued"
