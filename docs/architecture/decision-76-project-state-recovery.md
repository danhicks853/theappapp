# Decision 76: Project State Recovery System

**Status**: ✅ COMPLETE  
**Date Resolved**: November 1, 2025  
**Priority**: P1 - HIGH  
**Depends On**: Decision 5 (state management), Database schema

---

## Context

Decision 5 specifies "Complete recovery capability" for system reliability. The system needs to handle orchestrator crashes, server restarts, and unexpected failures without losing project progress.

---

## Decision Summary

### Core Approach
- **File-based checkpointing**: Persistent volumes preserve all written files
- **Database state tracking**: Log current task, agent, and progress
- **Automatic recovery**: Orchestrator resumes on startup
- **LLM-based evaluation**: Orchestrator reviews state and decides next action

---

## 1. Checkpointing Strategy

### File System as Primary Checkpoint
- **All project files on persistent volumes** (Docker volumes, not ephemeral containers)
- Files are the source of truth for project state
- No separate checkpoint files needed

### What Gets Persisted
- Source code files
- Configuration files
- Test files
- Documentation
- Build artifacts
- `.git` directory (if using Git)

**Rationale**: Files already represent the complete project state. No need for additional checkpoint mechanism.

---

## 2. Database State Tracking

### Database Schema: `project_state` Table

```sql
CREATE TABLE project_state (
    id SERIAL PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id),
    current_task_id VARCHAR(100),
    current_agent_id VARCHAR(100),
    last_action TEXT,
    status VARCHAR(50) NOT NULL,  -- 'active', 'paused', 'completed', 'failed'
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB  -- Additional context
);

CREATE INDEX idx_project_state_project ON project_state(project_id);
CREATE INDEX idx_project_state_status ON project_state(status);
```

### State Fields

| Field | Purpose | Example |
|-------|---------|---------|
| `project_id` | Which project | `550e8400-e29b-41d4-a716-446655440000` |
| `current_task_id` | Task being worked on | `task_implement_auth` |
| `current_agent_id` | Agent assigned to task | `backend_dev` |
| `last_action` | Last action taken | `Created file auth.py` |
| `status` | Project status | `active`, `paused`, `completed` |
| `metadata` | Additional context | `{"files_modified": 3, "tests_passing": true}` |

### State Updates

```python
async def update_project_state(
    project_id: str,
    task_id: str,
    agent_id: str,
    action: str,
    status: str = "active"
):
    """Update project state after each significant action"""
    await db.execute(
        """
        INSERT INTO project_state 
            (project_id, current_task_id, current_agent_id, last_action, status)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (project_id) 
        DO UPDATE SET
            current_task_id = $2,
            current_agent_id = $3,
            last_action = $4,
            status = $5,
            updated_at = NOW()
        """,
        project_id, task_id, agent_id, action, status
    )
```

---

## 3. Recovery Trigger

### Automatic Recovery on Startup

**When**: Orchestrator starts up (after crash or restart)

**Process**:
1. Query database for all projects with `status = 'active'`
2. For each active project, initiate recovery process
3. Log recovery attempts for monitoring

```python
class Orchestrator:
    async def startup(self):
        """Orchestrator startup routine"""
        logger.info("Orchestrator starting up...")
        
        # Find all active projects
        active_projects = await db.fetch(
            "SELECT * FROM project_state WHERE status = 'active'"
        )
        
        logger.info(f"Found {len(active_projects)} active projects to recover")
        
        # Recover each project
        for project_state in active_projects:
            await self.recover_project(project_state)
        
        logger.info("Recovery complete, orchestrator ready")
```

### Manual Recovery Option

**When**: User clicks "Resume Project" button in UI

**Use case**: User paused project manually, wants to resume later

```python
@router.post("/api/projects/{project_id}/resume")
async def resume_project(project_id: str):
    """Manually resume a paused project"""
    project_state = await db.fetchrow(
        "SELECT * FROM project_state WHERE project_id = $1",
        project_id
    )
    
    if project_state['status'] == 'paused':
        await orchestrator.recover_project(project_state)
        return {"success": True, "message": "Project resumed"}
    else:
        return {"success": False, "message": "Project not paused"}
```

---

## 4. Recovery Process

### Orchestrator LLM-Based Recovery

**Approach**: Orchestrator reviews state and decides next action using LLM reasoning

