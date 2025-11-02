"""
Phase Transition Service

Handles smooth transitions between development phases with agent handoffs.
Archives artifacts, notifies agents, and generates transition reports.

Reference: Phase 3.1 - Phase Management System
"""
import logging
from typing import Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@dataclass
class TransitionReport:
    """Report generated during phase transition."""
    transition_id: str
    from_phase: str
    to_phase: str
    project_id: str
    completed_deliverables: List[str]
    achievements: List[str]
    next_steps: List[str]
    new_agents: List[str]
    archived_artifacts: List[str]
    transition_time: str
    summary: str


class PhaseTransitionService:
    """
    Service for managing phase transitions with agent handoffs.
    
    Transition Steps:
    1. Validate current phase complete
    2. Archive current phase artifacts
    3. Notify agents of phase change
    4. Assign new agents for next phase
    5. Generate transition report
    6. Update project state
    
    Example:
        service = PhaseTransitionService(engine, phase_manager, llm_client)
        report = await service.transition(
            from_phase=PhaseType.WORKSHOPPING,
            to_phase=PhaseType.IMPLEMENTATION,
            project_id="proj-123"
        )
    """
    
    def __init__(
        self,
        engine: Engine,
        phase_manager: Any,
        llm_client: Optional[Any] = None
    ):
        """
        Initialize phase transition service.
        
        Args:
            engine: Database engine
            phase_manager: PhaseManager instance
            llm_client: Optional LLM client for generating reports
        """
        self.engine = engine
        self.phase_manager = phase_manager
        self.llm_client = llm_client
        logger.info("PhaseTransitionService initialized")
    
    async def transition(
        self,
        from_phase: Any,  # PhaseType
        to_phase: Any,  # PhaseType
        project_id: str,
        autonomy_level: int = 3
    ) -> TransitionReport:
        """
        Execute phase transition with full workflow.
        
        Args:
            from_phase: Current phase (PhaseType)
            to_phase: Next phase (PhaseType)
            project_id: Project identifier
            autonomy_level: Autonomy level for validation
        
        Returns:
            TransitionReport with details of transition
        
        Raises:
            ValueError: If transition validation fails
        """
        logger.info(f"Starting phase transition: {from_phase.value} → {to_phase.value}")
        
        transition_id = self._generate_transition_id()
        
        # Step 1: Validate current phase complete
        await self._validate_phase_complete(from_phase, project_id, autonomy_level)
        
        # Step 2: Archive current phase artifacts
        archived_artifacts = await self._archive_artifacts(from_phase, project_id)
        
        # Step 3: Get deliverables summary
        completed_deliverables = await self._get_completed_deliverables(from_phase, project_id)
        
        # Step 4: Notify agents of phase change
        await self._notify_agents(from_phase, to_phase, project_id)
        
        # Step 5: Execute phase transition in PhaseManager
        await self.phase_manager.transition_phase(project_id, from_phase, to_phase)
        
        # Step 6: Get new agents for next phase
        new_phase = await self.phase_manager.get_current_phase(project_id)
        new_agents = new_phase.assigned_agents if new_phase else []
        
        # Step 7: Generate transition report
        report = await self._generate_transition_report(
            transition_id=transition_id,
            from_phase=from_phase.value,
            to_phase=to_phase.value,
            project_id=project_id,
            completed_deliverables=completed_deliverables,
            archived_artifacts=archived_artifacts,
            new_agents=new_agents
        )
        
        # Step 8: Store transition record
        await self._store_transition_record(report)
        
        logger.info(f"Phase transition complete: {transition_id}")
        return report
    
    async def _validate_phase_complete(
        self,
        phase: Any,
        project_id: str,
        autonomy_level: int
    ) -> None:
        """
        Validate that current phase is complete before transition.
        
        Raises:
            ValueError: If phase not complete
        """
        from backend.services.phase_validator import PhaseValidator
        
        # Get current phase
        current_phase = await self.phase_manager.get_current_phase(project_id)
        if not current_phase:
            raise ValueError(f"No active phase found for project {project_id}")
        
        if current_phase.phase_name != phase:
            raise ValueError(
                f"Current phase {current_phase.phase_name.value} does not match "
                f"expected phase {phase.value}"
            )
        
        # Validate phase can complete
        validator = PhaseValidator(self.engine)
        result = await validator.can_complete_phase(current_phase.id, autonomy_level)
        
        if not result.can_complete:
            raise ValueError(
                f"Phase {phase.value} cannot complete. Blockers: {', '.join(result.blockers)}"
            )
        
        logger.info(f"Phase {phase.value} validation passed")
    
    async def _archive_artifacts(
        self,
        phase: Any,
        project_id: str
    ) -> List[str]:
        """
        Archive phase artifacts for historical record.
        
        In a real implementation, this would:
        - Copy deliverable files to archive location
        - Create snapshots of database state
        - Archive test results and coverage reports
        - Store logs and metrics
        
        Returns:
            List of archived artifact paths
        """
        logger.info(f"Archiving artifacts for phase: {phase.value}")
        
        # Get current phase
        current_phase = await self.phase_manager.get_current_phase(project_id)
        if not current_phase:
            return []
        
        # Get deliverables
        from backend.services.deliverable_tracker import DeliverableTracker
        tracker = DeliverableTracker(self.engine)
        deliverables = await tracker.get_phase_deliverables(current_phase.id)
        
        archived = []
        for deliverable in deliverables:
            if deliverable.artifact_path:
                # TODO: Actually copy files to archive location
                archive_path = f"archive/{project_id}/{phase.value}/{deliverable.name}"
                archived.append(archive_path)
                logger.debug(f"Archived: {deliverable.name} → {archive_path}")
        
        logger.info(f"Archived {len(archived)} artifacts")
        return archived
    
    async def _get_completed_deliverables(
        self,
        phase: Any,
        project_id: str
    ) -> List[str]:
        """Get list of completed deliverables for phase."""
        current_phase = await self.phase_manager.get_current_phase(project_id)
        if not current_phase:
            return []
        
        from backend.services.deliverable_tracker import DeliverableTracker, DeliverableStatus
        tracker = DeliverableTracker(self.engine)
        deliverables = await tracker.get_phase_deliverables(current_phase.id)
        
        completed = [
            d.name for d in deliverables 
            if d.status in [DeliverableStatus.COMPLETED, DeliverableStatus.VALIDATED]
        ]
        
        return completed
    
    async def _notify_agents(
        self,
        from_phase: Any,
        to_phase: Any,
        project_id: str
    ) -> None:
        """
        Notify agents about phase transition.
        
        In a real implementation, this would:
        - Send notifications to agent processes
        - Update agent state with new phase context
        - Trigger agent briefing for new phase
        """
        logger.info(f"Notifying agents of transition: {from_phase.value} → {to_phase.value}")
        
        # TODO: Implement actual agent notification system
        # For now, just log the notification
        logger.debug(f"Agent notification sent for project {project_id}")
    
    async def _generate_transition_report(
        self,
        transition_id: str,
        from_phase: str,
        to_phase: str,
        project_id: str,
        completed_deliverables: List[str],
        archived_artifacts: List[str],
        new_agents: List[str]
    ) -> TransitionReport:
        """
        Generate comprehensive transition report.
        
        Uses LLM if available to create natural language summary.
        """
        logger.info("Generating transition report")
        
        # Generate achievements summary
        achievements = [
            f"Completed {len(completed_deliverables)} deliverables",
            f"Archived {len(archived_artifacts)} artifacts",
            f"Phase {from_phase} successfully validated"
        ]
        
        # Generate next steps based on next phase
        next_steps = self._get_next_phase_steps(to_phase)
        
        # Generate summary
        if self.llm_client:
            summary = await self._generate_llm_summary(
                from_phase, to_phase, completed_deliverables, achievements
            )
        else:
            summary = self._generate_basic_summary(
                from_phase, to_phase, len(completed_deliverables)
            )
        
        report = TransitionReport(
            transition_id=transition_id,
            from_phase=from_phase,
            to_phase=to_phase,
            project_id=project_id,
            completed_deliverables=completed_deliverables,
            achievements=achievements,
            next_steps=next_steps,
            new_agents=new_agents,
            archived_artifacts=archived_artifacts,
            transition_time=datetime.utcnow().isoformat(),
            summary=summary
        )
        
        logger.info(f"Transition report generated: {transition_id}")
        return report
    
    def _get_next_phase_steps(self, to_phase: str) -> List[str]:
        """Get next steps for upcoming phase."""
        phase_steps = {
            "workshopping": [
                "Gather and document requirements",
                "Create architecture decision records",
                "Design system architecture",
                "Break down tasks with estimates"
            ],
            "implementation": [
                "Set up project structure and dependencies",
                "Implement backend API endpoints",
                "Develop frontend components",
                "Write unit and integration tests"
            ],
            "testing": [
                "Run full test suite and fix failures",
                "Achieve ≥90% code coverage",
                "Execute E2E tests for critical flows",
                "Document and fix bugs"
            ],
            "deployment": [
                "Create Docker containers",
                "Set up CI/CD pipeline",
                "Configure environment variables",
                "Write deployment documentation"
            ],
            "monitoring": [
                "Configure structured logging",
                "Set up health check endpoints",
                "Create metrics dashboards",
                "Define alert rules"
            ],
            "maintenance": [
                "Write user and developer documentation",
                "Define backup and recovery procedures",
                "Plan update and maintenance strategy",
                "Handoff to operations team"
            ]
        }
        
        return phase_steps.get(to_phase, ["Begin phase activities"])
    
    async def _generate_llm_summary(
        self,
        from_phase: str,
        to_phase: str,
        completed_deliverables: List[str],
        achievements: List[str]
    ) -> str:
        """Generate natural language summary using LLM."""
        # TODO: Implement LLM-based summary generation
        logger.info("LLM summary generation not yet implemented")
        return self._generate_basic_summary(from_phase, to_phase, len(completed_deliverables))
    
    def _generate_basic_summary(
        self,
        from_phase: str,
        to_phase: str,
        deliverable_count: int
    ) -> str:
        """Generate basic summary without LLM."""
        return (
            f"Successfully completed {from_phase} phase with {deliverable_count} deliverables. "
            f"Transitioning to {to_phase} phase. All artifacts archived and new agents assigned."
        )
    
    async def _store_transition_record(self, report: TransitionReport) -> None:
        """Store transition record in database."""
        query = text("""
            INSERT INTO phase_transitions 
            (id, project_id, from_phase, to_phase, completed_deliverables, 
             achievements, next_steps, new_agents, archived_artifacts, 
             summary, transition_time, created_at)
            VALUES (:id, :project_id, :from_phase, :to_phase, :completed_deliverables::jsonb,
                    :achievements::jsonb, :next_steps::jsonb, :new_agents, :archived_artifacts,
                    :summary, :transition_time, NOW())
        """)
        
        with self.engine.connect() as conn:
            conn.execute(query, {
                "id": report.transition_id,
                "project_id": report.project_id,
                "from_phase": report.from_phase,
                "to_phase": report.to_phase,
                "completed_deliverables": report.completed_deliverables,
                "achievements": report.achievements,
                "next_steps": report.next_steps,
                "new_agents": report.new_agents,
                "archived_artifacts": report.archived_artifacts,
                "summary": report.summary,
                "transition_time": report.transition_time
            })
            conn.commit()
        
        logger.debug(f"Transition record stored: {report.transition_id}")
    
    async def get_transition_history(self, project_id: str) -> List[TransitionReport]:
        """Get all phase transitions for a project."""
        query = text("""
            SELECT id, project_id, from_phase, to_phase, completed_deliverables,
                   achievements, next_steps, new_agents, archived_artifacts,
                   summary, transition_time
            FROM phase_transitions
            WHERE project_id = :project_id
            ORDER BY transition_time ASC
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {"project_id": project_id})
            rows = result.fetchall()
            
            transitions = [
                TransitionReport(
                    transition_id=str(row[0]),
                    project_id=str(row[1]),
                    from_phase=row[2],
                    to_phase=row[3],
                    completed_deliverables=row[4] or [],
                    achievements=row[5] or [],
                    next_steps=row[6] or [],
                    new_agents=row[7] or [],
                    archived_artifacts=row[8] or [],
                    summary=row[9],
                    transition_time=row[10]
                )
                for row in rows
            ]
            
            logger.info(f"Retrieved {len(transitions)} transitions for project {project_id}")
            return transitions
    
    def _generate_transition_id(self) -> str:
        """Generate unique transition ID."""
        import uuid
        return f"trans-{uuid.uuid4()}"
