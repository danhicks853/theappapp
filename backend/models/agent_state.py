"""Agent execution state models.

These dataclasses capture the runtime state required for the iterative
agent execution loop defined in Decision 83: Agent Execution Loop
Architecture. They provide complete observability for recovery flows,
loop detection, and confidence gating.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class LLMCall:
    """Record of an LLM invocation performed during a task step."""

    prompt: str
    response: str
    tokens_used: int = 0
    cost_usd: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ToolExecution:
    """Audit record for a tool execution routed through TAS."""

    request_id: str
    tool_name: str
    operation: str
    parameters: Dict[str, Any]
    status: str
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: Optional[datetime] = None


@dataclass
class Action:
    """Action plan produced for the next execution step."""

    description: str
    tool_name: Optional[str]
    operation: Optional[str]
    parameters: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def signature(self) -> str:
        """Return a deterministic signature for loop comparison."""

        return "|".join(
            [
                self.description or "",
                self.tool_name or "",
                self.operation or "",
                str(sorted(self.parameters.items())),
            ]
        )


@dataclass
class Result:
    """Outcome of executing an action plan."""

    success: bool
    output: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    attempt: int = 1
    duration_ms: Optional[int] = None


@dataclass
class ValidationResult:
    """Validation signal confirming whether progress was achieved."""

    success: bool
    issues: Sequence[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    @property
    def error_signature(self) -> str:
        """Return a condensed signature to feed loop detection."""

        if self.success or not self.issues:
            return ""
        return "|".join(sorted(str(issue) for issue in self.issues))


@dataclass
class Step:
    """Comprehensive audit record for a single iteration."""

    step_number: int
    timestamp: datetime
    reasoning: str
    action: Action
    result: Result
    validation: ValidationResult
    tokens_used: int = 0
    cost_usd: float = 0.0


@dataclass
class TaskState:
    """Mutable state describing end-to-end execution progress."""

    task_id: str
    agent_id: str
    project_id: Optional[str]
    goal: str
    acceptance_criteria: Sequence[str]
    constraints: Dict[str, Any]
    current_step: int = 0
    max_steps: int = 20
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    steps_history: List[Step] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    failure_count: int = 0
    last_errors: List[str] = field(default_factory=list)
    consecutive_failures: int = 0
    progress_score: float = 0.0
    progress_metrics: Dict[str, Any] = field(default_factory=dict)
    token_usage: List[int] = field(default_factory=list)
    llm_calls: List[LLMCall] = field(default_factory=list)
    tool_executions: List[ToolExecution] = field(default_factory=list)
    total_cost_usd: float = 0.0
    decision_reasoning: List[str] = field(default_factory=list)
    escalation_triggered: bool = False
    escalation_reason: Optional[str] = None
    timeout_reached: bool = False
    resource_limit_hit: bool = False
    last_confidence_check_step: int = 0
    last_confidence_score: Optional[float] = None

    def record_error(self, signature: str) -> None:
        """Track error signatures for loop detection analysis."""

        if signature:
            self.last_errors.append(signature)
            self.failure_count += 1
            self.consecutive_failures += 1

    def record_success(self) -> None:
        """Reset counters on successful iteration."""

        self.consecutive_failures = 0
        if self.failure_count > 0:
            self.failure_count -= 1


@dataclass
class TaskResult:
    """Final summary produced after task execution."""

    task_id: str
    success: bool
    steps: List[Step]
    artifacts: Dict[str, Any]
    reasoning: List[str]
    confidence: Optional[float]
    errors: Sequence[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


__all__ = [
    "Action",
    "LLMCall",
    "Result",
    "Step",
    "TaskResult",
    "TaskState",
    "ToolExecution",
    "ValidationResult",
]
