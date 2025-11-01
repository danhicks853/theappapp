"""Unit tests for BaseAgent iterative execution loop."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import pytest

from backend.agents.base_agent import BaseAgent
from backend.models.agent_state import Action, Result, ValidationResult


class StubOrchestrator:
    """Lightweight orchestrator stub for unit tests."""

    def __init__(self, confidence: float = 0.9):
        self.confidence = confidence
        self.tool_requests: List[Dict[str, Any]] = []
        self.gates: List[Dict[str, Any]] = []
        self.confidence_requests: List[Dict[str, Any]] = []

    async def execute_tool(self, request: Dict[str, Any]) -> Dict[str, Any]:
        self.tool_requests.append(request)
        return {
            "status": "success",
            "result": {"output": "ok"},
            "error": None,
            "tests": {"passed": 1, "failed": 0},
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
    """Stub LLM client providing deterministic planning and evaluation."""

    def __init__(self, plans: Optional[Iterable[Dict[str, Any]]] = None, *, confidence: float = 0.9):
        self._plans = list(plans or [])
        self._plan_calls = 0
        self.confidence = confidence

    async def plan_next_action(self, **_: Any) -> Dict[str, Any]:
        if self._plan_calls < len(self._plans):
            plan = self._plans[self._plan_calls]
        else:
            plan = {
                "description": f"step-{self._plan_calls}",
                "tool_name": None,
                "operation": None,
                "parameters": {},
                "reasoning": f"reason-{self._plan_calls}",
            }
        self._plan_calls += 1
        return plan

    async def evaluate_progress(self, **_: Any) -> Dict[str, Any]:
        return {"success": True, "metrics": {"progress_score": 1.0}}

    async def evaluate_confidence(self, **_: Any) -> float:
        return self.confidence


class TestAgent(BaseAgent):
    """Concrete BaseAgent for exercising loop behaviour."""

    def __init__(
        self,
        orchestrator: StubOrchestrator,
        llm_client: StubLLMClient,
        results: Iterable[Result],
        *,
        validations: Optional[Iterable[Optional[ValidationResult]]] = None,
        max_retries: int = 3,
    ) -> None:
        super().__init__(
            agent_id="agent-1",
            agent_type="test_agent",
            orchestrator=orchestrator,
            llm_client=llm_client,
            max_retries=max_retries,
        )
        self._results = list(results)
        self._validations = list(validations or [])

    async def _execute_internal_action(self, action: Action, state: Any, attempt: int) -> Result:
        if self._results:
            return self._results.pop(0)
        return Result(success=True, metadata={"tests": {"passed": 1, "failed": 0}})

    async def _evaluate_progress(self, state: Any, result: Result) -> Optional[ValidationResult]:
        if self._validations:
            return self._validations.pop(0)
        return await super()._evaluate_progress(state, result)


@pytest.mark.asyncio
async def test_run_task_success_single_iteration() -> None:
    orchestrator = StubOrchestrator()
    llm = StubLLMClient(plans=[
        {
            "description": "initial-step",
            "tool_name": None,
            "operation": None,
            "parameters": {},
            "reasoning": "proceed",
        }
    ])
    results = [
        Result(
            success=True,
            output={"artifact": "content"},
            metadata={"tests": {"passed": 1, "failed": 0}},
        )
    ]
    agent = TestAgent(orchestrator, llm, results)

    task = {
        "task_id": "task-123",
        "project_id": "project-1",
        "payload": {"goal": "Do the thing", "acceptance_criteria": [], "max_steps": 3},
    }

    outcome = await agent.run_task(task)

    assert outcome.success is True
    assert len(outcome.steps) == 1
    assert outcome.artifacts["step_0"] == {"artifact": "content"}
    assert orchestrator.tool_requests == []


@pytest.mark.asyncio
async def test_retry_generates_unique_replanned_actions() -> None:
    orchestrator = StubOrchestrator()
    plans = [
        {"description": "attempt-1", "tool_name": None, "operation": None, "parameters": {}, "reasoning": "try 1"},
        {"description": "attempt-2", "tool_name": None, "operation": None, "parameters": {}, "reasoning": "try 2"},
    ]
    llm = StubLLMClient(plans=plans)
    results = [
        Result(success=False, error="boom", metadata={"tests": {"passed": 0, "failed": 1}}),
        Result(success=True, metadata={"tests": {"passed": 1, "failed": 0}}),
    ]
    agent = TestAgent(orchestrator, llm, results)

    task = {"task_id": "task-retry", "project_id": "project-1", "payload": {"goal": "", "acceptance_criteria": []}}
    outcome = await agent.run_task(task)

    assert outcome.success is True
    assert llm._plan_calls == 2  # original plan + replanned attempt


@pytest.mark.asyncio
async def test_loop_detection_triggers_gate_after_three_failures() -> None:
    orchestrator = StubOrchestrator()
    llm = StubLLMClient(plans=[{"description": "loop", "tool_name": None, "operation": None, "parameters": {}, "reasoning": "loop"}])
    failure_result = Result(success=False, error="same", metadata={})
    failure_validation = ValidationResult(success=False, issues=["identical"], metrics={"progress_score": 0.0})
    agent = TestAgent(
        orchestrator,
        llm,
        [failure_result, failure_result, failure_result],
        validations=[failure_validation, failure_validation, failure_validation],
        max_retries=1,
    )

    task = {"task_id": "task-loop", "project_id": "project-1", "payload": {"goal": "", "acceptance_criteria": [], "max_steps": 5}}
    outcome = await agent.run_task(task)

    assert outcome.success is False
    assert orchestrator.gates, "Gate should be created after loop detection"
    assert "Loop" in orchestrator.gates[0]["reason"]


@pytest.mark.asyncio
async def test_progress_hierarchy_prefers_tests_then_artifacts_then_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    orchestrator = StubOrchestrator()
    llm = StubLLMClient()
    agent = TestAgent(orchestrator, llm, results=[])

    task = {"task_id": "task-progress", "project_id": "project-1", "payload": {"goal": "", "acceptance_criteria": []}}
    state = agent._initialize_state(task)

    # Test metrics take precedence
    result_with_tests = Result(success=False, metadata={"tests": {"passed": 2, "failed": 0}})
    validation = await agent._evaluate_progress(state, result_with_tests)
    assert validation.success is True
    assert validation.metrics["tests_passed"] == 2

    # Artifact metrics used when tests absent
    result_with_artifacts = Result(success=False, metadata={"artifacts": ["file.py"]})
    validation = await agent._evaluate_progress(state, result_with_artifacts)
    assert validation.success is True
    assert validation.metrics["artifact_count"] == 1

    # LLM fallback when deterministic data missing
    async def fake_llm_progress(**_: Any) -> Dict[str, Any]:
        return {"success": True, "metrics": {"progress_score": 0.5}}

    monkeypatch.setattr(llm, "evaluate_progress", fake_llm_progress)
    validation = await agent._evaluate_progress(state, Result(success=False, metadata={}))
    assert validation.success is True
    assert validation.metrics["progress_score"] == 0.5
