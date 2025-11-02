"""
Store API Routes

TheAppApp App Store - browse and install pre-built specialists.

Reference: TheAppApp App Store feature
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_db
from backend.services.store_service import StoreService
from backend.services.specialist_service import SpecialistService
from backend.services.openai_adapter import OpenAIAdapter
from backend.services.rag_service import RAGService
import os

router = APIRouter(prefix="/api/v1/store", tags=["store"])


# Pydantic models
class TemplateResponse(BaseModel):
    """Response model for specialist template."""
    template_id: str
    name: str
    display_name: str
    avatar_seed: str
    author: str
    current_version: str
    description: str
    bio: str
    interests: List[str]
    favorite_tool: str
    quote: str
    tags: List[str]


class TemplateVersionResponse(BaseModel):
    """Response model for template version details."""
    version: str
    released: str
    system_prompt: str
    capabilities: List[str]
    web_search_enabled: bool
    web_search_config: Optional[dict]
    tools_enabled: dict
    changelog: str
    breaking_changes: bool


class InstallRequest(BaseModel):
    """Request to install a template."""
    version: Optional[str] = None  # Defaults to latest


# Dependencies
def get_store_service():
    """Get store service."""
    return StoreService()


def get_specialist_service():
    """Get specialist service with dependencies."""
    api_key = os.getenv("OPENAI_API_KEY")
    openai_adapter = OpenAIAdapter(api_key=api_key) if api_key else None
    rag_service = RAGService(openai_adapter) if openai_adapter else None
    return SpecialistService(openai_adapter=openai_adapter, rag_service=rag_service)


@router.get("/specialists", response_model=List[TemplateResponse])
async def list_store_specialists(
    tags: Optional[str] = None,
    store: StoreService = Depends(get_store_service)
):
    """
    Browse TheAppApp App Store.
    
    Lists all available pre-built specialist templates.
    
    Query params:
    - tags: Comma-separated list of tags to filter by
    """
    tag_list = tags.split(",") if tags else None
    templates = store.list_templates(tags=tag_list)
    
    return [TemplateResponse(**template.__dict__) for template in templates]


@router.get("/specialists/{template_id}", response_model=TemplateResponse)
async def get_store_specialist(
    template_id: str,
    store: StoreService = Depends(get_store_service)
):
    """Get details for a specific specialist template."""
    template = store.get_template(template_id)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return TemplateResponse(**template.__dict__)


@router.get("/specialists/{template_id}/versions", response_model=List[str])
async def list_template_versions(
    template_id: str,
    store: StoreService = Depends(get_store_service)
):
    """List all available versions for a template."""
    versions = store.list_versions(template_id)
    
    if not versions:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return versions


@router.get("/specialists/{template_id}/versions/{version}", response_model=TemplateVersionResponse)
async def get_template_version(
    template_id: str,
    version: str,
    store: StoreService = Depends(get_store_service)
):
    """Get details for a specific version of a template."""
    version_data = store.get_template_version(template_id, version)
    
    if not version_data:
        raise HTTPException(status_code=404, detail="Version not found")
    
    return TemplateVersionResponse(**version_data.__dict__)


@router.post("/specialists/{template_id}/install", status_code=201)
async def install_specialist(
    template_id: str,
    request: InstallRequest,
    db: AsyncSession = Depends(get_db),
    store: StoreService = Depends(get_store_service),
    specialist_service: SpecialistService = Depends(get_specialist_service)
):
    """
    Install a specialist from TheAppApp App Store.
    
    Creates a new specialist instance based on the template.
    """
    try:
        # Get installation data from store
        install_data = store.install_template(template_id, request.version)
        
        # Create specialist using specialist service
        specialist = await specialist_service.create_specialist(
            name=install_data["name"],
            description=install_data["description"],
            system_prompt=install_data["system_prompt"],
            scope=install_data["scope"],
            web_search_enabled=install_data["web_search_enabled"],
            web_search_config=install_data["web_search_config"],
            tools_enabled=install_data["tools_enabled"],
            db=db
        )
        
        # Update with store-specific fields
        await db.execute(
            """
            UPDATE specialists 
            SET version = :version,
                template_id = :template_id,
                installed_from_store = :from_store,
                display_name = :display_name,
                avatar = :avatar,
                bio = :bio,
                interests = :interests,
                favorite_tool = :favorite_tool,
                quote = :quote
            WHERE id = :id
            """,
            {
                "id": specialist.id,
                "version": install_data["version"],
                "template_id": install_data["template_id"],
                "from_store": install_data["installed_from_store"],
                "display_name": install_data["display_name"],
                "avatar": install_data["avatar"],
                "bio": install_data["bio"],
                "interests": install_data["interests"],
                "favorite_tool": install_data["favorite_tool"],
                "quote": install_data["quote"]
            }
        )
        await db.commit()
        
        return {
            "specialist_id": specialist.id,
            "template_id": template_id,
            "version": install_data["version"],
            "message": f"Successfully installed {install_data['display_name']}!"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/specialists/{template_id}/check-update")
async def check_for_update(
    template_id: str,
    current_version: str,
    store: StoreService = Depends(get_store_service)
):
    """
    Check if an update is available for an installed specialist.
    
    Query params:
    - current_version: Currently installed version
    """
    latest_version = store.check_for_updates(template_id, current_version)
    
    return {
        "template_id": template_id,
        "current_version": current_version,
        "latest_version": store.get_latest_version(template_id),
        "update_available": latest_version is not None,
        "new_version": latest_version
    }
