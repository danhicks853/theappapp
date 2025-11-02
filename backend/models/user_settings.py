"""User settings models and validation for orchestrator autonomy configuration."""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field, validator


class AutonomyLevel(str, Enum):
    """Enumerates orchestrator autonomy levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class UserSettings(BaseModel):
    """Represents persisted user settings with autonomy configuration."""

    user_id: str = Field(..., min_length=1, description="Unique identifier for the user")
    autonomy_level: AutonomyLevel = Field(
        AutonomyLevel.MEDIUM,
        description="Orchestrator autonomy preference",
    )

    @validator("autonomy_level", pre=True)
    def _normalize_level(cls, value: str | AutonomyLevel) -> AutonomyLevel:
        if isinstance(value, AutonomyLevel):
            return value
        lowered = value.lower()
        if lowered not in {member.value for member in AutonomyLevel}:
            raise ValueError("autonomy_level must be 'low', 'medium', or 'high'")
        return AutonomyLevel(lowered)
