# Decision 78: Docker Container Lifecycle Management

**Status**: ✅ COMPLETE  
**Date Resolved**: November 1, 2025  
**Priority**: P1 - HIGH  
**Depends On**: Decision 14 (sandboxing), Decision 16 (multi-project)

---

## Context

Decision 14 specifies Docker-based sandboxing for code execution. The system needs to manage container lifecycle for multiple languages while maintaining fast execution and proper resource cleanup.

---

## Decision Summary

### Core Approach
- **On-demand creation**: Create container when task starts
- **Task-scoped lifetime**: Container lives for full task duration
- **Immediate cleanup**: Destroy container when task completes
- **Pre-built golden images**: Images built during development, not runtime
- **No resource limits**: Trust agents not to abuse resources
- **No monitoring**: Containers are ephemeral, no health checks needed

---

## 1. Container Lifecycle

### Creation Timing

**One container per task**:
- Container created when agent starts a code execution task
- Container stays alive for entire task duration
- Agent can execute multiple code snippets in same container
- Container destroyed immediately when task completes

### Lifecycle Flow

```
Task Starts
    ↓
Create Container (from golden image)
    ↓
Mount project files (persistent volume)
    ↓
Agent executes code (multiple times if needed)
    ↓
    ├─ Run tests
    ├─ See failure
    ├─ Modify code
    ├─ Run tests again
    └─ (all in same container)
    ↓
Task Completes
    ↓
Destroy Container
    ↓
Files persist on volume
```

### Example Task Execution

```python
# Agent: Backend Developer
# Task: Implement authentication

# 1. Container created
container = await container_manager.create_container(
    project_id="project_123",
    language="python"
)

# 2. Agent works in container (multiple operations)
await container.exec("pip install flask-jwt-extended")
await container.exec("python -m pytest tests/test_auth.py")  # Fails
# Agent modifies code
await container.exec("python -m pytest tests/test_auth.py")  # Passes

# 3. Task complete, destroy container
await container_manager.destroy_container(container.id)

# 4. Files remain on persistent volume
```

---

## 2. Golden Images

### Supported Languages

**Extended language set**:
1. **Python** (`helix-python:latest`)
2. **Node.js** (`helix-nodejs:latest`)
3. **Java** (`helix-java:latest`)
4. **Go** (`helix-go:latest`)
5. **Ruby** (`helix-ruby:latest`)
6. **PHP** (`helix-php:latest`)
7. **.NET** (`helix-dotnet:latest`)
8. **PowerShell** (`helix-powershell:latest`) - for Windows machine development

### Image Contents

Each golden image includes:
- Language runtime and toolchain
- Common dependencies and libraries
- Build tools (make, cmake, etc.)
- Testing frameworks
- Linters and formatters
- Version control tools (git)
- Text editors (vim, nano)

### Image Management

**External management**:
- Images built and maintained outside the system
- System pulls pre-built images from registry
- No runtime image building
- Updates handled externally (manual or CI/CD)

**Image Registry**:
```yaml
# docker-compose.yml or deployment config
services:
  orchestrator:
    environment:
      DOCKER_REGISTRY: "registry.example.com/helix"
      PYTHON_IMAGE: "helix-python:latest"
      NODEJS_IMAGE: "helix-nodejs:latest"
      JAVA_IMAGE: "helix-java:latest"
      GO_IMAGE: "helix-go:latest"
      RUBY_IMAGE: "helix-ruby:latest"
      PHP_IMAGE: "helix-php:latest"
      DOTNET_IMAGE: "helix-dotnet:latest"
      POWERSHELL_IMAGE: "helix-powershell:latest"
```

---

## 3. Container Manager Implementation

### Container Manager Service

