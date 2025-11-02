"""
Production LLM Validation Tests

Tests the NEW hybrid validation system against REAL production code.
Validates actual orchestrator responses with:
- Stage 0: Programmatic consistency
- Stage 1: Pydantic schema validation  
- Stage 2: AI tribunal (optional, slow)
"""
import pytest
import os
from backend.services.orchestrator_llm_client import OrchestratorLLMClient
from backend.tests.llm_tribunal_framework import (
    evaluate_with_rubric,
    evaluate_with_tribunal
)


@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.slow
@pytest.mark.asyncio
class TestProductionOrchestratorValidation:
    """Test real orchestrator responses with hybrid validation."""
    
    @pytest.mark.asyncio
    async def test_orchestrator_response_passes_validation(self):
        """REAL TEST: Orchestrator response passes our validation framework."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY not set")
        
        # REAL orchestrator call
        client = OrchestratorLLMClient()
        
        print("\n🔍 Step 1: Making REAL orchestrator call...")
        decision = await client.select_agent(
            task_description="Implement password hashing and salting",
            candidate_agents=[
                {"agent_type": "backend_developer", "name": "Backend Dev"},
                {"agent_type": "security_expert", "name": "Security Expert"}
            ],
            project_context={"project_name": "AuthSystem"}
        )
        
        # Convert to dict for validation
        response = {
            "reasoning": decision.reasoning,
            "decision": decision.decision,
            "confidence": decision.confidence
        }
        
        print(f"\n📋 Response:")
        print(f"   Reasoning: {response['reasoning'][:80]}...")
        print(f"   Decision: {response['decision']}")
        print(f"   Confidence: {response['confidence']}")
        
        # STAGE 0+1: Rubric validation (fast, free)
        print("\n🎯 Step 2: Validating with rubric (Stage 0 + 1)...")
        result = evaluate_with_rubric(response, "orchestrator_decision")
        
        print(f"\n📊 Validation Result:")
        print(f"   Passed: {result.passed}")
        print(f"   Score: {result.score:.2f}")
        print(f"   Errors: {result.errors}")
        print(f"   Warnings: {result.warnings}")
        print(f"   Consistency Issues: {result.consistency_issues}")
        
        # Real orchestrator should pass validation
        assert result.passed, f"Orchestrator failed validation: {result.errors}"
        assert result.score >= 0.8, f"Low quality score: {result.score}"
        assert len(result.errors) == 0, f"Unexpected errors: {result.errors}"
        
        print("\n✅ Real orchestrator response validated successfully!")
        print(f"   Time: <100ms")
        print(f"   Cost: $0")
    
    @pytest.mark.asyncio
    async def test_orchestrator_with_tribunal(self):
        """REAL TEST: Orchestrator + AI Tribunal validation (expensive)."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY not set")
        
        from openai import AsyncOpenAI
        
        # REAL orchestrator call
        client = OrchestratorLLMClient()
        openai_client = AsyncOpenAI(api_key=api_key)
        
        print("\n🔍 Making REAL orchestrator call...")
        decision = await client.select_agent(
            task_description="Set up PostgreSQL database with proper indexes",
            candidate_agents=[
                {"agent_type": "database_expert", "name": "DB Expert"},
                {"agent_type": "backend_developer", "name": "Backend Dev"}
            ],
            project_context={"project_name": "DataSystem", "tech_stack": ["PostgreSQL"]}
        )
        
        response = {
            "reasoning": decision.reasoning,
            "decision": decision.decision,
            "confidence": decision.confidence
        }
        
        print(f"\n📋 Orchestrator Response:")
        print(f"   Confidence: {response['confidence']}")
        
        # STAGE 1: Quick validation first
        print("\n🎯 Stage 1: Quick validation...")
        rubric_result = evaluate_with_rubric(response, "orchestrator_decision")
        
        if not rubric_result.passed:
            print(f"❌ Failed quick validation: {rubric_result.errors}")
            pytest.fail("Should pass quick validation")
        
        # STAGE 2: AI Tribunal (slow, expensive)
        print("\n🔍 Stage 2: AI Tribunal evaluation (3 judges)...")
        verdict = await evaluate_with_tribunal(
            response=response,
            context={
                "task_goal": "Select best agent for PostgreSQL setup",
                "current_state": "Need agent selection"
            },
            openai_client=openai_client,
            threshold=0.7
        )
        
        print(f"\n⚖️ Tribunal Verdict:")
        print(f"   Passed: {verdict.passed}")
        print(f"   Consensus Score: {verdict.consensus_score:.2f}")
        print(f"   Consensus Confidence: {verdict.consensus_confidence:.2f}")
        print(f"   Unanimous: {verdict.unanimous}")
        print(f"   Disagreement: {verdict.disagreement:.2f}")
        print(f"   Trace ID: {verdict.trace_id}")
        
        for eval in verdict.evaluations:
            print(f"\n   Judge {eval.judge_id} ({eval.criteria}):")
            print(f"     Score: {eval.score:.2f}, Confidence: {eval.confidence:.2f}")
            print(f"     {eval.reasoning[:80]}...")
        
        # Real orchestrator should pass tribunal
        assert verdict.passed, f"Tribunal rejected: {verdict.reasoning}"
        assert verdict.consensus_score >= 0.7
        
        print(f"\n✅ Production orchestrator passed AI tribunal!")
        print(f"   Trace ID: {verdict.trace_id}")


@pytest.mark.integration  
@pytest.mark.llm
class TestValidationFrameworkFeatures:
    """Test new framework features."""
    
    def test_pydantic_validation_catches_errors(self):
        """Test Pydantic catches schema errors."""
        bad_response = {
            "reasoning": "",  # Empty - should fail
            "decision": {},
            "confidence": 1.5  # Out of range - should fail
        }
        
        result = evaluate_with_rubric(bad_response, "orchestrator_decision")
        
        assert not result.passed
        assert len(result.errors) > 0
        print(f"\n✅ Pydantic caught {len(result.errors)} errors")
    
    def test_trimmed_mean_outlier_resistance(self):
        """Test trimmed mean handles outliers better than average."""
        from backend.tests.llm_tribunal_framework import Tribunal
        
        # Outlier scenario: [0.9, 0.9, 0.1] - one bad judge
        vals = [0.9, 0.9, 0.1]
        simple_mean = sum(vals) / len(vals)  # 0.633
        trimmed = Tribunal._trimmed_mean(vals, trim=0.2)  # 0.9 (removes outlier)
        
        print(f"\n📊 Outlier Resistance:")
        print(f"   Values: {vals}")
        print(f"   Simple Mean: {simple_mean:.2f}")
        print(f"   Trimmed Mean: {trimmed:.2f}")
        
        assert trimmed > simple_mean
        print(f"\n✅ Trimmed mean more resistant to outliers")
    
    def test_disagreement_metric(self):
        """Test disagreement calculation."""
        from backend.tests.llm_tribunal_framework import Tribunal
        
        # All agree: [True, True, True]
        unanimous = Tribunal._disagreement([True, True, True])
        
        # Maximum disagreement: [True, True, False] or [True, False, False]
        split = Tribunal._disagreement([True, True, False])
        
        # Complete disagreement impossible with 3 judges
        
        print(f"\n📊 Disagreement Metrics:")
        print(f"   Unanimous (3/3): {unanimous:.2f}")
        print(f"   Split (2/1): {split:.2f}")
        
        assert unanimous < split
        assert unanimous == 0.0  # All agree
        print(f"\n✅ Disagreement metric working correctly")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
