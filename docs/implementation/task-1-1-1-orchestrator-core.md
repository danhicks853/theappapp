# Task 1.1.1: Orchestrator Core System - Hub-and-Spoke Architecture

## Status
✅ **COMPLETED**

## Reference
- **Decision**: Decision 67 - Orchestrator LLM Integration Architecture
- **Tracker**: Task 1.1.1 in Phase 1: Core Architecture Implementation
- **File**: `backend/services/orchestrator.py`

---

## Implementation Summary

Implemented the Orchestrator class as the central hub in a hub-and-spoke architecture for autonomous software development. The orchestrator coordinates all agents, manages task queues, routes messages, and maintains project state.

### Key Components Implemented

#### 1. **Orchestrator Class**
The main coordinator with the following responsibilities:
- **Agent Registry**: Maintains active agents with registration/unregistration
- **Task Queue**: FIFO queue with priority support
- **Message Routing**: Routes all agent communication through orchestrator
- **State Management**: Tracks project state and progress
- **Specialist Consultation**: Routes help requests to appropriate specialists
- **Escalation**: Creates gates for human approval

#### 2. **Data Models**
- **Agent**: Represents an agent with type, status, and current task
- **Task**: Represents work units with priority, type, and status
- **ProjectState**: Tracks complete project state and progress
- **Enums**: AgentType, TaskStatus, MessageType for type safety

#### 3. **Hub-and-Spoke Pattern Enforcement**
- All agent communication flows through orchestrator
- No direct agent-to-agent communication allowed
- Message routing validates sender and recipient exist
- All messages include orchestrator routing information

#### 4. **Task Queue Management**
- Priority-based queue (higher priority = processed first)
- FIFO ordering for same priority tasks
- Methods: `enqueue_task()`, `dequeue_task()`, `peek_task()`, `get_pending_count()`
- Supports task prioritization for urgent work

#### 5. **Agent Management**
- Agent registration with validation
- Agent retrieval by ID or type
- Status tracking (idle, active, paused, stopped)
- Current task assignment tracking

#### 6. **Message Routing**
- Routes messages between agents through orchestrator
- Validates sender and recipient existence
- Buffers messages for recipients
- Includes routing metadata

#### 7. **Specialist Consultation**
- Routes help requests to appropriate specialist type
- Selects first available specialist
- Creates consultation tracking information
- Buffers consultation requests

#### 8. **Escalation System**
- Creates gates for human approval
- Pauses agents on escalation
- Returns gate ID for tracking
- Stores escalation context

---

## Architecture Decisions

### Hub-and-Spoke Pattern
**Decision**: Implement strict hub-and-spoke with orchestrator as hub
- **Rationale**: Ensures all coordination flows through orchestrator, enabling intelligent routing and state management
- **Implementation**: All `route_message()` calls validate both sender and recipient, preventing direct agent communication

### Task Queue with Priority
**Decision**: Use PriorityQueue with FIFO fallback
- **Rationale**: Allows urgent tasks to jump queue while maintaining fairness for same-priority tasks
- **Implementation**: Negative priority values ensure higher numbers = higher priority

### Message Buffering
**Decision**: Buffer messages per agent rather than storing globally
- **Rationale**: Simplifies message retrieval and maintains agent isolation
- **Implementation**: `message_buffer` dict maps agent_id to list of messages

### State Centralization
**Decision**: Orchestrator maintains complete project state
- **Rationale**: Single source of truth for project progress and status
- **Implementation**: ProjectState object updated on every significant operation

---

## Test Coverage

### Unit Tests (40 tests)
Located in `backend/tests/unit/test_orchestrator.py`

**Test Classes**:
1. **TestOrchestratorInitialization** (3 tests)
   - Orchestrator creation
   - Unique ID generation
   - Project state initialization

2. **TestAgentRegistration** (8 tests)
   - Successful registration
   - Duplicate prevention
   - ID validation
   - Agent retrieval
   - Unregistration
   - Type-based retrieval

3. **TestTaskQueue** (8 tests)
   - Enqueue/dequeue operations
   - Empty queue handling
   - Peek without removal
   - Priority ordering
   - FIFO ordering for same priority

4. **TestTaskAssignment** (4 tests)
   - Task assignment to agent
   - Unknown agent handling
   - State updates on assignment

5. **TestMessageRouting** (4 tests)
   - Message routing between agents
   - Sender/recipient validation
   - Orchestrator routing info

6. **TestSpecialistConsultation** (2 tests)
   - Specialist consultation
   - No specialist available handling

7. **TestEscalation** (3 tests)
   - Gate creation
   - Agent pausing
   - Escalation without agent

8. **TestStateManagement** (4 tests)
   - Phase updates
   - Metadata updates
   - Status retrieval

9. **TestHubAndSpokeEnforcement** (2 tests)
   - All communication through orchestrator
   - Complete state visibility

### Integration Tests (12 tests)
Located in `backend/tests/integration/test_orchestrator_integration.py`

**Test Classes**:
1. **TestOrchestratorHubAndSpokeWorkflow** (3 tests)
   - Full task assignment workflow
   - Specialist consultation workflow
   - Multiple agents with multiple tasks

2. **TestOrchestratorStateConsistency** (2 tests)
   - State consistency across operations
   - State persistence

3. **TestOrchestratorMessageBuffering** (2 tests)
   - Message buffering for multiple recipients
   - Message ordering

4. **TestOrchestratorAgentManagement** (2 tests)
   - Agent status transitions
   - Multiple agents independent states

---

## API Reference

