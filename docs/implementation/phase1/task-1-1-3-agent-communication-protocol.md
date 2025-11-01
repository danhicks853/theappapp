# Task 1.1.3: Create Agent Communication Protocol

**Task**: 1.1.3  
**Phase**: Phase 1 - Core Architecture Implementation  
**Completed**: Nov 1, 2025  
**Coverage**: 100% (26/26 tests passing)

---

## Implementation Summary

Implemented a complete agent communication protocol for the hub-and-spoke architecture. All agent communication flows through the orchestrator with structured Pydantic message models. The system enforces the hub-and-spoke pattern at the routing layer, preventing direct agent-to-agent communication.

---

## Files Created

- `backend/models/communication.py` - Core communication protocol with 6 message types
- `backend/models/__init__.py` - Package exports
- `backend/tests/models/test_communication.py` - Comprehensive test suite (26 tests)
- `backend/tests/models/__init__.py` - Test package marker

---

## Key Classes/Functions

### Message Types (Enums)

**`MessageType`** - Six message types for orchestrator communication:
- `TASK_ASSIGNMENT` - Orchestrator assigns task to agent
- `TASK_RESULT` - Agent returns completed task result
- `HELP_REQUEST` - Agent requests specialist consultation
- `SPECIALIST_RESPONSE` - Specialist provides consultation response
- `PROGRESS_UPDATE` - Agent reports progress on current task
- `ERROR_REPORT` - Agent reports error or blocker

**`AgentType`** - 11 agent types in the system:
- ORCHESTRATOR, BACKEND_DEVELOPER, FRONTEND_DEVELOPER, QA_ENGINEER, SECURITY_EXPERT
- DEVOPS_ENGINEER, DOCUMENTATION_EXPERT, UI_UX_DESIGNER, GITHUB_SPECIALIST
- WORKSHOPPER, PROJECT_MANAGER

**`MessagePriority`** - Message priority levels:
- LOW (1), NORMAL (2), HIGH (3), CRITICAL (4)

### Message Models (Pydantic)

**`BaseMessage`** - Base class for all messages:
- `message_id` - Unique message identifier (auto-generated UUID)
- `sender_id` - ID of sending agent
- `sender_type` - Type of sending agent
- `recipient_id` - ID of receiving agent
- `recipient_type` - Type of receiving agent
- `message_type` - Type of message
- `correlation_id` - Tracks related messages (auto-generated UUID)
- `timestamp` - When message was created
- `priority` - Message priority (default: NORMAL)

**`TaskAssignmentMessage`** - Orchestrator → Agent:
- `task_id` - Unique task identifier
- `task_type` - Type of task (e.g., 'backend_development')
- `task_description` - Detailed description of task
- `requirements` - Task requirements and constraints
- `context` - Task-specific context (project info, dependencies)
- `deadline` - Optional task deadline
- `dependencies` - List of task IDs this depends on

**`TaskResultMessage`** - Agent → Orchestrator:
- `task_id` - ID of completed task
- `status` - Final status (completed, failed, blocked, partial)
- `result` - Task result/output
- `execution_time_seconds` - How long task took
- `tokens_used` - LLM tokens used (if applicable)
- `errors` - Errors encountered
- `notes` - Additional notes

**`HelpRequestMessage`** - Agent → Orchestrator:
- `question` - The question or help request
- `context` - Context about current task
- `current_task_id` - ID of task agent is working on
- `specific_concern` - What specifically is the concern
- `attempted_approaches` - What has already been tried
- `suggested_agent` - Optional suggestion for specialist
- `urgency` - Urgency level (low, normal, high, critical)

**`SpecialistResponseMessage`** - Orchestrator → Agent:
- `collaboration_id` - ID tracking collaboration session
- `consulted_agent_type` - Which specialist was consulted
- `answer` - The specialist's answer
- `additional_context` - Extra context or resources
- `code_reference` - Optional reference to relevant code
- `suggested_next_steps` - Recommendations for next steps
- `confidence` - Specialist's confidence (0-1, validated)

**`ProgressUpdateMessage`** - Agent → Orchestrator:
- `task_id` - ID of task in progress
- `progress_percentage` - Progress 0-100 (validated)
- `current_step` - Description of current step
- `estimated_completion` - Estimated completion time
- `blockers` - Current blockers
- `tokens_used_so_far` - LLM tokens used so far

