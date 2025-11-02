"""
GitHub OAuth Routes

Handles GitHub OAuth flow for connecting user accounts.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import httpx
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/github", tags=["github"])


def get_db():
    """Get database session (placeholder - implement based on your DB setup)."""
    # TODO: Implement your database session dependency
    pass


@router.get("/connect")
async def initiate_oauth():
    """
    Initiate GitHub OAuth flow.
    
    Redirects user to GitHub authorization page.
    """
    client_id = os.getenv('GITHUB_CLIENT_ID')
    redirect_uri = os.getenv('GITHUB_REDIRECT_URI', 'http://localhost:8000/api/v1/github/callback')
    
    if not client_id:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")
    
    # GitHub OAuth authorization URL
    github_auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=repo,user,delete_repo"
    )
    
    return RedirectResponse(url=github_auth_url)


@router.get("/callback")
async def oauth_callback(
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Handle GitHub OAuth callback.
    
    Exchanges authorization code for access token and stores credentials.
    """
    # Handle OAuth errors
    if error:
        logger.error(f"GitHub OAuth error: {error}")
        return RedirectResponse(url=f"/settings/github?error={error}")
    
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    
    # Get OAuth credentials
    client_id = os.getenv('GITHUB_CLIENT_ID')
    client_secret = os.getenv('GITHUB_CLIENT_SECRET')
    redirect_uri = os.getenv('GITHUB_REDIRECT_URI', 'http://localhost:8000/api/v1/github/callback')
    
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")
    
    try:
        # Exchange code for access token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                'https://github.com/login/oauth/access_token',
                data={
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'code': code,
                    'redirect_uri': redirect_uri
                },
                headers={'Accept': 'application/json'}
            )
            
            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=token_response.status_code,
                    detail="Failed to exchange code for token"
                )
            
            token_data = token_response.json()
            
            if 'error' in token_data:
                raise HTTPException(status_code=400, detail=token_data.get('error_description', 'OAuth error'))
            
            access_token = token_data.get('access_token')
            refresh_token = token_data.get('refresh_token')
            expires_in = token_data.get('expires_in')
            
            if not access_token:
                raise HTTPException(status_code=400, detail="No access token in response")
            
            # Get GitHub user info
            user_response = await client.get(
                'https://api.github.com/user',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/vnd.github.v3+json'
                }
            )
            
            if user_response.status_code != 200:
                raise HTTPException(status_code=user_response.status_code, detail="Failed to get user info")
            
            user_data = user_response.json()
            github_username = user_data.get('login')
            github_user_id = user_data.get('id')
            
            # Store credentials
            # TODO: Get actual user_id from session/auth
            user_id = 1  # Placeholder
            
            from backend.services.github_credential_manager import GitHubCredentialManager
            
            cred_manager = GitHubCredentialManager(db)
            success = cred_manager.store_tokens(
                user_id=user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=expires_in,
                github_username=github_username,
                github_user_id=github_user_id
            )
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to store credentials")
            
            logger.info(f"GitHub OAuth successful for user_id={user_id}, github_username={github_username}")
            
            # Redirect back to frontend settings page
            return RedirectResponse(url="/settings/github?success=true")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/credentials")
async def disconnect_github(db: Session = Depends(get_db)):
    """
    Disconnect GitHub account (delete credentials).
    """
    try:
        # TODO: Get actual user_id from session/auth
        user_id = 1  # Placeholder
        
        from backend.services.github_credential_manager import GitHubCredentialManager
        
        cred_manager = GitHubCredentialManager(db)
        success = cred_manager.delete_credentials(user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="No credentials found")
        
        return {"success": True, "message": "GitHub account disconnected"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disconnect GitHub: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_connection_status(db: Session = Depends(get_db)):
    """
    Get GitHub connection status for current user.
    """
    try:
        # TODO: Get actual user_id from session/auth
        user_id = 1  # Placeholder
        
        from backend.services.github_credential_manager import GitHubCredentialManager
        
        cred_manager = GitHubCredentialManager(db)
        info = cred_manager.get_credential_info(user_id)
        
        if not info:
            return {
                "connected": False,
                "github_username": None,
                "github_user_id": None
            }
        
        return {
            "connected": True,
            "github_username": info['github_username'],
            "github_user_id": info['github_user_id'],
            "token_expiry": info['token_expiry'],
            "has_refresh_token": info['has_refresh_token']
        }
    
    except Exception as e:
        logger.error(f"Failed to get GitHub status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
