# Decision 4: Communication Pattern

## Status
✅ RESOLVED  
**Date**: Oct 31, 2025  
**Priority**: P0 - BLOCKING

---

## Context

Need to determine how agents communicate - directly with each other, through orchestrator, via shared message bus, or other patterns.

---

## Decision

### **Choice: Coordinator-Agent Only (Hub-and-Spoke)**

**Rationale**:
- **Safety and Control**: Orchestrator has full visibility into all communication
- **Pause Capability**: Can pause any interaction for human review
- **Simpler Security**: Single point of security enforcement
- **Clear Authority**: Orchestrator mediates all agent interactions
- **Audit Trail**: Complete log of all communication

**Implementation**:
- All agent communication flows through central orchestrator
- No direct agent-to-agent communication allowed
- Orchestrator routes messages between agents
- Enforced at architecture level

**Trade-offs**:
- Orchestrator becomes communication bottleneck
- Extra hop for agent collaboration
- Worth it for control and safety

---

## Related Decisions

**Dependencies**:
- Decision 3: Orchestrator Pattern (coordinator role)
- Decision 1: Microservices Architecture (enables mediation)

**Detailed In**:
- Decision 70: Agent Collaboration Protocol (collaboration through orchestrator)
- Decision 67: Orchestrator LLM Integration (intelligent routing)

---

## Implementation Notes

This decision established the hub-and-spoke pattern that became central to the system architecture. The coordinator-only communication enables:
- Complete orchestrator visibility
- Security enforcement at single point
- Human intervention capability
- Full audit trail

Later refined in Decision 70 with structured collaboration protocol and Decision 67 with intelligent routing logic.

---

**Last Updated**: Nov 1, 2025  
**Status**: Core communication architecture
