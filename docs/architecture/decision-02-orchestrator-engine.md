# Decision 2: Orchestrator Engine Approach

## Status
✅ RESOLVED  
**Date**: Oct 31, 2025  
**Priority**: P0 - BLOCKING

---

## Context

Need to decide whether to use existing workflow orchestration frameworks (Temporal, Cadence) or build custom orchestrator engine.

---

## Decision

### **Choice: Custom-built Orchestrator**

**Rationale**:
- Must avoid copyleft licenses (GPL, AGPL) for commercialization potential
- Need full control over intellectual property
- Requirement for custom coordination logic specific to AI agents
- Flexibility to implement exactly what we need

**Implementation**:
- Custom orchestrator service built from scratch
- Message queue for agent communication
- Database for state management
- No dependency on Temporal/Cadence or similar frameworks

**Trade-offs**:
- More development effort upfront
- Responsible for our own orchestration logic
- No pre-built workflow features
- Worth it for IP control and commercialization

---

## Related Decisions

**Dependencies**:
- Decision 1: System Architecture (microservices enables custom orchestrator)
- Decision 5: Agent State Management (database backing)

**Related**:
- Decision 67: Orchestrator LLM Integration (implements custom logic with AI)

---

## Implementation Notes

This decision prioritized IP ownership and commercial viability over using existing frameworks. The custom orchestrator approach enables:
- Proprietary coordination algorithms
- AI-specific workflow patterns
- No licensing restrictions
- Full customization for agent management

---

**Last Updated**: Nov 1, 2025  
**Status**: Foundation for custom orchestrator development
