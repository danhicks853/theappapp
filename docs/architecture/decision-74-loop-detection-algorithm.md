# Decision 74: Loop Detection Algorithm

**Status**: ✅ COMPLETE  
**Date Resolved**: November 1, 2025  
**Priority**: P0 - BLOCKING  
**Depends On**: Decision 32 (failure handling), Decision 36 (debugging), Decision 67 (orchestrator LLM)

---

## Context

The system needs to detect when agents are stuck in unproductive loops and trigger human intervention gates. Phase 3 Decision 32 specifies "After 3rd unresolved loop → gate", but the algorithm for detecting loops versus genuine progress was undefined.

**Key Requirements**:
- Distinguish between identical failures (true loops) and progressive attempts
- Recognize when agents are making progress vs. spinning wheels
- Handle edge cases like intermittent failures and multi-agent collaboration loops
- Integrate with orchestrator's decision-making and gate system

---

## Decision

### 1. Identical Failure Detection

**Approach**: **Tiered Detection System**

#### Primary Detection: Exact Error Message Matching
- Fast, definitive loop detection
- String comparison of error messages
- Immediate loop counter increment on exact match

#### Secondary Tracking: Key Error Indicators
- Extract and store error metadata:
  - Error type (syntax, runtime, logic, dependency, etc.)
  - Error location (file, line, function)
  - Error context (stack trace hash, affected components)
- Used for pattern analysis and RAG learning
- Provides context for orchestrator reasoning

**Implementation**:
```python
class FailureSignature:
    exact_message: str           # Full error message
    error_type: ErrorType        # Classified error category
    location: str                # File:line or component
    context_hash: str            # Hash of stack trace/context
    timestamp: datetime
    agent_id: str
    task_id: str
```

**Loop Detection Logic**:
1. Extract failure signature from agent output
2. Check exact message match against recent failures (same task)
3. If exact match → increment loop counter
4. Store key indicators regardless for orchestrator analysis

---

### 2. Progress Definition

**Approach**: **Test-Driven Progress Metrics with Orchestrator Oversight**

#### Primary Progress Indicators (When Tests Exist)
- **Improved test coverage**: Coverage % increases
- **Reduced failure rate**: Fewer tests failing
- **Quantifiable metrics**: Can measure objectively

#### Fallback Progress Indicators (No Tests)
- **Task completion markers**: Files created, dependencies installed, code written
- **Subtask completion**: Partial progress on decomposed tasks
- **Orchestrator evaluation**: LLM-based goal proximity assessment

#### No Tests = Problem Detection
- If agent is working without tests and showing no measurable progress
- Orchestrator should detect this as an issue
- May trigger earlier intervention or test creation requirement

**Progress Evaluation Algorithm**:
```
IF tests exist:
    progress = (coverage_improved OR failure_rate_decreased)
ELSE IF task_completion_indicators_present:
    progress = (files_created OR dependencies_added OR code_written)
ELSE:
    orchestrator_evaluates_goal_proximity()
    IF no_progress_detected:
        flag_for_intervention()
```

**Non-Loop Progress Scenarios**:
- Initial project setup (creating test infrastructure)
- Documentation tasks (no code/tests)
- Configuration tasks (environment setup)
- Refactoring (tests unchanged but code improved)

For these, orchestrator uses LLM reasoning to evaluate goal proximity.

---

### 3. Loop State Tracking

**Approach**: **In-Memory Orchestrator State**

#### Storage Strategy
- **Primary**: In-memory data structures in orchestrator process
- **No database persistence**: Loop state is ephemeral
- **Rationale**: Loops break on restart anyway; 6 loops isn't significantly worse than 3

#### State Structure
```python
class LoopTracker:
    task_id: str
    agent_id: str
    failure_history: List[FailureSignature]  # Recent failures
    loop_count: int
    last_failure_time: datetime
    progress_metrics: ProgressSnapshot
    collaboration_chain: List[CollaborationEvent]  # For collab loops
```

