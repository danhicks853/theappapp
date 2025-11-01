# Decision 59: Malicious Code Prevention

## Status
✅ RESOLVED | Date: Oct 31, 2025 | Priority: P0

## Decision
**Choice**: Container isolation as primary security layer (starting point)

**Implementation**:
- Docker containers with resource limits, network isolation, filesystem isolation
- Each agent runs in isolated container with only project directory access
- Non-root user execution, time limits on processes
- Philosophy: Assume agents run malicious code, design for safety
- Note: Security may be loosened later based on needs

## Related
- Decision 78: Docker Container Lifecycle
