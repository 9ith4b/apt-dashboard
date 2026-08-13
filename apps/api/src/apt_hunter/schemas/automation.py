from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, model_validator

AIProvider = Literal["openai", "deepseek", "dashscope", "siliconflow", "ollama", "custom"]


class AIModelConfigCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    provider: AIProvider
    base_url: HttpUrl
    model: str = Field(min_length=1, max_length=200)
    api_key: str | None = Field(default=None, max_length=2000)
    enabled: bool = True
    is_default: bool = False
    timeout_seconds: int = Field(default=90, ge=5, le=300)
    temperature: float = Field(default=0.1, ge=0, le=2)

    @model_validator(mode="after")
    def require_cloud_credential(self) -> "AIModelConfigCreate":
        if self.provider != "ollama" and not self.api_key:
            raise ValueError("云端模型必须配置 API Key")
        return self


class AIModelConfigUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    provider: AIProvider | None = None
    base_url: HttpUrl | None = None
    model: str | None = Field(default=None, min_length=1, max_length=200)
    api_key: str | None = Field(default=None, max_length=2000)
    clear_api_key: bool = False
    enabled: bool | None = None
    is_default: bool | None = None
    timeout_seconds: int | None = Field(default=None, ge=5, le=300)
    temperature: float | None = Field(default=None, ge=0, le=2)


class AIModelConfigRead(BaseModel):
    id: UUID
    name: str
    provider: AIProvider
    base_url: str
    model: str
    has_api_key: bool
    enabled: bool
    is_default: bool
    timeout_seconds: int
    temperature: float
    updated_by: str
    last_test_status: str | None
    last_test_error: str | None
    last_tested_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AIModelTestRead(BaseModel):
    ok: bool
    message: str
    latency_ms: int
    model: str


class AIProcessingPolicyUpdate(BaseModel):
    automation_enabled: bool
    unattended_mode: bool = True
    require_verification: bool = True
    auto_create_events: bool = True
    auto_manage_indicators: bool = True
    indicator_auto_threshold: int = Field(default=80, ge=0, le=100)
    relevance_threshold: int = Field(ge=0, le=100)
    auto_approve_threshold: int = Field(ge=0, le=100)
    auto_reject_threshold: int = Field(ge=0, le=100)
    minimum_evidence_coverage: int = Field(ge=0, le=100)
    max_article_chars: int = Field(ge=5000, le=200000)

    @model_validator(mode="after")
    def validate_thresholds(self) -> "AIProcessingPolicyUpdate":
        if self.auto_reject_threshold >= self.relevance_threshold:
            raise ValueError("自动排除阈值必须低于相关性阈值")
        if self.auto_approve_threshold < self.relevance_threshold:
            raise ValueError("自动确认阈值不能低于相关性阈值")
        return self


class AIProcessingPolicyRead(AIProcessingPolicyUpdate):
    updated_by: str
    updated_at: datetime


class AutomationStatusRead(BaseModel):
    automation_enabled: bool
    active_model_name: str | None
    active_model: str | None
    open_exceptions: int
    processed_24h: int
    auto_approved_24h: int
    needs_review_24h: int
    failed_24h: int


class AutomationExceptionRead(BaseModel):
    id: UUID
    report_id: UUID | None
    report_title: str | None
    exception_type: str
    severity: Literal["low", "medium", "high", "critical"]
    status: Literal["open", "resolved", "dismissed"]
    title: str
    description: str
    details: dict[str, object]
    assigned_to: str | None
    resolved_by: str | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AutomationExceptionDecision(BaseModel):
    status: Literal["resolved", "dismissed"]
    resolved_by: str = Field(min_length=1, max_length=100)


class BackfillRead(BaseModel):
    promoted: int