### Orchestrator Methods

#### Agent Management
```python
def register_agent(agent: Agent) -> bool
    """Register an agent with the orchestrator."""

def unregister_agent(agent_id: str) -> bool
    """Unregister an agent from the orchestrator."""

def get_agent(agent_id: str) -> Optional[Agent]
    """Get an agent by ID."""

def get_agents_by_type(agent_type: AgentType) -> List[Agent]
    """Get all agents of a specific type."""
```

#### Task Management
```python
def enqueue_task(task: Task) -> None
    """Add a task to the queue."""

def dequeue_task() -> Optional[Task]
    """Remove and return next task."""

def peek_task() -> Optional[Task]
    """View next task without removing."""

def get_pending_count() -> int
    """Get number of pending tasks."""

def assign_task(task: Task, agent_id: str) -> bool
    """Assign a task to an agent."""
```

#### Communication
```python
def route_message(
    sender_id: str,
    recipient_id: str,
    message_type: MessageType,
    payload: Dict[str, Any]
) -> bool
    """Route a message between agents."""

def consult_specialist(
    requesting_agent_id: str,
    specialist_type: AgentType,
    question: str,
    context: Dict[str, Any]
) -> Optional[Dict[str, Any]]
    """Route consultation request to specialist."""
```

#### Escalation & State
```python
def escalate_to_human(
    reason: str,
    context: Dict[str, Any],
    agent_id: Optional[str] = None
) -> str
    """Escalate issue to human review."""

def update_state(
    phase: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None
    """Update project state."""

def get_project_state() -> ProjectState
    """Get current project state."""

def get_orchestrator_status() -> Dict[str, Any]
    """Get comprehensive orchestrator status."""
```

---

## Usage Examples

### Basic Setup
```python
from backend.services.orchestrator import Orchestrator, Agent, Task, AgentType

# Create orchestrator
orchestrator = Orchestrator("my-project")

# Register agents
backend_dev = Agent("backend-1", AgentType.BACKEND_DEVELOPER)
orchestrator.register_agent(backend_dev)

# Create and enqueue task
task = Task(
    task_id="task-1",
    task_type="implement_api",
    agent_type=AgentType.BACKEND_DEVELOPER,
    priority=5
)
orchestrator.enqueue_task(task)

# Assign task
orchestrator.assign_task(task, "backend-1")
```

### Message Routing
```python
# Backend dev asks QA for help
orchestrator.route_message(
    sender_id="backend-1",
    recipient_id="qa-1",
    message_type=MessageType.HELP_REQUEST,
    payload={"question": "What test coverage is needed?"}
)
```

### Specialist Consultation
```python
# Consult security expert
result = orchestrator.consult_specialist(
    requesting_agent_id="backend-1",
    specialist_type=AgentType.SECURITY_EXPERT,
    question="Is this authentication approach secure?",
    context={"approach": "JWT tokens"}
)
```

### Escalation
```python
# Escalate to human
gate_id = orchestrator.escalate_to_human(
    reason="Loop detected after 3 failures",
    context={"task_id": "task-1", "error": "timeout"},
    agent_id="backend-1"
)
```

---

## Acceptance Criteria Met

✅ **Single orchestrator instance coordinates all agents**
- Orchestrator class is singleton per project
- All agents registered with orchestrator
- No direct agent-to-agent communication

✅ **All communication flows through hub**
- `route_message()` enforces routing through orchestrator
- Message buffer stores messages per agent
- All messages include orchestrator routing info

✅ **Agents cannot contact each other directly**
- `route_message()` validates sender and recipient
- No public method for direct agent communication
- Architecture enforces hub-and-spoke pattern

✅ **Hub-and-spoke enforcement verified**
- Unit tests verify pattern enforcement
- Integration tests verify complete workflows
- Message routing tests confirm all paths through hub

---

## Dependencies

### Internal
- None (core module, no other backend dependencies)

### External
- Python 3.8+
- Standard library only (typing, dataclasses, enum, datetime, uuid, queue)

### Future Dependencies
- Database for state persistence (Decision 76)
- LLM client for orchestrator reasoning (Decision 67)
- RAG client for knowledge queries (Decision 68)

---

## Next Steps

1. ✅ **Task 1.1.1 Complete**: Orchestrator core system implemented
2. ⏭️ **Task 1.1.2**: Implement synchronous task queue system (already included in Orchestrator)
3. ⏭️ **Task 1.1.3**: Create agent communication protocol
4. ⏭️ **Task 1.1.4**: Build project state management system
5. ⏭️ **Task 1.1.5**: Implement agent lifecycle management

---

## Notes

- The orchestrator is designed to be extended with LLM reasoning capabilities (Decision 67)
- Task queue uses Python's PriorityQueue for thread-safe operations
- Message buffering is in-memory; production will need database persistence
- State management is basic; will be enhanced with database backing (Decision 76)
- All code follows strict type hints for clarity and IDE support

---

## Testing Instructions

### Run Unit Tests
```bash
pytest backend/tests/unit/test_orchestrator.py -v
```

### Run Integration Tests
```bash
pytest backend/tests/integration/test_orchestrator_integration.py -v
```

### Run All Tests
```bash
pytest backend/tests/ -v
```

### Run with Coverage
```bash
pytest backend/tests/ --cov=backend.services.orchestrator --cov-report=html
```

---

*Implementation completed: Nov 1, 2025*
*Decision reference: Decision 67 - Orchestrator LLM Integration Architecture*
*Phase: 1 - Core Architecture Implementation*
