from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apt_hunter.db.session import get_db
from apt_hunter.models import (
    AIAnalysisRun,
    AIModelConfig,
    AIProcessingPolicy,
    AutomationException,
    Report,
    ReportAnalysis,
)
from apt_hunter.schemas.automation import (
    AIModelConfigCreate,
    AIModelConfigRead,
    AIModelConfigUpdate,
    AIModelTestRead,
    AIProcessingPolicyRead,
    AIProcessingPolicyUpdate,
    AutomationExceptionDecision,
    AutomationExceptionRead,
    AutomationStatusRead,
    BackfillRead,
)
from apt_hunter.services.ai_gateway import test_model_connection
from apt_hunter.services.auth import AuthPrincipal
from apt_hunter.services.automation import default_model_config, get_or_create_policy
from apt_hunter.services.secrets import encrypt_secret

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


def _actor(request: Request) -> str:
    principal = getattr(request.state, "principal", None)
    return principal.username if isinstance(principal, AuthPrincipal) else "local-admin"


def _config_or_404(session: Session, config_id: UUID) -> AIModelConfig:
    config = session.get(AIModelConfig, config_id)
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型配置不存在")
    return config


def _config_read(config: AIModelConfig) -> AIModelConfigRead:
    return AIModelConfigRead(
        id=config.id,
        name=config.name,
        provider=config.provider,
        base_url=config.base_url,
        model=config.model,
        has_api_key=bool(config.api_key_ciphertext),
        enabled=config.enabled,
        is_default=config.is_default,
        timeout_seconds=config.timeout_seconds,
        temperature=config.temperature,
        updated_by=config.updated_by,
        last_test_status=config.last_test_status,
        last_test_error=config.last_test_error,
        last_tested_at=config.last_tested_at,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


def _policy_read(policy: AIProcessingPolicy) -> AIProcessingPolicyRead:
    return AIProcessingPolicyRead.model_validate(policy, from_attributes=True)


@router.get("/configs", response_model=list[AIModelConfigRead])
def list_model_configs(session: DbSession) -> list[AIModelConfigRead]:
    configs = session.scalars(
        select(AIModelConfig).order_by(AIModelConfig.is_default.desc(), AIModelConfig.name)
    )
    return [_config_read(config) for config in configs]


@router.post("/configs", response_model=AIModelConfigRead, status_code=status.HTTP_201_CREATED)
def create_model_config(
    payload: AIModelConfigCreate,
    request: Request,
    session: DbSession,
) -> AIModelConfigRead:
    if payload.is_default:
        session.execute(update(AIModelConfig).values(is_default=False))
    config = AIModelConfig(
        name=payload.name.strip(),
        provider=payload.provider,
        base_url=str(payload.base_url).rstrip("/"),
        model=payload.model.strip(),
        api_key_ciphertext=encrypt_secret(payload.api_key) if payload.api_key else None,
        enabled=payload.enabled,
        is_default=payload.is_default,
        timeout_seconds=payload.timeout_seconds,
        temperature=payload.temperature,
        updated_by=_actor(request),
    )
    session.add(config)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="模型配置名称已存在"
        ) from exc
    session.refresh(config)
    return _config_read(config)


@router.patch("/configs/{config_id}", response_model=AIModelConfigRead)
def update_model_config(
    config_id: UUID,
    payload: AIModelConfigUpdate,
    request: Request,
    session: DbSession,
) -> AIModelConfigRead:
    config = _config_or_404(session, config_id)
    changes = payload.model_dump(exclude_unset=True)
    clear_api_key = bool(changes.pop("clear_api_key", False))
    api_key = changes.pop("api_key", None)
    if changes.get("is_default") is True:
        session.execute(
            update(AIModelConfig).where(AIModelConfig.id != config.id).values(is_default=False)
        )
    for field, value in changes.items():
        if field == "base_url" and value is not None:
            value = str(value).rstrip("/")
        if field in {"name", "model"} and isinstance(value, str):
            value = value.strip()
        setattr(config, field, value)
    if clear_api_key:
        config.api_key_ciphertext = None
    elif api_key:
        config.api_key_ciphertext = encrypt_secret(str(api_key))
    if config.provider != "ollama" and not config.api_key_ciphertext:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="云端模型必须配置 API Key",
        )
    config.updated_by = _actor(request)
    config.last_test_status = None
    config.last_test_error = None
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="模型配置名称已存在"
        ) from exc
    session.refresh(config)
    return _config_read(config)


@router.delete("/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model_config(config_id: UUID, session: DbSession) -> None:
    config = _config_or_404(session, config_id)
    policy = get_or_create_policy(session)
    if config.is_default and policy.automation_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="请先停用AI自动化或切换默认模型",
        )
    session.delete(config)
    session.commit()


@router.post("/configs/{config_id}/test", response_model=AIModelTestRead)
def test_config(config_id: UUID, session: DbSession) -> AIModelTestRead:
    config = _config_or_404(session, config_id)
    run = AIAnalysisRun(
        model_config_id=config.id,
        stage="connection_test",
        status="running",
        model=config.model,
        prompt_version="connection-test-v1",
    )
    session.add(run)
    session.commit()
    try:
        latency_ms, message = test_model_connection(config)
        config.last_test_status = "succeeded"
        config.last_test_error = None
        run.status = "succeeded"
        run.duration_ms = latency_ms
        run.result = {"message": message}
        result = AIModelTestRead(
            ok=True, message=message, latency_ms=latency_ms, model=config.model
        )
    except Exception as exc:
        config.last_test_status = "failed"
        config.last_test_error = str(exc)[:2000]
        run.status = "failed"
        run.error = str(exc)[:4000]
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"模型连接测试失败：{str(exc)[:500]}",
        ) from exc
    finally:
        config.last_tested_at = datetime.now(UTC)
        session.commit()
    return result


