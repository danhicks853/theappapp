"""
Tribunal Negative Control Tests

CI tests that must fail or trigger alerts.
Tests disagreement detection and indeterminate handling.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.tests.llm_tribunal_framework import evaluate_with_tribunal


class MockOpenAIClient:
    """Mock client that can queue responses or errors."""
    
    def __init__(self):
        self.responses = []
        self.errors = []
        self.call_count = 0
        
    def queue_json_responses(self, responses):
        """Queue JSON responses for judges."""
        self.responses = responses
        
    def queue_errors_once(self, error_type):
        """Queue an error for the first judge."""
        self.errors = [error_type]
    
    async def create_completion(self, **kwargs):
        """Simulate API call."""
        idx = self.call_count
        self.call_count += 1
        
        # Check for queued error
        if idx < len(self.errors):
            if self.errors[idx] == "parse_error":
                raise ValueError("Simulated parse error")
        
        # Return queued response
        if idx < len(self.responses):
            import json
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(
                    content=json.dumps(self.responses[idx])
                ))
            ]
            return mock_response
        
        # Default response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(
                content='{"score": 0.9, "confidence": 0.9, "reasoning": "default"}'
            ))
        ]
        return mock_response


@pytest.fixture
def mock_client():
    """Create mock OpenAI client."""
    client = MagicMock()
    
    # Create completion handler
    mock_handler = MockOpenAIClient()
    
    async def mock_create(**kwargs):
        return await mock_handler.create_completion(**kwargs)
    
    client.chat.completions.create = AsyncMock(side_effect=mock_create)
    client._mock_handler = mock_handler
    
    return client


@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.asyncio
class TestTribunalNegativeControls:
    """Negative control tests for tribunal."""
    
    @pytest.mark.asyncio
    async def test_tribunal_disagreement_alert(self, mock_client):
        """Test high disagreement triggers alert."""
        # Queue responses with high disagreement: [0.95, 0.4, 0.55]
        mock_client._mock_handler.queue_json_responses([
            {"score": 0.95, "confidence": 0.9, "reasoning": "Looks great"},
            {"score": 0.4, "confidence": 0.9, "reasoning": "Not good"},
            {"score": 0.55, "confidence": 0.9, "reasoning": "Mediocre"}
        ])
        
        response = {
            "proximity_score": 0.6,
            "reasoning": "x" * 20,
            "evidence": "y",
            "confidence": 0.8
        }
        
        context = {
            "task_goal": "Test task",
            "current_state": "Test state"
        }
        
        verdict = await evaluate_with_tribunal(
            response=response,
            context=context,
            openai_client=mock_client,
            threshold=0.6
        )
        
        # Should have high disagreement
        assert verdict.disagreement > 0.3, f"Expected high disagreement, got {verdict.disagreement}"
        print(f"\n✅ High disagreement detected: {verdict.disagreement:.2f}")
    
    @pytest.mark.asyncio
    async def test_tribunal_indeterminate_on_parse_error(self, mock_client):
        """Test parse error triggers indeterminate verdict."""
        # Queue one error, two successes
        mock_client._mock_handler.queue_errors_once("parse_error")
        mock_client._mock_handler.queue_json_responses([
            {"score": 0.9, "confidence": 0.9, "reasoning": "ok"},
            {"score": 0.9, "confidence": 0.9, "reasoning": "ok"}
        ])
        
        response = {
            "proximity_score": 0.8,
            "reasoning": "x" * 20,
            "evidence": "y",
            "confidence": 0.9
        }
        
        context = {
            "task_goal": "Test task",
            "current_state": "Test state"
        }
        
        verdict = await evaluate_with_tribunal(
            response=response,
            context=context,
            openai_client=mock_client,
            threshold=0.8
        )
        
        # Should be indeterminate due to judge failure
        assert getattr(verdict, "indeterminate", False) is True, \
            "Expected indeterminate verdict on parse error"
        print(f"\n✅ Indeterminate verdict on parse error")
        print(f"   Reasoning: {verdict.reasoning[:100]}...")
    
    @pytest.mark.asyncio
    async def test_tribunal_fails_without_majority(self, mock_client):
        """Test 2-of-3 pass rule: verdict fails if only 1 judge passes."""
        # Queue responses: 1 pass, 2 fail
        mock_client._mock_handler.queue_json_responses([
            {"score": 0.9, "confidence": 0.9, "reasoning": "Pass"},
            {"score": 0.5, "confidence": 0.9, "reasoning": "Fail"},
            {"score": 0.4, "confidence": 0.9, "reasoning": "Fail"}
        ])
        
        response = {
            "proximity_score": 0.7,
            "reasoning": "x" * 20,
            "evidence": "y",
            "confidence": 0.8
        }
        
        context = {
            "task_goal": "Test task",
            "current_state": "Test state"
        }
        
        verdict = await evaluate_with_tribunal(
            response=response,
            context=context,
            openai_client=mock_client,
            threshold=0.7
        )
        
        # Should fail: only 1 of 3 judges passed
        assert not verdict.passed, "Expected failure with only 1/3 judges passing"
        print(f"\n✅ Verdict correctly failed with 1/3 judges passing")
        print(f"   Median score: {verdict.consensus_score:.2f}")
    
    @pytest.mark.asyncio
    async def test_tribunal_passes_with_majority(self, mock_client):
        """Test 2-of-3 pass rule: verdict passes if 2+ judges pass."""
        # Queue responses: 2 pass, 1 fail
        mock_client._mock_handler.queue_json_responses([
            {"score": 0.9, "confidence": 0.9, "reasoning": "Pass"},
            {"score": 0.85, "confidence": 0.9, "reasoning": "Pass"},
            {"score": 0.6, "confidence": 0.9, "reasoning": "Fail"}
        ])
        
        response = {
            "proximity_score": 0.8,
            "reasoning": "x" * 20,
            "evidence": "y",
            "confidence": 0.8
        }
        
        context = {
            "task_goal": "Test task",
            "current_state": "Test state"
        }
        
        verdict = await evaluate_with_tribunal(
            response=response,
            context=context,
            openai_client=mock_client,
            threshold=0.7
        )
        
        # Should pass: 2 of 3 judges passed
        assert verdict.passed, "Expected pass with 2/3 judges passing"
        assert not verdict.unanimous, "Should not be unanimous"
        print(f"\n✅ Verdict correctly passed with 2/3 judges passing")
        print(f"   Median score: {verdict.consensus_score:.2f}")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
