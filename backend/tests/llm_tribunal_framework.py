"""
LLM Tribunal Testing Framework

Implements two-stage LLM testing per Decision 72:
- Stage 1: Rubric Validation (fast, deterministic)
- Stage 2: AI Panel Evaluation (3-judge consensus)

Reference: docs/testing/testing_philosophy.md
"""
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class EvaluationCriteria(str, Enum):
    """Evaluation criteria for AI tribunal."""
    LOGICAL_CONSISTENCY = "logical_consistency"
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    INSTRUCTION_ADHERENCE = "instruction_adherence"
    CODE_QUALITY = "code_quality"
    SECURITY_AWARENESS = "security_awareness"


@dataclass
class RubricResult:
    """Result of Stage 1 rubric validation."""
    passed: bool
    errors: List[str]
    warnings: List[str]
    score: float  # 0-1


@dataclass
class JudgeEvaluation:
    """Single judge's evaluation."""
    judge_id: str
    criteria: EvaluationCriteria
    score: float  # 0-1
    confidence: float  # 0-1
    reasoning: str
    passed: bool  # True if score >= threshold


@dataclass
class TribunalVerdict:
    """Final tribunal verdict with consensus."""
    passed: bool
    consensus_score: float  # Average of judges
    consensus_confidence: float  # Average confidence
    judge_evaluations: List[JudgeEvaluation]
    unanimous: bool
    reasoning: str


class RubricValidator:
    """
    Stage 1: Rubric Validation
    
    Fast, deterministic validation of LLM response structure.
    """
    
    @staticmethod
    def validate_goal_proximity_response(response: Dict[str, Any]) -> RubricResult:
        """
        Validate orchestrator goal proximity LLM response.
        
        Required structure:
        {
            "proximity_score": float (0-1),
            "reasoning": str (non-empty),
            "evidence": str (non-empty),
            "confidence": float (0-1)
        }
        """
        errors = []
        warnings = []
        score = 1.0
        
        # Check required fields
        required_fields = ["proximity_score", "reasoning", "evidence", "confidence"]
        for field in required_fields:
            if field not in response:
                errors.append(f"Missing required field: {field}")
                score -= 0.25
        
        # Validate proximity_score
        if "proximity_score" in response:
            proximity = response["proximity_score"]
            if not isinstance(proximity, (int, float)):
                errors.append(f"proximity_score must be number, got {type(proximity).__name__}")
                score -= 0.2
            elif not (0 <= proximity <= 1):
                errors.append(f"proximity_score must be 0-1, got {proximity}")
                score -= 0.2
        
        # Validate confidence
        if "confidence" in response:
            confidence = response["confidence"]
            if not isinstance(confidence, (int, float)):
                errors.append(f"confidence must be number, got {type(confidence).__name__}")
                score -= 0.2
            elif not (0 <= confidence <= 1):
                errors.append(f"confidence must be 0-1, got {confidence}")
                score -= 0.2
        
        # Validate reasoning
        if "reasoning" in response:
            reasoning = response["reasoning"]
            if not isinstance(reasoning, str):
                errors.append(f"reasoning must be string, got {type(reasoning).__name__}")
                score -= 0.15
            elif len(reasoning.strip()) == 0:
                warnings.append("reasoning is empty")
                score -= 0.05
            elif len(reasoning.strip()) < 20:
                warnings.append("reasoning is very short (< 20 chars)")
                score -= 0.05
        
        # Validate evidence
        if "evidence" in response:
            evidence = response["evidence"]
            if not isinstance(evidence, str):
                errors.append(f"evidence must be string, got {type(evidence).__name__}")
                score -= 0.15
            elif len(evidence.strip()) == 0:
                warnings.append("evidence is empty")
                score -= 0.05
        
        passed = len(errors) == 0 and score >= 0.7
        
        return RubricResult(
            passed=passed,
            errors=errors,
            warnings=warnings,
            score=max(0.0, score)
        )
    
    @staticmethod
    def validate_prompt_improvement_response(response: Dict[str, Any]) -> RubricResult:
        """
        Validate AI assistant prompt improvement response.
        
        Required structure:
        {
            "suggestions": [{"suggestion": str, "rationale": str}],
            "confidence": float (0-1),
            "reasoning": str
        }
        """
        errors = []
        warnings = []
        score = 1.0
        
        # Check required fields
        required_fields = ["suggestions", "confidence", "reasoning"]
        for field in required_fields:
            if field not in response:
                errors.append(f"Missing required field: {field}")
                score -= 0.33
        
        # Validate suggestions
        if "suggestions" in response:
            suggestions = response["suggestions"]
            if not isinstance(suggestions, list):
                errors.append(f"suggestions must be list, got {type(suggestions).__name__}")
                score -= 0.3
            elif len(suggestions) == 0:
                warnings.append("suggestions list is empty")
                score -= 0.1
            else:
                for i, suggestion in enumerate(suggestions):
                    if not isinstance(suggestion, dict):
                        errors.append(f"suggestion[{i}] must be dict")
                        score -= 0.1
                    elif "suggestion" not in suggestion:
                        errors.append(f"suggestion[{i}] missing 'suggestion' field")
                        score -= 0.1
                    elif "rationale" not in suggestion:
                        errors.append(f"suggestion[{i}] missing 'rationale' field")
                        score -= 0.1
        
        # Validate confidence
        if "confidence" in response:
            confidence = response["confidence"]
            if not isinstance(confidence, (int, float)):
                errors.append(f"confidence must be number")
                score -= 0.2
            elif not (0 <= confidence <= 1):
                errors.append(f"confidence must be 0-1")
                score -= 0.2
        
        # Validate reasoning
        if "reasoning" in response:
            reasoning = response["reasoning"]
            if not isinstance(reasoning, str):
                errors.append(f"reasoning must be string")
                score -= 0.2
            elif len(reasoning.strip()) == 0:
                warnings.append("reasoning is empty")
                score -= 0.1
        
        passed = len(errors) == 0 and score >= 0.7
        
        return RubricResult(
            passed=passed,
            errors=errors,
            warnings=warnings,
            score=max(0.0, score)
        )


