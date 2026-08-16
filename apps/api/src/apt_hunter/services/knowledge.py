import hashlib
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.orm import Session

from apt_hunter.models import (
    AttackTechnique,
    EventObservable,
    EventReport,
    EventTechnique,
    Evidence,
    Observable,
    Report,
    ReportObservable,
    ReportTechnique,
)


def _observable_id(observable_type: str, normalized: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"apt-hunter:observable:{observable_type}:{normalized}")


def _evidence_id(
    report_id: UUID,
    subject_type: str,
    subject_key: str,
    quote: str,
) -> UUID:
    quote_hash = hashlib.sha256(quote.encode("utf-8")).hexdigest()
    return uuid5(
        NAMESPACE_URL,
        f"apt-hunter:evidence:{report_id}:{subject_type}:{subject_key}:{quote_hash}",
    )


def _upsert_evidence(
    session: Session,
    *,
    report_id: UUID,
    subject_type: str,
    subject_key: str,
    candidate: dict[str, object],
    method_version: str,
) -> UUID:
    quote = str(candidate.get("evidence", ""))[:5000]
    evidence_id = _evidence_id(report_id, subject_type, subject_key, quote)
    values = {
        "id": evidence_id,
        "report_id": report_id,
        "subject_type": subject_type,
        "subject_key": subject_key[:1000],
        "quote": quote,
        "start_offset": candidate.get("start_offset"),
        "end_offset": candidate.get("end_offset"),
        "locator": None,
        "evidence_type": "direct",
        "created_by": method_version,
    }
    if session.get_bind().dialect.name == "postgresql":
        session.execute(
            postgresql_insert(Evidence)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[Evidence.id],
                set_={
                    "quote": quote,
                    "start_offset": candidate.get("start_offset"),
                    "end_offset": candidate.get("end_offset"),
                    "created_by": method_version,
                },
            )
        )
    else:
        existing = session.get(Evidence, evidence_id)
        if existing is None:
            session.add(Evidence(**values))
        else:
            existing.quote = quote
            existing.start_offset = _optional_int(candidate.get("start_offset"))
            existing.end_offset = _optional_int(candidate.get("end_offset"))
            existing.created_by = method_version
    return evidence_id


def _optional_int(value: object) -> int | None:
    return int(value) if isinstance(value, (int, float)) else None


def _confidence(candidate: dict[str, object]) -> int:
    value = candidate.get("confidence", 0)
    return max(0, min(100, int(value))) if isinstance(value, (int, float)) else 0


def _upsert_observable(
    session: Session,
    candidate: dict[str, object],
    observed_at: datetime,
) -> UUID:
    observable_type = str(candidate["type"])
    normalized = str(candidate["normalized"])
    observable_id = _observable_id(observable_type, normalized)
    values = {
        "id": observable_id,
        "type": observable_type,
        "value_original": str(candidate["value"]),
        "value_normalized": normalized,
        "scope": str(candidate.get("scope", "public")),
        "validation_status": "valid",
        "first_seen": observed_at,
        "last_seen": observed_at,
    }
    if session.get_bind().dialect.name == "postgresql":
        session.execute(
            postgresql_insert(Observable)
            .values(**values)
            .on_conflict_do_update(
                constraint="uq_observables_type_value",
                set_={
                    "value_original": str(candidate["value"]),
                    "scope": str(candidate.get("scope", "public")),
                    "validation_status": "valid",
                    "first_seen": func.least(Observable.first_seen, observed_at),
                    "last_seen": func.greatest(Observable.last_seen, observed_at),
                },
            )
        )
    else:
        existing = session.get(Observable, observable_id)
        if existing is None:
            session.add(Observable(**values))
        else:
            existing.value_original = str(candidate["value"])
            existing.scope = str(candidate.get("scope", "public"))
            previous_last = _utc(existing.last_seen) if existing.last_seen else None
            previous_first = _utc(existing.first_seen) if existing.first_seen else None
            if previous_last is None or observed_at > previous_last:
                existing.last_seen = observed_at
            if previous_first is None or observed_at < previous_first:
                existing.first_seen = observed_at
    return observable_id


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _upsert_technique(session: Session, candidate: dict[str, object]) -> str:
    technique_id = str(candidate["technique_id"]).upper()
    name = str(candidate.get("name", f"MITRE ATT&CK {technique_id}"))
    tactic = candidate.get("tactic")
    if session.get_bind().dialect.name == "postgresql":
        session.execute(
            postgresql_insert(AttackTechnique)
            .values(technique_id=technique_id, name=name, tactic=tactic)
            .on_conflict_do_update(
                index_elements=[AttackTechnique.technique_id],
                set_={"name": name, "tactic": tactic},
            )
        )
    else:
        existing = session.get(AttackTechnique, technique_id)
        if existing is None:
            session.add(AttackTechnique(technique_id=technique_id, name=name, tactic=tactic))
        else:
            existing.name = name
            existing.tactic = str(tactic) if tactic is not None else None
    return technique_id


