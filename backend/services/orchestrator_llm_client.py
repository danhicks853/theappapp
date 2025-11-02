"""LLM client used by the orchestrator for reasoning and coordination.

Implements the requirements from Decision 67 for chain-of-thought reasoning,
agent selection, and progress evaluation. The client relies on the shared
prompt utilities defined in ``backend.prompts.orchestrator_prompts``.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Protocol, Sequence

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from backend.prompts.orchestrator_prompts import (
    BASE_SYSTEM_PROMPT,
    CollaborationRecord,
    RAGPattern,
    build_context,
    validate_prompt_requirements,
)


class TokenLogger(Protocol):
    """Typed protocol for logging token usage (Decision 75 alignment)."""

    async def log(
        self,
        *,
        agent: str,
        model: str,
        tokens_input: int,
        tokens_output: int,
        project_id: Optional[str] = None,
        decision_type: Optional[str] = None,
    ) -> None:
        """Persist token usage information asynchronously."""


@dataclass(frozen=True)
class OrchestratorDecision:
    """Structured decision payload returned by the LLM client."""

    reasoning: str
    decision: Dict[str, Any]
    confidence: float


class OrchestratorLLMClient:
    """Wrapper around OpenAI chat completions for orchestrator reasoning."""

    def __init__(
        self,
        *,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        openai_client: Optional[AsyncOpenAI] = None,
        token_logger: Optional[TokenLogger] = None,
        project_id: Optional[str] = None,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self._client = openai_client or AsyncOpenAI()
        self._token_logger = token_logger
        self._project_id = project_id

        validate_prompt_requirements(BASE_SYSTEM_PROMPT)

    async def reason_about_task(
        self,
        *,
        decision_type: str,
        project_context: Mapping[str, Any],
        decision_context: Mapping[str, Any],
        rag_patterns: Sequence[RAGPattern] = (),
        collaboration_history: Sequence[CollaborationRecord] = (),
        autonomy_level: str = "medium",
    ) -> OrchestratorDecision:
        """Produce a structured decision for the orchestrator."""

        context = build_context(
            project_context=project_context,
            decision_context=decision_context,
            rag_patterns=rag_patterns,
            collaboration_history=collaboration_history,
            autonomy_level=autonomy_level,
        )
        prompt = self._build_user_prompt(decision_type=decision_type, context=context)

        response = await self._create_chat_completion(prompt)
        payload = self._parse_response(response)

        await self._log_tokens(response, decision_type)
        return OrchestratorDecision(
            reasoning=payload["reasoning"],
            decision=payload["decision"],
            confidence=float(payload["confidence"]),
        )

    async def select_agent(
        self,
        *,
        task_description: str,
        candidate_agents: Sequence[Dict[str, Any]],
        project_context: Mapping[str, Any],
        rag_patterns: Sequence[RAGPattern] = (),
        autonomy_level: str = "medium",
    ) -> OrchestratorDecision:
        """Choose the most appropriate agent for a task."""

        decision_context = {
            "decision_type": "agent_selection",
            "situation": task_description,
            "options": [agent.get("name", agent.get("agent_type")) for agent in candidate_agents],
            "constraints": "Select the best-suited agent based on expertise and availability.",
            "urgency": "medium",
        }

        return await self.reason_about_task(
            decision_type="agent_selection",
            project_context=project_context,
            decision_context=decision_context,
            rag_patterns=rag_patterns,
            autonomy_level=autonomy_level,
        )

    async def evaluate_progress(
        self,
        *,
        progress_summary: str,
        project_context: Mapping[str, Any],
        autonomy_level: str = "medium",
    ) -> float:
        """Translate project progress into a confidence score (0.0-1.0)."""

        decision_context = {
            "decision_type": "progress_evaluation",
            "situation": progress_summary,
            "options": ["continue", "adjust", "escalate"],
            "constraints": "Return a confidence score between 0.0 and 1.0",
            "urgency": "medium",
        }

        decision = await self.reason_about_task(
            decision_type="progress_evaluation",
            project_context=project_context,
            decision_context=decision_context,
            autonomy_level=autonomy_level,
        )
        return max(0.0, min(1.0, decision.confidence))

    async def _create_chat_completion(self, user_prompt: str) -> ChatCompletion:
        """Call the OpenAI chat completions endpoint."""

        return await self._client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": BASE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

    async def _log_tokens(self, response: ChatCompletion, decision_type: str) -> None:
        if not self._token_logger or not response.usage:
            return

        await self._token_logger.log(
            agent="orchestrator",
            model=response.model,
            tokens_input=response.usage.prompt_tokens or 0,
            tokens_output=response.usage.completion_tokens or 0,
            project_id=self._project_id,
            decision_type=decision_type,
        )

    def _build_user_prompt(self, *, decision_type: str, context: str) -> str:
        instructions = (
            "You must respond with a JSON object containing: reasoning (string), "
            "decision (object), and confidence (float between 0 and 1)."
        )
        return (
            f"[ORCHESTRATOR CONTEXT]\n{context}\n"
            f"Decision Type: {decision_type}\n"
            f"{instructions}\n"
            "When providing the decision object, include `action`, `details`, and `next_steps`."
        )

    def _parse_response(self, response: ChatCompletion) -> Dict[str, Any]:
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise ValueError("Empty response from orchestrator LLM")

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise ValueError("LLM response was not valid JSON") from exc

        missing_fields = {"reasoning", "decision", "confidence"} - payload.keys()
        if missing_fields:
            raise ValueError(
                "LLM response missing required fields: " + ", ".join(sorted(missing_fields))
            )

        return payload


async def warm_start(client: OrchestratorLLMClient) -> None:
    """Small helper to warm the client (useful in tests to prime connections)."""

    await asyncio.sleep(0)
