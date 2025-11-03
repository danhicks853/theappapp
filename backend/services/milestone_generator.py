"""
Milestone Generator Service

AI-assisted phase planning and milestone generation from project descriptions.
Breaks projects into 6 phases with milestones and estimates.

Reference: Phase 3.1 - Phase Management System
"""
import logging
from typing import List, Optional, Any
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@dataclass
class Milestone:
    """Milestone data model."""
    id: str
    phase_name: str
    name: str
    description: str
    tasks: List[str]
    estimated_days: int
    dependencies: List[str]
    deliverables: List[str]


@dataclass
class PhasePlan:
    """Complete phase plan with milestones."""
    phase_name: str
    description: str
    milestones: List[Milestone]
    total_estimated_days: int
    agent_assignments: List[str]


@dataclass
class ProjectPlan:
    """Complete project plan across all phases."""
    project_id: str
    project_description: str
    phases: List[PhasePlan]
    total_estimated_days: int
    complexity_score: float  # 0.0-1.0
    generated_at: str


class MilestoneGenerator:
    """
    Service for AI-assisted milestone generation and project planning.
    
    Features:
    - Analyze project descriptions
    - Generate milestones for each phase
    - Estimate timelines based on complexity
    - Define deliverables per milestone
    
    Example:
        generator = MilestoneGenerator(engine, llm_client)
        plan = await generator.generate_project_plan(
            project_id="proj-123",
            description="Build a task management app with React and FastAPI"
        )
    """
    
    # Default milestone templates for each phase
    DEFAULT_MILESTONES = {
        "workshopping": [
            {
                "name": "Requirements Gathering",
                "description": "Collect and document all project requirements",
                "tasks": ["User interviews", "Requirement analysis", "User stories"],
                "estimated_days": 3,
                "deliverables": ["Requirements document"]
            },
            {
                "name": "Architecture Design",
                "description": "Design system architecture and technology stack",
                "tasks": ["System architecture", "Technology selection", "ADRs"],
                "estimated_days": 4,
                "deliverables": ["Architecture diagram", "ADRs", "Tech stack doc"]
            },
            {
                "name": "Task Planning",
                "description": "Break down work into detailed tasks",
                "tasks": ["Task breakdown", "Estimation", "Sprint planning"],
                "estimated_days": 2,
                "deliverables": ["Task breakdown document"]
            }
        ],
        "implementation": [
            {
                "name": "Project Setup",
                "description": "Set up development environment and project structure",
                "tasks": ["Create repos", "Setup dependencies", "Configure dev environment"],
                "estimated_days": 2,
                "deliverables": ["Project structure", "Dependencies configured"]
            },
            {
                "name": "Backend Development",
                "description": "Implement backend API and business logic",
                "tasks": ["API endpoints", "Business logic", "Database models"],
                "estimated_days": 10,
                "deliverables": ["Backend code", "Unit tests"]
            },
            {
                "name": "Frontend Development",
                "description": "Build user interface and components",
                "tasks": ["UI components", "Pages", "State management"],
                "estimated_days": 8,
                "deliverables": ["Frontend code", "Component tests"]
            },
            {
                "name": "Integration",
                "description": "Integrate frontend and backend",
                "tasks": ["API integration", "E2E flows", "Bug fixes"],
                "estimated_days": 5,
                "deliverables": ["Integration tests", "Working application"]
            }
        ],
        "testing": [
            {
                "name": "Test Suite Completion",
                "description": "Write comprehensive test coverage",
                "tasks": ["Unit tests", "Integration tests", "E2E tests"],
                "estimated_days": 5,
                "deliverables": ["Complete test suite"]
            },
            {
                "name": "Coverage Goals",
                "description": "Achieve 90%+ code coverage",
                "tasks": ["Run coverage", "Fill gaps", "Fix failing tests"],
                "estimated_days": 3,
                "deliverables": ["Coverage report ≥90%"]
            },
            {
                "name": "Bug Fixing",
                "description": "Identify and fix all bugs",
                "tasks": ["Bug testing", "Bug fixes", "Regression testing"],
                "estimated_days": 4,
                "deliverables": ["Bug report", "All tests passing"]
            }
        ],
        "deployment": [
            {
                "name": "Containerization",
                "description": "Create Docker containers for all services",
                "tasks": ["Dockerfiles", "Docker Compose", "Container testing"],
                "estimated_days": 3,
                "deliverables": ["Dockerfile", "docker-compose.yml"]
            },
            {
                "name": "CI/CD Setup",
                "description": "Configure automated deployment pipeline",
                "tasks": ["GitHub Actions", "Environment config", "Secret management"],
                "estimated_days": 4,
                "deliverables": ["CI/CD config", "Pipeline working"]
            },
            {
                "name": "Deployment Documentation",
                "description": "Document deployment procedures",
                "tasks": ["Deployment guide", "Troubleshooting", "Rollback procedures"],
                "estimated_days": 2,
                "deliverables": ["Deployment docs"]
            }
        ],
        "monitoring": [
            {
                "name": "Logging Setup",
                "description": "Configure structured logging",
                "tasks": ["Logging config", "Log aggregation", "Log rotation"],
                "estimated_days": 2,
                "deliverables": ["Logging configuration"]
            },
            {
                "name": "Metrics and Alerts",
                "description": "Set up monitoring and alerting",
                "tasks": ["Metrics collection", "Dashboards", "Alert rules"],
                "estimated_days": 3,
                "deliverables": ["Metrics dashboard", "Alert config"]
            },
            {
                "name": "Health Checks",
                "description": "Implement health and readiness endpoints",
                "tasks": ["Health endpoints", "Dependency checks", "Testing"],
                "estimated_days": 2,
                "deliverables": ["Health check endpoints"]
            }
        ],
        "maintenance": [
            {
                "name": "Documentation",
                "description": "Complete user and developer documentation",
                "tasks": ["User guide", "API docs", "Developer guide"],
                "estimated_days": 4,
                "deliverables": ["User docs", "Developer docs"]
            },
            {
                "name": "Backup Strategy",
                "description": "Define and implement backup procedures",
                "tasks": ["Backup plan", "Recovery testing", "Automation"],
                "estimated_days": 2,
                "deliverables": ["Backup strategy doc"]
            },
            {
                "name": "Handoff and Training",
                "description": "Prepare for operational handoff",
                "tasks": ["Team training", "Handoff docs", "Support plan"],
                "estimated_days": 3,
                "deliverables": ["Handoff complete"]
            }
        ]
    }
    
    def __init__(self, engine: Engine, llm_client: Optional[Any] = None):
        """
        Initialize milestone generator.
        
        Args:
            engine: Database engine
            llm_client: Optional LLM client for intelligent planning
        """
        self.engine = engine
        self.llm_client = llm_client
        logger.info("MilestoneGenerator initialized")
    
    async def generate_project_plan(
        self,
        project_id: str,
        project_description: str
    ) -> ProjectPlan:
        """
        Generate complete project plan with milestones for all phases.
        
        Args:
            project_id: Project identifier
            project_description: Natural language project description
        
        Returns:
            Complete ProjectPlan with all phases and milestones
        """
        logger.info(f"Generating project plan for: {project_id}")
        
        # Analyze complexity
        complexity = await self._analyze_complexity(project_description)
        
        # Generate phase plans
        phases = []
        total_days = 0
        
        from backend.services.phase_manager import PhaseType, PHASE_AGENT_ASSIGNMENTS
        
        for phase_type in PhaseType:
            phase_name = phase_type.value
            
            # Generate milestones for phase
            if self.llm_client:
                milestones = await self._generate_llm_milestones(
                    phase_name, project_description, complexity
                )
            else:
                milestones = await self._generate_default_milestones(
                    phase_name, complexity
                )
            
            # Calculate phase duration
            phase_days = sum(m.estimated_days for m in milestones)
            total_days += phase_days
            
            # Get agent assignments
            agents = PHASE_AGENT_ASSIGNMENTS.get(phase_type, [])
            
            # Create phase plan
            phase_plan = PhasePlan(
                phase_name=phase_name,
                description=self._get_phase_description(phase_name),
                milestones=milestones,
                total_estimated_days=phase_days,
                agent_assignments=agents
            )
            phases.append(phase_plan)
        
        # Create project plan
        from datetime import datetime
        plan = ProjectPlan(
            project_id=project_id,
            project_description=project_description,
            phases=phases,
            total_estimated_days=total_days,
            complexity_score=complexity,
            generated_at=datetime.utcnow().isoformat()
        )
        
        # Store in database
        await self._store_project_plan(plan)
        
        # Count total milestones across all phases
        total_milestones = sum(len(phase.milestones) for phase in plan.phases)
        logger.info(f"Generated project plan: {total_milestones} milestones across {len(plan.phases)} phases, {plan.total_estimated_days} days")
        
        return plan
    
    async def _analyze_complexity(self, description: str) -> float:
        """
        Analyze project complexity (0.0-1.0).
        
        Factors:
        - Length of description (more detail = more complex)
        - Keywords (API, database, authentication, etc.)
        - Features mentioned
        """
        # Simple heuristic-based complexity
        complexity = 0.5  # Base complexity
        
        description_lower = description.lower()
        
        # Adjust based on keywords
        complexity_keywords = {
            'authentication': 0.05,
            'database': 0.05,
            'api': 0.05,
            'real-time': 0.1,
            'microservices': 0.15,
            'machine learning': 0.2,
            'ai': 0.15,
            'distributed': 0.15,
            'blockchain': 0.2,
            'payment': 0.1,
            'security': 0.05,
            'scale': 0.1
        }
        
        for keyword, weight in complexity_keywords.items():
            if keyword in description_lower:
                complexity += weight
        
        # Adjust based on description length
        word_count = len(description.split())
        if word_count > 100:
            complexity += 0.1
        elif word_count > 50:
            complexity += 0.05
        
        # Cap at 1.0
        return min(complexity, 1.0)
    
    async def _generate_default_milestones(
        self,
        phase_name: str,
        complexity: float
    ) -> List[Milestone]:
        """Generate milestones using default templates."""
        templates = self.DEFAULT_MILESTONES.get(phase_name, [])
        milestones = []
        
        for i, template in enumerate(templates):
            # Adjust estimates based on complexity
            base_days = template["estimated_days"]
            adjusted_days = int(base_days * (1 + complexity * 0.5))
            
            milestone = Milestone(
                id=self._generate_milestone_id(),
                phase_name=phase_name,
                name=template["name"],
                description=template["description"],
                tasks=template["tasks"],
                estimated_days=adjusted_days,
                dependencies=[milestones[i-1].id] if i > 0 else [],
                deliverables=template.get("deliverables", [])
            )
            milestones.append(milestone)
        
        return milestones
    
    async def _generate_llm_milestones(
        self,
        phase_name: str,
        project_description: str,
        complexity: float
    ) -> List[Milestone]:
        """
        Generate milestones using LLM.
        
        TODO: Implement actual LLM-based generation
        """
        logger.info("LLM milestone generation not yet implemented")
        return await self._generate_default_milestones(phase_name, complexity)
    
    def _get_phase_description(self, phase_name: str) -> str:
        """Get description for a phase."""
        descriptions = {
            "workshopping": "Requirements gathering, architecture design, and task planning",
            "implementation": "Code development, testing, and integration",
            "testing": "Comprehensive testing and quality assurance",
            "deployment": "Containerization, CI/CD setup, and deployment",
            "monitoring": "Observability, logging, and health checks",
            "maintenance": "Documentation, backup strategy, and operational handoff"
        }
        return descriptions.get(phase_name, "Phase activities")
    
    async def _store_project_plan(self, plan: ProjectPlan) -> None:
        """Store project plan in database."""
        # Store plan overview
        query = text("""
            INSERT INTO project_plans
            (project_id, project_description, total_estimated_days, 
             complexity_score, generated_at, created_at)
            VALUES (:project_id, :description, :total_days, 
                    :complexity, :generated_at, NOW())
            ON CONFLICT (project_id) DO UPDATE
            SET project_description = EXCLUDED.project_description,
                total_estimated_days = EXCLUDED.total_estimated_days,
                complexity_score = EXCLUDED.complexity_score,
                generated_at = EXCLUDED.generated_at,
                updated_at = NOW()
        """)
        
        with self.engine.connect() as conn:
            conn.execute(query, {
                "project_id": plan.project_id,
                "description": plan.project_description,
                "total_days": plan.total_estimated_days,
                "complexity": plan.complexity_score,
                "generated_at": plan.generated_at
            })
            conn.commit()
        
        # Store milestones
        for phase in plan.phases:
            for milestone in phase.milestones:
                await self._store_milestone(plan.project_id, milestone)
        
        logger.debug(f"Project plan stored: {plan.project_id}")
    
    async def _store_milestone(self, project_id: str, milestone: Milestone) -> None:
        """Store a milestone in database."""
        import json
        
        query = text("""
            INSERT INTO milestones
            (id, project_id, phase_name, name, description, tasks,
             estimated_days, dependencies, deliverables, created_at, updated_at)
            VALUES (:id, :project_id, :phase_name, :name, :description, :tasks,
                    :estimated_days, :dependencies, :deliverables, NOW(), NOW())
            ON CONFLICT (id) DO UPDATE
            SET name = EXCLUDED.name,
                description = EXCLUDED.description,
                tasks = EXCLUDED.tasks,
                estimated_days = EXCLUDED.estimated_days,
                dependencies = EXCLUDED.dependencies,
                deliverables = EXCLUDED.deliverables,
                updated_at = NOW()
        """)
        
        with self.engine.connect() as conn:
            conn.execute(query, {
                "id": milestone.id,
                "project_id": project_id,
                "phase_name": milestone.phase_name,
                "name": milestone.name,
                "description": milestone.description,
                "tasks": json.dumps(milestone.tasks) if milestone.tasks else "[]",
                "estimated_days": milestone.estimated_days,
                "dependencies": json.dumps(milestone.dependencies) if milestone.dependencies else "[]",
                "deliverables": json.dumps(milestone.deliverables) if milestone.deliverables else "[]"
            })
            conn.commit()
    
    async def get_project_plan(self, project_id: str) -> Optional[ProjectPlan]:
        """Retrieve stored project plan."""
        # Get plan overview
        query = text("""
            SELECT project_id, project_description, total_estimated_days,
                   complexity_score, generated_at
            FROM project_plans
            WHERE project_id = :project_id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {"project_id": project_id})
            row = result.first()
            
            if not row:
                return None
            
            # Get all milestones
            milestones_query = text("""
                SELECT id, phase_name, name, description, tasks,
                       estimated_days, dependencies, deliverables
                FROM milestones
                WHERE project_id = :project_id
                ORDER BY phase_name, created_at
            """)
            
            milestones_result = conn.execute(milestones_query, {"project_id": project_id})
            milestone_rows = milestones_result.fetchall()
            
            # Group milestones by phase
            phases = {}
            for m_row in milestone_rows:
                phase_name = m_row[1]
                if phase_name not in phases:
                    phases[phase_name] = []
                
                milestone = Milestone(
                    id=str(m_row[0]),
                    phase_name=m_row[1],
                    name=m_row[2],
                    description=m_row[3],
                    tasks=m_row[4] or [],
                    estimated_days=m_row[5],
                    dependencies=m_row[6] or [],
                    deliverables=m_row[7] or []
                )
                phases[phase_name].append(milestone)
            
            # Build phase plans
            from backend.services.phase_manager import PHASE_AGENT_ASSIGNMENTS, PhaseType
            phase_plans = []
            
            for phase_name, milestones in phases.items():
                phase_days = sum(m.estimated_days for m in milestones)
                phase_type = PhaseType(phase_name)
                agents = PHASE_AGENT_ASSIGNMENTS.get(phase_type, [])
                
                phase_plan = PhasePlan(
                    phase_name=phase_name,
                    description=self._get_phase_description(phase_name),
                    milestones=milestones,
                    total_estimated_days=phase_days,
                    agent_assignments=agents
                )
                phase_plans.append(phase_plan)
            
            # Create project plan
            plan = ProjectPlan(
                project_id=str(row[0]),
                project_description=row[1],
                phases=phase_plans,
                total_estimated_days=row[2],
                complexity_score=row[3],
                generated_at=row[4]
            )
            
            return plan
    
    def _generate_milestone_id(self) -> str:
        """Generate unique milestone ID."""
        import uuid
        return f"milestone-{uuid.uuid4()}"
