"""Unit tests for ProjectStateManager."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine

from backend.services.project_state_manager import (
    InMemoryCache,
    ProjectStateManager,
    ProjectStateNotFoundError,
    StateConflictError,
    StateRollbackError,
    project_state_snapshots_table,
    project_state_table,
    project_state_transactions_table,
)


@pytest.fixture()
def engine() -> Engine:
    engine = create_engine("sqlite:///:memory:", future=True)
    project_state_table.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


def seed_project_state(engine, overrides: Dict[str, object] | None = None) -> str:
    overrides = overrides or {}
    now = datetime.now(timezone.utc)
    values: Dict[str, object] = {
        "project_id": overrides.get("project_id", "proj-123"),
        "current_phase": overrides.get("current_phase", "initialization"),
        "active_task_id": overrides.get("active_task_id"),
        "active_agent_id": overrides.get("active_agent_id"),
        "completed_tasks": overrides.get("completed_tasks", []),
        "pending_tasks": overrides.get("pending_tasks", ["task-1"]),
        "metadata": overrides.get("metadata", {}),
        "status": overrides.get("status", "active"),
        "last_action": overrides.get("last_action"),
        "created_at": overrides.get("created_at", now),
        "last_updated": overrides.get("last_updated", now),
    }

    with engine.begin() as connection:
        connection.execute(project_state_table.insert().values(**values))

    return values["project_id"]  # type: ignore[return-value]


def test_get_state_uses_cache(engine) -> None:
    project_id = seed_project_state(engine)
    manager = ProjectStateManager(engine=engine, cache=InMemoryCache())

    snapshot = manager.get_state(project_id)
    assert snapshot.project_id == project_id
    assert snapshot.status == "active"

    with engine.begin() as connection:
        connection.execute(
            project_state_table.update()
            .where(project_state_table.c.project_id == project_id)
            .values(status="paused", last_updated=datetime.now(timezone.utc))
        )

    cached = manager.get_state(project_id)
    assert cached.status == "active"  # still cached

    refreshed = manager.get_state(project_id, use_cache=False)
    assert refreshed.status == "paused"


def test_update_state_merges_metadata_and_records_transaction(engine) -> None:
    project_id = seed_project_state(engine, overrides={"metadata": {"foo": "initial"}})
    manager = ProjectStateManager(engine=engine, cache=InMemoryCache())

    result = manager.update_state(
        project_id,
        phase="planning",
        metadata={"bar": "baz"},
        pending_tasks=["task-2"],
        last_action="Entered planning",
        actor="orchestrator",
    )

    assert result.current_phase == "planning"
    assert sorted(result.pending_tasks) == ["task-2"]
    assert result.metadata["foo"] == "initial"
    assert result.metadata["bar"] == "baz"
    assert result.last_action == "Entered planning"

    with engine.begin() as connection:
        tx_record = connection.execute(
            select(project_state_transactions_table)
            .where(project_state_transactions_table.c.project_id == project_id)
            .order_by(project_state_transactions_table.c.occurred_at.desc())
            .limit(1)
        ).mappings().first()

    assert tx_record is not None
    assert tx_record["change_type"] == "update_state"
    assert tx_record["payload"]["current_phase"] == "planning"
    assert tx_record["previous_state"]["current_phase"] == "initialization"


def test_record_task_completion_updates_lists_and_metadata(engine) -> None:
    project_id = seed_project_state(engine, overrides={"pending_tasks": ["task-1", "task-2"]})
    manager = ProjectStateManager(engine=engine, cache=InMemoryCache())

    snapshot = manager.record_task_completion(
        project_id,
        task_id="task-1",
        agent_id="agent-42",
        result_metadata={"outcome": "success"},
        actor="orchestrator",
    )

    assert "task-1" in snapshot.completed_tasks
    assert "task-1" not in snapshot.pending_tasks
    assert snapshot.metadata["task_results"]["task-1"]["outcome"] == "success"
    assert snapshot.metadata["task_owners"]["task-1"] == "agent-42"


def test_rollback_state_restores_previous_transaction(engine) -> None:
    project_id = seed_project_state(engine)
    manager = ProjectStateManager(engine=engine, cache=InMemoryCache())

    manager.update_state(project_id, status="paused", phase="execution", actor="tester")

    with engine.begin() as connection:
        transaction_id = connection.execute(
            select(project_state_transactions_table.c.id)
            .where(project_state_transactions_table.c.project_id == project_id)
            .order_by(project_state_transactions_table.c.occurred_at.desc())
            .limit(1)
        ).scalar_one()

    snapshot = manager.rollback_state(project_id, transaction_id=transaction_id, actor="tester")
    assert snapshot.status == "active"
    assert snapshot.current_phase == "initialization"


def test_create_snapshot_persists_state(engine) -> None:
    project_id = seed_project_state(engine)
    manager = ProjectStateManager(engine=engine, cache=InMemoryCache())

    snapshot_id = manager.create_snapshot(project_id, taken_by="system", notes="hourly")

    with engine.begin() as connection:
        stored = connection.execute(
            select(project_state_snapshots_table)
            .where(project_state_snapshots_table.c.id == snapshot_id)
            .limit(1)
        ).mappings().first()

    assert stored is not None
    assert stored["taken_by"] == "system"


def test_get_state_missing_project_raises(engine) -> None:
    manager = ProjectStateManager(engine=engine, cache=InMemoryCache())
    with pytest.raises(ProjectStateNotFoundError):
        manager.get_state("missing", use_cache=False)


def test_update_state_conflict_detection(engine) -> None:
    project_id = seed_project_state(engine)
    manager = ProjectStateManager(engine=engine, cache=InMemoryCache())

    snapshot = manager.get_state(project_id)

    manager.update_state(project_id, phase="execution")

    with pytest.raises(StateConflictError):
        manager.update_state(
            project_id,
            phase="planning",
            expected_last_updated=snapshot.last_updated,
        )


def test_update_state_sets_active_fields(engine) -> None:
    project_id = seed_project_state(engine)
    manager = ProjectStateManager(engine=engine, cache=InMemoryCache())

    snapshot = manager.update_state(
        project_id,
        active_task_id="task-42",
        active_agent_id="agent-007",
        status="paused",
        last_action="Paused for review",
        actor="system",
    )

    assert snapshot.active_task_id == "task-42"
    assert snapshot.active_agent_id == "agent-007"
    assert snapshot.status == "paused"
    assert snapshot.last_action == "Paused for review"


def test_update_state_no_changes_returns_snapshot(engine) -> None:
    project_id = seed_project_state(engine)
    manager = ProjectStateManager(engine=engine, cache=InMemoryCache())

    original = manager.get_state(project_id)
    updated = manager.update_state(project_id)

    assert updated == original


def test_update_state_missing_project_raises(engine) -> None:
    project_id = seed_project_state(engine)
    with engine.begin() as connection:
        connection.execute(project_state_table.delete())

    manager = ProjectStateManager(engine=engine, cache=InMemoryCache())

    with pytest.raises(ProjectStateNotFoundError):
        manager.update_state(project_id, phase="lost")


def test_record_task_completion_missing_project(engine) -> None:
    project_id = seed_project_state(engine)
    with engine.begin() as connection:
        connection.execute(project_state_table.delete())

    manager = ProjectStateManager(engine=engine, cache=InMemoryCache())

    with pytest.raises(ProjectStateNotFoundError):
        manager.record_task_completion(project_id, task_id="task-1", agent_id=None)


def test_rollback_state_snapshot(engine) -> None:
    project_id = seed_project_state(engine)
    manager = ProjectStateManager(engine=engine, cache=InMemoryCache())

    snapshot_id = manager.create_snapshot(project_id, taken_by="system")
    manager.update_state(project_id, status="paused", phase="mid", actor="system")

    restored = manager.rollback_state(project_id, snapshot_id=snapshot_id, actor="system")
    assert restored.status == "active"
    assert restored.current_phase == "initialization"


def test_rollback_state_restore_at(engine) -> None:
    project_id = seed_project_state(engine)
    manager = ProjectStateManager(engine=engine, cache=InMemoryCache())

    manager.update_state(project_id, status="paused", actor="system")
    restore_at = datetime.now(timezone.utc)
    manager.update_state(project_id, status="completed", phase="done", actor="system")

    restored = manager.rollback_state(project_id, restore_at=restore_at, actor="system")
    assert restored.status == "active"
    assert restored.current_phase == "initialization"


def test_rollback_state_requires_single_target(engine) -> None:
    project_id = seed_project_state(engine)
    manager = ProjectStateManager(engine=engine, cache=InMemoryCache())

    with pytest.raises(ValueError):
        manager.rollback_state(project_id, transaction_id="a", snapshot_id="b")


def test_rollback_state_missing_transaction_raises(engine) -> None:
    project_id = seed_project_state(engine)
    manager = ProjectStateManager(engine=engine, cache=InMemoryCache())

    with pytest.raises(StateRollbackError):
        manager.rollback_state(project_id, transaction_id="does-not-exist")


def test_rollback_state_missing_snapshot_raises(engine) -> None:
    project_id = seed_project_state(engine)
    manager = ProjectStateManager(engine=engine, cache=InMemoryCache())

    with pytest.raises(StateRollbackError):
        manager.rollback_state(project_id, snapshot_id="missing-snapshot")


def test_rollback_state_restore_at_no_match(engine) -> None:
    project_id = seed_project_state(engine)
    manager = ProjectStateManager(engine=engine, cache=InMemoryCache())

    with pytest.raises(StateRollbackError):
        manager.rollback_state(project_id, restore_at=datetime(2020, 1, 1, tzinfo=timezone.utc))


def test_get_state_parses_string_fields(engine) -> None:
    project_id = seed_project_state(engine)
    manager = ProjectStateManager(engine=engine, cache=InMemoryCache())

    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            UPDATE project_state
            SET completed_tasks='["done"]',
                pending_tasks='["pending"]',
                metadata='{"priority": "high"}',
                created_at='2025-11-01 10:00:00',
                last_updated='2025-11-01T10:05:00+00:00'
            WHERE project_id = ?
            """,
            (project_id,),
        )

    snapshot = manager.get_state(project_id, use_cache=False)
    assert snapshot.completed_tasks == ["done"]
    assert snapshot.pending_tasks == ["pending"]
    assert snapshot.metadata["priority"] == "high"
    assert snapshot.created_at.tzinfo is timezone.utc
    assert snapshot.last_updated.tzinfo is timezone.utc


