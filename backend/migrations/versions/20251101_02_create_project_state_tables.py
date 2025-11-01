"""Create project state persistence tables.

Revision ID: 20251101_02
Revises: 20251101_01
Create Date: 2025-11-01 21:52:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251101_02"
down_revision = "20251101_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_state",
        sa.Column("project_id", sa.String(length=36), primary_key=True),
        sa.Column("current_phase", sa.String(length=100), nullable=False, server_default="initialization"),
        sa.Column("active_task_id", sa.String(length=100), nullable=True),
        sa.Column("active_agent_id", sa.String(length=100), nullable=True),
        sa.Column("completed_tasks", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("pending_tasks", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("last_action", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('active', 'paused', 'completed', 'failed')",
            name="ck_project_state_status_valid",
        ),
    )
    op.create_index(
        "ix_project_state_status",
        "project_state",
        ["status"],
    )

    op.create_table(
        "project_state_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("taken_by", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["project_state.project_id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_project_state_snapshots_project_id",
        "project_state_snapshots",
        ["project_id", "snapshot_at"],
    )

    op.create_table(
        "project_state_transactions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("change_type", sa.String(length=50), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("actor", sa.String(length=100), nullable=True),
        sa.Column("previous_state", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["project_state.project_id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_project_state_transactions_project_id",
        "project_state_transactions",
        ["project_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_project_state_transactions_project_id", table_name="project_state_transactions")
    op.drop_table("project_state_transactions")

    op.drop_index("ix_project_state_snapshots_project_id", table_name="project_state_snapshots")
    op.drop_table("project_state_snapshots")

    op.drop_index("ix_project_state_status", table_name="project_state")
    op.drop_table("project_state")
