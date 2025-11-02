"""
Real Orchestrator LLM Integration Tests

Tests the ACTUAL orchestrator LLM client with hybrid validation.
Uses the production code, not test mocks.
"""
import pytest
import os
from backend.services.orchestrator_llm_client import OrchestratorLLMClient


@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.slow
@pytest.mark.asyncio
class TestRealOrchestratorLLM:
    """Test real orchestrator LLM calls with validation."""
    
    @pytest.mark.asyncio
    async def test_orchestrator_agent_selection_real(self):
        """REAL TEST: Orchestrator selects agent with actual LLM call."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY not set")
        
        client = OrchestratorLLMClient(
            model="gpt-4o-mini",
            temperature=0.3
        )
        
        print("\n🔍 Making REAL orchestrator LLM call for agent selection...")
        
        decision = await client.select_agent(
            task_description="Implement user authentication with JWT tokens",
            candidate_agents=[
                {"agent_type": "backend_developer", "name": "Backend Dev 1"},
                {"agent_type": "security_expert", "name": "Security Expert 1"},
                {"agent_type": "database_expert", "name": "DB Expert 1"}
            ],
            project_context={
                "project_name": "TestApp",
                "current_phase": "development",
                "tech_stack": ["Python", "FastAPI", "PostgreSQL"]
            }
        )
        
        print(f"\n📊 Orchestrator Decision:")
        print(f"   Reasoning: {decision.reasoning[:100]}...")
        print(f"   Decision: {decision.decision}")
        print(f"   Confidence: {decision.confidence}")
        
        # Validate structure programmatically
        assert decision.reasoning is not None
        assert len(decision.reasoning) > 0
        assert decision.decision is not None
        assert isinstance(decision.decision, dict)
        assert 0.0 <= decision.confidence <= 1.0
        
        # Validate decision quality
        assert "action" in decision.decision or "agent" in decision.decision
        
        print(f"\n✅ Real orchestrator response validated!")
    
    @pytest.mark.asyncio
    async def test_orchestrator_progress_evaluation_real(self):
        """REAL TEST: Orchestrator evaluates progress with actual LLM."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY not set")
        
        client = OrchestratorLLMClient()
        
        print("\n🔍 Making REAL orchestrator LLM call for progress evaluation...")
        
        confidence = await client.evaluate_progress(
            progress_summary="Implemented authentication endpoints. All tests passing. Documentation complete.",
            project_context={
                "project_name": "TestApp",
                "goal": "Implement user authentication"
            }
        )
        
        print(f"\n📊 Progress Evaluation:")
        print(f"   Confidence Score: {confidence}")
        
        # Validate
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5, "Good progress should have confidence > 0.5"
        
        print(f"\n✅ Real orchestrator progress evaluation validated!")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
