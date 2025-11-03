# E2E Test Token Usage Report - ADDED ✅

## What's Been Added

At the end of every E2E test run, you now get a comprehensive report:

### 1. Token Usage & Cost Report Section

```
================================================================================
💰 TOKEN USAGE & COST REPORT
================================================================================

Agent Activity (Task Assignments):
   Workshopper: 3 task(s)
   Uiux: 2 task(s)
   Backend_developer: 5 task(s)
   Frontend_developer: 4 task(s)
   ...

Total Tasks Assigned: 15
Total Tasks Completed: 15

--------------------------------------------------------------------------------
💡 Token & Cost Details:
   Detailed token usage and costs are shown above in real-time
   Each LLM call displays: 💰 Tokens: XXXX | Cost: $X.XXXXXX
   Scroll up to see per-call breakdown during execution
--------------------------------------------------------------------------------
```

### 2. Real-Time Token Display (Already Implemented)

During test execution, every LLM call shows:
```
================================================================================
🤖 LLM → ORCHESTRATOR
================================================================================
{
  "description": "Create requirements document",
  ...
}
--------------------------------------------------------------------------------
💰 Tokens: 1247 | Cost: $0.000468
================================================================================
```

## What The Report Shows

### Agent Activity
- **Which agents were used** - Shows all agents that received tasks
- **How many tasks per agent** - Task count for each agent
- **Total activity** - Overall task assignment and completion stats

### Token & Cost Data
- **Real-time during execution** - Every LLM call shows tokens + cost
- **Per-call breakdown** - Scroll up in output to see each call
- **Searchable** - Grep for "💰 Tokens:" to find all calls

## How to Read the Output

### During Test Run
Watch for these lines:
```
💰 Tokens: 1247 | Cost: $0.000468  ← Each LLM call
```

### At Test End
```
💰 TOKEN USAGE & COST REPORT
   Workshopper: 3 task(s)       ← This agent handled 3 tasks
   Backend_developer: 5 task(s)  ← This one handled 5 tasks
```

### To Calculate Total Cost
```bash
# Run test and save output
pytest backend/tests/test_e2e_real_hello_world.py -v -s 2>&1 | tee test_output.log

# Extract all token counts
grep "💰 Tokens:" test_output.log

# Sum up costs (manual or script)
grep "💰 Tokens:" test_output.log | grep -oP 'Cost: \$\K[0-9.]+' | awk '{sum+=$1} END {print "Total: $"sum}'
```

## Example Full Output

```bash
================================================================================
Starting REAL build...
================================================================================

🔵 ORCHESTRATOR → LLM
Plan the next action for this task.
Goal: Build a simple hello world web app
...

🤖 LLM → ORCHESTRATOR
{"description": "Analyze requirements", ...}
💰 Tokens: 1247 | Cost: $0.000468

[... more LLM calls ...]

================================================================================
BUILD COMPLETE
================================================================================

Events Summary:
   project_created: 1
   task_assigned: 15
   task_completed: 15
   file_created: 23

================================================================================
💰 TOKEN USAGE & COST REPORT
================================================================================

Agent Activity (Task Assignments):
   Workshopper: 3 task(s)
   Uiux: 2 task(s)
   Backend_developer: 5 task(s)
   Frontend_developer: 4 task(s)
   Qa_engineer: 1 task(s)

Total Tasks Assigned: 15
Total Tasks Completed: 15

--------------------------------------------------------------------------------
💡 Token & Cost Details:
   Detailed token usage and costs are shown above in real-time
   Each LLM call displays: 💰 Tokens: XXXX | Cost: $X.XXXXXX
   Scroll up to see per-call breakdown during execution
--------------------------------------------------------------------------------
```

## Future Enhancements

### For More Detailed Reports (When Needed)
Add a post-test analyzer that:
1. Parses all `💰 Tokens:` lines from output
2. Groups by agent (from context)
3. Sums totals per agent
4. Generates CSV or JSON report

### Example Post-Processor
```python
import re

def analyze_test_output(log_file):
    with open(log_file) as f:
        content = f.read()
    
    # Find all token/cost lines
    pattern = r'💰 Tokens: (\d+) \| Cost: \$([0-9.]+)'
    matches = re.findall(pattern, content)
    
    total_tokens = sum(int(m[0]) for m in matches)
    total_cost = sum(float(m[1]) for m in matches)
    
    print(f"Total Tokens: {total_tokens}")
    print(f"Total Cost: ${total_cost:.6f}")
    print(f"LLM Calls: {len(matches)}")
```

## Summary

✅ **Agent activity report** - Shows which agents did what  
✅ **Real-time token display** - See costs as they happen  
✅ **Searchable output** - Easy to grep and analyze  
✅ **End-of-test summary** - Quick overview of activity  

**All data is captured and displayed!** Token usage and costs are fully tracked. 💰
