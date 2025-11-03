"""
Project Build Service

Top-level orchestration layer coordinating entire build process.
Ties together: DB → MilestoneGenerator → PhaseManager → Orchestrator → Agents → EventBus

Reference: Phase 3.5 - Backend Integration
"""
import logging
import asyncio
from typing import Optional, Any, Dict, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from backend.services.event_bus import EventBus, Event, EventType, get_event_bus
from backend.services.milestone_generator import MilestoneGenerator
from backend.services.phase_manager import PhaseManager
from backend.services.orchestrator import Orchestrator
from backend.services.agent_factory import AgentFactory
from backend.services.task_executor import TaskExecutor

logger = logging.getLogger(__name__)


class BuildStatus(str, Enum):
    """Build status values."""
    INITIALIZING = "initializing"
    PLANNING = "planning"
    BUILDING = "building"
    TESTING = "testing"
    DEPLOYING = "deploying"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BuildProgress:
    """Build progress information."""
    project_id: str
    status: BuildStatus
    current_phase: str
    progress_percent: float
    active_agent: Optional[str]
    last_event: Optional[str]
    started_at: str
    updated_at: str


class ProjectBuildService:
    """
    Top-level service coordinating entire project build process.
    
    Workflow:
    1. User submits project request
    2. Create project in database
    3. Generate milestones and deliverables (MilestoneGenerator)
    4. Initialize phase manager
    5. Create and start orchestrator
    6. Register all agents
    7. Begin task delegation
    8. Stream progress via EventBus
    9. Handle phase transitions
    10. Complete build or handle failures
    
    Example:
        service = ProjectBuildService(db_engine, llm_client)
        
        # Start build
        project_id = await service.start_build(
            description="Build a todo app with React and FastAPI",
            tech_stack={"frontend": "react", "backend": "fastapi"}
        )
        
        # Monitor progress
        progress = await service.get_build_status(project_id)
        print(f"Progress: {progress.progress_percent}%")
        
        # Pause if needed
        await service.pause_build(project_id)
    """
    
    def __init__(
        self,
        db_engine: Any,
        llm_client: Any,
        event_bus: Optional[EventBus] = None
    ):
        """
        Initialize project build service.
        
        Args:
            db_engine: SQLAlchemy engine
            llm_client: LLM client for agents
            event_bus: Optional event bus (uses global if not provided)
        """
        self.db_engine = db_engine
        self.event_bus = event_bus or get_event_bus()
        
        # Create AgentLLMClient if none provided
        if llm_client is None:
            import os
            from backend.services.agent_llm_client import AgentLLMClient
            from backend.services.openai_adapter import OpenAIAdapter
            
            # Get API key from environment or service
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OPENAI_API_KEY not found in environment, trying api_key_service")
                from backend.services.api_key_service import get_api_key
                api_key = get_api_key(db_engine, "openai")
            
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment or database. Please set it.")
            
            # Create OpenAI adapter with API key
            openai_adapter = OpenAIAdapter(api_key=api_key)
            self.llm_client = AgentLLMClient(openai_adapter)
            logger.info("Created default AgentLLMClient with OpenAI adapter")
        else:
            self.llm_client = llm_client
        
        # Service dependencies
        self.milestone_generator = MilestoneGenerator(db_engine, self.llm_client)
        self.agent_factory = AgentFactory(db_engine)
        
        # Active builds: {project_id: (orchestrator, phase_manager, task_executor)}
        self.active_builds: Dict[str, Tuple[Orchestrator, PhaseManager, TaskExecutor]] = {}
        
        logger.info("ProjectBuildService initialized")
    
    async def start_build(
        self,
        description: str,
        tech_stack: Dict[str, str],
        user_id: Optional[str] = None,
        auto_approve_gates: bool = False
    ) -> str:
        """
        Start a new project build.
        
        Args:
            description: Project description
            tech_stack: Technology stack choices
            user_id: Optional user identifier
            auto_approve_gates: Whether to auto-approve gates
        
        Returns:
            project_id
        """
        logger.info(f"Starting build: {description[:100]}...")
        
        # 0. Run startup safety checks
        from backend.services.startup_checks import StartupChecker
        
        logger.info("=" * 80)
        logger.info("RUNNING BUILD SAFETY CHECKS")
        logger.info("=" * 80)
        
        checker = StartupChecker()
        checks_passed = await checker.run_all_checks()
        
        # Generate project_id first (needed for events)
        import uuid
        project_id = f"proj-{uuid.uuid4()}"
        
        # Publish check results as events
        for service_name, result in checker.results.items():
            status = "available" if result["available"] else "unavailable"
            await self.event_bus.publish(Event(
                event_type=EventType.SYSTEM_CHECK,
                project_id=project_id,
                data={
                    "service": service_name,
                    "status": status,
                    "message": result["message"],
                    "required": result.get("required", False)
                }
            ))
        
        if not checks_passed:
            error_msg = "Required services not available for build"
            await self.event_bus.publish(Event(
                event_type=EventType.PROJECT_FAILED,
                project_id=project_id,
                data={"error": error_msg}
            ))
            raise RuntimeError(error_msg)
        
        logger.info("✅ All required services available - proceeding with build")
        logger.info("=" * 80)
        
        # 1. Create project in database
        await self._create_project(description, tech_stack, project_id)
        
        # 2. Initialize event bus subscription for this project
        await self.event_bus.publish(Event(
            event_type=EventType.PROJECT_CREATED,
            project_id=project_id,
            data={"description": description, "tech_stack": tech_stack}
        ))
        
        # 3. Generate milestones and deliverables
        await self.event_bus.publish(Event(
            event_type=EventType.PROJECT_STARTED,
            project_id=project_id,
            data={"status": "planning"}
        ))
        
        # Store project description for later use in tasks
        self.project_descriptions = getattr(self, 'project_descriptions', {})
        self.project_descriptions[project_id] = {
            'description': description,
            'requirements': None
        }
        
        # Create project-level container for file operations
        from backend.services.container_manager import get_container_manager
        container_mgr = get_container_manager()
        
        logger.info(f"Creating project container for {project_id}")
        container_result = await container_mgr.create_container(
            task_id=project_id,  # Use project_id as container identifier
            project_id=project_id,
            language="python"  # Default container for file operations
        )
        
        if not container_result.get("success"):
            logger.warning(f"Failed to create project container: {container_result.get('message')}")
            logger.warning("File operations may fail without container")
        else:
            logger.info(f"✅ Project container created for {project_id}")
        
        # Generate project plan with milestones
        project_plan = await self.milestone_generator.generate_project_plan(
            project_id=project_id,
            project_description=description
        )
        
        # Convert milestones to dict format for PhaseManager
        # Milestones are organized by phase in the plan
        milestones_dict = []
        for phase in project_plan.phases:
            for milestone in phase.milestones:
                # Convert deliverable strings to dict format expected by DeliverableTracker
                deliverables_list = []
                for deliverable_name in milestone.deliverables:
                    deliverables_list.append({
                        "title": deliverable_name,
                        "description": f"Deliverable: {deliverable_name}",
                        "type": "implementation",
                        "dependencies": []
                    })
                
                milestone_dict = {
                    "id": milestone.id,
                    "title": milestone.name,
                    "description": milestone.description,
                    "phase": milestone.phase_name,
                    "deliverables": deliverables_list
                }
                milestones_dict.append(milestone_dict)
        
        # 4. Initialize phase manager
        phase_manager = PhaseManager(
            engine=self.db_engine,
            project_id=project_id
        )
        await phase_manager.initialize(milestones_dict)
        
        # 5. Create orchestrator with TAS client
        from backend.services.tool_access_service import ToolAccessService
        tas_client = ToolAccessService(db_session=None, use_db=False)  # In-memory for now
        
        orchestrator = Orchestrator(
            project_id=project_id,
            llm_client=self.llm_client,
            tas_client=tas_client
        )
        
        # 6. Register all agents
        agents = await self.agent_factory.create_and_register_all_agents(
            orchestrator=orchestrator,
            llm_client=self.llm_client
        )
        
        # 7. Create task executor for running agents (single worker for synchronous execution)
        task_executor = TaskExecutor(
            orchestrator=orchestrator,
            event_bus=self.event_bus,
            max_workers=1,  # Single worker for sequential execution
            phase_manager=phase_manager  # Pass phase_manager for deliverable tracking
        )
        
        # Register agent instances with executor
        for agent in agents:
            task_executor.register_agent_instance(agent.agent_id, agent)
        
        # Start executor worker loops
        await task_executor.start()
        
        await self.event_bus.publish(Event(
            event_type=EventType.PROJECT_STARTED,
            project_id=project_id,
            data={
                "status": "building",
                "agents_count": len(agents),
                "milestones_count": len(milestones_dict)
            }
        ))
        
        # 8. Store active build
        self.active_builds[project_id] = (orchestrator, phase_manager, task_executor)
        
        # 9. Start build loop (async)
        asyncio.create_task(self._run_build_loop(project_id))
        
        logger.info(f"Build started: {project_id}")
        return project_id
    
    async def _run_build_loop(self, project_id: str) -> None:
        """
        Main build loop - runs until build completes or fails.
        
        Args:
            project_id: Project identifier
        """
        try:
            orchestrator, phase_manager, task_executor = self.active_builds[project_id]
            
            while True:
                # Check if build complete
                if phase_manager.is_complete():
                    await self._handle_build_complete(project_id)
                    break
                
                # Get next deliverables for current phase
                deliverables = await phase_manager.get_pending_deliverables()
                
                if not deliverables:
                    # Phase complete, transition
                    transitioned = await phase_manager.try_phase_transition()
                    if transitioned:
                        await self.event_bus.publish(Event(
                            event_type=EventType.PHASE_COMPLETED,
                            project_id=project_id,
                            data={"phase": phase_manager.current_phase}
                        ))
                        continue
                    else:
                        # No deliverables and can't transition - wait
                        await asyncio.sleep(5)
                        continue
                
                # Create ONE task at a time and wait for it to complete
                if deliverables:
                    deliverable = deliverables[0]  # Take only the first one
                    await self._create_task_from_deliverable(
                        orchestrator, deliverable, project_id
                    )
                    
                    # Wait for this task to complete before processing next
                    await asyncio.sleep(2)  # Give it time to start
                    
                    # Wait for queue to be empty (task completed)
                    while not orchestrator.task_queue.empty():
                        await asyncio.sleep(0.5)
                    
                    # CRITICAL: Wait for database commit from mark_completed() to finish
                    # The agent's mark_completed() happens AFTER task is removed from queue
                    await asyncio.sleep(1)
                
                # Brief pause between iterations
                await asyncio.sleep(0.5)
        
        except Exception as e:
            logger.error(f"Build loop error: {e}", exc_info=True)
            await self._handle_build_error(project_id, str(e))
    
    async def _create_task_from_deliverable(
        self,
        orchestrator: Orchestrator,
        deliverable: Dict[str, Any],
        project_id: str
    ) -> None:
        """
        Create and queue a task from a deliverable.
        
        The orchestrator will intelligently assign the task to the appropriate agent
        based on the deliverable content, available agents, and current context.
        
        Args:
            orchestrator: Orchestrator to queue task with
            deliverable: Deliverable dict with id, title, description, type
            project_id: Project ID
        """
        from backend.services.orchestrator import Task, TaskPriority, TaskStatus
        
        # Let orchestrator analyze and decide which agent is best suited
        # Build a rich task description for intelligent agent selection
        task_description = self._build_task_description_for_orchestrator(deliverable)
        
        # Create task WITHOUT agent_type - orchestrator will assign
        task = Task(
            task_id=deliverable["id"],
            description=task_description,
            deliverable_id=deliverable["id"],
            agent_type=None,  # Orchestrator will decide
            priority=TaskPriority.NORMAL,
            status=TaskStatus.PENDING,
            project_id=project_id,
            metadata={
                "deliverable": deliverable,
                "phase": "workshopping",  # TODO: Get from phase manager
                "deliverable_type": deliverable.get("type"),
                "deliverable_title": deliverable.get("title")
            }
        )
        
        # Add to orchestrator queue - orchestrator will intelligently assign agent
        orchestrator.enqueue_task(task)
    
    def _build_task_description_for_orchestrator(self, deliverable: Dict[str, Any]) -> str:
        """
        Build a rich task description that helps the orchestrator intelligently 
        select the right agent based on deliverable content and project context.
        
        Args:
            deliverable: Deliverable dict with id, title, description, type
        
        Returns:
            Rich task description string for orchestrator analysis
        """
        deliverable_type = deliverable.get("type", "deliverable")
        deliverable_title = deliverable.get("title", "Untitled")
        deliverable_desc = deliverable.get("description", "")
        
        # Build rich description for orchestrator to analyze
        description = (
            f"Deliverable: {deliverable_title}\n"
            f"Type: {deliverable_type}\n"
            f"Description: {deliverable_desc}\n\n"
            f"This task requires creating or completing a {deliverable_type} deliverable. "
            f"The orchestrator should select the agent best suited for this type of work."
        )
        
        return description
    async def get_build_status(self, project_id: str) -> BuildProgress:
        """
        Get current build status.
        
        Args:
            project_id: Project identifier
        
        Returns:
            BuildProgress with current state
        """
        if project_id not in self.active_builds:
            # Check database for completed/failed builds
            return BuildProgress(
                project_id=project_id,
                status=BuildStatus.COMPLETED,
                current_phase="unknown",
                progress_percent=100.0,
                active_agent=None,
                last_event=None,
                started_at="",
                updated_at=datetime.utcnow().isoformat()
            )
        
        orchestrator, phase_manager, _ = self.active_builds[project_id]
        
        # Calculate progress
        total_deliverables = await phase_manager.get_total_deliverables()
        completed_deliverables = await phase_manager.get_completed_count()
        progress_percent = (completed_deliverables / total_deliverables * 100) if total_deliverables > 0 else 0
        
        # Get last event
        history = self.event_bus.get_history(project_id, limit=1)
        last_event = history[0].event_type if history else None
        
        return BuildProgress(
            project_id=project_id,
            status=BuildStatus.BUILDING,
            current_phase=phase_manager.current_phase or "initialization",
            progress_percent=progress_percent,
            active_agent=orchestrator.project_state.active_agent_id,
            last_event=last_event,
            started_at="",  # TODO: Get from database
            updated_at=datetime.utcnow().isoformat()
        )
    
    async def pause_build(self, project_id: str) -> bool:
        """Pause active build."""
        if project_id not in self.active_builds:
            return False
        
        await self.event_bus.publish(Event(
            event_type=EventType.PROJECT_PAUSED,
            project_id=project_id
        ))
        
        logger.info(f"Build paused: {project_id}")
        return True
    
    async def cancel_build(self, project_id: str, reason: str = "") -> bool:
        """Cancel active build and cleanup resources."""
        if project_id not in self.active_builds:
            return False
        
        orchestrator, phase_manager, task_executor = self.active_builds.pop(project_id)
        
        # Cleanup (TODO: stop containers, close connections)
        
        await self.event_bus.publish(Event(
            event_type=EventType.PROJECT_FAILED,
            project_id=project_id,
            data={"reason": reason or "Cancelled by user"}
        ))
        
        logger.info(f"Build cancelled: {project_id}")
        return True
    
    async def _create_project(
        self,
        description: str,
        tech_stack: Dict[str, str],
        user_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> str:
        """Create project in database."""
        import uuid
        if not project_id:
            project_id = f"proj-{uuid.uuid4()}"
        
        # TODO: Insert into database
        
        return project_id
    
    async def _handle_build_complete(self, project_id: str) -> None:
        """Handle build completion."""
        logger.info(f"Build complete: {project_id}")
        
        # Stop task executor
        if project_id in self.active_builds:
            _, _, task_executor = self.active_builds[project_id]
            await task_executor.stop()
        
        await self.event_bus.publish(Event(
            event_type=EventType.PROJECT_COMPLETED,
            project_id=project_id,
            data={"status": "completed"}
        ))
        
        # Remove from active builds
        if project_id in self.active_builds:
            del self.active_builds[project_id]
        
        logger.info(f"Build completed: {project_id}")
    
    async def _handle_build_error(
        self,
        project_id: str,
        error: str
    ) -> None:
        """Handle build error."""
        logger.error(f"Build error: {project_id} - {error}")
        
        # Stop task executor
        if project_id in self.active_builds:
            _, _, task_executor = self.active_builds[project_id]
            await task_executor.stop()
        
        await self.event_bus.publish(Event(
            event_type=EventType.PROJECT_FAILED,
            project_id=project_id,
            data={"error": error}
        ))
        # Remove from active builds
        if project_id in self.active_builds:
            del self.active_builds[project_id]
        
        logger.error(f"Build failed: {project_id} - {error}")
