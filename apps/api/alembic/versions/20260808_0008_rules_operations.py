"""Add watch rules, notifications, and persistent operation jobs."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0008"
down_revision: str | None = "20260808_0007"
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
        "watch_rules",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("conditions", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("severity", sa.String(length=32), server_default="medium", nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "severity IN ('info', 'low', 'medium', 'high', 'critical')",
            name="ck_watch_rules_watch_rule_severity_value",
        ),
        sa.CheckConstraint("version >= 1", name="ck_watch_rules_watch_rule_version_positive"),
        sa.PrimaryKeyConstraint("id", name="pk_watch_rules"),
        sa.UniqueConstraint("name", name="uq_watch_rules_name"),
    )
    op.create_index(
        "ix_watch_rules_enabled_severity",
        "watch_rules",
        ["enabled", "severity"],
        unique=False,
    )
    op.create_table(
        "watch_rule_hits",
        sa.Column("rule_id", sa.Uuid(), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("matched_on", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            ["watch_rules.id"],
            name="fk_watch_rule_hits_rule_id_watch_rules",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_watch_rule_hits"),
        sa.UniqueConstraint(
            "rule_id", "subject_type", "subject_id", name="uq_watch_rule_hits_subject"
        ),
    )
    op.create_index(
        "ix_watch_rule_hits_rule_created",
        "watch_rule_hits",
        ["rule_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_watch_rule_hits_subject",
        "watch_rule_hits",
        ["subject_type", "subject_id"],
        unique=False,
    )
    op.create_table(
        "notifications",
        sa.Column("hit_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "severity IN ('info', 'low', 'medium', 'high', 'critical')",
            name="ck_notifications_notification_severity_value",
        ),
        sa.ForeignKeyConstraint(
            ["hit_id"],
            ["watch_rule_hits.id"],
            name="fk_notifications_hit_id_watch_rule_hits",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
        sa.UniqueConstraint("hit_id", name="uq_notifications_hit_id"),
    )
    op.create_index(
        "ix_notifications_read_created",
        "notifications",
        ["read_at", "created_at"],
        unique=False,
    )
    op.create_table(
        "operation_jobs",
        sa.Column("task_id", sa.String(length=100), nullable=False),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="queued", nullable=False),
        sa.Column("progress", sa.Integer(), server_default="0", nullable=False),
        sa.Column("attempt", sa.Integer(), server_default="1", nullable=False),
        sa.Column("payload", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("result", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("requested_by", sa.String(length=100), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("parent_job_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'canceled')",
            name="ck_operation_jobs_operation_job_status_value",
        ),
        sa.CheckConstraint(
            "progress BETWEEN 0 AND 100",
            name="ck_operation_jobs_operation_job_progress_range",
        ),
        sa.CheckConstraint("attempt >= 1", name="ck_operation_jobs_operation_job_attempt_positive"),
        sa.CheckConstraint("version >= 1", name="ck_operation_jobs_operation_job_version_positive"),
        sa.ForeignKeyConstraint(
            ["parent_job_id"],
            ["operation_jobs.id"],
            name="fk_operation_jobs_parent_job_id_operation_jobs",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_operation_jobs"),
        sa.UniqueConstraint("task_id", name="uq_operation_jobs_task_id"),
    )
    op.create_index(
        "ix_operation_jobs_status_created",
        "operation_jobs",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_operation_jobs_subject",
        "operation_jobs",
        ["subject_type", "subject_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_operation_jobs_subject", table_name="operation_jobs")
    op.drop_index("ix_operation_jobs_status_created", table_name="operation_jobs")
    op.drop_table("operation_jobs")
    op.drop_index("ix_notifications_read_created", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_watch_rule_hits_subject", table_name="watch_rule_hits")
    op.drop_index("ix_watch_rule_hits_rule_created", table_name="watch_rule_hits")
    op.drop_table("watch_rule_hits")
    op.drop_index("ix_watch_rules_enabled_severity", table_name="watch_rules")
    op.drop_table("watch_rules")
