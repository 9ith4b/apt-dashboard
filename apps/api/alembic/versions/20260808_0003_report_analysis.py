"""Add article extraction and analyst review state."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260808_0003"
down_revision: str | None = "20260808_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_analyses",
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("extraction_status", sa.String(length=32), nullable=False),
        sa.Column("review_status", sa.String(length=32), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("final_url", sa.Text(), nullable=True),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extraction_error", sa.Text(), nullable=True),
        sa.Column("actors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("infrastructure", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("victims", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence_auto", sa.Integer(), nullable=True),
        sa.Column("method_version", sa.String(length=32), nullable=False),
        sa.Column("analyst_note", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(length=100), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
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
            "confidence_auto IS NULL OR confidence_auto BETWEEN 0 AND 100",
            name="ck_report_analyses_report_analysis_confidence_range",
        ),
        sa.CheckConstraint(
            "extraction_status IN ('queued', 'processing', 'ready', 'failed')",
            name="ck_report_analyses_report_analysis_extraction_status",
        ),
        sa.CheckConstraint(
            "review_status IN ('pending', 'approved', 'rejected')",
            name="ck_report_analyses_report_analysis_review_status",
        ),
        sa.CheckConstraint(
            "version >= 1", name="ck_report_analyses_report_analysis_version_positive"
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["reports.id"],
            ondelete="CASCADE",
            name="fk_report_analyses_report_id_reports",
        ),
        sa.PrimaryKeyConstraint("report_id", name="pk_report_analyses"),
    )
    op.create_index(
        "ix_report_analyses_pending_review",
        "report_analyses",
        ["updated_at"],
        unique=False,
        postgresql_where=sa.text("review_status = 'pending'"),
    )
    op.create_index(
        "ix_report_analyses_review_updated",
        "report_analyses",
        ["review_status", "updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_report_analyses_review_updated", table_name="report_analyses")
    op.drop_index(
        "ix_report_analyses_pending_review",
        table_name="report_analyses",
        postgresql_where=sa.text("review_status = 'pending'"),
    )
    op.drop_table("report_analyses")
