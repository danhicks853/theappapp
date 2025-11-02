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
def list_store_specialists(
    tags: Optional[str] = None,
    store: StoreService = Depends(get_store_service)
):
    """
    Browse TheAppApp App Store.
    
    Lists all available pre-built specialist templates.
    Filters out specialists that are already installed.
    """
    from backend.api.dependencies import _engine
    from sqlalchemy import text
    
    tag_list = tags.split(",") if tags else None
    templates = store.list_templates(tags=tag_list)
    
    # Get already installed template IDs
    installed_template_ids = set()
    if _engine is not None:
        try:
            with _engine.connect() as conn:
                result = conn.execute(
                    text("SELECT DISTINCT template_id FROM specialists WHERE template_id IS NOT NULL")
                )
                installed_template_ids = {row[0] for row in result.fetchall()}
        except Exception:
            pass  # If error, just show all templates
    
    # Filter out already installed templates
    available_templates = [t for t in templates if t.template_id not in installed_template_ids]
    
    return [TemplateResponse(**template.__dict__) for template in available_templates]


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
def install_specialist(
    template_id: str,
    request: InstallRequest,
    store: StoreService = Depends(get_store_service),
):
    """
    Install a specialist from TheAppApp App Store.
    
    Creates a new specialist instance based on the template.
    """
    from backend.api.dependencies import _engine
    from sqlalchemy import text
    import uuid
    
    if _engine is None:
        raise HTTPException(status_code=500, detail="Database engine not initialized")
    
    try:
        # Get installation data from store
        install_data = store.install_template(template_id, request.version)
        
        # Create specialist directly with engine
        specialist_id = str(uuid.uuid4())
        
        with _engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO specialists (
                        id, name, description, system_prompt, scope, 
                        web_search_enabled, web_search_config, tools_enabled,
                        version, template_id, installed_from_store,
                        display_name, avatar, bio, interests, favorite_tool, quote,
                        status, tags, model, temperature, max_tokens, required
                    ) VALUES (
                        :id, :name, :description, :system_prompt, :scope,
                        :web_search_enabled, :web_search_config, :tools_enabled,
                        :version, :template_id, :installed_from_store,
                        :display_name, :avatar, :bio, :interests, :favorite_tool, :quote,
                        :status, :tags, :model, :temperature, :max_tokens, :required
                    )
                """),
                {
                    "id": specialist_id,
                    "name": install_data["name"],
                    "description": install_data["description"],
                    "system_prompt": install_data["system_prompt"],
                    "scope": install_data.get("scope", "global"),
                    "web_search_enabled": install_data.get("web_search_enabled", False),
                    "web_search_config": install_data.get("web_search_config"),
                    "tools_enabled": install_data.get("tools_enabled"),
                    "version": install_data["version"],
                    "template_id": install_data["template_id"],
                    "installed_from_store": True,
                    "display_name": install_data["display_name"],
                    "avatar": install_data["avatar"],
                    "bio": install_data["bio"],
                    "interests": install_data.get("interests", []),
                    "favorite_tool": install_data["favorite_tool"],
                    "quote": install_data["quote"],
                    "status": "active",
                    "tags": install_data.get("tags", []),
                    "model": install_data.get("model", "gpt-4"),
                    "temperature": float(install_data.get("temperature", 0.7)),
                    "max_tokens": int(install_data.get("max_tokens", 4000)),
                    "required": False
                }
            )
            conn.commit()
        
        return {
            "specialist_id": specialist_id,
            "template_id": template_id,
            "version": install_data["version"],
            "message": f"Successfully installed {install_data['display_name']}!"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error installing specialist: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Installation failed: {str(e)}")


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
