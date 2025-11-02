"""
Built-In Agent Loader

Helper service to instantiate built-in system agents with correct classes.
Maps agent_type to concrete agent class implementations.

Reference: Section 1.2.5 - Built-In Agents vs Specialists Separation
"""
import logging
from typing import Optional, Any, Type

from backend.models.agent_types import BUILT_IN_AGENTS, is_built_in_agent
from backend.services.prompt_loading_service import PromptLoadingService
from backend.agents.base_agent import BaseAgent
from backend.agents.backend_dev_agent import BackendDeveloperAgent
from backend.agents.frontend_dev_agent import FrontendDeveloperAgent
from backend.agents.qa_engineer_agent import QAEngineerAgent
from backend.agents.security_expert_agent import SecurityExpertAgent
from backend.agents.devops_engineer_agent import DevOpsEngineerAgent
from backend.agents.documentation_expert_agent import DocumentationExpertAgent
from backend.agents.uiux_designer_agent import UIUXDesignerAgent
from backend.agents.github_specialist_agent import GitHubSpecialistAgent
from backend.agents.workshopper_agent import WorkshopperAgent
from backend.agents.project_manager_agent import ProjectManagerAgent

logger = logging.getLogger(__name__)


# Mapping of agent_type to concrete agent class
AGENT_CLASS_MAP: dict[str, Type[BaseAgent]] = {
    "backend_dev": BackendDeveloperAgent,
    "frontend_dev": FrontendDeveloperAgent,
    "qa_engineer": QAEngineerAgent,
    "security_expert": SecurityExpertAgent,
    "devops_engineer": DevOpsEngineerAgent,
    "documentation_expert": DocumentationExpertAgent,
    "uiux_designer": UIUXDesignerAgent,
    "github_specialist": GitHubSpecialistAgent,
    "workshopper": WorkshopperAgent,
    "project_manager": ProjectManagerAgent,
    # Orchestrator doesn't have a separate class, uses BaseAgent
    "orchestrator": BaseAgent,
}


async def load_built_in_agent(
    agent_type: str,
    engine: Any,
    orchestrator: Optional[Any] = None,
    llm_client: Optional[Any] = None,
    **kwargs
) -> BaseAgent:
    """
    Load and instantiate a built-in system agent with versioned prompt.
    
    Args:
        agent_type: Built-in agent type (e.g., 'backend_dev')
        engine: Database engine for prompt loading
        orchestrator: Orchestrator instance
        llm_client: LLM client instance
        **kwargs: Additional arguments for agent constructor
    
    Returns:
        Configured agent instance with correct class and versioned prompt
    
    Raises:
        ValueError: If agent_type not a built-in agent
        RuntimeError: If no active prompt found for agent
    
    Example:
        agent = await load_built_in_agent(
            agent_type="backend_dev",
            engine=engine,
            orchestrator=orchestrator,
            llm_client=llm_client
        )
    """
    # Validate built-in agent
    if not is_built_in_agent(agent_type):
        raise ValueError(
            f"Not a built-in agent: {agent_type}. "
            f"Must be one of: {', '.join(BUILT_IN_AGENTS)}"
        )
    
    logger.info(f"Loading built-in agent: {agent_type}")
    
    # Load versioned prompt
    prompt_loader = PromptLoadingService(engine)
    system_prompt = await prompt_loader.get_active_prompt(agent_type)
    
    # Get correct agent class
    agent_class = AGENT_CLASS_MAP.get(agent_type, BaseAgent)
    
    # Instantiate with versioned prompt
    agent = agent_class(
        agent_id=f"{agent_type}-instance",
        agent_type=agent_type,
        orchestrator=orchestrator,
        llm_client=llm_client,
        system_prompt=system_prompt,
        **kwargs
    )
    
    logger.info(f"Built-in agent loaded: {agent_type} (class: {agent_class.__name__})")
    return agent


def get_built_in_agent_class(agent_type: str) -> Type[BaseAgent]:
    """
    Get the concrete class for a built-in agent type.
    
    Args:
        agent_type: Built-in agent type
    
    Returns:
        Agent class (subclass of BaseAgent)
    
    Raises:
        ValueError: If agent_type not a built-in agent
    """
    if not is_built_in_agent(agent_type):
        raise ValueError(f"Not a built-in agent: {agent_type}")
    
    return AGENT_CLASS_MAP.get(agent_type, BaseAgent)


def list_built_in_agents() -> list[str]:
    """
    Get list of all built-in agent types.
    
    Returns:
        List of built-in agent type identifiers
    """
    return BUILT_IN_AGENTS.copy()
