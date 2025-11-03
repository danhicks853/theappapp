# Cost Tracking & Metadata Collection - IMPLEMENTED ✅

## What's Now Active

### 1. Clean Logging Output
**Shows:** Only USER prompts (system prompts hidden - you know those from config)

**Example Output:**
```
================================================================================
🔵 ORCHESTRATOR → LLM
================================================================================
Plan the next action for this task.

Goal: Build a simple hello world web app

Current Progress:
- Step: 1/20
- Progress Score: 0.00
...
================================================================================
🤖 LLM → ORCHESTRATOR
================================================================================
{
  "description": "Analyze project requirements",
  "tool_name": "file_system",
  ...
}
--------------------------------------------------------------------------------
💰 Tokens: 1247 | Cost: $0.000468
================================================================================
```

### 2. Metadata Collection (ACTIVE)
Every LLM call now tracks:
- ✅ **User prompt** (what was asked)
- ✅ **LLM response** (what it said)
- ✅ **Tokens used** (from OpenAI response.usage)
- ✅ **Cost in USD** (calculated based on model)
- ✅ **Timestamp** (when it happened)

**Storage:** `TaskState.llm_calls` - List of LLMCall objects

### 3. Cost Calculation (ACTIVE)
Pricing table (2024 rates):
```python
"gpt-4o": $0.00625 / 1K tokens (average)
"gpt-4o-mini": $0.000375 / 1K tokens (average)
"gpt-4": $0.045 / 1K tokens (average)
"gpt-3.5-turbo": $0.0015 / 1K tokens (average)
```

Automatically calculates cost per call and displays in output.

## How to Access Metadata

### During Execution
Metadata is automatically collected in `task_state.llm_calls[]`

### After Task Completion
Access from the BaseAgent's Step history:
```python
for step in task_state.steps_history:
    total_tokens = step.tokens_used  # Sum of all LLM calls in this step
    total_cost = step.cost_usd  # Sum of all costs
```

### Current Session Total
```python
# Total tokens across all LLM calls
total_tokens = sum(call.tokens_used for call in task_state.llm_calls)

# Total cost
total_cost = sum(call.cost_usd for call in task_state.llm_calls)
```

## Console Output Example

```
================================================================================
🔵 ORCHESTRATOR → LLM
================================================================================
Plan the next action for this task.
Goal: Build a simple hello world web app
Current Progress:
- Step: 1/20
Respond with a JSON object with action details...
================================================================================

[... OpenAI API call happens ...]

================================================================================
🤖 LLM → ORCHESTRATOR
================================================================================
{
  "description": "Create requirements document",
  "tool_name": "file_system",
  "operation": "write",
  "parameters": {"path": "requirements.md", "content": "..."},
  "reasoning": "First, I need to document the requirements..."
}
--------------------------------------------------------------------------------
💰 Tokens: 1247 | Cost: $0.000468
================================================================================
✅ Parsed action: Create requirements document
```

## Cost Tracking Features

### Per-Call Tracking ✅
- Each LLM call shows its token count and cost
- Stored in LLMCall object for later analysis

### Per-Task Tracking ✅
- `task_state.llm_calls` contains all calls for the task
- Easy to sum up: `sum(call.cost_usd for call in task_state.llm_calls)`

### Per-Step Tracking ✅
- Each Step in history has `tokens_used` and `cost_usd` aggregated
- `state.steps_history[-1].cost_usd` = cost of last step

### Project-Level Tracking (Ready to implement)
When you add database persistence:
```python
# Query all LLM calls for a project
calls = db.query(LLMCallRecord).filter_by(project_id=project_id).all()

# Total project cost
total = db.query(func.sum(LLMCallRecord.cost_usd)).filter_by(project_id=project_id).scalar()

# Cost breakdown by agent
costs_by_agent = db.query(
    LLMCallRecord.agent_id,
    func.sum(LLMCallRecord.cost_usd)
).group_by(LLMCallRecord.agent_id).all()
```

## What You See vs What's Tracked

### Console Output (Visible):
- ✅ User prompts only
- ✅ LLM responses
- ✅ Token count
- ✅ Cost per call

### Hidden But Tracked:
- System prompts (stored in LLMCall.prompt but not shown)
- Timestamp
- Model used
- Full message history

## Test It

```bash
pytest backend/tests/test_e2e_real_hello_world.py -v -s
```

You'll see:
1. Clean prompts (no system noise)
2. Real-time cost tracking
3. Token usage per call
4. All metadata collected for later reporting

## Future: Add to Database

When ready, just add persistence:
1. Create `llm_calls` table in Alembic migration
2. Save `task_state.llm_calls` to database after each task
3. Query for reports and analytics

The data structure is ready - just needs DB persistence layer!

## Summary

✅ **Clean logging** - Only user prompts shown  
✅ **Metadata collection** - All data captured  
✅ **Cost calculation** - Automatic per model  
✅ **Real-time display** - See costs as they happen  
✅ **Storage ready** - In TaskState for later DB persistence  

**You can now track and report on LLM costs!** 💰
