"""Add observable, evidence, ATT&CK, and event merge knowledge tables."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0006"
down_revision: str | None = "20260808_0005"
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
    op.add_column(
        "report_analyses",
        sa.Column("observables", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
    )
    op.add_column(
        "report_analyses",
        sa.Column(
            "attack_techniques",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
    )
    op.add_column("threat_events", sa.Column("superseded_by_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_threat_events_superseded_by_id_threat_events",
        "threat_events",
        "threat_events",
        ["superseded_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_threat_events_superseded_by_id",
        "threat_events",
        ["superseded_by_id"],
        unique=False,
    )

    op.create_table(
        "evidence",
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("subject_type", sa.String(length=50), nullable=False),
        sa.Column("subject_key", sa.String(length=1000), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=True),
        sa.Column("end_offset", sa.Integer(), nullable=True),
        sa.Column("locator", sa.String(length=500), nullable=True),
        sa.Column("evidence_type", sa.String(length=32), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "evidence_type IN ('direct', 'indirect', 'contradicting', 'analyst')",
            name="ck_evidence_evidence_type_value",
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["reports.id"],
            name="fk_evidence_report_id_reports",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evidence"),
    )
    op.create_index(
        "ix_evidence_report_subject",
        "evidence",
        ["report_id", "subject_type"],
        unique=False,
    )

    op.create_table(
        "observables",
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("value_original", sa.Text(), nullable=False),
        sa.Column("value_normalized", sa.Text(), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("validation_status", sa.String(length=32), nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_observables"),
        sa.UniqueConstraint("type", "value_normalized", name="uq_observables_type_value"),
    )
    op.create_index("ix_observables_last_seen", "observables", ["last_seen"], unique=False)

    op.create_table(
        "attack_techniques",
        sa.Column("technique_id", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("tactic", sa.String(length=100), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("technique_id", name="pk_attack_techniques"),
    )

    op.create_table(
        "report_observables",
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("observable_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "confidence BETWEEN 0 AND 100",
            name="ck_report_observables_report_observable_confidence_range",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence.id"],
            name="fk_report_observables_evidence_id_evidence",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["observable_id"],
            ["observables.id"],
            name="fk_report_observables_observable_id_observables",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["reports.id"],
            name="fk_report_observables_report_id_reports",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("report_id", "observable_id", name="pk_report_observables"),
    )
    op.create_index(
        "ix_report_observables_observable_report",
        "report_observables",
        ["observable_id", "report_id"],
        unique=False,
    )

    op.create_table(
        "event_observables",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("observable_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "confidence BETWEEN 0 AND 100",
            name="ck_event_observables_event_observable_confidence_range",
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["threat_events.id"],
            name="fk_event_observables_event_id_threat_events",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence.id"],
            name="fk_event_observables_evidence_id_evidence",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["observable_id"],
            ["observables.id"],
            name="fk_event_observables_observable_id_observables",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("event_id", "observable_id", name="pk_event_observables"),
    )
    op.create_index(
        "ix_event_observables_observable_event",
        "event_observables",
        ["observable_id", "event_id"],
        unique=False,
    )

    op.create_table(
        "report_techniques",
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("technique_id", sa.String(length=16), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "confidence BETWEEN 0 AND 100",
            name="ck_report_techniques_report_technique_confidence_range",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence.id"],
            name="fk_report_techniques_evidence_id_evidence",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["reports.id"],
            name="fk_report_techniques_report_id_reports",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["technique_id"],
            ["attack_techniques.technique_id"],
            name="fk_report_techniques_technique_id_attack_techniques",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("report_id", "technique_id", name="pk_report_techniques"),
    )
    op.create_index(
        "ix_report_techniques_technique_report",
        "report_techniques",
        ["technique_id", "report_id"],
        unique=False,
    )

    op.create_table(
        "event_techniques",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("technique_id", sa.String(length=16), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "confidence BETWEEN 0 AND 100",
            name="ck_event_techniques_event_technique_confidence_range",
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["threat_events.id"],
            name="fk_event_techniques_event_id_threat_events",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence.id"],
            name="fk_event_techniques_evidence_id_evidence",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["technique_id"],
            ["attack_techniques.technique_id"],
            name="fk_event_techniques_technique_id_attack_techniques",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("event_id", "technique_id", name="pk_event_techniques"),
    )
    op.create_index(
        "ix_event_techniques_technique_event",
        "event_techniques",
        ["technique_id", "event_id"],
        unique=False,
    )

    op.create_table(
        "event_merge_candidates",
        sa.Column("source_event_id", sa.Uuid(), nullable=False),
        sa.Column("target_event_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("moved_report_ids", sa.JSON(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "score BETWEEN 0 AND 100",
            name="ck_event_merge_candidates_event_merge_candidate_score_range",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'undone')",
            name="ck_event_merge_candidates_event_merge_candidate_status",
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_event_merge_candidates_event_merge_candidate_version_positive",
        ),
        sa.ForeignKeyConstraint(
            ["source_event_id"],
            ["threat_events.id"],
            name="fk_event_merge_candidates_source_event_id_threat_events",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_event_id"],
            ["threat_events.id"],
            name="fk_event_merge_candidates_target_event_id_threat_events",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_event_merge_candidates"),
        sa.UniqueConstraint(
            "source_event_id",
            "target_event_id",
            name="uq_event_merge_candidates_pair",
        ),
    )
    op.create_index(
        "ix_event_merge_candidates_status_score",
        "event_merge_candidates",
        ["status", "score"],
        unique=False,
    )
    op.create_index(
        "ix_event_merge_candidates_target_event",
        "event_merge_candidates",
        ["target_event_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_event_merge_candidates_target_event", table_name="event_merge_candidates")
    op.drop_index("ix_event_merge_candidates_status_score", table_name="event_merge_candidates")
    op.drop_table("event_merge_candidates")
    op.drop_index("ix_event_techniques_technique_event", table_name="event_techniques")
    op.drop_table("event_techniques")
    op.drop_index("ix_report_techniques_technique_report", table_name="report_techniques")
    op.drop_table("report_techniques")
    op.drop_index("ix_event_observables_observable_event", table_name="event_observables")
    op.drop_table("event_observables")
    op.drop_index("ix_report_observables_observable_report", table_name="report_observables")
    op.drop_table("report_observables")
    op.drop_table("attack_techniques")
    op.drop_index("ix_observables_last_seen", table_name="observables")
    op.drop_table("observables")
    op.drop_index("ix_evidence_report_subject", table_name="evidence")
    op.drop_table("evidence")
    op.drop_index("ix_threat_events_superseded_by_id", table_name="threat_events")
    op.drop_constraint(
        "fk_threat_events_superseded_by_id_threat_events",
        "threat_events",
        type_="foreignkey",
    )
    op.drop_column("threat_events", "superseded_by_id")
    op.drop_column("report_analyses", "attack_techniques")
    op.drop_column("report_analyses", "observables")
