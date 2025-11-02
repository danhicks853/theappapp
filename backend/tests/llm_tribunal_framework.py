"""
LLM Tribunal Testing Framework - Production-Hardened Implementation

Hybrid multi-layer validation:
- Stage 0: Programmatic consistency checks (fast, free)
- Stage 1: Pydantic schema validation (fast, free)
- Stage 2: AI tribunal evaluation (slow, costs money)

Production features:
- Diverse judge models (gpt-4o, gpt-4o-mini, gpt-4-turbo)
- Median consensus for 3 judges (outlier resistant)
- Concurrent execution with timeouts
- Fail-closed on errors
- Full telemetry logging
"""
import json
import re
import statistics
import uuid
import asyncio
import time
import logging
from typing import List, Dict, Any, Literal
from pydantic import BaseModel, Field, ValidationError, field_validator

logger = logging.getLogger(__name__)


# ============================================================================
# Model Capabilities (avoid "works on my box" drift)
# ============================================================================

MODEL_CAPS = {
    "gpt-4o": {"temperature": True, "response_format": True},
    "gpt-4o-mini": {"temperature": True, "response_format": True},
    "gpt-4-turbo": {"temperature": True, "response_format": True},
    # Legacy/unsupported models
    "gpt-5": {"temperature": False, "response_format": True},  # No temperature support
}

ALLOWED_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]  # Production allowlist


def _judge_kwargs(model_name: str, temperature: float, seed: int) -> Dict[str, Any]:
    """
    Build API kwargs based on model capabilities.
    
    Prevents capability errors by checking model support.
    """
    caps = MODEL_CAPS.get(model_name, {"temperature": True, "response_format": False})
    
    kwargs = {
        "model": model_name,
        "seed": seed,
        "messages": [],  # Will be filled by caller
    }
    
    # Only add temperature if supported
    if caps["temperature"] and temperature is not None:
        kwargs["temperature"] = temperature
    
    # Only add response_format if supported
    if caps["response_format"]:
        kwargs["response_format"] = {"type": "json_object"}
    
    return kwargs


# ============================================================================
# Response Models (Pydantic for automatic validation)
# ============================================================================

class GoalProximity(BaseModel):
    """Goal proximity LLM response schema."""
    proximity_score: float = Field(ge=0, le=1, description="How close to goal (0-1)")
    reasoning: str = Field(min_length=1, description="Why this score")
    evidence: str = Field(min_length=1, description="Concrete evidence")
    confidence: float = Field(ge=0, le=1, description="Confidence in assessment")
    
    @field_validator("reasoning", "evidence")
    @classmethod
    def nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("cannot be empty")
        return v


