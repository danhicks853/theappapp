"""
Unit tests for Orchestrator core system.

Tests verify hub-and-spoke pattern enforcement, task queue operations,
agent registration, message routing, and state management.
"""

import pytest
from backend.services.orchestrator import (
    Orchestrator,
    Agent,
    Task,
    AgentType,
    TaskStatus,
    MessageType
)


class TestOrchestratorInitialization:
    """Test orchestrator initialization and basic properties."""
    
    def test_orchestrator_creation(self):
        """Test creating a new orchestrator instance."""
        project_id = "test-project-123"
        orchestrator = Orchestrator(project_id)
        
        assert orchestrator.project_id == project_id
        assert orchestrator.orchestrator_id is not None
        assert len(orchestrator.active_agents) == 0
        assert orchestrator.get_pending_count() == 0
        assert orchestrator.project_state.current_phase == "initialization"
    
    def test_orchestrator_has_unique_ids(self):
        """Test that each orchestrator gets a unique ID."""
        orch1 = Orchestrator("project-1")
        orch2 = Orchestrator("project-2")
        
        assert orch1.orchestrator_id != orch2.orchestrator_id
    
    def test_project_state_initialization(self):
        """Test that project state is properly initialized."""
        project_id = "test-project"
        orchestrator = Orchestrator(project_id)
        state = orchestrator.get_project_state()
        
        assert state.project_id == project_id
        assert state.current_phase == "initialization"
        assert state.active_task_id is None
        assert state.active_agent_id is None
        assert len(state.completed_tasks) == 0
        assert len(state.pending_tasks) == 0


class TestAgentRegistration:
    """Test agent registration and management."""
    
    def test_register_agent_success(self):
        """Test successfully registering an agent."""
        orchestrator = Orchestrator("project-1")
        agent = Agent(
            agent_id="agent-1",
            agent_type=AgentType.BACKEND_DEVELOPER
        )
        
        result = orchestrator.register_agent(agent)
        
        assert result is True
        assert orchestrator.get_agent("agent-1") == agent
    
    def test_register_duplicate_agent_fails(self):
        """Test that registering the same agent twice fails."""
        orchestrator = Orchestrator("project-1")
        agent = Agent(
            agent_id="agent-1",
            agent_type=AgentType.BACKEND_DEVELOPER
        )
        
        orchestrator.register_agent(agent)
        result = orchestrator.register_agent(agent)
        
        assert result is False
    
    def test_register_agent_without_id_raises_error(self):
        """Test that registering agent without ID raises ValueError."""
        orchestrator = Orchestrator("project-1")
        agent = Agent(
            agent_id="",
            agent_type=AgentType.BACKEND_DEVELOPER
        )
        
        with pytest.raises(ValueError):
            orchestrator.register_agent(agent)
    
    def test_register_agent_with_none_id_raises_error(self):
        """Test that registering agent with None ID raises ValueError."""
        orchestrator = Orchestrator("project-1")
        agent = Agent(
            agent_id=None,
            agent_type=AgentType.BACKEND_DEVELOPER
        )
        
        with pytest.raises(ValueError):
            orchestrator.register_agent(agent)
    
    def test_get_agent_returns_none_for_unknown_agent(self):
        """Test that getting unknown agent returns None."""
        orchestrator = Orchestrator("project-1")
        
        result = orchestrator.get_agent("unknown-agent")
        
        assert result is None
    
    def test_unregister_agent_success(self):
        """Test successfully unregistering an agent."""
        orchestrator = Orchestrator("project-1")
        agent = Agent(
            agent_id="agent-1",
            agent_type=AgentType.BACKEND_DEVELOPER
        )
        orchestrator.register_agent(agent)
        
        result = orchestrator.unregister_agent("agent-1")
        
        assert result is True
        assert orchestrator.get_agent("agent-1") is None
    
    def test_unregister_unknown_agent_fails(self):
        """Test that unregistering unknown agent fails."""
        orchestrator = Orchestrator("project-1")
        
        result = orchestrator.unregister_agent("unknown-agent")
        
        assert result is False
    
    def test_get_agents_by_type(self):
        """Test retrieving agents by type."""
        orchestrator = Orchestrator("project-1")
        
        backend_agent = Agent(
            agent_id="backend-1",
            agent_type=AgentType.BACKEND_DEVELOPER
        )
        frontend_agent = Agent(
            agent_id="frontend-1",
            agent_type=AgentType.FRONTEND_DEVELOPER
        )
        backend_agent_2 = Agent(
            agent_id="backend-2",
            agent_type=AgentType.BACKEND_DEVELOPER
        )
        
        orchestrator.register_agent(backend_agent)
        orchestrator.register_agent(frontend_agent)
        orchestrator.register_agent(backend_agent_2)
        
        backend_agents = orchestrator.get_agents_by_type(AgentType.BACKEND_DEVELOPER)
        
        assert len(backend_agents) == 2
        assert all(a.agent_type == AgentType.BACKEND_DEVELOPER for a in backend_agents)


