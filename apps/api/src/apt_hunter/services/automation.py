from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
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

APT_RELEVANT_CLASSIFICATIONS = frozenset({"apt_event", "actor_research"})
APT_EVENT_CLASSIFICATIONS = frozenset({"apt_event"})


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
    observables: list[dict[str, object]] | None = None
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


def _merge_observable_assessments(
    candidates: list[dict[str, object]], analysis: AIAnalysisPayload
) -> list[dict[str, object]]:
    assessments = {(item.type.casefold(), item.normalized): item for item in analysis.observables}
    merged: list[dict[str, object]] = []
    for candidate in candidates:
        key = (
            str(candidate.get("type", "")).casefold(),
            str(candidate.get("normalized", "")),
        )
        assessment = assessments.get(key)
        if assessment is None:
            merged.append(candidate)
            continue
        merged.append(
            {
                **candidate,
                "evidence": assessment.evidence,
                "confidence": assessment.confidence,
                "ai_disposition": assessment.disposition,
                "ai_role": assessment.role,
                "ai_confidence": assessment.confidence,
                "indicator_candidate": assessment.indicator_candidate,
                "indicator_purpose": assessment.purpose,
                "indicator_severity": assessment.severity,
                "indicator_ttl_days": assessment.ttl_days,
                "ai_decision_reason": assessment.decision_reason,
            }
        )
    return merged


def _int_value(value: object, fallback: int) -> int:
    return int(value) if isinstance(value, (int, float, str)) else fallback


def _fallback_outcome(
    *,
    deterministic: DiamondResult,
    policy_values: Mapping[str, object],
    initial_relevance_score: int,
    model_config_id: UUID | None,
    exception_type: str,
    exception_title: str,
    exception_description: str,
    exception_details: dict[str, object] | None = None,
) -> AutomationOutcome:
    has_threat_context = any(
        (
            deterministic.actors,
            deterministic.capabilities,
            deterministic.infrastructure,
            deterministic.victims,
            deterministic.attack_techniques,
        )
    )
    fallback_score = max(
        initial_relevance_score,
        deterministic.confidence if has_threat_context else 0,
    )
    return AutomationOutcome(
        enabled=True,
        automation_status="fallback",
        review_status="pending",
        report_status="candidate",
        method_version=f"ai-fallback:{PROMPT_VERSION}",
        model_config_id=model_config_id,
        relevance_score=fallback_score,
        classification="irrelevant",
        decision_reason=(
            "AI连续调用异常；本地提取只保留为候选证据，不会自动确认APT事件。"
            "系统已保留异常记录并等待自动重试。"
        ),
        confidence=deterministic.confidence,
        actors=deterministic.actors,
        capabilities=deterministic.capabilities,
        infrastructure=deterministic.infrastructure,
        victims=deterministic.victims,
        attack_techniques=deterministic.attack_techniques,
        observables=deterministic.observables,
        exception_type=exception_type,
        exception_title=exception_title,
        exception_description=exception_description,
        exception_details=exception_details or {},
    )


def _automation_decision(
    *,
    relevant: bool,
    relevance_score: int,
    classification: str,
    verified_confidence: int,
    verified_coverage: int,
    verification_approved: bool,
    contradictions: bool,
    verification_failed: bool,
    policy_values: Mapping[str, object],
) -> tuple[str, str, str, bool, bool, bool]:
    """Apply strict APT scope and evidence gates without unattended bypasses."""
    in_apt_scope = (
        classification in APT_RELEVANT_CLASSIFICATIONS
        and relevant
        and relevance_score >= _int_value(policy_values["relevance_threshold"], 60)
    )
    scope_conflict = (classification not in APT_RELEVANT_CLASSIFICATIONS and relevant) or (
        classification in APT_RELEVANT_CLASSIFICATIONS
        and not relevant
        and relevance_score >= _int_value(policy_values["relevance_threshold"], 60)
    )
    gates_approved = (
        in_apt_scope
        and verified_confidence >= _int_value(policy_values["auto_approve_threshold"], 85)
        and verified_coverage >= _int_value(policy_values["minimum_evidence_coverage"], 70)
        and verification_approved
        and not contradictions
        and not verification_failed
    )
    gates_rejected = (
        not in_apt_scope
        and not scope_conflict
        and relevance_score <= _int_value(policy_values["auto_reject_threshold"], 20)
        and verification_approved
        and not verification_failed
    )
    if gates_approved:
        return "auto_approved", "approved", "approved", True, False, scope_conflict
    if gates_rejected:
        return "auto_rejected", "rejected", "rejected", False, True, scope_conflict
    return "needs_review", "pending", "candidate", False, False, scope_conflict


