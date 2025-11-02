"""
Unit tests for API Key Service.

Tests encryption, decryption, caching, and validation of API keys.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from cryptography.fernet import Fernet

from backend.services.api_key_service import APIKeyService


@pytest.fixture
def encryption_key():
    """Generate test encryption key."""
    return Fernet.generate_key().decode()


@pytest.fixture
def service(encryption_key):
    """Create APIKeyService with test encryption key."""
    with patch.dict('os.environ', {'ENCRYPTION_KEY': encryption_key}):
        return APIKeyService()


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock()


class TestInitialization:
    """Test service initialization."""
    
    def test_service_initializes_with_encryption_key(self, encryption_key):
        """Test service initializes with encryption key from environment."""
        with patch.dict('os.environ', {'ENCRYPTION_KEY': encryption_key}):
            service = APIKeyService()
            assert service.cipher is not None
    
    def test_service_fails_without_encryption_key(self):
        """Test service raises error if ENCRYPTION_KEY not set."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="ENCRYPTION_KEY environment variable not set"):
                APIKeyService()


class TestSetKey:
    """Test setting API keys."""
    
    @pytest.mark.asyncio
    async def test_set_key_encrypts_and_stores(self, service, mock_db):
        """Test set_key encrypts API key and stores in database."""
        api_key = "sk-test-key-123"
        
        with patch.object(service, 'test_key', new=AsyncMock(return_value=True)):
            result = await service.set_key("openai", api_key, mock_db)
            
            assert result is True
            # Verify database insert/update was called
            mock_db.execute.assert_called_once()
            # Verify stored value is encrypted (not plaintext)
            call_args = str(mock_db.execute.call_args)
            assert api_key not in call_args
    
    @pytest.mark.asyncio
    async def test_set_key_validates_before_storing(self, service, mock_db):
        """Test set_key validates key before storing."""
        api_key = "sk-test-key-123"
        
        with patch.object(service, 'test_key', new=AsyncMock(return_value=True)):
            result = await service.set_key("openai", api_key, mock_db)
            assert result is True
            service.test_key.assert_called_once_with("openai", api_key)
    
    @pytest.mark.asyncio
    async def test_set_key_rejects_invalid_key(self, service, mock_db):
        """Test set_key rejects invalid API key."""
        api_key = "invalid-key"
        
        with patch.object(service, 'test_key', new=AsyncMock(return_value=False)):
            result = await service.set_key("openai", api_key, mock_db)
            assert result is False
            # Should not call database
            mock_db.execute.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_set_key_updates_existing(self, service, mock_db):
        """Test set_key updates existing key (upsert)."""
        api_key = "sk-new-key-456"
        
        with patch.object(service, 'test_key', new=AsyncMock(return_value=True)):
            await service.set_key("openai", api_key, mock_db)
            
            # Should have called execute (for upsert)
            assert mock_db.execute.called


class TestGetKey:
    """Test retrieving API keys."""
    
    @pytest.mark.asyncio
    async def test_get_key_decrypts_from_database(self, service, mock_db):
        """Test get_key retrieves and decrypts key from database."""
        api_key = "sk-test-key-123"
        encrypted = service.cipher.encrypt(api_key.encode()).decode()
        
        # Mock database response
        mock_result = Mock()
        mock_result.first.return_value = (encrypted,)
        mock_db.execute.return_value = mock_result
        
        result = await service.get_key("openai", mock_db)
        
        assert result == api_key
    
    @pytest.mark.asyncio
    async def test_get_key_returns_none_if_not_found(self, service, mock_db):
        """Test get_key returns None if key not in database."""
        mock_result = Mock()
        mock_result.first.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await service.get_key("nonexistent", mock_db)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_key_uses_cache(self, service, mock_db):
        """Test get_key uses cache for repeated requests."""
        api_key = "sk-test-key-123"
        encrypted = service.cipher.encrypt(api_key.encode()).decode()
        
        mock_result = Mock()
        mock_result.first.return_value = (encrypted,)
        mock_db.execute.return_value = mock_result
        
        # First call - should hit database
        result1 = await service.get_key("openai", mock_db)
        call_count_1 = mock_db.execute.call_count
        
        # Second call - should use cache
        result2 = await service.get_key("openai", mock_db)
        call_count_2 = mock_db.execute.call_count
        
        assert result1 == result2 == api_key
        # Cache should prevent second database call
        assert call_count_2 == call_count_1


class TestTestKey:
    """Test API key validation."""
    
    @pytest.mark.asyncio
    async def test_test_key_openai_valid(self, service):
        """Test validation of valid OpenAI key."""
        with patch('backend.services.api_key_service.AsyncOpenAI') as MockClient:
            mock_client = MockClient.return_value
            mock_client.models.list = AsyncMock(return_value=Mock())
            
            result = await service.test_key("openai", "sk-valid-key")
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_test_key_openai_invalid(self, service):
        """Test validation rejects invalid OpenAI key."""
        with patch('openai.AsyncOpenAI') as MockClient:
            mock_client = MockClient.return_value
            mock_client.models.list = AsyncMock(side_effect=Exception("Invalid API key"))
            
            result = await service.test_key("openai", "sk-invalid-key")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_test_key_unknown_service(self, service):
        """Test validation returns False for unknown service."""
        result = await service.test_key("unknown_service", "some-key")
        assert result is False


class TestRotateKey:
    """Test key rotation."""
    
    @pytest.mark.asyncio
    async def test_rotate_key_replaces_existing(self, service, mock_db):
        """Test rotate_key replaces existing key."""
        new_key = "sk-new-key-789"
        
        with patch.object(service, 'set_key', new=AsyncMock(return_value=True)) as mock_set:
            result = await service.rotate_key("openai", new_key, mock_db)
            
            assert result is True
            mock_set.assert_called_once_with("openai", new_key, mock_db)
    
    @pytest.mark.asyncio
    async def test_rotate_key_clears_cache(self, service, mock_db):
        """Test rotate_key clears cached old key."""
        # Add key to cache
        service._cache["openai"] = ("old-key", 0)
        
        with patch.object(service, 'set_key', new=AsyncMock(return_value=True)):
            await service.rotate_key("openai", "new-key", mock_db)
            
            # Cache should be cleared for this service
            assert "openai" not in service._cache


class TestEncryptionDecryption:
    """Test encryption and decryption."""
    
    def test_encrypt_decrypt_roundtrip(self, service):
        """Test encryption and decryption are inverse operations."""
        plaintext = "sk-test-key-secret-123"
        
        encrypted = service._encrypt(plaintext)
        decrypted = service._decrypt(encrypted)
        
        assert decrypted == plaintext
        assert encrypted != plaintext
    
    def test_encrypted_value_is_different_each_time(self, service):
        """Test same plaintext produces different ciphertext (IV randomization)."""
        plaintext = "sk-test-key-123"
        
        encrypted1 = service._encrypt(plaintext)
        encrypted2 = service._encrypt(plaintext)
        
        # Different ciphertexts due to IV
        assert encrypted1 != encrypted2
        # But both decrypt to same plaintext
        assert service._decrypt(encrypted1) == plaintext
        assert service._decrypt(encrypted2) == plaintext
