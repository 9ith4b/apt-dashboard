from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from apt_hunter.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Source(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint(
            "poll_interval_minutes BETWEEN 5 AND 1440",
            name="source_poll_interval_range",
        ),
        UniqueConstraint("type", "name"),
        UniqueConstraint("type", "url", name="uq_sources_type_url"),
        Index(
            "ix_sources_due_poll",
            "next_poll_at",
            postgresql_where=text("enabled IS TRUE"),
        ),
    )

    type: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    config: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    secret_ref: Mapped[str | None] = mapped_column(String(255))
    enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    health_status: Mapped[str] = mapped_column(String(32), default="disabled", nullable=False)
    poll_interval_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_poll_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    etag: Mapped[str | None] = mapped_column(String(500))
    last_modified: Mapped[str | None] = mapped_column(String(500))
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Report(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reports"
    __table_args__ = (
        Index("ix_reports_status_published_at", "status", "published_at"),
        Index("ix_reports_source_published_at", "source_id", "published_at"),
        UniqueConstraint("exact_hash"),
        UniqueConstraint("canonical_url", name="uq_reports_canonical_url"),
    )

    source_id: Mapped[UUID] = mapped_column(ForeignKey("sources.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(16), default="und", nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    exact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    relevance_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    relevance_reasons: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="new", nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReportAnalysis(TimestampMixin, Base):
    __tablename__ = "report_analyses"
    __table_args__ = (
        CheckConstraint(
            "extraction_status IN ('queued', 'processing', 'ready', 'failed')",
            name="report_analysis_extraction_status",
        ),
        CheckConstraint(
            "review_status IN ('pending', 'approved', 'rejected')",
            name="report_analysis_review_status",
        ),
        CheckConstraint(
            "confidence_auto IS NULL OR confidence_auto BETWEEN 0 AND 100",
            name="report_analysis_confidence_range",
        ),
        CheckConstraint("version >= 1", name="report_analysis_version_positive"),
        Index("ix_report_analyses_review_updated", "review_status", "updated_at"),
        Index(
            "ix_report_analyses_pending_review",
            "updated_at",
            postgresql_where=text("review_status = 'pending'"),
        ),
    )

    report_id: Mapped[UUID] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True
    )
    extraction_status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    content_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    final_url: Mapped[str | None] = mapped_column(Text)
    content_type: Mapped[str | None] = mapped_column(String(100))
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extraction_error: Mapped[str | None] = mapped_column(Text)
    actors: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list, nullable=False)
    capabilities: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    infrastructure: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    victims: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list, nullable=False)
    evidence: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list, nullable=False)
    observables: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list, nullable=False)
    attack_techniques: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    reviewed_actors: Mapped[list[dict[str, object]] | None] = mapped_column(JSON)
    reviewed_capabilities: Mapped[list[dict[str, object]] | None] = mapped_column(JSON)
    reviewed_infrastructure: Mapped[list[dict[str, object]] | None] = mapped_column(JSON)
    reviewed_victims: Mapped[list[dict[str, object]] | None] = mapped_column(JSON)
    confidence_auto: Mapped[int | None] = mapped_column(Integer)
    method_version: Mapped[str] = mapped_column(String(32), default="rules-v1", nullable=False)
    analyst_note: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[str | None] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class AnalysisRevision(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "analysis_revisions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('approved', 'rejected')",
            name="analysis_revision_decision",
        ),
        CheckConstraint("review_version >= 2", name="analysis_revision_version_positive"),
        UniqueConstraint("report_id", "review_version", name="uq_analysis_revision_version"),
    )

    report_id: Mapped[UUID] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), nullable=False
    )
    review_version: Mapped[int] = mapped_column(Integer, nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    analyst_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[str] = mapped_column(String(100), nullable=False)


class ThreatEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "threat_events"
    __table_args__ = (
        Index("ix_threat_events_status_first_seen", "status", "first_seen"),
        Index("ix_threat_events_superseded_by_id", "superseded_by_id"),
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="candidate", nullable=False)
    confidence_auto: Mapped[int | None] = mapped_column(Integer)
    confidence_analyst: Mapped[int | None] = mapped_column(Integer)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    superseded_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("threat_events.id", ondelete="SET NULL")
    )


class EventReport(TimestampMixin, Base):
    __tablename__ = "event_reports"
    __table_args__ = (UniqueConstraint("report_id", name="uq_event_reports_report_id"),)

    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("threat_events.id", ondelete="CASCADE"), primary_key=True
    )
    report_id: Mapped[UUID] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True
    )
    evidence_role: Mapped[str] = mapped_column(String(32), default="supporting", nullable=False)


