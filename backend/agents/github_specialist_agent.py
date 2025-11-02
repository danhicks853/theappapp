"""GitHub Specialist Agent - Version control and GitHub operations."""
import asyncio
import logging
from typing import Any, Dict, Optional
import httpx

from backend.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

GITHUB_SPECIALIST_SYSTEM_PROMPT = """You are a GitHub and Git expert.

Expertise:
- Git workflows (branching, merging, rebasing)
- GitHub Actions and CI/CD
- Pull request best practices
- Code review processes
- GitHub API integration
- Repository management
- Semantic versioning
- Release management

Responsibilities:
1. Design Git workflows
2. Create GitHub Actions workflows
3. Review and approve pull requests
4. Manage branches and releases
5. Set up repository automation
6. Troubleshoot Git issues

Output: Git commands, GitHub Actions YAML, PR reviews, workflow designs.
"""


class GitHubSpecialistAgent(BaseAgent):
    """
    GitHub Specialist Agent with retry logic and gate triggering.
    
    Operations:
    - create_repo: Create a new GitHub repository
    - delete_repo: Delete a GitHub repository
    - merge_pr: Merge a pull request
    
    Features:
    - Exponential backoff retry (3 attempts: 1s, 2s, 4s)
    - Automatic gate triggering on failure
    - Token-based authentication via GitHubCredentialManager
    """
    
    MAX_RETRIES = 3
    BASE_BACKOFF = 1  # seconds
    
    def __init__(self, agent_id: str, orchestrator: Any, llm_client: Any, user_id: int = 1, **kwargs):
        super().__init__(
            agent_id=agent_id,
            agent_type="github_specialist",
            orchestrator=orchestrator,
            llm_client=llm_client,
            system_prompt=GITHUB_SPECIALIST_SYSTEM_PROMPT,
            **kwargs
        )
        self.user_id = user_id  # For credential lookup
    
    async def _get_access_token(self, db_session: Any) -> Optional[str]:
        """Get GitHub access token from credential manager."""
        from backend.services.github_credential_manager import GitHubCredentialManager
        
        try:
            cred_manager = GitHubCredentialManager(db_session)
            token = await cred_manager.get_access_token(self.user_id)
            return token
        except Exception as e:
            logger.error(f"Failed to get GitHub access token: {e}", exc_info=True)
            return None
    
    async def _execute_with_retry(
        self,
        operation_name: str,
        operation_func,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute operation with exponential backoff retry.
        
        Args:
            operation_name: Name of operation for logging
            operation_func: Async function to execute
            *args, **kwargs: Arguments to pass to operation
        
        Returns:
            Dict with success, result, trigger_gate, reason
        """
        last_error = None
        
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.info(f"{operation_name} attempt {attempt}/{self.MAX_RETRIES}")
                
                result = await operation_func(*args, **kwargs)
                
                logger.info(f"{operation_name} succeeded on attempt {attempt}")
                return {
                    "success": True,
                    "result": result,
                    "trigger_gate": False,
                    "attempts": attempt
                }
            
            except httpx.HTTPStatusError as e:
                last_error = e
                status_code = e.response.status_code
                
                # Don't retry on client errors (except rate limiting)
                if 400 <= status_code < 500 and status_code != 429:
                    logger.error(f"{operation_name} failed with client error {status_code}: {e}")
                    return {
                        "success": False,
                        "error": str(e),
                        "status_code": status_code,
                        "trigger_gate": True,
                        "reason": f"GitHub API error {status_code}: {e.response.text[:200]}",
                        "attempts": attempt
                    }
                
                # Retry on server errors or rate limiting
                if attempt < self.MAX_RETRIES:
                    backoff = self.BASE_BACKOFF * (2 ** (attempt - 1))
                    logger.warning(
                        f"{operation_name} failed (attempt {attempt}), "
                        f"retrying in {backoff}s. Error: {e}"
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.error(f"{operation_name} failed after {self.MAX_RETRIES} attempts: {e}")
            
            except Exception as e:
                last_error = e
                logger.error(f"{operation_name} failed with unexpected error: {e}", exc_info=True)
                
                if attempt < self.MAX_RETRIES:
                    backoff = self.BASE_BACKOFF * (2 ** (attempt - 1))
                    logger.warning(f"Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
        
        # All retries failed - trigger gate
        return {
            "success": False,
            "error": str(last_error),
            "trigger_gate": True,
            "reason": f"{operation_name} failed after {self.MAX_RETRIES} attempts: {last_error}",
            "attempts": self.MAX_RETRIES
        }
    
    async def create_repo(
        self,
        name: str,
        description: Optional[str] = None,
        private: bool = False,
        auto_init: bool = True,
        db_session: Any = None
    ) -> Dict[str, Any]:
        """
        Create a new GitHub repository.
        
        Args:
            name: Repository name
            description: Repository description
            private: Whether repo should be private
            auto_init: Initialize with README
            db_session: Database session for credential lookup
        
        Returns:
            Result dict with success, repo data, or error with trigger_gate
        """
        async def _create():
            token = await self._get_access_token(db_session)
            if not token:
                raise ValueError("No GitHub access token found")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.github.com/user/repos",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    json={
                        "name": name,
                        "description": description,
                        "private": private,
                        "auto_init": auto_init
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        
        return await self._execute_with_retry("create_repo", _create)
    
    async def delete_repo(
        self,
        owner: str,
        repo: str,
        db_session: Any = None
    ) -> Dict[str, Any]:
        """
        Delete a GitHub repository.
        
        Args:
            owner: Repository owner username
            repo: Repository name
            db_session: Database session for credential lookup
        
        Returns:
            Result dict with success or error with trigger_gate
        """
        async def _delete():
            token = await self._get_access_token(db_session)
            if not token:
                raise ValueError("No GitHub access token found")
            
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"https://api.github.com/repos/{owner}/{repo}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                return {"deleted": True, "repo": f"{owner}/{repo}"}
        
        return await self._execute_with_retry("delete_repo", _delete)
    
    async def merge_pr(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        commit_title: Optional[str] = None,
        commit_message: Optional[str] = None,
        merge_method: str = "merge",
        db_session: Any = None
    ) -> Dict[str, Any]:
        """
        Merge a pull request.
        
        Args:
            owner: Repository owner username
            repo: Repository name
            pull_number: Pull request number
            commit_title: Optional merge commit title
            commit_message: Optional merge commit message
            merge_method: "merge", "squash", or "rebase"
            db_session: Database session for credential lookup
        
        Returns:
            Result dict with success, merge data, or error with trigger_gate
        """
        async def _merge():
            token = await self._get_access_token(db_session)
            if not token:
                raise ValueError("No GitHub access token found")
            
            payload = {"merge_method": merge_method}
            if commit_title:
                payload["commit_title"] = commit_title
            if commit_message:
                payload["commit_message"] = commit_message
            
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/merge",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        
        return await self._execute_with_retry("merge_pr", _merge)