#### Memory Management
- Keep last N failures per task (e.g., N=10)
- Clear state on task completion or human intervention
- Garbage collect old task states (e.g., >24 hours inactive)

**Trade-offs Accepted**:
- ✅ Fast access for frequent loop checks
- ✅ Simple implementation, no database overhead
- ✅ Automatic cleanup on restart
- ❌ State lost on orchestrator restart (acceptable - fresh start)
- ❌ No historical loop analysis across restarts (can use logs if needed)

---

### 4. Loop Counter Triggers

**Approach**: **Same Agent-Task-Error Combination**

#### Trigger Conditions
Loop counter increments when:
1. **Same task**: Task ID matches
2. **Same agent**: Agent ID matches (or collaboration chain matches)
3. **Same/similar error**: Exact message match OR semantic similarity for collaboration loops

#### Collaboration Loop Detection
**Definition**: One collaboration loop = Agent A → Orchestrator → Agent B → Orchestrator → Agent A (with same/similar request)

**Example**:
```
Loop 1:
  - Agent A (Backend Dev) requests help from Agent B (Security Expert)
  - Orchestrator routes request
  - Agent B responds
  - Orchestrator returns response to Agent A
  - Agent A makes same/similar request again
  → Loop count = 1

Loop 2:
  - Same sequence repeats
  → Loop count = 2

Loop 3:
  - Same sequence repeats
  → Loop count = 3 → GATE TRIGGERED
```

**Collaboration Request Similarity**:
- Use semantic similarity (embeddings) to detect "same or similar request"
- Threshold: >0.85 cosine similarity = same request
- Prevents agents from slightly rewording requests to bypass detection

#### Time Window Considerations
- No explicit time window for loop counting
- Orchestrator's LLM reasoning considers time between attempts
- Very long gaps (e.g., >24 hours) may indicate external factors changed

---

### 5. Edge Case Handling

**Approach**: **Orchestrator LLM-Based Reasoning**

#### Orchestrator Evaluation Capability
The orchestrator uses LLM reasoning to evaluate:
- **Goal proximity**: "Is the agent moving toward or away from the goal?"
- **Regressive progress**: "Is attempt 3 worse than attempt 1?"
- **External factors**: "Is this failure due to external dependencies?"
- **Collaboration effectiveness**: "Are agents achieving anything through collaboration?"

#### Edge Case Scenarios

##### Intermittent Failures (External API Down)
**Detection**:
- Different error messages across attempts
- Error type: dependency/network failure
- Orchestrator recognizes external cause

**Handling**:
- May not count as loop if error varies
- Orchestrator can suggest retry with backoff
- May escalate if external issue persists

##### Progressive Degradation (Getting Worse)
**Detection**:
- Test failure rate increasing
- More errors appearing
- Orchestrator LLM detects "moving away from goal"

**Handling**:
- Counts as loop even if errors differ
- Orchestrator may trigger gate earlier
- Suggests rollback or different approach

##### External Dependency Failures (Not Agent's Fault)
**Detection**:
- Error type: dependency, network, authentication
- Consistent external error messages
- No code changes causing issue

**Handling**:
- Orchestrator distinguishes from agent failure
- May pause task until dependency resolves
- Doesn't count against agent's loop counter
- May escalate to human for dependency resolution

##### Multi-Agent Collaboration Loops
**Detection**:
- Track collaboration chains: A → B → A
- Semantic similarity of requests
- No progress despite multiple collaborations

**Handling**:
- Same 3-loop threshold as regular loops
- Orchestrator detects "agents have looped between collaboration requests and achieved nothing"
- Gate triggered after 3 unproductive collaboration cycles

#### Orchestrator Decision Process
```
FOR each failure:
    1. Extract failure signature
    2. Check for exact error match (definite loop)
    3. Evaluate goal proximity (LLM reasoning)
    4. Classify failure type (agent vs. external)
    5. Assess progress indicators
    6. Determine if loop counter should increment
    7. Decide on intervention (continue, escalate, gate)
```

