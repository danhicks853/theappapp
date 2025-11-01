# Decision 83: Agent Execution Loop Architecture

**Status**: ✅ RESOLVED  
**Date Resolved**: Nov 1, 2025  
**Priority**: P0 - BLOCKING  
**Depends On**: Decision 67 (Orchestrator), Decision 71 (TAS), Decision 74 (Loop Detection)

---

## Context

During architecture review, a critical gap was identified: agents lack specified iterative execution loops. Without this, agents risk becoming "fake loops" that complete tasks in single LLM calls without step-by-step iteration, retry logic, validation, progress tracking, or state persistence.

This creates brittleness, poor observability, and inability to recover from failures.

**Reference**: External feedback on "fake agent loops" vs real iterative execution patterns

---

## Decision

**All agents MUST use iterative goal-based execution loops with full state tracking, validation, retry logic, and loop detection.**

### Selected Architecture

| Component | Decision | Rationale |
|-----------|----------|-----------|
| **Execution Pattern** | Goal-Based Termination Loop | Stops when goals met, not arbitrary count |
| **State Management** | Full Audit State | Complete observability for debugging/learning |
| **Step Structure** | Full Step with Reasoning | Plan → Execute → Validate with chain-of-thought |
| **Retry Logic** | Intelligent Retry with Replanning | Different approach each retry, not identical attempts |
| **Termination Criteria** | Multi-Criteria with Confidence Gating | Goals met, max steps, loops, timeout, cost, confidence |
| **Loop Detection** | Dual Monitoring | Agent-side + external monitoring |
| **Progress Validation** | Hybrid: Tests → Artifacts → LLM | Priority order, fallback to LLM |
| **Tool Execution** | Via Orchestrator + TAS | Agent → Orch → TAS → Audit → Result |

---

## Core Principles

1. **NO single-shot prompt→response patterns** - Always iterative
2. **Explicit termination criteria** - Not just "model said done"
3. **Per-step validation and retry** - Verify progress continuously
4. **Full audit trail** - Complete observability
5. **Orchestrator confidence gating** - Human escalation on low confidence
6. **TAS integration** - All tools through permission layer

---

## Architecture Overview

### Execution Loop Pattern

```python
async def run_task(self, task: Task) -> TaskResult:
    state = self._initialize_state(task)
    
    while not self._should_terminate(state):
        # 1. Plan next action
        action = await self._plan_next_step(state)
        
        # 2. Execute with retry
        result = await self._execute_step_with_retry(action, state)
        
        # 3. Validate result
        validation = await self._validate_step(result, state)
        
        # 4. Update state
        state = self._update_state(state, result, validation)
        
        # 5. Check for loops (3 identical failures)
        if self.loop_detector.is_looping(state):
            return await self._escalate_loop(state)
        
        # 6. Confidence check (every 5 steps / on uncertainty / on request)
        if self._should_request_confidence_check(state):
            confidence = await self._request_confidence_evaluation(state)
            if confidence < 0.5:
                return await self._escalate_low_confidence(state, confidence)
        
        # 7. Log progress
        await self._log_step_progress(state)
        
        state.current_step += 1
    
    return self._finalize_result(state)
```

**Key Features**:
- Real iteration (not fake single-shot)
- Each step: plan → execute → validate
- Multiple exit conditions
- Confidence checks at intervals
- Complete state tracking

---

## State Management

### TaskState Structure

```python
@dataclass
class TaskState:
    # Identifiers
    task_id: str
    agent_id: str
    project_id: str
    
    # Task definition
    goal: str
    acceptance_criteria: List[str]
    constraints: Dict[str, Any]
    
    # Execution tracking
    current_step: int = 0
    max_steps: int = 20
    started_at: datetime = field(default_factory=datetime.now)
    
    # Full audit trail
    steps_history: List[Step] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    
    # Failure tracking (loop detection)
    failure_count: int = 0
    last_errors: List[str] = field(default_factory=list)
    consecutive_failures: int = 0
    
    # Progress metrics
    progress_score: float = 0.0
    progress_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Resource tracking
    token_usage: List[int] = field(default_factory=list)
    llm_calls: List[LLMCall] = field(default_factory=list)
    tool_executions: List[ToolExecution] = field(default_factory=list)
    total_cost_usd: float = 0.0
    
    # Decision transparency
    decision_reasoning: List[str] = field(default_factory=list)
    
    # Termination flags
    escalation_triggered: bool = False
    escalation_reason: Optional[str] = None
    timeout_reached: bool = False
    resource_limit_hit: bool = False
    
    # Orchestrator interaction
    last_confidence_check_step: int = 0
    last_confidence_score: Optional[float] = None
```

**Purpose**: Complete observability for debugging, recovery, and learning.

---

## Step Structure

### Step Record