```python
class ContainerManager:
    """Manages Docker container lifecycle"""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.active_containers = {}  # task_id -> container
        
        # Image mappings
        self.images = {
            'python': os.getenv('PYTHON_IMAGE', 'helix-python:latest'),
            'nodejs': os.getenv('NODEJS_IMAGE', 'helix-nodejs:latest'),
            'java': os.getenv('JAVA_IMAGE', 'helix-java:latest'),
            'go': os.getenv('GO_IMAGE', 'helix-go:latest'),
            'ruby': os.getenv('RUBY_IMAGE', 'helix-ruby:latest'),
            'php': os.getenv('PHP_IMAGE', 'helix-php:latest'),
            'dotnet': os.getenv('DOTNET_IMAGE', 'helix-dotnet:latest'),
            'powershell': os.getenv('POWERSHELL_IMAGE', 'helix-powershell:latest')
        }
    
    async def create_container(
        self,
        project_id: str,
        task_id: str,
        language: str
    ) -> Container:
        """Create container for task execution"""
        
        # Get image for language
        image = self.images.get(language)
        if not image:
            raise ValueError(f"Unsupported language: {language}")
        
        # Get project path
        project_path = self.get_project_path(project_id)
        
        # Create container
        container = self.docker_client.containers.run(
            image=image,
            detach=True,
            volumes={
                project_path: {
                    'bind': '/workspace',
                    'mode': 'rw'
                }
            },
            working_dir='/workspace',
            network_mode='bridge',
            remove=False,  # Manual cleanup
            stdin_open=True,
            tty=True
        )
        
        # Track active container
        self.active_containers[task_id] = container
        
        logger.info(
            f"Created container {container.id[:12]} for task {task_id} "
            f"(language: {language})"
        )
        
        return container
    
    async def destroy_container(self, task_id: str):
        """Destroy container after task completion"""
        
        container = self.active_containers.get(task_id)
        if not container:
            logger.warning(f"No container found for task {task_id}")
            return
        
        try:
            # Stop and remove container
            container.stop(timeout=5)
            container.remove()
            
            logger.info(f"Destroyed container for task {task_id}")
        except Exception as e:
            logger.error(f"Error destroying container: {e}")
        finally:
            # Remove from tracking
            del self.active_containers[task_id]
    
    async def exec_command(
        self,
        task_id: str,
        command: str
    ) -> dict:
        """Execute command in container"""
        
        container = self.active_containers.get(task_id)
        if not container:
            raise ValueError(f"No active container for task {task_id}")
        
        # Execute command
        exit_code, output = container.exec_run(
            cmd=command,
            workdir='/workspace',
            demux=True  # Separate stdout/stderr
        )
        
        stdout, stderr = output
        
        return {
            'exit_code': exit_code,
            'stdout': stdout.decode('utf-8') if stdout else '',
            'stderr': stderr.decode('utf-8') if stderr else ''
        }
    
    def get_project_path(self, project_id: str) -> str:
        """Get absolute path to project files"""
        return os.path.abspath(f"/app/projects/{project_id}")
```

---

## 4. Agent Integration

### Agent Code Execution

```python
class Agent:
    def __init__(self, container_manager: ContainerManager):
        self.container_manager = container_manager
        self.current_container = None
    
    async def start_task(
        self,
        project_id: str,
        task_id: str,
        language: str
    ):
        """Start task and create container"""
        
        # Create container for this task
        self.current_container = await self.container_manager.create_container(
            project_id=project_id,
            task_id=task_id,
            language=language
        )
        
        logger.info(f"Agent started task {task_id} with container")
    
    async def execute_code(self, command: str) -> dict:
        """Execute code in current container"""
        
        if not self.current_container:
            raise RuntimeError("No active container")
        
        result = await self.container_manager.exec_command(
            task_id=self.current_task_id,
            command=command
        )
        
        return result
    
    async def complete_task(self, task_id: str):
        """Complete task and destroy container"""
        
        # Destroy container
        await self.container_manager.destroy_container(task_id)
        
        self.current_container = None
        
        logger.info(f"Agent completed task {task_id}, container destroyed")
```

### Multi-Operation Task Example

```python
# Agent: Backend Developer
# Task: Implement and test authentication

async def implement_auth_task(agent: Agent):
    # 1. Start task (creates container)
    await agent.start_task(
        project_id="project_123",
        task_id="task_auth",
        language="python"
    )
    
    # 2. Install dependencies
    result = await agent.execute_code("pip install flask-jwt-extended")
    
    # 3. Run initial tests (expect failures)
    result = await agent.execute_code("python -m pytest tests/test_auth.py")
    # Output: 5 failed, 0 passed
    
    # 4. Agent modifies code (writes to /workspace via persistent volume)
    # ... agent makes changes ...
    
    # 5. Run tests again
    result = await agent.execute_code("python -m pytest tests/test_auth.py")
    # Output: 5 passed, 0 failed
    
    # 6. Run linter
    result = await agent.execute_code("flake8 auth.py")
    
    # 7. Complete task (destroys container)
    await agent.complete_task("task_auth")
    
    # Files remain on persistent volume
```

---

## 5. Resource Management

### No Resource Limits

**Approach**: Trust agents not to abuse resources

**Rationale**:
- Agents are LLM-powered, not user-provided code
- Tasks are time-bounded (orchestrator timeout)
- Simpler implementation
- Better performance (no artificial constraints)

