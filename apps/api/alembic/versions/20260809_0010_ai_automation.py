"""Add configurable AI automation and exception-driven review."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260809_0010"
down_revision: str | None = "20260808_0009"
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
        "ai_model_configs",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("api_key_ciphertext", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), server_default="90", nullable=False),
        sa.Column("temperature", sa.Float(), server_default="0.1", nullable=False),
        sa.Column("updated_by", sa.String(length=100), nullable=False),
        sa.Column("last_test_status", sa.String(length=32), nullable=True),
        sa.Column("last_test_error", sa.Text(), nullable=True),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "provider IN ('openai', 'deepseek', 'dashscope', 'siliconflow', 'ollama', 'custom')",
            name="ck_ai_model_configs_ai_model_config_provider_value",
        ),
        sa.CheckConstraint(
            "timeout_seconds BETWEEN 5 AND 300",
            name="ck_ai_model_configs_ai_model_config_timeout_range",
        ),
        sa.CheckConstraint(
            "temperature BETWEEN 0 AND 2",
            name="ck_ai_model_configs_ai_model_config_temperature_range",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ai_model_configs"),
        sa.UniqueConstraint("name", name="uq_ai_model_configs_name"),
    )
    op.create_index(
        "uq_ai_model_configs_default",
        "ai_model_configs",
        ["is_default"],
        unique=True,
        postgresql_where=sa.text("is_default IS TRUE"),
    )
    op.create_index(
        "ix_ai_model_configs_enabled_updated",
        "ai_model_configs",
        ["enabled", "updated_at"],
        unique=False,
    )
    op.create_table(
        "ai_processing_policies",
        sa.Column("key", sa.String(length=32), nullable=False),
        sa.Column("automation_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("require_verification", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("auto_create_events", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("relevance_threshold", sa.Integer(), server_default="60", nullable=False),
        sa.Column("auto_approve_threshold", sa.Integer(), server_default="85", nullable=False),
        sa.Column("auto_reject_threshold", sa.Integer(), server_default="20", nullable=False),
        sa.Column("minimum_evidence_coverage", sa.Integer(), server_default="70", nullable=False),
        sa.Column("max_article_chars", sa.Integer(), server_default="60000", nullable=False),
        sa.Column("updated_by", sa.String(length=100), server_default="system", nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "relevance_threshold BETWEEN 0 AND 100",
            name="ck_ai_processing_policies_ai_policy_relevance_range",
        ),
        sa.CheckConstraint(
            "auto_approve_threshold BETWEEN 0 AND 100",
            name="ck_ai_processing_policies_ai_policy_auto_approve_range",
        ),
        sa.CheckConstraint(
            "auto_reject_threshold BETWEEN 0 AND 100",
            name="ck_ai_processing_policies_ai_policy_auto_reject_range",
        ),
        sa.CheckConstraint(
            "minimum_evidence_coverage BETWEEN 0 AND 100",
            name="ck_ai_processing_policies_ai_policy_evidence_coverage_range",
        ),
        sa.CheckConstraint(
            "max_article_chars BETWEEN 5000 AND 200000",
            name="ck_ai_processing_policies_ai_policy_article_chars_range",
        ),
        sa.PrimaryKeyConstraint("key", name="pk_ai_processing_policies"),
    )
    op.execute(
        sa.text("INSERT INTO ai_processing_policies (key, updated_by) VALUES ('default', 'system')")
    )
    op.create_table(
        "ai_analysis_runs",
        sa.Column("report_id", sa.Uuid(), nullable=True),
        sa.Column("model_config_id", sa.Uuid(), nullable=True),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="running", nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column("evidence_coverage", sa.Integer(), nullable=True),
        sa.Column("input_chars", sa.Integer(), server_default="0", nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("result", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "stage IN ('analysis', 'verification', 'connection_test')",
            name="ck_ai_analysis_runs_ai_analysis_run_stage_value",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="ck_ai_analysis_runs_ai_analysis_run_status_value",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 100",
            name="ck_ai_analysis_runs_ai_analysis_run_confidence_range",
        ),
        sa.CheckConstraint(
            "evidence_coverage IS NULL OR evidence_coverage BETWEEN 0 AND 100",
            name="ck_ai_analysis_runs_ai_analysis_run_evidence_range",
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["reports.id"],
            name="fk_ai_analysis_runs_report_id_reports",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["model_config_id"],
            ["ai_model_configs.id"],
            name="fk_ai_analysis_runs_model_config_id_ai_model_configs",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ai_analysis_runs"),
    )
    op.create_index(
        "ix_ai_analysis_runs_report_created",
        "ai_analysis_runs",
        ["report_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_ai_analysis_runs_status_created",
        "ai_analysis_runs",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_ai_analysis_runs_config_created",
        "ai_analysis_runs",
        ["model_config_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "automation_exceptions",
        sa.Column("report_id", sa.Uuid(), nullable=True),
        sa.Column("exception_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=32), server_default="medium", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="open", nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("assigned_to", sa.String(length=100), nullable=True),
        sa.Column("resolved_by", sa.String(length=100), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_automation_exceptions_automation_exception_severity_value",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'resolved', 'dismissed')",
            name="ck_automation_exceptions_automation_exception_status_value",
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["reports.id"],
            name="fk_automation_exceptions_report_id_reports",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_automation_exceptions"),
    )
    op.create_index(
        "ix_automation_exceptions_status_created",
        "automation_exceptions",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_automation_exceptions_report_status",
        "automation_exceptions",
        ["report_id", "status"],
        unique=False,
    )
    with op.batch_alter_table("report_analyses") as batch_op:
        batch_op.add_column(
            sa.Column(
                "automation_status",
                sa.String(length=32),
                server_default="not_configured",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("ai_relevance_score", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("ai_classification", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("ai_summary", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("ai_claims", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False)
        )
        batch_op.add_column(
            sa.Column(
                "ai_verification", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False
            )
        )
        batch_op.add_column(sa.Column("evidence_coverage", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("decision_reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("model_config_id", sa.Uuid(), nullable=True))
        batch_op.create_check_constraint(
            "report_analysis_automation_status",
            "automation_status IN ('not_configured', 'processing', 'auto_approved', "
            "'needs_review', 'auto_rejected', 'fallback')",
        )
        batch_op.create_check_constraint(
            "report_analysis_ai_relevance_range",
            "ai_relevance_score IS NULL OR ai_relevance_score BETWEEN 0 AND 100",
        )
        batch_op.create_check_constraint(
            "report_analysis_evidence_coverage_range",
            "evidence_coverage IS NULL OR evidence_coverage BETWEEN 0 AND 100",
        )
        batch_op.create_foreign_key(
            "fk_report_analyses_model_config_id_ai_model_configs",
            "ai_model_configs",
            ["model_config_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_report_analyses_model_config", ["model_config_id"])


def downgrade() -> None:
    with op.batch_alter_table("report_analyses") as batch_op:
        batch_op.drop_index("ix_report_analyses_model_config")
        batch_op.drop_constraint(
            "fk_report_analyses_model_config_id_ai_model_configs", type_="foreignkey"
        )
        batch_op.drop_constraint("report_analysis_evidence_coverage_range", type_="check")
        batch_op.drop_constraint("report_analysis_ai_relevance_range", type_="check")
        batch_op.drop_constraint("report_analysis_automation_status", type_="check")
        batch_op.drop_column("model_config_id")
        batch_op.drop_column("decision_reason")
        batch_op.drop_column("evidence_coverage")
        batch_op.drop_column("ai_verification")
        batch_op.drop_column("ai_claims")
        batch_op.drop_column("ai_summary")
        batch_op.drop_column("ai_classification")
        batch_op.drop_column("ai_relevance_score")
        batch_op.drop_column("automation_status")
    op.drop_index("ix_automation_exceptions_report_status", table_name="automation_exceptions")
    op.drop_index("ix_automation_exceptions_status_created", table_name="automation_exceptions")
    op.drop_table("automation_exceptions")
    op.drop_index("ix_ai_analysis_runs_config_created", table_name="ai_analysis_runs")
    op.drop_index("ix_ai_analysis_runs_status_created", table_name="ai_analysis_runs")
    op.drop_index("ix_ai_analysis_runs_report_created", table_name="ai_analysis_runs")
    op.drop_table("ai_analysis_runs")
    op.drop_table("ai_processing_policies")
    op.drop_index("ix_ai_model_configs_enabled_updated", table_name="ai_model_configs")
    op.drop_index("uq_ai_model_configs_default", table_name="ai_model_configs")
    op.drop_table("ai_model_configs")
