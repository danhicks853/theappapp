# TheAppApp Testing Philosophy

## Overview
This document defines the comprehensive testing strategy that guides all development tasks. Every piece of code must be thoroughly tested at multiple levels to ensure reliability and maintainability.

---

## Testing Hierarchy

### 1. Unit Tests - Every Single Task
**Scope**: Each individual task (1.1, 1.2, 1.3, etc.)

**Coverage Requirements**:
- **≥90% branch coverage** for all modules
- **≥95% branch coverage** for critical modules (orchestrator, TAS, security, RAG)
- **100% coverage** for public APIs and error handling
- **Test all code paths** - success, failure, edge cases

**Quality Requirements**:
- **Isolated testing** - No external dependencies (mock everything)
- **Fast execution** - Unit tests must complete in seconds
- **Descriptive assertions** - Clear what is being tested and why
- **Deterministic** - No randomness, same input = same output
- **Independent** - Tests can run in any order

**Implementation Standards**:
```python
# Example for task 1.1.1
def test_orchestrator_initialization():
    # Test successful initialization
    orchestrator = Orchestrator()
    assert orchestrator.state == "ready"
    assert orchestrator.agents == []
    
    # Test initialization with configuration
    config = {"max_projects": 10}
    orchestrator = Orchestrator(config)
    assert orchestrator.config == config
    
    # Test failure cases
    with pytest.raises(InvalidConfigError):
        Orchestrator({"max_projects": -1})
```

**Tools**: pytest (Python), Jest (TypeScript), language-specific frameworks

### 2. Integration Tests - Every Task Set
**Scope**: Each task set (1.1-1.2, 2.1-2.3, etc.)

**Coverage Requirements**:
- **≥75% functional coverage** for all workflows
- **≥85% functional coverage** for critical workflows (orchestration, human gates, agent collaboration)
- **100% coverage** for data persistence and recovery scenarios

**Quality Requirements**:
- **Real database** - Tests **must** run against the Postgres fixtures defined in `backend/tests/integration/conftest.py` (no SQLite or in-memory substitutes)
- **Component interaction** - Test how tasks work together
- **Database integration** - Real database operations (TestContainers)
- **External service mocking** - Controlled external dependencies
- **State management** - Verify data flows between components
- **Error propagation** - Test failure handling across boundaries

**Implementation Standards**:
```python
# Example for task set 1.1-1.2 (Orchestrator + Agents)
def test_orchestrator_agent_coordination():
    # Setup real orchestrator and agent
    orchestrator = Orchestrator()
    backend_dev = BackendDeveloperAgent()
    
    # Test agent registration
    orchestrator.register_agent(backend_dev)
    assert len(orchestrator.agents) == 1
    assert orchestrator.agents[0].type == "backend_developer"
    
    # Test task assignment
    task = Task(type="backend_development", requirements={})
    result = orchestrator.assign_task(task)
    assert result.assigned_agent == backend_dev
    assert result.status == "assigned"
```

**Tools**: pytest with fixtures, TestContainers, real PostgreSQL/Redis

### 3. End-to-End Tests - Every Phase
**Scope**: Each complete phase (Phase 1, Phase 2, etc.)

**Coverage Requirements**:
- **≥70% scenario coverage** for all user journeys
- **100% coverage** for critical scenarios (project creation, human approval gates, agent orchestration)
- **100% coverage** for onboarding and checkout flows

**Quality Requirements**:
- **Full workflow testing** - Complete phase execution
- **Real environment** - Production-like setup with Docker Compose
- **User scenarios** - Real usage patterns (Playwright)
- **Performance validation** - Response times and resource usage
- **Security verification** - Authentication, authorization, data protection