class TestTaskQueue:
    """Test task queue operations."""
    
    def test_enqueue_task(self):
        """Test enqueueing a task."""
        orchestrator = Orchestrator("project-1")
        task = Task(
            task_id="task-1",
            task_type="code_review",
            agent_type=AgentType.QA_ENGINEER
        )
        
        orchestrator.enqueue_task(task)
        
        assert orchestrator.get_pending_count() == 1
    
    def test_enqueue_none_task_raises_error(self):
        """Test that enqueueing None raises ValueError."""
        orchestrator = Orchestrator("project-1")
        
        with pytest.raises(ValueError):
            orchestrator.enqueue_task(None)
    
    def test_dequeue_task(self):
        """Test dequeueing a task."""
        orchestrator = Orchestrator("project-1")
        task = Task(
            task_id="task-1",
            task_type="code_review",
            agent_type=AgentType.QA_ENGINEER
        )
        orchestrator.enqueue_task(task)
        
        dequeued = orchestrator.dequeue_task()
        
        assert dequeued.task_id == "task-1"
        assert orchestrator.get_pending_count() == 0
    
    def test_dequeue_empty_queue_returns_none(self):
        """Test that dequeueing from empty queue returns None."""
        orchestrator = Orchestrator("project-1")
        
        result = orchestrator.dequeue_task()
        
        assert result is None
    
    def test_peek_task(self):
        """Test peeking at next task without removing it."""
        orchestrator = Orchestrator("project-1")
        task = Task(
            task_id="task-1",
            task_type="code_review",
            agent_type=AgentType.QA_ENGINEER
        )
        orchestrator.enqueue_task(task)
        
        peeked = orchestrator.peek_task()
        
        assert peeked.task_id == "task-1"
        assert orchestrator.get_pending_count() == 1  # Still in queue
    
    def test_peek_empty_queue_returns_none(self):
        """Test that peeking at empty queue returns None."""
        orchestrator = Orchestrator("project-1")
        
        result = orchestrator.peek_task()
        
        assert result is None
    
    def test_task_priority_ordering(self):
        """Test that tasks are processed by priority (higher first)."""
        orchestrator = Orchestrator("project-1")
        
        low_priority = Task(
            task_id="task-low",
            task_type="documentation",
            agent_type=AgentType.DOCUMENTATION_EXPERT,
            priority=1
        )
        high_priority = Task(
            task_id="task-high",
            task_type="security_review",
            agent_type=AgentType.SECURITY_EXPERT,
            priority=10
        )
        medium_priority = Task(
            task_id="task-medium",
            task_type="code_review",
            agent_type=AgentType.QA_ENGINEER,
            priority=5
        )
        
        orchestrator.enqueue_task(low_priority)
        orchestrator.enqueue_task(high_priority)
        orchestrator.enqueue_task(medium_priority)
        
        # Should dequeue in priority order: high, medium, low
        assert orchestrator.dequeue_task().task_id == "task-high"
        assert orchestrator.dequeue_task().task_id == "task-medium"
        assert orchestrator.dequeue_task().task_id == "task-low"
    
    def test_same_priority_fifo_ordering(self):
        """Test FIFO ordering for tasks with same priority."""
        orchestrator = Orchestrator("project-1")
        
        task1 = Task(
            task_id="task-1",
            task_type="test",
            agent_type=AgentType.QA_ENGINEER,
            priority=5
        )
        task2 = Task(
            task_id="task-2",
            task_type="test",
            agent_type=AgentType.QA_ENGINEER,
            priority=5
        )
        task3 = Task(
            task_id="task-3",
            task_type="test",
            agent_type=AgentType.QA_ENGINEER,
            priority=5
        )
        
        orchestrator.enqueue_task(task1)
        orchestrator.enqueue_task(task2)
        orchestrator.enqueue_task(task3)
        
        # Should dequeue in FIFO order
        assert orchestrator.dequeue_task().task_id == "task-1"
        assert orchestrator.dequeue_task().task_id == "task-2"
        assert orchestrator.dequeue_task().task_id == "task-3"
    
    def test_prioritize_task_not_implemented(self):
        """Test that prioritize_task returns False (not yet implemented)."""
        orchestrator = Orchestrator("project-1")
        
        task = Task(
            task_id="task-1",
            task_type="test",
            agent_type=AgentType.QA_ENGINEER,
            priority=5
        )
        orchestrator.enqueue_task(task)
        
        # prioritize_task is a placeholder - should return False
        result = orchestrator.prioritize_task("task-1", 10)
        assert result is False


