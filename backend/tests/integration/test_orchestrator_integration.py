"""
Integration tests for Orchestrator core system.

Tests verify end-to-end orchestrator workflows including:
- Hub-and-spoke communication patterns
- Task queue with agent assignment
- Message routing and specialist consultation
- State management across operations
"""

import asyncio

from backend.services.orchestrator import (
    Orchestrator,
    Agent,
    Task,
    AgentType,
    MessageType
)


class TestOrchestratorHubAndSpokeWorkflow:
    """Test complete hub-and-spoke workflow."""
    
    def test_full_task_assignment_workflow(self):
        """Test complete workflow: enqueue → assign → route messages."""
        # Setup
        orchestrator = Orchestrator("project-1")
        
        backend_dev = Agent(
            agent_id="backend-1",
            agent_type=AgentType.BACKEND_DEVELOPER
        )
        qa_engineer = Agent(
            agent_id="qa-1",
            agent_type=AgentType.QA_ENGINEER
        )
        
        orchestrator.register_agent(backend_dev)
        orchestrator.register_agent(qa_engineer)
        
        # Create and enqueue task
        task = Task(
            task_id="task-1",
            task_type="implement_api",
            agent_type=AgentType.BACKEND_DEVELOPER,
            priority=5,
            payload={"endpoint": "/users", "method": "POST"}
        )
        orchestrator.enqueue_task(task)
        
        # Assign task to agent
        assert orchestrator.assign_task(task, "backend-1") is True
        
        # Verify state
        assert backend_dev.current_task_id == "task-1"
        assert backend_dev.status == "active"
        assert orchestrator.project_state.active_task_id == "task-1"
        
        # Backend dev asks QA for help
        orchestrator.route_message(
            sender_id="backend-1",
            recipient_id="qa-1",
            message_type=MessageType.HELP_REQUEST,
            payload={"question": "What test coverage is needed?"}
        )
        
        # Verify message routing
        assert len(orchestrator.message_buffer["qa-1"]) == 1
        message = orchestrator.message_buffer["qa-1"][0]
        assert message["sender_id"] == "backend-1"
        assert message["routed_through"] == orchestrator.orchestrator_id
    
    def test_specialist_consultation_workflow(self):
        """Test specialist consultation workflow."""
        orchestrator = Orchestrator("project-1")
        
        backend_dev = Agent(
            agent_id="backend-1",
            agent_type=AgentType.BACKEND_DEVELOPER
        )
        security_expert = Agent(
            agent_id="security-1",
            agent_type=AgentType.SECURITY_EXPERT
        )
        
        orchestrator.register_agent(backend_dev)
        orchestrator.register_agent(security_expert)
        
        # Backend dev needs security consultation
        consultation = orchestrator.consult_specialist(
            requesting_agent_id="backend-1",
            specialist_type=AgentType.SECURITY_EXPERT,
            question="Is JWT token validation sufficient?",
            context={
                "implementation": "RS256 with 24h expiry",
                "refresh_token": "enabled"
            }
        )
        
        # Verify consultation was routed
        assert consultation is not None
        assert consultation["specialist_id"] == "security-1"
        
        # Verify message in specialist's buffer
        assert len(orchestrator.message_buffer["security-1"]) == 1
        message = orchestrator.message_buffer["security-1"][0]
        assert message["message_type"] == MessageType.HELP_REQUEST.value
        assert message["payload"]["question"] == "Is JWT token validation sufficient?"
    
    def test_multiple_agents_multiple_tasks_workflow(self):
        """Test orchestrator managing multiple agents with multiple tasks."""
        orchestrator = Orchestrator("project-1")
        
        # Register multiple agents
        agents = {
            "backend-1": Agent("backend-1", AgentType.BACKEND_DEVELOPER),
            "frontend-1": Agent("frontend-1", AgentType.FRONTEND_DEVELOPER),
            "qa-1": Agent("qa-1", AgentType.QA_ENGINEER),
            "security-1": Agent("security-1", AgentType.SECURITY_EXPERT)
        }
        
        for agent in agents.values():
            orchestrator.register_agent(agent)
        
        # Enqueue multiple tasks with different priorities
        tasks = [
            Task("task-1", "implement_api", AgentType.BACKEND_DEVELOPER, priority=5),
            Task("task-2", "build_ui", AgentType.FRONTEND_DEVELOPER, priority=3),
            Task("task-3", "security_review", AgentType.SECURITY_EXPERT, priority=10),
            Task("task-4", "test_suite", AgentType.QA_ENGINEER, priority=4)
        ]
        
        for task in tasks:
            orchestrator.enqueue_task(task)
        
        # Verify queue has all tasks
        assert orchestrator.get_pending_count() == 4
        
        # Assign tasks (should dequeue in priority order)
        task_security = orchestrator.dequeue_task()
        assert task_security.task_id == "task-3"  # Highest priority
        orchestrator.assign_task(task_security, "security-1")
        
        task_api = orchestrator.dequeue_task()
        assert task_api.task_id == "task-1"
        orchestrator.assign_task(task_api, "backend-1")
        
        # Verify state reflects active tasks
        state = orchestrator.get_project_state()
        assert state.active_task_id == "task-1"  # Last assigned
        assert state.active_agent_id == "backend-1"
    
    def test_escalation_workflow(self):
        """Test escalation workflow with loop detection."""
        orchestrator = Orchestrator("project-1")
        
        agent = Agent("agent-1", AgentType.BACKEND_DEVELOPER, status="active")
        orchestrator.register_agent(agent)
        
        # Simulate task failure loop
        failures = []
        for i in range(3):
            task = Task(
                f"task-{i}",
                "implement_feature",
                AgentType.BACKEND_DEVELOPER,
                payload={"attempt": i + 1}
            )
            orchestrator.assign_task(task, "agent-1")
            failures.append(task)
        
        # After 3 failures, escalate to human
        gate_id = asyncio.run(
            orchestrator.escalate_to_human(
                reason="Loop detected: 3 identical failures",
                context={
                    "task_id": "task-2",
                    "error": "Timeout after 30 seconds",
                    "attempts": 3
                },
                agent_id="agent-1"
            )
        )
        
        # Verify escalation
        assert gate_id is not None
        assert agent.status == "paused"


