# Testing & Quality Standards

**Purpose**: Define quality standards and testing requirements for all implementation  
**Status**: Complete and Ready to Use  
**Compliance**: MANDATORY for all development work

---

## 📖 Quick Reference for LLMs

### MUST READ BEFORE ANY CODING
2. **[`testing_philosophy.md`](testing_philosophy.md)** - MANDATORY testing approach

**DO NOT SKIP THESE DOCUMENTS**

---

## 📂 Files in This Directory

### 1. testing_philosophy.md
**Purpose**: Comprehensive testing strategy and requirements  
**When to Use**: When designing tests for any component  

**Contains**:
- **Testing Hierarchy** - Unit → Integration → E2E
- **Test-Driven Development** - Write tests BEFORE code
- **Coverage Requirements** - 100% for all code
- **LLM-Specific Testing** - How to test AI components
- **Test Organization** - Directory structure and naming
- **Quality Standards** - What makes a good test

**Key Principles**:
- Tests define correctness
- Write failing tests first
- Never modify tests to pass
- 100% coverage is mandatory
- LLM components need special testing

---

## 🎯 How to Use These Standards

### Before Starting Any Task

**Complete This Checklist**:
```
[ ] Read development_guardrails.md completely
[ ] Understand testing_philosophy.md approach
[ ] Found task in ../planning/development_tracker.md
[ ] Read referenced decision document
[ ] Reviewed previous task documentation
[ ] Identified test scenarios
[ ] Planned documentation structure
```

---

### During Implementation

**Follow This Process**:
```
1. Write failing tests FIRST (TDD)
2. Implement to satisfy tests
3. Verify 100% test coverage
4. Document as you build
5. Run all tests (must pass 100%)
6. Update tracker status
7. Create implementation docs
```

---

### After Implementation

**Verify Compliance**:
```
[ ] All tests passing (100%)
[ ] Test coverage 100%
[ ] No tests modified to pass
[ ] Implementation matches decision
[ ] Documentation complete
[ ] Tracker updated accurately
[ ] Pre-task checklist completed
```

---

## ⚠️ Critical Rules (NEVER VIOLATE)

### Absolute Requirements

1. **NEVER skip unit tests** - All code must have tests
2. **NEVER modify tests to pass** - Fix code, not tests
3. **NEVER implement extra features** - Stay in decision scope
4. **NEVER update tracker prematurely** - Only when complete
5. **NEVER skip documentation** - Document everything
6. **NEVER ignore decision details** - Follow exactly

### Warning Signs (STOP if you think these)

- ❌ "This test is wrong" → The test is right, fix the code
- ❌ "I'll skip this test" → All tests are mandatory
- ❌ "This would be nice to add" → Stay within scope
- ❌ "I'll document later" → Document as you build
- ❌ "Good enough for now" → Quality is non-negotiable

---

## 📊 Quality Metrics

### Required Standards

**Test Coverage**:
- Line coverage: 100%
- Branch coverage: 100%
- Function coverage: 100%

**Test Results**:
- All tests passing: 100%
- No failures: 0
- No skipped tests: 0

**Decision Alignment**:
- Requirements implemented: 100%
- Deviations from spec: 0
- Extra features added: 0

**Documentation**:
- Implementation docs: Complete
- Cross-references: All added
- Previous work referenced: Yes

---

## 🧪 Testing Levels

### Unit Tests (Most Important)
- Test individual functions/methods
- Mock all external dependencies
- Fast execution (<1ms per test)
- 100% coverage of logic

### Integration Tests
- Test component interactions
- Real database (test instance)
- Validate data flow
- Check error handling

### E2E Tests
- Test complete user workflows
- Real browser (Playwright)
- Full stack validation
- User perspective

### LLM-Specific Tests
- Prompt validation
- Response structure checking
- AI-assisted evaluation
- Quality rubrics
- A/B testing

---

## 📋 Pre-Task Checklist (From Guardrails)

### Task Validation
- [ ] Task exists in enhanced tracker
- [ ] Decision reference identified
- [ ] Enhancement specification reviewed
- [ ] File path confirmed
- [ ] Class/method names identified