**Implementation Standards**:
```python
# Example for Phase 1 (Core Architecture)
def test_phase_1_complete_workflow():
    # Setup complete system
    orchestrator = Orchestrator()
    agents = create_all_agent_types()
    
    # Test project creation workflow
    project = Project(name="Test Project")
    result = orchestrator.create_project(project)
    
    # Verify all agents initialized
    assert len(result.agents) == 11
    assert result.state == "ready"
    
    # Test task execution through complete flow
    task = create_sample_task()
    execution_result = orchestrator.execute_task(task)
    assert execution_result.completed == True
    assert execution_result.deliverables != []
```

**Tools**: Playwright, Selenium, Docker Compose, real services

### 4. LLM Tests - Every LLM Component
**Scope**: All components using LLM (orchestrator, agents, prompts)

**Reference**: Decision 72 - LLM Testing Strategy

**Coverage Requirements**:
- **100% coverage** - All LLM interaction points
- **Stage 1 (Rubric)**: 100% structure validation
- **Stage 2 (AI Panel)**: 100% semantic evaluation

**Two-Stage Evaluation**:

**Stage 1: Rubric Validation** (Fast, Deterministic)
```python
def test_orchestrator_reasoning_structure():
    """Rubric validation - verify output structure"""
    client = OrchestratorLLMClient()
    result = client.reason_about_task(task="example")
    
    # Required fields present
    assert "reasoning" in result
    assert "decision" in result
    assert "confidence" in result
    
    # Valid data types
    assert isinstance(result["confidence"], float)
    assert 0 <= result["confidence"] <= 1
    
    # JSON structure valid
    assert result["decision"]["agent_type"] in VALID_AGENT_TYPES
```

**Stage 2: AI Panel Evaluation** (Expensive, Semantic)
```python
def test_orchestrator_reasoning_quality():
    """AI evaluation - verify reasoning quality"""
    client = OrchestratorLLMClient()
    test_case = load_golden_test_case("task_reasoning_001")
    
    result = client.reason_about_task(task=test_case.input)
    
    # 3-evaluator panel
    evaluators = LLMEvaluatorPanel(evaluator_count=3)
    evaluation = evaluators.evaluate(
        output=result,
        criteria=[
            "logical_consistency",
            "completeness",
            "accuracy",
            "instruction_adherence",
            "code_quality",  # if code generated
            "security_awareness"  # if security relevant
        ]
    )
    
    # Consensus required
    assert evaluation.consensus_passed
    assert evaluation.confidence >= 0.8
```

**Golden Dataset**:
- Production-sampled successful interactions (10% sample rate)
- All edge cases handled well
- Error scenarios with proper recovery
- Inter-agent collaboration examples

**Quality Requirements**:
- **Rubric tests** run with every task (fast, deterministic)
- **AI panel tests** run for LLM tasks (expensive, thorough)
- **A/B testing** when prompts change (regression detection)
- **Human validation** spot-check 10% of AI evaluations

**Tools**: pytest, custom LLM evaluator framework, Qdrant for golden dataset

---

## Critical Testing Policy

### Zero Tolerance for Test Failures
- **ALL tests must pass** - No exceptions, no workarounds
- **Any failure stops the process** - Request user input immediately with failure report:
  - Test name and failure type (assertion, timeout, error)
  - Complete error message and stack trace
  - Code location (file:line)
  - Attempted root cause (if determinable from error message)
- **NEVER modify tests** to engineer a pass when there's a known issue
- **Fix the issue** - Address the root cause of test failures
- **No test is allowed to fail** - Failing tests indicate broken code, not broken tests

### Retry Policy
- **One retry only** for timeout or infrastructure issues (network, container startup, DB connection)
- **If same test fails again** → Stop and ask for user input (possible flaky test)
- **No retries** for assertion failures or logic errors (fix the code)
- **Track retry attempts** - Log all retries for flakiness detection

### Test Integrity Principles
- **Tests are the source of truth** - If tests fail, code is wrong
- **Never skip tests** - All tests must run in CI/CD pipeline
- **Never mark tests as expected failure** - Fix the underlying issue
- **Never disable tests** - All tests remain active throughout development
- **Test failures block progress** - No task completion until all tests pass
- **No coverage regression** - New/changed code must not reduce coverage percentages