```python
async def recover_project(self, project_state: dict):
    """Recover a project after interruption"""
    
    project_id = project_state['project_id']
    
    logger.info(f"Recovering project {project_id}")
    
    # 1. Load project context
    project = await self.load_project(project_id)
    
    # 2. Scan file system to assess current state
    file_state = await self.scan_project_files(project_id)
    
    # 3. Load task history
    task_history = await self.load_task_history(project_id)
    
    # 4. Ask orchestrator LLM to evaluate state and decide next action
    recovery_decision = await self.orchestrator_llm.evaluate_recovery(
        project_goal=project['goal'],
        current_task=project_state['current_task_id'],
        last_action=project_state['last_action'],
        file_state=file_state,
        task_history=task_history
    )
    
    # 5. Execute recovery decision
    if recovery_decision.action == "continue_task":
        # Continue with current task
        await self.assign_task(
            project_id=project_id,
            task_id=project_state['current_task_id'],
            agent_id=project_state['current_agent_id']
        )
    elif recovery_decision.action == "restart_task":
        # Restart current task from beginning
        await self.restart_task(
            project_id=project_id,
            task_id=project_state['current_task_id']
        )
    elif recovery_decision.action == "next_task":
        # Move to next task (current task appears complete)
        await self.assign_next_task(project_id)
    elif recovery_decision.action == "human_review":
        # Unclear state, need human input
        await self.trigger_gate(
            project_id=project_id,
            reason="Recovery requires human review",
            details=recovery_decision.reasoning
        )
    
    logger.info(f"Recovery decision for {project_id}: {recovery_decision.action}")
```

### File State Scanning

```python
async def scan_project_files(self, project_id: str) -> dict:
    """Scan project files to assess current state"""
    
    project_path = self.get_project_path(project_id)
    
    # Count files by type
    file_counts = {
        'source_files': 0,
        'test_files': 0,
        'config_files': 0,
        'total_files': 0
    }
    
    # List recently modified files
    recent_files = []
    
    for root, dirs, files in os.walk(project_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_counts['total_files'] += 1
            
            if file.endswith(('.py', '.js', '.ts', '.java')):
                file_counts['source_files'] += 1
            elif 'test' in file.lower():
                file_counts['test_files'] += 1
            elif file in ['package.json', 'requirements.txt', 'pom.xml']:
                file_counts['config_files'] += 1
            
            # Track recently modified (last 1 hour)
            mtime = os.path.getmtime(file_path)
            if time.time() - mtime < 3600:
                recent_files.append({
                    'path': file_path,
                    'modified': datetime.fromtimestamp(mtime)
                })
    
    return {
        'file_counts': file_counts,
        'recent_files': recent_files,
        'last_modified': max([f['modified'] for f in recent_files]) if recent_files else None
    }
```

### Orchestrator LLM Recovery Evaluation

```python
async def evaluate_recovery(
    self,
    project_goal: str,
    current_task: str,
    last_action: str,
    file_state: dict,
    task_history: list
) -> RecoveryDecision:
    """Evaluate project state and decide recovery action"""
    
    prompt = f"""
    You are recovering a project after an interruption.
    
    Project Goal: {project_goal}
    Current Task: {current_task}
    Last Action: {last_action}
    
    File State:
    - Total files: {file_state['file_counts']['total_files']}
    - Source files: {file_state['file_counts']['source_files']}
    - Test files: {file_state['file_counts']['test_files']}
    - Recently modified: {len(file_state['recent_files'])} files
    
    Task History: {len(task_history)} tasks completed
    
    Based on this state, decide the best recovery action:
    1. "continue_task" - Continue with current task (appears incomplete)
    2. "restart_task" - Restart current task from beginning (partial work unclear)
    3. "next_task" - Move to next task (current task appears complete)
    4. "human_review" - Unclear state, need human input
    
    Provide your decision and reasoning.
    """
    
    response = await self.llm.generate(prompt)
    
    return RecoveryDecision(
        action=response.action,
        reasoning=response.reasoning
    )
```

---

## 5. Partial Task Handling

### Orchestrator Evaluates Partial Work

**Approach**: Orchestrator LLM decides whether to continue or restart based on file state

**Decision Criteria**:
- **Continue**: Files show clear progress toward task goal
- **Restart**: Partial work is incomplete or unclear
- **Next**: Task appears complete despite not being marked as such

**Example Scenarios**:

| Scenario | Last Action | File State | Decision |
|----------|-------------|------------|----------|
| Auth implementation | "Created auth.py" | auth.py exists, 50 lines | Continue |
| Test writing | "Writing tests..." | test file empty | Restart |
| API endpoint | "Completed endpoint" | All files present, tests pass | Next task |
| Unknown state | "Working on..." | No recent changes | Human review |

---

## 6. Recovery Scenarios

### Scenario 1: Orchestrator Crash Mid-Task

**State**:
- Database: `current_task = "implement_auth"`, `agent = "backend_dev"`
- Files: `auth.py` partially written (100 lines)

**Recovery**:
1. Orchestrator scans files, sees partial `auth.py`
2. LLM evaluates: "Auth implementation in progress, continue"
3. Assigns task back to backend_dev with context: "Continue auth implementation"

### Scenario 2: Server Restart During Tests

**State**:
- Database: `current_task = "run_tests"`, `agent = "qa_engineer"`
- Files: All source files complete, tests written

**Recovery**:
1. Orchestrator scans files, sees complete implementation
2. LLM evaluates: "Tests appear ready, continue test execution"
3. Assigns task back to qa_engineer: "Run test suite"

### Scenario 3: Long Pause (User Stopped Project)

**State**:
- Database: `status = "paused"`, `current_task = "deploy"`
- Files: All code complete, ready for deployment

