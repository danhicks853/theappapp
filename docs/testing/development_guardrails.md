# Development Guardrails System - Enhanced

## Overview
This document creates strict guardrails to ensure I follow the enhanced tracker, decisions, and testing philosophy without deviation. Every implementation task must pass through these checkpoints.

**📋 PLANNING COMPLETE**: All 300 tasks have complete specifications including file paths, class names, acceptance criteria, and test requirements. Use these specifications as your primary implementation guide. NO CODE HAS BEEN IMPLEMENTED YET - all tasks are TODO.

---

## Mandatory Pre-Task Checklist

Before starting ANY task, I must complete this checklist:

### 📋 **CRITICAL: Task Execution Guide Compliance**
- [ ] **Read TASK_EXECUTION_GUIDE.md completely** - Follow the exact workflow from `docs/TASK_EXECUTION_GUIDE.md`
- [ ] **Follow Step 1: Locate Next Task** - Find first TODO task in development_tracker.md
- [ ] **Follow Step 2: Read Referenced Decision** - Open and understand the complete decision document
- [ ] **Follow Step 3-7 sequentially** - Implementation → Tests → Run Tests → Resolve Failures → Documentation → Commit
- [ ] **No deviations from guide** - The task execution guide is the source of truth for workflow

### 📋 **Task Validation**
- [ ] **Task exists in enhanced tracker** - Verify task number and description
- [ ] **Decision reference identified** - Find exact decision number and title
- [ ] **Enhancement specification reviewed** - Read the complete task specification in development_tracker.md
- [ ] **File path confirmed** - Verify the exact file path where code should be implemented
- [ ] **Class/method names identified** - Note the specific class and method names to implement

### 📚 **Document Cross-Reference**
- [ ] **Phase decision document** - Read relevant phase decisions (linked in task reference)
- [ ] **Enhanced development tracker** - Verify task status, dependencies, and complete specification
- [ ] **Testing philosophy** - Review testing requirements for task type
- [ ] **Previous implementations** - Check for related completed tasks
- [ ] **Task clarity checklist** - Review task_clarity_checklist.md for quality standards

### 🧪 **Test Preparation**
- [ ] **Unit test scenarios identified** - List all test cases needed
- [ ] **Integration test scope defined** - What components interact
- [ ] **E2E test relevance confirmed** - How this fits phase testing
- [ ] **Testing tools selected** - Frameworks and libraries needed

### 📚 **Documentation Requirements**
- [ ] **Previous task docs reviewed** - Refer back to documentation from previous task
- [ ] **Documentation structure planned** - Tree structure under `docs/` identified
- [ ] **Implementation details planned** - What needs to be documented
- [ ] **Cross-reference strategy** - How to link between related docs

---

## Task Implementation Template

I must use this exact format for every task:

```
## Task Implementation: [Task Number] - [Task Name]

### 📖 **Reference Documents**
- **Decision**: Phase X Decision Y - [Decision Title]
- **Tracker**: Task [Task Number] in section [Section Name]
- **Testing**: Unit/Integration/E2E requirements per testing philosophy

### 🎯 **Requirements Analysis**
- **What must be implemented**: [Specific requirements from decision]
- **Success criteria**: [How we know it's complete]
- **Dependencies**: [What must be completed first]
- **Integration points**: [How it connects to other components]

### 🧪 **Testing Strategy**
- **Unit tests**: [List of specific unit test cases]
- **Integration tests**: [Component interactions to test]
- **E2E relevance**: [How this contributes to phase testing]

### ✅ **Implementation**
[Code implementation with explanations]

### 🧪 **Test Results**
- **Unit tests**: All passing with coverage report
- **Integration tests**: All passing with interaction validation
- **E2E tests**: Phase-level tests still passing

### 📊 **Tracker Update**
- Task marked: TODO → IN_PROGRESS → COMPLETED
- Dependencies updated: [Any dependent tasks ready]
- Phase progress: [Updated phase completion percentage]

### 📚 **Documentation Creation**
- **Implementation doc created**: `docs/implementation/[task-number]-[task-name].md`
- **Architecture decisions documented**: Design choices and rationale
- **API reference updated**: Function signatures and usage examples
- **Cross-references added**: Links to related components and previous tasks
- **Code examples provided**: Usage patterns and integration guides

### 🔍 **Compliance Verification**
- ✅ Decision requirements fully implemented
- ✅ Testing philosophy strictly followed
- ✅ All tests passing (100%)
- ✅ No test modifications to pass
- ✅ Tracker accurately updated
- ✅ Documentation complete and cross-referenced
```

