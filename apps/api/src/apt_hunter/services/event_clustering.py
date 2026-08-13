import re
from collections import defaultdict
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.orm import Session

from apt_hunter.models import (
    AIProcessingPolicy,
    EventActor,
    EventMergeCandidate,
    EventObservable,
    EventReport,
    EventTechnique,
    Report,
    ReportAnalysis,
    ThreatEvent,
)
from apt_hunter.services.actor_normalization import sync_event_actors_from_reports
from apt_hunter.services.knowledge import sync_event_knowledge

_TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{2,}", re.IGNORECASE)
MERGE_THRESHOLD = 45
AUTO_MERGE_THRESHOLD = 90


def _candidate_id(source_event_id: UUID, target_event_id: UUID) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        f"apt-hunter:event-merge:{source_event_id}:{target_event_id}",
    )


def _overlap[OverlapValue](left: set[OverlapValue], right: set[OverlapValue]) -> int:
    return len(left & right)


def _title_similarity(left: str, right: str) -> float:
    left_tokens = {match.group(0).casefold() for match in _TOKEN_PATTERN.finditer(left)}
    right_tokens = {match.group(0).casefold() for match in _TOKEN_PATTERN.finditer(right)}
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def score_event_similarity(
    *,
    source: ThreatEvent,
    target: ThreatEvent,
    source_actors: set[UUID],
    target_actors: set[UUID],
    source_observables: set[UUID],
    target_observables: set[UUID],
    source_techniques: set[str],
    target_techniques: set[str],
    source_victims: set[str],
    target_victims: set[str],
) -> tuple[int, dict[str, object]]:
    actor_overlap = _overlap(source_actors, target_actors)
    observable_overlap = _overlap(source_observables, target_observables)
    technique_overlap = _overlap(source_techniques, target_techniques)
    victim_overlap = _overlap(source_victims, target_victims)
    source_date = source.first_seen or source.created_at
    target_date = target.first_seen or target.created_at
    date_distance_days = abs((source_date - target_date).days)
    title_similarity = _title_similarity(source.title, target.title)
    score = (
        (35 if actor_overlap else 0)
        + min(35, observable_overlap * 15)
        + min(15, technique_overlap * 7)
        + min(8, victim_overlap * 4)
        + (7 if date_distance_days <= 14 else 3 if date_distance_days <= 30 else 0)
        + min(10, round(title_similarity * 10))
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


def _feature_sets(
    session: Session,
    event_ids: list[UUID],
) -> tuple[
    dict[UUID, set[UUID]],
    dict[UUID, set[UUID]],
    dict[UUID, set[str]],
    dict[UUID, set[str]],
]:
    actors: dict[UUID, set[UUID]] = defaultdict(set)
    observables: dict[UUID, set[UUID]] = defaultdict(set)
    techniques: dict[UUID, set[str]] = defaultdict(set)
    victims: dict[UUID, set[str]] = defaultdict(set)
    for event_id, actor_id in session.execute(
        select(EventActor.event_id, EventActor.actor_id).where(EventActor.event_id.in_(event_ids))
    ):
        actors[event_id].add(actor_id)
    for event_id, observable_id in session.execute(
        select(EventObservable.event_id, EventObservable.observable_id).where(
            EventObservable.event_id.in_(event_ids)
        )
    ):
        observables[event_id].add(observable_id)
    for event_id, technique_id in session.execute(
        select(EventTechnique.event_id, EventTechnique.technique_id).where(
            EventTechnique.event_id.in_(event_ids)
        )
    ):
        techniques[event_id].add(technique_id)
    analysis_rows = session.execute(
        select(EventReport.event_id, ReportAnalysis)
        .join(ReportAnalysis, ReportAnalysis.report_id == EventReport.report_id)
        .where(EventReport.event_id.in_(event_ids))
    )
    for event_id, analysis in analysis_rows:
        entities = (
            analysis.reviewed_victims if analysis.reviewed_victims is not None else analysis.victims
        )
        victims[event_id].update(
            str(entity.get("name", "")).casefold() for entity in entities if entity.get("name")
        )
    return actors, observables, techniques, victims


def generate_merge_candidates(session: Session, source_event_id: UUID) -> int:
    source = session.get(ThreatEvent, source_event_id)
    if source is None or source.superseded_by_id is not None:
        return 0
    targets = list(
        session.scalars(
            select(ThreatEvent).where(
                ThreatEvent.id != source_event_id,
                ThreatEvent.status == "confirmed",
                ThreatEvent.superseded_by_id.is_(None),
            )
        )
    )
    if not targets:
        return 0
    event_ids = [source_event_id, *[event.id for event in targets]]
    actors, observables, techniques, victims = _feature_sets(session, event_ids)
    created = 0
    best_auto_candidate: tuple[int, UUID] | None = None
    for target in targets:
        score, features = score_event_similarity(
            source=source,
            target=target,
            source_actors=actors[source_event_id],
            target_actors=actors[target.id],
            source_observables=observables[source_event_id],
            target_observables=observables[target.id],
            source_techniques=techniques[source_event_id],
            target_techniques=techniques[target.id],
            source_victims=victims[source_event_id],
            target_victims=victims[target.id],
        )
        if score < MERGE_THRESHOLD:
            continue
        candidate_id = _candidate_id(source_event_id, target.id)
        if score >= AUTO_MERGE_THRESHOLD and (
            best_auto_candidate is None or score > best_auto_candidate[0]
        ):
            best_auto_candidate = (score, candidate_id)
        if session.get_bind().dialect.name == "postgresql":
            session.execute(
                postgresql_insert(EventMergeCandidate)
                .values(
                    id=candidate_id,
                    source_event_id=source_event_id,
                    target_event_id=target.id,
                    score=score,
                    features=features,
                    status="pending",
                    moved_report_ids=[],
                    version=1,
                )
                .on_conflict_do_update(
                    constraint="uq_event_merge_candidates_pair",
                    set_={"score": score, "features": features},
                    where=EventMergeCandidate.status == "pending",
                )
            )
            created += 1
        else:
            existing = session.get(EventMergeCandidate, candidate_id)
            if existing is None:
                session.add(
                    EventMergeCandidate(
                        id=candidate_id,
                        source_event_id=source_event_id,
                        target_event_id=target.id,
                        score=score,
                        features=features,
                    )
                )
                created += 1
            elif existing.status == "pending":
                existing.score = score
                existing.features = features
    policy = session.get(AIProcessingPolicy, "default")
    if (
        best_auto_candidate is not None
        and policy is not None
        and policy.automation_enabled
        and policy.unattended_mode
    ):
        session.flush()
        score, candidate_id = best_auto_candidate
        candidate = session.get(EventMergeCandidate, candidate_id)
        if candidate is not None and candidate.status == "pending":
            decide_merge_candidate(
                session,
                candidate_id,
                decision="approved",
                reason=(
                    "无人值守自动合并：攻击者、技术对象、ATT&CK技术、受害者与时间窗口"
                    f"的综合相似度为 {score}%。人工可在事件页撤销。"
                ),
                expected_version=candidate.version,
            )
    return created


def _refresh_event(session: Session, event: ThreatEvent) -> None:
    reports = list(
        session.scalars(
            select(Report)
            .join(EventReport, EventReport.report_id == Report.id)
            .where(EventReport.event_id == event.id)
        )
    )
    if reports:
        observed = [report.published_at or report.created_at for report in reports]
        event.first_seen = min(observed)
        event.last_seen = max(observed)
    sync_event_actors_from_reports(session, event.id)
    sync_event_knowledge(session, event.id)


def decide_merge_candidate(
    session: Session,
    candidate_id: UUID,
    *,
    decision: str,
    reason: str | None,
    expected_version: int,
) -> EventMergeCandidate:
    candidate = session.scalar(
        select(EventMergeCandidate).where(EventMergeCandidate.id == candidate_id).with_for_update()
    )
    if candidate is None:
        raise ValueError("Merge candidate not found")
    if candidate.status != "pending" or candidate.version != expected_version:
        raise RuntimeError("Merge candidate changed; reload before deciding")
    if decision == "rejected":
        candidate.status = "rejected"
        candidate.decision_reason = reason
        candidate.reviewed_at = datetime.now(UTC)
        candidate.version += 1
        return candidate

    event_ids = sorted([candidate.source_event_id, candidate.target_event_id], key=str)
    locked_events = list(
        session.scalars(
            select(ThreatEvent)
            .where(ThreatEvent.id.in_(event_ids))
            .order_by(ThreatEvent.id)
            .with_for_update()
        )
    )
    events = {event.id: event for event in locked_events}
    source = events.get(candidate.source_event_id)
    target = events.get(candidate.target_event_id)
    if source is None or target is None:
        raise ValueError("Merge event not found")
    if source.superseded_by_id is not None or target.superseded_by_id is not None:
        raise RuntimeError("A merge event has already been superseded")

    moved_report_ids = list(
        session.scalars(select(EventReport.report_id).where(EventReport.event_id == source.id))
    )
    session.execute(
        update(EventReport).where(EventReport.event_id == source.id).values(event_id=target.id)
    )
    source.status = "superseded"
    source.superseded_by_id = target.id
    source.version += 1
    target.version += 1
    _refresh_event(session, target)

    candidate.status = "approved"
    candidate.decision_reason = reason
    candidate.moved_report_ids = [str(report_id) for report_id in moved_report_ids]
    candidate.reviewed_at = datetime.now(UTC)
    candidate.version += 1
    session.execute(
        update(EventMergeCandidate)
        .where(
            EventMergeCandidate.id != candidate.id,
            EventMergeCandidate.status == "pending",
            or_(
                EventMergeCandidate.source_event_id == source.id,
                EventMergeCandidate.target_event_id == source.id,
            ),
        )
        .values(
            status="rejected",
            decision_reason="Automatically closed because an event was superseded",
            reviewed_at=datetime.now(UTC),
            version=EventMergeCandidate.version + 1,
        )
    )
    return candidate


def undo_merge_candidate(
    session: Session,
    candidate_id: UUID,
    *,
    expected_version: int,
) -> EventMergeCandidate:
    candidate = session.scalar(
        select(EventMergeCandidate).where(EventMergeCandidate.id == candidate_id).with_for_update()
    )
    if candidate is None:
        raise ValueError("Merge candidate not found")
    if candidate.status != "approved" or candidate.version != expected_version:
        raise RuntimeError("Only the current approved merge can be undone")
    event_ids = sorted([candidate.source_event_id, candidate.target_event_id], key=str)
    locked_events = list(
        session.scalars(
            select(ThreatEvent)
            .where(ThreatEvent.id.in_(event_ids))
            .order_by(ThreatEvent.id)
            .with_for_update()
        )
    )
    events = {event.id: event for event in locked_events}
    source = events.get(candidate.source_event_id)
    target = events.get(candidate.target_event_id)
    if source is None or target is None or source.superseded_by_id != target.id:
        raise RuntimeError("The merge is no longer reversible")
    moved_report_ids = [UUID(value) for value in candidate.moved_report_ids]
    if moved_report_ids:
        session.execute(
            update(EventReport)
            .where(
                EventReport.event_id == target.id,
                EventReport.report_id.in_(moved_report_ids),
            )
            .values(event_id=source.id)
        )
    source.status = "confirmed"
    source.superseded_by_id = None
    source.version += 1
    target.version += 1
    _refresh_event(session, source)
    _refresh_event(session, target)
    candidate.status = "undone"
    candidate.reviewed_at = datetime.now(UTC)
    candidate.version += 1
    return candidate
