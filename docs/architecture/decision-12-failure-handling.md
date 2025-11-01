# Decision 12: Agent Failure Handling

## Status
✅ RESOLVED | Date: Oct 31, 2025 | Priority: P0

## Decision
**Choice**: Simple timeout + progress checkpoint monitoring with explicit completion protocol

**Implementation**:
- Task-specific timeouts with progress reporting requirements
- Explicit "TASK_COMPLETE" messages only (progress messages separate)
- Orchestrator validates completion before advancing
- Agent replacement on timeout/failure

**Safety Features**: Message type separation, artifact verification, rollback capability

## Related
- Decision 74: Loop Detection Algorithm (failure pattern detection)
- Decision 76: Project State Recovery (recovery mechanisms)