---

## Compliance Verification System

### 🔍 **Self-Audit Questions**
After each task, I must answer:

1. **Task Execution Guide Compliance**: Did I follow ALL steps from `docs/TASK_EXECUTION_GUIDE.md` exactly?
2. **Decision Compliance**: Did I implement exactly what the decision specified?
3. **Testing Compliance**: Did I follow the testing hierarchy (unit → integration → e2e)?
4. **Quality Compliance**: Are ALL tests passing without modification?
5. **Tracker Compliance**: Is the tracker updated accurately?
6. **Documentation Compliance**: Is comprehensive documentation created and cross-referenced?
7. **Reference Compliance**: Did I refer back to previous task documentation when needed?

### ❌ **Failure Modes**
If any answer is "NO", I must:
- **Stop immediately** - Do not proceed
- **Identify the gap** - What requirement wasn't met?
- **Fix the issue** - Address the root cause
- **Consult with user** - If unsure how to proceed
- **Only continue** - When all compliance checks pass

---

## Automated Validation Checklist

### 📋 **Pre-Commit Validation**
Before marking any task complete, verify:

- [ ] **Task exists in tracker** with correct number and description
- [ ] **Decision reference is correct** with exact phase and decision number
- [ ] **All unit tests written** and passing at 100% coverage
- [ ] **All integration tests written** and passing
- [ ] **E2E tests still pass** for the current phase
- [ ] **No tests were modified** to accommodate implementation
- [ ] **Implementation matches decision requirements** exactly
- [ ] **Tracker updated** with correct status and progress
- [ ] **Implementation documentation created** under `docs/implementation/`
- [ ] **Architecture decisions documented** with rationale
- [ ] **Cross-references added** to previous tasks and related components
- [ ] **Previous task docs referenced** when building upon existing work

### 🚫 **Blocking Conditions**
If any of these conditions exist, I CANNOT proceed:

- **Task execution guide not followed** - Stop and restart following `docs/TASK_EXECUTION_GUIDE.md` exactly
- **Task not found in tracker** - Stop and create missing task
- **Decision reference unclear** - Stop and clarify with user
- **Any test failing** - Stop and fix implementation
- **Test coverage < 90%** (or < 95% for critical modules) - Stop and add missing tests
- **Implementation deviates from decision** - Stop and realign
- **Tracker not updated** - Stop and update accurately
- **Documentation missing** - Stop and create comprehensive docs
- **No cross-references** - Stop and add links to related work
- **Previous docs not referenced** - Stop and review and reference prior work
- **Tests not run before commit** - Stop and run full test suite
- **Implementation not committed to git** - Stop and commit with proper message

---

## Quality Assurance Process

### 🔄 **Review Cycle**
For every task implementation:

1. **Pre-implementation review**
   - Verify task exists in tracker
   - Confirm decision reference
   - Define testing strategy
   - Review previous task documentation
   - Plan documentation structure

2. **Implementation phase**
   - Write failing tests first
   - Implement to satisfy tests
   - Document decisions made
   - Track architectural choices

3. **Post-implementation review**
   - Verify all tests pass
   - Confirm decision compliance
   - Update tracker accurately
   - Create comprehensive documentation

4. **Final validation**
   - Cross-reference all documents
   - Ensure no deviations
   - Verify documentation completeness
   - Present completion report

### 📊 **Quality Metrics**
Every task completion must include:

- **Test coverage**: 100% line, branch, function
- **Test results**: All passing, no failures
- **Decision alignment**: 100% requirement coverage
- **Documentation completeness**: Full implementation docs created
- **Cross-reference coverage**: All related components linked
- **Reference compliance**: Previous work properly referenced
- **Tracker accuracy**: Status and progress updated

---

## Error Prevention System