```python
@dataclass
class Step:
    step_number: int
    timestamp: datetime
    
    # Planning
    reasoning: str  # Chain-of-thought
    planned_action: Action
    
    # Execution
    execution_result: Result
    attempt_number: int  # Retry attempt
    
    # Validation
    validation: ValidationResult
    acceptance_progress: float  # 0.0-1.0
    
    # Outcome
    success: bool
    error_if_failed: Optional[str] = None
    
    # Resources
    tokens_used: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0
```

---

## Termination Criteria

### Multiple Exit Conditions

```python
def _should_terminate(self, state: TaskState) -> bool:
    return (
        self._acceptance_criteria_met(state) or  # ✅ Goals achieved
        state.current_step >= state.max_steps or  # ⏱️ Budget exhausted
        self.loop_detector.is_looping(state) or  # 🔄 Loop detected
        state.escalation_triggered or  # 🚨 Human escalation
        state.timeout_reached or  # ⏰ Timeout
        state.resource_limit_hit  # 💰 Cost limit
    )
```

### Confidence Gating

**When to Check**:
- Every 5 steps
- When agent reports uncertainty
- On explicit request

**Threshold**: `confidence < 0.5` triggers human gate

```python
def _should_request_confidence_check(self, state: TaskState) -> bool:
    steps_since_last = state.current_step - state.last_confidence_check_step
    return (
        steps_since_last >= 5 or
        self._agent_is_uncertain(state) or
        state.metadata.get("request_confidence_check", False)
    )

async def _request_confidence_evaluation(self, state: TaskState) -> float:
    confidence_request = {
        "agent_id": self.agent_id,
        "task_id": state.task_id,
        "current_step": state.current_step,
        "goal": state.goal,
        "progress_score": state.progress_score,
        "steps_history": state.steps_history[-5:],
        "artifacts": state.artifacts
    }
    
    return await self.orchestrator.evaluate_confidence(confidence_request)
```

**Escalation**:
```python
if confidence < 0.5:
    gate_id = await self.orchestrator.create_gate(
        reason=f"Low confidence: {confidence:.2f}",
        context={"task_id": state.task_id, ...},
        agent_id=self.agent_id
    )
```

---

## Retry Logic

### Intelligent Retry with Replanning

**Key**: Each retry uses a DIFFERENT approach.

```python
async def _execute_step_with_retry(
    self, 
    action: Action, 
    state: TaskState,
    max_retries: int = 3
) -> Result:
    original_action = action
    
    for attempt in range(1, max_retries + 1):
        result = await self._execute_via_orchestrator(action, state)
        
        if result.success:
            return result
        
        if attempt < max_retries:
            await asyncio.sleep(2 ** attempt)  # Backoff
            
            # Replan with DIFFERENT approach
            action = await self._replan_after_failure(
                original_action=original_action,
                error=result.error,
                attempt=attempt,
                state=state
            )
    
    return Result(success=False, error=f"Failed after {max_retries} attempts")
```

**Prevents**: Repeating identical operations expecting different results.

---

## Loop Detection

### Dual Monitoring

**Agent-Side** (fast, immediate):
```python
def is_looping(self, state: TaskState) -> bool:
    if len(state.last_errors) < 3:
        return False
    
    recent_errors = state.last_errors[-3:]
    
    # 3 consecutive identical errors = loop
    return len(set(recent_errors)) == 1 and len(recent_errors) == 3
```

**External Monitoring** (orchestrator/service):
- Semantic similarity in actions
- Progress stall detection
- Backup detection layer

---

## Progress Validation

### Hybrid Approach (Priority Order)

```python
async def _evaluate_progress(self, state: TaskState) -> ProgressEvaluation:
    # 1. Test-based metrics (highest priority)
    if self._has_tests(state):
        return self._evaluate_test_progress(state)
    
    # 2. Artifact-based metrics
    if self._has_artifacts(state):
        return self._evaluate_artifact_progress(state)
    
    # 3. LLM evaluation (fallback)
    return await self._llm_evaluate_progress(state)
```

**Test Metrics**:
- Coverage increase
- Passing tests increase
- Failure rate decrease

**Artifact Metrics**:
- Files created
- Code written
- Dependencies added

**LLM Evaluation** (fallback for subjective tasks):
- Design decisions
- Architecture reviews
- Quality assessments

---

## Tool Execution

### Via Orchestrator + TAS

**Flow**: Agent → Orchestrator → TAS → Tool → TAS Audit → Orchestrator → Agent

```python
async def _execute_via_orchestrator(
    self, 
    action: Action, 
    state: TaskState
) -> Result:
    tool_request = {
        "request_id": str(uuid.uuid4()),
        "agent_id": self.agent_id,
        "project_id": state.project_id,
        "tool_name": action.tool_name,
        "operation": action.operation,
        "parameters": action.parameters
    }
    
    # Orchestrator routes to TAS
    result = await self.orchestrator.execute_tool(tool_request)
    
    if result["status"] == "denied":
        return self._handle_permission_denial(result, state)
    
    return Result(
        success=result["result"].get("success", False),
        output=result["result"].get("data"),
        metadata=result
    )
```

