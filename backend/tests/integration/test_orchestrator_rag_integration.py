"""Integration tests for orchestrator RAG-mediated context queries."""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from backend.models import AutonomyLevel
from backend.services.orchestrator import Agent, AgentType, Orchestrator


class StubRAGService:
    def __init__(self, patterns: List[Dict[str, Any]]) -> None:
        self.patterns = patterns
        self.calls: List[Dict[str, Any]] = []

    async def search(self, **kwargs: Any):
        self.calls.append(kwargs)
        return self.patterns


@pytest.mark.asyncio
async def test_query_knowledge_base_formats_rag_results():
    rag_patterns = [
        type("pattern", (), {
            "title": "Pattern A",
            "problem": "Latency spikes",
            "solution": "Add caching",
            "when_to_try": "When response time exceeds 500ms",
            "success_count": 4,
            "similarity": 0.92,
        })(),
    ]
    rag_service = StubRAGService(rag_patterns)
    orchestrator = Orchestrator(
        project_id="proj-1",
        rag_service=rag_service,
        autonomy_level=AutonomyLevel.MEDIUM,
    )

    results = await orchestrator.query_knowledge_base(
        query="How to handle latency",
        agent_type="backend_developer",
        task_type="performance_tuning",
    )

    assert len(results) == 1
    assert results[0]["title"] == "Pattern A"
    assert rag_service.calls[0]["agent_type"] == "backend_developer"


@pytest.mark.asyncio
async def test_route_collaboration_selects_idle_specialist():
    orchestrator = Orchestrator(project_id="proj-1")
    specialist_idle = Agent(agent_id="agent-1", agent_type=AgentType.SECURITY_EXPERT, status="idle")
    specialist_busy = Agent(agent_id="agent-2", agent_type=AgentType.SECURITY_EXPERT, status="active", metadata={"current_load": 5})
    orchestrator.register_agent(specialist_idle)
    orchestrator.register_agent(specialist_busy)

    result = orchestrator.route_collaboration({"context": "Need security review"})

    assert result["selected_agent"] == "agent-1"
    assert result["agent_type"] == AgentType.SECURITY_EXPERT.value


@pytest.mark.asyncio
async def test_should_escalate_delegates_to_policy():
    orchestrator = Orchestrator(project_id="proj-1", autonomy_level=AutonomyLevel.MEDIUM)

    assert orchestrator.should_escalate(confidence_score=0.2) is True
    assert orchestrator.should_escalate(confidence_score=0.8) is False
