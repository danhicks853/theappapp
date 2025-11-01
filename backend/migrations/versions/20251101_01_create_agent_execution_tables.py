"""Create agent execution history tables.

Revision ID: 20251101_01
Revises: 
Create Date: 2025-11-01 17:23:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251101_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_execution_history",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("agent_id", sa.String(length=100), nullable=False),
        sa.Column("task_id", sa.String(length=100), nullable=False),
        sa.Column("project_id", sa.String(length=100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_steps", sa.Integer(), nullable=True),
        sa.Column("final_status", sa.String(length=50), nullable=True),
        sa.Column("escalation_reason", sa.Text(), nullable=True),
        sa.Column("total_cost_usd", sa.Numeric(10, 4), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("state_snapshot", sa.JSON(), nullable=True),
    )

    op.create_table(
        "agent_execution_steps",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("execution_id", sa.String(length=36), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("action", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("validation", sa.JSON(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(10, 4), nullable=True),
        sa.ForeignKeyConstraint(["execution_id"], ["agent_execution_history.id"], ondelete="CASCADE"),
    )

    op.create_index(
        "ix_agent_execution_steps_execution_id",
        "agent_execution_steps",
        ["execution_id", "step_number"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_execution_steps_execution_id", table_name="agent_execution_steps")
    op.drop_table("agent_execution_steps")
    op.drop_table("agent_execution_history")
