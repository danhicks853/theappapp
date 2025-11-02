"""Add user settings autonomy level and orchestrator decisions table.

Revision ID: 20251101_03
Revises: 20251101_02
Create Date: 2025-11-01 20:05:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251101_03"
down_revision = "20251101_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_settings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column(
            "autonomy_level",
            sa.String(length=10),
            nullable=False,
            server_default="medium",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", name="uq_user_settings_user"),
        sa.CheckConstraint(
            "autonomy_level IN ('low', 'medium', 'high')",
            name="ck_user_settings_autonomy_level",
        ),
    )

    op.create_table(
        "orchestrator_decisions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("decision_type", sa.String(length=50), nullable=False),
        sa.Column("situation", sa.JSON(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("decision", sa.JSON(), nullable=False),
        sa.Column("autonomy_level", sa.String(length=10), nullable=False),
        sa.Column("rag_context", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("tokens_input", sa.Integer(), nullable=True),
        sa.Column("tokens_output", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("execution_result", sa.JSON(), nullable=True),
        sa.CheckConstraint(
            "autonomy_level IN ('low', 'medium', 'high')",
            name="ck_orchestrator_decisions_autonomy_level",
        ),
    )
    op.create_index(
        "ix_orchestrator_decisions_project",
        "orchestrator_decisions",
        ["project_id"],
    )
    op.create_index(
        "ix_orchestrator_decisions_type",
        "orchestrator_decisions",
        ["decision_type"],
    )
    op.create_index(
        "ix_orchestrator_decisions_created",
        "orchestrator_decisions",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_orchestrator_decisions_created", table_name="orchestrator_decisions")
    op.drop_index("ix_orchestrator_decisions_type", table_name="orchestrator_decisions")
    op.drop_index("ix_orchestrator_decisions_project", table_name="orchestrator_decisions")
    op.drop_table("orchestrator_decisions")
    op.drop_table("user_settings")
