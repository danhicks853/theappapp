"""
API Key Service

Manages encrypted storage and retrieval of API keys for external services.
Uses Fernet (symmetric encryption) with ENCRYPTION_KEY from environment.

Reference: Section 1.2.1 - API Key Management Service
"""
import os
import logging
import time
from typing import Optional, Dict, Tuple

from cryptography.fernet import Fernet
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class APIKeyService:
    """
    Service for managing encrypted API keys.
    
    Features:
    - Fernet encryption for all stored keys
    - In-memory caching (5 minutes)
    - Key validation before storage
    - Support for multiple services (OpenAI, etc.)
    
    Example:
        key_service = APIKeyService()
        await key_service.set_key("openai", "sk-proj-...", db)
        api_key = await key_service.get_key("openai", db)
    """
    
    CACHE_TTL_SECONDS = 300  # 5 minutes
    
    def __init__(self):
        """Initialize API key service with encryption."""
        encryption_key = os.getenv("ENCRYPTION_KEY")
        if not encryption_key:
            raise ValueError("ENCRYPTION_KEY environment variable not set")
        
        self.cipher = Fernet(encryption_key.encode())
        self._cache: Dict[str, Tuple[str, float]] = {}  # {service: (key, timestamp)}
        logger.info("API key service initialized")
    
    async def get_key(self, service: str, db: AsyncSession) -> Optional[str]:
        """
        Get decrypted API key for service.
        
        Args:
            service: Service name (e.g., "openai")
            db: Database session
        
        Returns:
            Decrypted API key, or None if not found
        """
        # Check cache first
        if service in self._cache:
            key, timestamp = self._cache[service]
            if time.time() - timestamp < self.CACHE_TTL_SECONDS:
                logger.debug(f"Cache hit for service: {service}")
                return key
            else:
                # Cache expired
                logger.debug(f"Cache expired for service: {service}")
                del self._cache[service]
        
        # Query database
        logger.debug(f"Fetching key for service: {service}")
        query = text("SELECT api_key_encrypted FROM api_keys WHERE service = :service AND is_active = true")
        result = await db.execute(query, {"service": service})
        row = result.first()
        
        if not row:
            logger.warning(f"No active key found for service: {service}")
            return None
        
        # Decrypt
        encrypted_key = row[0]
        decrypted_key = self._decrypt(encrypted_key)
        
        # Cache for next time
        self._cache[service] = (decrypted_key, time.time())
        logger.info(f"Key retrieved and cached for service: {service}")
        
        return decrypted_key
    
    async def set_key(self, service: str, api_key: str, db: AsyncSession) -> bool:
        """
        Encrypt and store API key after validation.
        
        Args:
            service: Service name (e.g., "openai")
            api_key: Plaintext API key
            db: Database session
        
        Returns:
            True if key was stored, False if validation failed
        """
        logger.info(f"Setting key for service: {service}")
        
        # Validate key before storing
        if not await self.test_key(service, api_key):
            logger.error(f"Key validation failed for service: {service}")
            return False
        
        # Encrypt
        encrypted_key = self._encrypt(api_key)
        
        # Upsert to database (insert or update)
        query = text("""
            INSERT INTO api_keys (service, api_key_encrypted, is_active, created_at, updated_at)
            VALUES (:service, :encrypted, true, NOW(), NOW())
            ON CONFLICT (service)
            DO UPDATE SET
                api_key_encrypted = :encrypted,
                updated_at = NOW(),
                is_active = true
        """)
        
        await db.execute(query, {"service": service, "encrypted": encrypted_key})
        await db.commit()
        
        # Update cache
        self._cache[service] = (api_key, time.time())
        logger.info(f"Key stored successfully for service: {service}")
        
        return True
    
    async def test_key(self, service: str, api_key: str) -> bool:
        """
        Test API key validity before storing.
        
        Args:
            service: Service name
            api_key: API key to test
        
        Returns:
            True if key is valid, False otherwise
        """
        logger.debug(f"Testing key for service: {service}")
        
        try:
            if service == "openai":
                # Test OpenAI key by listing models
                client = AsyncOpenAI(api_key=api_key)
                await client.models.list()
                logger.info("OpenAI key validation successful")
                return True
            else:
                logger.warning(f"Unknown service for validation: {service}")
                return False
        
        except Exception as e:
            logger.error(f"Key validation failed: {e}")
            return False
    
    async def rotate_key(self, service: str, new_key: str, db: AsyncSession) -> bool:
        """
        Rotate API key (replace existing key).
        
        Args:
            service: Service name
            new_key: New API key
            db: Database session
        
        Returns:
            True if rotation successful
        """
        logger.info(f"Rotating key for service: {service}")
        
        # Clear cache for this service
        if service in self._cache:
            del self._cache[service]
        
        # Set new key (validates and stores)
        return await self.set_key(service, new_key, db)
    
    def _encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext using Fernet.
        
        Args:
            plaintext: String to encrypt
        
        Returns:
            Base64-encoded ciphertext
        """
        return self.cipher.encrypt(plaintext.encode()).decode()
    
    def _decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext using Fernet.
        
        Args:
            ciphertext: Base64-encoded ciphertext
        
        Returns:
            Decrypted plaintext string
        """
        return self.cipher.decrypt(ciphertext.encode()).decode()