class AITribunal:
    """
    Stage 2: AI Panel Evaluation
    
    3-judge consensus panel for semantic quality assessment.
    """
    
    def __init__(self, openai_client=None):
        """Initialize tribunal with OpenAI client (or mock for testing)."""
        self.openai_client = openai_client
    
    async def evaluate_goal_proximity_quality(
        self,
        task_goal: str,
        current_state: str,
        llm_response: Dict[str, Any],
        threshold: float = 0.8
    ) -> TribunalVerdict:
        """
        Tribunal evaluates goal proximity LLM response quality.
        
        Judge 1: Logical consistency (is reasoning sound?)
        Judge 2: Completeness (covers all aspects?)
        Judge 3: Accuracy (matches actual state?)
        
        Requires ≥80% confidence consensus.
        """
        judge_evaluations = []
        
        # Judge 1: Logical Consistency
        judge1 = await self._evaluate_judge(
            judge_id="judge_1",
            criteria=EvaluationCriteria.LOGICAL_CONSISTENCY,
            prompt=self._build_logical_consistency_prompt(
                task_goal, current_state, llm_response
            ),
            threshold=threshold
        )
        judge_evaluations.append(judge1)
        
        # Judge 2: Completeness
        judge2 = await self._evaluate_judge(
            judge_id="judge_2",
            criteria=EvaluationCriteria.COMPLETENESS,
            prompt=self._build_completeness_prompt(
                task_goal, current_state, llm_response
            ),
            threshold=threshold
        )
        judge_evaluations.append(judge2)
        
        # Judge 3: Accuracy
        judge3 = await self._evaluate_judge(
            judge_id="judge_3",
            criteria=EvaluationCriteria.ACCURACY,
            prompt=self._build_accuracy_prompt(
                task_goal, current_state, llm_response
            ),
            threshold=threshold
        )
        judge_evaluations.append(judge3)
        
        # Calculate consensus
        consensus_score = sum(j.score for j in judge_evaluations) / len(judge_evaluations)
        consensus_confidence = sum(j.confidence for j in judge_evaluations) / len(judge_evaluations)
        unanimous = all(j.passed for j in judge_evaluations)
        passed = consensus_score >= threshold and consensus_confidence >= threshold
        
        # Build reasoning
        reasoning = self._build_consensus_reasoning(judge_evaluations)
        
        return TribunalVerdict(
            passed=passed,
            consensus_score=consensus_score,
            consensus_confidence=consensus_confidence,
            judge_evaluations=judge_evaluations,
            unanimous=unanimous,
            reasoning=reasoning
        )
    
    async def _evaluate_judge(
        self,
        judge_id: str,
        criteria: EvaluationCriteria,
        prompt: str,
        threshold: float
    ) -> JudgeEvaluation:
        """Execute single judge evaluation."""
        if self.openai_client is None:
            # Mock for testing
            return JudgeEvaluation(
                judge_id=judge_id,
                criteria=criteria,
                score=0.85,
                confidence=0.9,
                reasoning="Mock judge evaluation",
                passed=True
            )
        
        # Real OpenAI evaluation
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"You are evaluating LLM output for {criteria.value}."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3  # Low temperature for consistent evaluation
            )
            
            # Parse response
            content = response.choices[0].message.content
            evaluation = json.loads(content)
            
            return JudgeEvaluation(
                judge_id=judge_id,
                criteria=criteria,
                score=evaluation["score"],
                confidence=evaluation["confidence"],
                reasoning=evaluation["reasoning"],
                passed=evaluation["score"] >= threshold
            )
            
        except Exception as e:
            logger.error(f"Judge {judge_id} evaluation failed: {e}")
            return JudgeEvaluation(
                judge_id=judge_id,
                criteria=criteria,
                score=0.0,
                confidence=0.0,
                reasoning=f"Evaluation failed: {e}",
                passed=False
            )
    
    def _build_logical_consistency_prompt(
        self,
        task_goal: str,
        current_state: str,
        llm_response: Dict[str, Any]
    ) -> str:
        """Build prompt for logical consistency evaluation."""
        return f"""Evaluate the logical consistency of this LLM response.

Task Goal: {task_goal}
Current State: {current_state}

LLM Response:
{json.dumps(llm_response, indent=2)}

Evaluate:
1. Is the reasoning logically sound?
2. Do the conclusions follow from the evidence?
3. Are there logical fallacies or contradictions?

Respond in JSON:
{{
    "score": <0-1>,
    "confidence": <0-1>,
    "reasoning": "<your analysis>"
}}
"""
    
    def _build_completeness_prompt(
        self,
        task_goal: str,
        current_state: str,
        llm_response: Dict[str, Any]
    ) -> str:
        """Build prompt for completeness evaluation."""
        return f"""Evaluate the completeness of this LLM response.

Task Goal: {task_goal}
Current State: {current_state}

LLM Response:
{json.dumps(llm_response, indent=2)}

Evaluate:
1. Does it address all aspects of the task?
2. Is the evidence comprehensive?
3. Are edge cases considered?

Respond in JSON:
{{
    "score": <0-1>,
    "confidence": <0-1>,
    "reasoning": "<your analysis>"
}}
"""
    
    def _build_accuracy_prompt(
        self,
        task_goal: str,
        current_state: str,
        llm_response: Dict[str, Any]
    ) -> str:
        """Build prompt for accuracy evaluation."""
        return f"""Evaluate the accuracy of this LLM response.

Task Goal: {task_goal}
Current State: {current_state}

LLM Response:
{json.dumps(llm_response, indent=2)}

Evaluate:
1. Does the proximity score match the actual progress?
2. Is the evidence accurately described?
3. Are there factual errors?

Respond in JSON:
{{
    "score": <0-1>,
    "confidence": <0-1>,
    "reasoning": "<your analysis>"
}}
"""
    
    def _build_consensus_reasoning(self, evaluations: List[JudgeEvaluation]) -> str:
        """Build consensus reasoning from all judges."""
        lines = ["Tribunal Evaluation:"]
        for eval in evaluations:
            status = "PASS" if eval.passed else "FAIL"
            lines.append(f"- {eval.criteria.value}: {status} (score: {eval.score:.2f}, confidence: {eval.confidence:.2f})")
            lines.append(f"  {eval.reasoning}")
        return "\n".join(lines)


