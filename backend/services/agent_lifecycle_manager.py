"""Agent lifecycle management with resource tracking and gate integration."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from threading import RLock
from typing import Any, Callable, Dict, Iterable, Optional, Set


logger = logging.getLogger(__name__)


class LifecycleStateError(RuntimeError):
    """Raised when an invalid lifecycle transition is attempted."""


class AgentLifecycleState(Enum):
    """Lifecycle states an agent can occupy."""

    INITIALIZING = "initializing"
    READY = "ready"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    CLEANED_UP = "cleaned_up"


@dataclass(slots=True)
class AgentResources:
    """Tracks the resources allocated for an agent instance."""

    memory_mb: float = 0.0
    open_file_handles: Set[str] = field(default_factory=set)
    database_connections: Set[str] = field(default_factory=set)

    def reset(self) -> None:
        """Reset resource usage to defaults."""

        self.memory_mb = 0.0
        self.open_file_handles.clear()
        self.database_connections.clear()


@dataclass(slots=True)
class AgentLifecycleRecord:
    """Stores lifecycle metadata and resource usage for an agent."""

    agent_id: str
    state: AgentLifecycleState
    resources: AgentResources = field(default_factory=AgentResources)
    metadata: Dict[str, Any] = field(default_factory=dict)
    pause_reason: Optional[str] = None
    pause_gate_id: Optional[str] = None
    last_transition_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_known_task_id: Optional[str] = None


@dataclass(slots=True)
class AgentLifecycleSnapshot:
    """Immutable snapshot of an agent's lifecycle information."""

    agent_id: str
    state: AgentLifecycleState
    resources: AgentResources
    metadata: Dict[str, Any]
    pause_reason: Optional[str]
    pause_gate_id: Optional[str]
    last_transition_at: datetime
    last_known_task_id: Optional[str]


StatusCallback = Callable[[str, AgentLifecycleState, Dict[str, Any]], None]


