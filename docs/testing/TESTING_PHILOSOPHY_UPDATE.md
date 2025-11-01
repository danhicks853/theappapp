# Testing Philosophy Update Summary

**Date**: Nov 1, 2025  
**Updated**: `testing_philosophy.md` and `TASK_EXECUTION_GUIDE.md`

---

## Changes Made

### 1. Coverage Requirements (Updated)

**Previous**: 100% coverage across the board  
**New**: Tiered coverage based on risk

**Unit Tests**:
- ✅ **≥90% branch coverage** - All modules
- ✅ **≥95% branch coverage** - Critical modules (orchestrator, TAS, security, RAG, agent framework)
- ✅ **100% coverage** - Public APIs, error handlers, security functions

**Integration Tests**:
- ✅ **≥75% functional coverage** - All workflows
- ✅ **≥85% functional coverage** - Critical workflows (orchestration, gates, collaboration)
- ✅ **100% coverage** - Data persistence, recovery, state management

**E2E Tests**:
- ✅ **≥70% scenario coverage** - All user journeys
- ✅ **100% coverage** - Critical scenarios (project creation, approval gates, orchestration)
- ✅ **100% coverage** - Onboarding and checkout flows

**LLM Tests** (NEW - fully integrated):
- ✅ **100% coverage** - All LLM interaction points
- ✅ **Stage 1 (Rubric)**: 100% structure validation
- ✅ **Stage 2 (AI Panel)**: 100% semantic evaluation

---

### 2. Test Failure Policy (NEW)

**All Tests Must Pass**:
- Any failure stops the process
- Request user input immediately with failure report:
  - Test name and failure type
  - Complete error message and stack trace
  - Code location (file:line)
  - Attempted root cause analysis
- No exceptions, no workarounds

**Retry Policy** (NEW):
- ✅ **One retry only** for timeout/infrastructure issues
- ✅ **If same test fails twice** → Stop and ask for user input (flaky test)
- ❌ **No retries** for assertion/logic errors (fix code immediately)
- ✅ **Track retry attempts** for flakiness detection

**No Coverage Regression** (NEW):
- New/changed code must not reduce coverage percentages
- Enforced at PR/merge time

---

### 3. Security Requirements (NEW)

**Test Data Security**:
- ✅ **No secrets in tests** - Use fake API keys only
- ✅ **No hardcoded passwords** - Use environment variables
- ✅ **Synthetic data only** - No real user data, secrets, or PII
- ✅ **No production data** - Tests never touch production
- ✅ **Encrypted test secrets** - If needed, use test-only encryption

**Security Coverage**:
- ✅ **100%** - Authentication, authorization, permission checks
- ✅ **100%** - TAS privilege enforcement
- ✅ **100%** - Secrets handling, encryption, data protection

---

### 4. LLM Testing Integration (NEW - Major Addition)

**Added as 4th Tier** in testing hierarchy alongside Unit, Integration, E2E

**Two-Stage Evaluation**:

**Stage 1: Rubric Validation** (Fast, Deterministic)
- JSON structure compliance
- Required fields present
- Valid data types and ranges
- Run with every LLM task
- Example: Verify LLM output has "reasoning", "decision", "confidence" fields

**Stage 2: AI Panel Evaluation** (Expensive, Semantic)
- 3-evaluator consensus panel
- Semantic quality assessment
- Criteria: logical_consistency, completeness, accuracy, instruction_adherence, code_quality, security_awareness
- Run with every LLM task (comprehensive validation)
- Requires ≥80% confidence for pass

**Golden Dataset**:
- Production-sampled successful interactions (10% sample rate)
- Edge cases handled well
- Error scenarios with recovery
- Inter-agent collaboration examples
- Stored in Qdrant

**Quality Requirements**:
- Rubric tests: Every LLM task
- AI panel tests: Every LLM task
- A/B testing: When prompts change
- Human validation: Spot-check 10% of AI evaluations

**Reference**: Decision 72 - LLM Testing Strategy

---

### 6. Best Practices (NEW - Major Addition)

Added comprehensive best practices section covering:

