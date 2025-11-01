"""Project state management system with persistence and caching.

Module: Project State Manager Service
Purpose: Maintain durable project state with caching, snapshots, and rollbacks

Reference: Decision 76 - Project State Recovery System
Task: 1.1.4 - Build project state management system
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, JSON, MetaData, String, Table, Text, select
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError


_METADATA = MetaData()

project_state_table = Table(
    "project_state",
    _METADATA,
    Column("project_id", String(36), primary_key=True),
    Column("current_phase", String(100), nullable=False),
    Column("active_task_id", String(100)),
    Column("active_agent_id", String(100)),
    Column("completed_tasks", JSON(), nullable=False),
    Column("pending_tasks", JSON(), nullable=False),
    Column("metadata", JSON(), nullable=False),
    Column("status", String(20), nullable=False),
    Column("last_action", Text()),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("last_updated", DateTime(timezone=True), nullable=False),
)

project_state_snapshots_table = Table(
    "project_state_snapshots",
    _METADATA,
    Column("id", String(36), primary_key=True),
    Column(
        "project_id",
        String(36),
        ForeignKey("project_state.project_id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("snapshot_at", DateTime(timezone=True), nullable=False),
    Column("state", JSON(), nullable=False),
    Column("taken_by", String(100)),
    Column("notes", Text()),
)

project_state_transactions_table = Table(
    "project_state_transactions",
    _METADATA,
    Column("id", String(36), primary_key=True),
    Column(
        "project_id",
        String(36),
        ForeignKey("project_state.project_id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("change_type", String(50), nullable=False),
    Column("payload", JSON(), nullable=False),
    Column("actor", String(100)),
    Column("previous_state", JSON()),
)


class StatePersistenceError(Exception):
    """Raised when project state cannot be persisted."""


class StateRollbackError(Exception):
    """Raised when rollback cannot be completed."""


class StateConflictError(Exception):
    """Raised when optimistic concurrency detects conflicting updates."""


class ProjectStateNotFoundError(Exception):
    """Raised when an existing project state record cannot be located."""


@dataclass(frozen=True)
class ProjectStateSnapshot:
    """Immutable representation of a project state record."""

    project_id: str
    current_phase: str
    active_task_id: Optional[str]
    active_agent_id: Optional[str]
    completed_tasks: List[str]
    pending_tasks: List[str]
    metadata: Dict[str, Any]
    status: str
    last_action: Optional[str]
    created_at: datetime
    last_updated: datetime


@dataclass(frozen=True)
class ProjectProgress:
    """Summary of project progress metrics."""

    project_id: str
    completed_tasks: int
    pending_tasks: int
    total_tasks: int
    completion_ratio: float
    status: str
    last_updated: datetime


class InMemoryCache:
    """Simple in-memory cache backing store."""

    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}

    def get(self, key: str) -> Any:
        return self._store.get(key)

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def delete(self, key: str) -> None:
        if key in self._store:
            del self._store[key]


class ProjectStateManager:
    """Manages project state persistence with write-through caching."""

    def __init__(
        self,
        *,
        engine: Engine,
        cache: Optional[InMemoryCache] = None,
        snapshot_interval_minutes: int = 5,
    ) -> None:
        self._engine = engine
        self._cache = cache or InMemoryCache()
        self._snapshot_interval_minutes = snapshot_interval_minutes

    def get_state(self, project_id: str, *, use_cache: bool = True) -> ProjectStateSnapshot:
        """Fetch current project state."""

        cache_key = self._cache_key(project_id)
        cached = self._cache.get(cache_key) if use_cache else None
        if cached is not None:
            return cached

        with self._engine.begin() as connection:
            row = self._fetch_state_row(connection, project_id)

        if row is None:
            raise ProjectStateNotFoundError(f"No state found for project {project_id}")

        snapshot = self._row_to_snapshot(row)
        self._cache.set(cache_key, snapshot)
        return snapshot

    def update_state(
        self,
        project_id: str,
        *,
        phase: Optional[str] = None,
        active_task_id: Optional[str] = None,
        active_agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        pending_tasks: Optional[Iterable[str]] = None,
        status: Optional[str] = None,
        last_action: Optional[str] = None,
        expected_last_updated: Optional[datetime] = None,
        actor: Optional[str] = None,
    ) -> ProjectStateSnapshot:
        """Apply targeted project state updates."""

        now = datetime.now(timezone.utc)
        with self._engine.begin() as connection:
            current_state = self._fetch_state_row(connection, project_id)
            if current_state is None:
                raise ProjectStateNotFoundError(f"No state found for project {project_id}")

            if expected_last_updated and not self._same_instant(
                expected_last_updated, current_state["last_updated"]
            ):
                raise StateConflictError("Project state was updated by another process")

            update_fields: Dict[str, Any] = {}
            if phase is not None:
                update_fields["current_phase"] = phase
            if active_task_id is not None:
                update_fields["active_task_id"] = active_task_id
            if active_agent_id is not None:
                update_fields["active_agent_id"] = active_agent_id
            if status is not None:
                update_fields["status"] = status
            if last_action is not None:
                update_fields["last_action"] = last_action
            if metadata is not None:
                merged_metadata = {
                    **self._coerce_dict(current_state.get("metadata"), {}),
                    **metadata,
                }
                update_fields["metadata"] = merged_metadata
            if pending_tasks is not None:
                update_fields["pending_tasks"] = list(pending_tasks)

            if not update_fields:
                return self._row_to_snapshot(current_state)

            update_fields["last_updated"] = now
            self._execute_update(
                connection=connection,
                project_id=project_id,
                update_fields=update_fields,
                actor=actor,
                change_type="update_state",
                previous_state=current_state,
            )

        self._cache.delete(self._cache_key(project_id))
        return self.get_state(project_id, use_cache=False)

    def record_task_completion(
        self,
        project_id: str,
        *,
        task_id: str,
        agent_id: Optional[str],
        result_metadata: Optional[Dict[str, Any]] = None,
        actor: Optional[str] = None,
    ) -> ProjectStateSnapshot:
        """Mark a task as complete and update project state."""

        now = datetime.now(timezone.utc)
        with self._engine.begin() as connection:
            current_state = self._fetch_state_row(connection, project_id)
            if current_state is None:
                raise ProjectStateNotFoundError(f"No state found for project {project_id}")

            completed_tasks = self._coerce_list(current_state.get("completed_tasks"))
            pending_tasks = self._coerce_list(current_state.get("pending_tasks"))
            metadata_payload = self._coerce_dict(current_state.get("metadata"), {})

            if task_id in pending_tasks:
                pending_tasks.remove(task_id)
            if task_id not in completed_tasks:
                completed_tasks.append(task_id)

            if result_metadata:
                task_results = metadata_payload.setdefault("task_results", {})
                task_results[task_id] = result_metadata

            if agent_id:
                task_owners = metadata_payload.setdefault("task_owners", {})
                task_owners[task_id] = agent_id

            update_fields = {
                "active_task_id": None,
                "active_agent_id": None,
                "completed_tasks": completed_tasks,
                "pending_tasks": pending_tasks,
                "metadata": metadata_payload,
                "last_action": f"Completed task {task_id}",
                "last_updated": now,
            }

            self._execute_update(
                connection=connection,
                project_id=project_id,
                update_fields=update_fields,
                actor=actor,
                change_type="record_task_completion",
                previous_state=current_state,
            )

        self._cache.delete(self._cache_key(project_id))
        return self.get_state(project_id, use_cache=False)

    def get_progress(self, project_id: str) -> ProjectProgress:
        """Return project progress summary."""

        snapshot = self.get_state(project_id)
        completed = len(snapshot.completed_tasks)
        pending = len(snapshot.pending_tasks)
        total = completed + pending
        completion_ratio = (completed / total) if total else 0.0
        return ProjectProgress(
            project_id=project_id,
            completed_tasks=completed,
            pending_tasks=pending,
            total_tasks=total,
            completion_ratio=completion_ratio,
            status=snapshot.status,
            last_updated=snapshot.last_updated,
        )

    def rollback_state(
        self,
        project_id: str,
        *,
        transaction_id: Optional[str] = None,
        snapshot_id: Optional[str] = None,
        restore_at: Optional[datetime] = None,
        actor: Optional[str] = None,
    ) -> ProjectStateSnapshot:
        """Restore state from transaction log or snapshot."""

        if sum(bool(value) for value in (transaction_id, snapshot_id, restore_at)) != 1:
            raise ValueError("Provide exactly one restore target")

        with self._engine.begin() as connection:
            current_state = self._fetch_state_row(connection, project_id)
            if current_state is None:
                raise ProjectStateNotFoundError(f"No state found for project {project_id}")

            target_state: Optional[Dict[str, Any]] = None

            if transaction_id:
                row = connection.execute(
                    select(project_state_transactions_table.c.previous_state)
                    .where(
                        project_state_transactions_table.c.id == transaction_id,
                        project_state_transactions_table.c.project_id == project_id,
                    )
                    .limit(1)
                ).mappings().first()
                if row and row["previous_state"]:
                    target_state = self._coerce_dict(row["previous_state"], {})
                else:
                    raise StateRollbackError("Transaction does not contain previous state")

            if snapshot_id:
                row = connection.execute(
                    select(project_state_snapshots_table.c.state)
                    .where(
                        project_state_snapshots_table.c.id == snapshot_id,
                        project_state_snapshots_table.c.project_id == project_id,
                    )
                    .limit(1)
                ).mappings().first()
                if row:
                    target_state = self._coerce_dict(row["state"], {})
                else:
                    raise StateRollbackError("Snapshot not found")

            if restore_at:
                normalized_restore = self._normalize_datetime(restore_at)
                row = connection.execute(
                    select(project_state_transactions_table.c.previous_state)
                    .where(
                        project_state_transactions_table.c.project_id == project_id,
                        project_state_transactions_table.c.occurred_at <= normalized_restore,
                    )
                    .order_by(project_state_transactions_table.c.occurred_at.desc())
                    .limit(1)
                ).mappings().first()
                if row:
                    target_state = self._coerce_dict(row["previous_state"], {})
                else:
                    raise StateRollbackError("No transaction available before restore_at")

            if not target_state:
                raise StateRollbackError("Unable to resolve rollback target state")

            try:
                connection.execute(
                    project_state_table.update()
                    .where(project_state_table.c.project_id == project_id)
                    .values(
                        current_phase=target_state.get("current_phase"),
                        active_task_id=target_state.get("active_task_id"),
                        active_agent_id=target_state.get("active_agent_id"),
                        completed_tasks=self._coerce_list(target_state.get("completed_tasks")),
                        pending_tasks=self._coerce_list(target_state.get("pending_tasks")),
                        metadata=self._coerce_dict(target_state.get("metadata"), {}),
                        status=target_state.get("status", "active"),
                        last_action=target_state.get("last_action"),
                        last_updated=datetime.now(timezone.utc),
                    )
                )
            except IntegrityError as exc:  # pragma: no cover
                raise StateRollbackError("Failed to apply rollback") from exc

            self._record_transaction(
                connection=connection,
                project_id=project_id,
                change_type="rollback_state",
                payload={
                    "transaction_id": transaction_id,
                    "snapshot_id": snapshot_id,
                    "restore_at": self._normalize_datetime(restore_at).isoformat()
                    if restore_at
                    else None,
                },
                actor=actor,
                previous_state=current_state,
            )

        self._cache.delete(self._cache_key(project_id))
        return self.get_state(project_id, use_cache=False)

    def create_snapshot(
        self,
        project_id: str,
        *,
        taken_by: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> str:
        """Persist a snapshot of the current state and return snapshot ID."""

        snapshot = self.get_state(project_id, use_cache=False)
        snapshot_id = self._generate_uuid()
        payload = self._snapshot_to_dict(snapshot)

        with self._engine.begin() as connection:
            connection.execute(
                project_state_snapshots_table.insert().values(
                    id=snapshot_id,
                    project_id=project_id,
                    snapshot_at=datetime.now(timezone.utc),
                    state=payload,
                    taken_by=taken_by,
                    notes=notes,
                )
            )

        return snapshot_id

    # ------------------------------------------------------------------
    # Internal helper methods
    # ------------------------------------------------------------------

    def _execute_update(
        self,
        *,
        connection: Connection,
        project_id: str,
        update_fields: Dict[str, Any],
        actor: Optional[str],
        change_type: str,
        previous_state: Dict[str, Any],
    ) -> None:
        try:
            connection.execute(
                project_state_table.update()
                .where(project_state_table.c.project_id == project_id)
                .values(**update_fields)
            )
        except IntegrityError as exc:  # pragma: no cover
            raise StatePersistenceError("Failed to update project state") from exc

        self._record_transaction(
            connection=connection,
            project_id=project_id,
            change_type=change_type,
            payload={key: value for key, value in update_fields.items() if key != "last_updated"},
            actor=actor,
            previous_state=previous_state,
        )

    def _record_transaction(
        self,
        *,
        connection: Connection,
        project_id: str,
        change_type: str,
        payload: Dict[str, Any],
        actor: Optional[str],
        previous_state: Optional[Dict[str, Any]],
    ) -> None:
        connection.execute(
            project_state_transactions_table.insert().values(
                id=self._generate_uuid(),
                project_id=project_id,
                occurred_at=datetime.now(timezone.utc),
                change_type=change_type,
                payload=payload,
                actor=actor,
                previous_state=self._serialize_state(previous_state) if previous_state else None,
            )
        )

    def _fetch_state_row(self, connection: Connection, project_id: str) -> Optional[Dict[str, Any]]:
        result = connection.execute(
            select(project_state_table).where(project_state_table.c.project_id == project_id).limit(1)
        ).mappings().first()
        return dict(result) if result else None

    def _row_to_snapshot(self, row: Dict[str, Any]) -> ProjectStateSnapshot:
        return ProjectStateSnapshot(
            project_id=row["project_id"],
            current_phase=row["current_phase"],
            active_task_id=row.get("active_task_id"),
            active_agent_id=row.get("active_agent_id"),
            completed_tasks=self._coerce_list(row.get("completed_tasks")),
            pending_tasks=self._coerce_list(row.get("pending_tasks")),
            metadata=self._coerce_dict(row.get("metadata"), {}),
            status=row["status"],
            last_action=row.get("last_action"),
            created_at=self._normalize_datetime(row["created_at"]),
            last_updated=self._normalize_datetime(row["last_updated"]),
        )

    @staticmethod
    def _coerce_list(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                return []
        return list(value)

    @staticmethod
    def _coerce_dict(value: Any, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if value is None:
            return dict(default or {})
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return dict(default or {})
        return dict(value)

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _serialize_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        serialized: Dict[str, Any] = {}
        for key, value in state.items():
            if isinstance(value, datetime):
                serialized[key] = self._normalize_datetime(value).isoformat()
            elif isinstance(value, (list, dict)):
                serialized[key] = value
            elif value is None or isinstance(value, (str, int, float, bool)):
                serialized[key] = value
            else:
                serialized[key] = str(value)
        return serialized

    def _snapshot_to_dict(self, snapshot: ProjectStateSnapshot) -> Dict[str, Any]:
        payload = asdict(snapshot)
        payload["created_at"] = self._normalize_datetime(snapshot.created_at).isoformat()
        payload["last_updated"] = self._normalize_datetime(snapshot.last_updated).isoformat()
        return payload

    @staticmethod
    def _same_instant(left: datetime, right: datetime) -> bool:
        return ProjectStateManager._normalize_datetime(left) == ProjectStateManager._normalize_datetime(right)

    @staticmethod
    def _cache_key(project_id: str) -> str:
        return f"project_state:{project_id}"

    @staticmethod
    def _generate_uuid() -> str:
        return uuid4().hex
