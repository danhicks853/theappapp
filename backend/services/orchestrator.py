"""
Orchestrator Core System - Hub-and-Spoke Architecture

The Orchestrator is the central coordinator in the hub-and-spoke architecture.
All agents communicate through the orchestrator; no direct agent-to-agent communication is allowed.

Architecture:
- Hub: Orchestrator (this class)
- Spokes: All agents (Backend Dev, Frontend Dev, QA, Security, DevOps, etc.)
- Communication: All messages flow through orchestrator
- State: Orchestrator maintains complete project state
- Coordination: Orchestrator makes routing and escalation decisions
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid
from queue import PriorityQueue


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


class TaskStatus(Enum):
    """Task lifecycle states."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class MessageType(Enum):
    """Types of messages in orchestrator communication."""
    TASK_ASSIGNMENT = "task_assignment"
    TASK_RESULT = "task_result"
    HELP_REQUEST = "help_request"
    SPECIALIST_RESPONSE = "specialist_response"
    PROGRESS_UPDATE = "progress_update"
    ERROR_REPORT = "error_report"


@dataclass
class Agent:
    """Represents an agent in the system."""
    agent_id: str
    agent_type: AgentType
    status: str = "idle"  # idle, active, paused, stopped
    current_task_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """Represents a task in the system."""
    task_id: str
    task_type: str
    agent_type: AgentType
    priority: int = 0  # Higher number = higher priority
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    
    def __lt__(self, other: 'Task') -> bool:
        """Support comparison for PriorityQueue when priorities are equal."""
        if not isinstance(other, Task):
            return NotImplemented
        # Compare by creation time if priorities are equal
        return self.created_at < other.created_at


@dataclass
class ProjectState:
    """Represents the complete state of a project."""
    project_id: str
    current_phase: str
    active_task_id: Optional[str] = None
    active_agent_id: Optional[str] = None
    completed_tasks: List[str] = field(default_factory=list)
    pending_tasks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)