**Acceptable Risk**:
- Runaway processes possible but unlikely
- Orchestrator timeout provides safety net
- Can add limits later if needed

### Cleanup Strategy

**Immediate cleanup after task**:
- No container pooling or reuse
- Fresh container for each task
- Prevents state leakage between tasks
- Simplifies debugging (no shared state)

**Cleanup on failure**:
```python
async def execute_task_with_cleanup(agent: Agent, task: Task):
    """Execute task with guaranteed cleanup"""
    try:
        await agent.start_task(task.project_id, task.id, task.language)
        await agent.execute_task(task)
        await agent.complete_task(task.id)
    except Exception as e:
        logger.error(f"Task failed: {e}")
        # Ensure cleanup even on failure
        await container_manager.destroy_container(task.id)
        raise
```

---

## 6. Multi-Language Support

### Language Selection

**Project-level language**:
- User selects primary language during project creation
- Stored in project metadata
- Used for all code execution tasks in that project

```python
# Project creation
project = {
    'id': 'project_123',
    'name': 'My API',
    'language': 'python',  # Primary language
    'description': '...'
}

# Task execution uses project language
container = await container_manager.create_container(
    project_id=project['id'],
    task_id='task_1',
    language=project['language']
)
```

### Multi-Language Projects

**Future enhancement** (not implemented initially):
- Support multiple languages per project
- Agent specifies language per task
- Example: Python backend + Node.js frontend

**Current approach**: Single language per project

---

## 7. Container Networking

### Network Isolation

**Bridge network**:
- Containers on isolated bridge network
- Can access external internet (for package installation)
- Cannot access host network directly
- Cannot communicate with other containers

### Port Mapping

**No port mapping by default**:
- Containers don't expose ports
- Code execution only (no running servers in containers)
- If needed, orchestrator can create container with port mapping

**Future enhancement**: Support running dev servers in containers for testing

---

## 8. Performance Considerations

### Fast Container Creation

**Optimization strategies**:
1. **Pre-pulled images**: Images pulled during system startup, not on-demand
2. **Lightweight images**: Golden images optimized for size
3. **No build steps**: Images pre-built, no runtime compilation
4. **Fast volume mounts**: Use Docker volumes, not bind mounts (where possible)

### Startup Time Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Container creation | <2 seconds | From pre-pulled image |
| Volume mount | <500ms | Persistent volume |
| First command execution | <1 second | Container ready |
| **Total task startup** | **<3 seconds** | Fast enough for good UX |

### Image Pre-Pulling

```python
class ContainerManager:
    async def startup(self):
        """Pre-pull all images during system startup"""
        logger.info("Pre-pulling Docker images...")
        
        for language, image in self.images.items():
            try:
                logger.info(f"Pulling {image}...")
                self.docker_client.images.pull(image)
                logger.info(f"✓ {image} ready")
            except Exception as e:
                logger.error(f"Failed to pull {image}: {e}")
        
        logger.info("All images ready")
```

---

## 9. Error Handling

### Container Creation Failures

```python
async def create_container(self, project_id: str, task_id: str, language: str):
    """Create container with error handling"""
    try:
        container = self.docker_client.containers.run(...)
        return container
    except docker.errors.ImageNotFound:
        logger.error(f"Image not found for language: {language}")
        raise ContainerError(f"Language {language} not supported")
    except docker.errors.APIError as e:
        logger.error(f"Docker API error: {e}")
        raise ContainerError("Failed to create container")
```

### Cleanup Failures

```python
async def destroy_container(self, task_id: str):
    """Destroy container with error handling"""
    container = self.active_containers.get(task_id)
    if not container:
        return
    
    try:
        container.stop(timeout=5)
        container.remove()
    except docker.errors.NotFound:
        logger.warning(f"Container already removed: {task_id}")
    except docker.errors.APIError as e:
        logger.error(f"Failed to destroy container: {e}")
        # Try force removal
        try:
            container.remove(force=True)
        except:
            logger.error(f"Force removal failed, container may be orphaned")
```

### Orphaned Container Cleanup

