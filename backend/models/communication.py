"""
Agent Communication Protocol - Message Models and Routing

Module: Communication Protocol
Purpose: Define structured message types for agent ↔ orchestrator communication

Reference: Decision 67 - Orchestrator LLM Integration Architecture
           Decision 70 - Agent Collaboration Protocol
Task: 1.1.3 - Create agent communication protocol

This module provides Pydantic models for all message types in the hub-and-spoke
architecture. All agent communication flows through the orchestrator; no direct
agent-to-agent communication is allowed.

Message Types:
- TASK_ASSIGNMENT: Orchestrator assigns task to agent
- TASK_RESULT: Agent returns completed task result
- HELP_REQUEST: Agent requests specialist consultation
- SPECIALIST_RESPONSE: Specialist provides consultation response
- PROGRESS_UPDATE: Agent reports progress on current task
- ERROR_REPORT: Agent reports error or blocker
"""

from typing import Dict, List, Optional, Any, Union, Literal
from enum import Enum
from datetime import datetime
import uuid
from pydantic import BaseModel, Field, ConfigDict


class MessageType(Enum):
    """Types of messages in orchestrator communication."""
    TASK_ASSIGNMENT = "task_assignment"
    TASK_RESULT = "task_result"
    HELP_REQUEST = "help_request"
    SPECIALIST_RESPONSE = "specialist_response"
    PROGRESS_UPDATE = "progress_update"
    ERROR_REPORT = "error_report"


class AgentType(Enum):
    """Available agent types in the system."""
    ORCHESTRATOR = "orchestrator"
    BACKEND_DEVELOPER = "backend_developer"
    FRONTEND_DEVELOPER = "frontend_developer"
    QA_ENGINEER = "qa_engineer"
    SECURITY_EXPERT = "security_expert"
    DEVOPS_ENGINEER = "devops_engineer"
    DOCUMENTATION_EXPERT = "documentation_expert"
    UI_UX_DESIGNER = "ui_ux_designer"
    GITHUB_SPECIALIST = "github_specialist"
    WORKSHOPPER = "workshopper"
    PROJECT_MANAGER = "project_manager"


