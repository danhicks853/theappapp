"""System prompts and context builders for the orchestrator LLM client.

This module translates Decision 67 prompt requirements into concrete helpers that
can be reused across orchestrator LLM interactions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

# Maximum token budget for orchestrator prompts. Decision 67 specifies an
# 8000-token ceiling; we approximate by dividing character count by four.
_MAX_TOKENS = 8000
_TOKEN_APPROX_CHARS = 4

# ---------------------------------------------------------------------------
# System prompt template
# ---------------------------------------------------------------------------

BASE_SYSTEM_PROMPT = """You are the Orchestrator, the central coordinator for autonomous software development.

Your role:
- Coordinate all agents in the hub-and-spoke architecture
- Make strategic decisions about task routing and agent assignments
- Vet project decisions with appropriate specialists
- Detect when human intervention is needed
- Manage project state and ensure progress

Your responsibilities:
- Maintain complete project awareness (state, history, progress)
- Route tasks to appropriate agents with minimal necessary context
- Query knowledge base for relevant patterns and inject into agent context
- Detect agent loops and progress vs identical failures
- Escalate to humans based on autonomy level and situation criticality

Your constraints:
- All agent communication flows through you (hub-and-spoke)
- You must use chain-of-thought reasoning for transparency
- You defer to Project Manager for project design decisions
- You vet PM decisions with specialists before execution
- You never send tasks directly between agents

Your approach:
- Strategic: Think several steps ahead
- Collaborative: Leverage specialist expertise
- Transparent: Show your reasoning process
- Adaptive: Learn from knowledge retrieved via RAG
- Prudent: Escalate when uncertain
"""

_REQUIRED_PROMPT_SECTIONS = (
    "Your role:",
    "Your responsibilities:",
    "Your constraints:",
    "Your approach:",
)


@dataclass(frozen=True)
class RAGPattern:
    """Normalized representation of orchestrator-mediated RAG results."""

    title: str
    success_count: int
    problem: str
    solution: str
    when_to_try: str
    similarity: float


@dataclass(frozen=True)
class CollaborationRecord:
    """Snapshot of prior specialist consultations relevant to a decision."""

    specialist_type: str
    summary: str
    outcome: str


def _approximate_tokens(text: str) -> int:
    """Return a coarse token approximation for the given text."""

    if not text:
        return 0
    return max(1, len(text) // _TOKEN_APPROX_CHARS)


def build_context(
    *,
    project_context: Mapping[str, object],
    decision_context: Mapping[str, object],
    rag_patterns: Sequence[RAGPattern] = (),
    autonomy_level: str,
    collaboration_history: Sequence[CollaborationRecord] = (),
) -> str:
    """Assemble the orchestrator context layer described in Decision 67.

    Args:
        project_context: High-level project metadata (name, phase, progress).
        decision_context: Current situation requiring orchestration.
        rag_patterns: Ranked historical knowledge entries for the task.
        autonomy_level: Current autonomy slider setting (low/medium/high).
        collaboration_history: Prior collaboration decisions for reference.

    Returns:
        Fully formatted context string ready for prompt injection.

    Raises:
        ValueError: If the resulting prompt would exceed the token budget.
    """

    project_lines = [
        f"Current Project: {project_context.get('project_name', 'Unknown')}",
        f"Current Phase: {project_context.get('phase_name', 'Unknown')} ({project_context.get('phase_progress', '0')}%)",
        f"Autonomy Level: {autonomy_level}",
        "",
        "Project State:",
        f"- Active Agent: {project_context.get('active_agent', 'None')} working on {project_context.get('active_task', 'No task')}",
        f"- Completed Tasks: {project_context.get('completed_tasks', 0)}",
        f"- Pending Tasks: {project_context.get('pending_tasks', 0)}",
        f"- Recent Decisions: {project_context.get('recent_decisions', 'None')}",
        "",
        "Recent Agent Activity:",
        str(project_context.get('recent_agent_activity', 'No recent activity recorded.')),
        "",
        "Available Agents:",
        str(project_context.get('agent_roster', 'No agents registered.')),
        "",
    ]

    rag_section: list[str] = []
    if rag_patterns:
        rag_section.append("[ORCHESTRATOR CONTEXT: Historical Knowledge]")
        rag_section.append("Similar situations have been resolved these ways:\n")
        for idx, pattern in enumerate(rag_patterns[:3], start=1):
            if pattern.success_count >= 5:
                label = "Most Common"
            elif pattern.success_count >= 3:
                label = "Moderate"
            else:
                label = "Less Common"
            rag_section.extend(
                [
                    f"Pattern {idx} ({label} - {pattern.success_count} successes, similarity={pattern.similarity:.2f}):",
                    f"- Problem: {pattern.problem}",
                    f"- Solution: {pattern.solution}",
                    f"- When to try: {pattern.when_to_try}",
                    "",
                ]
            )
        rag_section.append(
            "Recommendation: Try patterns in order. Pattern 1 is most likely based on historical data."
        )
        rag_section.append("[END CONTEXT]\n")

    collaboration_section: list[str] = []
    if collaboration_history:
        collaboration_section.append("Collaboration History:")
        for record in collaboration_history:
            collaboration_section.extend(
                [
                    f"- Specialist: {record.specialist_type}",
                    f"  Summary: {record.summary}",
                    f"  Outcome: {record.outcome}",
                ]
            )
        collaboration_section.append("")

    decision_lines = [
        "Decision Context:",
        f"Decision Required: {decision_context.get('decision_type', 'unspecified')}",
        f"Situation: {decision_context.get('situation', 'No description provided')}\n",
        "Options:",
    ]

    options = decision_context.get("options")
    if isinstance(options, Iterable):
        for option in options:  # type: ignore[assignment]
            decision_lines.append(f"- {option}")
    else:
        decision_lines.append("- None provided")

    decision_lines.extend(
        [
            "",
            f"Constraints: {decision_context.get('constraints', 'None noted')}",
            f"Urgency: {decision_context.get('urgency', 'unspecified')}",
        ]
    )

    sections = project_lines + rag_section + collaboration_section + decision_lines
    context_block = "\n".join(sections).strip() + "\n"

    total_tokens = _approximate_tokens(BASE_SYSTEM_PROMPT) + _approximate_tokens(context_block)
    if total_tokens > _MAX_TOKENS:
        raise ValueError(
            "Composed orchestrator prompt exceeds token budget. "
            f"Estimated tokens={total_tokens}, limit={_MAX_TOKENS}."
        )

    return context_block


def validate_prompt_requirements(prompt: str) -> None:
    """Ensure the prompt contains all mandated sections from Decision 67."""

    missing = [section for section in _REQUIRED_PROMPT_SECTIONS if section not in prompt]
    if missing:
        raise ValueError(
            "Prompt is missing required sections: " + ", ".join(missing)
        )

    tokens = _approximate_tokens(prompt)
    if tokens > _MAX_TOKENS:
        raise ValueError(
            "Prompt violates orchestrator token budget. "
            f"Estimated tokens={tokens}, limit={_MAX_TOKENS}."
        )
