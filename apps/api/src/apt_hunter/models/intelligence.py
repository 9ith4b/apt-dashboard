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
    __table_args__ = (Index("ix_threat_events_status_first_seen", "status", "first_seen"),)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="candidate", nullable=False)
    confidence_auto: Mapped[int | None] = mapped_column(Integer)
    confidence_analyst: Mapped[int | None] = mapped_column(Integer)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


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
