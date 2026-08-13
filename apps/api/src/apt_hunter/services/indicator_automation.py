from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.orm import Session

from apt_hunter.models import (
    AIProcessingPolicy,
    Indicator,
    IndicatorEvidence,
    Observable,
    ObservableEnrichment,
    Report,
    ReportObservable,
)


def _indicator_pattern(observable: Observable) -> str:
    field = {
        "domain": "domain-name:value",
        "ipv4": "ipv4-addr:value",
        "ipv6": "ipv6-addr:value",
        "url": "url:value",
        "email": "email-addr:value",
        "md5": "file:hashes.MD5",
        "sha1": "file:hashes.'SHA-1'",
        "sha256": "file:hashes.'SHA-256'",
    }.get(observable.type, "artifact:payload_bin")
    escaped = observable.value_normalized.replace("\\", "\\\\").replace("'", "\\'")
    return f"[{field} = '{escaped}']"


def _score(value: object) -> int:
    try:
        return max(0, min(100, int(float(str(value)))))
    except (TypeError, ValueError):
        return 0


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _ttl_days(candidate: dict[str, object]) -> int:
    defaults = {
        "domain": 30,
        "url": 30,
        "ipv4": 14,
        "ipv6": 14,
        "email": 30,
        "md5": 365,
        "sha1": 365,
        "sha256": 365,
    }
    fallback = defaults.get(str(candidate.get("type", "")), 30)
    try:
        return max(1, min(365, int(float(str(candidate.get("indicator_ttl_days", fallback))))))
    except (TypeError, ValueError):
        return fallback


def _severity(candidate: dict[str, object]) -> str:
    value = str(candidate.get("indicator_severity", "high")).casefold()
    return value if value in {"info", "low", "medium", "high", "critical"} else "high"


def _upsert_ai_context(
    session: Session,
    observable: Observable,
    report: Report,
    candidate: dict[str, object],
    now: datetime,
) -> None:
    result = {
        "disposition": candidate.get("ai_disposition"),
        "role": candidate.get("ai_role"),
        "confidence": _score(candidate.get("ai_confidence")),
        "indicator_candidate": bool(candidate.get("indicator_candidate")),
        "purpose": candidate.get("indicator_purpose"),
        "severity": _severity(candidate),
        "ttl_days": _ttl_days(candidate),
        "decision_reason": candidate.get("ai_decision_reason"),
        "evidence": candidate.get("evidence"),
        "report_id": str(report.id),
        "report_title": report.title,
        "managed_by": "ai-automation",
    }
    values = {
        "observable_id": observable.id,
        "provider": "ai-context",
        "status": "completed",
        "queried_at": now,
        "expires_at": now + timedelta(days=7),
        "result": result,
        "error": None,
    }
    if session.get_bind().dialect.name == "postgresql":
        session.execute(
            postgresql_insert(ObservableEnrichment)
            .values(**values)
            .on_conflict_do_update(
                constraint="uq_observable_enrichments_observable_provider",
                set_={key: value for key, value in values.items() if key != "observable_id"},
            )
        )
        return
    enrichment = session.scalar(
        select(ObservableEnrichment).where(
            ObservableEnrichment.observable_id == observable.id,
            ObservableEnrichment.provider == "ai-context",
        )
    )
    if enrichment is None:
        session.add(ObservableEnrichment(**values))
        return
    for key, value in values.items():
        setattr(enrichment, key, value)


def apply_ai_observable_decisions(
    session: Session,
    *,
    report: Report,
    candidates: list[dict[str, object]],
    policy: AIProcessingPolicy,
) -> dict[str, int]:
    """Apply grounded AI IOC decisions without creating a human approval gate.

    Analyst-created or analyst-corrected Indicators are immutable to this routine.
    """
    counts = {"assessed": 0, "promoted": 0, "updated": 0, "revoked": 0}
    if not policy.auto_manage_indicators:
        return counts
    now = datetime.now(UTC)
    observed_at = _utc(report.published_at or report.created_at)
    for candidate in candidates:
        disposition = str(candidate.get("ai_disposition", ""))
        if not disposition:
            continue
        observable = session.scalar(
            select(Observable).where(
                Observable.type == str(candidate.get("type", "")),
                Observable.value_normalized == str(candidate.get("normalized", "")),
            )
        )
        if observable is None:
            continue
        counts["assessed"] += 1
        _upsert_ai_context(session, observable, report, candidate, now)
        confidence = _score(candidate.get("ai_confidence"))
        indicator = session.scalar(
            select(Indicator).where(Indicator.observable_id == observable.id)
        )
        if indicator is not None and indicator.reviewed_by != "ai-automation":
            continue
        report_link = session.scalar(
            select(ReportObservable).where(
                ReportObservable.report_id == report.id,
                ReportObservable.observable_id == observable.id,
            )
        )
        if (
            disposition == "malicious"
            and bool(candidate.get("indicator_candidate"))
            and confidence >= policy.indicator_auto_threshold
            and report_link is not None
        ):
            purpose = str(candidate.get("indicator_purpose") or "AI识别的恶意技术对象")[:500]
            valid_until = max(now, observed_at) + timedelta(days=_ttl_days(candidate))
            if indicator is None:
                indicator = Indicator(
                    observable_id=observable.id,
                    purpose=purpose,
                    pattern=_indicator_pattern(observable),
                    valid_from=observed_at,
                    valid_until=valid_until,
                    confidence=confidence,
                    severity=_severity(candidate),
                    revoked=False,
                    reviewed_at=now,
                    reviewed_by="ai-automation",
                )
                session.add(indicator)
                session.flush()
                counts["promoted"] += 1
            else:
                changed = False
                if indicator.revoked:
                    indicator.revoked = False
                    changed = True
                if valid_until > _utc(indicator.valid_until):
                    indicator.valid_until = valid_until
                    changed = True
                if confidence >= indicator.confidence:
                    indicator.confidence = confidence
                    indicator.purpose = purpose
                    indicator.severity = _severity(candidate)
                    changed = True
                if changed:
                    indicator.reviewed_at = now
                    indicator.version += 1
                    counts["updated"] += 1
            if session.get(IndicatorEvidence, (indicator.id, report_link.evidence_id)) is None:
                session.add(
                    IndicatorEvidence(
                        indicator_id=indicator.id,
                        evidence_id=report_link.evidence_id,
                    )
                )
        elif (
            disposition == "benign"
            and confidence >= policy.indicator_auto_threshold
            and indicator is not None
            and not indicator.revoked
        ):
            indicator.revoked = True
            indicator.reviewed_at = now
            indicator.purpose = (
                f"AI撤销：{candidate.get('ai_decision_reason') or '新证据表明该对象为良性'}"
            )[:500]
            indicator.version += 1
            counts["revoked"] += 1
    return counts
