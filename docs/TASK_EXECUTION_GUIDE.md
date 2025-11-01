# Task Execution Guide for Non-Reasoning Models

**Purpose**: Complete step-by-step workflow for executing any task from `planning/development_tracker.md`

**Target**: Models without reasoning capability (GPT-4o-mini, Claude Haiku, Codex, etc.)

---

## Task Execution Workflow

### Command: "start the next task"

When you receive this command, follow these steps **exactly**:

---

## Step 1: Locate Next Task

1. Open `docs/planning/development_tracker.md`
2. Find first task marked `- [ ] **TODO**:`
3. Read complete task specification
4. Note the task number (e.g., 1.1.1, Task 1)

---

## Step 2: Read Referenced Decision

1. Look for **Reference** line in task (e.g., `docs/architecture/decision-67-*.md`)
2. Open and read the complete decision document
3. Review all code examples in the decision
4. Understand the acceptance criteria

---

## Step 3: Write Implementation Code

### File Creation
- Create file at exact path specified in **File**: field
- Use directory structure as specified (create directories if needed)

### Code Structure
```python
# File: backend/services/example.py

"""
Module: [Module name]
Purpose: [One-line purpose from task]

Reference: [Decision document reference]
"""

from typing import Dict, List, Optional
import asyncio
# ... all imports

class ExampleClass:
    """
    [Class purpose from task]
    
    Attributes:
        [List from task specification]
    
    Methods:
        [List from task specification]
    """
    
    def __init__(self, ...):
        """Initialize with [parameters from task]."""
        pass
    
    def method_name(self, ...):
        """
        [Method purpose from task]
        
        Args:
            [From task specification]
        
        Returns:
            [From task specification]
        
        Raises:
            [From Decision 80 - Error Handling]
        """
        pass
```

### Implementation Requirements
1. **Type Hints**: Full typing for all functions/methods
2. **Docstrings**: Google-style for all classes/functions
3. **Error Handling**: Use error taxonomy from Decision 80
4. **Imports**: Alphabetical, stdlib → third-party → local
5. **Code Style**: PEP 8 (Python) / Airbnb (TypeScript)

---

## Step 4: Write Tests

### Test File Location

**Pattern**: Mirror implementation path with `test_` prefix

**Examples**:
```
Implementation: backend/services/orchestrator.py
Test File:      backend/tests/services/test_orchestrator.py

Implementation: frontend/src/components/Dashboard.tsx  
Test File:      frontend/src/components/__tests__/Dashboard.test.tsx
```

### Test Structure

```python
# File: backend/tests/services/test_example.py

"""
Tests for: backend/services/example.py
Task: [Task number and title]
Coverage Target: 90%+
"""

import pytest
from backend.services.example import ExampleClass

class TestExampleClass:
    """Test suite for ExampleClass"""
    
    def test_initialization_success(self):
        """Test successful initialization with valid parameters"""
        obj = ExampleClass(param="value")
        assert obj.param == "value"
        assert obj.state == "initialized"
    
    def test_initialization_invalid_params(self):
        """Test initialization fails with invalid parameters"""
        with pytest.raises(ValueError):
            ExampleClass(param=None)
    
    def test_method_name_success(self):
        """Test method_name with valid input"""
        obj = ExampleClass()
        result = obj.method_name(input="test")
        assert result == "expected_output"
    
    def test_method_name_edge_cases(self):
        """Test method_name with edge cases"""
        obj = ExampleClass()
        # Test empty input
        result = obj.method_name(input="")
        assert result == ""
        # Test None input
        with pytest.raises(TypeError):
            obj.method_name(input=None)
```

### Test Coverage Requirements

**Unit Tests** (Required for EVERY task):
- ✅ Happy path (success case)
- ✅ Edge cases (empty, None, boundaries)
- ✅ Error cases (exceptions, validation failures)
- ✅ Integration points (mocked dependencies)
- **Target**: ≥90% branch coverage (≥95% for critical modules)
- **Critical modules**: orchestrator, TAS, security, RAG, agent framework

**Integration Tests** (Required for task sets):
- ✅ Component interaction
- ✅ Database operations (real database)
- ✅ External service calls (mocked services)
- ✅ End-to-end workflows

---

## Step 5: Write LLM Tests (If Task Uses LLM)

### When Required
If task file path contains:
- `llm_client`
- `prompts/`
- Any agent implementation
- Orchestrator logic

### LLM Test Structure

