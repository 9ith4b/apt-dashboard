"""Add Indicator hunting, enrichment, and Campaign tables."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0007"
down_revision: str | None = "20260808_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column[object]]:
    return [
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
    ]


def upgrade() -> None:
    op.create_table(
        "indicators",
        sa.Column("observable_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=500), nullable=False),
        sa.Column("pattern", sa.Text(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("revoked", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_by", sa.String(length=100), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "confidence BETWEEN 0 AND 100",
            name="ck_indicators_indicator_confidence_range",
        ),
        sa.CheckConstraint(
            "severity IN ('info', 'low', 'medium', 'high', 'critical')",
            name="ck_indicators_indicator_severity_value",
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_indicators_indicator_version_positive",
        ),
        sa.ForeignKeyConstraint(
            ["observable_id"],
            ["observables.id"],
            name="fk_indicators_observable_id_observables",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_indicators"),
        sa.UniqueConstraint("observable_id", name="uq_indicators_observable_id"),
    )
    op.create_index(
        "ix_indicators_revoked_valid_until",
        "indicators",
        ["revoked", "valid_until"],
        unique=False,
    )

    op.create_table(
        "indicator_evidence",
        sa.Column("indicator_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence.id"],
            name="fk_indicator_evidence_evidence_id_evidence",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["indicator_id"],
            ["indicators.id"],
            name="fk_indicator_evidence_indicator_id_indicators",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "indicator_id",
            "evidence_id",
            name="pk_indicator_evidence",
        ),
    )
    op.create_index(
        "ix_indicator_evidence_evidence_id",
        "indicator_evidence",
        ["evidence_id"],
        unique=False,
    )

    op.create_table(
        "observable_enrichments",
        sa.Column("observable_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("queried_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ck_observable_enrichments_observable_enrichment_status",
        ),
        sa.ForeignKeyConstraint(
            ["observable_id"],
            ["observables.id"],
            name="fk_observable_enrichments_observable_id_observables",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_observable_enrichments"),
        sa.UniqueConstraint(
            "observable_id",
            "provider",
            name="uq_observable_enrichments_observable_provider",
        ),
    )
    op.create_index(
        "ix_observable_enrichments_expires_at",
        "observable_enrichments",
        ["expires_at"],
        unique=False,
    )

    op.create_table(
        "campaigns",
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'closed')",
            name="ck_campaigns_campaign_status_value",
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_campaigns_campaign_version_positive",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_campaigns"),
        sa.UniqueConstraint("name", name="uq_campaigns_name"),
    )
    op.create_index(
        "ix_campaigns_status_last_seen",
        "campaigns",
        ["status", "last_seen"],
        unique=False,
    )

    op.create_table(
        "campaign_events",
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("stage", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("evidence_note", sa.Text(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_by", sa.String(length=100), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "stage IN ('unknown', 'reconnaissance', 'resource-development', "
            "'initial-access', 'execution', 'persistence', 'privilege-escalation', "
            "'defense-evasion', 'credential-access', 'discovery', 'lateral-movement', "
            "'collection', 'command-and-control', 'exfiltration', 'impact')",
            name="ck_campaign_events_campaign_event_stage_value",
        ),
        sa.CheckConstraint(
            "confidence BETWEEN 0 AND 100",
            name="ck_campaign_events_campaign_event_confidence_range",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.id"],
            name="fk_campaign_events_campaign_id_campaigns",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["threat_events.id"],
            name="fk_campaign_events_event_id_threat_events",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("campaign_id", "event_id", name="pk_campaign_events"),
    )
    op.create_index(
        "ix_campaign_events_event_campaign",
        "campaign_events",
        ["event_id", "campaign_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_campaign_events_event_campaign", table_name="campaign_events")
    op.drop_table("campaign_events")
    op.drop_index("ix_campaigns_status_last_seen", table_name="campaigns")
    op.drop_table("campaigns")
    op.drop_index(
        "ix_observable_enrichments_expires_at",
        table_name="observable_enrichments",
    )
    op.drop_table("observable_enrichments")
    op.drop_index(
        "ix_indicator_evidence_evidence_id",
        table_name="indicator_evidence",
    )
    op.drop_table("indicator_evidence")
    op.drop_index("ix_indicators_revoked_valid_until", table_name="indicators")
    op.drop_table("indicators")