---

### 6. Loop Counter Reset Conditions

**Approach**: **Reset on Success or Human Intervention**

#### Reset Triggers

##### 1. Successful Task Completion
- Task marked as complete
- All acceptance criteria met
- Loop counter reset to 0 for next task
- **Rationale**: Success proves agent can make progress; clean slate for new task

##### 2. Human Intervention
- Human approves gate and provides guidance
- Human manually intervenes in project
- Loop counter reset to 0
- **Rationale**: Human input changes context, invalidates old loop count

#### NOT Reset On

##### Agent Change (Without Human Intervention)
- Orchestrator autonomously assigns different agent
- Loop counter **persists** across agent change
- **Rationale**: Prevents gaming system by rotating agents
- **Exception**: If human approves agent change at gate, counter resets (human intervention)

**Example Scenario**:
```
Agent A fails 3 times → Gate triggered
Human reviews and approves continuing with Agent B
→ Loop counter resets (human intervention)
Agent B starts fresh

vs.

Agent A fails 2 times
Orchestrator autonomously switches to Agent B
→ Loop counter stays at 2 (no human intervention)
Agent B fails once
→ Loop counter = 3 → Gate triggered
```

#### Reset Scope
- Loop counter is per-task
- New task = new counter (even if same agent)
- Subtasks inherit parent task's counter (no reset on subtask boundaries)

---

## Implementation Details

### Loop Detection Service

```python
class LoopDetectionService:
    def __init__(self, orchestrator_llm: OrchestratorLLM):
        self.loop_trackers: Dict[str, LoopTracker] = {}
        self.orchestrator_llm = orchestrator_llm
        
    def record_failure(
        self, 
        task_id: str, 
        agent_id: str, 
        error_message: str,
        context: Dict
    ) -> LoopDetectionResult:
        """Record a failure and check for loops"""
        
        # Get or create tracker
        tracker = self.get_tracker(task_id)
        
        # Extract failure signature
        signature = self.extract_signature(
            error_message, 
            context, 
            agent_id, 
            task_id
        )
        
        # Check for exact match (definite loop)
        if self.has_exact_match(tracker, signature):
            tracker.loop_count += 1
            return LoopDetectionResult(
                is_loop=True,
                loop_count=tracker.loop_count,
                should_gate=(tracker.loop_count >= 3),
                reason="Exact error message match"
            )
        
        # Evaluate with orchestrator LLM
        evaluation = self.orchestrator_llm.evaluate_progress(
            task_goal=context['task_goal'],
            failure_history=tracker.failure_history,
            current_failure=signature,
            progress_metrics=tracker.progress_metrics
        )
        
        # Determine if this counts as a loop
        if evaluation.is_regressive or evaluation.no_progress:
            tracker.loop_count += 1
            return LoopDetectionResult(
                is_loop=True,
                loop_count=tracker.loop_count,
                should_gate=(tracker.loop_count >= 3),
                reason=evaluation.reasoning
            )
        
        # Not a loop - record and continue
        tracker.failure_history.append(signature)
        return LoopDetectionResult(
            is_loop=False,
            loop_count=tracker.loop_count,
            should_gate=False,
            reason="Progress detected"
        )
    
    def record_collaboration_loop(
        self,
        task_id: str,
        agent_a_id: str,
        agent_b_id: str,
        request: str
    ) -> LoopDetectionResult:
        """Check for collaboration loops"""
        
        tracker = self.get_tracker(task_id)
        
        # Check for similar collaboration requests
        similar_collab = self.find_similar_collaboration(
            tracker.collaboration_chain,
            agent_a_id,
            agent_b_id,
            request
        )
        
        if similar_collab:
            tracker.loop_count += 1
            return LoopDetectionResult(
                is_loop=True,
                loop_count=tracker.loop_count,
                should_gate=(tracker.loop_count >= 3),
                reason="Repeated collaboration request"
            )
        
        # Record collaboration
        tracker.collaboration_chain.append(
            CollaborationEvent(
                from_agent=agent_a_id,
                to_agent=agent_b_id,
                request=request,
                timestamp=datetime.now()
            )
        )
        
        return LoopDetectionResult(is_loop=False, loop_count=tracker.loop_count)
    
    def reset_counter(self, task_id: str, reason: str):
        """Reset loop counter for a task"""
        if task_id in self.loop_trackers:
            self.loop_trackers[task_id].loop_count = 0
            self.loop_trackers[task_id].failure_history.clear()
            self.loop_trackers[task_id].collaboration_chain.clear()
            logger.info(f"Loop counter reset for task {task_id}: {reason}")
    
    def extract_signature(self, error_message: str, context: Dict, 
                         agent_id: str, task_id: str) -> FailureSignature:
        """Extract failure signature from error"""
        return FailureSignature(
            exact_message=error_message,
            error_type=self.classify_error(error_message, context),
            location=context.get('file_location', 'unknown'),
            context_hash=self.hash_context(context.get('stack_trace', '')),
            timestamp=datetime.now(),
            agent_id=agent_id,
            task_id=task_id
        )
    
    def has_exact_match(self, tracker: LoopTracker, 
                       signature: FailureSignature) -> bool:
        """Check if exact error message has occurred before"""
        for prev_failure in tracker.failure_history:
            if prev_failure.exact_message == signature.exact_message:
                return True
        return False
    
    def find_similar_collaboration(self, chain: List[CollaborationEvent],
                                  agent_a: str, agent_b: str, 
                                  request: str) -> Optional[CollaborationEvent]:
        """Find similar collaboration request in history"""
        for event in chain:
            if (event.from_agent == agent_a and 
                event.to_agent == agent_b):
                similarity = self.compute_similarity(event.request, request)
                if similarity > 0.85:  # Threshold for "same request"
                    return event
        return None
```