def test_record_transaction_serializes_unknown_types(engine) -> None:
    project_id = seed_project_state(engine)
    manager = ProjectStateManager(engine=engine, cache=InMemoryCache())

    weird_state = {"odd": object()}
    with engine.begin() as connection:
        manager._record_transaction(
            connection=connection,
            project_id=project_id,
            change_type="custom",
            payload={},
            actor="tester",
            previous_state=weird_state,
        )

        record = connection.execute(
            select(project_state_transactions_table.c.previous_state)
            .where(project_state_transactions_table.c.change_type == "custom")
            .limit(1)
        ).scalar_one()

    assert record["odd"].startswith("<")  # object converted to string


def test_get_progress_handles_no_tasks(engine) -> None:
    project_id = seed_project_state(engine, overrides={"completed_tasks": [], "pending_tasks": []})
    manager = ProjectStateManager(engine=engine, cache=InMemoryCache())

    progress = manager.get_progress(project_id)
    assert progress.total_tasks == 0
    assert progress.completion_ratio == 0.0


def test_record_task_completion_without_agent_or_result(engine) -> None:
    project_id = seed_project_state(engine, overrides={"pending_tasks": ["task-1"]})
    manager = ProjectStateManager(engine=engine, cache=InMemoryCache())

    snapshot = manager.record_task_completion(project_id, task_id="task-1", agent_id=None, result_metadata=None)
    assert "task_results" not in snapshot.metadata
    assert snapshot.active_agent_id is None