### 🚫 **Common Deviations to Avoid**
- **Not following task execution guide** - CRITICAL - Follow `docs/TASK_EXECUTION_GUIDE.md` exactly, every step
- **Skipping unit tests** - NEVER allowed
- **Modifying tests to pass** - NEVER allowed
- **Implementing extra features** - Stay within decision scope
- **Updating tracker prematurely** - Only update when complete
- **Ignoring decision details** - Follow exactly as specified
- **Skipping documentation** - NEVER allowed - document everything
- **Not referencing previous work** - Always build upon existing docs
- **Poor cross-referencing** - Link all related components clearly
- **Not running tests before commit** - ALWAYS run full test suite
- **Not committing to git** - ALWAYS commit with descriptive message

### ⚠️ **Warning Signs**
If I find myself doing any of these, I must STOP:

- **Thinking "this test is wrong"** - The test is right, fix the code
- **Wanting to skip a test** - All tests are mandatory
- **Adding "nice to have" features** - Stay within scope
- **Rushing to completion** - Quality over speed
- **Assuming requirements** - Verify in decision documents
- **Thinking "I'll document later"** - Document as you build
- **Not checking previous docs** - Always review prior work first
- **Creating isolated documentation** - Always cross-reference

---

## Emergency Procedures

### 🆘 **When Stuck**
If I cannot proceed without breaking guardrails:

1. **Stop immediately** - Do not compromise standards
2. **Identify the blockage** - What specific issue?
3. **Consult decision documents** - Re-read requirements
4. **Review testing philosophy** - Ensure compliance
5. **Ask user for guidance** - Provide specific issue details
6. **Wait for clarification** - Do not proceed until resolved

### 📞 **Escalation Triggers**
I must escalate to user when:

- **Decision requirements unclear** - Need clarification
- **Test failures cannot be resolved** - Need guidance
- **Implementation conflicts with other tasks** - Need coordination
- **Tracker needs updates** - Need confirmation of changes
- **Any guardrail cannot be followed** - Need alternative approach

---

## Compliance Monitoring

### 📈 **Continuous Compliance**
Throughout development, I must:

- **Reference documents for every decision** - No assumptions
- **Write tests before implementation** - Test-driven development
- **Verify all tests pass** - No exceptions
- **Update tracker accurately** - Real-time status
- **Document all deviations** - If any occur (shouldn't)

### 🔍 **Regular Audits**
After each phase, I will:

- **Audit all completed tasks** - Verify compliance
- **Review test coverage** - Ensure 100% maintained
- **Check tracker accuracy** - Verify progress tracking
- **Validate decision alignment** - Confirm requirements met
- **Report any issues** - Transparent communication

---

## Notes
- **CRITICAL**: Task Execution Guide (`docs/TASK_EXECUTION_GUIDE.md`) is the PRIMARY workflow reference
- Follow task execution guide steps 1-7 EXACTLY for every task - no deviations
- These guardrails are MANDATORY - no exceptions
- Quality is non-negotiable - never compromise standards
- Enhanced specifications are the source of truth - always reference
- Decision documents are the source of truth - always reference
- Tests define correctness - never modify to pass
- Documentation is as critical as code - always document thoroughly
- Previous work must be referenced - build upon existing knowledge
- Cross-references are mandatory - create clear linkages
- Exact file paths, class names, and method names must be used - from enhanced specification
- Acceptance criteria must be met - from enhanced specification
- When in doubt - ask for clarification before proceeding
- All 300 tasks are fully specified - use the enhanced specifications as your primary guide
- **WORKFLOW**: Task Execution Guide → Development Tracker → Decision Document → Implementation → Tests → Documentation → Commit

---

## 📋 Planning Status

**Planning Phase**: COMPLETE ✅
**Implementation Phase**: NOT STARTED ⚠️

All 300 tasks have complete specifications including:
- Exact file paths
- Specific class and method names
- Clear acceptance criteria
- Detailed test requirements
- Implementation details
- Cross-references to decision documents

**Current State**: Documentation and planning only. No code exists. All tasks are TODO and ready for implementation.

**Result**: Implementation specifications are deterministic and unambiguous. Follow the enhanced specifications exactly when building.
