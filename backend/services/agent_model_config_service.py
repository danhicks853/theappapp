"""
Agent Model Configuration Service

Manages per-agent LLM model and temperature configuration.
Provides caching and validation for agent-specific settings.

Reference: Section 1.2.1 - Agent Model Configuration System
"""
import logging
import time
from typing import List, Dict, Tuple
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class AgentModelConfig:
    """
    Configuration for an agent's LLM settings.
    
    Attributes:
        agent_type: Type of agent (e.g., 'backend_dev', 'orchestrator')
        model: LLM model name (e.g., 'gpt-4o-mini', 'gpt-4o')
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens in response
    """
    agent_type: str
    model: str
    temperature: float
    max_tokens: int


class AgentModelConfigService:
    """
    Service for managing agent LLM configurations.
    
    Features:
    - Per-agent model and temperature settings
    - In-memory caching (5 minutes)
    - Configuration validation
    - Default fallback values
    
    Example:
        config_service = AgentModelConfigService()
        config = await config_service.get_config('backend_dev', db)
        # Returns: AgentModelConfig(model='gpt-4o-mini', temperature=0.7, ...)
    """
    
    CACHE_TTL_SECONDS = 300  # 5 minutes
    DEFAULT_MODEL = 'gpt-4o-mini'
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 4096
    ALLOWED_MODELS = ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo']
    
    def __init__(self):
        """Initialize agent model config service."""
        self._cache: Dict[str, Tuple[AgentModelConfig, float]] = {}
        logger.info("Agent model config service initialized")
    
    async def get_config(self, agent_type: str, db: AsyncSession) -> AgentModelConfig:
        """
        Get configuration for agent type.
        
        Args:
            agent_type: Agent type identifier
            db: Database session
        
        Returns:
            AgentModelConfig with model and temperature settings
        """
        # Check cache
        if agent_type in self._cache:
            config, timestamp = self._cache[agent_type]
            if time.time() - timestamp < self.CACHE_TTL_SECONDS:
                logger.debug(f"Cache hit for agent: {agent_type}")
                return config
            else:
                del self._cache[agent_type]
        
        # Query database
        logger.debug(f"Fetching config for agent: {agent_type}")
        query = text("""
            SELECT model, temperature, max_tokens
            FROM agent_model_configs
            WHERE agent_type = :agent_type AND is_active = true
        """)
        result = await db.execute(query, {"agent_type": agent_type})
        row = result.first()
        
        if row:
            config = AgentModelConfig(
                agent_type=agent_type,
                model=row[0],
                temperature=row[1],
                max_tokens=row[2]
            )
            logger.info(f"Config loaded for {agent_type}: model={config.model}, temp={config.temperature}")
        else:
            # Return defaults if not found
            logger.warning(f"No config found for {agent_type}, using defaults")
            config = AgentModelConfig(
                agent_type=agent_type,
                model=self.DEFAULT_MODEL,
                temperature=self.DEFAULT_TEMPERATURE,
                max_tokens=self.DEFAULT_MAX_TOKENS
            )
        
        # Cache it
        self._cache[agent_type] = (config, time.time())
        return config
    
    async def set_config(
        self,
        agent_type: str,
        model: str,
        temperature: float,
        max_tokens: int,
        db: AsyncSession
    ) -> bool:
        """
        Update configuration for agent type.
        
        Args:
            agent_type: Agent type identifier
            model: LLM model name
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum response tokens
            db: Database session
        
        Returns:
            True if updated successfully, False if validation failed
        """
        logger.info(f"Setting config for {agent_type}: model={model}, temp={temperature}")
        
        # Validate inputs
        if not self._validate_model(model):
            logger.error(f"Invalid model: {model}")
            return False
        
        if not self._validate_temperature(temperature):
            logger.error(f"Invalid temperature: {temperature} (must be 0.0-1.0)")
            return False
        
        if not self._validate_max_tokens(max_tokens):
            logger.error(f"Invalid max_tokens: {max_tokens} (must be positive)")
            return False
        
        # Upsert to database
        query = text("""
            INSERT INTO agent_model_configs (agent_type, model, temperature, max_tokens, updated_at)
            VALUES (:agent_type, :model, :temperature, :max_tokens, NOW())
            ON CONFLICT (agent_type)
            DO UPDATE SET
                model = :model,
                temperature = :temperature,
                max_tokens = :max_tokens,
                updated_at = NOW()
        """)
        
        await db.execute(query, {
            "agent_type": agent_type,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens
        })
        await db.commit()
        
        # Clear cache
        if agent_type in self._cache:
            del self._cache[agent_type]
        
        logger.info(f"Config updated successfully for {agent_type}")
        return True
    
    async def get_all_configs(self, db: AsyncSession) -> List[AgentModelConfig]:
        """
        Get configurations for all agents.
        
        Args:
            db: Database session
        
        Returns:
            List of AgentModelConfig objects
        """
        logger.debug("Fetching all agent configs")
        query = text("SELECT agent_type, model, temperature, max_tokens FROM agent_model_configs")
        result = await db.execute(query)
        rows = result.fetchall()
        
        configs = [
            AgentModelConfig(
                agent_type=row[0],
                model=row[1],
                temperature=row[2],
                max_tokens=row[3]
            )
            for row in rows
        ]
        
        logger.info(f"Loaded {len(configs)} agent configs")
        return configs
    
    def _validate_model(self, model: str) -> bool:
        """Validate model name is in allowed list."""
        return model in self.ALLOWED_MODELS
    
    def _validate_temperature(self, temperature: float) -> bool:
        """Validate temperature is in range 0.0-1.0."""
        return 0.0 <= temperature <= 1.0
    
    def _validate_max_tokens(self, max_tokens: int) -> bool:
        """Validate max_tokens is positive."""
        return max_tokens > 0