```python
# File: backend/tests/llm/test_orchestrator_llm.py

"""
LLM Tests for: Orchestrator LLM Integration
Reference: Decision 72 - LLM Testing Strategy
"""

import pytest
from backend.services.orchestrator_llm_client import OrchestratorLLMClient
from backend.tests.llm.evaluators import LLMEvaluatorPanel

class TestOrchestratorLLMReasoning:
    """Test LLM reasoning capabilities"""
    
    def test_reasoning_structure(self):
        """Stage 1: Rubric validation - verify output structure"""
        client = OrchestratorLLMClient()
        result = client.reason_about_task(task="example")
        
        # Rubric checks (deterministic)
        assert "reasoning" in result
        assert "decision" in result
        assert "confidence" in result
        assert 0 <= result["confidence"] <= 1
    
    def test_reasoning_quality_ai_eval(self):
        """Stage 2: AI evaluation - verify reasoning quality"""
        client = OrchestratorLLMClient()
        test_case = load_golden_test_case("task_reasoning_001")
        
        result = client.reason_about_task(task=test_case.input)
        
        # AI panel evaluation
        evaluators = LLMEvaluatorPanel(evaluator_count=3)
        evaluation = evaluators.evaluate(
            output=result,
            criteria=[
                "logical_consistency",
                "completeness",
                "accuracy",
                "instruction_adherence"
            ]
        )
        
        assert evaluation.consensus_passed
        assert evaluation.confidence >= 0.8
```

### LLM Testing Requirements (from Decision 72)
**When Required**: All tasks with LLM components (orchestrator, agents, prompts)

**Two-Stage Testing**:
1. **Stage 1 - Rubric** (Run with every LLM task):
   - Structure validation (JSON fields, types, ranges)
   - Format compliance (required fields present)
   - Fast, deterministic checks
2. **Stage 2 - AI Panel** (Run with every LLM task):
   - 3-evaluator consensus panel
   - Semantic quality evaluation
   - Criteria: logical_consistency, completeness, accuracy, instruction_adherence
   - Thorough semantic validation

**Coverage**: 100% of all LLM interaction points

**Golden Dataset**: Use production-sampled test cases from Qdrant

---

## Step 6: Run Tests

### Command Execution

**Python/Backend**:
```bash
# Run tests with coverage
pytest backend/tests/services/test_example.py -v --cov=backend/services/example --cov-report=term-missing --cov-branch

# Must show: Branch coverage >= 90% (or >= 95% for critical modules)
```

**TypeScript/Frontend**:
```bash
# Run tests with coverage
npm test -- frontend/src/components/__tests__/Dashboard.test.tsx --coverage --coverage-branches

# Must show: Branch coverage >= 90%
```

### Retry Policy
- **One retry only** for timeout/infrastructure issues (network, DB connection)
- **If same test fails twice** → Stop and ask for user input (possible flaky test)
- **No retries** for assertion/logic errors (fix the code immediately)

### Expected Output
```
================================ test session starts ================================
backend/tests/services/test_example.py::TestExampleClass::test_initialization_success PASSED
backend/tests/services/test_example.py::TestExampleClass::test_initialization_invalid_params PASSED
backend/tests/services/test_example.py::TestExampleClass::test_method_name_success PASSED
backend/tests/services/test_example.py::TestExampleClass::test_method_name_edge_cases PASSED

----------- coverage: platform win32, python 3.11 -----------
Name                              Stmts   Miss  Cover   Missing
---------------------------------------------------------------
backend/services/example.py          45      2    96%   78-79
---------------------------------------------------------------
TOTAL                                45      2    96%

========================== 4 passed in 0.23s ==========================
```

---

## Step 7: Resolve Test Failures

### If Tests Fail

**Check Failure Type**:
1. **Timeout/Infrastructure** (network, DB connection, container):
   - Retry once automatically
   - If fails again → Stop and ask for user input
2. **Assertion/Logic Error**:
   - No retry, fix code immediately
   - Never modify tests to pass

**DO NOT**:
- ❌ Modify tests to make them pass
- ❌ Skip failing tests
- ❌ Mark tests as "expected failure"
- ❌ Disable coverage checks
- ❌ Proceed to next step
- ❌ Retry assertion failures

**DO**:
1. ✅ Identify failure type (timeout vs assertion)
2. ✅ Retry once only for infrastructure issues
3. ✅ If same test fails twice → Request user input with failure report:
   - Test name and failure type
   - Complete error message and stack trace
   - Code location (file:line)
   - Attempted root cause analysis
4. ✅ For assertion failures → Fix implementation immediately
5. ✅ Re-run tests
6. ✅ Repeat until ALL tests pass

### Coverage Below Target

**If branch coverage < 90% (or < 95% for critical modules)**:
1. Run with `--cov-report=term-missing --cov-branch` to see uncovered branches
2. Add tests for uncovered code paths
3. Re-run until coverage meets target
4. **No coverage regression** - New code must not reduce existing coverage

---

## Step 8: Write Documentation

### Documentation Location

**Pattern**: `docs/implementation/phase[N]/[module-name].md`

**Examples**:
```
Task 1.1.1 (Phase 1, Orchestrator):
docs/implementation/phase1/orchestrator-core.md

Task 2.3.1 (Phase 2, TAS):
docs/implementation/phase2/tool-access-service.md

Task 4.1.1 (Phase 4, Frontend):
docs/implementation/phase4/cost-tracking-dashboard.md
```

### Documentation Template

