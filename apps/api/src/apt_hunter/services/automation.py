from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from apt_hunter.db.session import SessionLocal
from apt_hunter.models import (
    AIAnalysisRun,
    AIModelConfig,
    AIProcessingPolicy,
    AnalysisRevision,
    AutomationException,
    EventReport,
    Report,
    ReportAnalysis,
    ThreatEvent,
)
from apt_hunter.services.actor_normalization import sync_event_actors_from_reports
from apt_hunter.services.ai_gateway import (
    PROMPT_VERSION,
    VERIFY_PROMPT_VERSION,
    AIAnalysisPayload,
    analyze_with_model,
    ground_analysis,
    verify_with_model,
)
from apt_hunter.services.diamond import DiamondResult
from apt_hunter.services.event_clustering import generate_merge_candidates
from apt_hunter.services.knowledge import sync_event_knowledge
from apt_hunter.services.watch_rules import evaluate_event_rules


@dataclass(slots=True)
class AutomationOutcome:
    enabled: bool = False
    automation_status: str = "not_configured"
    review_status: str = "pending"
    report_status: str = "candidate"
    method_version: str = "rules-v2"
    model_config_id: UUID | None = None
    relevance_score: int | None = None
    classification: str | None = None
    summary: str | None = None
    claims: list[dict[str, object]] = field(default_factory=list)
    verification: dict[str, object] = field(default_factory=dict)
    evidence_coverage: int | None = None
    decision_reason: str | None = None
    confidence: int | None = None
    actors: list[dict[str, object]] | None = None
    capabilities: list[dict[str, object]] | None = None
    infrastructure: list[dict[str, object]] | None = None
    victims: list[dict[str, object]] | None = None
    attack_techniques: list[dict[str, object]] | None = None
    exception_type: str | None = None
    exception_title: str | None = None
    exception_description: str | None = None
    exception_details: dict[str, object] = field(default_factory=dict)


def get_or_create_policy(session: Session) -> AIProcessingPolicy:
    policy = session.get(AIProcessingPolicy, "default")
    if policy is None:
        policy = AIProcessingPolicy(key="default")
        session.add(policy)
        session.flush()
    return policy


def automation_enabled(session: Session) -> bool:
    policy = session.get(AIProcessingPolicy, "default")
    return bool(policy and policy.automation_enabled)


def default_model_config(session: Session) -> AIModelConfig | None:
    return session.scalar(
        select(AIModelConfig)
        .where(AIModelConfig.enabled.is_(True), AIModelConfig.is_default.is_(True))
        .order_by(AIModelConfig.updated_at.desc())
        .limit(1)
    )


def _start_run(
    *, report_id: UUID, config: AIModelConfig, stage: str, prompt_version: str, input_chars: int
) -> UUID:
    with SessionLocal.begin() as session:
        run = AIAnalysisRun(
            report_id=report_id,
            model_config_id=config.id,
            stage=stage,
            status="running",
            model=config.model,
            prompt_version=prompt_version,
            input_chars=input_chars,
        )
        session.add(run)
        session.flush()
        return run.id


def _finish_run(
    run_id: UUID,
    *,
    result: dict[str, object] | None = None,
    error: Exception | None = None,
    latency_ms: int | None = None,
    decision: str | None = None,
    confidence: int | None = None,
    evidence_coverage: int | None = None,
) -> None:
    with SessionLocal.begin() as session:
        run = session.get(AIAnalysisRun, run_id)
        if run is None:
            return
        run.status = "failed" if error else "succeeded"
        run.result = result or {}
        run.error = str(error)[:4000] if error else None
        run.duration_ms = latency_ms
        run.decision = decision
        run.confidence = confidence
        run.evidence_coverage = evidence_coverage


def _merge_entities(
    primary: list[dict[str, object]], fallback: list[dict[str, object]]
) -> list[dict[str, object]]:
    merged: dict[tuple[str, str], dict[str, object]] = {}
    for item in [*primary, *fallback]:
        key = (str(item.get("type", "")).casefold(), str(item.get("name", "")).casefold())
        if key[1] and key not in merged:
            merged[key] = item
    return list(merged.values())


