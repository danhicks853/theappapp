# Decision 84: Agent Implementation Strategy

**Status**: ✅ RESOLVED  
**Date Resolved**: Nov 2, 2025  
**Priority**: P0 - BLOCKING  
**Depends On**: Decision 71 (TAS), Decision 83 (Execution Loop)

---

## Context

With infrastructure complete (orchestrator, task queue, workers, DB), we need concrete decisions on how agents actually execute their work. This includes LLM integration patterns, file operations, completion tracking, and output formats.

---

## Decisions

### 1. LLM Integration Pattern
**Decision**: Use structured execution loop from Decision 83

**Implementation**:
- Agents follow: `plan_next_action()` → `execute_action()` → `validate_progress()` loop
- Each iteration calls LLM via `llm_client` for planning
- Execution uses tools (via TAS) or internal logic
- Validation checks progress toward goal

**Rationale**: Already designed in Decision 83, provides structure and observability

---

### 2. File Operations
**Decision**: All file writes go through TAS

**Implementation**:
- Agent requests: `{"tool": "file_write", "path": "/workspace/src/main.py", "content": "..."}`
- TAS validates permission and executes in container
- File reads are NOT gated - any agent can read any project file
- TAS provides audit trail of all writes

**Rationale**: 
- TAS overhead minimal (no LLM calls)
- Maintains security and audit
- Reads ungated for collaboration

---

### 3. Deliverable Completion Tracking
**Decision**: Agent notifies orchestrator when complete via tool call

**Implementation**:
```python
# Agent marks deliverable complete via tool
await self.orchestrator.execute_tool({
    "tool": "mark_deliverable_complete",
    "deliverable_id": "deliv-123",
    "status": "completed",
    "artifacts": ["src/main.py", "tests/test_main.py"]
})
```

**Rationale**: Explicit completion signal, orchestrator can update DB and trigger next tasks

---

### 4. Agent Output Format
**Decision**: Return actual work product in TaskResult

**Implementation**:
```python
class TaskResult:
    status: str  # "completed", "failed", "needs_input"
    output: Dict[str, Any]  # Work product
    iterations_used: int
    artifacts: List[str]  # File paths created/modified

# Examples:
# Code generation task:
output = {
    "type": "code",
    "files": {
        "src/main.py": "<code content>",
        "tests/test_main.py": "<test content>"
    },
    "summary": "Created FastAPI endpoint with tests"
}

# Code review task:
output = {
    "type": "review",
    "findings": [
        {"severity": "high", "file": "main.py", "line": 45, "issue": "..."}
    ],
    "approved": False,
    "feedback": "Need to add error handling"
}
```

**Artifact Storage**:
- Full code/artifacts stored in `task_artifacts` table until GitHub push
- After push, only file paths + commit SHA stored
- Enables rollback and audit

**Rationale**: Next agents read files directly from `/workspace`, but DB preserves history

---

### 5. Error Recovery Strategy
**Decision**: Retry with same agent (already implemented)

**Implementation**:
- TaskExecutor retries failed tasks 2x
- Max 3 attempts total per task
- After failure, task marked failed and error logged
- PhaseManager can decide to create new task or escalate

**Rationale**: Already implemented in TaskExecutor, simple and effective for MVP

---

### 6. MVP Scope
**Decision**: ALL agents must be implemented

**Agents to Implement (11 total)**:
1. ✅ BaseAgent (infrastructure complete)
2. WorkshopperAgent - Requirements gathering
3. BackendDeveloperAgent - Python/API code generation
4. FrontendDeveloperAgent - React/UI code generation  
5. QAEngineerAgent - Test generation and execution
6. SecurityExpertAgent - Security review
7. DevOpsEngineerAgent - Deployment scripts
8. DocumentationExpertAgent - API/user docs
9. UIUXDesignerAgent - Design specs
10. GitHubSpecialistAgent - Git operations
11. ProjectManagerAgent - Coordination

**Rationale**: Complete end-to-end workflow needed for production readiness

---

## Implementation Order

### Phase 1: Core Tools (Week 1)
1. Implement TAS with basic tools (file_write, file_read, mark_complete)
2. Add tool execution to orchestrator
3. Update BaseAgent to use TAS for file ops

### Phase 2: First Agent (Week 1-2)
1. WorkshopperAgent - Requirements gathering
   - Input: Project description
   - Output: User stories, acceptance criteria, tech stack
   - Tools: file_write (for requirements.md)

### Phase 3: Code Generation (Week 2-3)
2. BackendDeveloperAgent - API generation
   - Input: Requirements, existing code
   - Output: Python/FastAPI code, tests
   - Tools: file_write, file_read, execute_command (pytest)

3. FrontendDeveloperAgent - UI generation
   - Input: Requirements, API specs, designs
   - Output: React components, tests
   - Tools: file_write, file_read, execute_command (npm test)

### Phase 4: Quality & Deploy (Week 3-4)
4. QAEngineerAgent - Test generation
5. SecurityExpertAgent - Security review
6. DevOpsEngineerAgent - Deploy scripts
7. DocumentationExpertAgent - Docs generation

### Phase 5: Supporting (Week 4)
8. UIUXDesignerAgent - Design specs
9. GitHubSpecialistAgent - Git operations  
10. ProjectManagerAgent - Coordination

---

## Related Decisions

- **Decision 71**: Tool Access Service - Agent tool execution
- **Decision 83**: Execution Loop - Agent iteration framework
- **Decision 8**: Tool Access Matrix - Agent permissions

---

## Tasks

- [ ] Implement TAS basic tools (file_write, file_read, mark_complete)
- [ ] Update BaseAgent to use TAS for file operations
- [ ] Implement WorkshopperAgent full logic
- [ ] Implement BackendDeveloperAgent full logic
- [ ] Implement FrontendDeveloperAgent full logic
- [ ] Implement remaining 8 agents
- [ ] Add artifact storage to database
- [ ] E2E test with all agents

**Target**: 4 weeks for full agent implementation
