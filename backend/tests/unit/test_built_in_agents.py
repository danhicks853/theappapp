"""
Built-In Agents Unit Tests

Tests agent factory, prompt loading, and all 11 agent types.
"""
import pytest
from unittest.mock import Mock, mock_open, patch
from backend.services.agent_factory import AgentFactory
from backend.services.built_in_agent_loader import BuiltInAgentLoader


@pytest.mark.unit
class TestAgentFactory:
    """Test agent factory instantiation."""
    
    def test_create_agent_backend_developer(self):
        """Test creating backend developer agent."""
        factory = AgentFactory()
        
        agent = factory.create_agent(
            agent_type="backend_developer",
            agent_id="backend-1"
        )
        
        assert agent is not None
        assert agent.agent_id == "backend-1"
        assert agent.agent_type == "backend_developer"
    
    def test_create_agent_all_11_types(self):
        """Test creating all 11 built-in agent types."""
        factory = AgentFactory()
        
        agent_types = [
            "backend_developer",
            "frontend_developer",
            "qa_engineer",
            "security_expert",
            "devops_engineer",
            "database_expert",
            "ui_ux_designer",
            "documentation_expert",
            "product_manager",
            "architect",
            "data_scientist"
        ]
        
        for agent_type in agent_types:
            agent = factory.create_agent(
                agent_type=agent_type,
                agent_id=f"{agent_type}-1"
            )
            assert agent is not None
            assert agent.agent_type == agent_type
    
    def test_create_agent_invalid_type_raises_error(self):
        """Test creating agent with invalid type raises error."""
        factory = AgentFactory()
        
        with pytest.raises(ValueError):
            factory.create_agent(
                agent_type="invalid_agent_type",
                agent_id="agent-1"
            )
    
    def test_agent_has_prompt(self):
        """Test created agent has prompt loaded."""
        factory = AgentFactory()
        
        agent = factory.create_agent(
            agent_type="backend_developer",
            agent_id="backend-1"
        )
        
        assert hasattr(agent, "prompt")
        assert agent.prompt is not None


@pytest.mark.unit
class TestBuiltInAgentLoader:
    """Test built-in agent prompt loading."""
    
    def test_load_agent_prompt(self):
        """Test loading agent prompt from file."""
        loader = BuiltInAgentLoader()
        
        prompt = loader.load_prompt("backend_developer")
        
        assert prompt is not None
        assert len(prompt) > 0
    
    def test_load_all_agent_prompts(self):
        """Test loading all 11 agent prompts."""
        loader = BuiltInAgentLoader()
        
        agent_types = [
            "backend_developer", "frontend_developer", "qa_engineer",
            "security_expert", "devops_engineer", "database_expert",
            "ui_ux_designer", "documentation_expert", "product_manager",
            "architect", "data_scientist"
        ]
        
        for agent_type in agent_types:
            prompt = loader.load_prompt(agent_type)
            assert prompt is not None, f"Failed to load prompt for {agent_type}"
    
    def test_prompt_contains_role_definition(self):
        """Test prompt contains role definition."""
        loader = BuiltInAgentLoader()
        
        prompt = loader.load_prompt("backend_developer")
        
        # Should define the role
        assert "backend" in prompt.lower() or "developer" in prompt.lower()
    
    def test_load_nonexistent_agent_raises_error(self):
        """Test loading nonexistent agent raises error."""
        loader = BuiltInAgentLoader()
        
        with pytest.raises(FileNotFoundError):
            loader.load_prompt("nonexistent_agent")


@pytest.mark.unit
class TestPromptTemplateRendering:
    """Test prompt template variable substitution."""
    
    def test_render_prompt_with_variables(self):
        """Test rendering prompt with variables."""
        loader = BuiltInAgentLoader()
        
        template = "You are a {role} working on {project}"
        variables = {"role": "backend developer", "project": "TheAppApp"}
        
        rendered = loader.render_template(template, variables)
        
        assert "backend developer" in rendered
        assert "TheAppApp" in rendered
    
    def test_render_prompt_without_variables(self):
        """Test rendering prompt without variables returns original."""
        loader = BuiltInAgentLoader()
        
        template = "Static prompt with no variables"
        
        rendered = loader.render_template(template, {})
        
        assert rendered == template
    
    def test_render_prompt_missing_variable_raises_error(self):
        """Test rendering with missing variable raises error."""
        loader = BuiltInAgentLoader()
        
        template = "Project: {project}, Goal: {goal}"
        variables = {"project": "test"}  # Missing 'goal'
        
        with pytest.raises(KeyError):
            loader.render_template(template, variables)


@pytest.mark.unit
class TestAgentConfiguration:
    """Test agent configuration and customization."""
    
    def test_agent_with_custom_config(self):
        """Test creating agent with custom configuration."""
        factory = AgentFactory()
        
        agent = factory.create_agent(
            agent_type="backend_developer",
            agent_id="backend-1",
            config={"temperature": 0.5, "max_tokens": 2000}
        )
        
        assert agent.config["temperature"] == 0.5
        assert agent.config["max_tokens"] == 2000
    
    def test_agent_with_default_config(self):
        """Test agent uses default config when not specified."""
        factory = AgentFactory()
        
        agent = factory.create_agent(
            agent_type="backend_developer",
            agent_id="backend-1"
        )
        
        assert hasattr(agent, "config")
        assert agent.config is not None


@pytest.mark.unit
class TestAgentTypeValidation:
    """Test agent type validation."""
    
    def test_valid_agent_types(self):
        """Test all valid agent types are recognized."""
        factory = AgentFactory()
        
        valid_types = factory.get_valid_agent_types()
        
        assert len(valid_types) == 11
        assert "backend_developer" in valid_types
        assert "frontend_developer" in valid_types
        assert "qa_engineer" in valid_types
    
    def test_is_valid_agent_type(self):
        """Test checking if agent type is valid."""
        factory = AgentFactory()
        
        assert factory.is_valid_agent_type("backend_developer")
        assert factory.is_valid_agent_type("qa_engineer")
        assert not factory.is_valid_agent_type("invalid_type")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
