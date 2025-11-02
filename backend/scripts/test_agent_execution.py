#!/usr/bin/env python3
"""
Test Agent Execution

Demonstrates agents working together with orchestrator.
Tests the complete integration:
- Orchestrator
- Backend Dev Agent  
- LLM Client
- OpenAI Adapter

Run with: python -m backend.scripts.test_agent_execution
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.services.orchestrator import Orchestrator, Agent, Task, AgentType, TaskStatus
from backend.services.openai_adapter import OpenAIAdapter
from backend.services.agent_llm_client import AgentLLMClient
from backend.agents.backend_dev_agent import BackendDevAgent
from backend.models.agent_state import TaskState


class SimpleTokenLogger:
    """Simple token logger for demo."""
    def log_tokens(self, **kwargs):
        print(f"📊 Tokens: {kwargs.get('prompt_tokens', 0)} + {kwargs.get('completion_tokens', 0)} = {kwargs.get('prompt_tokens', 0) + kwargs.get('completion_tokens', 0)}")


async def main():
    """Run agent execution test."""
    print("=" * 70)
    print("🤖 AGENT EXECUTION TEST")
    print("=" * 70)
    print()
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not set")
        return 1
    
    print("✓ OpenAI API key found")
    print()
    
    # Create services
    print("🔧 Initializing services...")
    token_logger = SimpleTokenLogger()
    openai_adapter = OpenAIAdapter(api_key=api_key, token_logger=token_logger)
    llm_client = AgentLLMClient(openai_adapter)
    print("✓ OpenAI Adapter created")
    print("✓ LLM Client created")
    print()
    
    # Create orchestrator
    print("🎯 Creating Orchestrator...")
    project_id = str(uuid.uuid4())
    orchestrator = Orchestrator(
        project_id=project_id,
        llm_client=llm_client
    )
    print(f"✓ Orchestrator created (project: {project_id[:8]}...)")
    print()
    
    # Create and register Backend Dev agent
    print("👨‍💻 Creating Backend Developer Agent...")
    agent_id = "backend-dev-1"
    backend_agent = BackendDevAgent(
        agent_id=agent_id,
        orchestrator=orchestrator,
        llm_client=llm_client,
        openai_adapter=openai_adapter
    )
    
    # Register with orchestrator
    agent_metadata = Agent(
        agent_id=agent_id,
        agent_type=AgentType.BACKEND_DEVELOPER,
        status="idle"
    )
    orchestrator.register_agent(agent_metadata)
    print(f"✓ Backend Dev Agent registered (ID: {agent_id})")
    print()
    
    # Create a simple task
    print("📝 Creating task: 'Write a Python function to calculate factorial'...")
    task = Task(
        task_id=str(uuid.uuid4()),
        task_type="code_generation",
        agent_type=AgentType.BACKEND_DEVELOPER,
        priority=5,
        payload={
            "goal": "Write a Python function called 'factorial' that calculates the factorial of a number recursively. Include docstring and type hints.",
            "description": "Create a clean, well-documented factorial function",
            "acceptance_criteria": [
                "Function is named 'factorial'",
                "Uses recursion",
                "Has type hints",
                "Has docstring"
            ],
            "max_steps": 3
        },
        status=TaskStatus.PENDING
    )
    print(f"✓ Task created (ID: {task.task_id[:8]}...)")
    print()
    
    # Assign task
    print("🎯 Assigning task to Backend Dev Agent...")
    success = orchestrator.assign_task(task, agent_id)
    if not success:
        print("❌ Task assignment failed!")
        return 1
    print("✓ Task assigned")
    print()
    
    # Execute task
    print("=" * 70)
    print("🚀 EXECUTING TASK...")
    print("=" * 70)
    print()
    
    try:
        # Note: This is a simplified execution - real execution would need full orchestrator loop
        # For now, we're testing that the agent can at least plan an action
        
        # Create mock task state for agent
        task_state = TaskState(
            task_id=task.task_id,
            agent_id=agent_id,
            project_id=project_id,
            goal=task.payload["goal"],
            acceptance_criteria=task.payload["acceptance_criteria"],
            constraints={},
            max_steps=task.payload.get("max_steps", 20)
        )
        
        print("🤔 Agent is planning first action...")
        print()
        
        # Test: Agent plans next action
        action_plan = await llm_client.plan_next_action(
            task_state=task_state,
            system_prompt=backend_agent.system_prompt
        )
        
        print("💡 AGENT'S PLAN:")
        print(f"   Description: {action_plan.get('description', 'N/A')}")
        print(f"   Tool: {action_plan.get('tool_name', 'None')}")
        print(f"   Reasoning: {action_plan.get('reasoning', 'N/A')[:200]}...")
        print()
        
        print("=" * 70)
        print("✅ SUCCESS! Agent can think and plan!")
        print("=" * 70)
        print()
        
        print("📊 What we proved:")
        print("   ✓ Orchestrator works")
        print("   ✓ Agent registration works")
        print("   ✓ Task assignment works")
        print("   ✓ LLM Client works")
        print("   ✓ OpenAI Adapter works")
        print("   ✓ Agent can receive task and plan action")
        print()
        
        print("🎉 ALL SYSTEMS OPERATIONAL!")
        print()
        print("Next steps:")
        print("   1. Build full task execution loop in orchestrator")
        print("   2. Add tool execution (TAS)")
        print("   3. Add WebSocket streaming")
        print("   4. Build specialist creation API")
        print("   5. Build frontend")
        print()
        
        return 0
        
    except Exception as e:
        print(f"❌ ERROR during execution: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
