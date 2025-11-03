# LLM Logging & Debugging Status

## ✅ What's Already Implemented

### 1. Console Logging (ACTIVE)
**Location:** `backend/services/agent_llm_client.py`

Every LLM call now logs:
- **Full prompt** sent to OpenAI (system + user messages)
- **Complete response** from LLM
- **Parsed action** extracted from response

**Output Format:**
```
================================================================================
🔵 ORCHESTRATOR → LLM (via Agent)
================================================================================
[SYSTEM]
You are a technical product manager...

[USER]
Plan the next action for this task...
--------------------------------------------------------------------------------
================================================================================
🤖 LLM → ORCHESTRATOR (via Agent)
================================================================================
{
  "description": "Analyze requirements...",
  "tool_name": "file_system",
  ...
}
================================================================================
✅ Parsed action: Analyze requirements...
```

### 2. In-Memory Tracking (READY, NOT USED YET)
**Location:** `backend/models/agent_state.py`

```python
@dataclass
class LLMCall:
    """Record of an LLM invocation."""
    prompt: str
    response: str
    tokens_used: int = 0
    cost_usd: float = 0.0
    timestamp: datetime
```

**Storage:** `TaskState.llm_calls: List[LLMCall]`

This exists but we're **not populating it yet**.

### 3. Database Schema (NOT IMPLEMENTED)
Currently, LLM calls are **NOT** persisted to the database.

**What exists:**
- In-memory tracking in TaskState
- Console/log file output

**What doesn't exist:**
- Database table for llm_calls
- Persistent storage across sessions
- Query interface for historical calls

## 🔧 How to Use Current Logging

### View Real-Time During Test
```bash
pytest backend/tests/test_e2e_real_hello_world.py -v -s
```

The `-s` flag shows all print() output including LLM prompts/responses.

### View After Test
```bash
# Check log file
tail -f backend_logs.txt

# Or search for specific patterns
grep "ORCHESTRATOR → LLM" backend_logs.txt
```

## 📊 To Add Database Persistence (Future Task)

### Step 1: Create Database Table
Add to Alembic migration:
```python
op.create_table(
    'llm_calls',
    sa.Column('id', sa.Integer(), primary_key=True),
    sa.Column('project_id', sa.String()),
    sa.Column('task_id', sa.String()),
    sa.Column('agent_id', sa.String()),
    sa.Column('prompt', sa.Text()),
    sa.Column('response', sa.Text()),
    sa.Column('tokens_used', sa.Integer()),
    sa.Column('cost_usd', sa.Float()),
    sa.Column('timestamp', sa.DateTime()),
)
```

### Step 2: Populate LLMCall Objects
In `agent_llm_client.py`, after each LLM call:
```python
llm_call = LLMCall(
    prompt=str(messages),
    response=content,
    tokens_used=response.usage.total_tokens,
    cost_usd=calculate_cost(response),
    timestamp=datetime.now(UTC)
)
# Add to state
task_state.llm_calls.append(llm_call)
```

### Step 3: Persist to Database
In `task_executor.py` after task completion:
```python
# Save all LLM calls to database
for llm_call in task_state.llm_calls:
    db.add(LLMCallRecord(
        project_id=project_id,
        task_id=task.task_id,
        agent_id=agent.agent_id,
        **llm_call.__dict__
    ))
db.commit()
```

### Step 4: Query Interface
```python
# Get all LLM calls for a project
calls = db.query(LLMCallRecord).filter_by(project_id=project_id).all()

# Get calls for specific agent
calls = db.query(LLMCallRecord).filter_by(agent_id=agent_id).all()

# Calculate total cost
total = db.query(func.sum(LLMCallRecord.cost_usd)).filter_by(project_id=project_id).scalar()
```

## 🎯 Current Recommendation

**For Now:** Use console output during development. It's:
- ✅ Immediate
- ✅ Easy to see
- ✅ No database overhead
- ✅ Shows real AI thinking

**For Production:** Add database persistence when you need:
- Historical analysis
- Cost tracking across projects
- Debugging past builds
- Performance analytics

## Debug Tips

### See EVERYTHING
```bash
export LOG_LEVEL=DEBUG
pytest backend/tests/test_e2e_real_hello_world.py -v -s 2>&1 | tee full_output.log
```

### Search Specific LLM Calls
```bash
# Find all prompts
grep -A 20 "ORCHESTRATOR → LLM" full_output.log

# Find all responses  
grep -A 10 "LLM → ORCHESTRATOR" full_output.log

# Count total LLM calls
grep -c "ORCHESTRATOR → LLM" full_output.log
```

### Filter by Agent Type
```bash
# Find workshopper prompts
grep -B 5 "technical product manager" full_output.log

# Find backend dev prompts
grep -B 5 "Python backend developer" full_output.log
```

## Summary

✅ **Logging to console/files:** DONE  
⚠️ **In-memory tracking:** Ready but not used  
❌ **Database persistence:** Not implemented  

For debugging and development, **console output is sufficient**. Add database when you need historical analysis.