class TestTaskAssignment:
    """Test task assignment to agents."""
    
    def test_assign_task_to_agent(self):
        """Test assigning a task to an agent."""
        orchestrator = Orchestrator("project-1")
        agent = Agent(
            agent_id="agent-1",
            agent_type=AgentType.BACKEND_DEVELOPER
        )
        orchestrator.register_agent(agent)
        
        task = Task(
            task_id="task-1",
            task_type="implement_api",
            agent_type=AgentType.BACKEND_DEVELOPER
        )
        
        result = orchestrator.assign_task(task, "agent-1")
        
        assert result is True
        assert task.assigned_agent_id == "agent-1"
        assert task.status == TaskStatus.ASSIGNED
        assert agent.current_task_id == "task-1"
        assert agent.status == "active"
    
    def test_assign_task_to_unknown_agent_fails(self):
        """Test that assigning to unknown agent fails."""
        orchestrator = Orchestrator("project-1")
        task = Task(
            task_id="task-1",
            task_type="implement_api",
            agent_type=AgentType.BACKEND_DEVELOPER
        )
        
        result = orchestrator.assign_task(task, "unknown-agent")
        
        assert result is False
    
    def test_assign_none_task_raises_error(self):
        """Test that assigning None task raises ValueError."""
        orchestrator = Orchestrator("project-1")
        agent = Agent(
            agent_id="agent-1",
            agent_type=AgentType.BACKEND_DEVELOPER
        )
        orchestrator.register_agent(agent)
        
        with pytest.raises(ValueError):
            orchestrator.assign_task(None, "agent-1")
    
    def test_assign_task_updates_project_state(self):
        """Test that task assignment updates project state."""
        orchestrator = Orchestrator("project-1")
        agent = Agent(
            agent_id="agent-1",
            agent_type=AgentType.BACKEND_DEVELOPER
        )
        orchestrator.register_agent(agent)
        
        task = Task(
            task_id="task-1",
            task_type="implement_api",
            agent_type=AgentType.BACKEND_DEVELOPER
        )
        
        orchestrator.assign_task(task, "agent-1")
        state = orchestrator.get_project_state()
        
        assert state.active_task_id == "task-1"
        assert state.active_agent_id == "agent-1"