def persist_report_knowledge(
    session: Session,
    *,
    report_id: UUID,
    observed_at: datetime,
    observables: list[dict[str, object]],
    techniques: list[dict[str, object]],
    method_version: str,
) -> None:
    session.execute(delete(ReportObservable).where(ReportObservable.report_id == report_id))
    session.execute(delete(ReportTechnique).where(ReportTechnique.report_id == report_id))

    observable_links: list[ReportObservable] = []
    for candidate in observables:
        if not candidate.get("type") or not candidate.get("normalized"):
            continue
        observable_id = _upsert_observable(session, candidate, observed_at)
        subject_key = f"{candidate['type']}:{candidate['normalized']}"
        evidence_id = _upsert_evidence(
            session,
            report_id=report_id,
            subject_type="observable",
            subject_key=subject_key,
            candidate=candidate,
            method_version=method_version,
        )
        observable_links.append(
            ReportObservable(
                report_id=report_id,
                observable_id=observable_id,
                evidence_id=evidence_id,
                confidence=_confidence(candidate),
            )
        )

    technique_links: list[ReportTechnique] = []
    for candidate in techniques:
        if not candidate.get("technique_id"):
            continue
        technique_id = _upsert_technique(session, candidate)
        evidence_id = _upsert_evidence(
            session,
            report_id=report_id,
            subject_type="attack-technique",
            subject_key=technique_id,
            candidate=candidate,
            method_version=method_version,
        )
        technique_links.append(
            ReportTechnique(
                report_id=report_id,
                technique_id=technique_id,
                evidence_id=evidence_id,
                confidence=_confidence(candidate),
            )
        )

    session.add_all([*observable_links, *technique_links])


def sync_event_knowledge(session: Session, event_id: UUID) -> None:
    session.execute(delete(EventObservable).where(EventObservable.event_id == event_id))
    session.execute(delete(EventTechnique).where(EventTechnique.event_id == event_id))

    observable_rows = session.scalars(
        select(ReportObservable)
        .join(EventReport, EventReport.report_id == ReportObservable.report_id)
        .join(Report, Report.id == ReportObservable.report_id)
        .where(EventReport.event_id == event_id, Report.status == "approved")
    )
    observables: dict[UUID, ReportObservable] = {}
    for observable_row in observable_rows:
        current_observable = observables.get(observable_row.observable_id)
        if current_observable is None or observable_row.confidence > current_observable.confidence:
            observables[observable_row.observable_id] = observable_row

    technique_rows = session.scalars(
        select(ReportTechnique)
        .join(EventReport, EventReport.report_id == ReportTechnique.report_id)
        .join(Report, Report.id == ReportTechnique.report_id)
        .where(EventReport.event_id == event_id, Report.status == "approved")
    )
    techniques: dict[str, ReportTechnique] = {}
    for technique_row in technique_rows:
        current_technique = techniques.get(technique_row.technique_id)
        if current_technique is None or technique_row.confidence > current_technique.confidence:
            techniques[technique_row.technique_id] = technique_row

    session.add_all(
        [
            EventObservable(
                event_id=event_id,
                observable_id=row.observable_id,
                evidence_id=row.evidence_id,
                confidence=row.confidence,
            )
            for row in observables.values()
        ]
    )
    session.add_all(
        [
            EventTechnique(
                event_id=event_id,
                technique_id=row.technique_id,
                evidence_id=row.evidence_id,
                confidence=row.confidence,
            )
            for row in techniques.values()
        ]
    )