def _merge_techniques(
    primary: list[dict[str, object]], fallback: list[dict[str, object]]
) -> list[dict[str, object]]:
    merged: dict[str, dict[str, object]] = {}
    for item in [*primary, *fallback]:
        key = str(item.get("technique_id", "")).upper()
        if key and key not in merged:
            merged[key] = item
    return list(merged.values())


def _ai_evidence(analysis: AIAnalysisPayload) -> list[dict[str, object]]:
    dimensions = {
        "adversary": analysis.actors,
        "capability": analysis.capabilities,
        "infrastructure": analysis.infrastructure,
        "victim": analysis.victims,
    }
    evidence: list[dict[str, object]] = []
    for dimension, items in dimensions.items():
        for item in items:
            evidence.append(
                {
                    "dimension": dimension,
                    "entity": item.name,
                    "quote": item.evidence,
                }
            )
    return evidence[:80]


def _int_value(value: object, fallback: int) -> int:
    return int(value) if isinstance(value, (int, float, str)) else fallback


def run_ai_automation(
    *,
    report_id: UUID,
    title: str,
    content: str,
    deterministic: DiamondResult,
) -> tuple[AutomationOutcome, list[dict[str, object]]]:
    with SessionLocal() as session:
        policy = get_or_create_policy(session)
        if not policy.automation_enabled:
            return AutomationOutcome(), deterministic.evidence
        config = default_model_config(session)
        policy_values = {
            "require_verification": policy.require_verification,
            "relevance_threshold": policy.relevance_threshold,
            "auto_approve_threshold": policy.auto_approve_threshold,
            "auto_reject_threshold": policy.auto_reject_threshold,
            "minimum_evidence_coverage": policy.minimum_evidence_coverage,
            "max_article_chars": policy.max_article_chars,
        }
        if config is not None:
            session.expunge(config)

    if config is None:
        return (
            AutomationOutcome(
                enabled=True,
                automation_status="fallback",
                exception_type="model_not_configured",
                exception_title="AI自动化尚未配置默认模型",
                exception_description="报告已使用确定性提取安全降级，需要配置并测试默认模型。",
            ),
            deterministic.evidence,
        )

    scoped_content = content[: int(policy_values["max_article_chars"])]
    run_id = _start_run(
        report_id=report_id,
        config=config,
        stage="analysis",
        prompt_version=PROMPT_VERSION,
        input_chars=len(scoped_content),
    )
    try:
        raw_analysis, latency_ms = analyze_with_model(config, title=title, content=scoped_content)
        grounded, local_coverage, rejected = ground_analysis(raw_analysis, scoped_content)
        _finish_run(
            run_id,
            result=grounded.model_dump(mode="json"),
            latency_ms=latency_ms,
            decision="relevant" if grounded.relevant else "irrelevant",
            confidence=grounded.confidence,
            evidence_coverage=local_coverage,
        )
    except Exception as exc:
        _finish_run(run_id, error=exc)
        return (
            AutomationOutcome(
                enabled=True,
                automation_status="fallback",
                model_config_id=config.id,
                method_version=f"ai-fallback:{PROMPT_VERSION}",
                exception_type="ai_processing_failed",
                exception_title="AI分析失败，已安全降级",
                exception_description=str(exc)[:1000],
                exception_details={"model": config.model},
            ),
            deterministic.evidence,
        )

    verification: dict[str, object] = {
        "approved": True,
        "confidence": grounded.confidence,
        "evidence_coverage": local_coverage,
        "issues": [],
        "contradiction_found": False,
        "decision_reason": "未启用独立验证模型",
    }
    verification_failed = False
    if bool(policy_values["require_verification"]):
        verify_run_id = _start_run(
            report_id=report_id,
            config=config,
            stage="verification",
            prompt_version=VERIFY_PROMPT_VERSION,
            input_chars=len(scoped_content),
        )
        try:
            checked, verify_latency = verify_with_model(
                config,
                title=title,
                content=scoped_content,
                analysis=grounded,
            )
            verification = checked.model_dump(mode="json")
            _finish_run(
                verify_run_id,
                result=verification,
                latency_ms=verify_latency,
                decision="approved" if checked.approved else "rejected",
                confidence=checked.confidence,
                evidence_coverage=checked.evidence_coverage,
            )
        except Exception as exc:
            verification_failed = True
            verification = {
                "approved": False,
                "confidence": 0,
                "evidence_coverage": local_coverage,
                "issues": [f"独立验证失败：{str(exc)[:500]}"],
                "contradiction_found": False,
                "decision_reason": "验证阶段失败，禁止自动确认",
            }
            _finish_run(verify_run_id, error=exc)

    verified_coverage = min(
        local_coverage,
        _int_value(verification.get("evidence_coverage"), local_coverage),
    )
    verified_confidence = min(
        grounded.confidence,
        _int_value(verification.get("confidence"), grounded.confidence),
    )
    contradictions = bool(grounded.contradictions) or bool(verification.get("contradiction_found"))
    auto_approved = (
        grounded.relevant
        and grounded.relevance_score >= int(policy_values["relevance_threshold"])
        and verified_confidence >= int(policy_values["auto_approve_threshold"])
        and verified_coverage >= int(policy_values["minimum_evidence_coverage"])
        and bool(verification.get("approved"))
        and not contradictions
        and not verification_failed
    )
    auto_rejected = (
        not grounded.relevant
        and grounded.relevance_score <= int(policy_values["auto_reject_threshold"])
        and bool(verification.get("approved"))
        and not verification_failed
    )
    if auto_approved:
        automation_status = "auto_approved"
        review_status = "approved"
        report_status = "approved"
    elif auto_rejected:
        automation_status = "auto_rejected"
        review_status = "rejected"
        report_status = "rejected"
    else:
        automation_status = "needs_review"
        review_status = "pending"
        report_status = "candidate"

    exception_type: str | None = None
    exception_title: str | None = None
    exception_description: str | None = None
    if automation_status == "needs_review":
        if verification_failed:
            exception_type = "ai_verification_failed"
            exception_title = "AI验证阶段失败"
        elif contradictions:
            exception_type = "attribution_conflict"
            exception_title = "AI发现归因或证据冲突"
        elif verified_coverage < int(policy_values["minimum_evidence_coverage"]):
            exception_type = "evidence_gap"
            exception_title = "证据覆盖不足"
        else:
            exception_type = "low_confidence"
            exception_title = "AI置信度不足"
        exception_description = grounded.decision_reason

    primary_actors = [item.model_dump(mode="json") for item in grounded.actors]
    primary_capabilities = [item.model_dump(mode="json") for item in grounded.capabilities]
    primary_infrastructure = [item.model_dump(mode="json") for item in grounded.infrastructure]
    primary_victims = [item.model_dump(mode="json") for item in grounded.victims]
    primary_techniques = [item.model_dump(mode="json") for item in grounded.attack_techniques]
    outcome = AutomationOutcome(
        enabled=True,
        automation_status=automation_status,
        review_status=review_status,
        report_status=report_status,
        method_version=f"ai:{PROMPT_VERSION}",
        model_config_id=config.id,
        relevance_score=grounded.relevance_score,
        classification=grounded.classification,
        summary=grounded.summary,
        claims=[item.model_dump(mode="json") for item in grounded.claims],
        verification=verification,
        evidence_coverage=verified_coverage,
        decision_reason=grounded.decision_reason,
        confidence=verified_confidence,
        actors=_merge_entities(primary_actors, deterministic.actors),
        capabilities=_merge_entities(primary_capabilities, deterministic.capabilities),
        infrastructure=_merge_entities(primary_infrastructure, deterministic.infrastructure),
        victims=_merge_entities(primary_victims, deterministic.victims),
        attack_techniques=_merge_techniques(primary_techniques, deterministic.attack_techniques),
        exception_type=exception_type,
        exception_title=exception_title,
        exception_description=exception_description,
        exception_details={
            "rejected_ungrounded_items": rejected,
            "verification_issues": verification.get("issues", []),
            "relevance_score": grounded.relevance_score,
            "confidence": verified_confidence,
            "evidence_coverage": verified_coverage,
        },
    )
    return outcome, [*deterministic.evidence, *_ai_evidence(grounded)][:100]


