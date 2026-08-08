from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WatchConditions(BaseModel):
    keywords: list[str] = Field(default_factory=list, max_length=20)
    actor_names: list[str] = Field(default_factory=list, max_length=20)
    observable_types: list[str] = Field(default_factory=list, max_length=10)
    technique_ids: list[str] = Field(default_factory=list, max_length=20)
    min_confidence: int | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def require_condition(self) -> "WatchConditions":
        if not any(
            (
                self.keywords,
                self.actor_names,
                self.observable_types,
                self.technique_ids,
                self.min_confidence is not None,
            )
        ):
            raise ValueError("At least one watch condition is required")
        return self


class WatchRuleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=2000)
    conditions: WatchConditions
    severity: Literal["info", "low", "medium", "high", "critical"] = "medium"
    enabled: bool = True
    created_by: str = Field(default="analyst", min_length=2, max_length=100)


class WatchRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    conditions: WatchConditions | None = None
    severity: Literal["info", "low", "medium", "high", "critical"] | None = None
    enabled: bool | None = None
    expected_version: int = Field(ge=1)


class WatchRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str
    conditions: WatchConditions
    severity: str
    enabled: bool
    created_by: str
    version: int
    hit_count: int = 0
    created_at: datetime
    updated_at: datetime


class WatchRuleHitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rule_id: UUID
    subject_type: str
    subject_id: UUID
    subject_title: str
    matched_on: dict[str, object]
    created_at: datetime


class WatchRulePreviewRead(BaseModel):
    rule_id: UUID | None = None
    match_count: int
    matches: list[WatchRuleHitRead]


class WatchRuleEvaluationRead(BaseModel):
    rule_id: UUID
    evaluated_count: int
    created_hit_count: int
    hit_count: int


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hit_id: UUID | None
    title: str
    message: str
    severity: str
    target_type: str
    target_id: UUID | None
    read_at: datetime | None
    created_at: datetime


class NotificationListRead(BaseModel):
    unread_count: int
    items: list[NotificationRead]