```markdown
# [Task Title]

**Task**: [Task number]  
**Phase**: [Phase number]  
**Completed**: [Date]  
**Coverage**: [X%]

---

## Implementation Summary

[2-3 sentence summary of what was built]

---

## Files Created

- `[file path]` - [Purpose]
- `[test file path]` - [Test coverage]

---

## Key Classes/Functions

### `ClassName`
**Purpose**: [What it does]  
**Methods**:
- `method_name()` - [What it does]

---

## Design Decisions

- **[Decision made]**: [Rationale]
- **[Trade-off]**: [Why chosen]

---

## Test Coverage

**Unit Tests**: [X%]  
**Integration Tests**: [List if applicable]  
**LLM Tests**: [List if applicable]

**Test Files**:
- `[test file path]`

---

## Dependencies

- `[package]` - [Why needed]

---

## Usage Example

\`\`\`python
from [module] import [class]

# Example usage
obj = ClassName()
result = obj.method()
\`\`\`

---

## Related Tasks

- Depends on: [[Task number]]
- Enables: [[Task number]]

---

## Notes

[Any important notes, gotchas, or future considerations]
```

---

## Step 9: Update Task Status & Commit

### In development_tracker.md

**Change**:
```markdown
- [ ] **TODO**: [Task title]
```

**To**:
```markdown
- [x] **COMPLETED**: [Task title]
```

**Add completion note**:
```markdown
- [x] **COMPLETED**: [Task title]
  - **Completed**: [Date]
  - **Coverage**: [X%]
  - **Documentation**: `docs/implementation/phase[N]/[file].md`
```

### Git Commit

**After marking complete, commit your work**:

```bash
# Stage all changes
git add .

# Commit with descriptive message
git commit -m "feat: [Task number] - [Task title]

- Implementation: [file path]
- Tests: [test file path]
- Coverage: [X%]
- Documentation: docs/implementation/phase[N]/[file].md

Closes #[task number]"

# Push to GitHub
git push
```

**Commit Message Format**:
- `feat:` for new features/implementations
- `test:` for test additions
- `docs:` for documentation only
- `fix:` for bug fixes
- `refactor:` for code improvements

---

## Step 10: Return Summary

### Summary Format

```
TASK COMPLETED: [Task number] - [Task title]

IMPLEMENTATION:
- File: [file path]
- Lines of code: [X]
- Type hints: 100%
- Docstrings: 100%

TESTS:
- Test file: [test file path]
- Tests written: [X]
- All tests: PASSED ✓
- Coverage: [X%] (target: 90%+)
- LLM tests: [PASSED/N/A]

DOCUMENTATION:
- Location: docs/implementation/phase[N]/[file].md
- Includes: Usage examples, design decisions, dependencies

GIT:
- Committed: Yes
- Pushed to GitHub: Yes
- Commit: [commit hash]

NEXT TASK:
- [Next task number]: [Next task title]
- Reference: [Decision document]

STATUS: Ready for next task
```

---

## Example Complete Execution

### Input: "start the next task"

### Execution:
```
1. Located: Task 1.1.1 - Implement synchronous task queue system
2. Read: docs/architecture/decision-67-orchestrator-llm-integration.md
3. Created: backend/services/task_queue.py (87 lines)
4. Created: backend/tests/services/test_task_queue.py (156 lines)
5. Ran: pytest backend/tests/services/test_task_queue.py -v --cov
   Result: 8 tests passed, Coverage: 94%
6. Created: docs/implementation/phase1/task-queue.md
7. Updated: development_tracker.md (marked complete)
```

### Output:
```
TASK COMPLETED: 1.1.1 - Implement synchronous task queue system

IMPLEMENTATION:
- File: backend/services/task_queue.py
- Lines of code: 87
- Type hints: 100%
- Docstrings: 100%

TESTS:
- Test file: backend/tests/services/test_task_queue.py
- Tests written: 8
- All tests: PASSED ✓
- Coverage: 94% (target: 90%+)
- LLM tests: N/A

DOCUMENTATION:
- Location: docs/implementation/phase1/task-queue.md
- Includes: Usage examples, thread safety notes, performance characteristics

NEXT TASK:
- 1.1.2: Create agent communication protocol
- Reference: docs/architecture/decision-67-orchestrator-llm-integration.md

STATUS: Ready for next task
```

---

## Critical Requirements

### Must-Have for Every Task

1. ✅ All code written with full type hints
2. ✅ All code documented with docstrings
3. ✅ All tests written (unit + integration if specified)
4. ✅ All tests passing (100%)
5. ✅ Coverage >= 90%
6. ✅ LLM tests if task uses LLM (per Decision 72)
7. ✅ Documentation created
8. ✅ Task marked complete in tracker
9. ✅ Summary returned

### Failure Conditions

**Stop and ask for help if**:
- Tests fail after 3 fix attempts
- Coverage stuck below 90%
- Unclear how to implement from task specification
- Conflicting information between task and decision
- Missing dependency or tool

---

## Reference Documents

**Always consult**:
- `docs/testing/development_guardrails.md` - Quality standards
- `docs/testing/testing_philosophy.md` - Testing approach
- `docs/architecture/decision-72-llm-testing-strategy.md` - LLM testing
- `docs/architecture/decision-80-error-handling-system.md` - Error handling

**Task-specific**:
- Decision document referenced in task
- Related tasks in same section

---

**Last Updated**: Nov 1, 2025  
**Status**: Complete execution workflow for non-reasoning models  
**Usage**: Reference this for every "start the next task" command