class ThreatActor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "threat_actors"
    __table_args__ = (
        UniqueConstraint("canonical_key", name="uq_threat_actors_canonical_key"),
        Index("ix_threat_actors_canonical_name", "canonical_name"),
    )

    canonical_name: Mapped[str] = mapped_column(String(200), nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(200), nullable=False)
    origin_country: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)


class ThreatActorAlias(TimestampMixin, Base):
    __tablename__ = "threat_actor_aliases"
    __table_args__ = (Index("ix_threat_actor_aliases_actor_id", "actor_id"),)

    alias_key: Mapped[str] = mapped_column(String(200), primary_key=True)
    actor_id: Mapped[UUID] = mapped_column(
        ForeignKey("threat_actors.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(String(200), nullable=False)


class EventActor(TimestampMixin, Base):
    __tablename__ = "event_actors"
    __table_args__ = (
        CheckConstraint(
            "confidence BETWEEN 0 AND 100",
            name="event_actor_confidence_range",
        ),
        Index("ix_event_actors_actor_event", "actor_id", "event_id"),
    )

    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("threat_events.id", ondelete="CASCADE"), primary_key=True
    )
    actor_id: Mapped[UUID] = mapped_column(
        ForeignKey("threat_actors.id", ondelete="CASCADE"), primary_key=True
    )
    reported_name: Mapped[str] = mapped_column(String(500), nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, default="", nullable=False)


class Evidence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evidence"
    __table_args__ = (
        CheckConstraint(
            "evidence_type IN ('direct', 'indirect', 'contradicting', 'analyst')",
            name="evidence_type_value",
        ),
        Index("ix_evidence_report_subject", "report_id", "subject_type"),
    )

    report_id: Mapped[UUID] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), nullable=False
    )
    subject_type: Mapped[str] = mapped_column(String(50), nullable=False)
    subject_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    start_offset: Mapped[int | None] = mapped_column(Integer)
    end_offset: Mapped[int | None] = mapped_column(Integer)
    locator: Mapped[str | None] = mapped_column(String(500))
    evidence_type: Mapped[str] = mapped_column(String(32), default="direct", nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)


class Observable(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "observables"
    __table_args__ = (
        UniqueConstraint("type", "value_normalized", name="uq_observables_type_value"),
        Index("ix_observables_last_seen", "last_seen"),
    )

    type: Mapped[str] = mapped_column(String(32), nullable=False)
    value_original: Mapped[str] = mapped_column(Text, nullable=False)
    value_normalized: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(String(32), default="public", nullable=False)
    validation_status: Mapped[str] = mapped_column(String(32), default="valid", nullable=False)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReportObservable(TimestampMixin, Base):
    __tablename__ = "report_observables"
    __table_args__ = (
        CheckConstraint(
            "confidence BETWEEN 0 AND 100",
            name="report_observable_confidence_range",
        ),
        Index("ix_report_observables_observable_report", "observable_id", "report_id"),
    )

    report_id: Mapped[UUID] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True
    )
    observable_id: Mapped[UUID] = mapped_column(
        ForeignKey("observables.id", ondelete="CASCADE"), primary_key=True
    )
    evidence_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="RESTRICT"), nullable=False
    )
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)


class EventObservable(TimestampMixin, Base):
    __tablename__ = "event_observables"
    __table_args__ = (
        CheckConstraint(
            "confidence BETWEEN 0 AND 100",
            name="event_observable_confidence_range",
        ),
        Index("ix_event_observables_observable_event", "observable_id", "event_id"),
    )

    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("threat_events.id", ondelete="CASCADE"), primary_key=True
    )
    observable_id: Mapped[UUID] = mapped_column(
        ForeignKey("observables.id", ondelete="CASCADE"), primary_key=True
    )
    evidence_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="RESTRICT"), nullable=False
    )
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)


class AttackTechnique(TimestampMixin, Base):
    __tablename__ = "attack_techniques"

    technique_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    tactic: Mapped[str | None] = mapped_column(String(100))


class ReportTechnique(TimestampMixin, Base):
    __tablename__ = "report_techniques"
    __table_args__ = (
        CheckConstraint(
            "confidence BETWEEN 0 AND 100",
            name="report_technique_confidence_range",
        ),
        Index("ix_report_techniques_technique_report", "technique_id", "report_id"),
    )

    report_id: Mapped[UUID] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True
    )
    technique_id: Mapped[str] = mapped_column(
        ForeignKey("attack_techniques.technique_id", ondelete="CASCADE"), primary_key=True
    )
    evidence_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="RESTRICT"), nullable=False
    )
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)


