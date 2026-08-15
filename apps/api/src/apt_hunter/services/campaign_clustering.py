from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from apt_hunter.models import (
    AIModelConfig,
    AIProcessingPolicy,
    Campaign,
    CampaignEvent,
    EventActor,
    EventObservable,
    EventReport,
    EventTechnique,
    Observable,
    OperationJob,
    ReportAnalysis,
    ThreatActor,
    ThreatEvent,
)
from apt_hunter.services.ai_gateway import AICampaignDecision, analyze_campaign_with_model
from apt_hunter.services.watch_rules import evaluate_event_rules

CAMPAIGN_ENGINE_VERSION = "campaign-clustering-v1"
MIN_EVENT_CONFIDENCE = 70
MIN_CANDIDATE_SCORE = 45
MIN_JOIN_CONFIDENCE = 70
MIN_CREATE_CONFIDENCE = 75
RECENT_DECISION_WINDOW = timedelta(hours=24)
_TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{2,}", re.IGNORECASE)


@dataclass(slots=True)
class EventFacts:
    event: ThreatEvent
    actor_ids: set[UUID] = field(default_factory=set)
    actor_names: set[str] = field(default_factory=set)
    observables: set[str] = field(default_factory=set)
    techniques: set[str] = field(default_factory=set)
    victims: set[str] = field(default_factory=set)

    def as_prompt(self) -> dict[str, object]:
        return {
            "id": str(self.event.id),
            "title": self.event.title,
            "summary": self.event.summary[:2000],
            "first_seen": _iso(self.event.first_seen or self.event.created_at),
            "last_seen": _iso(
                self.event.last_seen or self.event.first_seen or self.event.created_at
            ),
            "actors": sorted(self.actor_names),
            "observables": sorted(self.observables)[:50],
            "techniques": sorted(self.techniques),
            "victims": sorted(self.victims)[:30],
        }


@dataclass(frozen=True, slots=True)
class ScoredEvent:
    facts: EventFacts
    score: int
    features: dict[str, object]

    def as_prompt(self) -> dict[str, object]:
        return {
            **self.facts.as_prompt(),
            "similarity_score": self.score,
            "link_features": self.features,
        }


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _tokens(value: str) -> set[str]:
    return {match.group(0).casefold() for match in _TOKEN_PATTERN.finditer(value)}