### Progress Evaluation

```python
class ProgressEvaluator:
    def evaluate_progress(
        self,
        task_goal: str,
        failure_history: List[FailureSignature],
        current_failure: FailureSignature,
        progress_metrics: ProgressSnapshot
    ) -> ProgressEvaluation:
        """Evaluate if agent is making progress"""
        
        # Check test metrics first
        if progress_metrics.has_tests:
            if (progress_metrics.coverage_improved or 
                progress_metrics.failure_rate_decreased):
                return ProgressEvaluation(
                    is_regressive=False,
                    no_progress=False,
                    reasoning="Test metrics show improvement"
                )
        
        # Check task completion indicators
        if progress_metrics.has_completion_indicators():
            return ProgressEvaluation(
                is_regressive=False,
                no_progress=False,
                reasoning="Task completion indicators present"
            )
        
        # Fall back to LLM reasoning
        llm_evaluation = self.orchestrator_llm.evaluate_goal_proximity(
            goal=task_goal,
            attempts=[f.to_dict() for f in failure_history],
            current_attempt=current_failure.to_dict()
        )
        
        return llm_evaluation
```

### Orchestrator Integration

```python
class Orchestrator:
    def handle_agent_failure(
        self,
        task_id: str,
        agent_id: str,
        error: AgentError
    ):
        """Handle agent failure with loop detection"""
        
        # Record failure and check for loops
        result = self.loop_detector.record_failure(
            task_id=task_id,
            agent_id=agent_id,
            error_message=error.message,
            context=error.context
        )
        
        # Log the result
        self.logger.log_loop_detection(result)
        
        # Trigger gate if needed
        if result.should_gate:
            self.trigger_gate(
                task_id=task_id,
                reason=f"Loop detected after {result.loop_count} attempts",
                details=result.reason
            )
            return
        
        # Decide next action
        if result.is_loop:
            # This is a loop but not yet at threshold
            self.logger.warn(
                f"Loop {result.loop_count}/3 detected for task {task_id}"
            )
            # Consider alternative approaches
            self.consider_alternative_approach(task_id, agent_id)
        else:
            # Not a loop, continue with agent
            self.continue_task(task_id, agent_id)
    
    def handle_task_completion(self, task_id: str):
        """Reset loop counter on successful completion"""
        self.loop_detector.reset_counter(task_id, "Task completed successfully")
    
    def handle_human_intervention(self, task_id: str):
        """Reset loop counter after human intervention"""
        self.loop_detector.reset_counter(task_id, "Human intervention")
```

