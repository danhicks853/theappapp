"""Two-stage LLM tests for OrchestratorLLMClient per Decision 72.

Stage 1: Rubric validation (fast, deterministic structural checks)
Stage 2: AI Panel evaluation (expensive, semantic quality assessment with real LLM jury)

These tests use REAL OpenAI API calls for both the system under test and the evaluator panel.
"""

from __future__ import annotations

import os

import pytest

from backend.services.orchestrator_llm_client import OrchestratorLLMClient
from backend.tests.llm.llm_evaluator_panel import (
    ORCHESTRATOR_CRITERIA,
    EvaluationCriteria,
    LLMEvaluatorPanel,
)


# Skip these tests if OPENAI_API_KEY is not set or if running in CI without LLM test flag
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY") or not os.getenv("RUN_LLM_TESTS"),
    reason="LLM tests require OPENAI_API_KEY and RUN_LLM_TESTS=1 environment variables",
)


# ==================================================================================
# STAGE 1: RUBRIC VALIDATION (Fast, Deterministic)
# ==================================================================================


@pytest.mark.asyncio
async def test_reason_about_task_rubric_structure():
    """Stage 1: Verify output structure and required fields."""
    client = OrchestratorLLMClient(model="gpt-4o-mini")

    decision = await client.reason_about_task(
        decision_type="agent_selection",
        project_context={"project_name": "TestProject", "phase_name": "Phase 1", "phase_progress": 10},
        decision_context={
            "situation": "Need to implement REST API for user authentication",
            "options": ["backend_developer", "security_expert"],
            "constraints": "Must follow OAuth 2.0 standards",
            "urgency": "medium",
        },
        rag_patterns=[],
        collaboration_history=[],
        autonomy_level="medium",
    )

    # Required fields present
    assert hasattr(decision, "reasoning"), "Missing 'reasoning' field"
    assert hasattr(decision, "decision"), "Missing 'decision' field"
    assert hasattr(decision, "confidence"), "Missing 'confidence' field"

    # Valid data types
    assert isinstance(decision.reasoning, str), "reasoning must be string"
    assert isinstance(decision.decision, dict), "decision must be dict"
    assert isinstance(decision.confidence, float), "confidence must be float"

    # Valid ranges
    assert 0.0 <= decision.confidence <= 1.0, f"confidence {decision.confidence} out of range [0.0, 1.0]"

    # Non-empty content
    assert len(decision.reasoning) > 0, "reasoning cannot be empty"
    assert len(decision.decision) > 0, "decision cannot be empty"

    # Decision structure
    assert "action" in decision.decision or "agent_type" in decision.decision, \
        "decision must contain 'action' or 'agent_type'"


@pytest.mark.asyncio
async def test_select_agent_rubric_structure():
    """Stage 1: Verify agent selection returns valid structure."""
    client = OrchestratorLLMClient(model="gpt-4o-mini")

    decision = await client.select_agent(
        task_description="Implement WebSocket server for real-time notifications",
        candidate_agents=[
            {"name": "backend_developer", "expertise": ["API", "WebSocket", "Python"]},
            {"name": "devops_engineer", "expertise": ["Infrastructure", "Scaling", "Deployment"]},
        ],
        project_context={"project_name": "TestProject"},
        rag_patterns=[],
        autonomy_level="medium",
    )

    # Structure validation
    assert isinstance(decision.decision, dict), "decision must be dict"
    assert isinstance(decision.confidence, float), "confidence must be float"
    assert 0.0 <= decision.confidence <= 1.0, "confidence out of range"

    # Agent selection should return agent identifier
    assert "agent_type" in decision.decision or "agent" in decision.decision, \
        "decision must identify selected agent"


@pytest.mark.asyncio
async def test_evaluate_progress_rubric_structure():
    """Stage 1: Verify progress evaluation returns numeric confidence."""
    client = OrchestratorLLMClient(model="gpt-4o-mini")

    score = await client.evaluate_progress(
        progress_summary="Backend API 80% complete, all tests passing, minor refactoring needed",
        project_context={"project_name": "TestProject", "phase_name": "Phase 1", "phase_progress": 80},
        autonomy_level="medium",
    )

    # Must return float in valid range
    assert isinstance(score, float), f"evaluate_progress must return float, got {type(score)}"
    assert 0.0 <= score <= 1.0, f"score {score} out of range [0.0, 1.0]"


# ==================================================================================
# STAGE 2: AI PANEL EVALUATION (Expensive, Semantic)
# ==================================================================================


