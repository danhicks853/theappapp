"""Unit tests for OrchestratorLLMClient."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from backend.prompts.orchestrator_prompts import CollaborationRecord, RAGPattern
from backend.services.orchestrator_llm_client import OrchestratorDecision, OrchestratorLLMClient


class StubChatCompletions:
    def __init__(self, response_payload: Dict[str, Any], *, model: str = "gpt-4o-mini") -> None:
        self._payload = response_payload
        self._model = model
        self._prompt_tokens = 120
        self._completion_tokens = 48

    async def create(self, *, model: str, temperature: float, response_format: Dict[str, Any], messages: List[Dict[str, str]]):
        payload_json = json.dumps(self._payload)
        return SimpleNamespace(
            model=model,
            usage=SimpleNamespace(prompt_tokens=self._prompt_tokens, completion_tokens=self._completion_tokens),
            choices=[SimpleNamespace(message=SimpleNamespace(content=payload_json))],
        )


class StubChat:
    def __init__(self, response_payload: Dict[str, Any]) -> None:
        self.completions = StubChatCompletions(response_payload)


class StubAsyncOpenAI:
    def __init__(self, response_payload: Dict[str, Any]) -> None:
        self.chat = StubChat(response_payload)


class TokenRecorder:
    def __init__(self) -> None:
        self.entries: List[Dict[str, Any]] = []

    async def log(self, **entry: Any) -> None:
        self.entries.append(entry)


@pytest.mark.asyncio
async def test_reason_about_task_logs_tokens_and_returns_decision():
    payload = {
        "reasoning": "Detailed chain of thought",
        "decision": {"action": "assign_agent", "details": {"agent": "backend"}},
        "confidence": 0.82,
    }
    token_logger = TokenRecorder()
    client = OrchestratorLLMClient(
        openai_client=StubAsyncOpenAI(payload),
        token_logger=token_logger,
        project_id="project-123",
    )

    decision = await client.reason_about_task(
        decision_type="agent_selection",
        project_context={"project_name": "Example", "phase_name": "Phase 1", "phase_progress": 10},
        decision_context={"situation": "Need backend specialist", "options": ["backend", "frontend"], "constraints": ""},
        rag_patterns=[
            RAGPattern(
                title="Pattern",
                success_count=4,
                problem="Scaling issue",
                solution="Use caching",
                when_to_try="When latency spikes",
                similarity=0.91,
            )
        ],
        collaboration_history=[
            CollaborationRecord(
                specialist_type="security_expert",
                summary="Reviewed threat model",
                outcome="Approved",
            )
        ],
    )

    assert isinstance(decision, OrchestratorDecision)
    assert decision.decision["action"] == "assign_agent"
    assert decision.confidence == pytest.approx(0.82)
    assert token_logger.entries and token_logger.entries[0]["tokens_input"] == 120


@pytest.mark.asyncio
async def test_evaluate_progress_clamps_confidence():
    payload = {
        "reasoning": "Progress is uncertain",
        "decision": {"action": "escalate", "details": {}},
        "confidence": 1.3,  # client should clamp value
    }
    client = OrchestratorLLMClient(openai_client=StubAsyncOpenAI(payload))

    score = await client.evaluate_progress(
        progress_summary="Agent encountered multiple failures",
        project_context={"project_name": "Example", "phase_name": "Phase 1", "phase_progress": 35},
    )

    assert 0.0 <= score <= 1.0
    assert score == 1.0


@pytest.mark.asyncio
async def test_reason_about_task_raises_on_malformed_json():
    class BadCompletions(StubChatCompletions):
        async def create(self, **_: Any):
            return SimpleNamespace(
                model="gpt-4o-mini",
                usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
                choices=[SimpleNamespace(message=SimpleNamespace(content="not-json"))],
            )

    class BadClient(StubAsyncOpenAI):
        def __init__(self):
            self.chat = SimpleNamespace(completions=BadCompletions({}))

    client = OrchestratorLLMClient(openai_client=BadClient())

    with pytest.raises(ValueError):
        await client.reason_about_task(
            decision_type="agent_selection",
            project_context={},
            decision_context={"situation": "", "options": []},
        )
