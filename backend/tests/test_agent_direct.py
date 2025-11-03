"""
Direct agent test - bypasses all orchestration.
Tests ONLY the agent's internal loop.
"""
import pytest
from unittest.mock import Mock, AsyncMock

from backend.agents.workshopper_agent import WorkshopperAgent
from backend.services.orchestrator import Task, AgentType


class MinimalLLMClient:
    """Minimal LLM that returns one action."""
    
    def __init__(self):
        self.call_count = 0
    
    async def plan_next_action(self, task_state, **kwargs):
        """Return action to write requirements.md."""
        self.call_count += 1
        
        print(f"\n💭 LLM Call #{self.call_count}")
        print(f"   Step: {task_state.current_step}/{task_state.max_steps}")
        print(f"   Goal: {task_state.goal[:80]}...")
        
        return {
            "description": "Write requirements.md",
            "tool_name": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": "test-proj",
                "task_id": "test-task",
                "path": "requirements.md",
                "content": "# Test Requirements\n\nUser story here."
            },
            "reasoning": "Writing requirements doc"
        }


@pytest.mark.asyncio
async def test_agent_loop_directly():
    """
    Test JUST the agent loop, no orchestrator.
    
    This will show us:
    - Does run_task() get called?
    - Does the while loop execute?
    - Does self-assessment run?
    - Does it exit properly?
    """
    print("\n" + "="*80)
    print("DIRECT AGENT LOOP TEST")
    print("="*80)
    print("\nTesting agent.run_task() directly...")
    print("Expected: 1 action, self-assess, exit")
    print("="*80 + "\n")
    
    # Create minimal orchestrator mock
    orchestrator = Mock()
    orchestrator.project_id = "test-proj"
    
    # Mock orchestrator.execute_tool (agent calls this, not tas_client)
    async def mock_execute_tool(request):
        print(f"   🔧 Tool executed: {request.get('tool', 'unknown')}")
        return {
            "status": "success",
            "result": {"status": "success", "path": "requirements.md"},
            "allowed": True
        }
    
    orchestrator.execute_tool = AsyncMock(side_effect=mock_execute_tool)
    
    # Create LLM client
    llm_client = MinimalLLMClient()
    
    # Create agent
    agent = WorkshopperAgent(
        agent_id="test-workshopper",
        orchestrator=orchestrator,
        llm_client=llm_client
    )
    
    # Create minimal task
    task = Task(
        task_id="test-task",
        task_type="workshopping",
        agent_type=AgentType.WORKSHOPPER,
        payload={
            "goal": "Write requirements.md with user stories",
            "id": "test-task",
            "project_id": "test-proj"
        },
        project_id="test-proj"
    )
    
    print("\n🚀 Calling agent.run_task()...\n")
    
    # Call run_task directly
    result = await agent.run_task(task)
    
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    print(f"\n✅ run_task() completed!")
    print(f"   Success: {result.success}")
    print(f"   Steps: {len(result.steps)}")
    print(f"   LLM Calls: {llm_client.call_count}")
    
    print("\n" + "="*80)
    print("ANALYSIS")
    print("="*80)
    
    if llm_client.call_count == 1:
        print("\n✅ PERFECT! Agent made 1 LLM call and exited")
        print("   Self-assessment worked!")
    elif llm_client.call_count > 1:
        print(f"\n❌ ISSUE: Agent made {llm_client.call_count} LLM calls")
        print("   Self-assessment NOT working - loop continued")
    else:
        print("\n❌ ISSUE: No LLM calls made")
        print("   run_task() didn't execute loop")
    
    print("\n" + "="*80)
    
    # Assert for test framework
    assert result.success, f"Expected success=True, got {result.success}"
    assert llm_client.call_count == 1, f"Expected 1 LLM call, got {llm_client.call_count}"