@pytest.mark.asyncio
@pytest.mark.slow
async def test_reason_about_task_semantic_quality():
    """Stage 2: AI panel evaluates reasoning quality with consensus."""
    client = OrchestratorLLMClient(model="gpt-4o-mini")
    panel = LLMEvaluatorPanel(evaluator_count=3, model="gpt-4o-mini")

    decision = await client.reason_about_task(
        decision_type="agent_selection",
        project_context={
            "project_name": "E-commerce Platform",
            "phase_name": "MVP Development",
            "phase_progress": 45,
        },
        decision_context={
            "situation": "Security vulnerability found in authentication module - SQL injection risk",
            "options": ["security_expert", "backend_developer"],
            "constraints": "Critical issue requiring immediate attention",
            "urgency": "critical",
        },
        rag_patterns=[],
        collaboration_history=[],
        autonomy_level="high",
    )

    # Evaluate reasoning quality using AI panel
    evaluation = await panel.evaluate(
        output=decision,
        criteria=ORCHESTRATOR_CRITERIA,
        context=(
            "Expected: Orchestrator should reason about the security vulnerability, "
            "consider urgency, and select security_expert for critical security issues. "
            "Reasoning should mention SQL injection risk and need for immediate security review."
        ),
    )

    # Assertions
    assert evaluation.consensus_passed, \
        f"AI panel consensus failed. Confidence: {evaluation.confidence:.2f}, " \
        f"Scores: {evaluation.criteria_scores}"

    assert evaluation.confidence >= 0.75, \
        f"Confidence {evaluation.confidence:.2f} below threshold 0.75"

    # Check individual criteria
    for criterion_name, score in evaluation.criteria_scores.items():
        assert score >= 0.6, \
            f"Criterion '{criterion_name}' scored {score:.2f}, below minimum 0.6"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_select_agent_semantic_quality():
    """Stage 2: AI panel evaluates agent selection reasoning."""
    client = OrchestratorLLMClient(model="gpt-4o-mini")
    panel = LLMEvaluatorPanel(evaluator_count=3, model="gpt-4o-mini")

    decision = await client.select_agent(
        task_description="Design database schema for multi-tenant SaaS application with complex permissions",
        candidate_agents=[
            {"name": "backend_developer", "expertise": ["Database", "API", "Architecture"]},
            {"name": "devops_engineer", "expertise": ["Infrastructure", "Scaling", "Deployment"]},
            {"name": "security_expert", "expertise": ["Security", "Auth", "Compliance"]},
        ],
        project_context={"project_name": "SaaS Platform", "phase_name": "Architecture"},
        rag_patterns=[],
        autonomy_level="medium",
    )

    # Evaluate with AI panel
    evaluation = await panel.evaluate(
        output=decision,
        criteria=[
            EvaluationCriteria(
                name="agent_match",
                description="Selected agent has appropriate expertise for the task",
                weight=2.0,
            ),
            EvaluationCriteria(
                name="reasoning_quality",
                description="Reasoning explains why this agent is best suited",
                weight=1.0,
            ),
        ],
        context=(
            "Expected: Should select backend_developer for database schema design. "
            "Reasoning should mention database expertise and architectural considerations."
        ),
    )

    assert evaluation.consensus_passed, \
        f"Agent selection reasoning failed consensus. Scores: {evaluation.criteria_scores}"

    assert evaluation.confidence >= 0.7, \
        f"Confidence {evaluation.confidence:.2f} below threshold"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_progress_evaluation_semantic_consistency():
    """Stage 2: Verify progress evaluation produces consistent scores for similar scenarios."""
    client = OrchestratorLLMClient(model="gpt-4o-mini")

    # Run same evaluation twice with slight variation
    score1 = await client.evaluate_progress(
        progress_summary="Backend complete, frontend 50% done, tests passing, on schedule",
        project_context={"project_name": "TestProject", "phase_name": "Development", "phase_progress": 75},
        autonomy_level="medium",
    )

    score2 = await client.evaluate_progress(
        progress_summary="Backend complete, frontend halfway done, all tests green, on track",
        project_context={"project_name": "TestProject", "phase_name": "Development", "phase_progress": 75},
        autonomy_level="medium",
    )

    # Scores should be similar (within 0.2) for semantically equivalent summaries
    difference = abs(score1 - score2)
    assert difference <= 0.2, \
        f"Inconsistent scoring: {score1:.2f} vs {score2:.2f} (diff: {difference:.2f})"

    # Both should be reasonably high for positive progress
    assert score1 >= 0.5, f"Score {score1:.2f} too low for positive progress"
    assert score2 >= 0.5, f"Score {score2:.2f} too low for positive progress"


# ==================================================================================
# GOLDEN DATASET TESTS (Future: Load from Qdrant or file)
# ==================================================================================


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.skip(reason="Golden dataset not yet implemented")
async def test_orchestrator_against_golden_dataset():
    """Stage 2: Test orchestrator against curated golden examples.

    TODO: Implement when golden dataset is available in Qdrant.
    Golden dataset should include:
    - Production-sampled successful decisions (10% sample rate)
    - Edge cases handled correctly
    - Error scenarios with proper recovery
    - Inter-agent collaboration examples
    """
    pass