---

## Integration with Existing Systems

### Decision 32: Failure Handling
- Loop detection provides the mechanism for "3rd unresolved loop → gate"
- Orchestrator uses loop detection results to trigger gates
- Gate system receives loop count and reasoning for display to user

### Decision 36: Debugging
- Progress recognition vs. identical failure now clearly defined
- Debugging agent can be invoked before gate if orchestrator detects patterns
- Loop detection feeds into debugging agent's context

### Decision 67: Orchestrator LLM
- Orchestrator LLM evaluates goal proximity and progress
- Chain-of-thought reasoning for ambiguous loop scenarios
- LLM-based classification of failure types and external factors

### Decision 68: RAG System
- Loop patterns stored in RAG for learning
- Successful loop-breaking strategies captured
- Future agents can query "how to break similar loops"

### Decision 70: Agent Collaboration
- Collaboration loop detection integrated
- Same 3-loop threshold applies
- Orchestrator tracks collaboration chains

---

## Testing Strategy

### Unit Tests

#### Exact Match Detection
```python
def test_exact_error_match_increments_counter():
    detector = LoopDetectionService(mock_llm)
    
    # First failure
    result1 = detector.record_failure(
        task_id="task1",
        agent_id="agent1",
        error_message="TypeError: cannot read property 'x' of undefined",
        context={}
    )
    assert result1.loop_count == 0
    
    # Second failure - exact match
    result2 = detector.record_failure(
        task_id="task1",
        agent_id="agent1",
        error_message="TypeError: cannot read property 'x' of undefined",
        context={}
    )
    assert result2.is_loop == True
    assert result2.loop_count == 1
```

#### Progress Detection
```python
def test_improved_coverage_not_counted_as_loop():
    detector = LoopDetectionService(mock_llm)
    
    result = detector.record_failure(
        task_id="task1",
        agent_id="agent1",
        error_message="Test failed: expected 5, got 3",
        context={
            'progress_metrics': {
                'has_tests': True,
                'coverage_improved': True,
                'prev_coverage': 60,
                'current_coverage': 75
            }
        }
    )
    
    assert result.is_loop == False
    assert result.reason == "Test metrics show improvement"
```

#### Collaboration Loop Detection
```python
def test_collaboration_loop_detection():
    detector = LoopDetectionService(mock_llm)
    
    # First collaboration
    result1 = detector.record_collaboration_loop(
        task_id="task1",
        agent_a_id="backend_dev",
        agent_b_id="security_expert",
        request="Can you review this authentication code?"
    )
    assert result1.is_loop == False
    
    # Second collaboration - similar request
    result2 = detector.record_collaboration_loop(
        task_id="task1",
        agent_a_id="backend_dev",
        agent_b_id="security_expert",
        request="Can you review this auth code again?"
    )
    assert result2.is_loop == True
    assert result2.loop_count == 1
```

### Integration Tests

#### Gate Triggering
```python
def test_gate_triggered_after_three_loops():
    orchestrator = Orchestrator()
    
    # Simulate 3 identical failures
    for i in range(3):
        orchestrator.handle_agent_failure(
            task_id="task1",
            agent_id="agent1",
            error=AgentError(message="Syntax error at line 42")
        )
    
    # Verify gate was triggered
    assert orchestrator.gate_service.is_gate_active("task1")
    assert orchestrator.gate_service.get_gate_reason("task1") == \
           "Loop detected after 3 attempts"
```