### Document Cross-Reference
- [ ] Phase decision document read
- [ ] Enhanced development tracker verified
- [ ] Testing philosophy reviewed
- [ ] Previous implementations checked
- [ ] Task clarity checklist reviewed

### Test Preparation
- [ ] Unit test scenarios identified
- [ ] Integration test scope defined
- [ ] E2E test relevance confirmed
- [ ] Testing tools selected

### Documentation Requirements
- [ ] Previous task docs reviewed
- [ ] Documentation structure planned
- [ ] Implementation details planned
- [ ] Cross-reference strategy defined

---

## 🚫 Blocking Conditions

### Cannot Proceed If:

- ❌ Task not found in tracker
- ❌ Decision reference unclear
- ❌ Any test failing
- ❌ Test coverage < 100%
- ❌ Implementation deviates from decision
- ❌ Tracker not updated
- ❌ Documentation missing
- ❌ No cross-references added
- ❌ Previous docs not referenced

**Action**: Stop immediately, fix the issue, then proceed.

---

## 📈 Continuous Compliance

### Throughout Development

**Always**:
- Reference documents for every decision
- Write tests before implementation
- Verify all tests pass
- Update tracker accurately
- Document all work

**Never**:
- Assume requirements
- Skip tests
- Modify tests to pass
- Add features outside scope
- Rush to completion

---

## 🎓 Development Philosophy

### Quality Over Speed
- Correctness is more important than velocity
- 100% test coverage is non-negotiable
- Documentation is as critical as code
- Standards exist to ensure success

### Test-Driven Development
- Write failing tests first
- Implement to satisfy tests
- Tests define correctness
- Code adapts to tests, not vice versa

### Specification-Driven Implementation
- Enhanced specifications are the source of truth
- Follow file paths exactly
- Use exact class/method names
- Meet all acceptance criteria

### Transparency & Traceability
- Document decisions as you make them
- Cross-reference all related work
- Build upon previous implementations
- Create clear linkages

---

## 🔍 Compliance Verification

### Self-Audit Questions (After Each Task)

1. **Decision Compliance**: Did I implement exactly what the decision specified?
2. **Testing Compliance**: Did I follow the testing hierarchy (unit → integration → e2e)?
3. **Quality Compliance**: Are ALL tests passing without modification?
4. **Tracker Compliance**: Is the tracker updated accurately?
5. **Documentation Compliance**: Is comprehensive documentation created and cross-referenced?
6. **Reference Compliance**: Did I refer back to previous task documentation when needed?

**If ANY answer is "NO"**: Stop, identify the gap, fix the issue, then continue.

---

## 📞 When You Need Help

### Escalation Triggers

**Ask user for guidance when**:
- Decision requirements are unclear
- Test failures cannot be resolved
- Implementation conflicts with other tasks
- Tracker needs updates beyond your authority
- Any guardrail cannot be followed

**DO NOT**:
- Proceed with uncertainty
- Make assumptions about requirements
- Compromise on quality standards
- Skip compliance checks

---

## 🎯 Success Criteria

### Every Task Must Achieve

✅ All tests written and passing (100%)  
✅ Test coverage at 100% (line, branch, function)  
✅ Implementation matches decision exactly  
✅ No deviations from specification  
✅ Documentation complete and cross-referenced  
✅ Tracker updated accurately  
✅ All pre-task checklist items completed  
✅ All compliance verification passed  

**Result**: Production-ready, maintainable, well-tested code.

---

## 📖 Related Documentation

### Primary References
- **Task Specs**: `../planning/development_tracker.md`
- **Decisions**: `../architecture/decision-XX-*.md`
- **Task Standards**: `../planning/task_clarity_checklist.md`

### Navigation
- **Main Index**: `../INDEX.md`
- **Architecture Catalog**: `../architecture/README.md`
- **Planning Overview**: `../planning/README.md`

---

**Last Updated**: November 1, 2025  
**Status**: Complete and Mandatory  
**Compliance**: Required for ALL development work  
**No Exceptions**: These standards apply to every task, every time
