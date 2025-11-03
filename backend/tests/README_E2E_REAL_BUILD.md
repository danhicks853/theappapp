# Real End-to-End Build Test

## Overview

`test_e2e_real_hello_world.py` is a **REAL** integration test that builds an actual "Hello World" web application using the complete backend system.

### What's REAL:
- ✅ Real LLM API calls to generate project plan
- ✅ Real agents writing actual code
- ✅ Real MilestoneGenerator creating deliverables
- ✅ Real PhaseManager tracking progress
- ✅ Real Orchestrator delegating tasks
- ✅ Real EventBus streaming events
- ✅ Real human gate approvals (interactive!)
- ✅ Real file generation

### What's MOCKED:
- GitHub operations only (repos, PRs, commits)

---

## Prerequisites

### 1. Database Running
```bash
docker-compose up -d postgres
```

### 2. Run Migrations
```bash
alembic upgrade head
```

### 3. LLM API Key Configured
Set your OpenAI API key (or other LLM provider):
```bash
export OPENAI_API_KEY="your-key-here"
```

### 4. Install Test Dependencies
```bash
pip install pytest pytest-asyncio
```

---

## Running the Test

```bash
# From project root
pytest backend/tests/test_e2e_real_hello_world.py -v -s --tb=short
```

**Flags:**
- `-v` = Verbose output
- `-s` = Show print statements (required for interactive gates!)
- `--tb=short` = Short traceback on errors

---

## What To Expect

### 1. Cost Warning
```
⚠️  WARNING: This test makes REAL LLM API calls!
⚠️  This will cost money and take time!

Type 'yes' to proceed with REAL build:
```

Type `yes` to continue.

### 2. Build Starts
The system will:
1. Generate milestones using LLM
2. Create deliverables and phases
3. Register all 11 agents
4. Start build loop

### 3. Real-Time Progress
You'll see events streaming:
```
🎯 Project Created: proj-abc123
🚀 Build Started (status: planning)
📋 Phase Started: workshopping
🤖 Agent Started: backend_dev
📝 Task Assigned: implementation to backend_dev
✍️  Code Generated: frontend/index.html (45 lines)
📄 File Created: backend/app.py
🧪 Test Generated: tests/test_app.py
✅ Test Passed: test_hello_world
```

### 4. Human Gates (INTERACTIVE!)

When a gate is triggered, you'll see:
```
================================================================================
🚧 HUMAN GATE REQUIRED
================================================================================
Gate: code_review
Phase: implementation
Description: Review generated code before proceeding

Context:
  files_changed: 3
  agent: backend_dev

--------------------------------------------------------------------------------
Type 'y' to APPROVE, 'n [feedback]' to REJECT, or 'auto' to auto-approve all
--------------------------------------------------------------------------------
Your response:
```

**Options:**
- `y` - Approve the gate
- `n` - Reject with no feedback
- `n needs refactoring` - Reject with feedback  
- `auto` - Auto-approve this and all remaining gates

### 5. Build Progress Updates
Every 10 seconds:
```
⏱️  Status: building | Phase: implementation | Progress: 34.2%
```

### 6. Build Complete
```
================================================================================
BUILD COMPLETE
================================================================================
Status: completed
Final Phase: deployment
Progress: 100.0%

📊 Events Summary:
   EventType.PROJECT_CREATED: 1
   EventType.AGENT_STARTED: 11
   EventType.CODE_GENERATED: 8
   EventType.TEST_PASSED: 12
   EventType.PHASE_COMPLETED: 6
   EventType.PROJECT_COMPLETED: 1

🚧 Gates Summary:
   Total gates: 4
   Approved: 4
   Rejected: 0

📦 GitHub Operations (mocked):
   Repos created: 1
   PRs created: 2
   Commits made: 5

📁 Generated Files:
   Output directory: /tmp/pytest-xyz/hello_world_output

✅ REAL BUILD TEST PASSED!
```

---

## Expected Duration

- **With auto-approve**: 2-5 minutes
- **With manual gates**: 5-15 minutes (depends on response time)

---

## Expected Cost

Rough estimate based on GPT-4:
- Milestone generation: ~$0.05-0.10
- Agent code generation: ~$0.20-0.50
- Code review: ~$0.10-0.20

**Total: ~$0.35-0.80 per test run**

---

## What Gets Built

The test builds a simple web app:

### Frontend (`frontend/index.html`)
- HTML page with a button
- Modern CSS styling (gradient background, nice button)
- JavaScript that shows popup on click

### Backend (`backend/app.py`)
- Flask API with `/greeting` endpoint
- Returns JSON: `{"message": "Hello World!"}`
- CORS enabled

### Tests (`tests/`)
- Frontend test: Button click behavior
- Backend test: API endpoint returns correct response
- Integration test: Full flow

### Configuration
- `requirements.txt` - Python dependencies
- `README.md` - How to run the project
- `.gitignore` - Standard ignores

---

## Troubleshooting

### Test Hangs
- Check database is running
- Check LLM API key is valid
- Look for gate prompts (you need to respond!)

### Build Fails
- Check error in event stream
- Review gate rejection feedback
- Check agent logs

### No Files Generated
- Files are written to temp directory
- Check `output_dir` in test output
- In production, would write to project workspace

---

## Verifying the Output

After test passes, you can:

1. **Find the output directory** (shown in test output)
2. **Navigate to it**
3. **Run the generated app**:
   ```bash
   cd /path/to/output
   pip install -r requirements.txt
   python backend/app.py
   ```
4. **Open `frontend/index.html` in browser**
5. **Click the button** - should see "Hello World!" popup!

---

## Marks/Tags

This test has special pytest marks:

- `@pytest.mark.asyncio` - Async test
- `@pytest.mark.integration` - Integration test
- `@pytest.mark.slow` - Takes time to run

Run only this test:
```bash
pytest -m "integration and slow" -v -s
```

Skip slow tests:
```bash
pytest -m "not slow"
```

---

## Notes

- This is a **real** test - it costs money and time!
- Use it to verify the complete backend pipeline works
- Great for demos - shows the whole system in action
- Can be adapted for other project types (change the description)
- Gates are educational - shows human-in-the-loop workflow

---

## Example Session

```bash
$ pytest backend/tests/test_e2e_real_hello_world.py -v -s

================================================================================
REAL END-TO-END BUILD TEST: Hello World Web App
================================================================================

⚠️  WARNING: This test makes REAL LLM API calls!
⚠️  This will cost money and take time!

Type 'yes' to proceed with REAL build: yes

================================================================================
Starting REAL build...
================================================================================

📝 Submitting build request...
   Description: Simple hello world web app
   Requirements: Button that shows popup

✅ Build started: proj-a1b2c3d4

================================================================================
MONITORING BUILD PROGRESS
================================================================================

🎯 Project Created: proj-a1b2c3d4
🚀 Build Started (status: planning)

[... events stream ...]

================================================================================
🚧 HUMAN GATE REQUIRED
================================================================================
Gate: milestone_complete
Phase: workshopping
Description: Review project plan

Type 'y' to APPROVE, 'n [feedback]' to REJECT, or 'auto' to auto-approve all
--------------------------------------------------------------------------------
Your response: auto
✅ Auto-approve enabled

[... more events ...]

⏱️  Status: building | Phase: implementation | Progress: 45.3%

[... continues until complete ...]

✅ REAL BUILD TEST PASSED!
```

---

Enjoy watching your AI system build a complete application! 🚀
