"""Integration tests for database migrations."""

from __future__ import annotations

import pytest
import sqlalchemy as sa


@pytest.mark.integration
def test_all_migrations_apply(postgres_engine: sa.Engine, clean_database: None) -> None:
    """Ensure Alembic applies head migration and expected tables exist."""

    inspector = sa.inspect(postgres_engine)

    tables = set(inspector.get_table_names())
    expected_tables = {
        "agent_execution_history",
        "agent_execution_steps",
        "project_state",
        "project_state_snapshots",
        "project_state_transactions",
    }
    assert expected_tables.issubset(tables)

    history_columns = {col["name"] for col in inspector.get_columns("agent_execution_history")}
    expected_history = {
        "id",
        "agent_id",
        "task_id",
        "project_id",
        "started_at",
        "completed_at",
        "total_steps",
        "final_status",
        "escalation_reason",
        "total_cost_usd",
        "total_tokens",
        "state_snapshot",
    }
    assert expected_history.issubset(history_columns)

    step_columns = {col["name"] for col in inspector.get_columns("agent_execution_steps")}
    expected_steps = {
        "id",
        "execution_id",
        "step_number",
        "timestamp",
        "reasoning",
        "action",
        "result",
        "validation",
        "success",
        "tokens_used",
        "cost_usd",
    }
    assert expected_steps.issubset(step_columns)

    indexes = {index["name"] for index in inspector.get_indexes("agent_execution_steps")}
    assert "ix_agent_execution_steps_execution_id" in indexes

    snapshot_indexes = {index["name"] for index in inspector.get_indexes("project_state_snapshots")}
    assert "ix_project_state_snapshots_project_id" in snapshot_indexes

    transaction_indexes = {index["name"] for index in inspector.get_indexes("project_state_transactions")}
    assert "ix_project_state_transactions_project_id" in transaction_indexes

    postgres_engine.dispose()
