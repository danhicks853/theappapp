# Container Architecture - Project vs Execution Containers

## The Strategy

### Project Container (Persistent)
- **Purpose:** File storage and workspace
- **Lifetime:** Entire project duration
- **Language:** Python (has all file operations tools)
- **Identifier:** `project_id`
- **Used By:** ALL agents for file operations
- **Location:** `/workspace/` (persistent volume)

### Execution Containers (Ephemeral)
- **Purpose:** Test and run code
- **Lifetime:** Single task or test run
- **Language:** Language-specific (Node, Go, Rust, etc.)
- **Identifier:** `task_id` or `agent_id-exec`
- **Used By:** Individual agents for testing
- **Cleanup:** Destroyed after task completion

## Flow Example: Backend Developer

```
1. Backend Dev needs to write Node.js API
   
2. Agent writes code to PROJECT container
   ↓
   file_system.write(
     container_id=project_id,  ← Project container
     path="api/server.js",
     content="const express = require('express')..."
   )
   ✅ File saved in /workspace/api/server.js

3. Agent wants to TEST the code
   ↓
   Orchestrator creates Node.js execution container
   ↓
   container_mgr.create_container(
     task_id=f"{agent_id}-exec",
     language="node"
   )
   
4. Agent copies file to execution container
   ↓
   Mount project workspace as read-only
   or
   Copy specific files needed for test

5. Agent runs code in Node container
   ↓
   exec_command(
     container_id=f"{agent_id}-exec",
     command="node api/server.js"
   )
   ✅ Tests pass!

6. Agent cleans up execution container
   ↓
   container_mgr.destroy_container(f"{agent_id}-exec")

7. Files remain in PROJECT container
   ✅ /workspace/api/server.js still exists
```

## Container Types

### 1. Project Container (Singleton)
```python
Container ID: project_id (e.g., "proj-abc123")
Image: python:3.11-slim
Purpose: Persistent file storage
Volume: /workspace (project files)
Lifetime: Project start → Project end
Destroyed: Only when project completes/fails
```

**What lives here:**
- All source code files
- Documentation (requirements.md, README.md)
- Configuration files
- Build artifacts
- Any file that needs to persist

### 2. Language Execution Containers (Ephemeral)
```python
Container ID: f"{agent_id}-exec-{language}"
Image: language-specific (node:18, golang:1.21, etc.)
Purpose: Test and execute code
Volume: Read-only mount of /workspace OR copy files
Lifetime: Task start → Task end
Destroyed: After test/execution completes
```

**What runs here:**
- Code execution for testing
- Compilation
- Test suites
- Linting/validation
- Package installation

## Implementation

### File Operations (Always Use Project Container)

```python
# backend/services/tool_access_service.py

async def _execute_file_system_tool(self, operation: str, parameters: Dict):
    project_id = parameters.get("project_id")
    
    # ALWAYS use project container for files
    container_id = project_id
    
    # Ensure project container exists
    if container_id not in container_mgr.active_containers:
        # Create if needed
        await container_mgr.create_container(
            task_id=project_id,
            project_id=project_id,
            language="python"
        )
    
    # All file operations in project container
    if operation == "write":
        await container_mgr.exec_command(
            container_id,  # ← Project container
            write_command
        )
```

### Code Execution (Use Language-Specific Container)

```python
# Example: Backend agent needs to run Node.js code

async def test_nodejs_code(self, code_file: str):
    # 1. Code already saved in PROJECT container
    
    # 2. Create Node execution container
    exec_container_id = f"{self.agent_id}-exec-node"
    result = await self.orchestrator.execute_tool({
        "tool": "container",
        "operation": "create",
        "parameters": {
            "task_id": exec_container_id,
            "project_id": self.project_id,
            "language": "node"
        }
    })
    
    # 3. Mount project workspace (read-only)
    # This happens automatically in create_container
    # Project /workspace is mounted to exec container
    
    # 4. Run tests in exec container
    test_result = await self.orchestrator.execute_tool({
        "tool": "container",
        "operation": "execute",
        "parameters": {
            "task_id": exec_container_id,
            "command": f"node /workspace/{code_file}"
        }
    })
    
    # 5. Clean up exec container
    await self.orchestrator.execute_tool({
        "tool": "container",
        "operation": "destroy",
        "parameters": {
            "task_id": exec_container_id
        }
    })
    
    # 6. Files remain in project container ✅
    return test_result
```

