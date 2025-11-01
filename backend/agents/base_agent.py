"""Base agent implementation for iterative execution loops.

This module implements the core agent execution architecture defined in
Decision 83: Agent Execution Loop Architecture. The BaseAgent enforces a
goal-driven iterative loop with retry logic, confidence gating, loop
prevention, and comprehensive state tracking. Subclasses provide
agent-specific planning and execution behaviour while inheriting a
rigorous control flow that prevents "fake agent loops" and guarantees
observability for recovery workflows.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from abc import ABC
from datetime import UTC, datetime
from typing import Any, Dict, Optional, Set

from backend.models.agent_state import (
    Action,
    Result,
    Step,
    TaskResult,
    TaskState,
    ToolExecution,
    ValidationResult,
)
from backend.services.loop_detector import LoopDetector

logger = logging.getLogger(__name__)



class BaseAgent(ABC):
    """Shared execution framework for all autonomous agents.

    The BaseAgent orchestrates a disciplined loop with the following
    guarantees:

    * Goal-based termination (Decision 83)
    * Intelligent retry with replanning on each failure
    * Loop detection after three identical error signatures (Decision 74)
    * Hybrid progress validation (tests → artifacts → LLM)
    * Confidence-based escalation to the orchestrator
    * Full audit trail for recovery and observability (Decision 76)
    """

    confidence_threshold: float
    confidence_check_interval: int
    max_retries: int

    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        orchestrator: Any,
        llm_client: Any,
        *,
        confidence_threshold: float = 0.5,
        confidence_check_interval: int = 5,
        max_retries: int = 3,
        loop_detector: Optional[Any] = None,
    ) -> None:
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.orchestrator = orchestrator
        self.llm_client = llm_client
        self.confidence_threshold = confidence_threshold
        self.confidence_check_interval = confidence_check_interval
        self.max_retries = max_retries
        self.loop_detector = loop_detector or LoopDetector()
        self.logger = logging.getLogger(f"agents.{self.agent_type}")

    async def run_task(self, task: Any) -> TaskResult:
        """Execute a task using the iterative execution loop."""

        state = self._initialize_state(task)
        self.logger.info(
            "Starting task %s for project %s", state.task_id, state.project_id
        )

        while not self._should_terminate(state):
            action = await self._plan_next_step(state)
            result = await self._execute_step_with_retry(action, state)
            validation = await self._validate_step(result, state)

            self._update_state(state, action, result, validation)

            if validation.success:
                state.record_success()
                self.loop_detector.record_success(state.task_id)
            else:
                signature = validation.error_signature
                state.record_error(signature)
                self.loop_detector.record_failure(state.task_id, signature)

            if self.loop_detector.is_looping(state):
                return await self._escalate_loop(state)

            if self._should_request_confidence_check(state):
                confidence = await self._request_confidence_evaluation(state)
                state.last_confidence_check_step = state.current_step
                state.last_confidence_score = confidence
                if confidence < self.confidence_threshold:
                    return await self._escalate_low_confidence(state, confidence)

            await self._log_step_progress(state)
            state.current_step += 1

        return await self._finalize_result(state)

    def _initialize_state(self, task: Any) -> TaskState:
        """Construct the initial state object for execution."""

        payload = self._extract_task_payload(task)
        project_id = self._get_task_attribute(task, "project_id")
        acceptance = payload.get("acceptance_criteria", [])
        goal = payload.get("goal") or payload.get("description") or ""
        constraints = payload.get("constraints", {})

        state = TaskState(
            task_id=self._get_task_attribute(task, "task_id", default=str(uuid.uuid4())),
            agent_id=self.agent_id,
            project_id=project_id,
            goal=goal,
            acceptance_criteria=acceptance,
            constraints=constraints,
            max_steps=payload.get("max_steps", 20),
        )

        if goal:
            state.decision_reasoning.append(f"Initial goal: {goal}")

        return state

    async def _plan_next_step(
        self,
        state: TaskState,
        *,
        previous_action: Optional[Action] = None,
        previous_result: Optional[Result] = None,
        attempt: int = 0,
    ) -> Action:
        """Produce the next action plan using the LLM client."""

        if hasattr(self.llm_client, "plan_next_action"):
            response = await self.llm_client.plan_next_action(
                task_state=state,
                previous_action=previous_action,
                previous_result=previous_result,
                attempt=attempt,
            )
            action = self._parse_llm_action(response)
        else:
            raise NotImplementedError(
                "llm_client must implement plan_next_action() or override _plan_next_step"
            )

        state.decision_reasoning.append(action.reasoning)
        return action

    async def _execute_step_with_retry(
        self,
        action: Action,
        state: TaskState,
    ) -> Result:
        """Execute an action with intelligent retry and replanning."""

        attempted_signatures: Set[str] = {action.signature()}
        current_action = action

        for attempt in range(1, self.max_retries + 1):
            result = await self._execute_action(current_action, state, attempt)
            result.attempt = attempt

            if result.success:
                return result

            if attempt == self.max_retries:
                return result

            await asyncio.sleep(self._backoff_seconds(attempt))
            current_action = await self._replan_after_failure(
                attempted_signatures=attempted_signatures,
                previous_action=current_action,
                failed_result=result,
                state=state,
                attempt=attempt,
            )

        return result

    async def _execute_action(
        self,
        action: Action,
        state: TaskState,
        attempt: int,
    ) -> Result:
        """Execute a planned action via orchestrator or subclass override."""

        if action.tool_name:
            request_id = action.metadata.get("request_id") or str(uuid.uuid4())
            payload = {
                "request_id": request_id,
                "agent_id": self.agent_id,
                "project_id": state.project_id,
                "task_id": state.task_id,
                "tool_name": action.tool_name,
                "operation": action.operation,
                "parameters": action.parameters,
            }
            response = await self.orchestrator.execute_tool(payload)
            execution = ToolExecution(
                request_id=request_id,
                tool_name=action.tool_name,
                operation=action.operation or "",
                parameters=action.parameters,
                status=response.get("status", "unknown"),
                output=response.get("result"),
                error=response.get("error"),
                finished_at=datetime.now(UTC),
            )
            state.tool_executions.append(execution)
            success = response.get("status") == "success"
            return Result(
                success=success,
                output=response.get("result"),
                error=response.get("error"),
                metadata=response,
                attempt=attempt,
            )

        return await self._execute_internal_action(action, state, attempt)

    async def _execute_internal_action(
        self,
        action: Action,
        state: TaskState,
        attempt: int,
    ) -> Result:
        """Fallback execution hook for subclasses without tool usage."""

        raise NotImplementedError(
            "Subclasses must implement _execute_internal_action for non-tool actions"
        )

    async def _replan_after_failure(
        self,
        *,
        attempted_signatures: Set[str],
        previous_action: Action,
        failed_result: Result,
        state: TaskState,
        attempt: int,
    ) -> Action:
        """Replan with a different approach after a failed attempt."""

        for _ in range(self.max_retries):
            new_action = await self._plan_next_step(
                state,
                previous_action=previous_action,
                previous_result=failed_result,
                attempt=attempt,
            )
            signature = new_action.signature()
            if signature not in attempted_signatures:
                attempted_signatures.add(signature)
                new_action.metadata["replanned"] = True
                new_action.metadata["attempt"] = attempt + 1
                return new_action

            self.logger.warning(
                "Duplicate action signature generated during retry | task=%s | attempt=%s",
                state.task_id,
                attempt,
            )

        raise RuntimeError(
            "Unable to generate a unique replanned action after multiple attempts"
        )

    async def _validate_step(self, result: Result, state: TaskState) -> ValidationResult:
        """Validate execution progress via hybrid strategy."""

        validation = await self._evaluate_progress(state, result)
        if validation is not None:
            return validation

        if result.success:
            return ValidationResult(success=True, issues=[], metrics={"progress_score": 1.0})

        return ValidationResult(
            success=False,
            issues=[result.error or "Unknown failure"],
            metrics={"progress_score": 0.0},
        )

    async def _evaluate_progress(
        self, state: TaskState, result: Result
    ) -> Optional[ValidationResult]:
        """Evaluate progress using hybrid strategy (tests → artifacts → LLM)."""

        test_validation = self._evaluate_test_progress(state, result)
        if test_validation is not None:
            return test_validation

        artifact_validation = self._evaluate_artifact_progress(state, result)
        if artifact_validation is not None:
            return artifact_validation

        return await self._llm_evaluate_progress(state, result)

    def _evaluate_test_progress(
        self, state: TaskState, result: Result
    ) -> Optional[ValidationResult]:
        """Evaluate progress based on deterministic test metrics."""

        tests = result.metadata.get("tests") if isinstance(result.metadata, dict) else None
        tests = tests or state.progress_metrics.get("tests")
        if not tests:
            return None

        passed = tests.get("passed", 0)
        failed = tests.get("failed", 0)
        total = passed + failed
        success = failed == 0 and total > 0
        metrics = {
            "tests_total": total,
            "tests_passed": passed,
            "tests_failed": failed,
            "progress_score": 1.0 if success else max(0.0, min(0.9, passed / max(total, 1))),
        }
        issues = [] if success else ["Test failures detected"]
        return ValidationResult(success=success, issues=issues, metrics=metrics)

    def _evaluate_artifact_progress(
        self, state: TaskState, result: Result
    ) -> Optional[ValidationResult]:
        """Evaluate progress using artifact metrics (files, outputs, etc.)."""

        artifacts = None
        if isinstance(result.metadata, dict):
            artifacts = result.metadata.get("artifacts")
        if artifacts is None and isinstance(result.output, dict):
            artifacts = result.output.get("artifacts")

        if artifacts is None:
            artifacts = state.artifacts if state.artifacts else None

        if artifacts is None:
            return None

        artifact_count = len(artifacts) if isinstance(artifacts, (list, dict)) else 1
        success = artifact_count > 0
        metrics = {
            "artifact_count": artifact_count,
            "progress_score": 0.7 if success else 0.0,
        }
        issues = [] if success else ["No new artifacts produced"]
        return ValidationResult(success=success, issues=issues, metrics=metrics)

    async def _llm_evaluate_progress(
        self, state: TaskState, result: Result
    ) -> Optional[ValidationResult]:
        """Fallback to LLM-based progress evaluation when deterministic data absent."""

        if not self.llm_client or not hasattr(self.llm_client, "evaluate_progress"):
            return None

        response = await self.llm_client.evaluate_progress(
            task_state=state,
            result=result,
        )
        return self._parse_validation(response)

    def _update_state(
        self,
        state: TaskState,
        action: Action,
        result: Result,
        validation: ValidationResult,
    ) -> None:
        """Persist iteration results into the TaskState audit trail."""

        progress_delta = float(validation.metrics.get("progress_score", 0.0))
        state.progress_score = max(state.progress_score, progress_delta)
        state.progress_metrics.update(validation.metrics)

        step = Step(
            step_number=state.current_step,
            timestamp=datetime.now(UTC),
            reasoning=action.reasoning,
            action=action,
            result=result,
            validation=validation,
            tokens_used=sum(call.tokens_used for call in state.llm_calls),
            cost_usd=sum(call.cost_usd for call in state.llm_calls),
        )
        state.steps_history.append(step)

        if result.success and result.output is not None:
            state.artifacts[f"step_{state.current_step}"] = result.output

    def _should_terminate(self, state: TaskState) -> bool:
        """Evaluate termination criteria."""

        if self._acceptance_criteria_met(state):
            return True

        if state.current_step >= state.max_steps:
            state.timeout_reached = True
            return True

        if state.escalation_triggered or state.resource_limit_hit:
            return True

        return False

    def _acceptance_criteria_met(self, state: TaskState) -> bool:
        """Determine whether acceptance criteria are satisfied."""

        if not state.acceptance_criteria:
            return state.progress_score >= 1.0

        completed = state.progress_metrics.get("completed_acceptance_items", 0)
        return completed >= len(state.acceptance_criteria)

    async def _log_step_progress(self, state: TaskState) -> None:
        """Emit structured logs for observability."""

        if not state.steps_history:
            return

        last_step = state.steps_history[-1]
        self.logger.info(
            "Step %s | success=%s | progress=%.2f",
            last_step.step_number,
            last_step.validation.success,
            state.progress_score,
        )

    def _should_request_confidence_check(self, state: TaskState) -> bool:
        """Decide whether the orchestrator should evaluate confidence."""

        steps_since_last = state.current_step - state.last_confidence_check_step
        uncertainty_flag = state.progress_metrics.get("agent_uncertain", False)
        manual_request = state.progress_metrics.get("request_confidence_check", False)

        return (
            steps_since_last >= self.confidence_check_interval
            or uncertainty_flag
            or manual_request
        )

    async def _request_confidence_evaluation(self, state: TaskState) -> float:
        """Delegate confidence evaluation to the orchestrator."""

        request_payload = {
            "agent_id": self.agent_id,
            "task_id": state.task_id,
            "current_step": state.current_step,
            "goal": state.goal,
            "progress_score": state.progress_score,
            "steps_history": [
                {
                    "step_number": step.step_number,
                    "reasoning": step.reasoning,
                    "success": step.validation.success,
                    "issues": list(step.validation.issues),
                }
                for step in state.steps_history[-5:]
            ],
            "artifacts": state.artifacts,
        }
        response = await self.orchestrator.evaluate_confidence(request_payload)
        try:
            return float(response)
        except (TypeError, ValueError):
            self.logger.warning("Invalid confidence response: %s", response)
            return 0.0

    async def _escalate_loop(self, state: TaskState) -> TaskResult:
        """Trigger a gate when loop detection threshold is exceeded."""

        gate_id = await self.orchestrator.create_gate(
            reason="Loop detected after repeated identical failures",
            context={
                "task_id": state.task_id,
                "agent_id": self.agent_id,
                "errors": state.last_errors[-3:],
            },
            agent_id=self.agent_id,
        )
        state.escalation_triggered = True
        state.escalation_reason = f"Loop escalation gate {gate_id}"
        return await self._finalize_result(state)

    async def _escalate_low_confidence(
        self, state: TaskState, confidence: float
    ) -> TaskResult:
        """Escalate to human review when confidence is too low."""

        gate_id = await self.orchestrator.create_gate(
            reason=f"Low confidence detected: {confidence:.2f}",
            context={
                "task_id": state.task_id,
                "agent_id": self.agent_id,
                "confidence": confidence,
            },
            agent_id=self.agent_id,
        )
        state.escalation_triggered = True
        state.escalation_reason = f"Low confidence gate {gate_id}"
        return await self._finalize_result(state)

    async def _finalize_result(self, state: TaskState) -> TaskResult:
        """Assemble the final TaskResult structure."""

        state.completed_at = datetime.now(UTC)
        success = self._acceptance_criteria_met(state) and not state.escalation_triggered
        errors = [err for err in state.last_errors if err]

        return TaskResult(
            task_id=state.task_id,
            success=success,
            steps=state.steps_history,
            artifacts=state.artifacts,
            reasoning=state.decision_reasoning,
            confidence=state.last_confidence_score,
            errors=errors,
            metadata={
                "completed_at": state.completed_at.isoformat(),
                "started_at": state.started_at.isoformat(),
                "escalation_reason": state.escalation_reason,
            },
        )

    def _parse_llm_action(self, response: Dict[str, Any]) -> Action:
        """Normalise an LLM planning response to an Action dataclass."""

        return Action(
            description=response.get("description", ""),
            tool_name=response.get("tool_name"),
            operation=response.get("operation"),
            parameters=response.get("parameters", {}),
            reasoning=response.get("reasoning", ""),
            metadata=response.get("metadata", {}),
        )

    def _parse_validation(self, response: Dict[str, Any]) -> ValidationResult:
        """Normalise an LLM validation response to ValidationResult."""

        return ValidationResult(
            success=bool(response.get("success", False)),
            issues=response.get("issues", []),
            metrics=response.get("metrics", {}),
        )

    def _backoff_seconds(self, attempt: int) -> float:
        """Compute exponential backoff duration."""

        return float(2 ** attempt)

    @staticmethod
    def _extract_task_payload(task: Any) -> Dict[str, Any]:
        """Fetch a payload dictionary regardless of task representation."""

        if isinstance(task, dict):
            return task.get("payload", task)
        return getattr(task, "payload", {}) or {}

    @staticmethod
    def _get_task_attribute(task: Any, name: str, default: Any = None) -> Any:
        """Access attributes for either dict-like or object tasks."""

        if isinstance(task, dict):
            return task.get(name, default)
        return getattr(task, name, default)
