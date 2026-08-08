"""Create the initial intelligence tables."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("secret_ref", sa.String(length=255), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("health_status", sa.String(length=32), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sources")),
        sa.UniqueConstraint("type", "name", name=op.f("uq_sources_type")),
    )
    op.create_table(
        "reports",
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("exact_hash", sa.String(length=64), nullable=False),
        sa.Column("relevance_score", sa.Integer(), nullable=False),
        sa.Column("relevance_reasons", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["sources.id"], name=op.f("fk_reports_source_id_sources")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reports")),
        sa.UniqueConstraint("exact_hash", name=op.f("uq_reports_exact_hash")),
    )
    op.create_index("ix_reports_status_published_at", "reports", ["status", "published_at"])
    op.create_table(
        "threat_events",
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("confidence_auto", sa.Integer(), nullable=True),
        sa.Column("confidence_analyst", sa.Integer(), nullable=True),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_threat_events")),
    )
    op.create_index("ix_threat_events_status_first_seen", "threat_events", ["status", "first_seen"])
    op.create_table(
        "event_reports",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_role", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["threat_events.id"],
            name=op.f("fk_event_reports_event_id_threat_events"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["reports.id"],
            name=op.f("fk_event_reports_report_id_reports"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("event_id", "report_id", name=op.f("pk_event_reports")),
    )


def downgrade() -> None:
    op.drop_table("event_reports")
    op.drop_index("ix_threat_events_status_first_seen", table_name="threat_events")
    op.drop_table("threat_events")
    op.drop_index("ix_reports_status_published_at", table_name="reports")
    op.drop_table("reports")
    op.drop_table("sources")
