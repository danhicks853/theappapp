"""
Phase Manager Service

Manages the 6-phase development workflow with LLM agent coordination.

Phases:
1. Workshopping - Requirements gathering, design, architecture
2. Implementation - Code development
3. Testing - Test creation and execution
4. Deployment - Containerization, CI/CD setup
5. Monitoring - Observability setup
6. Maintenance - Bug fixes, updates

Reference: Phase 3.1 - Phase Management System
"""
import logging
from typing import List, Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class PhaseType(str, Enum):
    """Phase types in development workflow."""
    WORKSHOPPING = "workshopping"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    MAINTENANCE = "maintenance"


class PhaseStatus(str, Enum):
    """Phase execution status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


@dataclass
class Phase:
    """Phase data model."""
    id: str
    project_id: str
    phase_name: PhaseType
    status: PhaseStatus
    assigned_agents: List[str]
    deliverables: List[Dict[str, Any]]
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: str
    updated_at: str


# Phase-to-Agent mapping
PHASE_AGENT_ASSIGNMENTS = {
    PhaseType.WORKSHOPPING: [
        "project_manager",
        "workshopper",
        "backend_dev",
        "frontend_dev"
    ],
    PhaseType.IMPLEMENTATION: [
        "project_manager",
        "backend_dev",
        "frontend_dev",
        "devops_engineer"
    ],
    PhaseType.TESTING: [
        "project_manager",
        "qa_engineer",
        "backend_dev",
        "frontend_dev"
    ],
    PhaseType.DEPLOYMENT: [
        "project_manager",
        "devops_engineer",
        "backend_dev"
    ],
    PhaseType.MONITORING: [
        "project_manager",
        "devops_engineer",
        "backend_dev"
    ],
    PhaseType.MAINTENANCE: [
        "project_manager",
        "backend_dev",
        "frontend_dev",
        "devops_engineer"
    ]
}


class PhaseManager:
    """
    Service for managing 6-phase development workflow.
    
    Features:
    - Start phases with designated agents
    - Track phase progress
    - Validate phase completion
    - Handle phase transitions
    - Prevent phase skipping
    
    Example:
        phase_mgr = PhaseManager(engine)
        phase = await phase_mgr.start_phase("proj-123", PhaseType.WORKSHOPPING)
        current = await phase_mgr.get_current_phase("proj-123")
        can_complete = await phase_mgr.complete_phase("proj-123", PhaseType.WORKSHOPPING)
    """
    
    # Phase order (cannot skip)
    PHASE_ORDER = [
        PhaseType.WORKSHOPPING,
        PhaseType.IMPLEMENTATION,
        PhaseType.TESTING,
        PhaseType.DEPLOYMENT,
        PhaseType.MONITORING,
        PhaseType.MAINTENANCE
    ]
    
    def __init__(self, engine: Engine):
        """Initialize phase manager with database engine."""
        self.engine = engine
        logger.info("PhaseManager initialized")
    
    async def start_phase(
        self,
        project_id: str,
        phase_name: PhaseType
    ) -> Phase:
        """
        Initialize a new phase with designated agents.
        
        Args:
            project_id: Project identifier
            phase_name: Phase to start
        
        Returns:
            Created Phase object
        
        Raises:
            ValueError: If trying to skip phases or phase already started
        """
        logger.info(f"Starting phase: project={project_id}, phase={phase_name.value}")
        
        # Validate phase order
        await self._validate_phase_order(project_id, phase_name)
        
        # Get assigned agents for this phase
        assigned_agents = PHASE_AGENT_ASSIGNMENTS.get(phase_name, [])
        
        query = text("""
            INSERT INTO phases (project_id, phase_name, status, assigned_agents, started_at, created_at, updated_at)
            VALUES (:project_id, :phase_name, :status, :assigned_agents, NOW(), NOW(), NOW())
            RETURNING id, project_id, phase_name, status, assigned_agents, started_at, completed_at, created_at, updated_at
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                "project_id": project_id,
                "phase_name": phase_name.value,
                "status": PhaseStatus.IN_PROGRESS.value,
                "assigned_agents": assigned_agents
            })
            conn.commit()
            
            row = result.first()
            phase = self._row_to_phase(row)
            
            logger.info(f"Phase started: id={phase.id}, agents={len(assigned_agents)}")
            return phase
    
    async def get_current_phase(self, project_id: str) -> Optional[Phase]:
        """
        Get the currently active phase for a project.
        
        Args:
            project_id: Project identifier
        
        Returns:
            Current Phase or None if no active phase
        """
        query = text("""
            SELECT id, project_id, phase_name, status, assigned_agents, started_at, completed_at, created_at, updated_at
            FROM phases
            WHERE project_id = :project_id AND status = :status
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                "project_id": project_id,
                "status": PhaseStatus.IN_PROGRESS.value
            })
            row = result.first()
            
            if row:
                return self._row_to_phase(row)
            else:
                logger.warning(f"No active phase for project: {project_id}")
                return None
    
    async def complete_phase(
        self,
        project_id: str,
        phase_name: PhaseType
    ) -> bool:
        """
        Mark a phase as completed.
        
        Note: This just updates the status. Validation should be done
        separately via PhaseValidator.
        
        Args:
            project_id: Project identifier
            phase_name: Phase to complete
        
        Returns:
            True if completed successfully, False if not found or already completed
        """
        logger.info(f"Completing phase: project={project_id}, phase={phase_name.value}")
        
        query = text("""
            UPDATE phases
            SET status = :completed_status,
                completed_at = NOW(),
                updated_at = NOW()
            WHERE project_id = :project_id 
              AND phase_name = :phase_name 
              AND status = :in_progress_status
            RETURNING id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                "project_id": project_id,
                "phase_name": phase_name.value,
                "completed_status": PhaseStatus.COMPLETED.value,
                "in_progress_status": PhaseStatus.IN_PROGRESS.value
            })
            conn.commit()
            
            if result.rowcount > 0:
                logger.info(f"Phase completed: {phase_name.value}")
                return True
            else:
                logger.warning(f"Phase not found or already completed: {phase_name.value}")
                return False
    
    async def transition_phase(
        self,
        project_id: str,
        from_phase: PhaseType,
        to_phase: PhaseType
    ) -> bool:
        """
        Handle transition from one phase to another.
        
        Validates completion of from_phase and starts to_phase.
        
        Args:
            project_id: Project identifier
            from_phase: Current phase
            to_phase: Next phase
        
        Returns:
            True if transition successful
        
        Raises:
            ValueError: If phases not in correct order or from_phase not completed
        """
        logger.info(f"Transitioning phase: {from_phase.value} → {to_phase.value}")
        
        # Validate phase order
        from_idx = self.PHASE_ORDER.index(from_phase)
        to_idx = self.PHASE_ORDER.index(to_phase)
        
        if to_idx != from_idx + 1:
            raise ValueError(
                f"Cannot transition from {from_phase.value} to {to_phase.value}. "
                f"Must go to {self.PHASE_ORDER[from_idx + 1].value}"
            )
        
        # Verify from_phase is completed
        query = text("""
            SELECT status FROM phases
            WHERE project_id = :project_id AND phase_name = :phase_name
            ORDER BY created_at DESC LIMIT 1
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                "project_id": project_id,
                "phase_name": from_phase.value
            })
            row = result.first()
            
            if not row or row[0] != PhaseStatus.COMPLETED.value:
                raise ValueError(
                    f"Cannot transition: {from_phase.value} is not completed"
                )
        
        # Start next phase
        await self.start_phase(project_id, to_phase)
        
        logger.info(f"Phase transition complete: {from_phase.value} → {to_phase.value}")
        return True
    
    async def get_phase_history(self, project_id: str) -> List[Phase]:
        """
        Get all phases for a project in chronological order.
        
        Args:
            project_id: Project identifier
        
        Returns:
            List of phases
        """
        query = text("""
            SELECT id, project_id, phase_name, status, assigned_agents, started_at, completed_at, created_at, updated_at
            FROM phases
            WHERE project_id = :project_id
            ORDER BY created_at ASC
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {"project_id": project_id})
            rows = result.fetchall()
            
            phases = [self._row_to_phase(row) for row in rows]
            logger.info(f"Retrieved {len(phases)} phases for project {project_id}")
            return phases
    
    async def get_phase(self, phase_id: str) -> Optional[Phase]:
        """
        Get a specific phase by ID.
        
        Args:
            phase_id: Phase identifier
        
        Returns:
            Phase or None if not found
        """
        query = text("""
            SELECT id, project_id, phase_name, status, assigned_agents, started_at, completed_at, created_at, updated_at
            FROM phases
            WHERE id = :phase_id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {"phase_id": phase_id})
            row = result.first()
            
            if row:
                return self._row_to_phase(row)
            else:
                logger.warning(f"Phase not found: {phase_id}")
                return None
    
    async def block_phase(
        self,
        project_id: str,
        phase_name: PhaseType,
        reason: str
    ) -> bool:
        """
        Mark a phase as blocked (e.g., due to gate or blocker issue).
        
        Args:
            project_id: Project identifier
            phase_name: Phase to block
            reason: Reason for blocking
        
        Returns:
            True if blocked successfully
        """
        logger.warning(f"Blocking phase: {phase_name.value}, reason={reason}")
        
        query = text("""
            UPDATE phases
            SET status = :blocked_status,
                updated_at = NOW()
            WHERE project_id = :project_id 
              AND phase_name = :phase_name 
              AND status = :in_progress_status
            RETURNING id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                "project_id": project_id,
                "phase_name": phase_name.value,
                "blocked_status": PhaseStatus.BLOCKED.value,
                "in_progress_status": PhaseStatus.IN_PROGRESS.value
            })
            conn.commit()
            
            return result.rowcount > 0
    
    async def unblock_phase(
        self,
        project_id: str,
        phase_name: PhaseType
    ) -> bool:
        """
        Unblock a phase and resume progress.
        
        Args:
            project_id: Project identifier
            phase_name: Phase to unblock
        
        Returns:
            True if unblocked successfully
        """
        logger.info(f"Unblocking phase: {phase_name.value}")
        
        query = text("""
            UPDATE phases
            SET status = :in_progress_status,
                updated_at = NOW()
            WHERE project_id = :project_id 
              AND phase_name = :phase_name 
              AND status = :blocked_status
            RETURNING id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                "project_id": project_id,
                "phase_name": phase_name.value,
                "in_progress_status": PhaseStatus.IN_PROGRESS.value,
                "blocked_status": PhaseStatus.BLOCKED.value
            })
            conn.commit()
            
            return result.rowcount > 0
    
    async def _validate_phase_order(
        self,
        project_id: str,
        phase_name: PhaseType
    ) -> None:
        """
        Validate that phases are started in correct order.
        
        Raises:
            ValueError: If trying to skip phases
        """
        # Get last completed phase
        query = text("""
            SELECT phase_name FROM phases
            WHERE project_id = :project_id AND status = :completed_status
            ORDER BY completed_at DESC LIMIT 1
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                "project_id": project_id,
                "completed_status": PhaseStatus.COMPLETED.value
            })
            row = result.first()
            
            if row:
                last_completed = PhaseType(row[0])
                last_idx = self.PHASE_ORDER.index(last_completed)
                next_expected = self.PHASE_ORDER[last_idx + 1] if last_idx + 1 < len(self.PHASE_ORDER) else None
                
                if next_expected and phase_name != next_expected:
                    raise ValueError(
                        f"Cannot start {phase_name.value}. "
                        f"Must complete {next_expected.value} first (current: {last_completed.value})"
                    )
            else:
                # No completed phases - must start with WORKSHOPPING
                if phase_name != PhaseType.WORKSHOPPING:
                    raise ValueError(
                        f"First phase must be {PhaseType.WORKSHOPPING.value}, not {phase_name.value}"
                    )
    
    def _row_to_phase(self, row) -> Phase:
        """Convert database row to Phase object."""
        return Phase(
            id=str(row[0]),
            project_id=str(row[1]),
            phase_name=PhaseType(row[2]),
            status=PhaseStatus(row[3]),
            assigned_agents=row[4] if row[4] else [],
            deliverables=[],  # Populated separately
            started_at=row[5].isoformat() if row[5] else None,
            completed_at=row[6].isoformat() if row[6] else None,
            created_at=row[7].isoformat() if row[7] else None,
            updated_at=row[8].isoformat() if row[8] else None
        )
