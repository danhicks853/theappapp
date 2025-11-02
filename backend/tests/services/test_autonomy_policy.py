"""Unit tests for autonomy escalation policy."""

from __future__ import annotations

import pytest

from backend.models.user_settings import AutonomyLevel
from backend.services.autonomy_policy import should_escalate


@pytest.mark.parametrize(
    "autonomy_level,confidence,expected",
    [
        (AutonomyLevel.LOW, 0.9, True),
        (AutonomyLevel.MEDIUM, 0.5, True),
        (AutonomyLevel.MEDIUM, 0.8, False),
        (AutonomyLevel.HIGH, 0.2, True),
        (AutonomyLevel.HIGH, 0.6, False),
    ],
)
def test_should_escalate_thresholds(autonomy_level, confidence, expected):
    """Escalation respects Decision 67 thresholds per autonomy level."""

    assert should_escalate(autonomy_level=autonomy_level, confidence_score=confidence) is expected
