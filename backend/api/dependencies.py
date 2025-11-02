"""FastAPI dependency injection providers for services and database connections."""

from __future__ import annotations

from typing import Generator

from sqlalchemy import MetaData, Table, create_engine
from sqlalchemy.engine import Engine, Connection

from backend.services.settings_service import SettingsService
from backend.services.api_key_service import APIKeyService
from backend.services.agent_model_config_service import AgentModelConfigService
from backend.services.gate_manager import GateManager
from backend.services.prompt_loading_service import PromptLoadingService
from backend.services.prompt_management_service import PromptManagementService

# Global engine instance (will be initialized in create_app)
_engine: Engine | None = None
_metadata: MetaData | None = None


def initialize_engine(database_url: str) -> None:
    """Initialize the global database engine.

    This should be called once during application startup.

    Args:
        database_url: SQLAlchemy database URL
    """
    global _engine, _metadata
    _engine = create_engine(database_url)
    _metadata = MetaData()
    _metadata.reflect(bind=_engine)


def get_engine() -> Generator[Engine, None, None]:
    """FastAPI dependency for database engine.

    Yields:
        The global SQLAlchemy engine instance

    Raises:
        RuntimeError: If engine has not been initialized
    """
    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call initialize_engine() first.")
    yield _engine


def get_db() -> Generator[Connection, None, None]:
    """FastAPI dependency for database connection.

    Yields:
        A SQLAlchemy database connection

    Raises:
        RuntimeError: If engine has not been initialized
    """
    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call initialize_engine() first.")
    
    with _engine.connect() as connection:
        yield connection


def get_settings_service() -> Generator[SettingsService, None, None]:
    """FastAPI dependency for SettingsService.

    Yields:
        Configured SettingsService instance

    Raises:
        RuntimeError: If engine/metadata has not been initialized
    """
    if _engine is None or _metadata is None:
        raise RuntimeError("Database not initialized. Call initialize_engine() first.")

    # Get the user_settings table from metadata
    user_settings_table: Table = _metadata.tables.get("user_settings")
    if user_settings_table is None:
        raise RuntimeError("user_settings table not found in database schema")

    yield SettingsService(engine=_engine, table=user_settings_table)


def get_api_key_service() -> Generator[APIKeyService, None, None]:
    """FastAPI dependency for APIKeyService.

    Yields:
        Configured APIKeyService instance

    Raises:
        RuntimeError: If engine/metadata has not been initialized
    """
    if _engine is None or _metadata is None:
        raise RuntimeError("Database not initialized. Call initialize_engine() first.")

    # Get the api_keys table from metadata
    api_keys_table: Table = _metadata.tables.get("api_keys")
    if api_keys_table is None:
        raise RuntimeError("api_keys table not found in database schema")

    yield APIKeyService(engine=_engine, table=api_keys_table)


def get_agent_model_config_service() -> Generator[AgentModelConfigService, None, None]:
    """FastAPI dependency for AgentModelConfigService.

    Yields:
        Configured AgentModelConfigService instance

    Raises:
        RuntimeError: If engine/metadata has not been initialized
    """
    if _engine is None or _metadata is None:
        raise RuntimeError("Database not initialized. Call initialize_engine() first.")

    # Get the agent_model_configs table from metadata
    agent_configs_table: Table = _metadata.tables.get("agent_model_configs")
    if agent_configs_table is None:
        raise RuntimeError("agent_model_configs table not found in database schema")

    yield AgentModelConfigService(engine=_engine, table=agent_configs_table)


def get_gate_manager() -> Generator[GateManager, None, None]:
    """FastAPI dependency for GateManager.

    Yields:
        Configured GateManager instance

    Raises:
        RuntimeError: If engine has not been initialized
    """
    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call initialize_engine() first.")

    yield GateManager(engine=_engine)


def get_prompt_loading_service() -> Generator[PromptLoadingService, None, None]:
    """FastAPI dependency for PromptLoadingService.

    Yields:
        Configured PromptLoadingService instance

    Raises:
        RuntimeError: If engine has not been initialized
    """
    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call initialize_engine() first.")

    yield PromptLoadingService(engine=_engine)


def get_prompt_management_service() -> Generator[PromptManagementService, None, None]:
    """FastAPI dependency for PromptManagementService.

    Yields:
        Configured PromptManagementService instance

    Raises:
        RuntimeError: If engine has not been initialized
    """
    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call initialize_engine() first.")

    yield PromptManagementService(engine=_engine)
