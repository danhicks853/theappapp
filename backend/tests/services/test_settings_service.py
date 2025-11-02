"""Unit tests for SettingsService autonomy level CRUD."""

from __future__ import annotations

import pytest

from backend.models.user_settings import AutonomyLevel, UserSettings
from backend.services.settings_service import InMemorySettingsService


def test_get_autonomy_level_returns_medium_when_missing():
    service = InMemorySettingsService()

    level = service.get_autonomy_level("nonexistent-user")

    assert level == AutonomyLevel.MEDIUM


def test_set_autonomy_level_creates_or_updates_and_returns_model():
    service = InMemorySettingsService()

    model = service.set_autonomy_level("user-123", AutonomyLevel.HIGH)

    assert isinstance(model, UserSettings)
    assert model.user_id == "user-123"
    assert model.autonomy_level == AutonomyLevel.HIGH

    # second call should update existing record
    model = service.set_autonomy_level("user-123", AutonomyLevel.LOW)
    assert model.autonomy_level == AutonomyLevel.LOW
