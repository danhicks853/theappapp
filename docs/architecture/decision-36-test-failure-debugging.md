# Decision 36: Test Failure Handling & Debugging

## Status
✅ RESOLVED | Date: Oct 31, 2025 | Priority: P0

## Decision
**Choice**: Progress-focused debugging with 3-cycle gate and agent collaboration

**Implementation**:
- **All failures**: Attempt fixes until hitting 3-cycle gate requirement (same exact failure)
- **Progress recognition**: Little by little progress is still progress, doesn't trigger gate
- **Agent collaboration**: Agents can request orchestrator help from other agents
- **Debugging process**: Failure analysis → Root cause → Fix attempt → Retest → Learning (store in Qdrant)
- **Escalation**: Only after 3 failed attempts on identical failure → raise human gate
- **Specialist access**: Security failures → Security Expert, Performance → DevOps, etc.

## Related
- Decision 74: Loop Detection Algorithm (implements 3-strike detection)
- Decision 70: Agent Collaboration Protocol (specialist consultation)
