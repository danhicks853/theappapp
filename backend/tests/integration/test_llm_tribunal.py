"""
LLM Tribunal Integration Tests

Tests LLM functionality using two-stage testing:
- Stage 1: Rubric Validation (structure)
- Stage 2: AI Tribunal (semantic quality)

Following Decision 72 - LLM Testing Strategy
"""
import pytest
from backend.tests.llm_tribunal_framework import (
    validate_llm_response_rubric,
    evaluate_llm_response_tribunal,
    RubricValidator
)


@pytest.mark.integration
@pytest.mark.llm
class TestGoalProximityLLMRubric:
    """Stage 1: Rubric validation for goal proximity."""
    
    def test_valid_goal_proximity_response(self):
        """Test valid response passes rubric."""
        response = {
            "proximity_score": 0.75,
            "reasoning": "Task is 75% complete. Login endpoint done, logout pending.",
            "evidence": "Files created: auth.py, test_auth.py. Login tests passing.",
            "confidence": 0.85
        }
        
        result = validate_llm_response_rubric(response, "goal_proximity")
        
        assert result.passed
        assert result.score >= 0.9
        assert len(result.errors) == 0
    
    def test_missing_required_field_fails_rubric(self):
        """Test missing field fails rubric."""
        response = {
            "proximity_score": 0.75,
            "reasoning": "Task is 75% complete.",
            # Missing evidence and confidence
        }
        
        result = validate_llm_response_rubric(response, "goal_proximity")
        
        assert not result.passed
        assert len(result.errors) > 0
        assert any("evidence" in err for err in result.errors)
        assert any("confidence" in err for err in result.errors)
    
    def test_invalid_score_range_fails_rubric(self):
        """Test score outside 0-1 fails rubric."""
        response = {
            "proximity_score": 1.5,  # Invalid: > 1
            "reasoning": "Task complete",
            "evidence": "All done",
            "confidence": 0.9
        }
        
        result = validate_llm_response_rubric(response, "goal_proximity")
        
        assert not result.passed
        assert any("proximity_score" in err and "0-1" in err for err in result.errors)
    
    def test_wrong_type_fails_rubric(self):
        """Test wrong field types fail rubric."""
        response = {
            "proximity_score": "seventy-five percent",  # Should be number
            "reasoning": "Task is 75% complete.",
            "evidence": "Files created",
            "confidence": 0.85
        }
        
        result = validate_llm_response_rubric(response, "goal_proximity")
        
        assert not result.passed
        assert any("proximity_score" in err and "number" in err for err in result.errors)
    
    def test_empty_reasoning_warns(self):
        """Test empty reasoning generates warning."""
        response = {
            "proximity_score": 0.75,
            "reasoning": "",  # Empty
            "evidence": "Files created",
            "confidence": 0.85
        }
        
        result = validate_llm_response_rubric(response, "goal_proximity")
        
        assert len(result.warnings) > 0
        assert any("reasoning" in warn for warn in result.warnings)
    
    def test_short_reasoning_warns(self):
        """Test very short reasoning generates warning."""
        response = {
            "proximity_score": 0.75,
            "reasoning": "Done",  # Too short
            "evidence": "Files created",
            "confidence": 0.85
        }
        
        result = validate_llm_response_rubric(response, "goal_proximity")
        
        assert len(result.warnings) > 0


@pytest.mark.integration
@pytest.mark.llm
class TestPromptImprovementLLMRubric:
    """Stage 1: Rubric validation for prompt improvements."""
    
    def test_valid_prompt_improvement_response(self):
        """Test valid AI assistant response passes rubric."""
        response = {
            "suggestions": [
                {
                    "suggestion": "Add more specific examples",
                    "rationale": "Examples help the model understand context better"
                },
                {
                    "suggestion": "Clarify output format",
                    "rationale": "Clear format reduces parsing errors"
                }
            ],
            "confidence": 0.8,
            "reasoning": "These improvements will enhance prompt clarity and reduce errors."
        }
        
        result = validate_llm_response_rubric(response, "prompt_improvement")
        
        assert result.passed
        assert result.score >= 0.9
        assert len(result.errors) == 0
    
    def test_empty_suggestions_warns(self):
        """Test empty suggestions list generates warning."""
        response = {
            "suggestions": [],
            "confidence": 0.8,
            "reasoning": "No improvements needed"
        }
        
        result = validate_llm_response_rubric(response, "prompt_improvement")
        
        assert len(result.warnings) > 0
        assert any("suggestions" in warn for warn in result.warnings)
    
    def test_malformed_suggestion_fails_rubric(self):
        """Test malformed suggestion object fails rubric."""
        response = {
            "suggestions": [
                {
                    "suggestion": "Add examples"
                    # Missing rationale
                }
            ],
            "confidence": 0.8,
            "reasoning": "Improvement suggestion"
        }
        
        result = validate_llm_response_rubric(response, "prompt_improvement")
        
        assert not result.passed
        assert any("rationale" in err for err in result.errors)


