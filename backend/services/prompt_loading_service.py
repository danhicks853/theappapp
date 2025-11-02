"""
Prompt Loading Service

Loads active prompt versions for agent types with caching.
Auto-loads latest version for each agent.

Reference: Section 1.2.4 - Prompt Versioning System
"""
import logging
import time
from typing import Optional, Dict, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class PromptLoadingService:
    """
    Service for loading active prompts with caching.
    
    Features:
    - Load active prompt for agent type
    - 5-minute cache TTL
    - Automatic fallback to defaults
    - Error handling
    
    Example:
        service = PromptLoadingService(engine)
        prompt = await service.get_active_prompt("backend_dev")
    """
    
    CACHE_TTL_SECONDS = 300  # 5 minutes
    
    def __init__(self, engine: Engine):
        """Initialize prompt loading service."""
        self.engine = engine
        self._cache: Dict[str, Tuple[str, float]] = {}
        logger.info("PromptLoadingService initialized")
    
    async def get_active_prompt(self, agent_type: str) -> str:
        """
        Get active prompt for agent type.
        
        Args:
            agent_type: Agent type identifier (e.g., 'backend_dev', 'orchestrator')
        
        Returns:
            Active prompt text
        
        Raises:
            RuntimeError: If no active prompt found and no default available
        """
        # Check cache
        if agent_type in self._cache:
            prompt_text, timestamp = self._cache[agent_type]
            if time.time() - timestamp < self.CACHE_TTL_SECONDS:
                logger.debug(f"Cache hit for agent type: {agent_type}")
                return prompt_text
            else:
                del self._cache[agent_type]
        
        # Query database for active prompt
        logger.debug(f"Loading active prompt for agent type: {agent_type}")
        
        query = text("""
            SELECT prompt_text
            FROM prompts
            WHERE agent_type = :agent_type AND is_active = true
            LIMIT 1
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {"agent_type": agent_type})
            row = result.fetchone()
            
            if row:
                prompt_text = row[0]
                # Cache it
                self._cache[agent_type] = (prompt_text, time.time())
                logger.info(f"Loaded active prompt for {agent_type} (length: {len(prompt_text)} chars)")
                return prompt_text
            else:
                logger.error(f"No active prompt found for agent type: {agent_type}")
                raise RuntimeError(f"No active prompt configured for agent type: {agent_type}")
    
    def clear_cache(self, agent_type: Optional[str] = None) -> None:
        """
        Clear cache for specific agent type or all.
        
        Args:
            agent_type: Optional agent type to clear, or None to clear all
        """
        if agent_type:
            if agent_type in self._cache:
                del self._cache[agent_type]
                logger.info(f"Cache cleared for agent type: {agent_type}")
        else:
            self._cache.clear()
            logger.info("Cache cleared for all agent types")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        return {
            "cached_agents": len(self._cache),
            "cache_ttl_seconds": self.CACHE_TTL_SECONDS
        }
