"""Integration tests for agent execution loop interactions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from backend.agents.base_agent import BaseAgent
from backend.models.agent_state import Result


class StubOrchestrator:
    """Integration stub capturing orchestrator interactions."""

    def __init__(self, confidence: float = 0.4) -> None:
        self.confidence = confidence
        self.tool_requests: List[Dict[str, Any]] = []
        self.gates: List[Dict[str, Any]] = []
        self.confidence_requests: List[Dict[str, Any]] = []

    async def execute_tool(self, request: Dict[str, Any]) -> Dict[str, Any]:
        self.tool_requests.append(request)
        return {
            "status": "success",
            "result": {"artifacts": {"file": "content"}},
        }

    async def evaluate_confidence(self, request: Dict[str, Any]) -> float:
        self.confidence_requests.append(request)
        return self.confidence

    async def create_gate(self, *, reason: str, context: Dict[str, Any], agent_id: Optional[str]) -> str:
        gate_id = f"gate-{len(self.gates) + 1}"
        self.gates.append({
            "gate_id": gate_id,
            "reason": reason,
            "context": context,
            "agent_id": agent_id,
        })
        return gate_id


class StubLLMClient:
    """LLM stub for integration testing."""

    async def plan_next_action(self, **_: Any) -> Dict[str, Any]:
        return {
            "description": "integrated-step",
            "tool_name": None,
            "operation": None,
            "parameters": {},
            "reasoning": "follow integration path",
        }

    async def evaluate_progress(self, **_: Any) -> Dict[str, Any]:
        return {
            "success": True,
            "issues": [],
            "metrics": {"progress_score": 0.5, "request_confidence_check": True},
        }

    async def evaluate_confidence(self, **_: Any) -> float:
        return 0.4


class IntegrationAgent(BaseAgent):
    """Concrete agent for integration-level testing."""

    async def _execute_internal_action(
        self,
        action: Any,
        state: Any,
        attempt: int,
    ) -> Result:
        return Result(
            success=True,
            output=None,
            metadata={},
        )


@pytest.mark.asyncio
async def test_low_confidence_triggers_gate() -> None:
    orchestrator = StubOrchestrator(confidence=0.3)
    llm_client = StubLLMClient()
    agent = IntegrationAgent(
        agent_id="agent-integration",
        agent_type="integration",
        orchestrator=orchestrator,
        llm_client=llm_client,
        confidence_threshold=0.5,
        confidence_check_interval=1,
    )

    task = {
        "task_id": "integration-task",
        "project_id": "project-xyz",
        "payload": {"goal": "", "acceptance_criteria": [], "max_steps": 3},
    }

    outcome = await agent.run_task(task)

    assert outcome.success is False, "Task should escalate due to low confidence gate"
    assert orchestrator.confidence_requests, "Confidence evaluation should be requested"
    assert orchestrator.gates, "Gate should be created when confidence below threshold"
    gate = orchestrator.gates[0]
    assert gate["reason"].startswith("Low confidence"), "Gate reason should reference low confidence"
