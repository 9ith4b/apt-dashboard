from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from apt_hunter.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Source(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sources"
    __table_args__ = (UniqueConstraint("type", "name"),)

    type: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    config: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    secret_ref: Mapped[str | None] = mapped_column(String(255))
    enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    health_status: Mapped[str] = mapped_column(String(32), default="disabled", nullable=False)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Report(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reports"
    __table_args__ = (
        Index("ix_reports_status_published_at", "status", "published_at"),
        UniqueConstraint("exact_hash"),
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

    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("threat_events.id", ondelete="CASCADE"), primary_key=True
    )
    report_id: Mapped[UUID] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True
    )
    evidence_role: Mapped[str] = mapped_column(String(32), default="supporting", nullable=False)
