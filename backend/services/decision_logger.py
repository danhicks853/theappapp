"""Simple decision logging service for orchestrator decisions."""

from __future__ import annotations

from typing import Any, Dict

from sqlalchemy import Table, insert
from sqlalchemy.engine import Engine

from backend.models import AutonomyLevel


class DecisionLogger:
    """Persists orchestrator decisions to the database."""

    def __init__(self, *, engine: Engine, table: Table) -> None:
        self._engine = engine
        self._table = table

    async def __call__(self, entry: Dict[str, Any]) -> None:
        """Async-compatible call interface for orchestrator.log_decision."""

        self._insert(entry)

    def _insert(self, entry: Dict[str, Any]) -> None:
        record = {
            "id": entry.get("id"),
            "project_id": entry.get("project_id"),
            "decision_type": entry.get("decision_type"),
            "situation": entry.get("situation"),
            "reasoning": entry.get("reasoning"),
            "decision": entry.get("decision"),
            "autonomy_level": entry.get("autonomy_level", AutonomyLevel.MEDIUM.value),
            "rag_context": entry.get("rag_context"),
            "confidence": entry.get("confidence"),
            "tokens_input": entry.get("tokens_input"),
            "tokens_output": entry.get("tokens_output"),
            "execution_result": entry.get("execution_result"),
        }

        with self._engine.begin() as connection:
            connection.execute(insert(self._table).values(record))
