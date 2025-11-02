"""
GitHub PR Integration Service

Integrates CodeReviewer with GitHub pull requests.
Posts AI-generated code reviews as PR comments.

Reference: Phase 2.4 - GitHub Integration (deferred from Phase 3+)
"""
import logging
from typing import Optional, Any, List
from dataclasses import dataclass

from backend.services.code_reviewer import CodeReviewer
from backend.services.pr_description_generator import PRDescriptionGenerator
from backend.services.commit_message_generator import CommitMessageGenerator

logger = logging.getLogger(__name__)


@dataclass
class PRReviewResult:
    """Result of PR review."""
    pr_number: int
    review_posted: bool
    comment_url: Optional[str]
    issues_found: int
    quality_score: float


class GitHubPRIntegration:
    """
    Service for integrating code review with GitHub PRs.
    
    Features:
    - Automatically reviews PRs using CodeReviewer
    - Posts review comments to GitHub
    - Generates PR descriptions
    - Suggests commit message improvements
    
    Example:
        integration = GitHubPRIntegration(
            code_reviewer, 
            pr_generator, 
            commit_generator,
            github_client
        )
        
        # Review PR
        result = await integration.review_pr(
            owner="user",
            repo="project",
            pr_number=123
        )
    """
    
    def __init__(
        self,
        code_reviewer: CodeReviewer,
        pr_generator: PRDescriptionGenerator,
        commit_generator: CommitMessageGenerator,
        github_client: Optional[Any] = None
    ):
        """Initialize GitHub PR integration."""
        self.code_reviewer = code_reviewer
        self.pr_generator = pr_generator
        self.commit_generator = commit_generator
        self.github_client = github_client
        logger.info("GitHubPRIntegration initialized")
    
    async def review_pr(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        auto_post: bool = True
    ) -> PRReviewResult:
        """
        Review a pull request and optionally post comments.
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            auto_post: Whether to automatically post review
        
        Returns:
            PRReviewResult with review status
        """
        logger.info(f"Reviewing PR #{pr_number} in {owner}/{repo}")
        
        if not self.github_client:
            logger.warning("GitHub client not configured")
            return PRReviewResult(
                pr_number=pr_number,
                review_posted=False,
                comment_url=None,
                issues_found=0,
                quality_score=0.0
            )
        
        # Get PR details
        pr_data = await self._get_pr_details(owner, repo, pr_number)
        
        # Get diff
        diff = await self._get_pr_diff(owner, repo, pr_number)
        
        # Review code
        review_result = await self.code_reviewer.review_code(diff)
        
        # Post review if auto_post
        comment_url = None
        if auto_post and review_result.issues:
            comment = await self.code_reviewer.generate_pr_comment(review_result)
            comment_url = await self._post_review_comment(
                owner, repo, pr_number, comment
            )
        
        return PRReviewResult(
            pr_number=pr_number,
            review_posted=bool(comment_url),
            comment_url=comment_url,
            issues_found=len(review_result.issues),
            quality_score=review_result.overall_quality
        )
    
    async def generate_pr_description(
        self,
        owner: str,
        repo: str,
        pr_number: int
    ) -> str:
        """
        Generate PR description from changes.
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
        
        Returns:
            Generated PR description
        """
        logger.info(f"Generating description for PR #{pr_number}")
        
        if not self.github_client:
            return "PR description generation requires GitHub client"
        
        # Get PR details
        pr_data = await self._get_pr_details(owner, repo, pr_number)
        
        # Get commits
        commits = await self._get_pr_commits(owner, repo, pr_number)
        commit_messages = [c.get("commit", {}).get("message", "") for c in commits]
        
        # Get files
        files = await self._get_pr_files(owner, repo, pr_number)
        files_changed = [f.get("filename") for f in files]
        
        # Get diff
        diff = await self._get_pr_diff(owner, repo, pr_number)
        
        # Generate description
        pr_desc = await self.pr_generator.generate(
            diff=diff,
            commit_messages=commit_messages,
            files_changed=files_changed,
            branch_name=pr_data.get("head", {}).get("ref")
        )
        
        return pr_desc.full_description
    
    async def suggest_commit_message(
        self,
        diff: str,
        files_changed: Optional[List[str]] = None
    ) -> str:
        """
        Suggest commit message for changes.
        
        Args:
            diff: Git diff
            files_changed: List of changed files
        
        Returns:
            Suggested commit message
        """
        logger.info("Generating commit message suggestion")
        
        commit = await self.commit_generator.generate_from_diff(
            diff=diff,
            files_changed=files_changed
        )
        
        return commit.full_message
    
    async def _get_pr_details(
        self,
        owner: str,
        repo: str,
        pr_number: int
    ) -> dict:
        """Get PR details from GitHub API."""
        if not self.github_client:
            return {}
        
        try:
            response = await self.github_client.get(
                f"/repos/{owner}/{repo}/pulls/{pr_number}"
            )
            return response.json() if hasattr(response, 'json') else {}
        except Exception as e:
            logger.error(f"Failed to get PR details: {e}")
            return {}
    
    async def _get_pr_diff(
        self,
        owner: str,
        repo: str,
        pr_number: int
    ) -> str:
        """Get PR diff."""
        if not self.github_client:
            return ""
        
        try:
            response = await self.github_client.get(
                f"/repos/{owner}/{repo}/pulls/{pr_number}",
                headers={"Accept": "application/vnd.github.v3.diff"}
            )
            return response.text if hasattr(response, 'text') else ""
        except Exception as e:
            logger.error(f"Failed to get PR diff: {e}")
            return ""
    
    async def _get_pr_commits(
        self,
        owner: str,
        repo: str,
        pr_number: int
    ) -> List[dict]:
        """Get PR commits."""
        if not self.github_client:
            return []
        
        try:
            response = await self.github_client.get(
                f"/repos/{owner}/{repo}/pulls/{pr_number}/commits"
            )
            return response.json() if hasattr(response, 'json') else []
        except Exception as e:
            logger.error(f"Failed to get PR commits: {e}")
            return []
    
    async def _get_pr_files(
        self,
        owner: str,
        repo: str,
        pr_number: int
    ) -> List[dict]:
        """Get PR files."""
        if not self.github_client:
            return []
        
        try:
            response = await self.github_client.get(
                f"/repos/{owner}/{repo}/pulls/{pr_number}/files"
            )
            return response.json() if hasattr(response, 'json') else []
        except Exception as e:
            logger.error(f"Failed to get PR files: {e}")
            return []
    
    async def _post_review_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        comment: str
    ) -> Optional[str]:
        """Post review comment to PR."""
        if not self.github_client:
            return None
        
        try:
            response = await self.github_client.post(
                f"/repos/{owner}/{repo}/issues/{pr_number}/comments",
                json={"body": comment}
            )
            result = response.json() if hasattr(response, 'json') else {}
            return result.get("html_url")
        except Exception as e:
            logger.error(f"Failed to post review comment: {e}")
            return None
