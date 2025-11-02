"""
Projects API Routes

Endpoints for creating and managing projects with specialist assignments.

Reference: MVP Demo Plan - Project Management
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_db
from backend.services.project_service import ProjectService

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


# Pydantic models
class ProjectCreate(BaseModel):
    """Request model for creating project."""
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    specialist_ids: List[str] = Field(default_factory=list)


class ProjectUpdate(BaseModel):
    """Request model for updating project."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1)
    status: Optional[str] = Field(None, pattern="^(active|completed|archived)$")


class ProjectResponse(BaseModel):
    """Response model for project."""
    id: str
    name: str
    description: str
    status: str
    created_at: str
    updated_at: str
    specialist_ids: List[str]


# Dependency to get project service
def get_project_service():
    """Get project service."""
    return ProjectService()


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    project: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    service: ProjectService = Depends(get_project_service)
):
    """
    Create a new project with specialist assignments.
    
    Specialists assigned at creation are IMMUTABLE - cannot be
    changed after project is created. This ensures consistency
    in project scope and specialist expertise.
    """
    try:
        created = await service.create_project(
            name=project.name,
            description=project.description,
            specialist_ids=project.specialist_ids,
            db=db
        )
        
        return ProjectResponse(**created.__dict__)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    service: ProjectService = Depends(get_project_service)
):
    """
    List all projects with optional status filtering.
    
    Query parameters:
    - status: Filter by 'active', 'completed', or 'archived'
    """
    projects = await service.list_projects(status=status, db=db)
    return [ProjectResponse(**p.__dict__) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    service: ProjectService = Depends(get_project_service)
):
    """Get a specific project by ID."""
    project = await service.get_project(project_id, db)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return ProjectResponse(**project.__dict__)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    updates: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    service: ProjectService = Depends(get_project_service)
):
    """
    Update project details.
    
    Can update name, description, and status.
    Cannot update specialist assignments (immutable).
    """
    # Convert to dict, excluding None values
    update_dict = {k: v for k, v in updates.dict().items() if v is not None}
    
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updated = await service.update_project(project_id, update_dict, db)
    
    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return ProjectResponse(**updated.__dict__)


@router.get("/{project_id}/specialists", response_model=List[str])
async def get_project_specialists(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    service: ProjectService = Depends(get_project_service)
):
    """
    Get list of specialists assigned to project.
    
    Read-only - specialists cannot be modified after project creation.
    """
    # Verify project exists
    project = await service.get_project(project_id, db)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    specialist_ids = await service.get_project_specialists(project_id, db)
    return specialist_ids
