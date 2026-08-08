from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

UserRole = Literal["viewer", "analyst", "admin"]


class LoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=1024)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if not normalized.replace("-", "").replace("_", "").replace(".", "").isalnum():
            raise ValueError("Username contains unsupported characters")
        return normalized


class UserRead(BaseModel):
    id: UUID
    username: str
    display_name: str
    role: UserRole
    enabled: bool
    last_login_at: datetime | None
    created_at: datetime


class AuthSessionRead(BaseModel):
    user: UserRead
    expires_at: datetime


class CsrfRead(BaseModel):
    csrf_token: str


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=100)
    display_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=12, max_length=1024)
    role: UserRole = "viewer"
    enabled: bool = True

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return LoginRequest.normalize_username(value)


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    password: str | None = Field(default=None, min_length=12, max_length=1024)
    role: UserRole | None = None
    enabled: bool | None = None


class AuditLogRead(BaseModel):
    id: UUID
    actor_user_id: UUID | None
    actor_username: str | None
    action: str
    object_type: str | None
    object_id: str | None
    result: str
    request_id: str
    ip_address: str
    details: dict[str, object]
    created_at: datetime
