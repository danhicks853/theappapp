"""Service for reading and updating user settings including autonomy level."""

from __future__ import annotations

from sqlalchemy import Table, insert, select, update
from sqlalchemy.engine import Engine

from backend.models.user_settings import AutonomyLevel, UserSettings


class SettingsService:
    """Provides CRUD operations for user settings."""

    def __init__(self, *, engine: Engine, table: Table) -> None:
        self._engine = engine
        self._table = table

    def get_autonomy_level(self, user_id: str) -> AutonomyLevel:
        with self._engine.begin() as connection:
            row = connection.execute(
                select(self._table.c.autonomy_level).where(self._table.c.user_id == user_id)
            ).first()

        if not row:
            return AutonomyLevel.MEDIUM

        return AutonomyLevel(row.autonomy_level)

    def set_autonomy_level(self, user_id: str, autonomy_level: AutonomyLevel) -> UserSettings:
        payload = {
            "user_id": user_id,
            "autonomy_level": autonomy_level.value,
        }

        with self._engine.begin() as connection:
            row = connection.execute(
                select(self._table.c.id).where(self._table.c.user_id == user_id)
            ).first()

            if row:
                connection.execute(
                    update(self._table)
                    .where(self._table.c.user_id == user_id)
                    .values(autonomy_level=autonomy_level.value)
                )
            else:
                payload["id"] = user_id
                connection.execute(insert(self._table).values(payload))

        return UserSettings(user_id=user_id, autonomy_level=autonomy_level)


class InMemorySettingsService:
    """In-memory implementation for unit testing (no SQLAlchemy)."""

    def __init__(self) -> None:
        self._store: Dict[str, AutonomyLevel] = {}

    def get_autonomy_level(self, user_id: str) -> AutonomyLevel:
        return self._store.get(user_id, AutonomyLevel.MEDIUM)

    def set_autonomy_level(self, user_id: str, autonomy_level: AutonomyLevel) -> UserSettings:
        self._store[user_id] = autonomy_level
        return UserSettings(user_id=user_id, autonomy_level=autonomy_level)
