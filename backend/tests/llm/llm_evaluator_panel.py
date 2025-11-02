"""LLM Evaluator Panel for two-stage testing per Decision 72.

This module provides the infrastructure for Stage 2 semantic evaluation using
a panel of LLM evaluators to assess reasoning quality, consistency, and adherence
to requirements.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

from openai import AsyncOpenAI


@dataclass(frozen=True)
class EvaluationCriteria:
    """Single criterion for evaluating LLM output quality."""

    name: str
    description: str
    weight: float = 1.0


@dataclass(frozen=True)
class EvaluatorResult:
    """Result from a single evaluator assessing one criterion."""

    criterion: str
    score: float  # 0.0-1.0
    reasoning: str
    evaluator_id: int


@dataclass(frozen=True)
class PanelEvaluation:
    """Aggregated results from the evaluator panel."""

    consensus_passed: bool
    confidence: float  # 0.0-1.0
    criteria_scores: Dict[str, float]  # criterion name -> average score
    individual_results: List[EvaluatorResult]
    consensus_threshold: float


class LLMEvaluatorPanel:
    """Panel of LLM evaluators for semantic quality assessment.

    Per Decision 72, Stage 2 tests use a 3-evaluator panel to assess LLM output
    quality against semantic criteria. Requires consensus (2/3) for passing.
    """

    def __init__(
        self,
        *,
        evaluator_count: int = 3,
        model: str = "gpt-4o-mini",
        consensus_threshold: float = 0.66,
        openai_client: AsyncOpenAI | None = None,
    ) -> None:
        """Initialize the evaluator panel.

        Args:
            evaluator_count: Number of evaluators in the panel (default: 3)
            model: OpenAI model to use for evaluation
            consensus_threshold: Minimum agreement ratio for consensus (default: 0.66 for 2/3)
            openai_client: Optional AsyncOpenAI client (for testing)
        """
        self.evaluator_count = evaluator_count
        self.model = model
        self.consensus_threshold = consensus_threshold
        self._client = openai_client or AsyncOpenAI()

    async def evaluate(
        self,
        *,
        output: Any,
        criteria: Sequence[EvaluationCriteria],
        context: str = "",
    ) -> PanelEvaluation:
        """Evaluate LLM output using the evaluator panel.

        Args:
            output: The LLM output to evaluate (dict, string, or object with __dict__)
            criteria: List of evaluation criteria to assess
            context: Optional context about what the output should contain

        Returns:
            PanelEvaluation with consensus and detailed scores
        """
        # Convert output to string representation for evaluation
        if hasattr(output, "__dict__"):
            output_str = str(output.__dict__)
        elif isinstance(output, dict):
            output_str = str(output)
        else:
            output_str = str(output)

        # Run evaluations in parallel for all criteria across all evaluators
        tasks = []
        for criterion in criteria:
            for evaluator_id in range(self.evaluator_count):
                tasks.append(
                    self._evaluate_single(
                        output_str=output_str,
                        criterion=criterion,
                        evaluator_id=evaluator_id,
                        context=context,
                    )
                )

        results = await asyncio.gather(*tasks)

        # Aggregate scores by criterion
        criteria_scores: Dict[str, List[float]] = {c.name: [] for c in criteria}
        for result in results:
            criteria_scores[result.criterion].append(result.score)

        # Calculate average score per criterion
        avg_scores = {
            criterion: sum(scores) / len(scores)
            for criterion, scores in criteria_scores.items()
        }

        # Calculate overall confidence (weighted average)
        total_weight = sum(c.weight for c in criteria)
        confidence = sum(
            avg_scores[c.name] * c.weight for c in criteria
        ) / total_weight

        # Consensus: at least threshold ratio of evaluators must pass (score >= 0.7)
        passing_count = sum(1 for score in avg_scores.values() if score >= 0.7)
        consensus_passed = (passing_count / len(criteria)) >= self.consensus_threshold

        return PanelEvaluation(
            consensus_passed=consensus_passed,
            confidence=confidence,
            criteria_scores=avg_scores,
            individual_results=results,
            consensus_threshold=self.consensus_threshold,
        )

    async def _evaluate_single(
        self,
        *,
        output_str: str,
        criterion: EvaluationCriteria,
        evaluator_id: int,
        context: str,
    ) -> EvaluatorResult:
        """Have a single evaluator assess one criterion.

        Args:
            output_str: String representation of the output
            criterion: The criterion to evaluate
            evaluator_id: Identifier for this evaluator (0-indexed)
            context: Context about expected output

        Returns:
            EvaluatorResult with score and reasoning
        """
        prompt = self._build_evaluation_prompt(
            output_str=output_str,
            criterion=criterion,
            context=context,
        )

        response = await self._client.chat.completions.create(
            model=self.model,
            temperature=0.3,  # Deterministic evaluation
            messages=[
                {
                    "role": "system",
                    "content": "You are an objective evaluator assessing LLM output quality. "
                    "Provide a score from 0.0 to 1.0 and brief reasoning.",
                },
                {"role": "user", "content": prompt},
            ],
        )

        content = response.choices[0].message.content or ""
        score, reasoning = self._parse_evaluation_response(content)

        return EvaluatorResult(
            criterion=criterion.name,
            score=score,
            reasoning=reasoning,
            evaluator_id=evaluator_id,
        )

    def _build_evaluation_prompt(
        self,
        *,
        output_str: str,
        criterion: EvaluationCriteria,
        context: str,
    ) -> str:
        """Build prompt for evaluator to assess one criterion."""
        return f"""Evaluate the following LLM output against this criterion:

Criterion: {criterion.name}
Description: {criterion.description}

Context (what the output should contain):
{context if context else 'No additional context provided'}

Output to evaluate:
{output_str}

Provide your evaluation in this format:
SCORE: <float between 0.0 and 1.0>
REASONING: <brief explanation of your score>

Focus only on the specified criterion. Be objective and consistent."""

    def _parse_evaluation_response(self, content: str) -> tuple[float, str]:
        """Parse evaluator response to extract score and reasoning."""
        lines = content.strip().split("\n")
        score = 0.5  # default if parsing fails
        reasoning = "Parsing failed"

        for line in lines:
            if line.startswith("SCORE:"):
                try:
                    score = float(line.split("SCORE:")[1].strip())
                    score = max(0.0, min(1.0, score))  # clamp to valid range
                except (ValueError, IndexError):
                    pass
            elif line.startswith("REASONING:"):
                reasoning = line.split("REASONING:")[1].strip()

        return score, reasoning


# Pre-defined common criteria for orchestrator evaluation
ORCHESTRATOR_CRITERIA = [
    EvaluationCriteria(
        name="logical_consistency",
        description="The reasoning follows a logical flow without contradictions",
        weight=1.5,
    ),
    EvaluationCriteria(
        name="completeness",
        description="All relevant factors are considered in the decision",
        weight=1.0,
    ),
    EvaluationCriteria(
        name="accuracy",
        description="Facts and constraints are correctly interpreted",
        weight=1.5,
    ),
    EvaluationCriteria(
        name="instruction_adherence",
        description="The output follows the specified format and requirements",
        weight=1.0,
    ),
]
