"""
GitHub Credential Manager

Manages encrypted storage and retrieval of GitHub OAuth tokens using Fernet symmetric encryption.
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session
from sqlalchemy import select

logger = logging.getLogger(__name__)


class GitHubCredentialManager:
    """
    Manages GitHub OAuth credentials with Fernet encryption.
    
    Features:
    - Encrypts tokens at rest using Fernet symmetric encryption
    - Automatic token refresh when expired
    - Secure key management via environment variable
    - One credential per user
    """
    
    def __init__(self, db_session: Session, encryption_key: Optional[str] = None):
        """
        Initialize credential manager.
        
        Args:
            db_session: SQLAlchemy database session
            encryption_key: Base64-encoded Fernet key (defaults to GITHUB_ENCRYPTION_KEY env var)
        
        Raises:
            ValueError: If no encryption key provided
        """
        self.db_session = db_session
        
        # Get encryption key
        key = encryption_key or os.getenv('GITHUB_ENCRYPTION_KEY')
        if not key:
            raise ValueError(
                "GitHub encryption key not found. Set GITHUB_ENCRYPTION_KEY environment variable. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        
        try:
            self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            raise ValueError(f"Invalid encryption key: {e}")
        
        logger.info("GitHubCredentialManager initialized")
    
    def store_tokens(
        self,
        user_id: int,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: Optional[int] = None,
        github_username: Optional[str] = None,
        github_user_id: Optional[int] = None
    ) -> bool:
        """
        Store encrypted GitHub tokens for a user.
        
        Args:
            user_id: User ID
            access_token: GitHub access token (plain text)
            refresh_token: GitHub refresh token (plain text), if available
            expires_in: Token expiry in seconds
            github_username: GitHub username
            github_user_id: GitHub user ID
        
        Returns:
            True if stored successfully
        """
        from backend.models.database import GitHubCredential
        
        try:
            # Encrypt tokens
            access_token_encrypted = self.cipher.encrypt(access_token.encode())
            refresh_token_encrypted = None
            if refresh_token:
                refresh_token_encrypted = self.cipher.encrypt(refresh_token.encode())
            
            # Calculate expiry
            token_expiry = None
            if expires_in:
                token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
            
            # Check if credential exists
            stmt = select(GitHubCredential).where(GitHubCredential.user_id == user_id)
            existing = self.db_session.execute(stmt).scalar_one_or_none()
            
            if existing:
                # Update existing
                existing.access_token_encrypted = access_token_encrypted
                existing.refresh_token_encrypted = refresh_token_encrypted
                existing.token_expiry = token_expiry
                existing.github_username = github_username
                existing.github_user_id = github_user_id
                existing.updated_at = datetime.utcnow()
                logger.info(f"Updated GitHub credentials for user_id={user_id}")
            else:
                # Create new
                credential = GitHubCredential(
                    user_id=user_id,
                    access_token_encrypted=access_token_encrypted,
                    refresh_token_encrypted=refresh_token_encrypted,
                    token_expiry=token_expiry,
                    github_username=github_username,
                    github_user_id=github_user_id
                )
                self.db_session.add(credential)
                logger.info(f"Stored new GitHub credentials for user_id={user_id}")
            
            self.db_session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to store GitHub credentials: {e}", exc_info=True)
            self.db_session.rollback()
            return False
    
    async def get_access_token(self, user_id: int) -> Optional[str]:
        """
        Get decrypted access token for a user.
        
        Automatically refreshes if token is expired.
        
        Args:
            user_id: User ID
        
        Returns:
            Decrypted access token, or None if not found/expired
        """
        from backend.models.database import GitHubCredential
        
        try:
            # Get credential
            stmt = select(GitHubCredential).where(GitHubCredential.user_id == user_id)
            credential = self.db_session.execute(stmt).scalar_one_or_none()
            
            if not credential:
                logger.warning(f"No GitHub credentials found for user_id={user_id}")
                return None
            
            # Check if expired
            if credential.token_expiry and datetime.utcnow() >= credential.token_expiry:
                logger.info(f"Token expired for user_id={user_id}, attempting refresh")
                # Attempt refresh
                if await self.refresh_access_token(user_id):
                    # Re-fetch credential
                    credential = self.db_session.execute(stmt).scalar_one_or_none()
                else:
                    logger.error(f"Token refresh failed for user_id={user_id}")
                    return None
            
            # Decrypt and return
            access_token = self.cipher.decrypt(credential.access_token_encrypted).decode()
            return access_token
            
        except Exception as e:
            logger.error(f"Failed to get access token: {e}", exc_info=True)
            return None
    
    async def refresh_access_token(self, user_id: int) -> bool:
        """
        Refresh expired access token using refresh token.
        
        Args:
            user_id: User ID
        
        Returns:
            True if refresh successful
        """
        from backend.models.database import GitHubCredential
        import httpx
        
        try:
            # Get credential
            stmt = select(GitHubCredential).where(GitHubCredential.user_id == user_id)
            credential = self.db_session.execute(stmt).scalar_one_or_none()
            
            if not credential or not credential.refresh_token_encrypted:
                logger.error(f"No refresh token found for user_id={user_id}")
                return False
            
            # Decrypt refresh token
            refresh_token = self.cipher.decrypt(credential.refresh_token_encrypted).decode()
            
            # Get GitHub OAuth credentials from environment
            client_id = os.getenv('GITHUB_CLIENT_ID')
            client_secret = os.getenv('GITHUB_CLIENT_SECRET')
            
            if not client_id or not client_secret:
                logger.error("GitHub OAuth credentials not found in environment")
                return False
            
            # Call GitHub OAuth refresh endpoint
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    'https://github.com/login/oauth/access_token',
                    data={
                        'client_id': client_id,
                        'client_secret': client_secret,
                        'grant_type': 'refresh_token',
                        'refresh_token': refresh_token
                    },
                    headers={'Accept': 'application/json'}
                )
                
                if response.status_code != 200:
                    logger.error(f"GitHub token refresh failed: {response.status_code}")
                    return False
                
                data = response.json()
                
                if 'access_token' not in data:
                    logger.error(f"No access token in refresh response: {data}")
                    return False
                
                # Store new tokens
                return self.store_tokens(
                    user_id=user_id,
                    access_token=data['access_token'],
                    refresh_token=data.get('refresh_token', refresh_token),  # Use old if not provided
                    expires_in=data.get('expires_in'),
                    github_username=credential.github_username,
                    github_user_id=credential.github_user_id
                )
        
        except Exception as e:
            logger.error(f"Token refresh failed: {e}", exc_info=True)
            return False
    
    def delete_credentials(self, user_id: int) -> bool:
        """
        Delete GitHub credentials for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            True if deleted successfully
        """
        from backend.models.database import GitHubCredential
        
        try:
            stmt = select(GitHubCredential).where(GitHubCredential.user_id == user_id)
            credential = self.db_session.execute(stmt).scalar_one_or_none()
            
            if credential:
                self.db_session.delete(credential)
                self.db_session.commit()
                logger.info(f"Deleted GitHub credentials for user_id={user_id}")
                return True
            else:
                logger.warning(f"No credentials found to delete for user_id={user_id}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to delete credentials: {e}", exc_info=True)
            self.db_session.rollback()
            return False
    
    def get_credential_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get non-sensitive credential information.
        
        Args:
            user_id: User ID
        
        Returns:
            Dict with github_username, github_user_id, token_expiry, etc. (no tokens)
        """
        from backend.models.database import GitHubCredential
        
        try:
            stmt = select(GitHubCredential).where(GitHubCredential.user_id == user_id)
            credential = self.db_session.execute(stmt).scalar_one_or_none()
            
            if not credential:
                return None
            
            return {
                'user_id': credential.user_id,
                'github_username': credential.github_username,
                'github_user_id': credential.github_user_id,
                'token_expiry': credential.token_expiry.isoformat() if credential.token_expiry else None,
                'has_refresh_token': credential.refresh_token_encrypted is not None,
                'created_at': credential.created_at.isoformat() if credential.created_at else None,
                'updated_at': credential.updated_at.isoformat() if credential.updated_at else None
            }
        
        except Exception as e:
            logger.error(f"Failed to get credential info: {e}", exc_info=True)
            return None


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.
    
    Returns:
        Base64-encoded Fernet key as string
    """
    return Fernet.generate_key().decode()


# Example usage:
# key = generate_encryption_key()
# print(f"Set this as GITHUB_ENCRYPTION_KEY: {key}")
