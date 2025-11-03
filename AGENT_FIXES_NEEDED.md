# Critical Agent Fixes Needed

## Problem Summary
1. **Agents return dicts instead of Result objects** → causes `'dict' has no attribute 'attempt'` error
2. **Agents don't mark deliverables complete** → causes 0% progress loop
3. **Task assignment is hardcoded** → should use orchestrator's LLM instead

## Fix Required for ALL 10 Agents

### Files to Fix:
1. ✅ `backend/agents/workshopper_agent.py` (DONE)
2. ❌ `backend/agents/backend_dev_agent.py`
3. ❌ `backend/agents/frontend_dev_agent.py`
4. ❌ `backend/agents/qa_engineer_agent.py`
5. ❌ `backend/agents/devops_engineer_agent.py`
6. ❌ `backend/agents/security_expert_agent.py`
7. ❌ `backend/agents/documentation_expert_agent.py`
8. ❌ `backend/agents/uiux_designer_agent.py`
9. ❌ `backend/agents/project_manager_agent.py`
10. ❌ `backend/agents/github_specialist_agent.py`

### Changes Needed Per Agent:

#### 1. Add Result Import
```python
from backend.models.agent_state import Result
```

#### 2. Change ALL return statements in `_execute_internal_action()`
```python
# BEFORE (WRONG):
return {
    "status": "completed",
    "output": "some output",
    "files_created": ["file.py"]
}

# AFTER (CORRECT):
return Result(
    success=True,
    output="some output",
    metadata={"files_created": ["file.py"]}
)
```

#### 3. Mark Deliverable Complete (CRITICAL FOR PROGRESS)
Before returning Result, agents should mark their deliverable complete:
```python
# At end of _execute_internal_action, before return:
await self.orchestrator.execute_tool({
    "agent_id": self.agent_id,
    "agent_type": self.agent_type,
    "tool": "deliverable",
    "operation": "mark_complete",
    "parameters": {
        "deliverable_id": state.task_id,  # or get from state
        "status": "completed",
        "artifacts": files_created_list
    }
})

return Result(success=True, output=output, metadata={...})
```

## Task Assignment Fix

### Current (WRONG): Hardcoded mapping
```python
# project_build_service.py line 334
def _map_deliverable_to_agent_type(self, deliverable):
    if "backend" in type:
        return AgentType.BACKEND_DEVELOPER
    # etc...
```

### Needed (CORRECT): Orchestrator decides via LLM
```python
# Orchestrator should use LLM to decide which agent
# based on deliverable description, phase, context
```

## Priority Order:
1. **FIX ALL AGENTS TO RETURN Result** (prevents crashes)
2. **ADD DELIVERABLE MARKING** (fixes 0% loop)
3. **REMOVE HARDCODED TASK ASSIGNMENT** (lets orchestrator/LLM decide)