**Test Organization**:
- Mirror source structure
- Naming conventions
- One test file per module
- Shared fixtures

**Test Clarity**:
- Descriptive names
- AAA pattern (Arrange, Act, Assert)
- Single assertion per test
- Clear failure messages

**Test Isolation**:
- No interdependencies
- Clean state for each test
- No shared state
- Guaranteed teardown

**Mocking Strategy**:
- Mock external dependencies
- Use real databases (TestContainers)
- Mock LLM in unit tests
- Real LLM in LLM tests

**Performance Optimization**:
- Parallel execution (pytest-xdist)
- Database pooling
- Lazy loading fixtures
- Incremental testing

**Security Best Practices**:
- No secrets committed
- Rotate test credentials
- Scan dependencies
- Audit test data

**Continuous Improvement**:
- Review flaky tests
- Update golden datasets quarterly
- Measure test effectiveness
- Refactor test code

**Documentation**:
- Document complex tests
- Maintain test README
- Update on changes
- Provide example tests

---

## Updated Documents

### 1. `testing_philosophy.md`
- Updated coverage requirements (tiered approach)
- Added retry policy
- Added security requirements
- Added nightly testing section
- **Added LLM testing as 4th tier** with complete examples
- Added comprehensive best practices section
- Updated from 100% coverage mandate to risk-based coverage

### 2. `TASK_EXECUTION_GUIDE.md`
- Updated Step 5: LLM Testing (expanded two-stage approach)
- Updated Step 6: Run Tests (branch coverage, retry policy)
- Updated Step 7: Resolve Test Failures (retry policy, coverage targets)
- Updated coverage targets throughout (90%/95% instead of 100%)

---

## Impact on Development

### What Changed for Developers

**More Realistic**:
- 90%+ coverage target (from 100%) is achievable
- Critical modules still require 95%+
- Focus on branch coverage (more meaningful than line coverage)

**Clearer Failure Handling**:
- One retry for infrastructure issues
- Immediate stop for assertion failures
- No ambiguity on what to do when tests fail

**Security Enforced**:
- Explicit "no secrets in tests" policy
- Synthetic data mandate
- No room for shortcuts

**LLM Testing Integrated**:
- Clear when LLM tests required
- Two-stage approach balances speed vs thoroughness
- Golden dataset provides regression detection

**Best Practices Documented**:
- No guessing on test organization
- Clear patterns for common scenarios
- Performance optimization guidance

---

## Compliance Checklist

### Every Task Must Now:

- [ ] **Unit tests**: ≥90% branch coverage (≥95% if critical module)
- [ ] **Integration tests**: If task set complete
- [ ] **E2E tests**: If phase complete
- [ ] **LLM tests**: If task uses LLM (both stages - rubric + AI panel)
- [ ] **All tests pass**: No failures allowed
- [ ] **Failure reporting**: Detailed report on any failure
- [ ] **Retry policy**: One retry max for infrastructure
- [ ] **No secrets**: Use synthetic data only
- [ ] **No coverage regression**: Coverage must not decrease

---

## Next Steps

### For Developers
1. Read updated `testing_philosophy.md` completely
2. Update test commands to use `--cov-branch`
3. Implement retry logic for infrastructure failures
4. Add LLM tests for any LLM components (two-stage)
5. Ensure no secrets in test files

### For Testing Workflow
1. Update coverage thresholds (90%/95% branch coverage)
2. Implement retry logic (1 retry for timeouts)
3. Add failure reporting on all test failures
4. Track flaky tests (same test fails twice)
5. Enforce no coverage regression

### For Testing Framework
1. Implement LLM evaluator panel framework
2. Set up golden dataset in Qdrant
3. Configure rubric validation (per LLM task)
4. Configure AI panel evaluation (per LLM task)
5. Add A/B testing for prompt changes

---

**Last Updated**: Nov 1, 2025  
**Status**: Testing philosophy updated and ready for use  
**Integration**: LLM testing fully integrated per Decision 72  
**Coverage**: Realistic, risk-based approach with 90%+ targets
