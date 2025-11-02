"""Tests for orchestrator prompt templates and context assembly."""

from __future__ import annotations

import pytest

from backend.prompts.orchestrator_prompts import (
    BASE_SYSTEM_PROMPT,
    CollaborationRecord,
    RAGPattern,
    build_context,
    validate_prompt_requirements,
)


def test_base_system_prompt_contains_required_sections():
    validate_prompt_requirements(BASE_SYSTEM_PROMPT)


def test_build_context_includes_sections_and_respects_token_budget():
    context = build_context(
        project_context={
            "project_name": "Project Atlas",
            "phase_name": "Phase 1",
            "phase_progress": 42,
            "active_agent": "backend_dev",
            "active_task": "Implement API",
            "completed_tasks": 5,
            "pending_tasks": 3,
            "recent_decisions": "Approved architecture",
            "recent_agent_activity": "Backend agent delivered data model",
            "agent_roster": "backend_dev, frontend_dev",
        },
        decision_context={
            "decision_type": "agent_selection",
            "situation": "Choose best specialist",
            "options": ["backend_dev", "frontend_dev"],
            "constraints": "Ensure expertise alignment",
            "urgency": "medium",
        },
        rag_patterns=[
            RAGPattern(
                title="Pattern 1",
                success_count=4,
                problem="Latency",
                solution="Introduce caching",
                when_to_try="When response times exceed 400ms",
                similarity=0.88,
            )
        ],
        collaboration_history=[
            CollaborationRecord(
                specialist_type="security_expert",
                summary="Reviewed auth strategy",
                outcome="Approved",
            )
        ],
        autonomy_level="medium",
    )

    # ensure key headers are present
    assert "Project State:" in context
    assert "Decision Context:" in context
    # ensure token estimate stays within budget
    validate_prompt_requirements(BASE_SYSTEM_PROMPT + "\n" + context)


def test_validate_prompt_requirements_detects_missing_sections():
    with pytest.raises(ValueError):
        validate_prompt_requirements("Incomplete prompt text")
