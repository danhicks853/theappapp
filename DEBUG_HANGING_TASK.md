# Debug Hanging Task Issue

## Changes Made to Fix Hanging

### 1. Simplified Workshopper Default Action
**Problem:** LLM call in default case was hanging
**Fix:** Replaced LLM call with simple template-based document generation

### 2. Added Task Execution Timeout  
**Problem:** Tasks could hang indefinitely
**Fix:** Added 60-second timeout to `task_executor.py` with asyncio.wait_for()

## How to Debug if Still Hanging

### Check Logs
```bash
# Look for these log messages:
tail -f backend_logs.txt

# Or check console output for:
- "Executing task {task_id} with agent {agent_id}"
- "Task {task_id} completed successfully"
- "Task {task_id} timed out after 60 seconds"
```

### What to Look For

1. **Task Assignment Log**
   - Should see: `Task Assigned: document to workshopper-xxx`
   - ✅ Means task was assigned

2. **Task Execution Start**
   - Should see: `Executing task xxx with agent workshopper-xxx`
   - ✅ Means agent started working

3. **Task Completion**
   - Should see: `Task xxx completed successfully`
   - ✅ Means task finished
   - Should see: Progress increase from 0%

4. **If Timeout**
   - Will see: `Task xxx timed out after 60 seconds`
   - ❌ Means something is hanging in agent execution

## Common Hang Points

### 1. BaseAgent.run_task() Loop
- Located in: `backend/agents/base_agent.py`
- The iterative execution loop
- Could hang if:
  - `_plan_next_step()` hangs (LLM call)
  - `_execute_action()` hangs (tool execution)
  - Loop condition never becomes false

### 2. LLM Client Calls
- `llm_client.plan_next_action()` 
- Could hang if:
  - OpenAI API is slow/down
  - No timeout on HTTP requests
  - Rate limiting

### 3. Orchestrator Tool Execution
- `orchestrator.execute_tool()`
- Could hang if:
  - File system operations blocked
  - Database operations timeout
  - Tool not implemented

## Quick Test

Run with verbose logging:
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run test
pytest backend/tests/test_e2e_real_hello_world.py -v -s 2>&1 | tee test_output.log
```

## If Timeout Occurs

The timeout will now throw an error after 60 seconds showing:
1. Which task timed out
2. Which agent was executing
3. Stack trace of where it was stuck

Check `test_output.log` for the full error.

## Next Steps if Still Hanging

1. **Increase timeout** (if LLM is legitimately slow)
   - Change `timeout=60.0` to `timeout=120.0` in task_executor.py

2. **Add more logging** in BaseAgent.run_task()
   - Log each step of the execution loop
   - See exactly where it hangs

3. **Mock LLM calls** for initial testing
   - Return dummy responses instantly
   - Verify the flow works without real API

4. **Check OpenAI API key**
   - Make sure it's valid
   - Check rate limits
   - Try a simple API call outside the system
