"""API endpoints for prompt versioning and management."""

from __future__ import annotations

from typing import Optional, List, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.api.dependencies import get_prompt_loading_service, get_prompt_management_service
from backend.services.prompt_loading_service import PromptLoadingService
from backend.services.prompt_management_service import PromptManagementService


router = APIRouter(prefix="/api/v1/prompts", tags=["prompts"])


class CreateVersionRequest(BaseModel):
    agent_type: str = Field(..., description="Agent type (e.g., 'backend_dev')")
    version: str = Field(..., description="Semantic version (e.g., '1.0.0')")
    prompt_text: str = Field(..., description="Prompt content")
    created_by: Optional[str] = Field(None, description="Creator identifier")
    notes: Optional[str] = Field(None, description="Version notes")


class CreatePatchRequest(BaseModel):
    agent_type: str
    prompt_text: str
    created_by: Optional[str] = None
    notes: Optional[str] = None


class PromoteRequest(BaseModel):
    agent_type: str
    version: str


class VersionResponse(BaseModel):
    version: str
    is_active: bool
    created_at: Optional[str]
    created_by: Optional[str]
    notes: Optional[str]


class PromptContentResponse(BaseModel):
    agent_type: str
    version: str
    prompt_text: str
    is_active: bool


@router.post("/versions", response_model=Dict[str, str])
async def create_version(
    payload: CreateVersionRequest,
    mgmt_svc: PromptManagementService = Depends(get_prompt_management_service),
) -> Dict[str, str]:
    """Create a new prompt version.
    
    Args:
        payload: Version creation parameters
        mgmt_svc: PromptManagementService instance (injected)
    
    Returns:
        Success status
    
    Raises:
        HTTPException: 400 if version invalid or already exists
    """
    try:
        await mgmt_svc.create_version(
            agent_type=payload.agent_type,
            version=payload.version,
            prompt_text=payload.prompt_text,
            created_by=payload.created_by,
            notes=payload.notes
        )
        return {"status": "created", "agent_type": payload.agent_type, "version": payload.version}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/patch", response_model=Dict[str, str])
async def create_patch(
    payload: CreatePatchRequest,
    mgmt_svc: PromptManagementService = Depends(get_prompt_management_service),
) -> Dict[str, str]:
    """Create a patch version (auto-increments from active version).
    
    Args:
        payload: Patch creation parameters
        mgmt_svc: PromptManagementService instance (injected)
    
    Returns:
        New version created
    
    Raises:
        HTTPException: 404 if no active version found
    """
    try:
        new_version = await mgmt_svc.create_patch(
            agent_type=payload.agent_type,
            prompt_text=payload.prompt_text,
            created_by=payload.created_by,
            notes=payload.notes
        )
        return {"status": "created", "agent_type": payload.agent_type, "version": new_version}
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/promote", response_model=Dict[str, str])
async def promote_version(
    payload: PromoteRequest,
    mgmt_svc: PromptManagementService = Depends(get_prompt_management_service),
) -> Dict[str, str]:
    """Promote a version to active.
    
    Args:
        payload: Promotion parameters
        mgmt_svc: PromptManagementService instance (injected)
    
    Returns:
        Success status
    
    Raises:
        HTTPException: 404 if version not found
    """
    try:
        await mgmt_svc.promote_to_active(
            agent_type=payload.agent_type,
            version=payload.version
        )
        return {"status": "promoted", "agent_type": payload.agent_type, "version": payload.version}
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{agent_type}/versions", response_model=List[VersionResponse])
async def get_versions(
    agent_type: str,
    mgmt_svc: PromptManagementService = Depends(get_prompt_management_service),
) -> List[VersionResponse]:
    """Get all versions for an agent type.
    
    Args:
        agent_type: Agent type identifier
        mgmt_svc: PromptManagementService instance (injected)
    
    Returns:
        List of versions
    """
    versions = await mgmt_svc.get_versions(agent_type)
    return [VersionResponse(**v) for v in versions]


@router.get("/{agent_type}/active", response_model=PromptContentResponse)
async def get_active_prompt(
    agent_type: str,
    loading_svc: PromptLoadingService = Depends(get_prompt_loading_service),
    mgmt_svc: PromptManagementService = Depends(get_prompt_management_service),
) -> PromptContentResponse:
    """Get active prompt for an agent type.
    
    Args:
        agent_type: Agent type identifier
        loading_svc: PromptLoadingService instance (injected)
        mgmt_svc: PromptManagementService instance (injected)
    
    Returns:
        Active prompt with content
    
    Raises:
        HTTPException: 404 if no active prompt found
    """
    try:
        prompt_text = await loading_svc.get_active_prompt(agent_type)
        versions = await mgmt_svc.get_versions(agent_type)
        active_version = next((v for v in versions if v["is_active"]), None)
        
        return PromptContentResponse(
            agent_type=agent_type,
            version=active_version["version"] if active_version else "unknown",
            prompt_text=prompt_text,
            is_active=True
        )
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{agent_type}/{version}", response_model=PromptContentResponse)
async def get_prompt_version(
    agent_type: str,
    version: str,
    mgmt_svc: PromptManagementService = Depends(get_prompt_management_service),
) -> PromptContentResponse:
    """Get specific prompt version.
    
    Args:
        agent_type: Agent type identifier
        version: Version to retrieve
        mgmt_svc: PromptManagementService instance (injected)
    
    Returns:
        Prompt content for specified version
    
    Raises:
        HTTPException: 404 if version not found
    """
    prompt_text = await mgmt_svc.get_prompt_content(agent_type, version)
    
    if not prompt_text:
        raise HTTPException(status_code=404, detail=f"Version {version} not found for {agent_type}")
    
    versions = await mgmt_svc.get_versions(agent_type)
    version_info = next((v for v in versions if v["version"] == version), None)
    
    return PromptContentResponse(
        agent_type=agent_type,
        version=version,
        prompt_text=prompt_text,
        is_active=version_info["is_active"] if version_info else False
    )


@router.delete("/cache/{agent_type}", response_model=Dict[str, str])
async def clear_cache(
    agent_type: str,
    loading_svc: PromptLoadingService = Depends(get_prompt_loading_service),
) -> Dict[str, str]:
    """Clear cache for an agent type (force reload from DB).
    
    Args:
        agent_type: Agent type identifier
        loading_svc: PromptLoadingService instance (injected)
    
    Returns:
        Success status
    """
    loading_svc.clear_cache(agent_type)
    return {"status": "cleared", "agent_type": agent_type}