def test_rollback_state_transaction_missing_previous(engine) -> None:
    project_id = seed_project_state(engine)
    manager = ProjectStateManager(engine=engine, cache=InMemoryCache())

    with engine.begin() as connection:
        connection.execute(
            project_state_transactions_table.insert().values(
                id="tx-1",
                project_id=project_id,
                occurred_at=datetime.now(timezone.utc),
                change_type="update",
                payload={},
                actor="tester",
                previous_state=None,
            )
        )

    with pytest.raises(StateRollbackError):
        manager.rollback_state(project_id, transaction_id="tx-1")


def test_helper_coerce_list_iterable(engine) -> None:
    manager = ProjectStateManager(engine=next(iter([]), None), cache=InMemoryCache())  # type: ignore[arg-type]
    result = manager._coerce_list(("a", "b"))
    assert result == ["a", "b"]


def test_helper_coerce_dict_iterable(engine) -> None:
    manager = ProjectStateManager(engine=next(iter([]), None), cache=InMemoryCache())  # type: ignore[arg-type]
    result = manager._coerce_dict({"a": 1})
    assert result == {"a": 1}
    fallback = manager._coerce_dict((("a", 1),), default={"b": 2})
    assert fallback == {"a": 1}


def test_helper_normalize_datetime_value_error(engine) -> None:
    manager = ProjectStateManager(engine=next(iter([]), None), cache=InMemoryCache())  # type: ignore[arg-type]
    dt = manager._normalize_datetime("2025-11-01 10:00:00")
    assert dt.tzinfo is timezone.utc


def test_helper_serialize_state_datetime(engine) -> None:
    manager = ProjectStateManager(engine=next(iter([]), None), cache=InMemoryCache())  # type: ignore[arg-type]
    state = {"when": datetime(2025, 11, 1, tzinfo=timezone.utc)}
    serialized = manager._serialize_state(state)
    assert serialized["when"].endswith("+00:00")
