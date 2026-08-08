"""Add normalized threat actors and event tracking links."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0005"
down_revision: str | None = "20260808_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "threat_actors",
        sa.Column("canonical_name", sa.String(length=200), nullable=False),
        sa.Column("canonical_key", sa.String(length=200), nullable=False),
        sa.Column("origin_country", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_threat_actors"),
        sa.UniqueConstraint("canonical_key", name="uq_threat_actors_canonical_key"),
    )
    op.create_index(
        "ix_threat_actors_canonical_name",
        "threat_actors",
        ["canonical_name"],
        unique=False,
    )
    op.create_table(
        "threat_actor_aliases",
        sa.Column("alias_key", sa.String(length=200), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("alias", sa.String(length=200), nullable=False),
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
            ["actor_id"],
            ["threat_actors.id"],
            ondelete="CASCADE",
            name="fk_threat_actor_aliases_actor_id_threat_actors",
        ),
        sa.PrimaryKeyConstraint("alias_key", name="pk_threat_actor_aliases"),
    )
    op.create_index(
        "ix_threat_actor_aliases_actor_id",
        "threat_actor_aliases",
        ["actor_id"],
        unique=False,
    )
    op.create_table(
        "event_actors",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("reported_name", sa.String(length=500), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
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
            "confidence BETWEEN 0 AND 100",
            name="ck_event_actors_event_actor_confidence_range",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["threat_actors.id"],
            ondelete="CASCADE",
            name="fk_event_actors_actor_id_threat_actors",
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["threat_events.id"],
            ondelete="CASCADE",
            name="fk_event_actors_event_id_threat_events",
        ),
        sa.PrimaryKeyConstraint("event_id", "actor_id", name="pk_event_actors"),
    )
    op.create_index(
        "ix_event_actors_actor_event",
        "event_actors",
        ["actor_id", "event_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_event_actors_actor_event", table_name="event_actors")
    op.drop_table("event_actors")
    op.drop_index("ix_threat_actor_aliases_actor_id", table_name="threat_actor_aliases")
    op.drop_table("threat_actor_aliases")
    op.drop_index("ix_threat_actors_canonical_name", table_name="threat_actors")
    op.drop_table("threat_actors")