class AgentLifecycleManager:
    """Manages agent lifecycle transitions and resource tracking."""

    def __init__(self, *, status_callback: Optional[StatusCallback] = None) -> None:
        self._records: Dict[str, AgentLifecycleRecord] = {}
        self._lock = RLock()
        self._status_callback = status_callback

    def set_status_callback(self, callback: Optional[StatusCallback]) -> None:
        """Configure callback invoked on lifecycle transitions."""

        with self._lock:
            self._status_callback = callback

    def register_agent(self, agent_id: str, *, metadata: Optional[Dict[str, Any]] = None) -> AgentLifecycleState:
        """Register a new agent and transition it to READY state."""

        return self.start_agent(agent_id, metadata=metadata)

    def start_agent(
        self,
        agent_id: str,
        *,
        initializer: Optional[Callable[[], Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentLifecycleState:
        """Start an agent and transition it to READY."""

        with self._lock:
            record = self._records.get(agent_id)

            if record and record.state not in {AgentLifecycleState.STOPPED, AgentLifecycleState.CLEANED_UP}:
                raise LifecycleStateError(
                    f"Agent {agent_id} cannot start from state {record.state.value}"
                )

            if record is None:
                record = AgentLifecycleRecord(agent_id=agent_id, state=AgentLifecycleState.INITIALIZING)
                self._records[agent_id] = record
            else:
                record.state = AgentLifecycleState.INITIALIZING

            if metadata:
                record.metadata.update(metadata)

            self._notify(agent_id, AgentLifecycleState.INITIALIZING, {"metadata": metadata or {}})

        if initializer:
            self._execute_initializer(initializer, agent_id)

        with self._lock:
            record = self._records[agent_id]
            record.state = AgentLifecycleState.READY
            record.last_transition_at = datetime.now(UTC)
            self._notify(agent_id, AgentLifecycleState.READY, {"metadata": metadata or {}})
            return record.state

    def _execute_initializer(self, initializer: Callable[[], Any], agent_id: str) -> None:
        try:
            result = initializer()
            if asyncio.iscoroutine(result):
                asyncio.run(result)  # pragma: no cover - defensive fallback
        except Exception:  # pragma: no cover - propagated to caller
            logger.exception("Agent %s initializer failed", agent_id)
            raise

    def resume_agent(
        self,
        agent_id: str,
        *,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentLifecycleState:
        """Resume an agent from READY or PAUSED state into ACTIVE."""

        with self._lock:
            record = self._ensure_record(agent_id)

            if record.state not in {AgentLifecycleState.READY, AgentLifecycleState.PAUSED}:
                raise LifecycleStateError(
                    f"Agent {agent_id} cannot resume from state {record.state.value}"
                )

            if record.state is AgentLifecycleState.PAUSED:
                record.pause_reason = None
                record.pause_gate_id = None

            if metadata:
                record.metadata.update(metadata)
                record.last_known_task_id = metadata.get("task_id", record.last_known_task_id)

            record.state = AgentLifecycleState.ACTIVE
            record.last_transition_at = datetime.now(UTC)

            payload = {"metadata": metadata or {}, "task_id": record.last_known_task_id}
            self._notify(agent_id, AgentLifecycleState.ACTIVE, payload)
            return record.state

    def pause_agent(
        self,
        agent_id: str,
        *,
        reason: str,
        gate_id: Optional[str] = None,
    ) -> AgentLifecycleState:
        """Pause an active agent, optionally associating it with a gate."""

        with self._lock:
            record = self._ensure_record(agent_id)

            if record.state is not AgentLifecycleState.ACTIVE:
                raise LifecycleStateError(
                    f"Agent {agent_id} cannot pause from state {record.state.value}"
                )

            record.state = AgentLifecycleState.PAUSED
            record.pause_reason = reason
            record.pause_gate_id = gate_id
            record.last_transition_at = datetime.now(UTC)

            payload = {"pause_reason": reason, "gate_id": gate_id}
            self._notify(agent_id, AgentLifecycleState.PAUSED, payload)
            return record.state

    def stop_agent(
        self,
        agent_id: str,
        *,
        reason: Optional[str] = None,
    ) -> AgentLifecycleState:
        """Gracefully stop an agent and mark it inactive."""

        with self._lock:
            record = self._ensure_record(agent_id)

            if record.state not in {
                AgentLifecycleState.READY,
                AgentLifecycleState.ACTIVE,
                AgentLifecycleState.PAUSED,
            }:
                raise LifecycleStateError(
                    f"Agent {agent_id} cannot stop from state {record.state.value}"
                )

            record.state = AgentLifecycleState.STOPPED
            record.metadata["stop_reason"] = reason
            record.last_transition_at = datetime.now(UTC)
            record.last_known_task_id = None

            payload = {"stop_reason": reason or ""}
            self._notify(agent_id, AgentLifecycleState.STOPPED, payload)
            return record.state

    def cleanup_agent(self, agent_id: str) -> AgentLifecycleState:
        """Release resources tracked for an agent and mark it CLEANED_UP."""

        with self._lock:
            record = self._ensure_record(agent_id)

            if record.state is not AgentLifecycleState.STOPPED:
                raise LifecycleStateError(
                    f"Agent {agent_id} cannot cleanup from state {record.state.value}"
                )

            record.resources.reset()
            record.metadata.pop("stop_reason", None)
            record.state = AgentLifecycleState.CLEANED_UP
            record.last_transition_at = datetime.now(UTC)

            self._notify(agent_id, AgentLifecycleState.CLEANED_UP, {})
            return record.state

    def update_resource_usage(
        self,
        agent_id: str,
        *,
        memory_mb: Optional[float] = None,
        open_file_handles: Optional[Iterable[str]] = None,
        database_connections: Optional[Iterable[str]] = None,
    ) -> AgentResources:
        """Update tracked resources for an agent."""

        with self._lock:
            record = self._ensure_record(agent_id)

            if memory_mb is not None:
                record.resources.memory_mb = memory_mb

            if open_file_handles is not None:
                record.resources.open_file_handles = set(open_file_handles)

            if database_connections is not None:
                record.resources.database_connections = set(database_connections)

            payload = {
                "resources": {
                    "memory_mb": record.resources.memory_mb,
                    "open_file_handles": list(record.resources.open_file_handles),
                    "database_connections": list(record.resources.database_connections),
                }
            }
            self._notify(agent_id, record.state, payload)
            return record.resources

    def attach_gate(self, agent_id: str, gate_id: str) -> None:
        """Associate a gate with a paused agent."""

        with self._lock:
            record = self._ensure_record(agent_id)
            if record.state is not AgentLifecycleState.PAUSED:
                raise LifecycleStateError(
                    f"Agent {agent_id} is not paused; cannot attach gate"
                )

            record.pause_gate_id = gate_id
            payload = {"pause_reason": record.pause_reason, "gate_id": gate_id}
            self._notify(agent_id, AgentLifecycleState.PAUSED, payload)

    def get_agent_status(self, agent_id: str) -> AgentLifecycleSnapshot:
        """Return an immutable snapshot for the agent's lifecycle state."""

        with self._lock:
            record = self._ensure_record(agent_id)
            snapshot = AgentLifecycleSnapshot(
                agent_id=record.agent_id,
                state=record.state,
                resources=AgentResources(
                    memory_mb=record.resources.memory_mb,
                    open_file_handles=set(record.resources.open_file_handles),
                    database_connections=set(record.resources.database_connections),
                ),
                metadata=dict(record.metadata),
                pause_reason=record.pause_reason,
                pause_gate_id=record.pause_gate_id,
                last_transition_at=record.last_transition_at,
                last_known_task_id=record.last_known_task_id,
            )
            return snapshot

    def _ensure_record(self, agent_id: str) -> AgentLifecycleRecord:
        record = self._records.get(agent_id)
        if not record:
            raise LifecycleStateError(f"Agent {agent_id} is not registered")
        return record

    def _notify(
        self,
        agent_id: str,
        state: AgentLifecycleState,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        callback = self._status_callback
        if not callback:
            return

        try:
            callback(agent_id, state, payload or {})
        except Exception:  # pragma: no cover - callback robustness
            logger.exception("Lifecycle status callback failed for agent %s", agent_id)