class EventTechnique(TimestampMixin, Base):
    __tablename__ = "event_techniques"
    __table_args__ = (
        CheckConstraint(
            "confidence BETWEEN 0 AND 100",
            name="event_technique_confidence_range",
        ),
        Index("ix_event_techniques_technique_event", "technique_id", "event_id"),
    )

    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("threat_events.id", ondelete="CASCADE"), primary_key=True
    )
    technique_id: Mapped[str] = mapped_column(
        ForeignKey("attack_techniques.technique_id", ondelete="CASCADE"), primary_key=True
    )
    evidence_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="RESTRICT"), nullable=False
    )
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)


class EventMergeCandidate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "event_merge_candidates"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'undone')",
            name="event_merge_candidate_status",
        ),
        CheckConstraint(
            "score BETWEEN 0 AND 100",
            name="event_merge_candidate_score_range",
        ),
        CheckConstraint("version >= 1", name="event_merge_candidate_version_positive"),
        UniqueConstraint(
            "source_event_id",
            "target_event_id",
            name="uq_event_merge_candidates_pair",
        ),
        Index("ix_event_merge_candidates_status_score", "status", "score"),
        Index("ix_event_merge_candidates_target_event", "target_event_id"),
    )

    source_event_id: Mapped[UUID] = mapped_column(
        ForeignKey("threat_events.id", ondelete="CASCADE"), nullable=False
    )
    target_event_id: Mapped[UUID] = mapped_column(
        ForeignKey("threat_events.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    features: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    decision_reason: Mapped[str | None] = mapped_column(Text)
    moved_report_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class Indicator(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "indicators"
    __table_args__ = (
        CheckConstraint(
            "confidence BETWEEN 0 AND 100",
            name="indicator_confidence_range",
        ),
        CheckConstraint(
            "severity IN ('info', 'low', 'medium', 'high', 'critical')",
            name="indicator_severity_value",
        ),
        CheckConstraint("version >= 1", name="indicator_version_positive"),
        UniqueConstraint("observable_id", name="uq_indicators_observable_id"),
        Index("ix_indicators_revoked_valid_until", "revoked", "valid_until"),
    )

    observable_id: Mapped[UUID] = mapped_column(
        ForeignKey("observables.id", ondelete="CASCADE"), nullable=False
    )
    purpose: Mapped[str] = mapped_column(String(500), nullable=False)
    pattern: Mapped[str] = mapped_column(Text, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    revoked: Mapped[bool] = mapped_column(default=False, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed_by: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class IndicatorEvidence(TimestampMixin, Base):
    __tablename__ = "indicator_evidence"
    __table_args__ = (Index("ix_indicator_evidence_evidence_id", "evidence_id"),)

    indicator_id: Mapped[UUID] = mapped_column(
        ForeignKey("indicators.id", ondelete="CASCADE"), primary_key=True
    )
    evidence_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="RESTRICT"), primary_key=True
    )


class ObservableEnrichment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "observable_enrichments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('completed', 'failed')",
            name="observable_enrichment_status",
        ),
        UniqueConstraint(
            "observable_id",
            "provider",
            name="uq_observable_enrichments_observable_provider",
        ),
        Index("ix_observable_enrichments_expires_at", "expires_at"),
    )

    observable_id: Mapped[UUID] = mapped_column(
        ForeignKey("observables.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    queried_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    result: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)


class Campaign(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive', 'closed')",
            name="campaign_status_value",
        ),
        CheckConstraint("version >= 1", name="campaign_version_positive"),
        UniqueConstraint("name", name="uq_campaigns_name"),
        Index("ix_campaigns_status_last_seen", "status", "last_seen"),
    )

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class CampaignEvent(TimestampMixin, Base):
    __tablename__ = "campaign_events"
    __table_args__ = (
        CheckConstraint(
            "stage IN ('unknown', 'reconnaissance', 'resource-development', "
            "'initial-access', 'execution', 'persistence', 'privilege-escalation', "
            "'defense-evasion', 'credential-access', 'discovery', 'lateral-movement', "
            "'collection', 'command-and-control', 'exfiltration', 'impact')",
            name="campaign_event_stage_value",
        ),
        CheckConstraint(
            "confidence BETWEEN 0 AND 100",
            name="campaign_event_confidence_range",
        ),
        Index("ix_campaign_events_event_campaign", "event_id", "campaign_id"),
    )

    campaign_id: Mapped[UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True
    )
    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("threat_events.id", ondelete="CASCADE"), primary_key=True
    )
    stage: Mapped[str] = mapped_column(String(50), default="unknown", nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed_by: Mapped[str] = mapped_column(String(100), nullable=False)