class TestMessageRouting:
    """Test message routing through orchestrator."""
    
    def test_route_message_between_agents(self):
        """Test routing a message from one agent to another."""
        orchestrator = Orchestrator("project-1")
        
        sender = Agent(
            agent_id="sender-1",
            agent_type=AgentType.BACKEND_DEVELOPER
        )
        recipient = Agent(
            agent_id="recipient-1",
            agent_type=AgentType.FRONTEND_DEVELOPER
        )
        
        orchestrator.register_agent(sender)
        orchestrator.register_agent(recipient)
        
        result = orchestrator.route_message(
            sender_id="sender-1",
            recipient_id="recipient-1",
            message_type=MessageType.HELP_REQUEST,
            payload={"question": "How should I structure the API?"}
        )
        
        assert result is True
        assert len(orchestrator.message_buffer["recipient-1"]) == 1
    
    def test_route_message_from_unknown_sender_raises_error(self):
        """Test that routing from unknown sender raises ValueError."""
        orchestrator = Orchestrator("project-1")
        
        recipient = Agent(
            agent_id="recipient-1",
            agent_type=AgentType.FRONTEND_DEVELOPER
        )
        orchestrator.register_agent(recipient)
        
        with pytest.raises(ValueError):
            orchestrator.route_message(
                sender_id="unknown-sender",
                recipient_id="recipient-1",
                message_type=MessageType.HELP_REQUEST,
                payload={}
            )
    
    def test_route_message_to_unknown_recipient_raises_error(self):
        """Test that routing to unknown recipient raises ValueError."""
        orchestrator = Orchestrator("project-1")
        
        sender = Agent(
            agent_id="sender-1",
            agent_type=AgentType.BACKEND_DEVELOPER
        )
        orchestrator.register_agent(sender)
        
        with pytest.raises(ValueError):
            orchestrator.route_message(
                sender_id="sender-1",
                recipient_id="unknown-recipient",
                message_type=MessageType.HELP_REQUEST,
                payload={}
            )
    
    def test_message_includes_orchestrator_routing_info(self):
        """Test that routed messages include orchestrator ID."""
        orchestrator = Orchestrator("project-1")
        
        sender = Agent(
            agent_id="sender-1",
            agent_type=AgentType.BACKEND_DEVELOPER
        )
        recipient = Agent(
            agent_id="recipient-1",
            agent_type=AgentType.FRONTEND_DEVELOPER
        )
        
        orchestrator.register_agent(sender)
        orchestrator.register_agent(recipient)
        
        orchestrator.route_message(
            sender_id="sender-1",
            recipient_id="recipient-1",
            message_type=MessageType.HELP_REQUEST,
            payload={"question": "test"}
        )
        
        message = orchestrator.message_buffer["recipient-1"][0]
        assert message["routed_through"] == orchestrator.orchestrator_id


class TestSpecialistConsultation:
    """Test specialist consultation workflow."""
    
    def test_consult_specialist_success(self):
        """Test consulting a specialist."""
        orchestrator = Orchestrator("project-1")
        
        requester = Agent(
            agent_id="backend-1",
            agent_type=AgentType.BACKEND_DEVELOPER
        )
        specialist = Agent(
            agent_id="security-1",
            agent_type=AgentType.SECURITY_EXPERT
        )
        
        orchestrator.register_agent(requester)
        orchestrator.register_agent(specialist)
        
        result = orchestrator.consult_specialist(
            requesting_agent_id="backend-1",
            specialist_type=AgentType.SECURITY_EXPERT,
            question="Is this authentication approach secure?",
            context={"approach": "JWT tokens"}
        )
        
        assert result is not None
        assert result["specialist_id"] == "security-1"
        assert result["specialist_type"] == "security_expert"
        assert "consultation_id" in result
    
    def test_consult_specialist_no_specialist_available(self):
        """Test consulting when no specialist of type is available."""
        orchestrator = Orchestrator("project-1")
        
        requester = Agent(
            agent_id="backend-1",
            agent_type=AgentType.BACKEND_DEVELOPER
        )
        orchestrator.register_agent(requester)
        
        result = orchestrator.consult_specialist(
            requesting_agent_id="backend-1",
            specialist_type=AgentType.SECURITY_EXPERT,
            question="Is this secure?",
            context={}
        )
        
        assert result is None


class TestEscalation:
    """Test escalation to human."""
    
    def test_escalate_to_human_creates_gate(self):
        """Test that escalation creates a gate ID."""
        orchestrator = Orchestrator("project-1")
        
        gate_id = orchestrator.escalate_to_human(
            reason="Loop detected after 3 failures",
            context={"task_id": "task-1", "error": "timeout"}
        )
        
        assert gate_id is not None
        assert len(gate_id) > 0
    
    def test_escalate_pauses_agent(self):
        """Test that escalation pauses the specified agent."""
        orchestrator = Orchestrator("project-1")
        
        agent = Agent(
            agent_id="agent-1",
            agent_type=AgentType.BACKEND_DEVELOPER,
            status="active"
        )
        orchestrator.register_agent(agent)
        
        orchestrator.escalate_to_human(
            reason="Test escalation",
            context={},
            agent_id="agent-1"
        )
        
        assert agent.status == "paused"
    
    def test_escalate_without_agent_id(self):
        """Test escalation without specifying an agent."""
        orchestrator = Orchestrator("project-1")
        
        gate_id = orchestrator.escalate_to_human(
            reason="Manual escalation",
            context={}
        )
        
        assert gate_id is not None


