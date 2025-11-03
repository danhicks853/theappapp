# Agent Flow Architecture Audit

## Executive Summary
**Status: ❌ CRITICAL GAPS - System is procedural, not agent-driven**

The current implementation has a **hardcoded procedural build loop** instead of the **orchestrator-driven agent collaboration** described in the ideal flow.

---

## Ideal Flow (User's Vision)

```
Project Start
  ↓
Orch → GitHub: Initialize repo
GitHub → Orch: Done
  ↓
Orch → Workshopper: Plan scope
Workshopper → Orch: Done, file is scope.md
  ↓
Orch reads scope.md
Orch → PM: Review scope.md, create project plan
PM → Orch: Done, file is plan.md
  ↓
Orch reads plan.md, extracts deliverables
Orch → Backend Dev: Build steps X, Y, Z with tests
Backend Dev → Orch: Built (summary + files)
  ↓
Orch → QA: Backend built, run tests until 90% coverage
QA → Orch: All good, 90% coverage
  ↓
Orch → Frontend: Backend ready, API contract = XYZ
Frontend → Orch: Complete
  ↓
Orch → UI/UX: Frontend complete, ensure good UX
UI/UX → Orch: Looks great
  ↓
Orch → PM: Product complete, verify all steps done
PM → Orch: Looks good
  ↓
Orch → GitHub: PR and merge
GitHub → Orch: Done
  ↓
PROJECT COMPLETE
```

---

## Current Implementation (What's Wrong)

### 1. ❌ ProjectBuildService.start_build() - Hardcoded Planning

**Location:** `backend/services/project_build_service.py:236-271`

**What it does NOW:**
```python
# Lines 237-240: Directly calls milestone_generator
project_plan = await self.milestone_generator.generate_project_plan(
    project_id=project_id,
    project_description=description
)

# Lines 242-264: Converts plan to deliverables
milestones_dict = []
for phase in project_plan.phases:
    for milestone in phase.milestones:
        # Create deliverables...

# Line 271: Initializes phase_manager with plan
await phase_manager.initialize(milestones_dict)
```

**What it SHOULD do:**
```python
# Initialize orchestrator + agents
orchestrator = Orchestrator(...)
agents = await agent_factory.create_and_register_all_agents(...)

# Create FIRST task: Workshopper scope planning
first_task = Task(
    task_id="scope-planning",
    description="Analyze project requirements and create scope document",
    agent_type=AgentType.WORKSHOPPER,
    metadata={"project_description": description}
)
orchestrator.enqueue_task(first_task)

# EXIT - Let orchestrator workflow take over
return project_id
```

**Gap:** ProjectBuildService acts as "project manager" instead of letting PM agent do it.

---

### 2. ❌ Build Loop - Hardcoded Deliverable Processing

**Location:** `backend/services/project_build_service.py:323-380`

**What it does NOW:**
```python
while True:
    # Get deliverables from pre-generated plan
    deliverables = await phase_manager.get_pending_deliverables()
    
    # Create tasks from deliverables in a loop
    for deliverable in deliverables:
        await self._create_task_from_deliverable(
            orchestrator, deliverable, project_id
        )
    
    # Wait for queue to be empty
    while not orchestrator.task_queue.empty():
        await asyncio.sleep(0.5)
```

**What it SHOULD do:**
```python
# NO BUILD LOOP!
# Orchestrator workflow handles everything:
# - Agent completes task
# - Orchestrator reads output
# - Orchestrator decides next task
# - Orchestrator enqueues next task
# - Repeat
```

**Gap:** Entire build loop is unnecessary - orchestrator should drive the workflow.

---

### 3. ❌ No Orchestrator Decision Logic

**Location:** `backend/services/orchestrator.py` (MISSING)

**What EXISTS:**
- `enqueue_task()` - Adds task to queue
- `dequeue_task()` - Removes task from queue
- `_intelligently_assign_agent_type()` - Assigns agent to task
- `_analyze_question_for_specialists()` - Keyword matching