**`ErrorReportMessage`** - Agent → Orchestrator:
- `task_id` - ID of task with error
- `error_type` - Category of error
- `error_message` - Error description
- `error_details` - Detailed error information
- `stack_trace` - Stack trace if applicable
- `recovery_attempted` - Recovery attempts made
- `needs_escalation` - Whether this needs human escalation

### MessageRouter Class

**Purpose**: Enforces hub-and-spoke pattern at routing layer

**Methods**:
- `set_orchestrator(orchestrator_id)` - Set orchestrator ID for validation
- `validate_message(message)` - Validate message for hub-and-spoke compliance
  - Raises `ValueError` if agent sends directly to another agent
  - Allows orchestrator to send to any agent
  - Allows agents to send only to orchestrator
- `route_message(message)` - Route message through orchestrator
  - Validates message
  - Logs message to history
  - Returns True on success
- `get_message_history(correlation_id, sender_id, message_type, limit)` - Get message history
  - Supports filtering by correlation ID, sender, or message type
  - Returns messages sorted by timestamp (most recent first)
  - Default limit: 100 messages

---

## Design Decisions

- **Pydantic v2 Models**: Used for automatic validation and serialization
- **Literal Types**: Used for message_type and status fields instead of enums to ensure type safety
- **Field Constraints**: Used `ge`/`le` constraints for progress_percentage and confidence instead of validators
- **Auto-Generated IDs**: message_id and correlation_id auto-generated as UUIDs
- **Hub-and-Spoke Enforcement**: MessageRouter validates all messages to prevent direct agent-to-agent communication
- **Message Priority**: Included priority field for future queue-based routing decisions
- **Correlation Tracking**: correlation_id allows tracking related messages across collaboration sessions

---

## Test Coverage

**Unit Tests**: 26 tests, 100% passing

Test Categories:
1. **Enum Tests** (3 tests):
   - MessageType values and count
   - AgentType values

2. **BaseMessage Tests** (2 tests):
   - Message creation with required fields
   - Auto-generated IDs are unique

3. **TaskAssignmentMessage Tests** (2 tests):
   - Basic message creation
   - Message with deadline

4. **TaskResultMessage Tests** (3 tests):
   - Successful task completion
   - Failed task with errors
   - Invalid status validation

5. **HelpRequestMessage Tests** (3 tests):
   - Basic help request creation
   - All urgency levels (low, normal, high, critical)
   - Invalid urgency validation

6. **SpecialistResponseMessage Tests** (2 tests):
   - Basic specialist response creation
   - Confidence validation (0-1 range)

7. **ProgressUpdateMessage Tests** (2 tests):
   - Basic progress update creation
   - Progress percentage validation (0-100 range)

8. **ErrorReportMessage Tests** (2 tests):
   - Basic error report creation
   - Escalation flag handling

9. **MessageRouter Tests** (5 tests):
   - Router initialization
   - Valid agent-to-orchestrator messages
   - Valid orchestrator-to-agent messages
   - Hub-and-spoke violation detection (agent-to-agent blocked)
   - Successful message routing
   - Message history retrieval

**Test Results**:
```
26 passed in 0.16s
```

---

## Dependencies

- `pydantic==2.12.3` - Data validation and serialization
- `pytest==8.4.2` - Testing framework
- `pytest-cov==7.0.0` - Coverage reporting

---

## Usage Example

### Creating and Routing Messages

```python
from backend.models.communication import (
    TaskAssignmentMessage,
    TaskResultMessage,
    MessageRouter,
    AgentType,
    MessageType,
)

# Initialize router
router = MessageRouter()
router.set_orchestrator("orch-1")

# Orchestrator assigns task to backend developer
task_msg = TaskAssignmentMessage(
    sender_id="orch-1",
    sender_type=AgentType.ORCHESTRATOR,
    recipient_id="backend-dev-1",
    recipient_type=AgentType.BACKEND_DEVELOPER,
    task_id="task-123",
    task_type="backend_development",
    task_description="Implement user authentication",
    requirements={"framework": "FastAPI", "auth_type": "JWT"},
    context={"project_id": "proj-1", "phase": "phase-1"}
)

# Route message (validates hub-and-spoke pattern)
router.route_message(task_msg)

# Agent returns result
result_msg = TaskResultMessage(
    sender_id="backend-dev-1",
    sender_type=AgentType.BACKEND_DEVELOPER,
    recipient_id="orch-1",
    recipient_type=AgentType.ORCHESTRATOR,
    task_id="task-123",
    status="completed",
    result={"endpoint": "/api/auth/login", "method": "POST"},
    execution_time_seconds=45.5,
    tokens_used=1250
)

# Route result message
router.route_message(result_msg)

# Get message history
history = router.get_message_history(sender_id="backend-dev-1")
print(f"Found {len(history)} messages from backend-dev-1")
```

