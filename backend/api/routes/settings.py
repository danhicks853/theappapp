"""Settings API endpoints for autonomy level and other user preferences."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.api.dependencies import get_settings_service, get_api_key_service
from backend.models.user_settings import AutonomyLevel
from backend.services.settings_service import SettingsService
from backend.services.api_key_service import APIKeyService


router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class AutonomyRequest(BaseModel):
    autonomy_level: AutonomyLevel = Field(..., description="New autonomy level")


class AutonomyResponse(BaseModel):
    autonomy_level: AutonomyLevel = Field(..., description="Current autonomy level")


class ApiKeyRequest(BaseModel):
    service: str = Field(..., description="Service name (e.g., 'openai')")
    api_key: str = Field(..., description="API key to store")


class ApiKeyStatusResponse(BaseModel):
    service: str
    is_configured: bool
    is_active: bool
    created_at: Optional[str] = None


class ApiKeyTestResponse(BaseModel):
    service: str
    is_valid: bool
    error: Optional[str] = None


class AgentConfigItem(BaseModel):
    agent_type: str
    model: str
    temperature: float
    max_tokens: int


class AgentConfigListResponse(BaseModel):
    configs: list[AgentConfigItem]


@router.get("/autonomy", response_model=AutonomyResponse)
def get_autonomy(user_id: str, service: SettingsService = Depends(get_settings_service)) -> AutonomyResponse:
    """Get the current autonomy level for the user.

    Args:
        user_id: User identifier (TODO: extract from JWT token in auth middleware)
        service: SettingsService instance (injected via FastAPI Depends)

    Returns:
        Current autonomy level for the user
    """
    level = service.get_autonomy_level(user_id)
    return AutonomyResponse(autonomy_level=level)


@router.put("/autonomy", response_model=AutonomyResponse)
def set_autonomy(
    payload: AutonomyRequest,
    user_id: str,
    service: SettingsService = Depends(get_settings_service),
) -> AutonomyResponse:
    """Update the autonomy level for the user.

    Args:
        payload: New autonomy level setting
        user_id: User identifier (TODO: extract from JWT token in auth middleware)
        service: SettingsService instance (injected via FastAPI Depends)

    Returns:
        Updated autonomy level
    """
    model = service.set_autonomy_level(user_id, payload.autonomy_level)
    return AutonomyResponse(autonomy_level=model.autonomy_level)


@router.post("/api-keys", response_model=ApiKeyStatusResponse)
async def set_api_key(
    payload: ApiKeyRequest,
    key_service: APIKeyService = Depends(get_api_key_service),
) -> ApiKeyStatusResponse:
    """Store or update an API key for a service.

    Args:
        payload: Service name and API key
        key_service: APIKeyService instance (injected)

    Returns:
        Status of the stored API key
    """
    await key_service.set_key(payload.service, payload.api_key)
    
    # Return status after setting
    return ApiKeyStatusResponse(
        service=payload.service,
        is_configured=True,
        is_active=True,
        created_at=None  # Could add timestamp from DB if needed
    )


@router.get("/api-keys/{service}", response_model=ApiKeyStatusResponse)
async def get_api_key_status(
    service: str,
    key_service: APIKeyService = Depends(get_api_key_service),
) -> ApiKeyStatusResponse:
    """Get the status of an API key for a service.

    Args:
        service: Service name (e.g., 'openai')
        key_service: APIKeyService instance (injected)

    Returns:
        Status of the API key (configured, active, etc.)
    """
    try:
        key = await key_service.get_key(service)
        is_configured = key is not None and len(key) > 0
        
        return ApiKeyStatusResponse(
            service=service,
            is_configured=is_configured,
            is_active=is_configured,  # Assume active if configured
            created_at=None
        )
    except Exception:
        return ApiKeyStatusResponse(
            service=service,
            is_configured=False,
            is_active=False,
            created_at=None
        )


@router.get("/api-keys/{service}/test", response_model=ApiKeyTestResponse)
async def test_api_key(
    service: str,
    key_service: APIKeyService = Depends(get_api_key_service),
) -> ApiKeyTestResponse:
    """Test if an API key is valid by making a test request.

    Args:
        service: Service name (e.g., 'openai')
        key_service: APIKeyService instance (injected)

    Returns:
        Validation result
    """
    try:
        is_valid = await key_service.test_key(service)
        return ApiKeyTestResponse(
            service=service,
            is_valid=is_valid,
            error=None if is_valid else "API key validation failed"
        )
    except Exception as e:
        return ApiKeyTestResponse(
            service=service,
            is_valid=False,
            error=str(e)
        )


@router.get("/agent-configs", response_model=list[AgentConfigItem])
async def get_agent_configs() -> list[AgentConfigItem]:
    """Get all agent model configurations.

    Returns:
        List of agent configurations
    """
    # TODO: Properly implement with database session
    # For now, return default configs from migration seed data
    default_configs = [
        {"agent_type": "orchestrator", "model": "gpt-4o-mini", "temperature": 0.3, "max_tokens": 4096},
        {"agent_type": "backend_dev", "model": "gpt-4o-mini", "temperature": 0.7, "max_tokens": 8192},
        {"agent_type": "frontend_dev", "model": "gpt-4o-mini", "temperature": 0.7, "max_tokens": 8192},
        {"agent_type": "qa_engineer", "model": "gpt-4o-mini", "temperature": 0.5, "max_tokens": 4096},
        {"agent_type": "security_expert", "model": "gpt-4o-mini", "temperature": 0.3, "max_tokens": 4096},
        {"agent_type": "devops_engineer", "model": "gpt-4o-mini", "temperature": 0.5, "max_tokens": 4096},
        {"agent_type": "documentation_expert", "model": "gpt-4o-mini", "temperature": 0.7, "max_tokens": 8192},
        {"agent_type": "uiux_designer", "model": "gpt-4o-mini", "temperature": 0.8, "max_tokens": 8192},
        {"agent_type": "github_specialist", "model": "gpt-4o-mini", "temperature": 0.5, "max_tokens": 4096},
        {"agent_type": "workshopper", "model": "gpt-4o-mini", "temperature": 0.7, "max_tokens": 8192},
        {"agent_type": "project_manager", "model": "gpt-4o-mini", "temperature": 0.5, "max_tokens": 4096},
    ]
    
    return [AgentConfigItem(**config) for config in default_configs]


@router.put("/agent-configs", response_model=dict)
async def update_agent_configs(
    configs: list[AgentConfigItem],
) -> dict:
    """Update agent model configurations in bulk.

    Args:
        configs: List of agent configurations to update

    Returns:
        Success status
    """
    # TODO: Properly implement with database session and AgentModelConfigService
    # For now, just return success
    return {"status": "success", "updated_count": len(configs)}