@router.get("/policy", response_model=AIProcessingPolicyRead)
def get_policy(session: DbSession) -> AIProcessingPolicyRead:
    policy = get_or_create_policy(session)
    session.commit()
    session.refresh(policy)
    return _policy_read(policy)


@router.put("/policy", response_model=AIProcessingPolicyRead)
def update_policy(
    payload: AIProcessingPolicyUpdate,
    request: Request,
    session: DbSession,
) -> AIProcessingPolicyRead:
    if payload.automation_enabled:
        active = default_model_config(session)
        if active is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="启用自动化前必须配置一个已启用的默认模型",
            )
        if active.last_test_status != "succeeded":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="启用自动化前必须通过默认模型连接测试",
            )
    policy = get_or_create_policy(session)
    for field, value in payload.model_dump().items():
        setattr(policy, field, value)
    policy.updated_by = _actor(request)
    session.commit()
    session.refresh(policy)
    return _policy_read(policy)


@router.post("/backfill", response_model=BackfillRead)
def backfill_filtered_reports(session: DbSession) -> BackfillRead:
    policy = get_or_create_policy(session)
    if not policy.automation_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="请先启用AI自动化")
    report_ids_with_analysis = select(ReportAnalysis.report_id)
    result = session.execute(
        update(Report)
        .where(Report.status == "filtered", Report.id.not_in(report_ids_with_analysis))
        .values(status="candidate")
    )
    session.commit()
    return BackfillRead(promoted=int(getattr(result, "rowcount", 0) or 0))


@router.get("/status", response_model=AutomationStatusRead)
def automation_status(session: DbSession) -> AutomationStatusRead:
    policy = get_or_create_policy(session)
    active = default_model_config(session)
    cutoff = datetime.now(UTC) - timedelta(hours=24)

    def count_analysis(status_value: str | None = None) -> int:
        statement = (
            select(func.count())
            .select_from(ReportAnalysis)
            .where(ReportAnalysis.updated_at >= cutoff)
        )
        if status_value:
            statement = statement.where(ReportAnalysis.automation_status == status_value)
        return int(session.scalar(statement) or 0)

    return AutomationStatusRead(
        automation_enabled=policy.automation_enabled,
        active_model_name=active.name if active else None,
        active_model=active.model if active else None,
        open_exceptions=int(
            session.scalar(
                select(func.count())
                .select_from(AutomationException)
                .where(AutomationException.status == "open")
            )
            or 0
        ),
        processed_24h=count_analysis(),
        auto_approved_24h=count_analysis("auto_approved"),
        needs_review_24h=count_analysis("needs_review"),
        failed_24h=int(
            session.scalar(
                select(func.count())
                .select_from(AIAnalysisRun)
                .where(
                    AIAnalysisRun.status == "failed",
                    AIAnalysisRun.created_at >= cutoff,
                )
            )
            or 0
        ),
    )


@router.get("/exceptions", response_model=list[AutomationExceptionRead])
def list_exceptions(
    session: DbSession,
    exception_status: Literal["open", "resolved", "dismissed"] = "open",
    limit: int = Query(default=100, ge=1, le=200),
) -> list[AutomationExceptionRead]:
    rows = session.execute(
        select(AutomationException, Report.title)
        .outerjoin(Report, Report.id == AutomationException.report_id)
        .where(AutomationException.status == exception_status)
        .order_by(AutomationException.created_at.desc())
        .limit(limit)
    )
    return [
        AutomationExceptionRead(
            id=item.id,
            report_id=item.report_id,
            report_title=report_title,
            exception_type=item.exception_type,
            severity=item.severity,
            status=item.status,
            title=item.title,
            description=item.description,
            details=item.details,
            assigned_to=item.assigned_to,
            resolved_by=item.resolved_by,
            resolved_at=item.resolved_at,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item, report_title in rows
    ]


@router.post("/exceptions/{exception_id}/decision", response_model=AutomationExceptionRead)
def decide_exception(
    exception_id: UUID,
    payload: AutomationExceptionDecision,
    session: DbSession,
) -> AutomationExceptionRead:
    item = session.get(AutomationException, exception_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="异常不存在")
    if item.status != "open":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="异常已处理")
    item.status = payload.status
    item.resolved_by = payload.resolved_by
    item.resolved_at = datetime.now(UTC)
    session.commit()
    session.refresh(item)
    report_title = session.scalar(select(Report.title).where(Report.id == item.report_id))
    return AutomationExceptionRead(
        id=item.id,
        report_id=item.report_id,
        report_title=report_title,
        exception_type=item.exception_type,
        severity=item.severity,
        status=item.status,
        title=item.title,
        description=item.description,
        details=item.details,
        assigned_to=item.assigned_to,
        resolved_by=item.resolved_by,
        resolved_at=item.resolved_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