**Permission Denial Handling**:
1. Find alternative allowed tool
2. Escalate to orchestrator for specialist help
3. Mark as blocking and escalate to human

---

## Implementation Requirements

### Base Agent Class

All agents MUST inherit from `BaseAgent`:

```python
class BaseAgent(ABC):
    def __init__(self, agent_id, agent_type, orchestrator, llm_client):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.orchestrator = orchestrator
        self.llm_client = llm_client
        self.loop_detector = LoopDetector()
    
    @abstractmethod
    async def run_task(self, task: Task) -> TaskResult:
        """Execute task with iterative loop. REQUIRED."""
        pass
    
    # Provided methods:
    # - _plan_next_step()
    # - _execute_step_with_retry()
    # - _validate_step()
    # - _update_state()
    # - _should_terminate()
    # - _execute_via_orchestrator()
    # - _request_confidence_evaluation()
```

### Orchestrator Extensions

```python
class Orchestrator:
    async def execute_tool(self, tool_request: dict) -> dict:
        """Forward to TAS."""
        return await self.tas_client.execute_tool(tool_request)
    
    async def evaluate_confidence(self, confidence_request: dict) -> float:
        """Evaluate agent confidence using LLM. Returns 0.0-1.0."""
        prompt = self._build_confidence_prompt(confidence_request)
        response = await self.llm_client.complete(prompt)
        return self._parse_confidence_score(response)
    
    async def create_gate(self, reason: str, context: dict, agent_id: str) -> str:
        """Create human approval gate. Returns gate_id."""
        pass
```

---

## Testing Requirements

### Unit Tests
- Loop detection logic (3 identical errors)
- Termination criteria (all 6 conditions)
- Retry with replanning (verifies different approaches)
- State management (history tracking)
- Confidence evaluation triggers

### Integration Tests
- Full task execution with iterations
- TAS permission denial handling
- Orchestrator confidence gating
- Loop detection → escalation flow
- Progress validation (all 3 methods)

### E2E Tests
- Complete task with multiple steps
- Recovery from failures with retry
- Loop detection → human gate
- Low confidence → human gate
- Tool permission denied → adaptation

---

## Database Schema

### Agent Execution History

```sql
CREATE TABLE agent_execution_history (
    id UUID PRIMARY KEY,
    agent_id VARCHAR(100) NOT NULL,
    task_id VARCHAR(100) NOT NULL,
    project_id VARCHAR(100),
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    total_steps INT,
    final_status VARCHAR(50),  -- success, failed, escalated
    escalation_reason TEXT,
    total_cost_usd DECIMAL(10, 4),
    total_tokens INT,
    state_snapshot JSONB  -- Final TaskState
);

CREATE TABLE agent_execution_steps (
    id UUID PRIMARY KEY,
    execution_id UUID REFERENCES agent_execution_history(id),
    step_number INT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    reasoning TEXT,
    action JSONB,
    result JSONB,
    validation JSONB,
    success BOOLEAN,
    tokens_used INT,
    cost_usd DECIMAL(10, 4)
);
```

---

## Implications

### Enables
- ✅ Reliable agent task execution
- ✅ Recovery from failures
- ✅ Complete observability
- ✅ Loop detection and prevention
- ✅ Human oversight via confidence gating
- ✅ Learning from execution patterns

### Requires
- Base agent implementation
- Orchestrator confidence evaluation
- TAS integration in all agents
- Loop detection service
- Database schema for execution history
- Comprehensive testing framework

### Blocks
- **All agent implementations** until BaseAgent complete
- Cannot implement Phase 1.2+ without this architecture

---

## Tasks Created

Added to development tracker:

### 1.2.0: Agent Execution Loop (NEW - P0)
- [ ] Implement BaseAgent class with execution loop
- [ ] Implement TaskState and Step data models
- [ ] Implement LoopDetector class
- [ ] Add orchestrator.execute_tool() method
- [ ] Add orchestrator.evaluate_confidence() method
- [ ] Add orchestrator.create_gate() method (if not exists)
- [ ] Create agent execution database tables
- [ ] Write unit tests for base agent
- [ ] Write integration tests for execution loop
- [ ] Document execution loop architecture

**This task MUST complete before any agent implementations (1.2.1-1.2.10).**

---

## Related Decisions

- **Decision 67**: Orchestrator LLM Integration - Confidence evaluation
- **Decision 71**: Tool Access Service - Permission enforcement
- **Decision 74**: Loop Detection Algorithm - Exact match detection
- **Decision 8**: Tool Access Matrix - What tools agents can use

---

## Documentation

**Decision Document**: `docs/architecture/decision-83-agent-execution-loop-architecture.md` (this file)  
**Implementation Guide**: To be created in `docs/implementation/base-agent-guide.md`  
**Code Examples**: To be created in `docs/examples/agent-execution-loop.md`

---

*Decision finalized: Nov 1, 2025*  
*Implementation priority: P0 - BLOCKING all agent work*