def _record_exception(session: Session, report: Report, outcome: AutomationOutcome) -> None:
    if not outcome.exception_type:
        return
    existing = session.scalar(
        select(AutomationException)
        .where(
            AutomationException.report_id == report.id,
            AutomationException.exception_type == outcome.exception_type,
            AutomationException.status == "open",
        )
        .limit(1)
    )
    if existing is not None:
        existing.description = outcome.exception_description or existing.description
        existing.details = outcome.exception_details
        return
    session.add(
        AutomationException(
            report_id=report.id,
            exception_type=outcome.exception_type,
            severity="high" if "conflict" in outcome.exception_type else "medium",
            title=outcome.exception_title or "AI自动化需要人工研判",
            description=outcome.exception_description or "自动化门禁未满足。",
            details=outcome.exception_details,
        )
    )


def _resolve_stale_ai_exceptions(
    session: Session, report: Report, outcome: AutomationOutcome
) -> None:
    """Close failures superseded by a successful retry of the same report."""
    stale = session.scalars(
        select(AutomationException).where(
            AutomationException.report_id == report.id,
            AutomationException.status == "open",
            AutomationException.exception_type.in_(
                ("ai_processing_failed", "ai_verification_failed")
            ),
            AutomationException.exception_type != outcome.exception_type,
        )
    ).all()
    for item in stale:
        item.status = "resolved"
        item.resolved_by = "ai-automation"
        item.resolved_at = datetime.now(UTC)