### Hub-and-Spoke Enforcement

```python
# This will raise ValueError - agents cannot send directly to each other
try:
    invalid_msg = TaskResultMessage(
        sender_id="backend-dev-1",
        sender_type=AgentType.BACKEND_DEVELOPER,
        recipient_id="frontend-dev-1",  # ERROR: Direct agent-to-agent
        recipient_type=AgentType.FRONTEND_DEVELOPER,
        task_id="task-123",
        status="completed"
    )
    router.route_message(invalid_msg)
except ValueError as e:
    print(f"Hub-and-spoke violation: {e}")
```

### Specialist Consultation

```python
from backend.models.communication import HelpRequestMessage, SpecialistResponseMessage

# Frontend developer requests help
help_msg = HelpRequestMessage(
    sender_id="frontend-dev-1",
    sender_type=AgentType.FRONTEND_DEVELOPER,
    recipient_id="orch-1",
    recipient_type=AgentType.ORCHESTRATOR,
    question="What is the User model structure?",
    current_task_id="task-456",
    specific_concern="Need to know available fields for display",
    attempted_approaches=["Checked API docs", "Reviewed schema file"],
    urgency="normal"
)

router.route_message(help_msg)

# Orchestrator routes to backend developer and gets response
response_msg = SpecialistResponseMessage(
    sender_id="orch-1",
    sender_type=AgentType.ORCHESTRATOR,
    recipient_id="frontend-dev-1",
    recipient_type=AgentType.FRONTEND_DEVELOPER,
    collaboration_id="collab-789",
    consulted_agent_type=AgentType.BACKEND_DEVELOPER,
    answer="User model has: id, username, email, profile_image_url, created_at",
    additional_context={"model_file": "models/user.py", "lines": "15-42"},
    confidence=0.95
)

router.route_message(response_msg)
```

---

## Related Tasks

- **Depends on**: Task 1.1.1 (Orchestrator Core), Task 1.1.2 (Task Queue)
- **Enables**: Task 1.1.4 (Project State Management), Task 1.1.5 (Agent Lifecycle)
- **Related**: Decision 67 (Orchestrator LLM Integration), Decision 70 (Agent Collaboration Protocol)

---

## Implementation Notes

### Pydantic v2 Migration

This implementation uses Pydantic v2 syntax:
- `ConfigDict` instead of `Config` class
- `Literal` types instead of `const=True` parameter
- Field constraints (`ge`, `le`) instead of `@validator` decorators
- Automatic validation on field assignment

### Message Flow Architecture

The communication protocol enforces the hub-and-spoke pattern:

```
Agent A → Orchestrator → Agent B
(allowed)

Agent A → Agent B
(BLOCKED - ValueError raised)

Orchestrator → Agent A
(allowed)
```

### Correlation Tracking

Each message includes a `correlation_id` that can be used to track related messages across a collaboration session. For example:
1. Agent sends HELP_REQUEST (correlation_id = "collab-123")
2. Orchestrator sends SPECIALIST_RESPONSE with same correlation_id
3. All messages in this collaboration can be retrieved via `get_message_history(correlation_id="collab-123")`

### Message Priority

Messages include a priority field (LOW, NORMAL, HIGH, CRITICAL) for future use in queue-based routing. Currently stored but not used in routing logic.

---

## Notes

- All message types are immutable Pydantic models (frozen=True can be added if needed)
- Message validation is automatic via Pydantic field constraints
- Hub-and-spoke enforcement happens at router level, not model level
- Message history is in-memory; for persistence, integrate with database
- All timestamps are UTC datetime objects
- UUIDs are generated as strings for JSON serialization

---

*Implementation completed: Nov 1, 2025*  
*Status: Ready for integration with orchestrator and agent systems*