class TestOrchestratorStateConsistency:
    """Test state consistency across operations."""
    
    def test_state_consistency_with_multiple_operations(self):
        """Test that state remains consistent through multiple operations."""
        orchestrator = Orchestrator("project-1")
        
        # Initial state
        initial_state = orchestrator.get_project_state()
        assert initial_state.current_phase == "initialization"
        
        # Update phase
        orchestrator.update_state(phase="planning")
        state = orchestrator.get_project_state()
        assert state.current_phase == "planning"
        
        # Register agents
        agents = [
            Agent(f"agent-{i}", AgentType.BACKEND_DEVELOPER)
            for i in range(3)
        ]
        for agent in agents:
            orchestrator.register_agent(agent)
        
        # Enqueue tasks
        for i in range(5):
            task = Task(
                f"task-{i}",
                "test",
                AgentType.BACKEND_DEVELOPER,
                priority=i
            )
            orchestrator.enqueue_task(task)
        
        # Assign tasks
        for i, agent in enumerate(agents):
            task = orchestrator.dequeue_task()
            orchestrator.assign_task(task, agent.agent_id)
        
        # Verify final state
        final_state = orchestrator.get_project_state()
        assert final_state.current_phase == "planning"
        assert final_state.active_agent_id == agents[-1].agent_id
        assert orchestrator.get_pending_count() == 2  # 5 - 3 assigned
    
    def test_state_persistence_across_operations(self):
        """Test that state persists across multiple operations."""
        orchestrator = Orchestrator("project-1")
        
        # Set initial state
        orchestrator.update_state(
            phase="development",
            metadata={"version": "1.0", "team_size": 5}
        )
        
        # Perform various operations
        agent = Agent("agent-1", AgentType.BACKEND_DEVELOPER)
        orchestrator.register_agent(agent)
        
        task = Task("task-1", "test", AgentType.BACKEND_DEVELOPER)
        orchestrator.enqueue_task(task)
        orchestrator.assign_task(task, "agent-1")
        
        # Verify state is still there
        state = orchestrator.get_project_state()
        assert state.current_phase == "development"
        assert state.metadata["version"] == "1.0"
        assert state.metadata["team_size"] == 5
        assert state.active_task_id == "task-1"


