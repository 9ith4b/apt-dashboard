from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator

SourceType = Literal["rss", "web", "x", "telegram"]
SECRET_REFS = {
    "x": "APT_HUNTER_X_BEARER_TOKEN",
    "telegram": "APT_HUNTER_TELEGRAM_BOT_TOKEN",
}


def _validate_connector(
    source_type: SourceType,
    url: AnyHttpUrl | str | None,
    config: dict[str, object],
    secret_ref: str | None,
) -> None:
    sensitive_keys = {
        key
        for key in config
        if any(word in key.casefold() for word in ("token", "secret", "password"))
    }
    if sensitive_keys:
        raise ValueError("Connector secrets must use secret_ref, not config fields")
    if source_type in {"rss", "web"} and url is None:
        raise ValueError("RSS and Web sources require an HTTP(S) URL")
    if source_type == "x" and not str(config.get("query", "")).strip():
        raise ValueError("X sources require config.query")
    if source_type == "telegram" and not config.get("chat_ids"):
        raise ValueError("Telegram sources require config.chat_ids")
    expected_ref = SECRET_REFS.get(source_type)
    if expected_ref and secret_ref != expected_ref:
        raise ValueError(f"{source_type} sources require secret_ref={expected_ref}")


class SourceCreate(BaseModel):
    type: SourceType = "rss"
    name: str = Field(min_length=2, max_length=200)
    url: AnyHttpUrl | None = None
    config: dict[str, object] = Field(default_factory=dict)
    secret_ref: str | None = Field(default=None, max_length=255)
    enabled: bool = True
    poll_interval_minutes: int = Field(default=60, ge=5, le=1440)

    @model_validator(mode="after")
    def validate_connector(self) -> "SourceCreate":
        _validate_connector(self.type, self.url, self.config, self.secret_ref)
        return self


class SourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    url: AnyHttpUrl | None = None
    config: dict[str, object] | None = None
    secret_ref: str | None = Field(default=None, max_length=255)
    enabled: bool | None = None
    poll_interval_minutes: int | None = Field(default=None, ge=5, le=1440)


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    name: str
    url: str | None
    config: dict[str, object]
    credential_configured: bool = False
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
