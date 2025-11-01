# Decision 14: Code Execution Sandboxing

## Status
✅ RESOLVED | Date: Oct 31, 2025 | Priority: P0

## Decision
**Choice**: Docker-based multi-language containers

**Implementation**:
- Linux containers for Python, Node.js, Java, Go, etc.
- Windows containers for PowerShell, .NET
- Resource limits (CPU, memory) but no artificial time limits
- Orchestrator handles timeouts naturally via progress monitoring
- Root user acceptable due to container isolation

## Related
- Detailed in Decision 78: Docker Container Lifecycle (8 language images)
