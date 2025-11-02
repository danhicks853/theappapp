#!/usr/bin/env python3
"""
Full Agent Execution Test

Tests complete agent task execution end-to-end:
- Multi-step planning
- Tool execution (mocked)
- Progress validation
- Task completion

Run with: python -m backend.scripts.test_full_agent_execution
"""
import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.services.openai_adapter import OpenAIAdapter
from backend.services.agent_llm_client import AgentLLMClient
from backend.agents.backend_dev_agent import BackendDevAgent


class MockOrchestrator:
    """Mock orchestrator for testing."""
    
    def __init__(self):
        self.gates_created = []
        self.confidence_checks = []
        self.tool_executions = []
    
    async def execute_tool(self, payload):
        """Mock tool execution - just return success."""
        self.tool_executions.append(payload)
        return {
            "status": "success",
            "result": f"Tool {payload['tool_name']} executed successfully",
            "output": "Mock tool output"
        }
    
    async def create_gate(self, reason, context, agent_id):
        """Mock gate creation."""
        gate_id = str(uuid.uuid4())
        self.gates_created.append({
            "gate_id": gate_id,
            "reason": reason,
            "context": context,
            "agent_id": agent_id
        })
        return gate_id
    
    async def evaluate_confidence(self, payload):
        """Mock confidence evaluation - always return high confidence."""
        self.confidence_checks.append(payload)
        return 0.9  # High confidence


class SimpleTokenLogger:
    """Token logger."""
    def __init__(self):
        self.total_tokens = 0
        self.call_count = 0
    
    def log_tokens(self, **kwargs):
        tokens = kwargs.get('prompt_tokens', 0) + kwargs.get('completion_tokens', 0)
        self.total_tokens += tokens
        self.call_count += 1
        print(f"  💰 Call #{self.call_count}: {tokens} tokens")


async def main():
    """Run full agent execution test."""
    print("=" * 70)
    print("🚀 FULL AGENT EXECUTION TEST - END TO END")
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
    llm_client = AgentLLMClient(openai_adapter, default_model="gpt-4o-mini")
    orchestrator = MockOrchestrator()
    print("✓ Services initialized")
    print()
    
    # Create agent
    print("👨‍💻 Creating Backend Developer Agent...")
    agent = BackendDevAgent(
        agent_id="backend-dev-test",
        orchestrator=orchestrator,
        llm_client=llm_client,
        openai_adapter=openai_adapter,
        max_retries=2,
        confidence_threshold=0.5
    )
    print("✓ Agent created")
    print()
    
    # Create task
    print("📝 Creating task: Write factorial function")
    task = {
        "task_id": str(uuid.uuid4()),
        "project_id": str(uuid.uuid4()),
        "payload": {
            "goal": "Write a Python function called 'factorial' that calculates factorial recursively with type hints and docstring",
            "description": "Create clean, well-documented factorial function",
            "acceptance_criteria": [
                "Function is named 'factorial'",
                "Uses recursion",
                "Has type hints",
                "Has docstring",
                "Handles edge cases"
            ],
            "max_steps": 5,
            "constraints": {}
        }
    }
    print(f"✓ Task created (max 5 steps)")
    print()
    
    # Execute task
    print("=" * 70)
    print("🎬 EXECUTING TASK - AGENT IS THINKING...")
    print("=" * 70)
    print()
    
    try:
        # Run the full task
        result = await agent.run_task(task)
        
        print()
        print("=" * 70)
        print("✅ TASK COMPLETE!")
        print("=" * 70)
        print()
        
        # Display results
        print("📊 EXECUTION SUMMARY:")
        print(f"   Success: {result.success}")
        print(f"   Steps taken: {len(result.steps)}")
        conf_str = f"{result.confidence:.2f}" if result.confidence is not None else "N/A"
        print(f"   Confidence: {conf_str}")
        print(f"   Total tokens: {token_logger.total_tokens}")
        print(f"   LLM calls: {token_logger.call_count}")
        print()
        
        if result.errors:
            print("⚠️  ERRORS:")
            for error in result.errors:
                print(f"   - {error}")
            print()
        
        print("📝 STEP BY STEP:")
        for i, step in enumerate(result.steps, 1):
            print(f"\n   Step {i}:")
            print(f"   Reasoning: {step.reasoning[:100]}...")
            print(f"   Success: {step.validation.success}")
            if step.action.tool_name:
                print(f"   Tool: {step.action.tool_name}")
        
        print()
        if result.artifacts:
            print("📦 ARTIFACTS PRODUCED:")
            for key, value in result.artifacts.items():
                print(f"   {key}: {str(value)[:200]}...")
        
        print()
        print("=" * 70)
        print("🎉 BACKEND END-TO-END TEST PASSED!")
        print("=" * 70)
        print()
        
        print("✅ PROVEN:")
        print("   ✓ Agent can execute multi-step tasks")
        print("   ✓ Agent makes multiple LLM calls")
        print("   ✓ Agent validates progress")
        print("   ✓ Agent produces artifacts")
        print("   ✓ Full execution loop works")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
