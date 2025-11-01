# Decision 11: Decision-Making Process

## Status
✅ RESOLVED | Date: Oct 31, 2025 | Priority: P1

## Decision
**Choice**: Hierarchical decision flow through orchestrator

**Process**: Agent question → Orchestrator → Specialist/human input → Orchestrator decision → Agent execution

**Example**: Backend Dev asks "PostgreSQL vs MongoDB?" → Orchestrator checks requirements → Security Expert recommends → Orchestrator decides → Agent implements

**Rationale**: Clear decision authority, specialist input when needed, human oversight on critical choices

## Related
- Decision 67: Orchestrator LLM Integration (intelligent decision-making)
- Decision 70: Agent Collaboration Protocol (specialist consultation)
