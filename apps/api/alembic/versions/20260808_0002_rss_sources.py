"""Add operational fields for RSS sources and report deduplication."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0002"
down_revision: str | None = "20260808_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("url", sa.Text(), nullable=True))
    op.add_column(
        "sources",
        sa.Column("poll_interval_minutes", sa.Integer(), server_default="60", nullable=False),
    )
    op.add_column(
        "sources", sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("sources", sa.Column("next_poll_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sources", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column("sources", sa.Column("etag", sa.String(length=500), nullable=True))
    op.add_column("sources", sa.Column("last_modified", sa.String(length=500), nullable=True))
    op.create_check_constraint(
        "ck_sources_source_poll_interval_range",
        "sources",
        "poll_interval_minutes BETWEEN 5 AND 1440",
    )
    op.create_unique_constraint("uq_sources_type_url", "sources", ["type", "url"])
    op.create_index(
        "ix_sources_due_poll",
        "sources",
        ["next_poll_at"],
        unique=False,
        postgresql_where=sa.text("enabled IS TRUE"),
    )
    op.create_unique_constraint("uq_reports_canonical_url", "reports", ["canonical_url"])
    op.create_index(
        "ix_reports_source_published_at",
        "reports",
        ["source_id", "published_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_reports_source_published_at", table_name="reports")
    op.drop_constraint("uq_reports_canonical_url", "reports", type_="unique")
    op.drop_index(
        "ix_sources_due_poll",
        table_name="sources",
        postgresql_where=sa.text("enabled IS TRUE"),
    )
    op.drop_constraint("uq_sources_type_url", "sources", type_="unique")
    op.drop_constraint(
        "ck_sources_source_poll_interval_range",
        "sources",
        type_="check",
    )
    op.drop_column("sources", "last_modified")
    op.drop_column("sources", "etag")
    op.drop_column("sources", "last_error")
    op.drop_column("sources", "next_poll_at")
    op.drop_column("sources", "last_checked_at")
    op.drop_column("sources", "poll_interval_minutes")
    op.drop_column("sources", "url")