#### Counter Reset
```python
def test_counter_resets_on_task_completion():
    orchestrator = Orchestrator()
    
    # Record 2 failures
    for i in range(2):
        orchestrator.handle_agent_failure(
            task_id="task1",
            agent_id="agent1",
            error=AgentError(message="Error")
        )
    
    assert orchestrator.loop_detector.get_loop_count("task1") == 2
    
    # Complete task
    orchestrator.handle_task_completion("task1")
    
    # Start new task - counter should be reset
    orchestrator.handle_agent_failure(
        task_id="task2",
        agent_id="agent1",
        error=AgentError(message="Error")
    )
    
    assert orchestrator.loop_detector.get_loop_count("task2") == 0
```

### LLM Evaluation Tests

#### Goal Proximity Evaluation
```python
def test_orchestrator_detects_regressive_progress():
    evaluator = ProgressEvaluator(orchestrator_llm)
    
    result = evaluator.evaluate_progress(
        task_goal="Implement user authentication",
        failure_history=[
            FailureSignature(exact_message="1 test failing"),
            FailureSignature(exact_message="3 tests failing"),
            FailureSignature(exact_message="5 tests failing")
        ],
        current_failure=FailureSignature(exact_message="8 tests failing"),
        progress_metrics=ProgressSnapshot(has_tests=True)
    )
    
    assert result.is_regressive == True
    assert "moving away from goal" in result.reasoning.lower()
```

### Edge Case Tests

#### External Dependency Failure
```python
def test_external_dependency_failure_not_counted():
    detector = LoopDetectionService(mock_llm)
    
    # Mock LLM to recognize external failure
    mock_llm.evaluate_progress.return_value = ProgressEvaluation(
        is_regressive=False,
        no_progress=False,
        reasoning="External API failure, not agent's fault"
    )
    
    result = detector.record_failure(
        task_id="task1",
        agent_id="agent1",
        error_message="API timeout: external service unavailable",
        context={'error_type': 'dependency'}
    )
    
    assert result.is_loop == False
```

---

## Monitoring and Observability

