"""
Agent Type Constants and Enums

Defines built-in agent types and categories for the system.
Built-in agents are core system agents that are always available in every project.
Specialists are user-created custom agents.

Reference: Section 1.2.5 - Built-In Agents vs Specialists Separation
"""
from enum import Enum
from typing import List


class AgentCategory(str, Enum):
    """Category of agent: built-in system agent or user specialist."""
    BUILT_IN = "built_in"
    SPECIALIST = "specialist"


# Built-in agent types (always available, cannot be removed)
# These MUST match the AgentType enum values in orchestrator.py
BUILT_IN_AGENTS: List[str] = [
    "orchestrator",
    "backend_developer",  # matches AgentType.BACKEND_DEVELOPER
    "frontend_developer",  # matches AgentType.FRONTEND_DEVELOPER
    "qa_engineer",
    "security_expert",
    "devops_engineer",
    "documentation_expert",
    "ui_ux_designer",  # matches AgentType.UI_UX_DESIGNER
    "github_specialist",
    "workshopper",
    "project_manager",
]


def is_built_in_agent(agent_type: str) -> bool:
    """
    Check if an agent type is a built-in system agent.
    
    Args:
        agent_type: Agent type identifier
    
    Returns:
        True if agent type is built-in, False otherwise
    """
    return agent_type in BUILT_IN_AGENTS


def validate_specialist_name(name: str) -> bool:
    """
    Validate that a specialist name doesn't conflict with built-in agents.
    
    Args:
        name: Proposed specialist name
    
    Returns:
        True if name is valid (not reserved), False if conflicts with built-in agent
    """
    return name.lower() not in [agent.lower() for agent in BUILT_IN_AGENTS]


def get_agent_category(agent_type: str) -> AgentCategory:
    """
    Determine the category of an agent.
    
    Args:
        agent_type: Agent type identifier
    
    Returns:
        AgentCategory.BUILT_IN or AgentCategory.SPECIALIST
    """
    if is_built_in_agent(agent_type):
        return AgentCategory.BUILT_IN
    return AgentCategory.SPECIALIST