def _title_similarity(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def score_campaign_relation(
    source: EventFacts, target: EventFacts
) -> tuple[int, dict[str, object]]:
    actor_overlap = len(source.actor_ids & target.actor_ids)
    observable_overlap = len(source.observables & target.observables)
    technique_overlap = len(source.techniques & target.techniques)
    victim_overlap = len(source.victims & target.victims)
    source_date = source.event.first_seen or source.event.created_at
    target_date = target.event.first_seen or target.event.created_at
    date_distance_days = abs((source_date - target_date).days)
    title_similarity = _title_similarity(source.event.title, target.event.title)
    score = (
        (30 if actor_overlap else 0)
        + min(30, observable_overlap * 15)
        + min(15, technique_overlap * 5)
        + min(10, victim_overlap * 5)
        + (7 if date_distance_days <= 30 else 3 if date_distance_days <= 180 else 0)
        + min(8, round(title_similarity * 8))
    )
    features: dict[str, object] = {
        "actor_overlap": actor_overlap,
        "observable_overlap": observable_overlap,
        "technique_overlap": technique_overlap,
        "victim_overlap": victim_overlap,
        "date_distance_days": date_distance_days,
        "title_similarity": round(title_similarity, 3),
    }
    return min(100, score), features


def _is_candidate(score: int, features: dict[str, object]) -> bool:
    if score < MIN_CANDIDATE_SCORE or int(features["actor_overlap"]) < 1:
        return False
    return bool(
        int(features["observable_overlap"])
        or int(features["technique_overlap"])
        or int(features["victim_overlap"])
        or float(features["title_similarity"]) >= 0.2
    )


def _load_event_facts(session: Session, events: list[ThreatEvent]) -> dict[UUID, EventFacts]:
    facts = {event.id: EventFacts(event=event) for event in events}
    ids = list(facts)
    if not ids:
        return facts
    for event_id, actor_id, actor_name in session.execute(
        select(EventActor.event_id, EventActor.actor_id, ThreatActor.canonical_name)
        .join(ThreatActor, ThreatActor.id == EventActor.actor_id)
        .where(EventActor.event_id.in_(ids))
    ):
        facts[event_id].actor_ids.add(actor_id)
        facts[event_id].actor_names.add(actor_name)
    for event_id, observable_type, observable_value in session.execute(
        select(
            EventObservable.event_id,
            Observable.type,
            Observable.value_normalized,
        )
        .join(Observable, Observable.id == EventObservable.observable_id)
        .where(EventObservable.event_id.in_(ids))
    ):
        facts[event_id].observables.add(f"{observable_type}:{observable_value}")
    for event_id, technique_id in session.execute(
        select(EventTechnique.event_id, EventTechnique.technique_id).where(
            EventTechnique.event_id.in_(ids)
        )
    ):
        facts[event_id].techniques.add(technique_id)
    for event_id, analysis in session.execute(
        select(EventReport.event_id, ReportAnalysis)
        .join(ReportAnalysis, ReportAnalysis.report_id == EventReport.report_id)
        .where(EventReport.event_id.in_(ids))
    ):
        entities = (
            analysis.reviewed_victims if analysis.reviewed_victims is not None else analysis.victims
        )
        facts[event_id].victims.update(
            str(item.get("name", "")).strip().casefold() for item in entities if item.get("name")
        )
    return facts


def _event_confidence(event: ThreatEvent) -> int:
    return event.confidence_analyst or event.confidence_auto or 0


def _eligible(facts: EventFacts) -> bool:
    event = facts.event
    return bool(
        event.status == "confirmed"
        and event.superseded_by_id is None
        and _event_confidence(event) >= MIN_EVENT_CONFIDENCE
        and facts.actor_ids
        and (facts.observables or facts.techniques)
    )


def _default_model_config(session: Session) -> AIModelConfig | None:
    return session.scalar(
        select(AIModelConfig)
        .where(AIModelConfig.enabled.is_(True), AIModelConfig.is_default.is_(True))
        .order_by(AIModelConfig.updated_at.desc())
        .limit(1)
    )


def _refresh_campaign_bounds(session: Session, campaign: Campaign) -> None:
    events = list(
        session.scalars(
            select(ThreatEvent)
            .join(CampaignEvent, CampaignEvent.event_id == ThreatEvent.id)
            .where(CampaignEvent.campaign_id == campaign.id)
        )
    )
    first_values = [event.first_seen or event.created_at for event in events]
    last_values = [event.last_seen or event.first_seen or event.created_at for event in events]
    campaign.first_seen = min(first_values) if first_values else None
    campaign.last_seen = max(last_values) if last_values else None


def _unique_campaign_name(session: Session, requested: str, source: EventFacts) -> str:
    base = " ".join(requested.split())[:300]
    if not base:
        actor = sorted(source.actor_names)[0]
        observed = source.event.first_seen or source.event.created_at
        base = f"{actor} 持续攻击活动 · {observed:%Y-%m}"
    candidate = base
    suffix = 2
    while session.scalar(
        select(Campaign.id).where(func.lower(Campaign.name) == candidate.casefold())
    ):
        marker = f" · {suffix}"
        candidate = f"{base[: 300 - len(marker)]}{marker}"
        suffix += 1
    return candidate


def _membership_note(decision: AICampaignDecision, score: int) -> str:
    reason = decision.evidence_note or decision.decision_reason or "结构化关联信号满足归类条件"
    return (
        f"AI自动归类（{CAMPAIGN_ENGINE_VERSION}，候选关联度 {score}%，"
        f"模型置信度 {decision.confidence}%）：{reason}"
    )[:5000]


def _assign(
    session: Session,
    *,
    campaign: Campaign,
    event_id: UUID,
    decision: AICampaignDecision,
    score: int,
) -> bool:
    existing = session.get(CampaignEvent, (campaign.id, event_id))
    if existing is not None:
        return False
    session.add(
        CampaignEvent(
            campaign_id=campaign.id,
            event_id=event_id,
            stage=decision.stage,
            confidence=decision.confidence,
            evidence_note=_membership_note(decision, score),
            reviewed_at=datetime.now(UTC),
            reviewed_by=CAMPAIGN_ENGINE_VERSION,
        )
    )
    campaign.version += 1
    return True


def _independent(reason: str, *, candidates: int = 0) -> dict[str, object]:
    return {
        "status": "independent",
        "reason": reason,
        "candidate_count": candidates,
        "engine_version": CAMPAIGN_ENGINE_VERSION,
    }


def cluster_event(session: Session, event_id: UUID) -> dict[str, object]:
    event = session.get(ThreatEvent, event_id)
    if event is None:
        return {"status": "skipped", "reason": "event_not_found"}
    existing_membership = session.scalar(
        select(CampaignEvent).where(CampaignEvent.event_id == event_id).limit(1)
    )
    if existing_membership is not None:
        return {
            "status": "already_assigned",
            "campaign_id": str(existing_membership.campaign_id),
        }

    peers = list(
        session.scalars(
            select(ThreatEvent)
            .where(
                ThreatEvent.id != event_id,
                ThreatEvent.status == "confirmed",
                ThreatEvent.superseded_by_id.is_(None),
            )
            .order_by(ThreatEvent.last_seen.desc().nullslast(), ThreatEvent.created_at.desc())
            .limit(500)
        )
    )
    facts_by_id = _load_event_facts(session, [event, *peers])
    source = facts_by_id[event_id]
    if not _eligible(source):
        return {
            "status": "skipped",
            "reason": "event_not_eligible",
            "confidence": _event_confidence(event),
        }

    scored: list[ScoredEvent] = []
    for peer in peers:
        target = facts_by_id[peer.id]
        if not _eligible(target):
            continue
        score, features = score_campaign_relation(source, target)
        if _is_candidate(score, features):
            scored.append(ScoredEvent(target, score, features))
    scored.sort(key=lambda item: item.score, reverse=True)
    scored = scored[:12]
    if not scored:
        return _independent("没有满足最低证据门槛的关联事件")

    peer_ids = [item.facts.event.id for item in scored]
    membership_rows = list(
        session.execute(
            select(CampaignEvent.event_id, CampaignEvent.campaign_id).where(
                CampaignEvent.event_id.in_(peer_ids)
            )
        )
    )
    peer_campaigns: dict[UUID, set[UUID]] = defaultdict(set)
    for peer_id, campaign_id in membership_rows:
        peer_campaigns[peer_id].add(campaign_id)

    campaign_scores: dict[UUID, ScoredEvent] = {}
    for candidate in scored:
        for campaign_id in peer_campaigns[candidate.facts.event.id]:
            current = campaign_scores.get(campaign_id)
            if current is None or candidate.score > current.score:
                campaign_scores[campaign_id] = candidate
    campaigns = {
        campaign.id: campaign
        for campaign in session.scalars(
            select(Campaign).where(
                Campaign.id.in_(list(campaign_scores)), Campaign.status == "active"
            )
        )
    }
    campaign_prompt = [
        {
            "id": str(campaign_id),
            "name": campaigns[campaign_id].name,
            "description": campaigns[campaign_id].description[:1500],
            "best_member_similarity": candidate.score,
            "link_features": candidate.features,
            "representative_event": candidate.facts.as_prompt(),
        }
        for campaign_id, candidate in sorted(
            campaign_scores.items(), key=lambda item: item[1].score, reverse=True
        )
        if campaign_id in campaigns
    ][:5]
    unassigned_candidates = [
        candidate for candidate in scored if not peer_campaigns[candidate.facts.event.id]
    ][:8]
    model_config = _default_model_config(session)
    if model_config is None:
        return {
            "status": "deferred",
            "reason": "default_model_not_configured",
            "candidate_count": len(scored),
        }
    decision, latency_ms = analyze_campaign_with_model(
        model_config,
        event=source.as_prompt(),
        campaign_candidates=campaign_prompt,
        event_candidates=[candidate.as_prompt() for candidate in unassigned_candidates],
    )

    if decision.action == "join_existing" and decision.confidence >= MIN_JOIN_CONFIDENCE:
        try:
            campaign_id = UUID(decision.campaign_id or "")
        except ValueError:
            return _independent("AI返回了无效的Campaign ID", candidates=len(scored))
        campaign = campaigns.get(campaign_id)
        candidate = campaign_scores.get(campaign_id)
        if campaign is None or candidate is None:
            return _independent("AI选择的Campaign不在候选范围内", candidates=len(scored))
        changed = _assign(
            session,
            campaign=campaign,
            event_id=event_id,
            decision=decision,
            score=candidate.score,
        )
        session.flush()
        _refresh_campaign_bounds(session, campaign)
        if changed:
            evaluate_event_rules(session, event_id)
        return {
            "status": "assigned",
            "campaign_id": str(campaign.id),
            "campaign_name": campaign.name,
            "confidence": decision.confidence,
            "latency_ms": latency_ms,
            "engine_version": CAMPAIGN_ENGINE_VERSION,
        }

    if decision.action == "create_new" and decision.confidence >= MIN_CREATE_CONFIDENCE:
        allowed = {str(item.facts.event.id): item for item in unassigned_candidates}
        selected = [
            allowed[item_id] for item_id in decision.related_event_ids if item_id in allowed
        ]
        if not selected and unassigned_candidates:
            selected = [unassigned_candidates[0]]
        if not selected:
            return _independent("没有可用于新建Campaign的独立关联事件", candidates=len(scored))
        campaign = Campaign(
            name=_unique_campaign_name(session, decision.campaign_name, source),
            description=(decision.description or decision.decision_reason)[:10000],
            status="active",
        )
        session.add(campaign)
        session.flush()
        changed_ids: list[UUID] = []
        source_score = max(item.score for item in selected)
        if _assign(
            session,
            campaign=campaign,
            event_id=event_id,
            decision=decision,
            score=source_score,
        ):
            changed_ids.append(event_id)
        for candidate in selected:
            if _assign(
                session,
                campaign=campaign,
                event_id=candidate.facts.event.id,
                decision=decision,
                score=candidate.score,
            ):
                changed_ids.append(candidate.facts.event.id)
        session.flush()
        _refresh_campaign_bounds(session, campaign)
        for changed_id in changed_ids:
            evaluate_event_rules(session, changed_id)
        return {
            "status": "created",
            "campaign_id": str(campaign.id),
            "campaign_name": campaign.name,
            "event_count": len(changed_ids),
            "confidence": decision.confidence,
            "latency_ms": latency_ms,
            "engine_version": CAMPAIGN_ENGINE_VERSION,
        }

    return _independent(
        decision.decision_reason or "AI判定当前证据不足以归入持续攻击活动",
        candidates=len(scored),
    )


def pending_campaign_event_ids(
    session: Session,
    *,
    limit: int,
    force: bool = False,
) -> list[UUID]:
    active_job = exists().where(
        OperationJob.job_type == "campaign_clustering",
        OperationJob.subject_type == "event",
        OperationJob.subject_id == ThreatEvent.id,
        OperationJob.status.in_(["queued", "running"]),
    )
    statement = select(ThreatEvent.id).where(
        ThreatEvent.status == "confirmed",
        ThreatEvent.superseded_by_id.is_(None),
        func.coalesce(ThreatEvent.confidence_analyst, ThreatEvent.confidence_auto, 0)
        >= MIN_EVENT_CONFIDENCE,
        exists().where(EventActor.event_id == ThreatEvent.id),
        (
            exists().where(EventObservable.event_id == ThreatEvent.id)
            | exists().where(EventTechnique.event_id == ThreatEvent.id)
        ),
        ~exists().where(CampaignEvent.event_id == ThreatEvent.id),
        ~active_job,
    )
    if not force:
        recent_job = exists().where(
            OperationJob.job_type == "campaign_clustering",
            OperationJob.subject_type == "event",
            OperationJob.subject_id == ThreatEvent.id,
            OperationJob.created_at >= datetime.now(UTC) - RECENT_DECISION_WINDOW,
        )
        statement = statement.where(~recent_job)
    return list(
        session.scalars(
            statement.order_by(
                ThreatEvent.last_seen.desc().nullslast(), ThreatEvent.created_at.desc()
            ).limit(limit)
        )
    )


def campaign_automation_ready(session: Session) -> bool:
    policy = session.get(AIProcessingPolicy, "default")
    return bool(
        policy
        and policy.automation_enabled
        and policy.unattended_mode
        and _default_model_config(session) is not None
    )
