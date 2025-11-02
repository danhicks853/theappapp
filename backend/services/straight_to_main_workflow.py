"""
Straight-to-Main Branch Workflow Service

Workflow for committing directly to main branch with gate approval.
Bypasses feature branches for simple changes with immediate integration.

Reference: Phase 2.4 - GitHub Integration
"""
import logging
from typing import Optional, Any, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DirectCommit:
    """Direct commit to main details."""
    commit_sha: Optional[str]
    commit_url: Optional[str]
    message: str
    files_changed: List[str]
    gate_id: Optional[str]
    status: str  # pending_approval, approved, committed, rejected
    created_at: str


class StraightToMainWorkflow:
    """
    Service for straight-to-main branch workflow.
    
    Strategy:
    - Small changes go directly to main after gate approval
    - No feature branches for simple commits
    - Gate created for approval before commit
    - On approval, commit directly to main
    - On rejection, agent revises
    
    Use Cases:
    - Documentation updates
    - Small bug fixes
    - Configuration changes
    - Minor refactoring
    
    Example:
        workflow = StraightToMainWorkflow(
            github_specialist,
            gate_manager,
            commit_generator
        )
        
        # Request commit to main
        commit_req = await workflow.request_commit_to_main(
            project_id="proj-123",
            changes={"file": "README.md", "content": "..."},
            description="Update installation docs"
        )
        
        # Wait for approval
        approved = await workflow.wait_for_approval(commit_req.gate_id)
        
        # Commit if approved
        if approved:
            await workflow.execute_commit(commit_req, owner, repo)
    """
    
    def __init__(
        self,
        github_specialist: Optional[Any] = None,
        gate_manager: Optional[Any] = None,
        commit_generator: Optional[Any] = None
    ):
        """Initialize straight-to-main workflow."""
        self.github_specialist = github_specialist
        self.gate_manager = gate_manager
        self.commit_generator = commit_generator
        logger.info("StraightToMainWorkflow initialized")
    
    async def request_commit_to_main(
        self,
        project_id: str,
        changes: dict,
        description: str,
        auto_trigger_gate: bool = True
    ) -> DirectCommit:
        """
        Request commit directly to main branch.
        
        Args:
            project_id: Project identifier
            changes: Dict with 'files', 'diff', 'description'
            description: Change description
            auto_trigger_gate: Whether to create gate automatically
        
        Returns:
            DirectCommit pending approval
        """
        logger.info("Requesting commit to main")
        
        # Generate commit message
        commit_message = await self._generate_commit_message(changes, description)
        
        files_changed = changes.get("files", [])
        
        # Create gate for approval
        gate_id = None
        if auto_trigger_gate and self.gate_manager:
            gate_id = await self._create_commit_gate(
                project_id, commit_message, files_changed, changes.get("diff")
            )
        
        direct_commit = DirectCommit(
            commit_sha=None,
            commit_url=None,
            message=commit_message,
            files_changed=files_changed,
            gate_id=gate_id,
            status="pending_approval" if gate_id else "ready",
            created_at=datetime.utcnow().isoformat()
        )
        
        logger.info(f"Commit request created, Gate: {gate_id}")
        return direct_commit
    
    async def execute_commit(
        self,
        direct_commit: DirectCommit,
        owner: str,
        repo: str,
        branch: str = "main"
    ) -> bool:
        """
        Execute approved commit to main.
        
        Args:
            direct_commit: DirectCommit to execute
            owner: GitHub owner
            repo: GitHub repo
            branch: Branch to commit to (default: main)
        
        Returns:
            True if committed successfully
        """
        if direct_commit.status != "approved":
            logger.error(f"Commit not approved: {direct_commit.status}")
            return False
        
        if not self.github_specialist:
            logger.error("GitHub specialist not configured")
            return False
        
        try:
            # Execute commit via GitHub API
            # (This would use github_specialist with git operations)
            commit_result = await self._push_to_main(
                owner, repo, branch, direct_commit
            )
            
            direct_commit.commit_sha = commit_result.get("sha")
            direct_commit.commit_url = commit_result.get("html_url")
            direct_commit.status = "committed"
            
            logger.info(f"Committed to {branch}: {direct_commit.commit_sha}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to commit: {e}")
            return False
    
    async def wait_for_approval(
        self,
        gate_id: str,
        timeout_seconds: int = 1800
    ) -> bool:
        """
        Wait for gate approval (blocking).
        
        Args:
            gate_id: Gate identifier
            timeout_seconds: Max time to wait (default: 30 min)
        
        Returns:
            True if approved, False if rejected or timeout
        """
        if not self.gate_manager:
            logger.warning("Gate manager not configured")
            return False
        
        try:
            import asyncio
            start_time = datetime.utcnow()
            
            while True:
                gate = await self.gate_manager.get_gate(gate_id)
                
                if gate.status == "approved":
                    return True
                elif gate.status == "rejected":
                    return False
                
                # Check timeout
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > timeout_seconds:
                    logger.warning(f"Gate approval timeout: {gate_id}")
                    return False
                
                await asyncio.sleep(10)
        
        except Exception as e:
            logger.error(f"Error waiting for approval: {e}")
            return False
    
    async def batch_commit(
        self,
        project_id: str,
        commits: List[dict],
        owner: str,
        repo: str
    ) -> List[DirectCommit]:
        """
        Request multiple commits in batch.
        
        Args:
            project_id: Project identifier
            commits: List of commit dicts with 'changes', 'description'
            owner: GitHub owner
            repo: GitHub repo
        
        Returns:
            List of DirectCommit results
        """
        logger.info(f"Batch committing {len(commits)} changes")
        
        results = []
        for commit_data in commits:
            # Request commit
            direct_commit = await self.request_commit_to_main(
                project_id=project_id,
                changes=commit_data["changes"],
                description=commit_data["description"],
                auto_trigger_gate=False  # Single gate for batch
            )
            results.append(direct_commit)
        
        # Create single gate for all commits
        if self.gate_manager:
            gate_id = await self._create_batch_commit_gate(
                project_id, results
            )
            for commit in results:
                commit.gate_id = gate_id
        
        return results
    
    def is_suitable_for_main(
        self,
        changes: dict,
        threshold_lines: int = 50
    ) -> bool:
        """
        Determine if changes are suitable for straight-to-main.
        
        Criteria:
        - Small changes (< threshold lines)
        - Documentation files
        - Configuration files
        - No breaking changes
        
        Args:
            changes: Dict with 'diff', 'files'
            threshold_lines: Max lines changed
        
        Returns:
            True if suitable for straight-to-main
        """
        diff = changes.get("diff", "")
        files = changes.get("files", [])
        
        # Count lines changed
        lines_changed = diff.count("\n+") + diff.count("\n-")
        if lines_changed > threshold_lines:
            logger.info(f"Too many lines changed: {lines_changed} > {threshold_lines}")
            return False
        
        # Check file types
        safe_extensions = [".md", ".txt", ".json", ".yml", ".yaml", ".toml", ".ini"]
        if all(any(f.endswith(ext) for ext in safe_extensions) for f in files):
            logger.info("All files are documentation/config - suitable for main")
            return True
        
        # Check for breaking change keywords
        if any(keyword in diff.lower() for keyword in ["breaking", "deprecated", "removed"]):
            logger.info("Breaking changes detected - not suitable for main")
            return False
        
        # Default: suitable if small enough
        return lines_changed <= threshold_lines
    
    async def _generate_commit_message(
        self,
        changes: dict,
        description: str
    ) -> str:
        """Generate commit message."""
        if self.commit_generator:
            try:
                commit = await self.commit_generator.generate_from_diff(
                    diff=changes.get("diff", ""),
                    context=description,
                    files_changed=changes.get("files", [])
                )
                return commit.full_message
            except Exception as e:
                logger.error(f"Commit generator failed: {e}")
        
        # Fallback to description
        return description
    
    async def _create_commit_gate(
        self,
        project_id: str,
        commit_message: str,
        files_changed: List[str],
        diff: Optional[str]
    ) -> str:
        """Create gate for commit approval."""
        if not self.gate_manager:
            return "no-gate"
        
        try:
            gate = await self.gate_manager.create_gate(
                project_id=project_id,
                gate_type="direct_commit_approval",
                context={
                    "commit_message": commit_message,
                    "files_changed": files_changed,
                    "diff_preview": diff[:500] if diff else None,
                    "reason": f"Approve direct commit to main: {commit_message}"
                }
            )
            return gate.gate_id
        except Exception as e:
            logger.error(f"Failed to create gate: {e}")
            return "gate-creation-failed"
    
    async def _create_batch_commit_gate(
        self,
        project_id: str,
        commits: List[DirectCommit]
    ) -> str:
        """Create gate for batch commit approval."""
        if not self.gate_manager:
            return "no-gate"
        
        try:
            commit_summary = [c.message for c in commits]
            gate = await self.gate_manager.create_gate(
                project_id=project_id,
                gate_type="batch_commit_approval",
                context={
                    "commit_count": len(commits),
                    "commits": commit_summary,
                    "reason": f"Approve {len(commits)} direct commits to main"
                }
            )
            return gate.gate_id
        except Exception as e:
            logger.error(f"Failed to create gate: {e}")
            return "gate-creation-failed"
    
    async def _push_to_main(
        self,
        owner: str,
        repo: str,
        branch: str,
        direct_commit: DirectCommit
    ) -> dict:
        """Push commit to main (simplified)."""
        # This would use github_specialist with actual git operations
        # For now, return placeholder
        return {
            "sha": "abc123def456",
            "html_url": f"https://github.com/{owner}/{repo}/commit/abc123"
        }
