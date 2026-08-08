from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from apt_hunter.models import (
    AttackTechnique,
    EventActor,
    EventObservable,
    EventReport,
    EventTechnique,
    ReportAnalysis,
    ThreatActor,
    ThreatEvent,
)
from apt_hunter.schemas.actor import (
    ActorEventRead,
    ActorTimelineBucket,
    ActorTrackingChangeSet,
    ActorTrackingComparison,
    ActorTrackingPeriod,
    ActorTrackingRead,
    ActorTrackingSummaryRead,
)

ActorEventRow = tuple[EventActor, ThreatEvent]
Bucket = Literal["auto", "day", "week", "month"]
ResolvedBucket = Literal["day", "week", "month"]


def observed_at(event: ThreatEvent) -> datetime:
    return event.first_seen or event.created_at


def resolve_period(
    rows: list[ActorEventRow],
    date_from: date | None,
    date_to: date | None,
) -> tuple[date, date]:
    observed_dates = [observed_at(event).astimezone(UTC).date() for _, event in rows]
    today = datetime.now(UTC).date()
    resolved_to = date_to or (max(observed_dates) if observed_dates else today)
    resolved_from = date_from or (min(observed_dates) if observed_dates else resolved_to)
    if resolved_from > resolved_to:
        raise ValueError("date_from must be on or before date_to")
    return resolved_from, resolved_to


def resolve_bucket(bucket: Bucket, day_count: int) -> ResolvedBucket:
    if bucket != "auto":
        return bucket
    if day_count <= 31:
        return "day"
    if day_count <= 180:
        return "week"
    return "month"


def rows_in_period(
    rows: list[ActorEventRow], date_from: date, date_to: date
) -> list[ActorEventRow]:
    return [
        row for row in rows if date_from <= observed_at(row[1]).astimezone(UTC).date() <= date_to
    ]


def _event_read(row: ActorEventRow) -> ActorEventRead:
    event_actor, event = row
    return ActorEventRead(
        id=event.id,
        title=event.title,
        summary=event.summary,
        status=event.status,
        confidence=event_actor.confidence,
        first_seen=event.first_seen,
        last_seen=event.last_seen,
        reported_name=event_actor.reported_name,
    )


def _trend(rows: list[ActorEventRow], bucket: ResolvedBucket) -> list[ActorTimelineBucket]:
    counts: dict[str, int] = defaultdict(int)
    for _, event in rows:
        observed = observed_at(event).astimezone(UTC)
        if bucket == "day":
            key = observed.strftime("%Y-%m-%d")
            label = key
        elif bucket == "week":
            iso_year, iso_week, _ = observed.isocalendar()
            key = f"{iso_year}-W{iso_week:02d}"
            label = f"{iso_year} 年第 {iso_week} 周"
        else:
            key = observed.strftime("%Y-%m")
            label = f"{key[:4]} 年 {int(key[5:])} 月"
        counts[f"{key}\0{label}"] += 1
    return [
        ActorTimelineBucket(
            key=compound.split("\0", 1)[0], label=compound.split("\0", 1)[1], event_count=count
        )
        for compound, count in sorted(counts.items())
    ]


def _entity_names(items: list[dict[str, object]] | None) -> set[str]:
    if not items:
        return set()
    return {
        name.strip()
        for item in items
        if isinstance((name := item.get("name")), str) and name.strip()
    }


def _facets(session: Session, event_ids: list[UUID]) -> dict[str, set[str]]:
    facets = {
        "malware": set[str](),
        "infrastructure": set[str](),
        "techniques": set[str](),
        "targets": set[str](),
    }
    if not event_ids:
        return facets
    report_rows = session.execute(
        select(
            ReportAnalysis.reviewed_capabilities,
            ReportAnalysis.reviewed_infrastructure,
            ReportAnalysis.reviewed_victims,
        )
        .join(EventReport, EventReport.report_id == ReportAnalysis.report_id)
        .where(EventReport.event_id.in_(event_ids))
    )
    for capabilities, infrastructure, victims in report_rows:
        facets["malware"].update(_entity_names(capabilities))
        facets["infrastructure"].update(_entity_names(infrastructure))
        facets["targets"].update(_entity_names(victims))
    technique_rows = session.execute(
        select(EventTechnique.technique_id, AttackTechnique.name)
        .join(AttackTechnique, AttackTechnique.technique_id == EventTechnique.technique_id)
        .where(EventTechnique.event_id.in_(event_ids))
    )
    for technique_id, name in technique_rows:
        facets["techniques"].add(
            f"{technique_id} · {name}" if name and name != technique_id else technique_id
        )
    return facets


