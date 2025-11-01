# Decision 72: LLM Testing Strategy & Implementation

**Status**: ✅ COMPLETE  
**Date Resolved**: Nov 1, 2025  
**Priority**: P0 - BLOCKING  
**Depends On**: Decision 19 (testing strategy), Decision 69 (prompt versioning)

---

## Context

Testing LLM-powered agents presents unique challenges:
- Non-deterministic outputs (same input → different valid responses)
- Semantic correctness (format correct but reasoning flawed)
- Regression detection (knowing if prompt changes degrade quality)
- Quality thresholds (what variance is acceptable)

**Scope**: Testing theappapp's agent system during development - validating agent prompts, chain-of-thought reasoning, and protocol adherence when we modify the system. This is NOT about agents testing their own work on user projects.

---

## Decision

**LLM testing will use hybrid AI+rubric evaluation on production-sampled datasets with A/B regression detection and multi-evaluator consensus.**

### Core Strategy
- **Evaluation Method**: Hybrid (AI evaluators + deterministic rubrics)
- **Golden Datasets**: Production data sampling from successful runs
- **Regression Detection**: A/B comparison (old vs new prompt versions)
- **Quality Thresholds**: 
  - Format compliance: **100%** (strict)
  - Reasoning quality: **Case-by-case** human judgment
  - Task completion: **95%+** accuracy
  - Consistency: Flexible (non-determinism expected)
- **Evaluators**: Multiple LLM evaluators (3-evaluator panel) with voting
- **Evaluation Criteria**: All of: logical consistency, completeness, accuracy, adherence to instructions, code quality, security awareness
- **Evaluator Validation**: Human spot-check sampling
- **Testing Timing**: Part of task completion testing during development (before marking AI tasks complete)
- **Failure Handling**: Alert for human review (no auto-rollback)

---

## Implementation Details

### 1. Hybrid Evaluation Method

#### Two-Stage Validation

**Stage 1: Rubric Validation** (Fast, Deterministic)
- JSON structure compliance
- Required fields present
- Syntax validation (code)
- Protocol adherence
- Security checks (no hardcoded secrets, etc.)

**Stage 2: AI Evaluation** (Expensive, Semantic)
- Runs only if rubric passes
- Multiple evaluators assess quality
- Check all criteria: logic, completeness, accuracy, instructions, code quality, security
- Consensus from panel

```python
def hybrid_evaluation(agent_output, test_case):
    # Step 1: Quick rubric checks
    rubric_result = RubricValidator().validate(agent_output)
    if not rubric_result.passed:
        return TestResult(passed=False, reason="Rubric failed")
    
    # Step 2: AI panel evaluation
    evaluations = [evaluator.evaluate(agent_output, test_case) 
                   for evaluator in get_evaluator_panel()]
    
    consensus = calculate_consensus(evaluations)
    return TestResult(passed=consensus.passed, 
                     rubric=rubric_result, 
                     ai_evals=evaluations,
                     consensus=consensus)
```

---

### 2. Golden Dataset: Production Sampling

**What Gets Collected**:
- Complete agent interactions (input → reasoning → output)
- Successful task completions (10% sample rate)
- All edge cases that were handled well
- All error scenarios with proper recovery
- Inter-agent collaboration examples

**Collection Schema**:
```sql
CREATE TABLE golden_test_cases (
    id UUID PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    agent_type VARCHAR(100) NOT NULL,
    input_context JSONB NOT NULL,
    agent_reasoning TEXT,
    agent_output JSONB NOT NULL,
    expected_behaviors JSONB NOT NULL,
    metadata JSONB,
    human_reviewed BOOLEAN DEFAULT false,
    approved BOOLEAN
);
```

**Dataset Management**:
- Automated collection flags candidates
- Weekly human review to validate quality
- Approve, reject, or annotate test cases
- Target: 50+ test cases per agent type

---

### 3. A/B Regression Detection

**Process**:
1. Run old prompt version on golden dataset
2. Run new prompt version on same golden dataset
3. Compare aggregate metrics
4. Make recommendation

```python
def run_ab_test(prompt_old, prompt_new, test_cases):
    results_old = [run_and_evaluate(prompt_old, tc) for tc in test_cases]
    results_new = [run_and_evaluate(prompt_new, tc) for tc in test_cases]
    
    comparison = {
        "pass_rate_old": calculate_pass_rate(results_old),
        "pass_rate_new": calculate_pass_rate(results_new),
        "improvements": count_improvements(results_old, results_new),
        "regressions": count_regressions(results_old, results_new)
    }
    
    return make_recommendation(comparison)
```

**Recommendation Logic**:
- Pass rate improves >5%: **APPROVE**
- Pass rate declines >5%: **REJECT**
- Has regressions: **REVIEW**
- Marginal/neutral: **REVIEW**

**Cost Optimization**:
- Quick check: 20 test cases
- Full validation: All test cases
- Run only on prompt changes (not every commit)

---

