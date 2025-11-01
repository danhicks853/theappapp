# Decision 3: Orchestrator Architecture Pattern

## Status
✅ RESOLVED  
**Date**: Oct 31, 2025  
**Priority**: P0 - BLOCKING

---

## Context

Need to define the specific architecture pattern for the orchestrator - whether it's a dumb coordinator, intelligent decision-maker, or central authority.

---

## Decision

### **Choice: Central Coordinator with Intelligent Gate Detection**

**Rationale**:
- Clear decision authority for human approvals
- Easier debugging with centralized coordination
- Centralized state management simplifies recovery
- Orchestrator actively monitors and makes decisions

**Key Features**:
- **Gate Detection**: Automatically detects when human approval needed
- **Agent Health Monitoring**: Tracks agent status and performance
- **Auto-Recovery**: Detects when agents go off-rails and intervenes
- **Decision Authority**: Central point for all critical decisions

**Trade-offs**:
- Single point of failure (mitigated by recovery systems)
- Orchestrator complexity increases
- Worth it for control and visibility

---

## Related Decisions

**Dependencies**:
- Decision 2: Orchestrator Engine (custom enables intelligence)
- Decision 4: Communication Pattern (coordinator-based)

**Expanded By**:
- Decision 67: Orchestrator LLM Integration (adds AI reasoning)
- Decision 74: Loop Detection Algorithm (auto-recovery mechanism)
- Decision 76: Project State Recovery (recovery capability)

---

## Implementation Notes

This decision established the orchestrator as an intelligent coordinator rather than a passive message router. Later enhanced with:
- LLM-based reasoning (Decision 67)
- Loop detection for off-rails scenarios (Decision 74)
- State recovery mechanisms (Decision 76)

The "intelligent gate detection" concept evolved into the comprehensive human-in-the-loop system.

---

**Last Updated**: Nov 1, 2025  
**Status**: Core pattern for all orchestrator functionality