**What's MISSING:**
```python
async def on_task_completed(self, task: Task, result: TaskResult):
    """
    CRITICAL: Orchestrator must decide what happens next!
    
    1. Read agent output files
    2. Extract context/information
    3. Decide next action:
       - Create new task for next agent
       - Request clarification
       - Escalate to human
       - Mark project complete
    4. Pass context to next agent
    """
    
    # Example: Workshopper completed scope
    if task.agent_type == AgentType.WORKSHOPPER:
        # Read scope.md
        scope_content = await self._read_agent_output("scope.md")
        
        # Create PM task with context
        pm_task = Task(
            description=f"Review scope and create project plan\n\nScope:\n{scope_content}",
            agent_type=AgentType.PROJECT_MANAGER,
            metadata={"previous_task": task.task_id, "scope_file": "scope.md"}
        )
        self.enqueue_task(pm_task)
    
    # Example: PM completed plan
    elif task.agent_type == AgentType.PROJECT_MANAGER:
        # Read plan.md
        plan_content = await self._read_agent_output("plan.md")
        
        # Extract deliverables from plan
        deliverables = self._parse_plan_deliverables(plan_content)
        
        # Create tasks for backend dev
        for deliverable in deliverables:
            backend_task = Task(
                description=f"Implement: {deliverable}",
                agent_type=AgentType.BACKEND_DEVELOPER,
                metadata={"deliverable": deliverable}
            )
            self.enqueue_task(backend_task)
```

**Gap:** No workflow orchestration - just queue management.

---

### 4. ❌ No Context Passing Between Agents

**Location:** `backend/services/task_executor.py:237-274`

**What it does NOW:**
```python
async def _handle_task_result(self, task: Task, result: TaskResult):
    task.status = TaskStatus.COMPLETED
    self.task_results[task.task_id] = result
    
    # Just mark deliverable complete - NO orchestrator decision
    await self._mark_deliverable_complete(deliverable_id, result)
```

**What it SHOULD do:**
```python
async def _handle_task_result(self, task: Task, result: TaskResult):
    # Store result
    self.task_results[task.task_id] = result
    
    # CRITICAL: Notify orchestrator to make decision
    await self.orchestrator.on_task_completed(task, result)
```

**Gap:** TaskExecutor marks deliverable complete but never tells orchestrator to decide next steps.

---

### 5. ❌ Agents Don't See Each Other's Work

**Location:** Agent prompt construction (all agents)

**What happens NOW:**
- Agent gets task description
- Agent executes task
- Agent returns result
- **NO visibility of previous agents' outputs**

**What SHOULD happen:**
- Agent gets task description
- **Agent sees relevant context from previous agents**
- Example: "Backend Dev completed API with contract XYZ. Build frontend to consume it."
- Agent has full context to make informed decisions

**Gap:** Each agent works in isolation without collaboration context.

---

### 6. ❌ No Agent Output Reading

**Location:** MISSING everywhere

**What's MISSING:**
```python
class Orchestrator:
    async def _read_agent_output(self, filename: str) -> str:
        """Read file that agent created."""
        # Use TAS to read from project container
        result = await self.tas_client.execute_tool(
            tool_name="file_system",
            operation="read",
            parameters={"path": filename, "project_id": self.project_id}
        )
        return result.get("content", "")
    
    async def _parse_plan_deliverables(self, plan_content: str) -> List[Dict]:
        """Parse PM's plan.md to extract deliverables."""
        # Use LLM to intelligently parse the plan
        prompt = f"Extract deliverables from this plan:\n\n{plan_content}"
        response = await self.llm_client.query(prompt)
        return response.deliverables
```

**Gap:** Orchestrator never reads what agents produce.

---

### 7. ❌ Phase Transitions Are Hardcoded

**Location:** `backend/services/project_build_service.py:343-351`

**What it does NOW:**
```python
if not deliverables:
    # Phase complete, transition
    transitioned = await phase_manager.try_phase_transition()
```

**What it SHOULD do:**
- PM agent decides when to transition phases
- Orch asks PM: "Are we ready for next phase?"
- PM reviews all work and says yes/no

**Gap:** Phase manager decides instead of PM agent.

---

### 8. ❌ Project Completion Detection

**Location:** `backend/services/project_build_service.py:335-337`

**What it does NOW:**
```python
if phase_manager.is_complete():
    await self._handle_build_complete(project_id)
    break
```

**What it SHOULD do:**
```python
# Orch → PM: "Is project complete?"
# PM → Orch: "Yes, all deliverables validated"
# Orch → GitHub: "Create PR and merge"
# GitHub → Orch: "Done"
# Orch: "Project complete"
```

**Gap:** PhaseManager decides completion instead of PM + GitHub workflow.

---

### 9. ❌ No GitHub Integration in Workflow

**Location:** GitHub agent exists but not used in workflow

