"""
Project Service

Business logic for creating and managing projects with specialist assignments.

Reference: MVP Demo Plan - Project Management
"""
import logging
import uuid
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Connection

logger = logging.getLogger(__name__)


@dataclass
class Project:
    """Project data model."""
    id: str
    name: str
    description: str
    status: str  # 'active', 'completed', 'archived'
    created_at: str
    updated_at: str
    specialist_ids: List[str]


class ProjectService:
    """
    Service for managing projects.
    
    Features:
    - Create projects with specialist assignments
    - Immutable specialist binding (can't add after creation)
    - List and retrieve projects
    - Update project status
    """
    
    def __init__(self):
        """Initialize project service."""
        logger.info("Project service initialized")
    
    def create_project(
        self,
        name: str,
        description: str,
        specialist_ids: List[str],
        db: Connection
    ) -> Project:
        """
        Create a new project with specialist assignments.
        
        Args:
            name: Project name
            description: Project description
            specialist_ids: List of specialist IDs to assign
            db: Database session
        
        Returns:
            Created project with specialists
        """
        logger.info(f"Creating project: {name}")
        
        project_id = str(uuid.uuid4())
        
        # Create project
        query = text("""
            INSERT INTO projects (id, name, description, status, created_at, updated_at)
            VALUES (:id, :name, :description, 'active', NOW(), NOW())
            RETURNING id, name, description, status, created_at, updated_at
        """)
        
        result = db.execute(query, {
            "id": project_id,
            "name": name,
            "description": description
        })
        
        row = result.first()
        
        # Bind specialists (IMMUTABLE - can only be set at creation)
        if specialist_ids:
            for specialist_id in specialist_ids:
                bind_query = text("""
                    INSERT INTO project_specialists (project_id, specialist_id, created_at)
                    VALUES (:project_id, :specialist_id, NOW())
                """)
                db.execute(bind_query, {
                    "project_id": project_id,
                    "specialist_id": specialist_id
                })
        
        db.commit()
        
        project = self._row_to_project(row, specialist_ids)
        logger.info(f"Project created: {project_id} with {len(specialist_ids)} specialists")
        
        return project
    
    def get_project(self, project_id: str, db: Connection) -> Optional[Project]:
        """Get project by ID with specialist assignments."""
        query = text("""
            SELECT p.id, p.name, p.description, p.status, p.created_at, p.updated_at
            FROM projects p
            WHERE p.id = :id
        """)
        
        result = db.execute(query, {"id": project_id})
        row = result.first()
        
        if not row:
            return None
        
        # Get specialists
        specialists_query = text("""
            SELECT specialist_id
            FROM project_specialists
            WHERE project_id = :project_id
        """)
        
        specialists_result = db.execute(specialists_query, {"project_id": project_id})
        specialist_ids = [str(r[0]) for r in specialists_result.fetchall()]
        
        return self._row_to_project(row, specialist_ids)
    
    def list_projects(
        self,
        status: Optional[str] = None,
        db: Connection = None
    ) -> List[Project]:
        """
        List projects with optional status filtering.
        
        Args:
            status: Filter by status ('active', 'completed', 'archived')
            db: Database session
        
        Returns:
            List of projects
        """
        where_clause = "WHERE status = :status" if status else ""
        params = {"status": status} if status else {}
        
        query = text(f"""
            SELECT id, name, description, status, created_at, updated_at
            FROM projects
            {where_clause}
            ORDER BY created_at DESC
        """)
        
        result = db.execute(query, params)
        rows = result.fetchall()
        
        # Get specialists for each project
        projects = []
        for row in rows:
            project_id = str(row[0])
            
            specialists_query = text("""
                SELECT specialist_id
                FROM project_specialists
                WHERE project_id = :project_id
            """)
            
            specialists_result = db.execute(specialists_query, {"project_id": project_id})
            specialist_ids = [str(r[0]) for r in specialists_result.fetchall()]
            
            projects.append(self._row_to_project(row, specialist_ids))
        
        logger.info(f"Listed {len(projects)} projects")
        return projects
    
    def update_project(
        self,
        project_id: str,
        updates: Dict[str, Any],
        db: Connection
    ) -> Optional[Project]:
        """
        Update project details (name, description, status).
        
        Note: Cannot update specialist assignments (immutable).
        
        Args:
            project_id: Project ID
            updates: Fields to update
            db: Database session
        
        Returns:
            Updated project or None if not found
        """
        # Build SET clause
        set_parts = []
        params = {"id": project_id}
        
        for field in ["name", "description", "status"]:
            if field in updates:
                set_parts.append(f"{field} = :{field}")
                params[field] = updates[field]
        
        if not set_parts:
            return self.get_project(project_id, db)
        
        set_clause = ", ".join(set_parts)
        
        query = text(f"""
            UPDATE projects
            SET {set_clause}, updated_at = NOW()
            WHERE id = :id
            RETURNING id, name, description, status, created_at, updated_at
        """)
        
        result = db.execute(query, params)
        db.commit()
        
        row = result.first()
        if not row:
            return None
        
        # Get specialists
        specialists_query = text("""
            SELECT specialist_id
            FROM project_specialists
            WHERE project_id = :project_id
        """)
        
        specialists_result = db.execute(specialists_query, {"project_id": project_id})
        specialist_ids = [str(r[0]) for r in specialists_result.fetchall()]
        
        logger.info(f"Project updated: {project_id}")
        return self._row_to_project(row, specialist_ids)
    
    def get_project_specialists(
        self,
        project_id: str,
        db: Connection
    ) -> List[str]:
        """
        Get list of specialist IDs assigned to project.
        
        Args:
            project_id: Project ID
            db: Database session
        
        Returns:
            List of specialist IDs
        """
        query = text("""
            SELECT specialist_id
            FROM project_specialists
            WHERE project_id = :project_id
            ORDER BY created_at
        """)
        
        result = db.execute(query, {"project_id": project_id})
        specialist_ids = [str(r[0]) for r in result.fetchall()]
        
        return specialist_ids
    
    def pause_project(self, project_id: str, db: Connection) -> Optional[Project]:
        """
        Pause a project - stops all active agents and saves state.
        
        Args:
            project_id: Project ID
            db: Database session
        
        Returns:
            Updated project with status 'paused' or None if not found
        """
        logger.info(f"Pausing project: {project_id}")
        
        # Update project status to paused
        query = text("""
            UPDATE projects
            SET status = 'paused', updated_at = NOW()
            WHERE id = :id AND status = 'active'
            RETURNING id, name, description, status, created_at, updated_at
        """)
        
        result = db.execute(query, {"id": project_id})
        db.commit()
        
        row = result.first()
        if not row:
            logger.warning(f"Project not found or not active: {project_id}")
            return None
        
        # Get specialists
        specialists_query = text("""
            SELECT specialist_id
            FROM project_specialists
            WHERE project_id = :project_id
        """)
        
        specialists_result = db.execute(specialists_query, {"project_id": project_id})
        specialist_ids = [str(r[0]) for r in specialists_result.fetchall()]
        
        # TODO: Stop active agents for this project
        # This would integrate with the orchestrator to gracefully stop agents
        # For now, we just update the status
        
        logger.info(f"Project paused: {project_id}")
        return self._row_to_project(row, specialist_ids)
    
    def resume_project(self, project_id: str, db: Connection) -> Optional[Project]:
        """
        Resume a paused project - restarts agents from saved state.
        
        Args:
            project_id: Project ID
            db: Database session
        
        Returns:
            Updated project with status 'active' or None if not found
        """
        logger.info(f"Resuming project: {project_id}")
        
        # Update project status to active
        query = text("""
            UPDATE projects
            SET status = 'active', updated_at = NOW()
            WHERE id = :id AND status = 'paused'
            RETURNING id, name, description, status, created_at, updated_at
        """)
        
        result = db.execute(query, {"id": project_id})
        db.commit()
        
        row = result.first()
        if not row:
            logger.warning(f"Project not found or not paused: {project_id}")
            return None
        
        # Get specialists
        specialists_query = text("""
            SELECT specialist_id
            FROM project_specialists
            WHERE project_id = :project_id
        """)
        
        specialists_result = db.execute(specialists_query, {"project_id": project_id})
        specialist_ids = [str(r[0]) for r in specialists_result.fetchall()]
        
        # TODO: Restart agents for this project
        # This would integrate with the orchestrator to restart agents from saved state
        # For now, we just update the status
        
        logger.info(f"Project resumed: {project_id}")
        return self._row_to_project(row, specialist_ids)
    
    def _row_to_project(self, row, specialist_ids: List[str]) -> Project:
        """Convert database row to Project object."""
        return Project(
            id=str(row[0]),
            name=row[1],
            description=row[2],
            status=row[3],
            created_at=row[4].isoformat() if row[4] else None,
            updated_at=row[5].isoformat() if row[5] else None,
            specialist_ids=specialist_ids
        )