def apply_automation_decision(
    session: Session,
    *,
    report: Report,
    analysis: ReportAnalysis,
    outcome: AutomationOutcome,
) -> None:
    _resolve_stale_ai_exceptions(session, report, outcome)
    _record_exception(session, report, outcome)
    if outcome.review_status == "pending":
        return
    now = datetime.now(UTC)
    analysis.review_status = outcome.review_status
    analysis.reviewed_at = now
    analysis.reviewed_by = "ai-automation"
    analysis.version += 1
    report.status = outcome.report_status
    session.add(
        AnalysisRevision(
            report_id=report.id,
            review_version=analysis.version,
            decision=outcome.review_status,
            snapshot={
                "automation_status": outcome.automation_status,
                "confidence_auto": outcome.confidence,
                "evidence_coverage": outcome.evidence_coverage,
                "claims": outcome.claims,
            },
            analyst_note=outcome.decision_reason,
            reviewed_by="ai-automation",
        )
    )
    if outcome.review_status != "approved":
        return
    policy = get_or_create_policy(session)
    if not policy.auto_create_events:
        return
    observed_at = report.published_at or report.created_at
    event_link = session.scalar(select(EventReport).where(EventReport.report_id == report.id))
    event = session.get(ThreatEvent, event_link.event_id) if event_link else None
    if event is None:
        event = ThreatEvent(
            title=report.title,
            summary=outcome.summary or report.normalized_text or analysis.content_text[:1000],
            status="confirmed",
            confidence_auto=outcome.confidence,
            first_seen=observed_at,
            last_seen=observed_at,
        )
        session.add(event)
        session.flush()
        session.add(EventReport(event_id=event.id, report_id=report.id, evidence_role="primary"))
        session.flush()
    else:
        event.title = report.title
        event.summary = outcome.summary or report.normalized_text or analysis.content_text[:1000]
        event.status = "confirmed"
        event.confidence_auto = outcome.confidence
        event.first_seen = observed_at
        event.last_seen = observed_at
        event.version += 1
    sync_event_actors_from_reports(session, event.id)
    sync_event_knowledge(session, event.id)
    generate_merge_candidates(session, event.id)
    evaluate_event_rules(session, event.id)
