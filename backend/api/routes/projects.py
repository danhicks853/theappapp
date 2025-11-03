"""
Projects API Routes

Endpoints for creating and managing projects with specialist assignments.

Reference: MVP Demo Plan - Project Management
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.engine import Connection

from backend.api.dependencies import get_db
from backend.services.project_service import ProjectService
from backend.services.project_build_service import ProjectBuildService, BuildProgress

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
    status: Optional[str] = Field(None, pattern="^(active|completed|archived|paused)$")


class ProjectResponse(BaseModel):
    """Response model for project."""
    id: str
    name: str
    description: str
    status: str
    created_at: str
    updated_at: str
    specialist_ids: List[str]


class BuildRequest(BaseModel):
    """Request model for starting a build."""
    description: str = Field(..., min_length=10, description="What to build")
    tech_stack: dict = Field(default_factory=dict, description="Technology choices")
    auto_approve_gates: bool = Field(default=False, description="Auto-approve gates")


class BuildResponse(BaseModel):
    """Response model for build initiation."""
    project_id: str
    status: str
    stream_url: Optional[str] = None
    message: str


class BuildStatusResponse(BaseModel):
    """Response model for build status."""
    project_id: str
    status: str
    current_phase: str
    progress_percent: float
    active_agent: Optional[str]
    last_event: Optional[str]
    started_at: str
    updated_at: str


# Dependency to get project service
def get_project_service():
    """Get project service."""
    return ProjectService()


# Dependency to get build service
def get_build_service():
    """Get project build service."""
    # TODO: Inject actual db_engine and llm_client
    return None  # Placeholder - needs proper initialization


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    project: ProjectCreate,
    db: Connection = Depends(get_db),
    service: ProjectService = Depends(get_project_service)
):
    """
    Create a new project with specialist assignments.
    
    Specialists assigned at creation are IMMUTABLE - cannot be
    changed after project is created. This ensures consistency
    in project scope and specialist expertise.
    """
    try:
        created = service.create_project(
            name=project.name,
            description=project.description,
            specialist_ids=project.specialist_ids,
            db=db
        )
        
        return ProjectResponse(**created.__dict__)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[ProjectResponse])
def list_projects(
    status: Optional[str] = None,
    db: Connection = Depends(get_db),
    service: ProjectService = Depends(get_project_service)
):
    """
    List all projects with optional status filtering.
    
    Query parameters:
    - status: Filter by 'active', 'completed', or 'archived'
    """
    projects = service.list_projects(status=status, db=db)
    return [ProjectResponse(**p.__dict__) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    db: Connection = Depends(get_db),
    service: ProjectService = Depends(get_project_service)
):
    """Get a specific project by ID."""
    project = service.get_project(project_id, db)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return ProjectResponse(**project.__dict__)


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    updates: ProjectUpdate,
    db: Connection = Depends(get_db),
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
    
    updated = service.update_project(project_id, update_dict, db)
    
    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return ProjectResponse(**updated.__dict__)


@router.get("/{project_id}/specialists", response_model=List[str])
def get_project_specialists(
    project_id: str,
    db: Connection = Depends(get_db),
    service: ProjectService = Depends(get_project_service)
):
    """
    Get list of specialists assigned to project.
    
    Read-only - specialists cannot be modified after project creation.
    """
    # Verify project exists
    project = service.get_project(project_id, db)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    specialist_ids = service.get_project_specialists(project_id, db)
    return specialist_ids


@router.post("/{project_id}/pause", response_model=ProjectResponse)
def pause_project(
    project_id: str,
    db: Connection = Depends(get_db),
    service: ProjectService = Depends(get_project_service)
):
    """
    Pause a project - stops all active agents and saves state.
    
    This is manual cost control - pausing stops all agent activity.
    Can only pause projects in 'active' status.
    """
    paused = service.pause_project(project_id, db)
    
    if not paused:
        # Try to get project to see if it exists
        project = service.get_project(project_id, db)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Can only pause active projects. Current status: {project.status}"
            )
    
    return ProjectResponse(**paused.__dict__)


@router.post("/{project_id}/resume", response_model=ProjectResponse)
def resume_project(
    project_id: str,
    db: Connection = Depends(get_db),
    service: ProjectService = Depends(get_project_service)
):
    """
    Resume a paused project - restarts agents from saved state.
    
    Can only resume projects in 'paused' status.
    """
    resumed = service.resume_project(project_id, db)
    
    if not resumed:
        # Try to get project to see if it exists
        project = service.get_project(project_id, db)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Can only resume paused projects. Current status: {project.status}"
            )
    
    return ProjectResponse(**resumed.__dict__)


# ============================================================================
# NEW: AI-Powered Build Endpoints
# ============================================================================

@router.post("/build", response_model=BuildResponse, status_code=202)
async def start_build(
    request: BuildRequest,
    build_service: ProjectBuildService = Depends(get_build_service)
):
    """
    Start an AI-powered project build.
    
    This endpoint initiates the full autonomous build process:
    1. Generates project plan with milestones
    2. Creates orchestrator and registers agents
    3. Begins building code, tests, and deployment configs
    4. Streams progress via events
    
    Returns immediately with project_id - build continues asynchronously.
    Monitor progress via GET /projects/{project_id}/build/status or WebSocket.
    
    **Example Request:**
    ```json
    {
        "description": "Build a todo list app with React frontend and FastAPI backend",
        "tech_stack": {
            "frontend": "react",
            "backend": "fastapi",
            "database": "postgresql"
        },
        "auto_approve_gates": false
    }
    ```
    """
    if not build_service:
        raise HTTPException(
            status_code=503,
            detail="Build service not initialized - contact administrator"
        )
    
    try:
        # Start the build
        project_id = await build_service.start_build(
            description=request.description,
            tech_stack=request.tech_stack,
            auto_approve_gates=request.auto_approve_gates
        )
        
        # Return build initiation response
        return BuildResponse(
            project_id=project_id,
            status="initializing",
            stream_url=f"ws://localhost:8000/ws/builds/{project_id}",
            message="Build started. Monitor progress via WebSocket or status endpoint."
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start build: {str(e)}")


@router.get("/{project_id}/build/status", response_model=BuildStatusResponse)
async def get_build_status(
    project_id: str,
    build_service: ProjectBuildService = Depends(get_build_service)
):
    """
    Get current build status and progress.
    
    Returns real-time information about:
    - Current phase (planning, implementation, testing, deployment)
    - Progress percentage
    - Active agent
    - Last event
    
    Poll this endpoint or use WebSocket for real-time updates.
    """
    if not build_service:
        raise HTTPException(
            status_code=503,
            detail="Build service not initialized"
        )
    
    try:
        progress = await build_service.get_build_status(project_id)
        
        return BuildStatusResponse(
            project_id=progress.project_id,
            status=progress.status,
            current_phase=progress.current_phase,
            progress_percent=progress.progress_percent,
            active_agent=progress.active_agent,
            last_event=progress.last_event,
            started_at=progress.started_at,
            updated_at=progress.updated_at
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/build/pause", status_code=204)
async def pause_build(
    project_id: str,
    build_service: ProjectBuildService = Depends(get_build_service)
):
    """
    Pause an active build.
    
    Pauses all agent activity and saves state.
    Resume with POST /{project_id}/build/resume
    """
    if not build_service:
        raise HTTPException(status_code=503, detail="Build service not initialized")
    
    success = await build_service.pause_build(project_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Build not found or not active")


@router.post("/{project_id}/build/cancel", status_code=204)
async def cancel_build(
    project_id: str,
    reason: Optional[str] = None,
    build_service: ProjectBuildService = Depends(get_build_service)
):
    """
    Cancel an active build.
    
    Stops all agents, cleans up resources, and marks build as cancelled.
    Cannot be resumed after cancellation.
    """
    if not build_service:
        raise HTTPException(status_code=503, detail="Build service not initialized")
    
    success = await build_service.cancel_build(project_id, reason or "User cancelled")
    
    if not success:
        raise HTTPException(status_code=404, detail="Build not found")