class MessagePriority(Enum):
    """Priority levels for messages."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class BaseMessage(BaseModel):
    """
    Base message model for all orchestrator communication.
    
    All messages in the system inherit from this base class and include:
    - Sender and recipient identification
    - Message type classification
    - Unique correlation ID for tracking
    - Timestamp for ordering
    - Priority for routing decisions
    """
    
    model_config = ConfigDict(use_enum_values=False)
    
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique message identifier")
    sender_id: str = Field(..., description="ID of sending agent")
    sender_type: AgentType = Field(..., description="Type of sending agent")
    recipient_id: str = Field(..., description="ID of receiving agent (usually orchestrator)")
    recipient_type: AgentType = Field(..., description="Type of receiving agent")
    message_type: MessageType = Field(..., description="Type of message")
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Tracks related messages")
    timestamp: datetime = Field(default_factory=datetime.now, description="When message was created")
    priority: MessagePriority = Field(default=MessagePriority.NORMAL, description="Message priority")


class TaskAssignmentMessage(BaseMessage):
    """
    Message from orchestrator assigning a task to an agent.
    
    Flow: Orchestrator → Agent
    
    Attributes:
        task_id: Unique identifier for the task
        task_type: Type of task (e.g., 'backend_development', 'testing')
        task_description: Human-readable description of what needs to be done
        requirements: Specific requirements and constraints
        context: Task-specific context (project info, dependencies, etc.)
        deadline: Optional deadline for task completion
        dependencies: List of task IDs this task depends on
    """
    
    message_type: Literal[MessageType.TASK_ASSIGNMENT] = MessageType.TASK_ASSIGNMENT
    task_id: str = Field(..., description="Unique task identifier")
    task_type: str = Field(..., description="Type of task to perform")
    task_description: str = Field(..., description="Detailed description of task")
    requirements: Dict[str, Any] = Field(default_factory=dict, description="Task requirements")
    context: Dict[str, Any] = Field(default_factory=dict, description="Task-specific context")
    deadline: Optional[datetime] = Field(default=None, description="Optional task deadline")
    dependencies: List[str] = Field(default_factory=list, description="Task IDs this depends on")


class TaskResultMessage(BaseMessage):
    """
    Message from agent returning completed task result.
    
    Flow: Agent → Orchestrator
    
    Attributes:
        task_id: ID of the task that was completed
        status: Final status of task (completed, failed, blocked)
        result: The actual result/output from the task
        execution_time_seconds: How long task took to execute
        tokens_used: LLM tokens used (if applicable)
        errors: Any errors encountered during execution
        notes: Additional notes or observations
    """
    
    message_type: Literal[MessageType.TASK_RESULT] = MessageType.TASK_RESULT
    task_id: str = Field(..., description="ID of completed task")
    status: Literal['completed', 'failed', 'blocked', 'partial'] = Field(..., description="Final task status")
    result: Dict[str, Any] = Field(default_factory=dict, description="Task result/output")
    execution_time_seconds: float = Field(default=0.0, description="Execution duration")
    tokens_used: Optional[int] = Field(default=None, description="LLM tokens used")
    errors: List[str] = Field(default_factory=list, description="Errors encountered")
    notes: str = Field(default="", description="Additional notes")


class HelpRequestMessage(BaseMessage):
    """
    Message from agent requesting specialist consultation.
    
    Flow: Agent → Orchestrator (orchestrator then routes to specialist)
    
    Attributes:
        question: The question or help needed
        context: Context about the current task
        current_task_id: ID of task agent is working on
        specific_concern: What specifically is the concern
        attempted_approaches: What has already been tried
        suggested_agent: Optional suggestion for which agent to consult
        urgency: How urgent is this request
    """
    
    message_type: Literal[MessageType.HELP_REQUEST] = MessageType.HELP_REQUEST
    question: str = Field(..., description="The question or help request")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context for the request")
    current_task_id: str = Field(..., description="Task ID agent is working on")
    specific_concern: str = Field(default="", description="Specific concern or blocker")
    attempted_approaches: List[str] = Field(default_factory=list, description="Approaches already tried")
    suggested_agent: Optional[AgentType] = Field(default=None, description="Suggested specialist (optional)")
    urgency: Literal['low', 'normal', 'high', 'critical'] = Field(default="normal", description="Urgency level")


class SpecialistResponseMessage(BaseMessage):
    """
    Message from specialist providing consultation response.
    
    Flow: Orchestrator → Agent (orchestrator routes specialist's response)
    
    Attributes:
        collaboration_id: ID tracking this collaboration session
        consulted_agent_type: Which specialist was consulted
        answer: The specialist's answer/response
        additional_context: Extra context or resources
        code_reference: Optional reference to relevant code
        suggested_next_steps: Recommendations for next steps
        confidence: Specialist's confidence in the answer (0-1)
    """
    
    message_type: Literal[MessageType.SPECIALIST_RESPONSE] = MessageType.SPECIALIST_RESPONSE
    collaboration_id: str = Field(..., description="Collaboration session ID")
    consulted_agent_type: AgentType = Field(..., description="Type of specialist consulted")
    answer: str = Field(..., description="The specialist's answer")
    additional_context: Dict[str, Any] = Field(default_factory=dict, description="Extra context")
    code_reference: Optional[str] = Field(default=None, description="Code reference if applicable")
    suggested_next_steps: List[str] = Field(default_factory=list, description="Recommended next steps")
    confidence: float = Field(default=0.8, ge=0, le=1, description="Confidence in answer (0-1)")


class ProgressUpdateMessage(BaseMessage):
    """
    Message from agent reporting progress on current task.
    
    Flow: Agent → Orchestrator
    
    Attributes:
        task_id: ID of task being worked on
        progress_percentage: How far along (0-100)
        current_step: Description of current step
        estimated_completion: Estimated time to completion
        blockers: Any blockers encountered
        tokens_used_so_far: LLM tokens used so far
    """
    
    message_type: Literal[MessageType.PROGRESS_UPDATE] = MessageType.PROGRESS_UPDATE
    task_id: str = Field(..., description="ID of task in progress")
    progress_percentage: int = Field(..., ge=0, le=100, description="Progress 0-100")
    current_step: str = Field(default="", description="Current step description")
    estimated_completion: Optional[datetime] = Field(default=None, description="Estimated completion time")
    blockers: List[str] = Field(default_factory=list, description="Current blockers")
    tokens_used_so_far: Optional[int] = Field(default=None, description="LLM tokens used so far")


class ErrorReportMessage(BaseMessage):
    """
    Message from agent reporting error or blocker.
    
    Flow: Agent → Orchestrator
    
    Attributes:
        task_id: ID of task that encountered error
        error_type: Category of error
        error_message: Description of the error
        error_details: Detailed error information
        stack_trace: Stack trace if applicable
        recovery_attempted: What recovery was attempted
        needs_escalation: Whether this needs human escalation
    """
    
    message_type: Literal[MessageType.ERROR_REPORT] = MessageType.ERROR_REPORT
    task_id: str = Field(..., description="ID of task with error")
    error_type: str = Field(..., description="Category of error")
    error_message: str = Field(..., description="Error description")
    error_details: Dict[str, Any] = Field(default_factory=dict, description="Detailed error info")
    stack_trace: Optional[str] = Field(default=None, description="Stack trace if applicable")
    recovery_attempted: List[str] = Field(default_factory=list, description="Recovery attempts")
    needs_escalation: bool = Field(default=False, description="Needs human escalation")


class MessageRouter:
    """
    Routes messages in the hub-and-spoke architecture.
    
    Enforces that:
    - All messages flow through orchestrator
    - No direct agent-to-agent communication
    - Messages are validated before routing
    - Routing decisions are logged
    
    This class is the enforcement point for the hub-and-spoke pattern.
    """
    
    def __init__(self):
        """Initialize the message router."""
        self.message_log: List[BaseMessage] = []
        self.orchestrator_id: Optional[str] = None
    
    def set_orchestrator(self, orchestrator_id: str) -> None:
        """
        Set the orchestrator ID for validation.
        
        Args:
            orchestrator_id: ID of the orchestrator instance
        """
        self.orchestrator_id = orchestrator_id
    
    def validate_message(self, message: BaseMessage) -> bool:
        """
        Validate message for hub-and-spoke compliance.
        
        Enforces:
        - Recipient must be orchestrator (or orchestrator sending to agent)
        - Message structure is valid
        - No direct agent-to-agent communication
        
        Args:
            message: Message to validate
            
        Returns:
            True if message is valid
            
        Raises:
            ValueError: If message violates hub-and-spoke pattern
        """
        # If sender is orchestrator, recipient can be any agent
        if message.sender_type == AgentType.ORCHESTRATOR:
            return True
        
        # If sender is an agent, recipient MUST be orchestrator
        if message.recipient_type != AgentType.ORCHESTRATOR:
            raise ValueError(
                f"Hub-and-spoke violation: Agent {message.sender_id} "
                f"cannot send to {message.recipient_id}. "
                f"All agent communication must flow through orchestrator."
            )
        
        return True
    
    def route_message(self, message: BaseMessage) -> bool:
        """
        Route a message through the orchestrator.
        
        Args:
            message: Message to route
            
        Returns:
            True if message was routed successfully
            
        Raises:
            ValueError: If message violates hub-and-spoke pattern
        """
        # Validate message
        self.validate_message(message)
        
        # Log message
        self.message_log.append(message)
        
        return True
    
    def get_message_history(
        self,
        correlation_id: Optional[str] = None,
        sender_id: Optional[str] = None,
        message_type: Optional[MessageType] = None,
        limit: int = 100
    ) -> List[BaseMessage]:
        """
        Get message history with optional filtering.
        
        Args:
            correlation_id: Filter by correlation ID
            sender_id: Filter by sender ID
            message_type: Filter by message type
            limit: Maximum number of messages to return
            
        Returns:
            List of messages matching criteria
        """
        results = self.message_log
        
        if correlation_id:
            results = [m for m in results if m.correlation_id == correlation_id]
        
        if sender_id:
            results = [m for m in results if m.sender_id == sender_id]
        
        if message_type:
            results = [m for m in results if m.message_type == message_type]
        
        # Return most recent messages first, up to limit
        return sorted(results, key=lambda m: m.timestamp, reverse=True)[:limit]


# Type alias for any message type
AnyMessage = Union[
    TaskAssignmentMessage,
    TaskResultMessage,
    HelpRequestMessage,
    SpecialistResponseMessage,
    ProgressUpdateMessage,
    ErrorReportMessage
]