class TestOrchestratorMessageBuffering:
    """Test message buffering and retrieval."""
    
    def test_message_buffering_for_multiple_recipients(self):
        """Test that messages are correctly buffered for multiple recipients."""
        orchestrator = Orchestrator("project-1")
        
        agents = [
            Agent(f"agent-{i}", AgentType.BACKEND_DEVELOPER)
            for i in range(3)
        ]
        for agent in agents:
            orchestrator.register_agent(agent)
        
        # Send messages from agent 0 to agents 1 and 2
        orchestrator.route_message(
            sender_id="agent-0",
            recipient_id="agent-1",
            message_type=MessageType.TASK_RESULT,
            payload={"result": "success"}
        )
        
        orchestrator.route_message(
            sender_id="agent-0",
            recipient_id="agent-2",
            message_type=MessageType.TASK_RESULT,
            payload={"result": "success"}
        )
        
        # Verify messages are buffered separately
        assert len(orchestrator.message_buffer["agent-1"]) == 1
        assert len(orchestrator.message_buffer["agent-2"]) == 1
        assert len(orchestrator.message_buffer["agent-0"]) == 0
    
    def test_message_ordering_in_buffer(self):
        """Test that messages are buffered in order."""
        orchestrator = Orchestrator("project-1")
        
        sender = Agent("sender-1", AgentType.BACKEND_DEVELOPER)
        recipient = Agent("recipient-1", AgentType.FRONTEND_DEVELOPER)
        
        orchestrator.register_agent(sender)
        orchestrator.register_agent(recipient)
        
        # Send multiple messages
        for i in range(5):
            orchestrator.route_message(
                sender_id="sender-1",
                recipient_id="recipient-1",
                message_type=MessageType.PROGRESS_UPDATE,
                payload={"step": i}
            )
        
        # Verify messages are in order
        messages = orchestrator.message_buffer["recipient-1"]
        assert len(messages) == 5
        for i, message in enumerate(messages):
            assert message["payload"]["step"] == i


class TestOrchestratorAgentManagement:
    """Test agent lifecycle management through orchestrator."""
    
    def test_agent_status_transitions(self):
        """Test agent status transitions during operations."""
        orchestrator = Orchestrator("project-1")
        
        agent = Agent("agent-1", AgentType.BACKEND_DEVELOPER, status="idle")
        orchestrator.register_agent(agent)
        
        # Verify initial status
        assert agent.status == "idle"
        
        # Assign task - agent becomes active
        task = Task("task-1", "test", AgentType.BACKEND_DEVELOPER)
        orchestrator.assign_task(task, "agent-1")
        assert agent.status == "active"
        
        # Escalate - agent becomes paused
        asyncio.run(
            orchestrator.escalate_to_human(
                reason="Test",
                context={},
                agent_id="agent-1"
            )
        )
        assert agent.status == "paused"
    
    def test_multiple_agents_independent_states(self):
        """Test that multiple agents maintain independent states."""
        orchestrator = Orchestrator("project-1")
        
        agents = [
            Agent(f"agent-{i}", AgentType.BACKEND_DEVELOPER)
            for i in range(3)
        ]
        for agent in agents:
            orchestrator.register_agent(agent)
        
        # Assign different tasks to different agents
        for i, agent in enumerate(agents):
            task = Task(f"task-{i}", "test", AgentType.BACKEND_DEVELOPER)
            orchestrator.assign_task(task, agent.agent_id)
        
        # Verify each agent has its own task
        for i, agent in enumerate(agents):
            assert agent.current_task_id == f"task-{i}"
            assert agent.status == "active"