class OrchestratorDecision(BaseModel):
    """Orchestrator decision response schema."""
    reasoning: str = Field(min_length=1, description="Decision reasoning")
    decision: Dict[str, Any] = Field(description="Structured decision")
    confidence: float = Field(ge=0, le=1, description="Confidence in decision")
    
    @field_validator("reasoning")
    @classmethod
    def nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("cannot be empty")
        return v
    
    @field_validator("decision")
    @classmethod
    def has_action(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if "action" not in v and "agent" not in v:
            raise ValueError("decision must have 'action' or 'agent'")
        return v


class PromptImprovement(BaseModel):
    """Prompt improvement response schema."""
    suggestions: List[Dict[str, str]] = Field(description="Improvement suggestions")
    confidence: float = Field(ge=0, le=1)
    reasoning: str = Field(min_length=1)
    
    @field_validator("suggestions")
    @classmethod
    def good_suggestions(cls, v: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if not v:
            raise ValueError("suggestions cannot be empty")
        for s in v:
            if "suggestion" not in s or "rationale" not in s:
                raise ValueError("each suggestion needs 'suggestion' and 'rationale'")
        return v
    
    @field_validator("reasoning")
    @classmethod
    def nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("cannot be empty")
        return v


# ============================================================================
# Result Models
# ============================================================================

class RubricResult(BaseModel):
    """Result of schema validation + consistency checks."""
    passed: bool
    score: float
    errors: List[str] = []
    warnings: List[str] = []
    consistency_issues: List[str] = []


class JudgeEval(BaseModel):
    """Single judge evaluation."""
    judge_id: str
    criteria: Literal["logical_consistency", "completeness", "accuracy"]
    score: float
    confidence: float
    passed: bool
    reasoning: str
    model_used: str = ""  # Track which model was used
    http_status: int = 200  # HTTP status code
    used_response_format: bool = False  # Whether JSON format was enforced


class Verdict(BaseModel):
    """Tribunal consensus verdict."""
    passed: bool
    consensus_score: float
    consensus_confidence: float
    unanimous: bool
    disagreement: float  # 0=all agree, 1=maximum disagreement
    evaluations: List[JudgeEval]
    reasoning: str
    trace_id: str  # For debugging/audit
    indeterminate: bool = False  # True if verdict couldn't be determined
    models_used: List[str] = []  # Track which models were used
    latency_ms: float = 0.0  # Total time taken
    estimated_cost: float = 0.0  # Estimated API cost


# ============================================================================
# Stage 0: Programmatic Consistency Checks
# ============================================================================

def _consistency_checks(resp: Dict[str, Any]) -> List[str]:
    """
    Fast programmatic logic checks.
    
    Catches obvious contradictions before expensive validation.
    Returns list of issues (empty = consistent).
    """
    issues = []
    s = resp.get("proximity_score")
    c = resp.get("confidence")
    r = (resp.get("reasoning", "") + " " + resp.get("evidence", "")).lower()
    
    # Extended phrase lists (from both systems)
    neg = (
        "no progress", "not started", "nothing done", "not implemented",
        "no files", "nothing implemented", "hasn't begun", "not created",
        "no work", "no code", "not working", "failed", "error"
    )
    pos = (
        "complete", "finished", "implemented", "working", "deployed",
        "passing", "successful", "done", "ready", "completed"
    )
    
    if isinstance(s, (int, float)):
        if s > 0.8 and any(p in r for p in neg):
            issues.append(f"high score ({s:.2f}) contradicts negative language")
        if s < 0.3 and any(p in r for p in pos):
            issues.append(f"low score ({s:.2f}) contradicts positive language")
        if 0.3 <= s <= 0.7:
            extreme = ("100%", "0%", "all done", "completely finished", "nothing", "none")
            if any(ex in r for ex in extreme):
                issues.append(f"mid score ({s:.2f}) uses extreme language")
    
    if isinstance(c, (int, float)):
        if c > 0.9 and any(w in r for w in ("uncertain", "maybe", "possibly", "perhaps")):
            issues.append(f"high confidence ({c:.2f}) but hedging language")
        if c < 0.5 and any(w in r for w in ("definitely", "certainly", "clearly", "obviously")):
            issues.append(f"low confidence ({c:.2f}) but definitive language")
    
    return issues


def _orchestrator_consistency_checks(resp: Dict[str, Any]) -> List[str]:
    """Consistency checks for orchestrator decision format."""
    issues = []
    c = resp.get("confidence")
    r = resp.get("reasoning", "").lower()
    decision = resp.get("decision", {})
    
    if isinstance(c, (int, float)):
        if c > 0.9 and any(w in r for w in ("uncertain", "unclear", "maybe")):
            issues.append(f"high confidence ({c:.2f}) but uncertain reasoning")
        if c < 0.4 and "clear" in r or "obvious" in r:
            issues.append(f"low confidence ({c:.2f}) but certain language")
    
    # Check decision structure
    if isinstance(decision, dict):
        if c and c > 0.8 and not decision:
            issues.append("high confidence but empty decision")
    
    return issues


# ============================================================================
# Stage 1: Schema Validation
# ============================================================================

def validate_goal_proximity(response: Dict[str, Any]) -> RubricResult:
    """
    Validate goal proximity response.
    
    Combines consistency checks + Pydantic validation.
    """
    errors = []
    warnings = []
    score = 1.0
    
    # Stage 0: Consistency checks
    issues = _consistency_checks(response)
    if issues:
        errors += issues
        score -= 0.25 * len(issues)
    
    # Stage 1: Schema validation
    try:
        GoalProximity(**response)
    except ValidationError as e:
        for err in e.errors():
            field = ".".join(str(x) for x in err["loc"])
            errors.append(f"{field}: {err['msg']}")
        score -= 0.2 * len(e.errors())
    
    # Additional warnings
    r = response.get("reasoning", "")
    if isinstance(r, str) and 0 < len(r.strip()) < 20:
        warnings.append("reasoning is very short")
        score -= 0.05
    
    return RubricResult(
        passed=(score >= 0.7 and not errors),
        score=max(0.0, score),
        errors=errors,
        warnings=warnings,
        consistency_issues=issues
    )


def validate_orchestrator_decision(response: Dict[str, Any]) -> RubricResult:
    """Validate orchestrator decision response."""
    errors = []
    warnings = []
    score = 1.0
    
    # Stage 0: Consistency checks
    issues = _orchestrator_consistency_checks(response)
    if issues:
        errors += issues
        score -= 0.25 * len(issues)
    
    # Stage 1: Schema validation
    try:
        OrchestratorDecision(**response)
    except ValidationError as e:
        for err in e.errors():
            field = ".".join(str(x) for x in err["loc"])
            errors.append(f"{field}: {err['msg']}")
        score -= 0.2 * len(e.errors())
    
    # Check decision quality
    decision = response.get("decision", {})
    if isinstance(decision, dict):
        if "next_steps" not in decision:
            warnings.append("decision missing next_steps")
            score -= 0.05
    
    return RubricResult(
        passed=(score >= 0.7 and not errors),
        score=max(0.0, score),
        errors=errors,
        warnings=warnings,
        consistency_issues=issues
    )


def validate_prompt_improvement(response: Dict[str, Any]) -> RubricResult:
    """Validate prompt improvement response."""
    errors = []
    warnings = []
    score = 1.0
    
    try:
        PromptImprovement(**response)
    except ValidationError as e:
        for err in e.errors():
            field = ".".join(str(x) for x in err["loc"])
            errors.append(f"{field}: {err['msg']}")
        score -= 0.2 * len(e.errors())
    
    r = response.get("reasoning", "")
    if isinstance(r, str) and 0 < len(r.strip()) < 20:
        warnings.append("reasoning short")
        score -= 0.05
    
    return RubricResult(
        passed=(score >= 0.7 and not errors),
        score=max(0.0, score),
        errors=errors,
        warnings=warnings,
        consistency_issues=[]
    )


# ============================================================================
# Stage 2: AI Tribunal
# ============================================================================

def _extract_json(txt: str) -> Dict[str, Any]:
    """Extract JSON from LLM response (handles markdown code blocks)."""
    # Try to find JSON at end
    m = re.search(r"\{.*\}$", txt.strip(), re.S)
    if not m:
        # Try anywhere in text
        m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        raise ValueError("no json found in response")
    return json.loads(m.group(0))


class Judge:
    """Single AI judge for tribunal evaluation."""
    
    def __init__(
        self,
        name: str,
        openai_client: Any,
        model_name: str,  # Specific model: gpt-5, gpt-4o, gpt-4.1-mini
        criteria: str,
        seed: int,
        temperature: float = 0.2,
        max_retries: int = 2,
        timeout_seconds: float = 8.0
    ):
        self.name = name
        self.openai_client = openai_client
        self.model_name = model_name
        self.criteria = criteria
        self.seed = seed
        self.temperature = temperature
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
    
    async def evaluate(
        self,
        task_goal: str,
        current_state: str,
        llm_response: Dict[str, Any]
    ) -> JudgeEval:
        """Evaluate LLM response quality."""
        sys_prompt = f"You are evaluating LLM output for {self.criteria}."
        user_prompt = (
            f"Task Goal: {task_goal}\n"
            f"Current State: {current_state}\n"
            f"LLM Response:\n{json.dumps(llm_response, ensure_ascii=False)}\n"
            f"Respond in JSON: {{\"score\":0-1,\"confidence\":0-1,\"reasoning\":\"...\"}}"
        )
        
        for attempt in range(self.max_retries + 1):
            try:
                # Build capability-aware kwargs
                api_kwargs = _judge_kwargs(self.model_name, self.temperature, self.seed)
                api_kwargs["messages"] = [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                
                used_response_format = "response_format" in api_kwargs
                
                # Call with timeout
                msg = await asyncio.wait_for(
                    self.openai_client.chat.completions.create(**api_kwargs),
                    timeout=self.timeout_seconds
                )
                
                data = _extract_json(msg.choices[0].message.content)
                s = float(data["score"])
                cf = float(data["confidence"])
                rs = str(data.get("reasoning", ""))
                
                return JudgeEval(
                    judge_id=self.name,
                    criteria=self.criteria,
                    score=max(0, min(1, s)),
                    confidence=max(0, min(1, cf)),
                    passed=s >= 0.8,
                    reasoning=rs,
                    model_used=self.model_name,
                    http_status=200,
                    used_response_format=used_response_format
                )
            except Exception as e:
                if attempt == self.max_retries:
                    # Last attempt failed
                    return JudgeEval(
                        judge_id=self.name,
                        criteria=self.criteria,
                        score=0.0,
                        confidence=0.0,
                        passed=False,
                        reasoning=f"parse_error: {str(e)}"
                    )
                continue
        
        # Should never reach here
        return JudgeEval(
            judge_id=self.name,
            criteria=self.criteria,
            score=0.0,
            confidence=0.0,
            passed=False,
            reasoning="max_retries_exceeded"
        )


class Tribunal:
    """3-judge AI tribunal for consensus evaluation."""
    
    def __init__(self, judges: List[Judge]):
        self.judges = judges
        self.total_timeout = 25.0  # Total budget for all judges
    
    @staticmethod
    def _consensus(vals: List[float]) -> float:
        """
        Calculate consensus score.
        
        For 3 judges: Use median (outlier resistant)
        For 5+ judges: Use 20% trimmed mean
        """
        if not vals:
            return 0.0
        
        n = len(vals)
        
        if n == 3:
            # Use median for 3 judges (more robust)
            return statistics.median(vals)
        elif n >= 5:
            # Use trimmed mean for 5+ judges
            k = int(n * 0.2)
            arr = sorted(vals)
            sel = arr[k:n-k] if k > 0 else arr
            return sum(sel) / len(sel) if sel else 0.0
        else:
            # Fallback to median
            return statistics.median(vals)
    
    @staticmethod
    def _disagreement(passes: List[bool]) -> float:
        """
        Calculate disagreement metric.
        
        0.0 = all judges agree
        0.5 = maximum disagreement (50/50 split)
        1.0 = impossible (reserved)
        
        Uses formula: 1 - (p^2 + (1-p)^2) where p = pass rate
        """
        if not passes:
            return 1.0
        a = sum(passes) / len(passes)
        return 1 - (a * a + (1 - a) * (1 - a))
    
    async def evaluate(
        self,
        task_goal: str,
        current_state: str,
        llm_response: Dict[str, Any],
        threshold: float = 0.8
    ) -> Verdict:
        """
        Evaluate LLM response with 3-judge tribunal.
        
        Production features:
        - Concurrent execution with total timeout
        - Fail-closed on parse errors
        - Full telemetry
        
        Returns consensus verdict with trace ID.
        """
        trace_id = str(uuid.uuid4())
        start_time = time.time()
        
        logger.info(f"[{trace_id}] Starting tribunal evaluation with {len(self.judges)} judges")
        
        try:
            # Run judges CONCURRENTLY with total timeout
            evals = await asyncio.wait_for(
                asyncio.gather(*[
                    j.evaluate(task_goal, current_state, llm_response)
                    for j in self.judges
                ], return_exceptions=True),
                timeout=self.total_timeout
            )
            
            # Check for failures
            failed_judges = []
            successful_evals = []
            
            for i, result in enumerate(evals):
                if isinstance(result, Exception):
                    failed_judges.append(f"{self.judges[i].name}: {str(result)}")
                elif "parse_error" in result.reasoning or "max_retries" in result.reasoning:
                    failed_judges.append(f"{result.judge_id}: {result.reasoning}")
                else:
                    successful_evals.append(result)
            
            # FAIL-CLOSED: If any judge failed, mark as indeterminate
            if failed_judges:
                latency = (time.time() - start_time) * 1000
                logger.error(f"[{trace_id}] Judge failures: {failed_judges}")
                
                return Verdict(
                    passed=False,
                    consensus_score=0.0,
                    consensus_confidence=0.0,
                    unanimous=False,
                    disagreement=1.0,
                    evaluations=successful_evals,
                    reasoning=f"INDETERMINATE: Judge failures - {'; '.join(failed_judges)}",
                    trace_id=trace_id,
                    indeterminate=True,
                    models_used=[j.model_name for j in self.judges],
                    latency_ms=latency,
                    estimated_cost=0.0
                )
            
            scores = [e.score for e in successful_evals]
            confs = [e.confidence for e in successful_evals]
            passes = [e.passed for e in successful_evals]
            
            # Use MEDIAN for 3 judges (outlier resistant)
            cscore = self._consensus(scores)
            cconf = self._consensus(confs)
            
            unanimous = all(passes)
            disagree = self._disagreement(passes)
            
            # High disagreement warning - ALERT POLICY
            if disagree > 0.3:
                logger.warning(
                    f"[{trace_id}] HIGH DISAGREEMENT: {disagree:.2f} - "
                    f"ALERT: Review required. Trace: {trace_id}"
                )
            
            # 2-OF-3 PASS RULE: Require majority agreement
            two_of_three = sum(passes) >= 2
            
            # Pass requires: score threshold + confidence threshold + majority
            passed = (cscore >= threshold and cconf >= threshold and two_of_three)
            
            reasoning = "\n".join([
                f"{e.criteria}: {'PASS' if e.passed else 'FAIL'} "
                f"s={e.score:.2f} c={e.confidence:.2f} {e.reasoning[:80]}..."
                for e in successful_evals
            ])
            
            # Telemetry
            latency = (time.time() - start_time) * 1000
            models_used = [j.model_name for j in self.judges]
            
            # Rough cost estimation (input ~200 tokens, output ~100 tokens per judge)
            cost_per_judge = {
                "gpt-4o": 0.0015,  # $2.50/1M input, $10/1M output
                "gpt-4o-mini": 0.0001,  # $0.15/1M input, $0.60/1M output
                "gpt-4-turbo": 0.002,  # $10/1M input, $30/1M output
            }
            estimated_cost = sum(cost_per_judge.get(m, 0.001) for m in models_used)
            
            logger.info(
                f"[{trace_id}] Verdict: {passed}, Score: {cscore:.2f}, "
                f"Disagreement: {disagree:.2f}, Latency: {latency:.0f}ms, Cost: ${estimated_cost:.4f}"
            )
            
            return Verdict(
                passed=passed,
                consensus_score=cscore,
                consensus_confidence=cconf,
                unanimous=unanimous,
                disagreement=disagree,
                evaluations=successful_evals,
                reasoning=reasoning,
                trace_id=trace_id,
                indeterminate=False,
                models_used=models_used,
                latency_ms=latency,
                estimated_cost=estimated_cost
            )
            
        except asyncio.TimeoutError:
            latency = (time.time() - start_time) * 1000
            logger.error(f"[{trace_id}] Tribunal timeout after {latency:.0f}ms")
            
            return Verdict(
                passed=False,
                consensus_score=0.0,
                consensus_confidence=0.0,
                unanimous=False,
                disagreement=1.0,
                evaluations=[],
                reasoning=f"INDETERMINATE: Tribunal timeout after {self.total_timeout}s",
                trace_id=trace_id,
                indeterminate=True,
                models_used=[j.model_name for j in self.judges],
                latency_ms=latency,
                estimated_cost=0.0
            )


# ============================================================================
# Public API
# ============================================================================

def evaluate_with_rubric(response: Dict[str, Any], rtype: str) -> RubricResult:
    """
    Evaluate response with rubric validation.
    
    Args:
        response: LLM response dict
        rtype: "goal_proximity", "orchestrator_decision", or "prompt_improvement"
    
    Returns:
        RubricResult with validation details
    """
    if rtype == "goal_proximity":
        return validate_goal_proximity(response)
    if rtype == "orchestrator_decision":
        return validate_orchestrator_decision(response)
    if rtype == "prompt_improvement":
        return validate_prompt_improvement(response)
    raise ValueError(f"unknown rtype: {rtype}")


async def evaluate_with_tribunal(
    response: Dict[str, Any],
    context: Dict[str, str],
    openai_client: Any,
    threshold: float = 0.8
) -> Verdict:
    """
    Evaluate response with AI tribunal.
    
    Production configuration:
    - 3 diverse judges using different models for independence
    - Judge 1: gpt-4o (logical consistency)
    - Judge 2: gpt-4o-mini (completeness)
    - Judge 3: gpt-4-turbo (accuracy)
    - Concurrent execution with per-judge and total timeouts
    - Median consensus (outlier resistant for 3 judges)
    
    Args:
        response: LLM response dict
        context: {"task_goal": "...", "current_state": "..."}
        openai_client: AsyncOpenAI client
        threshold: Pass threshold (default 0.8)
    
    Returns:
        Verdict with consensus, telemetry, and trace ID
    """
    # DIVERSE JUDGES: Different models for independence
    # Using available models: gpt-4o (frontier), gpt-4o-mini (efficient), gpt-4-turbo (legacy)
    judges = [
        Judge("judge_1", openai_client, "gpt-4o", "logical_consistency", seed=42, timeout_seconds=8.0),
        Judge("judge_2", openai_client, "gpt-4o-mini", "completeness", seed=43, timeout_seconds=8.0),
        Judge("judge_3", openai_client, "gpt-4-turbo", "accuracy", seed=44, timeout_seconds=8.0),
    ]
    
    tribunal = Tribunal(judges)
    
    return await tribunal.evaluate(
        task_goal=context.get("task_goal", ""),
        current_state=context.get("current_state", ""),
        llm_response=response,
        threshold=threshold
    )
