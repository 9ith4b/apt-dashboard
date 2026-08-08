"""Add reviewed Diamond snapshots and auditable threat event promotion."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260808_0004"
down_revision: str | None = "20260808_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "report_analyses",
        sa.Column("reviewed_actors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "report_analyses",
        sa.Column("reviewed_capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "report_analyses",
        sa.Column(
            "reviewed_infrastructure", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "report_analyses",
        sa.Column("reviewed_victims", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_table(
        "analysis_revisions",
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("review_version", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("analyst_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.String(length=100), nullable=False),
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
        sa.CheckConstraint(
            "decision IN ('approved', 'rejected')",
            name="ck_analysis_revisions_analysis_revision_decision",
        ),
        sa.CheckConstraint(
            "review_version >= 2",
            name="ck_analysis_revisions_analysis_revision_version_positive",
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["reports.id"],
            ondelete="CASCADE",
            name="fk_analysis_revisions_report_id_reports",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_analysis_revisions"),
        sa.UniqueConstraint(
            "report_id",
            "review_version",
            name="uq_analysis_revision_version",
        ),
    )
    op.create_unique_constraint(
        "uq_event_reports_report_id",
        "event_reports",
        ["report_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_event_reports_report_id", "event_reports", type_="unique")
    op.drop_table("analysis_revisions")
    op.drop_column("report_analyses", "reviewed_victims")
    op.drop_column("report_analyses", "reviewed_infrastructure")
    op.drop_column("report_analyses", "reviewed_capabilities")
    op.drop_column("report_analyses", "reviewed_actors")
