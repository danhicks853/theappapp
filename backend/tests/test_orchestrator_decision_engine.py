"""
Test Orchestrator LLM-Driven Decision Engine

Tests the core workflow intelligence: when a task completes,
orchestrator analyzes context and decides what happens next.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, MagicMock

from backend.services.orchestrator import Orchestrator, Task, TaskStatus, AgentType
from backend.agents.base_agent import TaskResult, Action


@pytest.fixture
def mock_llm_client():
    """Mock LLM client that returns decisions."""
    client = AsyncMock()
    
    # Mock decision: "Create PM task after Workshopper completes"
    client.query = AsyncMock(return_value={
        "action": "create_task",
        "reasoning": "Scope is complete. Need project manager to create detailed plan.",
        "next_agent_type": "project_manager",
        "task_description": "Review scope.md and create project plan with deliverables",
        "context_to_pass": {
            "files_to_reference": ["scope.md"],
            "key_information": "Simple web app project"
        },
        "urgency": "normal"
    })
    
    return client


@pytest.fixture
def mock_tas_client():
    """Mock TAS client for file operations."""
    tas = AsyncMock()
    
    # Mock file read: scope.md
    tas.execute_tool = AsyncMock(return_value={
        "success": True,
        "content": "# Project Scope\n\nBuild a simple hello world web app with a button."
    })
    
    return tas


@pytest.mark.asyncio
async def test_orchestrator_decision_after_task_completion(mock_llm_client, mock_tas_client):
    """
    Test: Orchestrator makes LLM decision when task completes.
    
    Flow:
    1. Workshopper completes scope planning task
    2. Orchestrator.on_task_completed() is called
    3. Orchestrator reads scope.md
    4. LLM analyzes and decides: "Create PM task"
    5. PM task is created and enqueued
    """
    print("\n" + "="*80)
    print("TEST: Orchestrator Decision Engine")
    print("="*80)
    
    # 1. Create orchestrator with mock LLM
    orchestrator = Orchestrator(
        project_id="test-project",
        llm_client=mock_llm_client,
        tas_client=mock_tas_client
    )
    
    # Set project goal for context
    orchestrator.project_state.goal = "Build hello world web app"
    orchestrator.project_state.current_phase = "planning"
    
    # Register a workshopper agent
    from backend.services.orchestrator import Agent
    workshopper = Agent(
        agent_id="workshopper-1",
        agent_type=AgentType.WORKSHOPPER,
        status="idle"
    )
    orchestrator.register_agent(workshopper)
    
    print("\n✓ Orchestrator initialized")
    print(f"  Project: {orchestrator.project_id}")
    print(f"  Goal: {orchestrator.project_state.goal}")
    print(f"  Registered agents: {len(orchestrator.active_agents)}")
    
    # 2. Create completed task (Workshopper finished scope)
    completed_task = Task(
        task_id="scope-planning-task",
        description="Analyze project requirements and create scope document",
        task_type="planning",
        agent_type=AgentType.WORKSHOPPER,
        priority=5,  # Normal priority
        status=TaskStatus.COMPLETED,
        project_id="test-project"
    )
    
    # 3. Create task result with artifacts
    task_result = TaskResult(
        task_id="scope-planning-task",
        success=True,
        steps=[
            Action(
                description="Created scope.md",
                tool_name="file_system",
                operation="write",
                parameters={"path": "scope.md"},
                reasoning="Document project scope"
            )
        ],
        artifacts=[
            {"filename": "scope.md", "type": "document"}
        ],
        summary="Scope planning complete. Created scope.md with project requirements.",
        progress_score=1.0
    )
    
    print("\n✓ Task completed")
    print(f"  Task: {completed_task.description}")
    print(f"  Agent: {completed_task.agent_type.value}")
    print(f"  Success: {task_result.success}")
    print(f"  Artifacts: {[a['filename'] for a in task_result.artifacts]}")
    
    # 4. Call orchestrator decision engine
    print("\n" + "-"*80)
    print("Calling Orchestrator.on_task_completed()...")
    print("-"*80)
    
    # Check queue is empty before
    initial_queue_size = orchestrator.task_queue.qsize()
    print(f"\nQueue size before: {initial_queue_size}")
    
    # THIS IS THE KEY METHOD - Orchestrator makes decision
    await orchestrator.on_task_completed(completed_task, task_result)
    
    # Check queue after
    final_queue_size = orchestrator.task_queue.qsize()
    print(f"Queue size after: {final_queue_size}")
    
    # 5. Verify LLM was called with context
    print("\n" + "-"*80)
    print("Verifying LLM was called...")
    print("-"*80)
    
    assert mock_llm_client.query.called, "LLM should be called for decision"
    
    # Get the prompt that was sent to LLM
    llm_call_args = mock_llm_client.query.call_args
    prompt = llm_call_args[0][0] if llm_call_args[0] else llm_call_args[1].get('prompt', '')
    
    print(f"\n✓ LLM called with prompt ({len(prompt)} chars)")
    print("\nPrompt excerpt:")
    print(prompt[:500] + "...\n")
    
    # Verify prompt contains key context
    assert "PROJECT GOAL: Build hello world web app" in prompt, "Prompt should include project goal"
    assert "workshopper" in prompt.lower(), "Prompt should mention completing agent"
    assert "scope" in prompt.lower(), "Prompt should mention scope"
    
    print("✓ Prompt includes:")
    print("  - Project goal")
    print("  - Completed task info")
    print("  - Available agents")
    
    # 6. Verify next task was created
    print("\n" + "-"*80)
    print("Verifying next task was created...")
    print("-"*80)
    
    assert final_queue_size > initial_queue_size, "New task should be enqueued"
    
    # Dequeue the task orchestrator created
    next_task = orchestrator.dequeue_task()
    
    assert next_task is not None, "Task should be in queue"
    assert next_task.agent_type == AgentType.PROJECT_MANAGER, "Should create PM task"
    
    print(f"\n✓ Next task created:")
    print(f"  Agent: {next_task.agent_type.value}")
    print(f"  Description: {next_task.description[:100]}...")
    print(f"  Has context: {next_task.metadata.get('context') is not None}")
    
    # Verify context was passed
    assert "scope.md" in next_task.description, "Task should reference scope.md"
    assert next_task.metadata.get('orchestrator_decision') is True, "Should be marked as orchestrator decision"
    assert next_task.metadata.get('previous_task_id') == completed_task.task_id, "Should link to previous task"
    
    context = next_task.metadata.get('context', {})
    assert 'files_to_reference' in context, "Context should include files"
    assert 'scope.md' in context['files_to_reference'], "Should reference scope.md"
    
    print("  - References scope.md ✓")
    print("  - Linked to previous task ✓")
    print("  - Context metadata included ✓")
    
    print("\n" + "="*80)
    print("✅ TEST PASSED: Orchestrator decision engine working!")
    print("="*80)
    print("\nWorkflow:")
    print("  1. Workshopper completed scope → ✓")
    print("  2. Orchestrator analyzed context → ✓")
    print("  3. LLM decided next step → ✓")
    print("  4. PM task created with context → ✓")
    print("\nThis is the core intelligence of the multi-agent system! 🎯")


@pytest.mark.asyncio
async def test_orchestrator_decision_project_complete():
    """
    Test: Orchestrator recognizes project completion.
    """
    print("\n" + "="*80)
    print("TEST: Orchestrator Detects Project Completion")
    print("="*80)
    
    # Mock LLM that says project is complete
    mock_llm = AsyncMock()
    mock_llm.query = AsyncMock(return_value={
        "action": "project_complete",
        "reasoning": "All deliverables are complete and validated. Project ready for deployment.",
        "urgency": "normal"
    })
    
    orchestrator = Orchestrator(
        project_id="test-project",
        llm_client=mock_llm,
        tas_client=AsyncMock()
    )
    
    orchestrator.project_state.goal = "Build hello world web app"
    orchestrator.project_state.status = "building"
    
    # Simulate final task completing
    final_task = Task(
        task_id="final-validation",
        description="Final project validation",
        task_type="validation",
        agent_type=AgentType.PROJECT_MANAGER,
        priority=5,
        status=TaskStatus.COMPLETED,
        project_id="test-project"
    )
    
    result = TaskResult(
        task_id="final-validation",
        success=True,
        steps=[],
        artifacts=[],
        summary="All deliverables validated",
        progress_score=1.0
    )
    
    print(f"\n✓ Final task: {final_task.description}")
    
    # Call decision engine
    await orchestrator.on_task_completed(final_task, result)
    
    # Verify project marked complete
    assert orchestrator.project_state.status == "completed", "Project should be marked complete"
    
    print(f"✓ Project status: {orchestrator.project_state.status}")
    print("\n✅ TEST PASSED: Orchestrator detected project completion!")


@pytest.mark.asyncio
async def test_orchestrator_decision_escalation():
    """
    Test: Orchestrator escalates to human when needed.
    """
    print("\n" + "="*80)
    print("TEST: Orchestrator Escalates to Human")
    print("="*80)
    
    # Mock LLM that escalates
    mock_llm = AsyncMock()
    mock_llm.query = AsyncMock(return_value={
        "action": "escalate_to_human",
        "reasoning": "Scope is unclear. Need human clarification on authentication requirements.",
        "urgency": "high"
    })
    
    mock_gate_manager = MagicMock()
    mock_gate_manager.create_gate = AsyncMock(return_value="gate-123")
    
    orchestrator = Orchestrator(
        project_id="test-project",
        llm_client=mock_llm,
        tas_client=AsyncMock(),
        gate_manager=mock_gate_manager
    )
    
    task = Task(
        task_id="unclear-scope",
        description="Define scope",
        task_type="planning",
        agent_type=AgentType.WORKSHOPPER,
        priority=5,
        status=TaskStatus.COMPLETED,
        project_id="test-project"
    )
    
    result = TaskResult(
        task_id="unclear-scope",
        success=False,
        steps=[],
        artifacts=[],
        summary="Scope unclear, needs clarification",
        progress_score=0.5
    )
    
    print(f"\n✓ Task: {task.description}")
    print(f"  Success: {result.success}")
    print(f"  Summary: {result.summary}")
    
    # Call decision engine
    await orchestrator.on_task_completed(task, result)
    
    # Verify escalation was created
    assert mock_gate_manager.create_gate.called, "Should create human gate"
    
    print(f"\n✓ Human gate created: gate-123")
    print("\n✅ TEST PASSED: Orchestrator escalated to human!")


if __name__ == "__main__":
    print("\nRunning Orchestrator Decision Engine Tests...\n")
    asyncio.run(test_orchestrator_decision_after_task_completion(
        mock_llm_client=Mock(),
        mock_tas_client=Mock()
    ))