def run_ai_automation(
    *,
    report_id: UUID,
    title: str,
    content: str,
    deterministic: DiamondResult,
    initial_relevance_score: int = 0,
) -> tuple[AutomationOutcome, list[dict[str, object]]]:
    with SessionLocal() as session:
        policy = get_or_create_policy(session)
        if not policy.automation_enabled:
            return AutomationOutcome(), deterministic.evidence
        config = default_model_config(session)
        policy_values = {
            "unattended_mode": policy.unattended_mode,
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
            _fallback_outcome(
                deterministic=deterministic,
                policy_values=policy_values,
                initial_relevance_score=initial_relevance_score,
                model_config_id=None,
                exception_type="model_not_configured",
                exception_title="AI自动化尚未配置默认模型",
                exception_description="报告已使用本地提取完成降级决策。",
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
        raw_analysis, latency_ms = analyze_with_model(
            config,
            title=title,
            content=scoped_content,
            observables=deterministic.observables,
        )
        grounded, local_coverage, rejected = ground_analysis(
            raw_analysis,
            scoped_content,
            deterministic.observables,
        )
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
            _fallback_outcome(
                deterministic=deterministic,
                policy_values=policy_values,
                initial_relevance_score=initial_relevance_score,
                model_config_id=config.id,
                exception_type="ai_processing_failed",
                exception_title="AI分析失败，已自动降级并安排重试",
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
    (
        automation_status,
        review_status,
        report_status,
        gates_approved,
        gates_rejected,
        scope_conflict,
    ) = _automation_decision(
        relevant=grounded.relevant,
        relevance_score=grounded.relevance_score,
        classification=grounded.classification,
        verified_confidence=verified_confidence,
        verified_coverage=verified_coverage,
        verification_approved=bool(verification.get("approved")),
        contradictions=contradictions,
        verification_failed=verification_failed,
        policy_values=policy_values,
    )
    unattended = bool(policy_values["unattended_mode"])

    exception_type: str | None = None
    exception_title: str | None = None
    exception_description: str | None = None
    gates_need_attention = not gates_approved and not gates_rejected
    if automation_status == "needs_review" or (unattended and gates_need_attention):
        if scope_conflict:
            exception_type = "apt_scope_conflict"
            exception_title = "AI分类与APT相关性冲突"
        elif verification_failed:
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
        exception_description = (
            f"无人值守模式已阻止不满足门禁的材料进入APT知识库：{grounded.decision_reason}"
            if unattended
            else grounded.decision_reason
        )

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
        actors=primary_actors,
        capabilities=_merge_entities(primary_capabilities, deterministic.capabilities),
        infrastructure=_merge_entities(primary_infrastructure, deterministic.infrastructure),
        victims=_merge_entities(primary_victims, deterministic.victims),
        attack_techniques=_merge_techniques(primary_techniques, deterministic.attack_techniques),
        observables=_merge_observable_assessments(
            deterministic.observables,
            grounded,
        ),
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


def retract_event_for_report(
    session: Session,
    report: Report,
    *,
    force: bool = False,
) -> None:
    """Retract an event when this report no longer supports it.

    Shared events stay confirmed while another approved report supports them.
    The event/report link is retained for auditability.
    """
    event_link = session.scalar(select(EventReport).where(EventReport.report_id == report.id))
    event = session.get(ThreatEvent, event_link.event_id) if event_link else None
    if event is None:
        return
    approved_support = int(
        session.scalar(
            select(func.count())
            .select_from(EventReport)
            .join(Report, Report.id == EventReport.report_id)
            .where(
                EventReport.event_id == event.id,
                EventReport.report_id != report.id,
                Report.status == "approved",
            )
        )
        or 0
    )
    if approved_support:
        sync_event_actors_from_reports(session, event.id)
        sync_event_knowledge(session, event.id)
        return
    if force or event.confidence_analyst is None:
        event.status = "rejected"
        event.version += 1


def apply_automation_decision(
    session: Session,
    *,
    report: Report,
    analysis: ReportAnalysis,
    outcome: AutomationOutcome,
) -> None:
    _resolve_stale_ai_exceptions(session, report, outcome)
    _record_exception(session, report, outcome)
    human_override = bool(
        analysis.reviewed_by
        and analysis.reviewed_by != "ai-automation"
        and any(
            value is not None
            for value in (
                analysis.reviewed_actors,
                analysis.reviewed_capabilities,
                analysis.reviewed_infrastructure,
                analysis.reviewed_victims,
            )
        )
    )
    if human_override:
        report.status = {
            "approved": "approved",
            "rejected": "rejected",
        }.get(analysis.review_status, "candidate")
        return
    if outcome.review_status == "pending":
        if analysis.reviewed_by == "ai-automation":
            analysis.review_status = "pending"
            analysis.reviewed_at = None
            analysis.reviewed_by = None
            analysis.version += 1
            report.status = "candidate"
            retract_event_for_report(session, report)
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
        retract_event_for_report(session, report)
        return
    if outcome.classification not in APT_EVENT_CLASSIFICATIONS:
        retract_event_for_report(session, report)
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
