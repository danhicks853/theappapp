"""Unit tests for AgentLifecycleManager lifecycle transitions and resource tracking."""

import pytest

from backend.services.agent_lifecycle_manager import (
    AgentLifecycleManager,
    AgentLifecycleSnapshot,
    AgentLifecycleState,
    AgentResources,
    LifecycleStateError,
)


@pytest.fixture()
def lifecycle_manager():
    events = []

    def callback(agent_id, state, payload):
        events.append((agent_id, state, payload))

    manager = AgentLifecycleManager(status_callback=callback)
    return manager, events


def test_start_agent_transitions_to_ready(lifecycle_manager):
    manager, events = lifecycle_manager
    initializer_called = False

    def initializer():
        nonlocal initializer_called
        initializer_called = True

    state = manager.start_agent("agent-1", initializer=initializer, metadata={"role": "developer"})

    assert initializer_called is True
    assert state is AgentLifecycleState.READY
    assert [event[1] for event in events] == [AgentLifecycleState.INITIALIZING, AgentLifecycleState.READY]

    snapshot = manager.get_agent_status("agent-1")
    assert snapshot.agent_id == "agent-1"
    assert snapshot.state is AgentLifecycleState.READY
    assert snapshot.metadata["role"] == "developer"


def test_resume_from_ready_sets_active_and_task_metadata(lifecycle_manager):
    manager, events = lifecycle_manager
    manager.start_agent("agent-2")

    state = manager.resume_agent("agent-2", metadata={"task_id": "task-42"})

    assert state is AgentLifecycleState.ACTIVE
    assert events[-1][1] is AgentLifecycleState.ACTIVE
    assert events[-1][2]["task_id"] == "task-42"

    snapshot = manager.get_agent_status("agent-2")
    assert snapshot.state is AgentLifecycleState.ACTIVE
    assert snapshot.last_known_task_id == "task-42"


@pytest.mark.parametrize("reason,gate_id", [("human_review", None), ("confidence_gate", "gate-9")])
def test_pause_sets_reason_and_gate(lifecycle_manager, reason, gate_id):
    manager, events = lifecycle_manager
    agent_id = "agent-3"
    manager.start_agent(agent_id)
    manager.resume_agent(agent_id)

    state = manager.pause_agent(agent_id, reason=reason, gate_id=gate_id)

    assert state is AgentLifecycleState.PAUSED
    payload = events[-1][2]
    assert payload["pause_reason"] == reason
    assert payload["gate_id"] == gate_id

    snapshot = manager.get_agent_status(agent_id)
    assert snapshot.state is AgentLifecycleState.PAUSED
    assert snapshot.pause_reason == reason
    assert snapshot.pause_gate_id == gate_id


@pytest.mark.parametrize("stop_state", [AgentLifecycleState.READY, AgentLifecycleState.ACTIVE, AgentLifecycleState.PAUSED])
def test_stop_and_cleanup_release_resources(lifecycle_manager, stop_state):
    manager, events = lifecycle_manager
    agent_id = f"agent-{stop_state.value}"
    manager.start_agent(agent_id)

    if stop_state is AgentLifecycleState.ACTIVE:
        manager.resume_agent(agent_id)
    elif stop_state is AgentLifecycleState.PAUSED:
        manager.resume_agent(agent_id)
        manager.pause_agent(agent_id, reason="gate", gate_id="gate-1")

    manager.update_resource_usage(
        agent_id,
        memory_mb=512.5,
        open_file_handles={"/tmp/file1"},
        database_connections={"db-conn"},
    )

    state = manager.stop_agent(agent_id, reason="completed")
    assert state is AgentLifecycleState.STOPPED
    assert events[-1][1] is AgentLifecycleState.STOPPED

    cleanup_state = manager.cleanup_agent(agent_id)
    assert cleanup_state is AgentLifecycleState.CLEANED_UP

    snapshot = manager.get_agent_status(agent_id)
    assert snapshot.state is AgentLifecycleState.CLEANED_UP
    assert snapshot.resources.memory_mb == 0.0
    assert snapshot.resources.open_file_handles == set()
    assert snapshot.resources.database_connections == set()


def test_update_resource_usage_and_notifications(lifecycle_manager):
    manager, events = lifecycle_manager
    manager.start_agent("agent-5")

    resources = manager.update_resource_usage(
        "agent-5",
        memory_mb=256.0,
        open_file_handles=["/tmp/a"],
        database_connections=["primary"],
    )

    assert isinstance(resources, AgentResources)
    assert resources.memory_mb == 256.0
    assert resources.open_file_handles == {"/tmp/a"}
    assert resources.database_connections == {"primary"}

    payload = events[-1][2]
    assert payload["resources"]["memory_mb"] == 256.0


def test_attach_gate_updates_paused_agent(lifecycle_manager):
    manager, events = lifecycle_manager
    manager.start_agent("agent-6")
    manager.resume_agent("agent-6")
    manager.pause_agent("agent-6", reason="awaiting_input")

    manager.attach_gate("agent-6", "gate-33")

    assert events[-1][1] is AgentLifecycleState.PAUSED
    assert events[-1][2]["gate_id"] == "gate-33"

    snapshot = manager.get_agent_status("agent-6")
    assert snapshot.pause_gate_id == "gate-33"


def test_invalid_transitions_raise_errors(lifecycle_manager):
    manager, _ = lifecycle_manager
    manager.start_agent("agent-7")

    with pytest.raises(LifecycleStateError):
        manager.pause_agent("agent-7", reason="not_active")

    manager.resume_agent("agent-7")
    manager.pause_agent("agent-7", reason="gate")

    manager.stop_agent("agent-7")
    with pytest.raises(LifecycleStateError):
        manager.resume_agent("agent-7")

    manager.cleanup_agent("agent-7")
    with pytest.raises(LifecycleStateError):
        manager.cleanup_agent("agent-7")


def test_start_after_cleanup_allows_restart(lifecycle_manager):
    manager, _ = lifecycle_manager
    manager.start_agent("agent-8")
    manager.stop_agent("agent-8")
    manager.cleanup_agent("agent-8")

    # Should reinitialize without error
    new_state = manager.start_agent("agent-8")

    assert new_state is AgentLifecycleState.READY


def test_snapshot_isolated_from_internal_state(lifecycle_manager):
    manager, _ = lifecycle_manager
    manager.start_agent("agent-9")
    manager.resume_agent("agent-9", metadata={"task_id": "task-init"})

    snapshot = manager.get_agent_status("agent-9")
    snapshot.resources.open_file_handles.add("/tmp/extra")

    fresh_snapshot = manager.get_agent_status("agent-9")
    assert "/tmp/extra" not in fresh_snapshot.resources.open_file_handles
    assert isinstance(snapshot, AgentLifecycleSnapshot)