### Metrics to Track
- Loop detection rate per agent type
- Average loops before gate trigger
- False positive rate (loops that shouldn't have been counted)
- Gate trigger frequency
- Time between loop detection and resolution

### Logging
```python
# Loop detection event
{
    "event": "loop_detected",
    "task_id": "task_123",
    "agent_id": "backend_dev_1",
    "loop_count": 2,
    "error_signature": "TypeError: ...",
    "is_exact_match": true,
    "orchestrator_reasoning": "Exact error message match",
    "timestamp": "2025-11-01T02:00:00Z"
}

# Gate trigger event
{
    "event": "gate_triggered",
    "task_id": "task_123",
    "agent_id": "backend_dev_1",
    "loop_count": 3,
    "trigger_reason": "Loop detected after 3 attempts",
    "failure_history": [...],
    "timestamp": "2025-11-01T02:05:00Z"
}

# Counter reset event
{
    "event": "loop_counter_reset",
    "task_id": "task_123",
    "reason": "Task completed successfully",
    "previous_count": 2,
    "timestamp": "2025-11-01T02:10:00Z"
}
```

### Dashboard Metrics
- **Loop Detection Rate**: Percentage of tasks that encounter loops
- **Average Loops Per Task**: Mean loop count before resolution
- **Gate Trigger Rate**: How often gates are triggered by loops
- **Resolution Time**: Time from gate trigger to human resolution
- **Agent Loop Patterns**: Which agents encounter loops most frequently

---

## Rationale

### Why Tiered Detection (Exact + Indicators)?
- **Fast path**: Exact matches are definitive and require no LLM reasoning
- **Learning path**: Key indicators enable pattern analysis and RAG learning
- **Balance**: Performance for common cases, intelligence for edge cases

### Why Test-Driven Progress Metrics?
- **Objective measurement**: Test coverage and failure rates are quantifiable
- **Aligns with development philosophy**: Encourages test-driven development
- **Fallback available**: Orchestrator LLM can evaluate non-test scenarios
- **Early problem detection**: "No tests" itself is a red flag

### Why In-Memory State?
- **Performance**: Fast access for frequent loop checks
- **Simplicity**: No database overhead or synchronization complexity
- **Acceptable trade-off**: Loop state is ephemeral; restart = fresh start
- **Cost-effective**: Reduces database load for high-frequency operations

### Why Same Threshold for Collaboration Loops?
- **Consistency**: Users understand one rule (3 loops = gate)
- **Fairness**: Collaboration shouldn't get special treatment
- **Prevents gaming**: Can't bypass limits by using collaboration
- **Simplicity**: Easier to explain and implement

### Why Reset on Success/Human Only?
- **Prevents gaming**: Can't bypass loops by rotating agents
- **Logical boundaries**: Success proves capability; human input changes context
- **Conservative approach**: Only reset when truly justified
- **Clear rules**: Easy to understand and implement

---

## Implications

### What This Enables
- ✅ Automated loop detection without manual monitoring
- ✅ Intelligent distinction between loops and progress
- ✅ Early intervention before agents waste excessive resources
- ✅ Learning from loop patterns via RAG integration
- ✅ Consistent gate triggering across all failure scenarios

### What This Constrains
- ⚠️ Agents must provide structured error output for signature extraction
- ⚠️ Orchestrator LLM must be capable of goal proximity evaluation
- ⚠️ Test-driven development is strongly encouraged (though not required)
- ⚠️ Loop state is lost on orchestrator restart (acceptable trade-off)

### Cost/Complexity Trade-offs
- **LLM Cost**: Orchestrator evaluation adds LLM calls for ambiguous cases
  - Mitigated by: Exact match fast path handles most cases
- **Memory Usage**: In-memory state for all active tasks
  - Mitigated by: Garbage collection of old tasks, limited history per task
- **Implementation Complexity**: Multi-factor loop detection is sophisticated
  - Mitigated by: Clear algorithm, comprehensive tests, phased rollout

---

## Related Decisions

- **Decision 32**: Failure handling - provides the "3 loops → gate" rule
- **Decision 36**: Debugging - progress recognition implementation
- **Decision 67**: Orchestrator LLM - provides reasoning capability
- **Decision 68**: RAG System - stores loop patterns for learning
- **Decision 70**: Agent Collaboration - collaboration loop detection

---

## Tasks Created

### Phase 1: Core Loop Detection (Week 4)
- [ ] **Task 1.4.5**: Implement `LoopDetectionService` with exact match detection
- [ ] **Task 1.4.6**: Implement failure signature extraction and storage
- [ ] **Task 1.4.7**: Integrate loop detection with orchestrator failure handling
- [ ] **Task 1.4.8**: Implement loop counter reset logic

### Phase 3: Advanced Loop Detection (Week 8)
- [ ] **Task 3.4.5**: Implement progress evaluation with test metrics
- [ ] **Task 3.4.6**: Implement orchestrator LLM goal proximity evaluation
- [ ] **Task 3.4.7**: Implement collaboration loop detection
- [ ] **Task 3.4.8**: Add edge case handling (external failures, intermittent issues)

### Phase 6: Testing & Monitoring (Week 12)
- [ ] **Task 6.6.5**: Create loop detection unit test suite
- [ ] **Task 6.6.6**: Create loop detection integration tests
- [ ] **Task 6.6.7**: Implement loop detection monitoring and metrics
- [ ] **Task 6.6.8**: Create loop detection dashboard

---

## Documentation

- **Architecture Diagram**: `docs/diagrams/loop-detection-flow.png` (to be created)
- **Sequence Diagram**: `docs/diagrams/loop-detection-sequence.png` (to be created)
- **API Documentation**: Loop detection service API reference (to be created)
- **Runbook**: Loop detection troubleshooting guide (to be created)

---

## Open Questions

None - all questions resolved during decision process.

---

## Approval

**Approved By**: User  
**Date**: November 1, 2025  
**Notes**: Decision made through collaborative discussion. All edge cases and scenarios reviewed and approved.

---

*Last Updated: November 1, 2025*