# Convenience functions for tests

def validate_llm_response_rubric(response: Dict[str, Any], response_type: str) -> RubricResult:
    """
    Validate LLM response using rubric (Stage 1).
    
    Args:
        response: LLM response dict
        response_type: "goal_proximity" or "prompt_improvement"
    
    Returns:
        RubricResult with pass/fail and details
    """
    if response_type == "goal_proximity":
        return RubricValidator.validate_goal_proximity_response(response)
    elif response_type == "prompt_improvement":
        return RubricValidator.validate_prompt_improvement_response(response)
    else:
        raise ValueError(f"Unknown response_type: {response_type}")


async def evaluate_llm_response_tribunal(
    response: Dict[str, Any],
    context: Dict[str, Any],
    openai_client=None,
    threshold: float = 0.8
) -> TribunalVerdict:
    """
    Evaluate LLM response using AI tribunal (Stage 2).
    
    Args:
        response: LLM response dict
        context: Context dict with task_goal, current_state, etc.
        openai_client: OpenAI client (or None for mocks)
        threshold: Pass threshold (default 0.8)
    
    Returns:
        TribunalVerdict with consensus evaluation
    """
    tribunal = AITribunal(openai_client)
    
    return await tribunal.evaluate_goal_proximity_quality(
        task_goal=context.get("task_goal", ""),
        current_state=context.get("current_state", ""),
        llm_response=response,
        threshold=threshold
    )
