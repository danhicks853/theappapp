"""
Unit tests for OpenAI Adapter service.

Tests the wrapper around OpenAI API with token logging hooks.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage

from backend.services.openai_adapter import OpenAIAdapter


@pytest.fixture
def mock_token_logger():
    """Mock token logger for testing."""
    return Mock()


@pytest.fixture
def adapter(mock_token_logger):
    """Create OpenAI adapter with mock token logger."""
    return OpenAIAdapter(api_key="test-key", token_logger=mock_token_logger)


@pytest.fixture
def mock_chat_completion():
    """Create a mock ChatCompletion response."""
    return ChatCompletion(
        id="chatcmpl-test",
        model="gpt-4o-mini",
        object="chat.completion",
        created=1234567890,
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                message=ChatCompletionMessage(
                    content="Test response",
                    role="assistant"
                )
            )
        ],
        usage=CompletionUsage(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30
        )
    )


class TestOpenAIAdapterInitialization:
    """Test adapter initialization."""
    
    def test_adapter_initializes_with_api_key(self, mock_token_logger):
        """Test adapter initializes with API key."""
        adapter = OpenAIAdapter(api_key="test-key", token_logger=mock_token_logger)
        assert adapter.api_key == "test-key"
        assert adapter.token_logger == mock_token_logger
    
    def test_adapter_initializes_without_token_logger(self):
        """Test adapter can initialize without token logger."""
        adapter = OpenAIAdapter(api_key="test-key")
        assert adapter.api_key == "test-key"
        assert adapter.token_logger is None
    
    def test_adapter_creates_async_client(self, adapter):
        """Test adapter creates AsyncOpenAI client."""
        assert adapter.client is not None
        assert isinstance(adapter.client, AsyncOpenAI)


class TestChatCompletion:
    """Test chat completion functionality."""
    
    @pytest.mark.asyncio
    async def test_chat_completion_success(self, adapter, mock_chat_completion):
        """Test successful chat completion call."""
        with patch.object(adapter.client.chat.completions, 'create', new=AsyncMock(return_value=mock_chat_completion)):
            response = await adapter.chat_completion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello"}],
                temperature=0.7
            )
            
            assert response == mock_chat_completion
            assert response.usage.prompt_tokens == 10
            assert response.usage.completion_tokens == 20
    
    @pytest.mark.asyncio
    async def test_chat_completion_calls_token_logger(self, adapter, mock_chat_completion, mock_token_logger):
        """Test chat completion calls token logger with usage data."""
        with patch.object(adapter.client.chat.completions, 'create', new=AsyncMock(return_value=mock_chat_completion)):
            await adapter.chat_completion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello"}],
                temperature=0.7
            )
            
            # Verify token logger was called
            mock_token_logger.log_tokens.assert_called_once()
            call_args = mock_token_logger.log_tokens.call_args[1]
            assert call_args['model'] == "gpt-4o-mini"
            assert call_args['prompt_tokens'] == 10
            assert call_args['completion_tokens'] == 20
    
    @pytest.mark.asyncio
    async def test_chat_completion_without_logger_succeeds(self, mock_chat_completion):
        """Test chat completion works without token logger."""
        adapter = OpenAIAdapter(api_key="test-key")  # No logger
        with patch.object(adapter.client.chat.completions, 'create', new=AsyncMock(return_value=mock_chat_completion)):
            response = await adapter.chat_completion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello"}],
                temperature=0.7
            )
            assert response == mock_chat_completion
    
    @pytest.mark.asyncio
    async def test_chat_completion_with_extra_kwargs(self, adapter, mock_chat_completion):
        """Test chat completion accepts extra kwargs."""
        with patch.object(adapter.client.chat.completions, 'create', new=AsyncMock(return_value=mock_chat_completion)) as mock_create:
            await adapter.chat_completion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello"}],
                temperature=0.7,
                max_tokens=100,
                top_p=0.9
            )
            
            # Verify extra kwargs were passed
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs['max_tokens'] == 100
            assert call_kwargs['top_p'] == 0.9


class TestErrorHandling:
    """Test error handling and retry logic."""
    
    @pytest.mark.asyncio
    async def test_retry_on_api_error(self, adapter):
        """Test adapter retries on API errors."""
        # Mock first two calls fail, third succeeds
        mock_create = AsyncMock(side_effect=[
            Exception("API Error"),
            Exception("API Error"),
            ChatCompletion(
                id="chatcmpl-test",
                model="gpt-4o-mini",
                object="chat.completion",
                created=1234567890,
                choices=[Choice(finish_reason="stop", index=0, message=ChatCompletionMessage(content="Success", role="assistant"))],
                usage=CompletionUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
            )
        ])
        
        with patch.object(adapter.client.chat.completions, 'create', mock_create):
            response = await adapter.chat_completion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello"}],
                temperature=0.7
            )
            
            # Should succeed after retries
            assert response.choices[0].message.content == "Success"
            # Should have been called 3 times (2 failures + 1 success)
            assert mock_create.call_count == 3
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, adapter):
        """Test adapter fails after max retries."""
        mock_create = AsyncMock(side_effect=Exception("API Error"))
        
        with patch.object(adapter.client.chat.completions, 'create', mock_create):
            with pytest.raises(Exception, match="API Error"):
                await adapter.chat_completion(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": "Hello"}],
                    temperature=0.7
                )
            
            # Should have tried 3 times (max retries)
            assert mock_create.call_count == 3


class TestEmbedText:
    """Test text embedding functionality."""
    
    @pytest.mark.asyncio
    async def test_embed_text_success(self, adapter):
        """Test successful text embedding."""
        mock_embedding = Mock()
        mock_embedding.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        
        with patch.object(adapter.client.embeddings, 'create', new=AsyncMock(return_value=mock_embedding)):
            result = await adapter.embed_text("Test text")
            
            assert result == [0.1, 0.2, 0.3]
    
    @pytest.mark.asyncio
    async def test_embed_text_with_custom_model(self, adapter):
        """Test embedding with custom model."""
        mock_embedding = Mock()
        mock_embedding.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        
        with patch.object(adapter.client.embeddings, 'create', new=AsyncMock(return_value=mock_embedding)) as mock_create:
            await adapter.embed_text("Test text", model="text-embedding-3-large")
            
            # Verify custom model was used
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs['model'] == "text-embedding-3-large"
    
    @pytest.mark.asyncio
    async def test_embed_text_default_model(self, adapter):
        """Test embedding uses default model."""
        mock_embedding = Mock()
        mock_embedding.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        
        with patch.object(adapter.client.embeddings, 'create', new=AsyncMock(return_value=mock_embedding)) as mock_create:
            await adapter.embed_text("Test text")
            
            # Verify default model was used
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs['model'] == "text-embedding-3-small"


class TestTokenLogging:
    """Test token logging functionality."""
    
    def test_log_tokens_with_logger(self, adapter, mock_chat_completion, mock_token_logger):
        """Test _log_tokens calls logger with correct data."""
        adapter._log_tokens(mock_chat_completion, {"agent_id": "test-agent"})
        
        mock_token_logger.log_tokens.assert_called_once_with(
            model=mock_chat_completion.model,
            prompt_tokens=10,
            completion_tokens=20,
            agent_id="test-agent"
        )
    
    def test_log_tokens_without_logger(self, mock_chat_completion):
        """Test _log_tokens handles missing logger gracefully."""
        adapter = OpenAIAdapter(api_key="test-key")  # No logger
        # Should not raise error
        adapter._log_tokens(mock_chat_completion, {})