@pytest.mark.integration
@pytest.mark.llm
class TestConsistencyChecks:
    """Stage 0: Programmatic consistency checks (fast, free)."""
    
    def test_consistency_catches_score_reasoning_mismatch(self):
        """Programmatic check catches high score with negative reasoning."""
        from backend.tests.llm_tribunal_framework import ConsistencyChecker
        
        response = {
            "proximity_score": 0.95,
            "reasoning": "Task just started, no progress yet.",
            "evidence": "No files created.",
            "confidence": 0.9
        }
        
        issues = ConsistencyChecker.check_goal_proximity_consistency(response)
        
        # Should catch the inconsistency WITHOUT expensive API calls
        assert len(issues) > 0, "Should detect high score with negative reasoning"
        assert any("High score" in issue for issue in issues)
        print(f"\n✅ Caught inconsistency programmatically: {issues[0]}")


@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.slow  # Mark as slow - runs real API calls
@pytest.mark.asyncio
class TestGoalProximityAITribunal:
    """Stage 2: REAL AI tribunal evaluation using actual OpenAI API."""
    
    @pytest.mark.asyncio
    async def test_tribunal_evaluates_good_response(self, real_openai_client):
        """REAL TEST: Tribunal evaluates a good LLM response with actual API calls."""
        llm_response = {
            "proximity_score": 0.75,
            "reasoning": "Task is 75% complete. Login endpoint implemented and tested. Logout endpoint in progress.",
            "evidence": "Files created: auth.py (200 lines), test_auth.py (50 lines). Login tests passing (10/10). Logout implementation started.",
            "confidence": 0.85
        }
        
        context = {
            "task_goal": "Implement user authentication with login and logout",
            "current_state": "Login endpoint complete and tested. Logout endpoint partially implemented."
        }
        
        print("\n🔍 Calling REAL OpenAI tribunal with 3 judges...")
        verdict = await evaluate_llm_response_tribunal(
            llm_response,
            context,
            real_openai_client,  # REAL OpenAI client
            threshold=0.7
        )
        
        print(f"\n📊 Tribunal Verdict:")
        print(f"   Passed: {verdict.passed}")
        print(f"   Consensus Score: {verdict.consensus_score:.2f}")
        print(f"   Consensus Confidence: {verdict.consensus_confidence:.2f}")
        print(f"   Unanimous: {verdict.unanimous}")
        for judge in verdict.judge_evaluations:
            print(f"\n   Judge {judge.judge_id} ({judge.criteria.value}):")
            print(f"     Score: {judge.score:.2f}, Confidence: {judge.confidence:.2f}")
            print(f"     Reasoning: {judge.reasoning[:100]}...")
        
        # REAL assertions based on actual tribunal evaluation
        assert len(verdict.judge_evaluations) == 3
        assert verdict.consensus_score > 0  # Real judges should give scores
        assert verdict.consensus_confidence > 0
        # Good response should generally pass
        assert verdict.passed, f"Tribunal rejected good response: {verdict.reasoning}"
    
    @pytest.mark.asyncio
    async def test_tribunal_consensus_calculation(self, real_openai_client):
        """REAL TEST: Verify tribunal consensus calculation with real judges."""
        llm_response = {
            "proximity_score": 0.75,
            "reasoning": "Solid progress made on core features. Implementation is on track.",
            "evidence": "Multiple files created and tested. Test coverage at 80%.",
            "confidence": 0.8
        }
        
        context = {
            "task_goal": "Implement feature X with comprehensive testing",
            "current_state": "Feature 75% complete with good test coverage"
        }
        
        print("\n🔍 Testing REAL tribunal consensus calculation...")
        verdict = await evaluate_llm_response_tribunal(
            llm_response,
            context,
            real_openai_client
        )
        
        # Verify consensus is properly calculated
        assert len(verdict.judge_evaluations) == 3
        
        actual_avg_score = sum(j.score for j in verdict.judge_evaluations) / 3
        actual_avg_confidence = sum(j.confidence for j in verdict.judge_evaluations) / 3
        
        assert abs(verdict.consensus_score - actual_avg_score) < 0.01
        assert abs(verdict.consensus_confidence - actual_avg_confidence) < 0.01
        
        print(f"\n✅ Consensus correctly calculated:")
        print(f"   Average score: {actual_avg_score:.2f}")
        print(f"   Consensus score: {verdict.consensus_score:.2f}")


@pytest.mark.integration
@pytest.mark.llm
class TestOrchestratorLLMIntegration:
    """Test orchestrator LLM calls with rubric validation."""
    
    def test_rubric_validates_llm_response_structure(self):
        """Test rubric validator works with LLM-style responses."""
        from backend.tests.llm_tribunal_framework import RubricValidator
        
        # Simulate LLM response that needs parsing
        llm_text_response = """
SCORE: 0.75
REASONING: Task is 75% complete. Login done, logout pending.
EVIDENCE: Files created: auth.py, test_auth.py
CONFIDENCE: 0.85
        """
        
        # Parse into dict (this would be done by orchestrator)
        parsed_response = {
            "proximity_score": 0.75,
            "reasoning": "Task is 75% complete. Login done, logout pending.",
            "evidence": "Files created: auth.py, test_auth.py",
            "confidence": 0.85
        }
        
        # Validate structure with rubric
        rubric_result = RubricValidator.validate_goal_proximity_response(parsed_response)
        
        assert rubric_result.passed
        assert rubric_result.score >= 0.9
        assert "proximity_score" in parsed_response
        assert "reasoning" in parsed_response


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "llm"])
