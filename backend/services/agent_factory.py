"""
Agent Factory Service

Creates agents with correct prompt loading strategy based on agent category.
Built-in agents load from prompt versioning system, specialists load inline prompts.

Reference: Section 1.2.5 - Built-In Agents vs Specialists Separation
"""
import logging
from typing import Optional, Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from backend.models.agent_types import BUILT_IN_AGENTS, AgentCategory, is_built_in_agent
from backend.services.prompt_loading_service import PromptLoadingService
from backend.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class AgentFactory:
    """
    Factory for creating agents with correct prompt loading strategy.
    
    Features:
    - Routes to built-in or specialist creation path
    - Loads prompts from correct source (versioning vs inline)
    - Validates agent types and specialist IDs
    - Returns configured agent instance
    
    Example:
        factory = AgentFactory(engine)
        
        # Built-in agent
        agent = await factory.create_agent(agent_type="backend_dev")
        
        # Specialist
        agent = await factory.create_agent(specialist_id="uuid-123")
    """
    
    def __init__(self, engine: Engine):
        """Initialize agent factory."""
        self.engine = engine
        self.prompt_loading_service = PromptLoadingService(engine)
        logger.info("AgentFactory initialized")
    
    async def create_agent(
        self,
        agent_type: Optional[str] = None,
        specialist_id: Optional[str] = None,
        orchestrator: Optional[Any] = None,
        llm_client: Optional[Any] = None,
        **kwargs
    ) -> BaseAgent:
        """
        Create an agent instance with correct prompt loading.
        
        Args:
            agent_type: Built-in agent type (e.g., 'backend_dev')
            specialist_id: UUID of user-created specialist
            orchestrator: Orchestrator instance
            llm_client: LLM client instance
            **kwargs: Additional arguments for BaseAgent
        
        Returns:
            Configured BaseAgent instance
        
        Raises:
            ValueError: If neither agent_type nor specialist_id provided, or both provided
            RuntimeError: If built-in agent type invalid or specialist not found
        """
        # Validation: Must provide exactly one
        if not agent_type and not specialist_id:
            raise ValueError("Must provide either agent_type (built-in) or specialist_id")
        
        if agent_type and specialist_id:
            raise ValueError("Cannot provide both agent_type and specialist_id")
        
        # Route to appropriate creation method
        if agent_type:
            return await self._create_built_in_agent(
                agent_type=agent_type,
                orchestrator=orchestrator,
                llm_client=llm_client,
                **kwargs
            )
        else:
            return await self._create_specialist_agent(
                specialist_id=specialist_id,
                orchestrator=orchestrator,
                llm_client=llm_client,
                **kwargs
            )
    
    async def _create_built_in_agent(
        self,
        agent_type: str,
        orchestrator: Optional[Any],
        llm_client: Optional[Any],
        **kwargs
    ) -> BaseAgent:
        """
        Create a built-in system agent with versioned prompt.
        
        Args:
            agent_type: Built-in agent type
            orchestrator: Orchestrator instance
            llm_client: LLM client instance
            **kwargs: Additional BaseAgent args
        
        Returns:
            BaseAgent instance with versioned prompt
        
        Raises:
            RuntimeError: If agent_type not in BUILT_IN_AGENTS or no active prompt
        """
        # Validate agent type
        if not is_built_in_agent(agent_type):
            raise RuntimeError(
                f"Invalid built-in agent type: {agent_type}. "
                f"Must be one of: {', '.join(BUILT_IN_AGENTS)}"
            )
        
        logger.info(f"Creating built-in agent: {agent_type}")
        
        # Load versioned prompt
        system_prompt = await self.prompt_loading_service.get_active_prompt(agent_type)
        
        # Create agent with versioned prompt
        agent = BaseAgent(
            agent_id=f"{agent_type}-{id(self)}",  # Generate unique ID
            agent_type=agent_type,
            orchestrator=orchestrator,
            llm_client=llm_client,
            system_prompt=system_prompt,
            **kwargs
        )
        
        logger.info(f"Built-in agent created: {agent_type}")
        return agent
    
    async def _create_specialist_agent(
        self,
        specialist_id: str,
        orchestrator: Optional[Any],
        llm_client: Optional[Any],
        **kwargs
    ) -> BaseAgent:
        """
        Create a specialist agent with inline prompt from database.
        
        Args:
            specialist_id: UUID of specialist
            orchestrator: Orchestrator instance
            llm_client: LLM client instance
            **kwargs: Additional BaseAgent args
        
        Returns:
            BaseAgent instance with specialist's inline prompt
        
        Raises:
            RuntimeError: If specialist not found in database
        """
        logger.info(f"Creating specialist agent: {specialist_id}")
        
        # Load specialist from database
        query = text("""
            SELECT name, system_prompt, model, temperature, max_tokens
            FROM specialists
            WHERE id = :specialist_id AND status = 'active'
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {"specialist_id": specialist_id})
            row = result.fetchone()
        
        if not row:
            raise RuntimeError(f"Specialist not found or inactive: {specialist_id}")
        
        name, system_prompt, model, temperature, max_tokens = row
        
        # Create agent with specialist's inline prompt
        agent = BaseAgent(
            agent_id=f"specialist-{specialist_id}",
            agent_type=f"specialist_{name}",  # Mark as specialist
            orchestrator=orchestrator,
            llm_client=llm_client,
            system_prompt=system_prompt,
            **kwargs
        )
        
        logger.info(f"Specialist agent created: {name} ({specialist_id})")
        return agent
    
    def get_agent_category(self, agent_type: Optional[str] = None) -> AgentCategory:
        """
        Get the category of an agent.
        
        Args:
            agent_type: Agent type to check
        
        Returns:
            AgentCategory.BUILT_IN or AgentCategory.SPECIALIST
        """
        if agent_type and is_built_in_agent(agent_type):
            return AgentCategory.BUILT_IN
        return AgentCategory.SPECIALIST
