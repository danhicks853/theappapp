"""Orchestrator Core System - Hub-and-Spoke Architecture."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from queue import PriorityQueue
from typing import Any, Awaitable, Dict, List, Optional

from backend.models import AutonomyLevel
from backend.services.autonomy_policy import should_escalate as autonomy_should_escalate
from backend.agents.base_agent import TaskResult


async def _awaitable(value: Any) -> Any:
    """Await value if needed, otherwise return synchronously."""

    if asyncio.iscoroutine(value) or isinstance(value, Awaitable):
        return await value
    return value


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
    description: str = ""  # Human-readable task description for orchestrator context
    priority: int = 0  # Higher number = higher priority
    payload: Dict[str, Any] = field(default_factory=dict)
    project_id: Optional[str] = None  # Project this task belongs to
    created_at: datetime = field(default_factory=datetime.now)
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)  # For orchestrator context passing
    deliverable_id: Optional[str] = None  # If task is for a deliverable
    
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
    
    def __init__(
        self,
        project_id: str,
        *,
        tas_client: Optional[Any] = None,
        llm_client: Optional[Any] = None,
        gate_manager: Optional[Any] = None,
        rag_service: Optional[Any] = None,
        decision_logger: Optional[Any] = None,
        autonomy_level: AutonomyLevel = AutonomyLevel.MEDIUM,
    ):
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

        # External service dependencies
        self.tas_client = tas_client
        self.llm_client = llm_client
        self.gate_manager = gate_manager
        self.rag_service = rag_service
        self._decision_logger = decision_logger
        self.autonomy_level = autonomy_level
        self.logger = logging.getLogger("orchestrator")

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
        
        If task.agent_type is None, intelligently assigns the appropriate agent
        based on task description and available agents.
        
        Args:
            task: Task to add to queue
            
        Raises:
            ValueError: If task is None
        """
        if not task:
            raise ValueError("Task is required")
        
        if not task.task_id:
            raise ValueError("Task must have task_id")
        
        # Intelligent agent assignment if not already assigned
        if task.agent_type is None:
            task.agent_type = self._intelligently_assign_agent_type(task)
            self.logger.info(
                f"Orchestrator assigned agent_type={task.agent_type.value} for task {task.task_id}"
            )
        
        # Negate priority so higher numbers = higher priority
        self.task_queue.put((-task.priority, task.created_at.timestamp(), task))
    
    async def on_task_completed(self, task: Task, result: TaskResult) -> None:
        """
        CORE ORCHESTRATOR INTELLIGENCE: Decide what happens next.
        
        Uses LLM reasoning with full project context to determine:
        - Should we create another task? Which agent?
        - Should we escalate to human?
        - Is the project complete?
        
        This is the "project manager brain" - sees everything, decides next steps.
        
        Args:
            task: Task that just completed
            result: Result from the agent
        """
        self.logger.info(f"Orchestrator analyzing completion of task {task.task_id}")
        
        # 1. Gather full project context
        project_context = await self._gather_project_context(task, result)
        
        # 2. Read agent outputs
        agent_outputs = await self._read_agent_outputs(task, result)
        
        # 3. Ask LLM: "What should happen next?"
        decision = await self._llm_decide_next_action(project_context, agent_outputs, task, result)
        
        # 4. Execute the decision
        await self._execute_orchestrator_decision(decision, task, result)
        
        self.logger.info(
            f"Orchestrator decision: {decision.get('action')} - {decision.get('reasoning')}"
        )
    
    async def _gather_project_context(self, task: Task, result: TaskResult) -> Dict[str, Any]:
        """
        Gather complete project context for orchestrator decision-making.
        
        Returns:
            Dict with project plan, scope, completed tasks, available agents, etc.
        """
        # Get project state
        context = {
            "project_id": self.project_id,
            "project_goal": getattr(self.project_state, 'goal', 'Not yet defined'),
            "current_phase": getattr(self.project_state, 'current_phase', 'initialization'),
            
            # Task that just completed
            "completed_task": {
                "id": task.task_id,
                "description": task.description,
                "agent_type": task.agent_type.value if task.agent_type else None,
                "success": result.success,
                "summary": result.summary if hasattr(result, 'summary') else None
            },
            
            # Available agents
            "available_agents": [
                {
                    "type": agent.agent_type.value if hasattr(agent.agent_type, 'value') else str(agent.agent_type),
                    "status": agent.status
                }
                for agent in self.active_agents.values()
            ],
            
            # Project history (recent tasks)
            "completed_tasks_history": [
                {
                    "agent": t.agent_type.value if t.agent_type and hasattr(t.agent_type, 'value') else "unknown",
                    "description": t.description,
                    "status": t.status.value if hasattr(t.status, 'value') else str(t.status)
                }
                for t in list(self.project_state.task_history)[-5:]  # Last 5 tasks
            ] if hasattr(self.project_state, 'task_history') else [],
            
            # Current state
            "active_task_count": self.task_queue.qsize(),
        }
        
        return context
    
    async def _read_agent_outputs(self, task: Task, result: TaskResult) -> Dict[str, str]:
        """
        Read files that the agent created.
        
        Returns:
            Dict mapping filename → content
        """
        outputs = {}
        
        # Get files from result artifacts
        if hasattr(result, 'artifacts') and result.artifacts:
            for artifact in result.artifacts:
                if isinstance(artifact, dict) and 'filename' in artifact:
                    filename = artifact['filename']
                    # Try to read the file via TAS
                    try:
                        content = await self._read_file_from_container(filename)
                        if content:
                            outputs[filename] = content
                    except Exception as e:
                        self.logger.warning(f"Could not read {filename}: {e}")
        
        return outputs
    
    async def _read_file_from_container(self, filename: str) -> Optional[str]:
        """Read a file from the project container using TAS."""
        if not self.tas_client:
            return None
        
        try:
            # Use TAS to read file
            result = await self.execute_tool({
                "tool_name": "file_system",
                "operation": "read",
                "parameters": {
                    "project_id": self.project_id,
                    "task_id": self.project_id,  # Use project_id as task_id for project-level files
                    "path": filename
                }
            })
            
            if result.get("success"):
                return result.get("content")
        except Exception as e:
            self.logger.debug(f"Could not read {filename}: {e}")
        
        return None
    
    async def _llm_decide_next_action(
        self,
        project_context: Dict[str, Any],
        agent_outputs: Dict[str, str],
        completed_task: Task,
        result: TaskResult
    ) -> Dict[str, Any]:
        """
        Use LLM to intelligently decide what should happen next.
        
        This is the CORE orchestrator intelligence - reasons about the project
        state and makes informed decisions about workflow.
        
        Returns:
            Decision dict with action, reasoning, next steps
        """
        # Build comprehensive prompt for LLM
        prompt = self._build_orchestrator_decision_prompt(
            project_context, agent_outputs, completed_task, result
        )
        
        # Ask LLM for decision
        if self.llm_client and hasattr(self.llm_client, 'query'):
            try:
                response = await self.llm_client.query(prompt)
                decision = self._parse_orchestrator_decision(response)
                return decision
            except Exception as e:
                self.logger.error(f"LLM decision error: {e}")
                # Fallback to simple logic
                return self._fallback_decision(project_context, completed_task)
        else:
            # No LLM available - use simple fallback
            return self._fallback_decision(project_context, completed_task)
    
    def _build_orchestrator_decision_prompt(
        self,
        project_context: Dict[str, Any],
        agent_outputs: Dict[str, str],
        completed_task: Task,
        result: TaskResult
    ) -> str:
        """Build the prompt for LLM orchestrator decision-making."""
        
        # Format agent outputs
        outputs_text = "\n".join([
            f"**{filename}**:\n```\n{content[:500]}...\n```"
            for filename, content in agent_outputs.items()
        ]) if agent_outputs else "No output files"
        
        # Format available agents
        agents_text = "\n".join([
            f"- {agent['type']} (status: {agent['status']})"
            for agent in project_context['available_agents']
        ])
        
        # Format task history
        history_text = "\n".join([
            f"{i+1}. {t['agent']}: {t['description']} → {t['status']}"
            for i, t in enumerate(project_context.get('completed_tasks_history', []))
        ]) if project_context.get('completed_tasks_history') else "This is the first task"
        
        prompt = f"""You are an intelligent orchestrator managing a software development project.

PROJECT GOAL: {project_context['project_goal']}
CURRENT PHASE: {project_context['current_phase']}

=== TASK JUST COMPLETED ===
Agent: {project_context['completed_task']['agent_type']}
Task: {project_context['completed_task']['description']}
Success: {project_context['completed_task']['success']}
Summary: {project_context['completed_task']['summary']}

=== AGENT OUTPUT FILES ===
{outputs_text}

=== PROJECT HISTORY ===
{history_text}

=== AVAILABLE AGENTS ===
{agents_text}

=== YOUR DECISION ===
Analyze the situation and decide what should happen next:

1. **What was accomplished?** Assess the completed work.
2. **What's the logical next step?** Consider the project goal and current state.
3. **Which agent should handle it?** Pick the right specialist.
4. **What context do they need?** What information from previous tasks is relevant?
5. **Or is something else needed?** (Human escalation? Project complete?)

Respond in JSON format:
{{
    "action": "create_task" | "escalate_to_human" | "project_complete" | "wait_for_more_tasks",
    "reasoning": "Clear explanation of why this is the right decision",
    "next_agent_type": "agent type" (if action is create_task),
    "task_description": "Specific task for the agent" (if action is create_task),
    "context_to_pass": {{
        "files_to_reference": ["filename1", "filename2"],
        "key_information": "Important context from previous work"
    }},
    "urgency": "low" | "normal" | "high"
}}

Think like a project manager - be strategic, consider dependencies, and keep the project moving forward efficiently.
"""
        
        return prompt
    
    def _parse_orchestrator_decision(self, llm_response: Any) -> Dict[str, Any]:
        """Parse LLM response into decision dict."""
        import json
        
        # If response is already a dict, return it
        if isinstance(llm_response, dict):
            return llm_response
        
        # Try to parse as JSON
        if isinstance(llm_response, str):
            try:
                # Look for JSON in response
                start = llm_response.find('{')
                end = llm_response.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = llm_response[start:end]
                    return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # Fallback: create decision from response text
        return {
            "action": "wait_for_more_tasks",
            "reasoning": "Could not parse LLM decision",
            "raw_response": str(llm_response)
        }
    
    def _fallback_decision(self, project_context: Dict[str, Any], completed_task: Task) -> Dict[str, Any]:
        """Simple fallback decision logic if LLM unavailable."""
        return {
            "action": "wait_for_more_tasks",
            "reasoning": "LLM unavailable - waiting for external task creation",
            "next_agent_type": None
        }
    
    async def _execute_orchestrator_decision(
        self,
        decision: Dict[str, Any],
        completed_task: Task,
        result: TaskResult
    ) -> None:
        """Execute the orchestrator's decision."""
        action = decision.get('action')
        
        if action == 'create_task':
            # Create next task
            await self._create_next_task_from_decision(decision, completed_task)
        
        elif action == 'escalate_to_human':
            # Escalate for human decision
            await self.escalate_to_human(
                reason=decision.get('reasoning', 'Orchestrator requesting guidance'),
                context={
                    "completed_task": completed_task.task_id,
                    "decision": decision
                }
            )
        
        elif action == 'project_complete':
            # Mark project as complete
            self.logger.info("🎉 Orchestrator determined project is complete!")
            self.project_state.status = "completed"
        
        elif action == 'wait_for_more_tasks':
            # Do nothing - wait for external task creation
            pass
        
        else:
            self.logger.warning(f"Unknown orchestrator action: {action}")
    
    async def _create_next_task_from_decision(
        self,
        decision: Dict[str, Any],
        previous_task: Task
    ) -> None:
        """Create and enqueue the next task based on orchestrator decision."""
        # Determine agent type
        agent_type_str = decision.get('next_agent_type', 'workshopper')
        try:
            agent_type = AgentType[agent_type_str.upper()]
        except (KeyError, AttributeError):
            # Try to find matching agent type
            for at in AgentType:
                if agent_type_str.lower() in at.value.lower():
                    agent_type = at
                    break
            else:
                agent_type = AgentType.WORKSHOPPER  # Default fallback
        
        # Build task description with context
        task_description = decision.get('task_description', 'Continue project work')
        context_to_pass = decision.get('context_to_pass', {})
        
        # Add context information to description
        if context_to_pass:
            files_ref = context_to_pass.get('files_to_reference', [])
            key_info = context_to_pass.get('key_information', '')
            
            if files_ref:
                task_description += f"\n\nReference files: {', '.join(files_ref)}"
            if key_info:
                task_description += f"\n\nContext: {key_info}"
        
        # Determine priority (higher is more urgent)
        urgency = decision.get('urgency', 'normal')
        priority = 10 if urgency == 'high' else 5 if urgency == 'normal' else 1
        
        # Create task
        next_task = Task(
            task_id=f"orch-task-{id(self)}-{len(self.project_state.task_history) if hasattr(self.project_state, 'task_history') else 0}",
            task_type=decision.get('task_type', 'orchestrator_assigned'),
            description=task_description,
            agent_type=agent_type,
            priority=priority,
            status=TaskStatus.PENDING,
            project_id=self.project_id,
            metadata={
                "orchestrator_decision": True,
                "previous_task_id": previous_task.task_id,
                "context": context_to_pass
            }
        )
        
        # Enqueue it
        self.enqueue_task(next_task)
        
        self.logger.info(
            f"Orchestrator created next task: {next_task.task_id} for {agent_type.value}"
        )
    
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
    
    async def escalate_to_human(
        self,
        reason: str,
        context: Dict[str, Any],
        agent_id: Optional[str] = None,
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
        if agent_id and agent_id in self.active_agents:
            agent = self.active_agents[agent_id]
            agent.status = "paused"

        gate_id = await self.create_gate(reason=reason, context=context, agent_id=agent_id)

        # TODO: persist escalation record per Decision 76 once storage layer exists
        return gate_id

    async def execute_tool(self, tool_request: Dict[str, Any]) -> Dict[str, Any]:
        """Forward a tool execution request to TAS and return the audited result."""

        if not self.tas_client or not hasattr(self.tas_client, "execute_tool"):
            raise NotImplementedError("TAS client not configured for orchestrator")

        # Convert tool_request to TAS format
        from backend.services.tool_access_service import ToolExecutionRequest
        
        tas_request = ToolExecutionRequest(
            agent_id=tool_request.get("agent_id", "unknown"),
            agent_type=tool_request.get("agent_type", "unknown"),
            tool_name=tool_request.get("tool", ""),
            operation=tool_request.get("operation", ""),
            parameters=tool_request.get("parameters", {}),
            project_id=tool_request.get("project_id"),
            task_id=tool_request.get("task_id")
        )
        
        response = await self.tas_client.execute_tool(tas_request)
        
        audit_record = {
            "status": "success" if response.success else "failed",
            "result": response.result,
            "error": response.message if not response.success else None,
            "audited_at": datetime.now(UTC).isoformat(),
            "allowed": response.allowed
        }
        
        self.logger.info(
            "Tool execution routed | tool=%s | status=%s",
            tool_request.get("tool"),
            audit_record["status"],
        )
        return audit_record

    async def evaluate_confidence(self, confidence_request: Dict[str, Any]) -> float:
        """Evaluate agent confidence using the configured LLM client."""

        if not self.llm_client or not hasattr(self.llm_client, "evaluate_confidence"):
            raise NotImplementedError("LLM client not configured for confidence evaluation")

        response = await _awaitable(
            self.llm_client.evaluate_confidence(confidence_request)
        )
        try:
            score = float(response)
        except (TypeError, ValueError):
            self.logger.warning("Invalid confidence score response: %s", response)
            return 0.0

        return max(0.0, min(1.0, score))

    def should_escalate(self, *, confidence_score: float) -> bool:
        """Determine whether to escalate based on autonomy level and confidence."""

        return autonomy_should_escalate(
            autonomy_level=self.autonomy_level,
            confidence_score=confidence_score,
        )

    async def query_knowledge_base(
        self,
        *,
        query: str,
        agent_type: str,
        task_type: str,
        technology: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieve RAG knowledge relevant to a task using orchestrator mediation."""

        if not self.rag_service or not hasattr(self.rag_service, "search"):
            raise NotImplementedError("RAG service not configured for orchestrator")

        patterns = await _awaitable(
            self.rag_service.search(
                query=query,
                agent_type=agent_type,
                task_type=task_type,
                technology=technology,
                limit=limit,
            )
        )

        formatted: List[Dict[str, Any]] = []
        for pattern in patterns:
            formatted.append(
                {
                    "title": getattr(pattern, "title", "Historical pattern"),
                    "problem": getattr(pattern, "problem", ""),
                    "solution": getattr(pattern, "solution", ""),
                    "when_to_try": getattr(pattern, "when_to_try", ""),
                    "success_count": getattr(pattern, "success_count", 0),
                    "similarity": getattr(pattern, "similarity", 0.0),
                }
            )

        return formatted

    async def vet_pm_decision(self, project_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Review a PM proposal with specialists and log the orchestrator decision."""

        self.logger.info("Vetting PM decision for project %s", self.project_id)
        required_specialists: List[AgentType] = []

        if project_plan.get("has_security_implications"):
            required_specialists.append(AgentType.SECURITY_EXPERT)
        if project_plan.get("has_performance_requirements"):
            required_specialists.append(AgentType.DEVOPS_ENGINEER)
        if project_plan.get("requires_backend_changes"):
            required_specialists.append(AgentType.BACKEND_DEVELOPER)

        feedback: List[Dict[str, Any]] = []
        for specialist_type in required_specialists:
            consultation = await _awaitable(
                self.consult_specialist(
                    requesting_agent_id=project_plan.get("pm_agent_id", "project_manager"),
                    specialist_type=specialist_type,
                    question=f"Review project plan section for {specialist_type.value}",
                    context={"project_plan": project_plan},
                )
            )
            if consultation:
                feedback.append(consultation)

        approved = not feedback
        decision_summary = {
            "approved": approved,
            "feedback": feedback,
        }

        await self.log_decision(
            decision_type="pm_vetting",
            reasoning="Specialist feedback gathered" if feedback else "No concerns identified",
            decision=decision_summary,
            confidence=1.0 if approved else 0.6,
            rag_context=None,
        )

        return decision_summary

    async def log_decision(
        self,
        *,
        decision_type: str,
        reasoning: str,
        decision: Dict[str, Any],
        confidence: float,
        rag_context: Optional[List[Dict[str, Any]]] = None,
        tokens: Optional[Dict[str, int]] = None,
        execution_result: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persist orchestrator decision details for analytics."""

        entry = {
            "project_id": self.project_id,
            "decision_type": decision_type,
            "situation": decision.get("situation"),
            "reasoning": reasoning,
            "decision": decision,
            "autonomy_level": self.autonomy_level.value,
            "rag_context": rag_context,
            "confidence": confidence,
            "tokens_input": (tokens or {}).get("input"),
            "tokens_output": (tokens or {}).get("output"),
            "execution_result": execution_result,
        }

        if not self._decision_logger:
            self.logger.debug("Decision logging skipped; recorder not configured | %s", decision_type)
            return

        await _awaitable(self._decision_logger(entry))

    def route_collaboration(
        self,
        help_request: Dict[str, Any],
        *,
        specialist_types: Optional[List[AgentType]] = None,
    ) -> Dict[str, Any]:
        """Select the best specialist for a collaboration request."""

        specialist_types = specialist_types or [
            AgentType.SECURITY_EXPERT,
            AgentType.DEVOPS_ENGINEER,
            AgentType.BACKEND_DEVELOPER,
        ]

        candidates: List[Agent] = []
        for agent_type in specialist_types:
            candidates.extend(self.get_agents_by_type(agent_type))

        if not candidates:
            return {
                "selected_agent": None,
                "reasoning": "No available specialists",
                "help_request": help_request,
            }

        selected = sorted(
            candidates,
            key=lambda agent: (
                agent.status != "idle",
                agent.metadata.get("current_load", 0),
            ),
        )[0]

        decision_payload = {
            "action": "route_collaboration",
            "details": {
                "agent_id": selected.agent_id,
                "agent_type": selected.agent_type.value,
            },
            "next_steps": ["Notify specialist", "Share context"],
        }

        asyncio.create_task(
            self.log_decision(
                decision_type="collaboration_routing",
                reasoning="Selected lowest-load specialist",
                decision=decision_payload,
                confidence=0.8,
                rag_context=None,
            )
        )

        return {
            "selected_agent": selected.agent_id,
            "agent_type": selected.agent_type.value,
            "reasoning": "Selected specialist based on availability",
            "help_request": help_request,
        }

    async def create_gate(
        self, reason: str, context: Dict[str, Any], agent_id: Optional[str]
    ) -> str:
        """Create a human approval gate and return its identifier."""

        gate_payload = {
            "project_id": self.project_id,
            "reason": reason,
            "context": context,
            "agent_id": agent_id,
        }

        if self.gate_manager and hasattr(self.gate_manager, "create_gate"):
            gate_id = await _awaitable(self.gate_manager.create_gate(**gate_payload))
        else:
            gate_id = str(uuid.uuid4())

        self.logger.info(
            "Gate created | gate_id=%s | reason=%s | agent=%s",
            gate_id,
            reason,
            agent_id,
        )
        return gate_id
    
    async def escalate_to_specialist(
        self,
        requesting_agent_id: str,
        question: str,
        context: Dict[str, Any],
        *,
        urgency: str = "normal",
        suggested_specialist: Optional[AgentType] = None
    ) -> Dict[str, Any]:
        """
        Full escalation workflow: route to specialist, deliver response.
        
        This combines collaboration routing with urgency analysis and response
        tracking. Implements the complete agent-to-agent help flow.
        
        Args:
            requesting_agent_id: ID of agent requesting help
            question: The specific question or request
            context: Relevant context (error details, code snippets, etc.)
            urgency: "low", "normal", "high", "critical"
            suggested_specialist: Optional hint about which specialist to use
        
        Returns:
            Dict with escalation_id, selected_specialist, response, outcome
        
        Example:
            result = await orchestrator.escalate_to_specialist(
                requesting_agent_id="backend-1",
                question="How do I handle this authentication error?",
                context={"error": "InvalidToken", "code_location": "auth.py:42"},
                urgency="high"
            )
        """
        escalation_id = str(uuid.uuid4())
        
        self.logger.info(
            "Escalation started | escalation_id=%s | from=%s | urgency=%s",
            escalation_id,
            requesting_agent_id,
            urgency
        )
        
        # 1. Analyze question and determine specialist types
        specialist_types = self._analyze_question_for_specialists(
            question, suggested_specialist
        )
        
        # 2. Build help request structure
        help_request = {
            "escalation_id": escalation_id,
            "requesting_agent_id": requesting_agent_id,
            "question": question,
            "context": context,
            "urgency": urgency,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        
        # 3. Route to best available specialist
        routing_result = self.route_collaboration(
            help_request=help_request,
            specialist_types=specialist_types
        )
        
        selected_specialist_id = routing_result.get("selected_agent")
        
        if not selected_specialist_id:
            # No specialist available - escalate to human gate
            self.logger.warning(
                "No specialist available | escalation_id=%s | creating gate",
                escalation_id
            )
            
            gate_id = await self.create_gate(
                reason="Specialist assistance needed but none available",
                context={
                    "escalation_id": escalation_id,
                    "question": question,
                    "requesting_agent": requesting_agent_id,
                    "context": context
                },
                agent_id=requesting_agent_id
            )
            
            return {
                "escalation_id": escalation_id,
                "status": "escalated_to_human",
                "gate_id": gate_id,
                "specialist": None,
                "response": None,
                "reasoning": "No specialists available, created human gate"
            }
        
        # 4. Log the escalation decision
        await self.log_decision(
            decision_type="specialist_escalation",
            reasoning=f"Question analysis suggests {routing_result.get('agent_type')} expertise",
            decision={
                "action": "escalate_to_specialist",
                "escalation_id": escalation_id,
                "specialist_id": selected_specialist_id,
                "specialist_type": routing_result.get("agent_type"),
                "urgency": urgency,
                "question_preview": question[:100]
            },
            confidence=0.85,
            rag_context=None
        )
        
        # 5. Curate context for specialist (only send relevant parts)
        curated_context = self._curate_context_for_specialist(
            context, routing_result.get("agent_type")
        )
        
        # 6. Deliver request to specialist
        # Note: In real implementation, this would send via message queue or agent interface
        specialist_payload = {
            "type": "help_request",
            "escalation_id": escalation_id,
            "from_agent": requesting_agent_id,
            "question": question,
            "context": curated_context,
            "urgency": urgency
        }
        
        self.logger.info(
            "Request delivered to specialist | escalation_id=%s | specialist=%s",
            escalation_id,
            selected_specialist_id
        )
        
        # 7. Track the collaboration
        # TODO: Persist to collaboration_requests table (Decision 70)
        # For now, store in memory
        if not hasattr(self, '_active_escalations'):
            self._active_escalations = {}
        
        self._active_escalations[escalation_id] = {
            "escalation_id": escalation_id,
            "requesting_agent": requesting_agent_id,
            "specialist": selected_specialist_id,
            "specialist_type": routing_result.get("agent_type"),
            "question": question,
            "context": context,
            "urgency": urgency,
            "status": "awaiting_response",
            "created_at": datetime.now(UTC),
            "payload": specialist_payload
        }
        
        return {
            "escalation_id": escalation_id,
            "status": "routed_to_specialist",
            "specialist_id": selected_specialist_id,
            "specialist_type": routing_result.get("agent_type"),
            "urgency": urgency,
            "reasoning": routing_result.get("reasoning"),
            "awaiting_response": True
        }
    
    def _intelligently_assign_agent_type(self, task: Task) -> AgentType:
        """
        Intelligently assign the best agent type for a task based on its description,
        metadata, and available agents.
        
        This is the core orchestrator intelligence - analyzing task requirements and
        matching them to the right specialist.
        
        Args:
            task: Task that needs agent assignment
            
        Returns:
            AgentType best suited for the task
        """
        # Get task info for analysis
        description = task.description.lower() if task.description else ""
        deliverable_type = task.metadata.get("deliverable_type", "").lower() if task.metadata else ""
        title = task.metadata.get("deliverable_title", "").lower() if task.metadata else ""
        
        # Combine all context for intelligent analysis
        full_context = f"{description} {deliverable_type} {title}"
        
        # Use specialist analysis logic
        potential_agents = self._analyze_question_for_specialists(full_context)
        
        # Return the first recommended agent, or fallback to workshopper
        if potential_agents:
            selected = potential_agents[0]
            self.logger.info(
                f"Task {task.task_id}: Selected {selected.value} based on analysis of: {deliverable_type} - {title}"
            )
            return selected
        
        # Default fallback
        return AgentType.WORKSHOPPER
    
    def _analyze_question_for_specialists(
        self,
        question: str,
        suggested_specialist: Optional[AgentType] = None
    ) -> List[AgentType]:
        """
        Analyze question content to suggest specialist types.
        
        Uses keyword matching to determine which specialists might help.
        Orchestrator can override the suggested_specialist if inappropriate.
        """
        question_lower = question.lower()
        
        # Keyword-based routing (simple for now, can be enhanced with LLM)
        if any(word in question_lower for word in ['security', 'auth', 'vulnerability', 'permission', 'xss', 'sql injection']):
            return [AgentType.SECURITY_EXPERT, AgentType.BACKEND_DEVELOPER]
        
        elif any(word in question_lower for word in ['deploy', 'docker', 'infrastructure', 'ci/cd', 'kubernetes']):
            return [AgentType.DEVOPS_ENGINEER, AgentType.BACKEND_DEVELOPER]
        
        elif any(word in question_lower for word in ['api', 'database', 'backend', 'server', 'endpoint']):
            return [AgentType.BACKEND_DEVELOPER, AgentType.DEVOPS_ENGINEER]
        
        elif any(word in question_lower for word in ['ui', 'frontend', 'react', 'component', 'css', 'styling']):
            return [AgentType.FRONTEND_DEVELOPER, AgentType.UI_UX_DESIGNER]
        
        elif any(word in question_lower for word in ['test', 'qa', 'bug', 'quality']):
            return [AgentType.QA_ENGINEER, AgentType.BACKEND_DEVELOPER]
        
        elif any(word in question_lower for word in ['documentation', 'readme', 'docs', 'guide']):
            return [AgentType.DOCUMENTATION_EXPERT]
        
        elif any(word in question_lower for word in ['git', 'github', 'pull request', 'commit', 'branch']):
            return [AgentType.GITHUB_SPECIALIST]
        
        elif suggested_specialist:
            # Use suggestion if provided and no keywords matched
            return [suggested_specialist]
        
        else:
            # Default: try backend dev and workshopper as generalists
            return [AgentType.BACKEND_DEVELOPER, AgentType.WORKSHOPPER]
    
    def _curate_context_for_specialist(
        self,
        context: Dict[str, Any],
        specialist_type: Optional[str]
    ) -> Dict[str, Any]:
        """
        Filter context to only send relevant information to specialist.
        
        Prevents overwhelming specialists with unnecessary context.
        """
        # For now, pass most context through, but limit sizes
        curated = {}
        
        for key, value in context.items():
            # Limit string lengths
            if isinstance(value, str) and len(value) > 1000:
                curated[key] = value[:1000] + "... (truncated)"
            # Limit list lengths
            elif isinstance(value, list) and len(value) > 10:
                curated[key] = value[:10] + ["... (truncated)"]
            else:
                curated[key] = value
        
        return curated
    
    async def deliver_specialist_response(
        self,
        escalation_id: str,
        response: str,
        specialist_id: str,
        *,
        confidence: float = 0.8,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Deliver specialist's response back to requesting agent.
        
        Args:
            escalation_id: ID of the escalation
            response: Specialist's answer/guidance
            specialist_id: ID of responding specialist
            confidence: Specialist's confidence in their response (0-1)
            additional_context: Optional additional context from specialist
        
        Returns:
            Outcome dict with delivery status
        """
        if not hasattr(self, '_active_escalations'):
            self._active_escalations = {}
        
        escalation = self._active_escalations.get(escalation_id)
        
        if not escalation:
            self.logger.warning(
                "Unknown escalation | escalation_id=%s",
                escalation_id
            )
            return {
                "status": "error",
                "message": "Escalation not found"
            }
        
        requesting_agent_id = escalation["requesting_agent"]
        
        self.logger.info(
            "Delivering response | escalation_id=%s | to=%s | confidence=%.2f",
            escalation_id,
            requesting_agent_id,
            confidence
        )
        
        # Update escalation status
        escalation["status"] = "completed"
        escalation["response"] = response
        escalation["specialist_confidence"] = confidence
        escalation["completed_at"] = datetime.now(UTC)
        
        # Record the outcome
        # TODO: Persist to collaboration_outcomes table (Decision 70)
        
        # Log the outcome
        await self.log_decision(
            decision_type="collaboration_outcome",
            reasoning=f"Specialist provided response with {confidence:.0%} confidence",
            decision={
                "action": "deliver_response",
                "escalation_id": escalation_id,
                "specialist_id": specialist_id,
                "requesting_agent": requesting_agent_id,
                "confidence": confidence,
                "response_length": len(response)
            },
            confidence=confidence,
            rag_context=None
        )
        
        return {
            "status": "delivered",
            "escalation_id": escalation_id,
            "requesting_agent": requesting_agent_id,
            "specialist": specialist_id,
            "response": response,
            "confidence": confidence,
            "outcome": "success"
        }
    
    async def evaluate_goal_proximity(
        self,
        task_goal: str,
        current_state: str,
        *,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate how close current state is to achieving task goal using LLM.
        
        This is a fallback method when quantifiable metrics are not available.
        Uses LLM to analyze progress and provide proximity score.
        
        Args:
            task_goal: What the task is trying to achieve
            current_state: Current state description
            additional_context: Optional extra context
        
        Returns:
            Dict with proximity_score (0-1), reasoning, confidence
        
        Example:
            result = await orchestrator.evaluate_goal_proximity(
                task_goal="Create user authentication API",
                current_state="Created login endpoint, working on logout"
            )
            # Returns: {"proximity_score": 0.6, "reasoning": "...", "confidence": 0.7}
        """
        self.logger.info(
            "Evaluating goal proximity | goal=%s | state=%s",
            task_goal[:50],
            current_state[:50]
        )
        
        # Build prompt for LLM
        prompt = self._build_proximity_prompt(
            task_goal=task_goal,
            current_state=current_state,
            additional_context=additional_context
        )
        
        try:
            # Call LLM (using OpenAI adapter if available)
            if hasattr(self, 'openai_adapter') and self.openai_adapter:
                response = await self._call_llm_for_proximity(prompt)
                return self._parse_proximity_response(response)
            else:
                # Fallback: heuristic evaluation
                return self._heuristic_proximity_evaluation(task_goal, current_state)
        
        except Exception as e:
            self.logger.error("Goal proximity evaluation failed: %s", e)
            return {
                "proximity_score": 0.5,  # Neutral score on error
                "reasoning": f"Evaluation failed: {str(e)}",
                "confidence": 0.0
            }
    
    def _build_proximity_prompt(
        self,
        task_goal: str,
        current_state: str,
        additional_context: Optional[Dict[str, Any]]
    ) -> str:
        """Build LLM prompt for goal proximity evaluation."""
        context_str = ""
        if additional_context:
            context_str = f"\n\nAdditional Context:\n{additional_context}"
        
        prompt = f"""You are evaluating progress toward a task goal.

Task Goal:
{task_goal}

Current State:
{current_state}{context_str}

Analyze the current state relative to the goal and provide:
1. A proximity score from 0 to 1 (0 = no progress, 1 = goal achieved)
2. Clear reasoning for your score
3. Specific evidence from the current state

Respond in this format:
SCORE: <0.0 to 1.0>
REASONING: <your explanation>
EVIDENCE: <specific points from current state>
"""
        return prompt
    
    async def _call_llm_for_proximity(self, prompt: str) -> str:
        """Call LLM to evaluate proximity."""
        # This would use the OpenAI adapter
        # Placeholder for now
        return "SCORE: 0.5\nREASONING: Partial progress\nEVIDENCE: Some work completed"
    
    def _parse_proximity_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured format."""
        import re
        
        # Extract score
        score_match = re.search(r'SCORE:\s*([\d.]+)', response)
        score = float(score_match.group(1)) if score_match else 0.5
        score = max(0.0, min(1.0, score))  # Clamp to 0-1
        
        # Extract reasoning
        reasoning_match = re.search(r'REASONING:\s*(.+?)(?=EVIDENCE:|$)', response, re.DOTALL)
        reasoning = reasoning_match.group(1).strip() if reasoning_match else "No reasoning provided"
        
        # Extract evidence
        evidence_match = re.search(r'EVIDENCE:\s*(.+?)$', response, re.DOTALL)
        evidence = evidence_match.group(1).strip() if evidence_match else ""
        
        # Confidence based on how well-formed the response is
        confidence = 0.8 if score_match and reasoning_match else 0.5
        
        return {
            "proximity_score": score,
            "reasoning": reasoning,
            "evidence": evidence,
            "confidence": confidence
        }
    
    def _heuristic_proximity_evaluation(
        self,
        task_goal: str,
        current_state: str
    ) -> Dict[str, Any]:
        """
        Fallback heuristic evaluation when LLM not available.
        
        Uses simple keyword matching and length comparison.
        """
        # Simple heuristic: check for goal keywords in current state
        goal_words = set(task_goal.lower().split())
        state_words = set(current_state.lower().split())
        
        # Calculate word overlap
        overlap = goal_words.intersection(state_words)
        overlap_ratio = len(overlap) / len(goal_words) if goal_words else 0
        
        # Estimate proximity based on overlap
        proximity_score = min(0.9, overlap_ratio * 1.2)  # Cap at 0.9
        
        reasoning = f"Keyword overlap: {len(overlap)}/{len(goal_words)} goal terms found in current state"
        
        return {
            "proximity_score": proximity_score,
            "reasoning": reasoning,
            "evidence": f"Matching terms: {', '.join(list(overlap)[:5])}",
            "confidence": 0.4  # Low confidence for heuristic
        }
    
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
