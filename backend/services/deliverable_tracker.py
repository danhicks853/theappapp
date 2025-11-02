"""
Deliverable Tracker Service

Tracks and validates phase deliverables with AI-powered quality checks.
Each phase has required deliverables that must be completed before phase completion.

Reference: Phase 3.1 - Phase Management System
"""
import logging
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class DeliverableType(str, Enum):
    """Types of deliverables."""
    DOCUMENT = "document"
    CODE_FILE = "code_file"
    TEST_FILE = "test_file"
    CONFIG_FILE = "config_file"
    DIAGRAM = "diagram"
    DEPLOYMENT_ARTIFACT = "deployment_artifact"


class DeliverableStatus(str, Enum):
    """Deliverable completion status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    VALIDATED = "validated"
    REJECTED = "rejected"


@dataclass
class Deliverable:
    """Deliverable data model."""
    id: str
    phase_id: str
    name: str
    description: str
    deliverable_type: DeliverableType
    status: DeliverableStatus
    artifact_path: Optional[str]
    validation_result: Optional[Dict[str, Any]]
    created_at: str
    updated_at: str


@dataclass
class ValidationResult:
    """Result of deliverable validation."""
    valid: bool
    score: float  # 0.0-1.0
    feedback: str
    issues: List[str]
    suggestions: List[str]


# Phase deliverable definitions
PHASE_DELIVERABLES = {
    "workshopping": [
        {
            "name": "Project Requirements Document",
            "description": "Detailed requirements specification with user stories",
            "type": DeliverableType.DOCUMENT,
            "required": True
        },
        {
            "name": "Architecture Decision Records",
            "description": "ADRs documenting key architectural decisions",
            "type": DeliverableType.DOCUMENT,
            "required": True
        },
        {
            "name": "System Architecture Diagram",
            "description": "High-level system architecture visualization",
            "type": DeliverableType.DIAGRAM,
            "required": True
        },
        {
            "name": "Task Breakdown",
            "description": "Detailed task list with estimates",
            "type": DeliverableType.DOCUMENT,
            "required": True
        },
        {
            "name": "Technology Stack Document",
            "description": "Selected technologies with justifications",
            "type": DeliverableType.DOCUMENT,
            "required": True
        }
    ],
    "implementation": [
        {
            "name": "Backend Code",
            "description": "Backend implementation with all features",
            "type": DeliverableType.CODE_FILE,
            "required": True
        },
        {
            "name": "Frontend Code",
            "description": "Frontend implementation with UI components",
            "type": DeliverableType.CODE_FILE,
            "required": True
        },
        {
            "name": "Unit Tests",
            "description": "Unit tests for all modules",
            "type": DeliverableType.TEST_FILE,
            "required": True
        },
        {
            "name": "Integration Tests",
            "description": "Integration tests for API endpoints",
            "type": DeliverableType.TEST_FILE,
            "required": True
        },
        {
            "name": "Database Migrations",
            "description": "All database schema migrations",
            "type": DeliverableType.CODE_FILE,
            "required": True
        }
    ],
    "testing": [
        {
            "name": "Test Coverage Report",
            "description": "Code coverage ≥90% with detailed report",
            "type": DeliverableType.DOCUMENT,
            "required": True
        },
        {
            "name": "E2E Test Suite",
            "description": "End-to-end tests covering critical user flows",
            "type": DeliverableType.TEST_FILE,
            "required": True
        },
        {
            "name": "Performance Test Results",
            "description": "Load testing and performance benchmarks",
            "type": DeliverableType.DOCUMENT,
            "required": False
        },
        {
            "name": "Bug Report Summary",
            "description": "List of bugs found and fixed",
            "type": DeliverableType.DOCUMENT,
            "required": True
        }
    ],
    "deployment": [
        {
            "name": "Dockerfile",
            "description": "Container configuration for all services",
            "type": DeliverableType.CONFIG_FILE,
            "required": True
        },
        {
            "name": "Docker Compose File",
            "description": "Multi-container orchestration configuration",
            "type": DeliverableType.CONFIG_FILE,
            "required": True
        },
        {
            "name": "CI/CD Pipeline",
            "description": "GitHub Actions or similar CI/CD configuration",
            "type": DeliverableType.CONFIG_FILE,
            "required": True
        },
        {
            "name": "Deployment Documentation",
            "description": "Step-by-step deployment guide",
            "type": DeliverableType.DOCUMENT,
            "required": True
        },
        {
            "name": "Environment Configuration",
            "description": "Environment variables and configuration templates",
            "type": DeliverableType.CONFIG_FILE,
            "required": True
        }
    ],
    "monitoring": [
        {
            "name": "Logging Configuration",
            "description": "Structured logging setup",
            "type": DeliverableType.CONFIG_FILE,
            "required": True
        },
        {
            "name": "Metrics Dashboard",
            "description": "Application metrics and monitoring setup",
            "type": DeliverableType.DEPLOYMENT_ARTIFACT,
            "required": False
        },
        {
            "name": "Alert Configuration",
            "description": "Alert rules for critical issues",
            "type": DeliverableType.CONFIG_FILE,
            "required": False
        },
        {
            "name": "Health Check Endpoints",
            "description": "Health and readiness check implementations",
            "type": DeliverableType.CODE_FILE,
            "required": True
        }
    ],
    "maintenance": [
        {
            "name": "User Documentation",
            "description": "End-user guides and documentation",
            "type": DeliverableType.DOCUMENT,
            "required": True
        },
        {
            "name": "Developer Documentation",
            "description": "Code documentation and contribution guide",
            "type": DeliverableType.DOCUMENT,
            "required": True
        },
        {
            "name": "Backup Strategy",
            "description": "Data backup and recovery procedures",
            "type": DeliverableType.DOCUMENT,
            "required": True
        },
        {
            "name": "Update Plan",
            "description": "Strategy for future updates and maintenance",
            "type": DeliverableType.DOCUMENT,
            "required": True
        }
    ]
}


class DeliverableTracker:
    """
    Service for tracking and validating phase deliverables.
    
    Features:
    - Define deliverables for each phase
    - Track completion status
    - Validate deliverable quality with AI
    - Calculate phase completeness
    
    Example:
        tracker = DeliverableTracker(engine, llm_client)
        deliverables = await tracker.define_deliverables("implementation")
        result = await tracker.validate_deliverable("del-123", artifact_content)
        completeness = await tracker.get_phase_completeness("phase-123")
    """
    
    def __init__(self, engine: Engine, llm_client: Optional[Any] = None):
        """
        Initialize deliverable tracker.
        
        Args:
            engine: Database engine
            llm_client: Optional LLM client for AI validation
        """
        self.engine = engine
        self.llm_client = llm_client
        logger.info("DeliverableTracker initialized")
    
    async def define_deliverables(
        self,
        phase_id: str,
        phase_name: str
    ) -> List[Deliverable]:
        """
        Define and create deliverables for a phase.
        
        Args:
            phase_id: Phase identifier
            phase_name: Phase name (workshopping, implementation, etc.)
        
        Returns:
            List of created deliverables
        """
        logger.info(f"Defining deliverables for phase: {phase_name}")
        
        definitions = PHASE_DELIVERABLES.get(phase_name, [])
        deliverables = []
        
        for defn in definitions:
            query = text("""
                INSERT INTO deliverables 
                (phase_id, name, description, deliverable_type, status, created_at, updated_at)
                VALUES (:phase_id, :name, :description, :type, :status, NOW(), NOW())
                RETURNING id, phase_id, name, description, deliverable_type, status, 
                          artifact_path, validation_result, created_at, updated_at
            """)
            
            with self.engine.connect() as conn:
                result = conn.execute(query, {
                    "phase_id": phase_id,
                    "name": defn["name"],
                    "description": defn["description"],
                    "type": defn["type"].value,
                    "status": DeliverableStatus.NOT_STARTED.value
                })
                conn.commit()
                
                row = result.first()
                deliverable = self._row_to_deliverable(row)
                deliverables.append(deliverable)
        
        logger.info(f"Created {len(deliverables)} deliverables for phase {phase_id}")
        return deliverables
    
    async def validate_deliverable(
        self,
        deliverable_id: str,
        artifact: Any
    ) -> ValidationResult:
        """
        Validate a deliverable with AI-powered quality checks.
        
        Args:
            deliverable_id: Deliverable identifier
            artifact: Artifact to validate (content, file path, etc.)
        
        Returns:
            ValidationResult with score and feedback
        """
        logger.info(f"Validating deliverable: {deliverable_id}")
        
        # Get deliverable info
        deliverable = await self.get_deliverable(deliverable_id)
        if not deliverable:
            raise ValueError(f"Deliverable not found: {deliverable_id}")
        
        # Perform validation
        if self.llm_client:
            # AI-powered validation
            validation = await self._ai_validate(deliverable, artifact)
        else:
            # Basic validation without AI
            validation = self._basic_validate(deliverable, artifact)
        
        # Store validation result
        query = text("""
            UPDATE deliverables
            SET validation_result = :validation_result::jsonb,
                status = :status,
                updated_at = NOW()
            WHERE id = :deliverable_id
        """)
        
        status = DeliverableStatus.VALIDATED if validation.valid else DeliverableStatus.REJECTED
        
        with self.engine.connect() as conn:
            conn.execute(query, {
                "deliverable_id": deliverable_id,
                "validation_result": {
                    "valid": validation.valid,
                    "score": validation.score,
                    "feedback": validation.feedback,
                    "issues": validation.issues,
                    "suggestions": validation.suggestions
                },
                "status": status.value
            })
            conn.commit()
        
        logger.info(f"Validation complete: score={validation.score:.2f}, valid={validation.valid}")
        return validation
    
    async def get_phase_completeness(self, phase_id: str) -> float:
        """
        Calculate phase completeness (0.0-1.0) based on deliverables.
        
        Args:
            phase_id: Phase identifier
        
        Returns:
            Completion percentage (0.0-1.0)
        """
        query = text("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN status IN ('completed', 'validated') THEN 1 END) as completed
            FROM deliverables
            WHERE phase_id = :phase_id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {"phase_id": phase_id})
            row = result.first()
            
            if row and row[0] > 0:
                completeness = row[1] / row[0]
                logger.info(f"Phase {phase_id} completeness: {completeness:.1%}")
                return completeness
            else:
                logger.warning(f"No deliverables found for phase: {phase_id}")
                return 0.0
    
    async def get_deliverable(self, deliverable_id: str) -> Optional[Deliverable]:
        """Get a specific deliverable by ID."""
        query = text("""
            SELECT id, phase_id, name, description, deliverable_type, status,
                   artifact_path, validation_result, created_at, updated_at
            FROM deliverables
            WHERE id = :deliverable_id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {"deliverable_id": deliverable_id})
            row = result.first()
            
            if row:
                return self._row_to_deliverable(row)
            return None
    
    async def get_phase_deliverables(self, phase_id: str) -> List[Deliverable]:
        """Get all deliverables for a phase."""
        query = text("""
            SELECT id, phase_id, name, description, deliverable_type, status,
                   artifact_path, validation_result, created_at, updated_at
            FROM deliverables
            WHERE phase_id = :phase_id
            ORDER BY created_at ASC
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {"phase_id": phase_id})
            rows = result.fetchall()
            
            return [self._row_to_deliverable(row) for row in rows]
    
    async def mark_completed(
        self,
        deliverable_id: str,
        artifact_path: Optional[str] = None
    ) -> bool:
        """Mark a deliverable as completed."""
        query = text("""
            UPDATE deliverables
            SET status = :status,
                artifact_path = :artifact_path,
                updated_at = NOW()
            WHERE id = :deliverable_id
            RETURNING id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                "deliverable_id": deliverable_id,
                "status": DeliverableStatus.COMPLETED.value,
                "artifact_path": artifact_path
            })
            conn.commit()
            
            return result.rowcount > 0
    
    async def _ai_validate(
        self,
        deliverable: Deliverable,
        artifact: Any
    ) -> ValidationResult:
        """
        AI-powered validation using LLM.
        
        TODO: Implement actual LLM validation
        """
        # Placeholder - would use LLM to analyze artifact quality
        logger.info("AI validation not yet implemented, using basic validation")
        return self._basic_validate(deliverable, artifact)
    
    def _basic_validate(
        self,
        deliverable: Deliverable,
        artifact: Any
    ) -> ValidationResult:
        """
        Basic validation without AI.
        
        Checks for presence and basic structure.
        """
        issues = []
        suggestions = []
        
        # Check if artifact exists
        if not artifact:
            issues.append("No artifact provided")
            return ValidationResult(
                valid=False,
                score=0.0,
                feedback="No artifact provided for validation",
                issues=issues,
                suggestions=["Please provide the deliverable artifact"]
            )
        
        # Basic checks based on deliverable type
        if deliverable.deliverable_type == DeliverableType.DOCUMENT:
            if isinstance(artifact, str) and len(artifact) < 100:
                issues.append("Document seems too short")
                suggestions.append("Provide more detailed documentation")
        
        # Calculate score
        score = 1.0 if not issues else 0.5
        valid = len(issues) == 0
        
        feedback = "Basic validation passed" if valid else "Issues found during validation"
        
        return ValidationResult(
            valid=valid,
            score=score,
            feedback=feedback,
            issues=issues,
            suggestions=suggestions
        )
    
    def _row_to_deliverable(self, row) -> Deliverable:
        """Convert database row to Deliverable object."""
        return Deliverable(
            id=str(row[0]),
            phase_id=str(row[1]),
            name=row[2],
            description=row[3],
            deliverable_type=DeliverableType(row[4]),
            status=DeliverableStatus(row[5]),
            artifact_path=row[6],
            validation_result=row[7],
            created_at=row[8].isoformat() if row[8] else None,
            updated_at=row[9].isoformat() if row[9] else None
        )