def _changes(
    current: dict[str, set[str]], previous: dict[str, set[str]]
) -> list[ActorTrackingChangeSet]:
    categories: tuple[Literal["malware", "infrastructure", "techniques", "targets"], ...] = (
        "malware",
        "infrastructure",
        "techniques",
        "targets",
    )
    return [
        ActorTrackingChangeSet(
            category=category,
            current_values=sorted(current[category]),
            previous_values=sorted(previous[category]),
            new_values=sorted(current[category] - previous[category]),
            disappeared_values=sorted(previous[category] - current[category]),
        )
        for category in categories
    ]


def build_tracking(
    session: Session,
    actor: ThreatActor,
    rows: list[ActorEventRow],
    date_from: date | None,
    date_to: date | None,
    bucket: Bucket,
) -> ActorTrackingRead:
    resolved_from, resolved_to = resolve_period(rows, date_from, date_to)
    day_count = (resolved_to - resolved_from).days + 1
    previous_to = resolved_from - timedelta(days=1)
    previous_from = previous_to - timedelta(days=day_count - 1)
    resolved_bucket = resolve_bucket(bucket, day_count)
    current_rows = rows_in_period(rows, resolved_from, resolved_to)
    previous_rows = rows_in_period(rows, previous_from, previous_to)
    current_count = len(current_rows)
    previous_count = len(previous_rows)
    percentage_change = (
        round((current_count - previous_count) / previous_count * 100, 1)
        if previous_count
        else None
    )
    current_ids = [event.id for _, event in current_rows]
    previous_ids = [event.id for _, event in previous_rows]
    return ActorTrackingRead(
        actor_id=actor.id,
        canonical_name=actor.canonical_name,
        period=ActorTrackingPeriod(
            date_from=resolved_from,
            date_to=resolved_to,
            previous_from=previous_from,
            previous_to=previous_to,
            day_count=day_count,
            bucket=resolved_bucket,
        ),
        comparison=ActorTrackingComparison(
            current_event_count=current_count,
            previous_event_count=previous_count,
            absolute_change=current_count - previous_count,
            percentage_change=percentage_change,
        ),
        trend=_trend(current_rows, resolved_bucket),
        changes=_changes(
            _facets(session, current_ids),
            _facets(session, previous_ids),
        ),
        events=[_event_read(row) for row in current_rows],
    )


def supporting_evidence_ids(session: Session, event_ids: list[UUID]) -> list[UUID]:
    if not event_ids:
        return []
    observable_ids = session.scalars(
        select(EventObservable.evidence_id).where(EventObservable.event_id.in_(event_ids))
    )
    technique_ids = session.scalars(
        select(EventTechnique.evidence_id).where(EventTechnique.event_id.in_(event_ids))
    )
    return sorted(set(observable_ids).union(technique_ids), key=str)


def build_summary(
    session: Session,
    tracking: ActorTrackingRead,
) -> ActorTrackingSummaryRead:
    count = tracking.comparison.current_event_count
    change = tracking.comparison.absolute_change
    direction = "增加" if change > 0 else "减少" if change < 0 else "持平"
    highlights = [
        f"本期记录 {count} 起已确认攻击事件，较上一等长周期{direction} {abs(change)} 起。"
    ]
    labels = {
        "malware": "能力或恶意软件",
        "infrastructure": "基础设施",
        "techniques": "ATT&CK 技术",
        "targets": "受害目标",
    }
    for item in tracking.changes:
        if item.new_values:
            highlights.append(f"新增{labels[item.category]}：{'、'.join(item.new_values)}。")
        if item.disappeared_values:
            highlights.append(
                f"本期未再出现{labels[item.category]}：{'、'.join(item.disappeared_values)}。"
            )
    event_ids = [event.id for event in tracking.events]
    return ActorTrackingSummaryRead(
        actor_id=tracking.actor_id,
        title=(
            f"{tracking.canonical_name} · {tracking.period.date_from.isoformat()} 至 "
            f"{tracking.period.date_to.isoformat()} 跟踪摘要"
        ),
        summary=(
            f"在所选 {tracking.period.day_count} 天周期内，{tracking.canonical_name} "
            f"共有 {count} 起已确认事件；所有变化均与紧邻的上一等长周期比较。"
        ),
        highlights=highlights,
        caveats=[
            "本摘要仅使用平台内已确认事件，未审核材料不会进入统计。",
            "“未再出现”只表示所选周期内没有观测，不代表基础设施或能力已经失效。",
            "摘要为规则生成草稿，发布前必须由分析员核对原始证据。",
        ],
        supporting_event_ids=event_ids,
        supporting_evidence_ids=supporting_evidence_ids(session, event_ids),
        generated_at=datetime.now(UTC),
    )