### 4. Quality Thresholds

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| **Format Compliance** | 100% | No exceptions - format errors break downstream systems |
| **Reasoning Quality** | Case-by-case | Context-dependent, requires human judgment |
| **Task Completion** | 95%+ | High bar for quality, allows edge case failures |
| **Consistency** | Flexible | Non-determinism expected and acceptable in LLMs |

---

### 5. Multiple Evaluator Panel

**Configuration**:
- **Panel Size**: 3 evaluators (odd number for tie-breaking)
- **Model**: GPT-4o for all evaluators
- **Temperature**: 0.3 (lower for consistency)
- **Roles**: General quality, Security focus, Technical accuracy

**Evaluation Criteria** (all checked by each evaluator):
1. **Logical Consistency**: Reasoning follows from premises
2. **Completeness**: All required aspects addressed
3. **Accuracy**: Facts and code are correct
4. **Adherence to Instructions**: Follows prompt guidelines
5. **Code Quality**: Syntax, best practices, readability
6. **Security Awareness**: No vulnerabilities, proper validation

**Consensus Calculation**:
- Use median score (reduces outlier impact)
- Require majority agreement for pass/fail
- Flag high disagreement (variance > 400) for human review
- Aggregate issues mentioned by 2+ evaluators

**Cost Management**:
- Full panel for A/B tests and final validation
- Single evaluator for quick checks
- Run panel only on important tests

---

### 6. Testing the Testers: Human Spot-Check

**Weekly Validation**:
- Random sample of 20 recent evaluations
- Human reviews evaluator decisions
- Record agreement/disagreement
- Track evaluator accuracy over time

```sql
CREATE TABLE evaluator_validation_log (
    test_id UUID,
    evaluator_id VARCHAR(50),
    evaluator_score INTEGER,
    human_agrees BOOLEAN,
    human_score INTEGER,
    notes TEXT,
    validated_at TIMESTAMP
);
```

**Action on Low Accuracy**:
- If evaluator accuracy < 80%, review and update evaluator prompt
- Re-test on failed cases
- Update evaluator instructions based on feedback

---

### 7. Integration with Development Workflow

**Testing Timing**: Before marking AI-related tasks as complete

**Flow**:
```
Developer: "Completing task 1.2.1 - Backend Dev Agent prompt update"
↓
System: Detects AI functionality changed
↓
System: Runs LLM tests (A/B comparison)
↓
Results: Format 100% ✅, Task completion 96% ✅, Reasoning needs review ⚠️
↓
System: Alerts developer for review
↓
Developer: Reviews cases, updates prompt
↓
System: Re-runs tests → All pass ✅
↓
Developer: Marks task complete
```

**When Tests Run**:
- ✅ Before completing AI-related tasks
- ✅ On prompt version changes
- ✅ On agent logic modifications
- ❌ NOT on every commit
- ❌ NOT blocking CI/CD pipeline
- ❌ NOT for non-AI changes

---

### 8. Failure Handling: Alert for Human Review

**Alert System**:
- Send notification (dashboard, email, Slack)
- Include summary, failures, cases needing review
- Link to review dashboard

**Review Dashboard Features**:
- View failing test cases
- See evaluator judgments
- Compare old vs new outputs
- Approve/reject changes
- Update prompts inline

**Manual Actions** (No Auto-Rollback):
- Approve changes (failures acceptable)
- Reject changes (revert to previous version)
- Update prompt to fix issues
- Update tests (if tests are wrong)
- Mark for further investigation

**Why Manual Review?**
- Context matters - some "failures" may be acceptable improvements
- Developer understands intent of changes
- Test failures may indicate tests need updating
- Gives opportunity to learn before reverting

---

## Rationale

### Why Hybrid (AI + Rubric)?
- **Cost-effective**: Quick rubric filters obvious failures before expensive AI eval
- **Comprehensive**: Catches both structural and semantic issues
- **Fast feedback**: Rubric fails immediately, no waiting for AI
- **Confidence**: Multiple validation layers

### Why Production Data Sampling?
- **Realistic**: Tests reflect actual usage patterns
- **Automatic growth**: Dataset expands as system is used
- **Edge case capture**: Real-world scenarios we might not think to write
- **Quality validation**: Only successful runs sampled

### Why A/B Comparison?
- **Direct evidence**: See exactly how new prompt compares to old
- **Objective**: Statistical comparison reduces bias
- **Clear decision**: Provides concrete recommendation

### Why These Thresholds?
- **100% format**: No tolerance for broken formats
- **Case-by-case reasoning**: Respects nuance and context
- **95% task completion**: High bar while allowing edge cases
- **Flexible consistency**: Acknowledges non-deterministic LLMs

### Why Multiple Evaluators?
- **Reduces bias**: Single evaluator may have blind spots
- **Robustness**: Consensus more reliable than single judgment
- **Coverage**: Different evaluators notice different issues

### Why Human Spot-Check?
- **Cost-effective**: Sample validation cheaper than 100% human review
- **Feedback loop**: Human corrections improve evaluator prompts
- **Quality assurance**: Catches evaluator drift early

### Why Part of Completion Testing?
- **Right timing**: Tests when functionality is actually ready
- **No blocking**: Doesn't slow development iteration
- **Thorough**: Full validation before task marked complete