```python
async def cleanup_orphaned_containers(self):
    """Clean up containers that weren't properly destroyed"""
    
    # Find containers with our label
    containers = self.docker_client.containers.list(
        filters={'label': 'helix.managed=true'}
    )
    
    for container in containers:
        # Check if container is tracked
        if container.id not in [c.id for c in self.active_containers.values()]:
            logger.warning(f"Found orphaned container: {container.id[:12]}")
            try:
                container.stop(timeout=5)
                container.remove()
                logger.info(f"Cleaned up orphaned container: {container.id[:12]}")
            except Exception as e:
                logger.error(f"Failed to clean up orphaned container: {e}")

# Run periodically
@scheduler.scheduled_job('interval', hours=1)
async def periodic_cleanup():
    await container_manager.cleanup_orphaned_containers()
```

---

## 10. Golden Image Specifications

### Python Image (`helix-python:latest`)

```dockerfile
FROM python:3.11-slim

# Install common tools
RUN apt-get update && apt-get install -y \
    git \
    vim \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install common Python packages
RUN pip install --no-cache-dir \
    pytest \
    pytest-cov \
    black \
    flake8 \
    mypy \
    requests \
    flask \
    fastapi \
    sqlalchemy

WORKDIR /workspace
```

### Node.js Image (`helix-nodejs:latest`)

```dockerfile
FROM node:20-slim

# Install common tools
RUN apt-get update && apt-get install -y \
    git \
    vim \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install common global packages
RUN npm install -g \
    typescript \
    eslint \
    prettier \
    jest \
    nodemon

WORKDIR /workspace
```

### PowerShell Image (`helix-powershell:latest`)

```dockerfile
FROM mcr.microsoft.com/powershell:latest

# Install common tools
RUN apt-get update && apt-get install -y \
    git \
    vim \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install common PowerShell modules
RUN pwsh -Command "Install-Module -Name Pester -Force -Scope AllUsers"
RUN pwsh -Command "Install-Module -Name PSScriptAnalyzer -Force -Scope AllUsers"

WORKDIR /workspace
```

**Note**: Other language images follow similar patterns.

---

## Implementation Details

### Docker Compose Configuration

```yaml
version: '3.8'

services:
  orchestrator:
    build: .
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock  # Docker socket for container management
      - project_data:/app/projects  # Persistent project files
    environment:
      DOCKER_REGISTRY: "registry.example.com/helix"
      PYTHON_IMAGE: "helix-python:latest"
      NODEJS_IMAGE: "helix-nodejs:latest"
      # ... other images

volumes:
  project_data:
    driver: local
```

### System Startup Sequence

```python
async def system_startup():
    """System startup sequence"""
    
    # 1. Initialize container manager
    container_manager = ContainerManager()
    
    # 2. Pre-pull all images
    await container_manager.startup()
    
    # 3. Clean up any orphaned containers from previous run
    await container_manager.cleanup_orphaned_containers()
    
    # 4. Start orchestrator
    orchestrator = Orchestrator(container_manager)
    await orchestrator.startup()
    
    logger.info("System ready")
```

---

## Rationale

### Why On-Demand Creation?
- No wasted resources on idle containers
- Fresh environment for each task
- Prevents state leakage
- Simpler than pooling

### Why Task-Scoped Lifetime?
- Allows multiple operations in same environment
- Agent can iterate (test → fix → test)
- Balances performance and isolation
- Natural cleanup boundary

### Why No Resource Limits?
- Agents are trusted (LLM-powered, not user code)
- Simpler implementation
- Better performance
- Orchestrator timeout provides safety

### Why External Image Management?
- Decouples image updates from system deployment
- Allows specialized image optimization
- Standard CI/CD practices apply
- Flexibility for different environments

---

## Related Decisions

- **Decision 14**: Sandboxing strategy (Docker-based)
- **Decision 16**: Multi-project support (isolated containers)
- **Decision 71**: Tool Access Service (container operations via TAS)

---

## Tasks Created

### Phase 2: Container Management (Week 6)
- [ ] **Task 2.1.1**: Implement `ContainerManager` service
- [ ] **Task 2.1.2**: Build golden images for all supported languages
- [ ] **Task 2.1.3**: Implement container lifecycle (create/destroy)
- [ ] **Task 2.1.4**: Implement command execution in containers
- [ ] **Task 2.1.5**: Implement orphaned container cleanup
- [ ] **Task 2.1.6**: Add container operations to TAS

### Phase 6: Testing (Week 12)
- [ ] **Task 6.6.17**: Test container creation/destruction
- [ ] **Task 6.6.18**: Test multi-operation tasks in same container
- [ ] **Task 6.6.19**: Test cleanup and error handling
- [ ] **Task 6.6.20**: Performance test container startup time

---

## Approval

**Approved By**: User  
**Date**: November 1, 2025

---

*Last Updated: November 1, 2025*