class TestStateManagement:
    """Test project state management."""
    
    def test_update_state_phase(self):
        """Test updating the current phase."""
        orchestrator = Orchestrator("project-1")
        
        orchestrator.update_state(phase="development")
        state = orchestrator.get_project_state()
        
        assert state.current_phase == "development"
    
    def test_update_state_metadata(self):
        """Test updating metadata."""
        orchestrator = Orchestrator("project-1")
        
        orchestrator.update_state(metadata={"key": "value", "count": 42})
        state = orchestrator.get_project_state()
        
        assert state.metadata["key"] == "value"
        assert state.metadata["count"] == 42
    
    def test_update_state_multiple_times(self):
        """Test updating state multiple times."""
        orchestrator = Orchestrator("project-1")
        
        orchestrator.update_state(phase="phase1", metadata={"step": 1})
        orchestrator.update_state(phase="phase2", metadata={"step": 2})
        
        state = orchestrator.get_project_state()
        assert state.current_phase == "phase2"
        assert state.metadata["step"] == 2
    
    def test_get_orchestrator_status(self):
        """Test getting comprehensive orchestrator status."""
        orchestrator = Orchestrator("project-1")
        
        agent = Agent(
            agent_id="agent-1",
            agent_type=AgentType.BACKEND_DEVELOPER
        )
        orchestrator.register_agent(agent)
        
        task = Task(
            task_id="task-1",
            task_type="test",
            agent_type=AgentType.BACKEND_DEVELOPER
        )
        orchestrator.enqueue_task(task)
        
        status = orchestrator.get_orchestrator_status()
        
        assert status["project_id"] == "project-1"
        assert status["active_agents_count"] == 1
        assert status["pending_tasks_count"] == 1
        assert "orchestrator_id" in status
        assert "created_at" in status


class TestTaskComparison:
    """Test Task comparison for PriorityQueue."""
    
    def test_task_less_than_comparison(self):
        """Test Task __lt__ method for ordering."""
        import time
        
        task1 = Task("task-1", "test", AgentType.BACKEND_DEVELOPER)
        time.sleep(0.01)  # Ensure different timestamps
        task2 = Task("task-2", "test", AgentType.BACKEND_DEVELOPER)
        
        # task1 should be less than task2 (created earlier)
        assert task1 < task2
        assert not (task2 < task1)
    
    def test_task_comparison_with_non_task_returns_not_implemented(self):
        """Test Task comparison with non-Task object."""
        task = Task("task-1", "test", AgentType.BACKEND_DEVELOPER)
        
        # Comparing with non-Task should return NotImplemented
        result = task.__lt__("not a task")
        assert result == NotImplemented


class TestHubAndSpokeEnforcement:
    """Test that hub-and-spoke pattern is enforced."""
    
    def test_all_agent_communication_through_orchestrator(self):
        """Test that all agent communication flows through orchestrator."""
        orchestrator = Orchestrator("project-1")
        
        agent1 = Agent(agent_id="agent-1", agent_type=AgentType.BACKEND_DEVELOPER)
        agent2 = Agent(agent_id="agent-2", agent_type=AgentType.FRONTEND_DEVELOPER)
        
        orchestrator.register_agent(agent1)
        orchestrator.register_agent(agent2)
        
        # Message should be routed through orchestrator
        orchestrator.route_message(
            sender_id="agent-1",
            recipient_id="agent-2",
            message_type=MessageType.HELP_REQUEST,
            payload={"test": "data"}
        )
        
        # Message should be in recipient's buffer (routed through orchestrator)
        assert len(orchestrator.message_buffer["agent-2"]) == 1
        message = orchestrator.message_buffer["agent-2"][0]
        assert message["routed_through"] == orchestrator.orchestrator_id
    
    def test_orchestrator_maintains_complete_state(self):
        """Test that orchestrator maintains complete project state."""
        orchestrator = Orchestrator("project-1")
        
        # Register multiple agents
        agents = [
            Agent(agent_id=f"agent-{i}", agent_type=AgentType.BACKEND_DEVELOPER)
            for i in range(3)
        ]
        for agent in agents:
            orchestrator.register_agent(agent)
        
        # Assign tasks
        for i, agent in enumerate(agents):
            task = Task(
                task_id=f"task-{i}",
                task_type="test",
                agent_type=AgentType.BACKEND_DEVELOPER
            )
            orchestrator.assign_task(task, agent.agent_id)
        
        # Verify orchestrator has complete visibility
        status = orchestrator.get_orchestrator_status()
        assert status["active_agents_count"] == 3
        assert status["active_task_id"] == "task-2"  # Last assigned
