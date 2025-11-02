# TheAppApp Code Execution Sandbox

Docker-based code execution environment for AI agents.

## Overview

This sandbox system allows AI agents to safely execute code in isolated Docker containers. Each task gets its own container with persistent project storage.

## Supported Languages

- **Python 3.11** - With numpy, pandas, pytest, black, flake8, mypy
- **Node.js 20** - With TypeScript, Jest, ESLint, Prettier
- **Java 17** - With Maven and Gradle
- **Go 1.21** - Latest stable Go
- **Ruby 3.2** - With Rails and RSpec
- **PHP 8.2** - With Composer
- **.NET 8.0** - Full SDK with C# support
- **PowerShell 7** - Cross-platform PowerShell

## Building Images

Build all images at once:

```bash
cd docker
chmod +x build-all.sh
./build-all.sh
```

Or build individually:

```bash
docker build -t theappapp-python:latest -f images/python/Dockerfile images/python/
docker build -t theappapp-node:latest -f images/node/Dockerfile images/node/
# ... etc
```

## Architecture

### Container Lifecycle

1. **Task Start** → Container created for specific language
2. **Execution** → Multiple commands run in same container
3. **Task End** → Container destroyed immediately

**Key Point**: One container per task, no reuse between tasks

### Volume Mounting

- Each project gets a persistent Docker volume: `theappapp-project-{project_id}`
- Mounted at `/workspace` in all containers
- Files persist across container recreations
- Isolated per project (no cross-project access)

### Security

- **Network Isolation**: Bridge network, no host access
- **No Privileged Mode**: Containers run without elevated permissions
- **Read-Only System**: System files are read-only
- **Resource Limits**: Optional CPU/memory limits (currently unlimited)
- **Image Labels**: All containers tagged with `theappapp-managed=true`

## Usage (via ContainerManager)

```python
from backend.services.container_manager import get_container_manager

# Get manager instance
manager = get_container_manager()

# Pre-pull images at startup
await manager.startup()

# Create container for a task
result = await manager.create_container(
    task_id="task-123",
    project_id="proj-456",
    language="python"
)

# Execute command
exec_result = await manager.exec_command(
    task_id="task-123",
    command="python script.py"
)

print(f"Exit code: {exec_result.exit_code}")
print(f"Output: {exec_result.stdout}")

# Destroy container when task completes
await manager.destroy_container(task_id="task-123")
```

## Cleanup

### Automatic Cleanup

- Containers are automatically destroyed when tasks complete
- Hourly cleanup job removes orphaned containers
- Job runs via `backend/jobs/container_cleanup.py`

### Manual Cleanup

Remove all TheAppApp containers:

```bash
docker ps -a --filter "label=theappapp-managed=true" -q | xargs docker rm -f
```

Remove all volumes:

```bash
docker volume ls --filter "name=theappapp-project-" -q | xargs docker volume rm
```

## Monitoring

The SandboxMonitor service tracks:
- All command executions
- Resource usage per task
- Error rates and patterns
- Execution duration statistics

## Code Validation

Before execution, the CodeValidator service checks for:
- Dangerous patterns (eval, exec, system calls)
- Syntax errors
- Code size limits (max 1MB)
- Hardcoded secrets/passwords

**Note**: Validation warnings don't block execution (agents might have legitimate use cases)

## Container Naming

- Format: `theappapp-{project_id}-{task_id}`
- Example: `theappapp-abc123-task456`
- Easily identifiable and trackable

## Volume Naming

- Format: `theappapp-project-{project_id}`
- Example: `theappapp-project-abc123`
- Persists independently of containers

## Troubleshooting

### Images not pulling

```bash
# Check Docker daemon
docker info

# Pull manually
docker pull python:3.11-slim
docker pull node:20-slim
# ... etc
```

### Containers not cleaning up

```bash
# Run cleanup job manually
python backend/jobs/container_cleanup.py

# Check for orphaned containers
docker ps -a --filter "label=theappapp-managed=true"
```

### Volume issues

```bash
# List volumes
docker volume ls --filter "name=theappapp-project-"

# Inspect volume
docker volume inspect theappapp-project-{project_id}

# Remove specific volume
docker volume rm theappapp-project-{project_id}
```

## Performance

- **Container Creation**: <2 seconds
- **First Command**: <1 second
- **Total Startup**: <3 seconds
- **Image Pre-pull**: ~5 minutes (one-time at startup)

## Development

### Adding New Language

1. Create `docker/images/{language}/Dockerfile`
2. Add to `LANGUAGE_IMAGES` dict in `container_manager.py`
3. Add to `build-all.sh` script
4. Build and test

### Testing

```bash
# Unit tests
pytest backend/tests/unit/test_container_manager.py

# Integration tests
pytest backend/tests/integration/test_container_lifecycle.py
```

## Security Considerations

- Containers are **NOT** fully sandboxed from kernel
- Trust the orchestrator timeout mechanism for long-running code
- Review code validation patterns regularly
- Monitor for suspicious activity via SandboxMonitor
- Keep base images updated for security patches

## License

Part of TheAppApp AI Agent Orchestration Platform
