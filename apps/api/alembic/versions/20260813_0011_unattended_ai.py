"""Make AI automation unattended and enable automatic IOC management."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260813_0011"
down_revision: str | None = "20260809_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ai_processing_policies",
        sa.Column("unattended_mode", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "ai_processing_policies",
        sa.Column(
            "auto_manage_indicators",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
    )
    op.add_column(
        "ai_processing_policies",
        sa.Column(
            "indicator_auto_threshold",
            sa.Integer(),
            server_default="80",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_ai_processing_policies_ai_policy_indicator_threshold_range",
        "ai_processing_policies",
        "indicator_auto_threshold BETWEEN 0 AND 100",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_ai_processing_policies_ai_policy_indicator_threshold_range",
        "ai_processing_policies",
        type_="check",
    )
    op.drop_column("ai_processing_policies", "indicator_auto_threshold")
    op.drop_column("ai_processing_policies", "auto_manage_indicators")
    op.drop_column("ai_processing_policies", "unattended_mode")