**What SHOULD happen:**
1. Project starts → Orch → GitHub: "Init repo"
2. After each major step → Orch → GitHub: "Commit + PR"
3. After PR review → Orch → GitHub: "Merge"
4. Project complete → Orch → GitHub: "Final merge"

**Gap:** GitHub agent exists but never called by orchestrator workflow.

---

## Required Changes

### Priority 1: Orchestrator Workflow Engine

**File:** `backend/services/orchestrator.py`

**Add:**
```python
async def on_task_completed(self, task: Task, result: TaskResult):
    """Core workflow decision logic."""
    
async def _read_agent_output(self, filename: str) -> str:
    """Read agent output files."""
    
async def _extract_context_for_next_agent(self, task: Task, result: TaskResult) -> Dict:
    """Extract relevant context from completed task."""
    
async def _create_next_tasks(self, completed_task: Task, context: Dict):
    """Decide and create next tasks based on completed work."""
```

### Priority 2: Remove Build Loop

**File:** `backend/services/project_build_service.py`

**Remove:**
- Lines 323-380: `_run_build_loop()`
- Lines 236-271: Direct `milestone_generator` call
- Phase manager initialization with hardcoded plan

**Replace with:**
- Create initial Workshopper task
- Exit and let orchestrator workflow take over

### Priority 3: Context Passing

**File:** `backend/services/task_executor.py`

**Modify `_handle_task_result`:**
```python
async def _handle_task_result(self, task: Task, result: TaskResult):
    self.task_results[task.task_id] = result
    
    # CRITICAL: Let orchestrator decide next steps
    await self.orchestrator.on_task_completed(task, result)
```

### Priority 4: Agent Prompts Include Context

**Files:** All agent classes

**Modify task execution to include:**
- Previous agents' outputs
- Relevant files from project
- API contracts, test results, etc.

---

## Gap Summary

| Component | Current State | Required State | Priority |
|-----------|---------------|----------------|----------|
| **Project Planning** | Hardcoded in ProjectBuildService | PM agent with LLM | P1 |
| **Build Loop** | Procedural deliverable processing | Orchestrator-driven workflow | P1 |
| **Orchestrator Logic** | Queue management only | Workflow decision engine | P1 |
| **Context Passing** | None | Agent sees previous work | P2 |
| **Output Reading** | Never reads agent files | Reads and parses outputs | P1 |
| **Phase Transitions** | PhaseManager decides | PM agent decides | P2 |
| **Completion** | PhaseManager.is_complete() | PM + GitHub workflow | P2 |
| **GitHub Integration** | Agent exists, not used | Used throughout workflow | P2 |

---

## Recommended Implementation Order

### Phase 1: Core Orchestrator Workflow
1. Add `Orchestrator.on_task_completed()`
2. Add `Orchestrator._read_agent_output()`
3. Implement basic workflow: Workshopper → PM → Dev

### Phase 2: Remove Build Loop
1. Modify `ProjectBuildService.start_build()` to only initialize
2. Create first Workshopper task
3. Let orchestrator workflow handle everything else

### Phase 3: Context Passing
1. Orchestrator reads agent outputs
2. Passes relevant context to next agent
3. Agents see previous work in their prompts

### Phase 4: Full Multi-Agent Flow
1. Integrate GitHub agent into workflow
2. PM agent manages phase transitions
3. PM agent validates project completion

---

## Test Strategy

### Unit Tests Needed
- `test_orchestrator_workflow_decision()` - Orch decides next task
- `test_orchestrator_reads_agent_output()` - Orch reads files
- `test_context_passed_to_next_agent()` - Context flows

### Integration Tests Needed
- `test_workshopper_to_pm_flow()` - First two agents
- `test_full_agent_collaboration()` - Complete workflow
- `test_github_integration()` - GitHub in loop

### E2E Tests Needed
- `test_hello_world_full_flow()` - Complete build with all agents

---

## Conclusion

**The system is currently 20% agent-driven, 80% procedural.**

To achieve the ideal multi-agent architecture:
1. ✅ Agents exist and work correctly
2. ✅ Orchestrator can assign tasks intelligently
3. ❌ **Orchestrator doesn't drive workflow (CRITICAL)**
4. ❌ **No context passing between agents (CRITICAL)**
5. ❌ **Hardcoded build loop instead of agent collaboration (CRITICAL)**

**Estimated effort:** 2-3 days to implement core workflow engine.
