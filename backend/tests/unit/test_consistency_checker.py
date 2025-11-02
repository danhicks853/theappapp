"""
Programmatic Consistency Checker Tests

Fast, free validation of logical consistency.
Tests the Stage 0 validation layer.
"""
import pytest
from backend.tests.llm_tribunal_framework import (
    evaluate_with_rubric,
    _consistency_checks
)


@pytest.mark.unit
class TestConsistencyChecker:
    """Test programmatic consistency validation."""
    
    def test_high_score_negative_reasoning_detected(self):
        """Test catches high score with negative reasoning."""
        response = {
            "proximity_score": 0.95,
            "reasoning": "Task just started, no progress yet.",
            "evidence": "Files created",
            "confidence": 0.9
        }
        
        issues = _consistency_checks(response)
        
        print(f"\nActual issues: {issues}")
        assert len(issues) > 0
        assert any("high score" in issue.lower() and "negative" in issue.lower() for issue in issues)
    
    def test_high_score_negative_evidence_detected(self):
        """Test catches high score with negative evidence."""
        response = {
            "proximity_score": 0.9,
            "reasoning": "Making progress",
            "evidence": "No files created. Nothing implemented.",
            "confidence": 0.8
        }
        
        issues = _consistency_checks(response)
        
        assert len(issues) > 0
        assert any("High score" in issue and "negative evidence" in issue for issue in issues)
    
    def test_low_score_positive_reasoning_detected(self):
        """Test catches low score with positive reasoning."""
        response = {
            "proximity_score": 0.1,
            "reasoning": "Task complete and working successfully",
            "evidence": "No progress",
            "confidence": 0.8
        }
        
        issues = _consistency_checks(response)
        
        assert len(issues) > 0
        assert any("Low score" in issue and "positive reasoning" in issue for issue in issues)
    
    def test_mid_score_extreme_language_detected(self):
        """Test catches mid score with extreme language."""
        response = {
            "proximity_score": 0.5,
            "reasoning": "Task is 100% complete and fully done",
            "evidence": "Some files created",
            "confidence": 0.7
        }
        
        issues = _consistency_checks(response)
        
        assert len(issues) > 0
        assert any("Mid score" in issue and "extreme" in issue for issue in issues)
    
    def test_consistent_response_no_issues(self):
        """Test consistent response has no issues."""
        response = {
            "proximity_score": 0.75,
            "reasoning": "Task is 75% complete. Login done, logout in progress.",
            "evidence": "Files created: auth.py, test_auth.py. Tests passing.",
            "confidence": 0.85
        }
        
        issues = _consistency_checks(response)
        
        assert len(issues) == 0
    
    def test_high_confidence_uncertain_language_detected(self):
        """Test catches high confidence with uncertain language."""
        response = {
            "proximity_score": 0.7,
            "reasoning": "Maybe the task is done, possibly complete, uncertain about it",
            "evidence": "Files exist",
            "confidence": 0.95
        }
        
        issues = _consistency_checks(response)
        
        assert len(issues) > 0
        assert any("High confidence" in issue and "uncertain" in issue for issue in issues)
    
    def test_low_confidence_definitive_language_detected(self):
        """Test catches low confidence with definitive language."""
        response = {
            "proximity_score": 0.7,
            "reasoning": "Definitely complete, certainly done, clearly finished",
            "evidence": "Files exist",
            "confidence": 0.3
        }
        
        issues = _consistency_checks(response)
        
        assert len(issues) > 0
        assert any("Low confidence" in issue and "definitive" in issue for issue in issues)
    
    def test_missing_score_returns_empty(self):
        """Test missing score returns no issues (rubric will catch this)."""
        response = {
            "reasoning": "Some reasoning",
            "evidence": "Some evidence",
            "confidence": 0.8
        }
        
        issues = _consistency_checks(response)
        
        assert len(issues) == 0  # Rubric layer handles missing fields
    
    def test_multiple_issues_detected(self):
        """Test catches multiple consistency issues."""
        response = {
            "proximity_score": 0.95,
            "reasoning": "Maybe not started, uncertain, no progress yet",
            "evidence": "Nothing done",
            "confidence": 0.95
        }
        
        issues = _consistency_checks(response)
        
        # Should catch: high score + negative reasoning, high score + negative evidence, high confidence + uncertain language
        assert len(issues) >= 2


@pytest.mark.unit
class TestConsistencyIntegration:
    """Test consistency checker integrated with rubric."""
    
    def test_rubric_includes_consistency_issues(self):
        """Test rubric validation includes consistency checks."""
        response = {
            "proximity_score": 0.95,
            "reasoning": "No progress yet",
            "evidence": "Nothing done",
            "confidence": 0.9
        }
        
        result = evaluate_with_rubric(response, "goal_proximity")
        
        # Should fail due to consistency issues
        assert not result.passed
        assert len(result.consistency_issues) > 0
        assert len(result.errors) > 0  # Consistency issues become errors
    
    def test_consistent_response_passes_rubric(self):
        """Test consistent response passes rubric with no issues."""
        response = {
            "proximity_score": 0.75,
            "reasoning": "Task is 75% complete with good progress",
            "evidence": "Multiple files created and tested",
            "confidence": 0.85
        }
        
        result = evaluate_with_rubric(response, "goal_proximity")
        
        assert result.passed
        assert len(result.consistency_issues) == 0
        assert result.score >= 0.9


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
