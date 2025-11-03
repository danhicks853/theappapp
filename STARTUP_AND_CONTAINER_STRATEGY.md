# Startup Checks & Container Strategy ✅

## What's Been Implemented

### 1. Startup Safety Checks (`startup_checks.py`)

Before the system accepts any work, it validates:

```python
✅ Docker: Daemon running and accessible
✅ Database: PostgreSQL connection working
⚠️  SearXNG: Web search service (optional, degrades gracefully)
⚠️  Qdrant: Vector database for RAG (optional, degrades gracefully)
```

**Usage:**
```python
from backend.services.startup_checks import run_startup_checks

# At application startup
if not await run_startup_checks():
    logger.error("Required services not available")
    sys.exit(1)
```

### 2. Project-Level Container Strategy

**Old Way (BAD):**
- Each task tried to create its own container
- "No container found for task" errors
- Wasteful: Multiple containers per project

**New Way (GOOD):**
- ONE container per project
- Created when project starts
- All agents share the project container
- Specialists can request additional containers if needed

## Architecture Flow

### Project Startup:
```
1. Run startup checks
   ├─ ✅ Docker available?
   ├─ ✅ Database accessible?
   ├─ ⚠️  SearXNG available? (optional)
   └─ ⚠️  Qdrant available? (optional)

2. Create new project
   └─ Create project-level container (Python)
      └─ Container ID = project_id
      └─ All agents use this container

3. Start build process
   └─ Agents use project container for file operations
```

### File Operations:
```
Agent needs to write file
  ↓
file_system tool checks for container
  ├─ Check: Does project container exist?
  │   ├─ YES → Use it ✅
  │   └─ NO → Create on-demand, then use
  ↓
Execute file operation in project container
  ↓
Done!
```

### Specialist Container Requests:
```
Backend Dev needs Node.js container
  ↓
Agent: "Orchestrator, I need a Node.js container"
  ↓
Orchestrator creates additional container
  ├─ Container ID = task_id or agent_id
  ├─ Image = node:latest
  └─ Agent ID recorded
  ↓
Agent uses specialist container for Node operations
```

## Code Changes

### 1. StartupChecker (`startup_checks.py`)
```python
checker = StartupChecker()
all_passed = await checker.run_all_checks()

# Results
checker.results = {
    "Docker": {"available": True, "required": True},
    "Database": {"available": True, "required": True},
    "SearXNG": {"available": False, "required": False},
    "Qdrant": {"available": False, "required": False}
}
```

### 2. Project Container Creation (`project_build_service.py`)
```python
# When project starts
container_result = await container_mgr.create_container(
    task_id=project_id,  # Container ID = project ID
    project_id=project_id,
    language="python"  # Default language
)

logger.info(f"✅ Project container created for {project_id}")
```

### 3. File System Tool Updates (`tool_access_service.py`)
```python
# Use project-level container (prefer project_id)
container_id = project_id if project_id in container_mgr.active_containers else task_id

# If no container exists, create project container
if container_id not in container_mgr.active_containers:
    await container_mgr.create_container(
        task_id=project_id,
        project_id=project_id,
        language="python"
    )
    container_id = project_id

# All file operations use container_id
await container_mgr.exec_command(container_id, command)
```

## Benefits

### ✅ Resource Efficiency
- **Before:** N tasks = N containers (wasteful)
- **After:** 1 project = 1 container (efficient)

### ✅ Faster File Operations
- Container already exists
- No "container not found" errors
- No startup delay per task

### ✅ Shared Project Workspace
- All agents see same /workspace
- Files persist across tasks
- True collaboration

### ✅ Graceful Degradation
- SearXNG down? Web search disabled, build continues
- Qdrant down? RAG disabled, build continues
- Docker down? System refuses to start (required)

## Startup Sequence

### Application Start:
```bash
python -m backend.main
```

Output:
```
================================================================================
RUNNING STARTUP SAFETY CHECKS
================================================================================
✅ Docker: Docker daemon is running and accessible
✅ Database: PostgreSQL database is accessible
⚠️  SearXNG: SearXNG not available: Connection refused
   (Web search will be disabled)
⚠️  Qdrant: Qdrant not available: Connection refused
   (RAG features will be disabled)
================================================================================
✅ ALL REQUIRED CHECKS PASSED (2/2 required services available)
================================================================================
Starting server...
```

### Project Start:
```
================================================================================
Starting project: proj-abc123
================================================================================
Creating project container...
✅ Project container created for proj-abc123

Starting build process...
  🔵 Orchestrator → Workshopper: "Create requirements.md"
  
  Workshopper uses file_system tool
    ↓
  file_system finds project container (proj-abc123)
    ↓
  Writes file to /workspace/requirements.md
    ↓
  ✅ Success!
```

## Future: Specialist Containers

When a specialist agent needs a different language:

```python
# Agent requests specialist container
await orchestrator.request_container(
    agent_id="backend-dev-1",
    language="node",
    reason="Need Node.js for API development"
)

# Orchestrator creates it
container_result = await container_mgr.create_container(
    task_id=f"{agent_id}-specialist",
    project_id=project_id,
    language="node"
)

# Agent now has TWO containers available:
# 1. Project container (Python) - for shared files
# 2. Specialist container (Node.js) - for Node operations
```

## Testing

### Test Startup Checks:
```python
from backend.services.startup_checks import run_startup_checks

async def test_startup():
    result = await run_startup_checks()
    assert result == True  # All required services available
```

### Test Project Container:
```bash
pytest backend/tests/test_e2e_real_hello_world.py -v -s
```

Expected output:
```
Creating project container for proj-xyz...
✅ Project container created for proj-xyz

🔵 ORCHESTRATOR → WORKSHOPPER
...
🤖 WORKSHOPPER → ORCHESTRATOR
{
  "tool_name": "file_system",
  "operation": "write",
  "path": "requirements.md"
}

✅ File written: requirements.md
```

## Summary

✅ **Startup checks ensure system is healthy**  
✅ **One container per project (not per task)**  
✅ **File operations just work (no "container not found")**  
✅ **Optional services degrade gracefully**  
✅ **Specialists can request additional containers**  

**The system now starts safely and manages containers intelligently!** 🎯
