"""Autonomy escalation policy derived from Decision 67."""

from __future__ import annotations

from dataclasses import dataclass

from backend.models.user_settings import AutonomyLevel


@dataclass(frozen=True)
class AutonomyThresholds:
    """Threshold configuration for a specific autonomy level."""

    escalation_floor: float
    description: str


_AUTONOMY_THRESHOLDS: dict[AutonomyLevel, AutonomyThresholds] = {
    AutonomyLevel.LOW: AutonomyThresholds(
        escalation_floor=0.999,  # always escalate regardless of score
        description="Low autonomy escalates all uncertainty to humans.",
    ),
    AutonomyLevel.MEDIUM: AutonomyThresholds(
        escalation_floor=0.7,
        description="Medium autonomy escalates on uncertainty above 0.3.",
    ),
    AutonomyLevel.HIGH: AutonomyThresholds(
        escalation_floor=0.3,
        description="High autonomy escalates only on low confidence (<0.3).",
    ),
}


def should_escalate(*, autonomy_level: AutonomyLevel, confidence_score: float) -> bool:
    """Return True when the situation should trigger human escalation."""

    thresholds = _AUTONOMY_THRESHOLDS[autonomy_level]
    if autonomy_level is AutonomyLevel.LOW:
        return True

    return confidence_score < thresholds.escalation_floor