class Orchestrator:
    """
    Central coordinator for autonomous software development.
    
    Implements hub-and-spoke architecture where:
    - Orchestrator is the hub
    - All agents are spokes
    - All communication flows through orchestrator
    - No direct agent-to-agent communication allowed
    
    Responsibilities:
    - Maintain active agents registry
    - Route tasks to appropriate agents
    - Manage task queue (FIFO with priority support)
    - Track project state
    - Route messages between agents (through orchestrator)
    - Coordinate specialist consultations
    - Escalate to humans when needed
    - Update project state
    """
    
    def __init__(self, project_id: str):
        """
        Initialize the Orchestrator.
        
        Args:
            project_id: Unique identifier for the project being orchestrated
        """
        self.orchestrator_id = str(uuid.uuid4())
        self.project_id = project_id
        
        # Agent registry - maps agent_id to Agent object
        self.active_agents: Dict[str, Agent] = {}
        
        # Task queue - FIFO with priority support
        # Using PriorityQueue: (priority, task_id, task)
        self.task_queue: PriorityQueue = PriorityQueue()
        
        # Project state tracking
        self.project_state: ProjectState = ProjectState(
            project_id=project_id,
            current_phase="initialization"
        )
        
        # Message routing - stores pending messages for agents
        self.message_buffer: Dict[str, List[Dict[str, Any]]] = {}
        
        # Initialization timestamp
        self.created_at = datetime.now()
    
    def register_agent(self, agent: Agent) -> bool:
        """
        Register an agent with the orchestrator.
        
        Args:
            agent: Agent object to register
            
        Returns:
            bool: True if registration successful, False if agent already registered
            
        Raises:
            ValueError: If agent_id is None or empty
        """
        if not agent.agent_id:
            raise ValueError("Agent must have a valid agent_id")
        
        if agent.agent_id in self.active_agents:
            return False
        
        self.active_agents[agent.agent_id] = agent
        self.message_buffer[agent.agent_id] = []
        return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from the orchestrator.
        
        Args:
            agent_id: ID of agent to unregister
            
        Returns:
            bool: True if unregistration successful, False if agent not found
        """
        if agent_id not in self.active_agents:
            return False
        
        del self.active_agents[agent_id]
        if agent_id in self.message_buffer:
            del self.message_buffer[agent_id]
        return True
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """
        Get an agent by ID.
        
        Args:
            agent_id: ID of agent to retrieve
            
        Returns:
            Agent object if found, None otherwise
        """
        return self.active_agents.get(agent_id)
    
    def get_agents_by_type(self, agent_type: AgentType) -> List[Agent]:
        """
        Get all agents of a specific type.
        
        Args:
            agent_type: Type of agents to retrieve
            
        Returns:
            List of agents matching the type
        """
        return [
            agent for agent in self.active_agents.values()
            if agent.agent_type == agent_type
        ]
    
    def assign_task(self, task: Task, agent_id: str) -> bool:
        """
        Assign a task to a specific agent.
        
        This is the primary method for routing work to agents.
        
        Args:
            task: Task to assign
            agent_id: ID of agent to assign task to
            
        Returns:
            bool: True if assignment successful, False if agent not found
            
        Raises:
            ValueError: If task or agent_id is None
        """
        if not task or not agent_id:
            raise ValueError("Task and agent_id are required")
        
        if agent_id not in self.active_agents:
            return False
        
        agent = self.active_agents[agent_id]
        task.assigned_agent_id = agent_id
        task.status = TaskStatus.ASSIGNED
        
        # Update agent state
        agent.current_task_id = task.task_id
        agent.status = "active"
        
        # Update project state
        self.project_state.active_task_id = task.task_id
        self.project_state.active_agent_id = agent_id
        self.project_state.last_updated = datetime.now()
        
        return True
    
    def enqueue_task(self, task: Task) -> None:
        """
        Add a task to the task queue.
        
        Tasks are processed in priority order (higher priority first),
        then FIFO for same priority.
        
        Args:
            task: Task to enqueue
            
        Raises:
            ValueError: If task is None
        """
        if not task:
            raise ValueError("Task cannot be None")
        
        # PriorityQueue uses (priority, insertion_order, item)
        # Negate priority so higher numbers = higher priority
        self.task_queue.put((-task.priority, task.created_at.timestamp(), task))
    
    def dequeue_task(self) -> Optional[Task]:
        """
        Remove and return the next task from the queue.
        
        Returns:
            Next task in queue, or None if queue is empty
        """
        if self.task_queue.empty():
            return None
        
        _, _, task = self.task_queue.get()
        return task
    
    def peek_task(self) -> Optional[Task]:
        """
        View the next task without removing it from queue.
        
        Returns:
            Next task in queue, or None if queue is empty
        """
        if self.task_queue.empty():
            return None
        
        # PriorityQueue doesn't support peek, so we get and put back
        _, _, task = self.task_queue.get()
        self.task_queue.put((-task.priority, task.created_at.timestamp(), task))
        return task
    
    def get_pending_count(self) -> int:
        """
        Get the number of pending tasks in the queue.
        
        Returns:
            Number of tasks waiting to be assigned
        """
        return self.task_queue.qsize()
    
    def prioritize_task(self, task_id: str, new_priority: int) -> bool:
        """
        Change the priority of a task in the queue.
        
        Note: This is a simplified implementation. In production,
        you'd need to rebuild the queue or use a different data structure.
        
        Args:
            task_id: ID of task to prioritize
            new_priority: New priority value (higher = more urgent)
            
        Returns:
            bool: True if task found and updated, False otherwise
        """
        # This is a placeholder - full implementation would require
        # extracting, modifying, and re-enqueueing the task
        # For now, return False to indicate not implemented
        return False
    
    def route_message(
        self,
        sender_id: str,
        recipient_id: str,
        message_type: MessageType,
        payload: Dict[str, Any]
    ) -> bool:
        """
        Route a message from one agent to another through the orchestrator.
        
        This enforces the hub-and-spoke pattern: all agent communication
        flows through the orchestrator.
        
        Args:
            sender_id: ID of sending agent
            recipient_id: ID of receiving agent
            message_type: Type of message
            payload: Message content
            
        Returns:
            bool: True if message routed successfully, False otherwise
            
        Raises:
            ValueError: If sender or recipient not found
        """
        if sender_id not in self.active_agents:
            raise ValueError(f"Sender agent {sender_id} not found")
        
        if recipient_id not in self.active_agents:
            raise ValueError(f"Recipient agent {recipient_id} not found")
        
        # Create message object
        message = {
            "message_id": str(uuid.uuid4()),
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "message_type": message_type.value,
            "payload": payload,
            "timestamp": datetime.now().isoformat(),
            "routed_through": self.orchestrator_id
        }
        
        # Buffer message for recipient
        if recipient_id not in self.message_buffer:
            self.message_buffer[recipient_id] = []
        
        self.message_buffer[recipient_id].append(message)
        return True
    
    def consult_specialist(
        self,
        requesting_agent_id: str,
        specialist_type: AgentType,
        question: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Route a consultation request from one agent to a specialist.
        
        This is used when an agent needs expert input on a specific topic.
        
        Args:
            requesting_agent_id: ID of agent requesting consultation
            specialist_type: Type of specialist to consult
            question: The question or request
            context: Relevant context for the specialist
            
        Returns:
            Response from specialist, or None if specialist not available
        """
        # Find available specialist of requested type
        specialists = self.get_agents_by_type(specialist_type)
        
        if not specialists:
            return None
        
        # For now, select first available specialist
        # In production, this would use more sophisticated selection
        specialist = specialists[0]
        
        # Create consultation request message
        message = {
            "message_id": str(uuid.uuid4()),
            "sender_id": requesting_agent_id,
            "recipient_id": specialist.agent_id,
            "message_type": MessageType.HELP_REQUEST.value,
            "payload": {
                "question": question,
                "context": context,
                "request_type": "consultation"
            },
            "timestamp": datetime.now().isoformat(),
            "routed_through": self.orchestrator_id
        }
        
        # Buffer message for specialist
        if specialist.agent_id not in self.message_buffer:
            self.message_buffer[specialist.agent_id] = []
        
        self.message_buffer[specialist.agent_id].append(message)
        
        return {
            "consultation_id": message["message_id"],
            "specialist_id": specialist.agent_id,
            "specialist_type": specialist_type.value
        }
    
    def escalate_to_human(
        self,
        reason: str,
        context: Dict[str, Any],
        agent_id: Optional[str] = None
    ) -> str:
        """
        Escalate an issue to human review.
        
        This creates a gate (human approval point) and pauses the relevant agent.
        
        Args:
            reason: Why escalation is needed
            context: Relevant context for human review
            agent_id: ID of agent that triggered escalation (optional)
            
        Returns:
            Gate ID for tracking the escalation
        """
        gate_id = str(uuid.uuid4())
        
        # Pause the agent if specified
        if agent_id and agent_id in self.active_agents:
            agent = self.active_agents[agent_id]
            agent.status = "paused"
        
        # Create escalation record structure for database storage
        # In production, this would be stored in database:
        # {
        #     "gate_id": gate_id,
        #     "project_id": self.project_id,
        #     "reason": reason,
        #     "context": context,
        #     "agent_id": agent_id,
        #     "created_at": datetime.now().isoformat(),
        #     "status": "pending_approval"
        # }
        
        return gate_id
    
    def update_state(
        self,
        phase: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update the project state.
        
        Args:
            phase: New phase name (optional)
            metadata: Additional metadata to merge (optional)
        """
        if phase:
            self.project_state.current_phase = phase
        
        if metadata:
            self.project_state.metadata.update(metadata)
        
        self.project_state.last_updated = datetime.now()
    
    def get_project_state(self) -> ProjectState:
        """
        Get the current project state.
        
        Returns:
            Current ProjectState object
        """
        return self.project_state
    
    def get_orchestrator_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of the orchestrator.
        
        Returns:
            Dictionary with orchestrator metrics and state
        """
        return {
            "orchestrator_id": self.orchestrator_id,
            "project_id": self.project_id,
            "active_agents_count": len(self.active_agents),
            "pending_tasks_count": self.get_pending_count(),
            "current_phase": self.project_state.current_phase,
            "active_task_id": self.project_state.active_task_id,
            "active_agent_id": self.project_state.active_agent_id,
            "completed_tasks_count": len(self.project_state.completed_tasks),
            "created_at": self.created_at.isoformat(),
            "last_updated": self.project_state.last_updated.isoformat()
        }
