"""Settings API endpoints for autonomy level and other user preferences."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.api.dependencies import get_settings_service
from backend.models.user_settings import AutonomyLevel
from backend.services.settings_service import SettingsService


router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class AutonomyRequest(BaseModel):
    autonomy_level: AutonomyLevel = Field(..., description="New autonomy level")


class AutonomyResponse(BaseModel):
    autonomy_level: AutonomyLevel = Field(..., description="Current autonomy level")


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