## Volume Mounting Strategy

### Project Container
```yaml
Volumes:
  - project-{project_id}:/workspace  # Persistent named volume
```

### Execution Containers
```yaml
Volumes:
  - project-{project_id}:/workspace:ro  # Read-only mount of project volume
```

This allows:
- ✅ Exec containers can READ all project files
- ✅ Exec containers can RUN code from /workspace
- ❌ Exec containers CANNOT write to /workspace (read-only)
- ✅ Only project container can WRITE files

## Agent Workflow

### Frontend Developer (React)

```
1. Write React component → PROJECT container
   file_system.write("src/App.tsx", code)

2. Create Node exec container for testing
   container.create(language="node")

3. Run npm build in exec container
   container.execute("npm run build")

4. Tests pass? → Files already in project container ✅

5. Destroy exec container
   container.destroy()
```

### QA Engineer

```
1. Read test files from PROJECT container
   file_system.read("tests/api.test.js")

2. Create Node exec container
   container.create(language="node")

3. Run tests in exec container
   container.execute("npm test")

4. Write test report → PROJECT container
   file_system.write("reports/test-results.json", results)

5. Destroy exec container
   container.destroy()
```

### Backend Developer (Python)

```
1. Write FastAPI code → PROJECT container
   file_system.write("api/main.py", code)

2. Can test in PROJECT container (already Python!)
   OR create separate exec container for isolation

3. Run tests
   container.execute("pytest api/")

4. Code already in project container ✅
```

## Benefits

### ✅ Single Source of Truth
- All files in ONE place (project container)
- No file synchronization needed
- No "which container has the latest file?" confusion

### ✅ Resource Efficient
- Exec containers are temporary (destroyed after use)
- Only ONE persistent container per project
- Docker volume handles file persistence

### ✅ Language Flexibility
- Agents can test in ANY language
- Project files accessible to all languages
- No dependency conflicts between languages

### ✅ Clean Separation
- **File Storage:** Project container
- **Code Execution:** Language-specific containers
- Clear responsibilities

### ✅ Easy Debugging
- All files in /workspace of project container
- Can inspect anytime: `docker exec proj-abc123 ls /workspace`
- Persistent across all agent actions

## Container Lifecycle

### Project Start
```bash
1. Create project container
   docker run -d \
     --name proj-abc123 \
     -v proj-abc123-workspace:/workspace \
     python:3.11-slim \
     sleep infinity

✅ Container runs for entire project
✅ /workspace volume persists all files
```

### Agent Execution
```bash
2. Agent needs to test Node.js code
   docker run -d \
     --name backend-dev-1-exec-node \
     -v proj-abc123-workspace:/workspace:ro \
     node:18 \
     sleep 60

3. Agent runs tests
   docker exec backend-dev-1-exec-node node /workspace/api/server.js

4. Agent cleans up
   docker rm -f backend-dev-1-exec-node

✅ Exec container destroyed
✅ Files still in proj-abc123:/workspace
```

### Project End
```bash
5. Project completes
   docker rm -f proj-abc123
   docker volume rm proj-abc123-workspace

✅ All cleaned up
```

## Summary

| Aspect | Project Container | Execution Containers |
|--------|------------------|---------------------|
| **Purpose** | File storage | Code execution/testing |
| **Lifetime** | Entire project | Single task |
| **Language** | Python | Any (Node, Go, Rust, etc.) |
| **Files** | Read/Write | Read-only |
| **Count** | 1 per project | N per agent/task |
| **Destroyed** | At project end | After each task |
| **Identifier** | `project_id` | `{agent_id}-exec-{lang}` |

**Architecture: ONE persistent project container + ephemeral execution containers as needed** 🎯
