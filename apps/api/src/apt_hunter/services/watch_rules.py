from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from apt_hunter.models import (
    CampaignEvent,
    EventActor,
    EventObservable,
    EventTechnique,
    Notification,
    Observable,
    ThreatActor,
    ThreatEvent,
    WatchRule,
    WatchRuleHit,
)
from apt_hunter.schemas.watch import WatchConditions, WatchRuleHitRead


@dataclass(frozen=True, slots=True)
class EventContext:
    id: UUID
    title: str
    summary: str
    confidence: int
    campaign_ids: tuple[UUID, ...]
    actor_names: tuple[str, ...]
    observable_types: tuple[str, ...]
    observable_values: tuple[str, ...]
    technique_ids: tuple[str, ...]


def event_contexts(session: Session, event_ids: list[UUID] | None = None) -> list[EventContext]:
    statement = select(ThreatEvent).where(
        ThreatEvent.status == "confirmed",
        ThreatEvent.superseded_by_id.is_(None),
    )
    if event_ids is not None:
        if not event_ids:
            return []
        statement = statement.where(ThreatEvent.id.in_(event_ids))
    events = list(session.scalars(statement.order_by(ThreatEvent.created_at.desc())))
    ids = [event.id for event in events]
    if not ids:
        return []

    actor_names: dict[UUID, list[str]] = defaultdict(list)
    campaign_ids: dict[UUID, list[UUID]] = defaultdict(list)
    for event_id, campaign_id in session.execute(
        select(CampaignEvent.event_id, CampaignEvent.campaign_id).where(
            CampaignEvent.event_id.in_(ids)
        )
    ):
        campaign_ids[event_id].append(campaign_id)
    for event_id, canonical_name, reported_name in session.execute(
        select(EventActor.event_id, ThreatActor.canonical_name, EventActor.reported_name)
        .join(ThreatActor, ThreatActor.id == EventActor.actor_id)
        .where(EventActor.event_id.in_(ids))
    ):
        actor_names[event_id].extend((canonical_name, reported_name))

    observable_types: dict[UUID, list[str]] = defaultdict(list)
    observable_values: dict[UUID, list[str]] = defaultdict(list)
    for event_id, observable_type, value in session.execute(
        select(EventObservable.event_id, Observable.type, Observable.value_normalized)
        .join(Observable, Observable.id == EventObservable.observable_id)
        .where(EventObservable.event_id.in_(ids))
    ):
        observable_types[event_id].append(observable_type)
        observable_values[event_id].append(value)

    techniques: dict[UUID, list[str]] = defaultdict(list)
    for event_id, technique_id in session.execute(
        select(EventTechnique.event_id, EventTechnique.technique_id).where(
            EventTechnique.event_id.in_(ids)
        )
    ):
        techniques[event_id].append(technique_id)

    return [
        EventContext(
            id=event.id,
            title=event.title,
            summary=event.summary,
            confidence=event.confidence_analyst or event.confidence_auto or 0,
            campaign_ids=tuple(sorted(set(campaign_ids[event.id]), key=str)),
            actor_names=tuple(sorted(set(actor_names[event.id]))),
            observable_types=tuple(sorted(set(observable_types[event.id]))),
            observable_values=tuple(sorted(set(observable_values[event.id]))),
            technique_ids=tuple(sorted(set(techniques[event.id]))),
        )
        for event in events
    ]


def match_event(conditions: WatchConditions, context: EventContext) -> dict[str, object] | None:
    matched: dict[str, object] = {}
    if conditions.campaign_ids:
        available_campaigns = set(context.campaign_ids)
        campaign_values = [
            value for value in conditions.campaign_ids if value in available_campaigns
        ]
        if not campaign_values:
            return None
        matched["campaign_ids"] = [str(value) for value in campaign_values]
    corpus = " ".join(
        (
            context.title,
            context.summary,
            *context.actor_names,
            *context.observable_values,
            *context.technique_ids,
        )
    ).casefold()
    if conditions.keywords:
        keyword_values = [value for value in conditions.keywords if value.casefold() in corpus]
        if not keyword_values:
            return None
        matched["keywords"] = keyword_values
    if conditions.actor_names:
        actors = " ".join(context.actor_names).casefold()
        actor_values = [value for value in conditions.actor_names if value.casefold() in actors]
        if not actor_values:
            return None
        matched["actor_names"] = actor_values
    if conditions.observable_types:
        available = {value.casefold() for value in context.observable_types}
        observable_values = [
            value for value in conditions.observable_types if value.casefold() in available
        ]
        if not observable_values:
            return None
        matched["observable_types"] = observable_values
    if conditions.technique_ids:
        available = {value.upper() for value in context.technique_ids}
        technique_values = [
            value for value in conditions.technique_ids if value.upper() in available
        ]
        if not technique_values:
            return None
        matched["technique_ids"] = technique_values
    if conditions.min_confidence is not None:
        if context.confidence < conditions.min_confidence:
            return None
        matched["confidence"] = context.confidence
    return matched


def preview_matches(
    session: Session,
    conditions: WatchConditions,
    *,
    rule_id: UUID | None = None,
    limit: int = 50,
) -> list[WatchRuleHitRead]:
    now = datetime.now(UTC)
    matches: list[WatchRuleHitRead] = []
    for context in event_contexts(session):
        matched_on = match_event(conditions, context)
        if matched_on is None:
            continue
        preview_id = uuid5(
            NAMESPACE_URL,
            f"apt-hunter:watch-preview:{rule_id or 'new'}:{context.id}",
        )
        matches.append(
            WatchRuleHitRead(
                id=preview_id,
                rule_id=rule_id or UUID(int=0),
                subject_type="event",
                subject_id=context.id,
                subject_title=context.title,
                matched_on=matched_on,
                created_at=now,
            )
        )
        if len(matches) >= limit:
            break
    return matches


def _persist_hit(
    session: Session,
    rule: WatchRule,
    context: EventContext,
    matched_on: dict[str, object],
) -> bool:
    existing = session.scalar(
        select(WatchRuleHit.id).where(
            WatchRuleHit.rule_id == rule.id,
            WatchRuleHit.subject_type == "event",
            WatchRuleHit.subject_id == context.id,
        )
    )
    if existing is not None:
        return False
    hit = WatchRuleHit(
        rule_id=rule.id,
        subject_type="event",
        subject_id=context.id,
        matched_on=matched_on,
    )
    session.add(hit)
    session.flush()
    session.add(
        Notification(
            hit_id=hit.id,
            title=f"关注规则命中：{rule.name}",
            message=f"已确认事件“{context.title}”命中关注规则，请核对证据后研判。",
            severity=rule.severity,
            target_type="event",
            target_id=context.id,
        )
    )
    return True


def evaluate_rule(session: Session, rule: WatchRule) -> tuple[int, int]:
    conditions = WatchConditions.model_validate(rule.conditions)
    contexts = event_contexts(session)
    created = 0
    for context in contexts:
        matched_on = match_event(conditions, context)
        if matched_on is not None and _persist_hit(session, rule, context, matched_on):
            created += 1
    return len(contexts), created


def evaluate_event_rules(session: Session, event_id: UUID) -> int:
    contexts = event_contexts(session, [event_id])
    if not contexts:
        return 0
    context = contexts[0]
    created = 0
    rules = session.scalars(select(WatchRule).where(WatchRule.enabled.is_(True)))
    for rule in rules:
        conditions = WatchConditions.model_validate(rule.conditions)
        matched_on = match_event(conditions, context)
        if matched_on is not None and _persist_hit(session, rule, context, matched_on):
            created += 1
    return created
