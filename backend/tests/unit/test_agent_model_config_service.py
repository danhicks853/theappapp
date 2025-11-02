"""
Unit tests for Agent Model Config Service.

Tests per-agent LLM configuration with caching and validation.
"""
import pytest
from unittest.mock import Mock, AsyncMock

from backend.services.agent_model_config_service import AgentModelConfigService, AgentModelConfig


@pytest.fixture
def service():
    """Create AgentModelConfigService."""
    return AgentModelConfigService()


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock()


class TestGetConfig:
    """Test retrieving agent configurations."""
    
    @pytest.mark.asyncio
    async def test_get_config_from_database(self, service, mock_db):
        """Test get_config retrieves from database."""
        mock_result = Mock()
        mock_result.first.return_value = ('gpt-4o-mini', 0.7, 8192)
        mock_db.execute.return_value = mock_result
        
        config = await service.get_config('backend_dev', mock_db)
        
        assert config.agent_type == 'backend_dev'
        assert config.model == 'gpt-4o-mini'
        assert config.temperature == 0.7
        assert config.max_tokens == 8192
    
    @pytest.mark.asyncio
    async def test_get_config_returns_default_if_not_found(self, service, mock_db):
        """Test get_config returns defaults if agent not in database."""
        mock_result = Mock()
        mock_result.first.return_value = None
        mock_db.execute.return_value = mock_result
        
        config = await service.get_config('unknown_agent', mock_db)
        
        assert config.agent_type == 'unknown_agent'
        assert config.model == 'gpt-4o-mini'  # Default
        assert config.temperature == 0.7  # Default
        assert config.max_tokens == 4096  # Default
    
    @pytest.mark.asyncio
    async def test_get_config_uses_cache(self, service, mock_db):
        """Test get_config uses cache for repeated requests."""
        mock_result = Mock()
        mock_result.first.return_value = ('gpt-4o', 0.5, 4096)
        mock_db.execute.return_value = mock_result
        
        # First call
        config1 = await service.get_config('orchestrator', mock_db)
        call_count_1 = mock_db.execute.call_count
        
        # Second call - should use cache
        config2 = await service.get_config('orchestrator', mock_db)
        call_count_2 = mock_db.execute.call_count
        
        assert config1.model == config2.model
        assert call_count_2 == call_count_1  # No additional DB call


class TestSetConfig:
    """Test updating agent configurations."""
    
    @pytest.mark.asyncio
    async def test_set_config_updates_database(self, service, mock_db):
        """Test set_config updates database."""
        result = await service.set_config(
            'backend_dev',
            'gpt-4o',
            0.8,
            16000,
            mock_db
        )
        
        assert result is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_set_config_validates_model(self, service, mock_db):
        """Test set_config rejects invalid model."""
        result = await service.set_config(
            'backend_dev',
            'invalid-model',
            0.7,
            4096,
            mock_db
        )
        
        assert result is False
        mock_db.execute.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_set_config_validates_temperature_range(self, service, mock_db):
        """Test set_config rejects invalid temperature."""
        result = await service.set_config(
            'backend_dev',
            'gpt-4o-mini',
            1.5,  # Invalid - must be 0.0-1.0
            4096,
            mock_db
        )
        
        assert result is False
        mock_db.execute.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_set_config_validates_max_tokens_positive(self, service, mock_db):
        """Test set_config rejects non-positive max_tokens."""
        result = await service.set_config(
            'backend_dev',
            'gpt-4o-mini',
            0.7,
            -100,  # Invalid - must be positive
            mock_db
        )
        
        assert result is False
        mock_db.execute.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_set_config_clears_cache(self, service, mock_db):
        """Test set_config clears cache for agent."""
        # Add to cache
        service._cache['backend_dev'] = (AgentModelConfig('backend_dev', 'gpt-4o-mini', 0.7, 4096), 0)
        
        await service.set_config('backend_dev', 'gpt-4o', 0.8, 8192, mock_db)
        
        # Cache should be cleared
        assert 'backend_dev' not in service._cache


class TestGetAllConfigs:
    """Test retrieving all agent configurations."""
    
    @pytest.mark.asyncio
    async def test_get_all_configs_returns_all_agents(self, service, mock_db):
        """Test get_all_configs returns all 10 agent types."""
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ('orchestrator', 'gpt-4o-mini', 0.3, 4096),
            ('backend_dev', 'gpt-4o-mini', 0.7, 8192),
        ]
        mock_db.execute.return_value = mock_result
        
        configs = await service.get_all_configs(mock_db)
        
        assert len(configs) == 2
        assert configs[0].agent_type == 'orchestrator'
        assert configs[1].agent_type == 'backend_dev'


class TestValidation:
    """Test configuration validation."""
    
    def test_validate_model_accepts_valid_models(self, service):
        """Test _validate_model accepts valid model names."""
        assert service._validate_model('gpt-4o-mini') is True
        assert service._validate_model('gpt-4o') is True
        assert service._validate_model('gpt-4-turbo') is True
        assert service._validate_model('gpt-3.5-turbo') is True
    
    def test_validate_model_rejects_invalid_models(self, service):
        """Test _validate_model rejects invalid model names."""
        assert service._validate_model('invalid-model') is False
        assert service._validate_model('gpt-5') is False
        assert service._validate_model('') is False
    
    def test_validate_temperature_accepts_valid_range(self, service):
        """Test _validate_temperature accepts 0.0-1.0."""
        assert service._validate_temperature(0.0) is True
        assert service._validate_temperature(0.5) is True
        assert service._validate_temperature(1.0) is True
    
    def test_validate_temperature_rejects_out_of_range(self, service):
        """Test _validate_temperature rejects values outside 0.0-1.0."""
        assert service._validate_temperature(-0.1) is False
        assert service._validate_temperature(1.1) is False
        assert service._validate_temperature(2.0) is False
    
    def test_validate_max_tokens_accepts_positive(self, service):
        """Test _validate_max_tokens accepts positive integers."""
        assert service._validate_max_tokens(1) is True
        assert service._validate_max_tokens(4096) is True
        assert service._validate_max_tokens(16000) is True
    
    def test_validate_max_tokens_rejects_non_positive(self, service):
        """Test _validate_max_tokens rejects non-positive values."""
        assert service._validate_max_tokens(0) is False
        assert service._validate_max_tokens(-100) is False


class TestAgentModelConfig:
    """Test AgentModelConfig dataclass."""
    
    def test_config_initialization(self):
        """Test AgentModelConfig initializes correctly."""
        config = AgentModelConfig(
            agent_type='backend_dev',
            model='gpt-4o',
            temperature=0.8,
            max_tokens=8192
        )
        
        assert config.agent_type == 'backend_dev'
        assert config.model == 'gpt-4o'
        assert config.temperature == 0.8
        assert config.max_tokens == 8192
