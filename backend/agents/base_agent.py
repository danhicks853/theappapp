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
from backend.services.openai_adapter import OpenAIAdapter
from backend.services.rag_service import RAGService
from backend.services.search_service import SearchService

logger = logging.getLogger(__name__)


class TASClient:
    """Tool Access Service client mixin for agents.
    
    Provides methods for agents to request tool access through TAS
    with proper permission checking and denial handling.
    """
    
    def __init__(self, agent_id: str, agent_type: str):
        """Initialize TAS client.
        
        Args:
            agent_id: Unique agent identifier
            agent_type: Type of agent (backend_dev, etc.)
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self._tas = None
    
    def _get_tas(self):
        """Lazy load TAS service."""
        if self._tas is None:
            from backend.services.tool_access_service import get_tool_access_service
            self._tas = get_tool_access_service()
        return self._tas
    
    async def request_tool_access(
        self,
        tool_name: str,
        operation: str,
        parameters: Dict[str, Any],
        project_id: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Request tool access through TAS.
        
        Args:
            tool_name: Name of tool to access
            operation: Operation to perform
            parameters: Operation parameters
            project_id: Associated project ID
            task_id: Associated task ID
        
        Returns:
            Tool execution result or denial message
        """
        from backend.services.tool_access_service import ToolExecutionRequest
        
        tas = self._get_tas()
        
        request = ToolExecutionRequest(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            tool_name=tool_name,
            operation=operation,
            parameters=parameters,
            project_id=project_id,
            task_id=task_id
        )
        
        response = await tas.execute_tool(request)
        
        return {
            "allowed": response.allowed,
            "success": response.success,
            "result": response.result,
            "message": response.message,
            "audit_id": response.audit_id
        }
    
    def validate_permission(
        self,
        tool_name: str,
        operation: str
    ) -> tuple[bool, str]:
        """Validate permission without executing (dry-run).
        
        Args:
            tool_name: Name of tool
            operation: Operation to check
        
        Returns:
            (allowed, reason)
        """
        tas = self._get_tas()
        return tas.check_permission(self.agent_type, tool_name, operation)
    
    def handle_denial(
        self,
        tool_name: str,
        operation: str,
        reason: str,
        state: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Handle tool access denial.
        
        Args:
            tool_name: Tool that was denied
            operation: Operation that was denied
            reason: Denial reason
            state: Optional task state for context
        
        Returns:
            Denial response with escalation options
        """
        logger.warning(
            f"Tool access denied for {self.agent_id} ({self.agent_type}): "
            f"tool={tool_name}, operation={operation}, reason={reason}"
        )
        
        return {
            "denied": True,
            "tool_name": tool_name,
            "operation": operation,
            "reason": reason,
            "escalation_available": True,  # For future gate creation
            "message": f"Access denied: {reason}"
        }
    
    async def request_permission_escalation(
        self,
        tool_name: str,
        operation: str,
        reason: str,
        context: Optional[Dict[str, Any]] = None,
        orchestrator: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Request permission escalation through human gate.
        
        Args:
            tool_name: Tool requiring elevated permission
            operation: Operation requiring permission
            reason: Why this permission is needed
            context: Additional context for human review
            orchestrator: Orchestrator instance for gate creation
        
        Returns:
            Escalation request response with gate ID
        """
        logger.info(
            f"Permission escalation requested: agent={self.agent_id}, "
            f"tool={tool_name}, operation={operation}"
        )
        
        # TODO: Integrate with gate system when available
        # For now, return structured escalation request
        escalation = {
            "escalation_requested": True,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool_name": tool_name,
            "operation": operation,
            "reason": reason,
            "context": context or {},
            "status": "pending_human_approval",
            "gate_id": None,  # Will be set when gate system integrated
            "message": f"Escalation requested: {reason}"
        }
        
        # When gate system is ready, create gate here:
        # if orchestrator:
        #     gate = await orchestrator.create_permission_gate(
        #         agent_id=self.agent_id,
        #         tool_name=tool_name,
        #         operation=operation,
        #         reason=reason,
        #         context=context
        #     )
        #     escalation["gate_id"] = gate.id
        #     escalation["status"] = "awaiting_approval"
        
        return escalation



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
        openai_adapter: Optional[OpenAIAdapter] = None,
        rag_service: Optional[RAGService] = None,
        search_service: Optional[SearchService] = None,
        system_prompt: Optional[str] = None,
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
        
        # MVP: New services for specialists
        self.openai_adapter = openai_adapter
        self.rag_service = rag_service
        self.search_service = search_service
        self.system_prompt = system_prompt
        
        # TAS client for direct tool access
        self.tas_client = TASClient(agent_id=agent_id, agent_type=agent_type)

    async def run_task(self, task: Any) -> TaskResult:
        """Execute a task using the iterative execution loop."""
        
        self.logger.info(f"🚀 RUN_TASK CALLED for agent {self.agent_id}")

        state = self._initialize_state(task)
        self.logger.info(
            "Starting task %s for project %s", state.task_id, state.project_id
        )

        while not self._should_terminate(state):
            print(f"🔄 Loop iteration {state.current_step} starting")
            action = await self._plan_next_step(state)
            result = await self._execute_step_with_retry(action, state)
            
            # Validate and update state BEFORE self-assessment
            validation = await self._validate_step(result, state)
            self._update_state(state, action, result, validation)
            
            # HARDCODED: Agent self-assesses if task is complete after key actions
            print(f"🔬 Checking if self-assessment needed (tool: {getattr(action, 'tool_name', None)})")
            try:
                is_complete = await self._self_assess_completion(state, action, result)
                print(f"🔍 Self-assessment result: {is_complete} (tool: {action.tool_name})")
                if is_complete:
                    print("✅ Agent self-assessed: Task complete - exiting loop")
                    # Mark as successful since self-assessment confirmed completion
                    state.record_success()
                    state.status = "completed"
                    state.progress_score = 1.0  # Mark as fully complete for success=True
                    return await self._finalize_result(state)
            except Exception as e:
                print(f"❌ Self-assessment failed: {e}")
                import traceback
                traceback.print_exc()

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

        print(f"🛑 Loop terminated - step:{state.current_step} max:{state.max_steps} timeout:{getattr(state, 'timeout_reached', False)}")
        return await self._finalize_result(state)

    def _initialize_state(self, task: Any) -> TaskState:
        """Construct the initial state object for execution."""

        payload = self._extract_task_payload(task)
        project_id = self._get_task_attribute(task, "project_id")
        acceptance = payload.get("acceptance_criteria", [])
        
        # Orchestrator provides fully contextualized goal - use it directly
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
                "agent_type": self.agent_type,
                "project_id": state.project_id,
                "task_id": state.task_id,
                "tool": action.tool_name,  # Orchestrator expects 'tool' not 'tool_name'
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

    async def _self_assess_completion(
        self,
        state: TaskState,
        action: Action,
        result: Result
    ) -> bool:
        """
        Agent self-assesses if task is complete (minimal tokens).
        
        Only checks after file_system or deliverable operations.
        Uses <100 tokens per check.
        """
        # Only check after key operations to minimize LLM calls
        if action.tool_name not in ["file_system", "deliverable"]:
            return False
        
        # Ultra-minimal prompt - truncate to save tokens
        goal_short = state.goal[:200] if state.goal else "task"
        action_desc = action.description[:100] if hasattr(action, 'description') else str(action.tool_name)
        
        prompt = f"""Task: {goal_short}
Action: {action_desc}

Complete? YES/NO:"""
        
        try:
            # Use simple completion with minimal tokens
            if hasattr(self.llm_client, 'simple_completion'):
                response = await self.llm_client.simple_completion(prompt, max_tokens=3)
            else:
                # Fallback to OpenAI adapter with API key from env
                import os
                from openai import AsyncOpenAI
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    self.logger.warning("No OPENAI_API_KEY - assuming task incomplete")
                    return False
                    
                client = AsyncOpenAI(api_key=api_key)
                completion = await client.chat.completions.create(
                    model="gpt-4o-mini",  # Cheapest model
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=3,
                    temperature=0
                )
                response = completion.choices[0].message.content
            
            is_complete = "YES" in response.upper()
            self.logger.info(f"🤔 Self-assessment: {'COMPLETE ✅' if is_complete else 'INCOMPLETE ⏳'}")
            return is_complete
            
        except Exception as e:
            self.logger.warning(f"Self-assessment failed: {e} - assuming incomplete")
            return False
    
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

    # MVP: Helper methods for specialists
    async def search_knowledge_base(self, query: str, limit: int = 5) -> list:
        """Search specialist's RAG knowledge base.
        
        MVP: Used by specialists to reference uploaded documentation.
        """
        if not self.rag_service:
            self.logger.debug("No RAG service configured for this agent")
            return []
        
        try:
            results = await self.rag_service.search(
                query=query,
                specialist_id=self.agent_id,
                limit=limit
            )
            self.logger.info(f"Found {len(results)} knowledge base results for: {query}")
            return [{"text": r.text, "score": r.score, "metadata": r.metadata} for r in results]
        except Exception as e:
            self.logger.error(f"Knowledge base search failed: {e}")
            return []
    
    async def search_web(self, query: str, search_config: Optional[Dict[str, Any]] = None) -> list:
        """Search the web with specialist-specific configuration.
        
        MVP: Used by specialists with scoped web search enabled.
        """
        if not self.search_service:
            self.logger.debug("No search service configured for this agent")
            return []
        
        try:
            if search_config:
                results = await self.search_service.search_with_config(query, search_config)
            else:
                results = await self.search_service.search(query)
            
            self.logger.info(f"Found {len(results)} web results for: {query}")
            return [{"title": r.title, "url": r.url, "snippet": r.snippet} for r in results]
        except Exception as e:
            self.logger.error(f"Web search failed: {e}")
            return []

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
