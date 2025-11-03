# Orchestrator Task Instructions - Universal Agent Workflow

## The Problem (Before)

Each agent needed individual system prompt updates:
```
❌ Update Workshopper prompt
❌ Update Backend Dev prompt  
❌ Update Frontend Dev prompt
❌ Update QA Engineer prompt
... 11 agents total!
```

**Issues:**
- Inconsistent instructions across agents
- Hard to maintain
- Easy to forget an agent
- New agents need manual updates

## The Solution (After)

**Orchestrator includes completion workflow in EVERY task:**

```python
# Orchestrator crafts task with built-in workflow
contextualized_goal = (
    f"We've been assigned a project: {project_desc}\n\n"
    f"{deliverable_action}\n\n"
    f"Focus on THIS specific project's needs.\n\n"
    f"WORKFLOW:\n"
    f"1. Complete your work (write files, run tests, etc.)\n"
    f"2. Mark deliverable complete using: deliverable.mark_complete\n"
    f"3. Stop - task done!\n\n"
    f"IMPORTANT: Always mark deliverable complete when finished!"
)
```

## Benefits

### ✅ Single Source of Truth
- One place to maintain instructions (orchestrator)
- Change once, applies to ALL agents
- No inconsistencies

### ✅ Universal Application
- **ALL agents** get the same workflow instructions
- Workshopper, Backend Dev, Frontend Dev, QA, etc.
- Future agents automatically included

### ✅ Maintainability
- Update orchestrator → affects all agents
- No need to touch 11+ agent files
- Easy to add new workflow steps

### ✅ Clear Communication
- Manager (orchestrator) sets expectations
- Workers (agents) follow clear workflow
- Natural organizational hierarchy

## Example Task (Before vs After)

### Before (Vague)
```
Orchestrator → Agent:
"Write comprehensive requirements.md with user stories"

Agent: "Okay, I'll write it... done! Now what?"
*keeps working indefinitely*
```

### After (Clear)
```
Orchestrator → Agent:
"We've been assigned a project: Simple hello world web app

Write comprehensive requirements.md with user stories

WORKFLOW:
1. Complete your work (write files, run tests, etc.)
2. Mark deliverable complete using: deliverable.mark_complete
3. Stop - task done!

IMPORTANT: Always mark deliverable complete when finished!"

Agent: "Got it! Writing file... marking complete... done!"
*stops working*
```

## What Agents See Now

Every agent receives:
```
Goal: We've been assigned a project: {PROJECT_DESCRIPTION}

{DELIVERABLE_ACTION}

Focus on THIS specific project's needs. Use your expertise to create 
high-quality deliverables that match the project requirements.

WORKFLOW:
1. Complete your work (write files, run tests, etc.)
2. Mark deliverable complete using: deliverable.mark_complete
3. Stop - task done!

IMPORTANT: Always mark deliverable complete when your work is finished!
```

## Architecture

```
Orchestrator (Manager)
  ↓
  Creates Task with Universal Instructions
  ↓
  Assigns to Agent (Any Agent Type)
  ↓
Agent Receives Task
  ↓
Agent Reads Goal (includes workflow)
  ↓
Agent Follows Workflow:
  1. Do work
  2. Mark complete
  3. Stop
  ↓
Task Complete! ✅
```

## Implementation

**File:** `backend/services/project_build_service.py`

**Method:** `_create_task_from_deliverable()`

**Lines:** 399-409

All task creation goes through this method, ensuring consistent instructions for every agent.

## Future Workflow Updates

Need to add a new step? Just update the orchestrator:

```python
# Example: Add verification step
contextualized_goal = (
    f"...\n\n"
    f"WORKFLOW:\n"
    f"1. Complete your work\n"
    f"2. Verify your work is correct\n"  # ← New step
    f"3. Mark deliverable complete\n"
    f"4. Stop - task done!\n"
)
```

**Effect:** ALL agents immediately get the new workflow!

## Testing

Run the test and watch ANY agent follow the workflow:

```bash
pytest backend/tests/test_e2e_real_hello_world.py -v -s
```

Expected output:
```
🤖 WORKSHOPPER → ORCHESTRATOR
{
  "description": "Create requirements.md...",
  "tool_name": "file_system",
  "operation": "write",
  ...
}

🤖 WORKSHOPPER → ORCHESTRATOR
{
  "description": "Mark deliverable complete",
  "tool_name": "deliverable",
  "operation": "mark_complete",
  ...
}

✅ Task complete!
```

## Summary

✅ **Orchestrator sets universal workflow** - One place to maintain  
✅ **All agents get same instructions** - Consistent behavior  
✅ **Easy to update** - Change once, affects all  
✅ **Natural hierarchy** - Manager instructs, workers execute  
✅ **Future-proof** - New agents automatically included  

**The orchestrator is now the single source of truth for agent workflows!** 🎯