**Recovery**:
1. User clicks "Resume Project"
2. Orchestrator scans files, sees deployment-ready state
3. LLM evaluates: "Ready for deployment, continue"
4. Assigns task to devops_agent: "Deploy application"

### Scenario 4: Unclear State

**State**:
- Database: `current_task = "refactor_code"`, `agent = "backend_dev"`
- Files: Many files modified, unclear if refactor complete

**Recovery**:
1. Orchestrator scans files, sees extensive changes
2. LLM evaluates: "Refactor state unclear, need human review"
3. Triggers gate: "Project recovery requires human review"
4. Human reviews state, decides next action

---

## 7. Transaction Boundaries

### What Constitutes a "Transaction"?

**Atomic Units**:
- Single file write (file created/modified)
- Single test run
- Single agent action (e.g., "run linter")

**Non-Atomic**:
- Multi-file refactoring (may be interrupted mid-way)
- Long-running test suites (may be interrupted)
- Multi-step agent tasks (may be interrupted)

### No Explicit Transactions

**Rationale**: 
- File system operations are atomic at OS level
- Database state updates are atomic (single INSERT/UPDATE)
- No need for distributed transactions or rollback mechanisms
- Orchestrator LLM handles partial state intelligently

**Acceptable Risk**: 
- Partial work may need to be restarted
- Orchestrator can detect and handle this scenario
- Cost of occasional restart < complexity of transaction system

---

## Implementation Details

### State Update Frequency

**Update database state after**:
- Task assignment
- Task completion
- Significant file changes (every N files or every M minutes)
- Agent errors or failures
- Gate triggers

```python
class Orchestrator:
    async def assign_task(self, project_id: str, task_id: str, agent_id: str):
        """Assign task to agent"""
        # Update state before starting
        await self.update_project_state(
            project_id=project_id,
            task_id=task_id,
            agent_id=agent_id,
            action=f"Assigned {task_id} to {agent_id}",
            status="active"
        )
        
        # Execute task
        await self.execute_task(project_id, task_id, agent_id)
    
    async def complete_task(self, project_id: str, task_id: str):
        """Mark task as complete"""
        await self.update_project_state(
            project_id=project_id,
            task_id=task_id,
            agent_id=None,
            action=f"Completed {task_id}",
            status="active"
        )
```

### Persistent Volume Configuration

```yaml
# Docker Compose example
services:
  orchestrator:
    volumes:
      - project_data:/app/projects  # Persistent volume for project files
      
volumes:
  project_data:
    driver: local
```

---

## Testing Strategy

### Recovery Tests

```python
def test_recovery_after_crash():
    """Test recovery after orchestrator crash"""
    # 1. Start project
    project_id = orchestrator.create_project("Test Project")
    
    # 2. Simulate work
    orchestrator.assign_task(project_id, "task_1", "backend_dev")
    
    # 3. Simulate crash (kill orchestrator)
    orchestrator.shutdown()
    
    # 4. Restart orchestrator
    orchestrator = Orchestrator()
    orchestrator.startup()
    
    # 5. Verify recovery
    assert orchestrator.is_project_active(project_id)
    assert orchestrator.get_current_task(project_id) == "task_1"

def test_recovery_with_partial_work():
    """Test recovery with partial file writes"""
    # 1. Start task
    orchestrator.assign_task(project_id, "implement_auth", "backend_dev")
    
    # 2. Write partial file
    write_file("auth.py", "# Partial implementation\n")
    
    # 3. Crash and restart
    orchestrator.shutdown()
    orchestrator = Orchestrator()
    orchestrator.startup()
    
    # 4. Verify orchestrator decides to continue (not restart)
    recovery_decision = orchestrator.get_recovery_decision(project_id)
    assert recovery_decision.action == "continue_task"
```

---

## Rationale

### Why File-Based Checkpointing?
- Files already represent complete project state
- No additional checkpoint mechanism needed
- Persistent volumes ensure durability
- Simple and reliable

### Why LLM-Based Recovery?
- Can intelligently evaluate partial work
- Handles ambiguous states gracefully
- No need for complex recovery rules
- Adapts to different project types

### Why Automatic Recovery?
- Minimizes downtime
- No manual intervention needed for common cases
- User experience: seamless continuation
- Falls back to human review for unclear cases

---

## Related Decisions

- **Decision 5**: State management architecture
- **Decision 67**: Orchestrator LLM integration
- **Decision 74**: Loop detection (recovery may trigger loops)

---

## Tasks Created

### Phase 1: Core Recovery (Week 4)
- [ ] **Task 1.4.9**: Create `project_state` table and state tracking
- [ ] **Task 1.4.10**: Implement automatic recovery on orchestrator startup
- [ ] **Task 1.4.11**: Implement file state scanning
- [ ] **Task 1.4.12**: Implement orchestrator LLM recovery evaluation

### Phase 6: Testing (Week 12)
- [ ] **Task 6.6.12**: Create recovery test suite
- [ ] **Task 6.6.13**: Test recovery scenarios (crash, restart, pause/resume)

---

## Approval

**Approved By**: User  
**Date**: November 1, 2025

---

*Last Updated: November 1, 2025*
