from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    title: str
    canonical_url: str
    language: str
    relevance_score: int
    relevance_reasons: list[str]
    status: str
    published_at: datetime | None
    created_at: datetime
