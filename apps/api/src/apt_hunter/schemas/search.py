from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class SearchResultRead(BaseModel):
    kind: Literal["actor", "event", "observable", "report"]
    id: UUID
    title: str
    subtitle: str
    url: str
    score: int


class SearchResponse(BaseModel):
    query: str
    total: int
    results: list[SearchResultRead]