### Issue Resolution Process
1. **Test fails** → Stop development immediately
2. **Check failure type**:
   - Timeout/infrastructure → Retry once
   - Same test fails twice → Stop and ask for user input
   - Assertion/logic error → No retry, fix code
3. **Analyze failure** → Understand root cause
4. **Fix implementation** → Make code correct (never fix tests)
5. **Re-run tests** → Verify fix works
6. **If stuck** → Request user input with error details
7. **Only proceed** → When ALL tests pass

---

## Testing Principles

### "Test Reality" Philosophy (from Phase 3)
- **Mock as little as possible** - Test real integrations
- **External services** - Test against real APIs when possible
- **Database operations** - Use real databases, not in-memory fakes
- **File system** - Test actual file operations
- **Network calls** - Test real network behavior
- **Exceptions**: Only mock when it would interfere with production systems

### Quality Gates
- **No task is complete without unit tests**
- **No task set is complete without integration tests**
- **No phase is complete without e2e tests**
- **All tests must pass 100%** before marking tasks complete
- **Performance tests must meet benchmarks** before phase completion

### Continuous Testing
- **Test-driven development** - Write tests before implementation
- **Automated execution** - Tests run on every commit
- **Parallel execution** - Run tests concurrently for speed
- **Fail-fast** - Stop on first test failure
- **Coverage reporting** - Track coverage trends over time

---

## Testing Tools & Frameworks

### Backend (Python/FastAPI)
- **Unit Tests**: pytest, pytest-asyncio, pytest-cov
- **Integration**: pytest with TestContainers, real PostgreSQL/Redis
- **E2E**: pytest with Docker Compose, real services
- **Security**: pytest-bandit, security scanning tools

### Frontend (React/TypeScript)
- **Unit Tests**: Jest, React Testing Library
- **Integration**: Jest with mock services, component integration
- **E2E**: Playwright, real browser automation
- **Performance**: Lighthouse, WebPageTest

### Infrastructure & DevOps
- **Container Tests**: Dockerfile testing, container security
- **Deployment Tests**: Terraform testing, infrastructure validation
- **Monitoring Tests**: Prometheus/Grafana integration testing
- **Security Tests**: OWASP ZAP, container scanning

---

## Test Data Management

### Test Data Strategy
- **Deterministic data** - Consistent test results
- **Isolated databases** - Each test gets clean database
- **Realistic data** - Test with production-like data volumes
- **Synthetic data only** - No real user data, secrets, or PII in tests
- **Data cleanup** - Automatic cleanup after each test

### Security Requirements
- **No secrets in tests** - Use fake API keys, test credentials only
- **No hardcoded passwords** - Use environment variables with test values
- **Synthetic data only** - Generate realistic but fake data
- **No production data** - Tests never touch production systems
- **Encrypted test secrets** - If secrets needed, encrypt with test-only keys

### Test Environments
- **Local development** - Fast feedback, minimal services
- **CI/CD pipeline** - Full service stack, automated
- **Staging** - Production-like, manual verification
- **Performance testing** - Dedicated hardware, realistic load

---

## Success Metrics

### Coverage Requirements

**Unit Tests**:
- **≥90% branch coverage** - All modules
- **≥95% branch coverage** - Critical modules (orchestrator, TAS, security, RAG, agent framework)
- **100% coverage** - Public APIs, error handlers, security functions

**Integration Tests**:
- **≥75% functional coverage** - All workflows
- **≥85% functional coverage** - Critical workflows (orchestration, gates, collaboration)
- **100% coverage** - Data persistence, recovery, state management

**E2E Tests**:
- **≥70% scenario coverage** - All user journeys
- **100% coverage** - Project creation, onboarding, checkout, human approval gates

