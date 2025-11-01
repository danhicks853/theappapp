# Decision 32: Phase Failure Handling

## Status
✅ RESOLVED | Date: Oct 31, 2025 | Priority: P0

## Decision
**Choice**: Structured failure handling with loop detection

**Implementation**:
- **Agent Task Failures**: Agents retry first, then escalate to orchestrator when stuck
- **Handoff Failures**: Next phase reports issues, orchestrator coordinates resolution
- **Technical Blockers**: Orchestrator asks appropriate agent to redesign approach
- **Loop Detection**: After 3rd unresolved loop between agents → raise human gate
- **Example**: Backend ↔ Security loop 3 times → human approval needed
- **Never Skip Phases**: All issues must be resolved before proceeding

## Related
- Decision 74: Loop Detection Algorithm (implements 3-strike detection)
