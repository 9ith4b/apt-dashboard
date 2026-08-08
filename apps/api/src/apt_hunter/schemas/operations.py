from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OperationJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: str
    job_type: str
    subject_type: str
    subject_id: UUID
    status: Literal["queued", "running", "succeeded", "failed", "canceled"]
    progress: int
    attempt: int
    payload: dict[str, object]
    result: dict[str, object]
    error: str | None
    requested_by: str
    started_at: datetime | None
    finished_at: datetime | None
    parent_job_id: UUID | None
    version: int
    created_at: datetime
    updated_at: datetime