### Why Manual Review (No Auto-Rollback)?
- **Context matters**: Developer understands intent
- **Learning opportunity**: Understand issues before reverting
- **Test evolution**: Tests may need updating, not just prompts
- **Informed decisions**: Human judgment on acceptable trade-offs

---

## Implications

### Enables
- ✅ Confident prompt updates
- ✅ Regression prevention
- ✅ Quality assurance for LLM components
- ✅ Automated testing of AI functionality
- ✅ Prompt optimization with measurable impact

### Constraints
- LLM testing costs (multiple evaluator runs per test)
- Human review required for edge cases
- Golden dataset requires ongoing curation
- Testing adds time to AI task completion

### Trade-offs
- **Cost vs Quality**: Multiple evaluators expensive but thorough
- **Speed vs Thoroughness**: Full A/B test slow but comprehensive
- **Automation vs Judgment**: Alert for review balances both
- **Coverage vs Maintenance**: Production sampling grows dataset but needs curation

---

## Related Decisions

- **Decision 19**: Overall testing strategy (7-stage pipeline)
- **Decision 69**: Prompt versioning (enables A/B testing)
- **Decision 67**: Orchestrator LLM (one of the agents to test)
- **Decision 68**: RAG System (agents query knowledge - must test)

---

## Tasks Created

### Phase 6.6: AI-Assisted Testing (Updated)
- [x] 6.6.1: Define LLM testing strategy → **COMPLETE** (this decision)
- [ ] 6.6.2: Implement rubric validation framework
  - [ ] Define rubrics per agent type
  - [ ] Format compliance checks
  - [ ] Protocol adherence validation
  - [ ] Security checks
- [ ] 6.6.3: Implement AI evaluator system
  - [ ] Evaluator prompt templates
  - [ ] 3-evaluator panel setup
  - [ ] Consensus calculation
  - [ ] Evaluator rotation/updates
- [ ] 6.6.4: Build production data collection
  - [ ] Sampling logic
  - [ ] Database schema
  - [ ] Human review interface
  - [ ] Dataset management tools
- [ ] 6.6.5: Implement A/B regression testing
  - [ ] A/B test runner
  - [ ] Comparison algorithms
  - [ ] Recommendation engine
  - [ ] Cost optimization (quick check vs full)
- [ ] 6.6.6: Build test alert system
  - [ ] Dashboard UI
  - [ ] Notification system
  - [ ] Review workflow
  - [ ] Approval/rejection actions
- [ ] 6.6.7: Implement evaluator validation
  - [ ] Spot-check sampling
  - [ ] Human review UI
  - [ ] Accuracy tracking
  - [ ] Feedback loop to update evaluators
- [ ] 6.6.8: Integration with development workflow
  - [ ] Task completion hooks
  - [ ] AI functionality detection
  - [ ] Test triggering logic
- [ ] 6.6.9: Testing and documentation
  - [ ] Test the testing framework (meta!)
  - [ ] Golden dataset seed creation
  - [ ] Developer guide
  - [ ] Evaluator maintenance guide

---

## Example Test Scenarios

### Scenario 1: Backend Dev Agent Prompt Update
**Input**: New prompt version 1.1 with improved error handling
**Process**:
1. Load golden dataset (50 backend dev test cases)
2. Run A/B test: v1.0 vs v1.1
3. Results: Format 100%, Task completion 98% (up from 94%), Reasoning flagged on 2 edge cases
4. Alert developer: Overall improvement but 2 cases need review
5. Developer reviews: Edge cases are acceptable trade-offs
6. Developer approves: v1.1 deployed

### Scenario 2: Orchestrator Decision Logic Change
**Input**: Modified orchestrator agent selection algorithm
**Process**:
1. Run orchestrator test suite (30 decision scenarios)
2. Quick check (10 cases): All pass
3. Full validation (30 cases): 29 pass, 1 fail
4. Failed case: Should have escalated to human but didn't
5. Alert developer: Critical failure in escalation logic
6. Developer fixes: Update escalation detection
7. Re-test: All pass
8. Task marked complete

### Scenario 3: Evaluator Validation
**Input**: Weekly spot-check of evaluator accuracy
**Process**:
1. Sample 20 random evaluations from past week
2. Human reviews each evaluation
3. Results: 18/20 agree, 2/20 disagree
4. Disagreement cases: Evaluator too lenient on code quality
5. Update evaluator prompt: Strengthen code quality criteria
6. Re-test on disagreement cases: Now aligned with human judgment
7. Continue monitoring

---

## Documentation

**Decision Document**: `docs/architecture/decision-72-llm-testing-strategy.md` (this file)  
**Testing Guide**: To be created in `docs/guides/llm-testing-guide.md`  
**Evaluator Prompts**: To be created in `prompts/evaluators/`  
**Rubric Definitions**: To be created in `docs/testing/rubrics.md`

---

*Decision finalized: Nov 1, 2025*  
*Implementation priority: P0 - Must complete before validating any LLM changes*