**LLM Tests** (per Decision 72):
- **100% coverage** - All LLM interaction points
- **Stage 1 (Rubric)**: 100% structure validation
- **Stage 2 (AI Panel)**: 100% semantic evaluation for reasoning components
- **Golden Dataset**: Representative samples from production

**Security Coverage**:
- **100%** - Authentication, authorization, permission checks
- **100%** - TAS privilege enforcement
- **100%** - Secrets handling, encryption, data protection

### Performance Benchmarks
- **Unit Tests**: < 5 seconds total execution time
- **Integration Tests**: < 2 minutes total execution time
- **E2E Tests**: < 10 minutes total execution time
- **Response Times**: API calls < 200ms, page loads < 2s

### Quality Standards
- **Zero flaky tests** - All tests must be deterministic
- **Clear error messages** - Test failures must be actionable
- **Documentation** - Complex test scenarios must be documented
- **Maintainability** - Tests must be easy to understand and modify

---

## Testing Workflow

### Development Process
1. **Write failing test** for the task requirement
2. **Implement minimal code** to make test pass
3. **Refactor and improve** while keeping tests green
4. **Add integration tests** for component interactions
5. **Verify e2e tests** pass for phase completion
6. **Update tracker** only when all tests pass

### Per-Task Testing
- **Every task**: Run unit tests with coverage
- **Every task set**: Run integration tests
- **Every phase**: Run E2E tests
- **Every LLM task**: Run rubric + AI panel tests
- **All tests must pass** before marking task complete

---

## Best Practices

### Test Organization
- **Mirror source structure** - Test files match implementation structure
- **Naming convention**: `test_[module].py` for Python, `[module].test.tsx` for TypeScript
- **One test file per module** - Keep tests co-located with implementation
- **Shared fixtures** - Use `conftest.py` (pytest) or test utilities for reusable setup

### Test Clarity
- **Descriptive names** - Test names should describe what is being tested and expected outcome
- **AAA pattern** - Arrange (setup), Act (execute), Assert (verify)
- **Single assertion per test** - Each test should verify one thing (exceptions for related assertions)
- **Clear failure messages** - Use descriptive assert messages for easier debugging

### Test Isolation
- **No test interdependencies** - Tests must run independently in any order
- **Clean state** - Each test gets fresh database/state (use fixtures/transactions)
- **No shared state** - Tests should not modify global state
- **Teardown guaranteed** - Use try/finally or fixtures to ensure cleanup

### Mocking Strategy
- **Mock external dependencies** - APIs, network calls, third-party services
- **Use real databases** - TestContainers for PostgreSQL, Redis in tests
- **Mock LLM calls in unit tests** - Use pre-recorded responses for speed
- **Real LLM calls in LLM tests** - Actual API calls with golden dataset validation

### Performance Optimization
- **Parallel execution** - Run independent tests concurrently (pytest-xdist)
- **Database pooling** - Reuse database connections across tests
- **Lazy loading** - Only create expensive fixtures when needed
- **Incremental testing** - Run only affected tests during development

### Security Best Practices
- **No secrets committed** - Use environment variables, never hardcode
- **Rotate test credentials** - Change test API keys regularly
- **Scan dependencies** - Check for vulnerabilities in test packages
- **Audit test data** - Ensure no PII or sensitive data in tests

### Continuous Improvement
- **Review flaky tests** - Investigate and fix tests that fail intermittently
- **Update golden datasets** - Refresh LLM test cases quarterly
- **Measure test effectiveness** - Track mutation testing scores
- **Refactor test code** - Treat tests like production code (DRY, maintainable)

### Documentation
- **Document complex tests** - Add comments explaining non-obvious test logic
- **Maintain test README** - Document test environment setup
- **Update on changes** - Keep test documentation current with code changes
- **Example tests** - Provide reference examples for each test type

---

## Notes
- This testing philosophy applies to ALL 300 development tasks
- No exceptions to the testing hierarchy
- Tests are as important as the implementation code
- Quality is non-negotiable - every line must be tested
- LLM components require special testing per Decision 72
