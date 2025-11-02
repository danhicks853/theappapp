"""
Milestone-based PR Workflow Service

Integrates GitHub PRs with milestone/deliverable completion via gates.
Creates PRs when deliverables are complete, triggers gates for approval.

Reference: Phase 2.4 - GitHub Integration
"""
import logging
from typing import Optional, Any, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MilestonePR:
    """Milestone PR details."""
    milestone_id: str
    deliverable_ids: List[str]
    pr_number: Optional[int]
    pr_url: Optional[str]
    branch_name: str
    status: str  # draft, open, approved, merged, closed
    gate_id: Optional[str]
    created_at: str


class MilestonePRWorkflow:
    """
    Service for milestone-based PR workflow with gate integration.
    
    Process:
    1. Agent completes deliverable(s) for a milestone
    2. Service creates feature branch with changes
    3. Service creates PR to main
    4. Gate triggered for human review
    5. On approval, PR merged; on rejection, agent revises
    
    Example:
        workflow = MilestonePRWorkflow(
            github_specialist,
            gate_manager,
            pr_generator
        )
        
        # Create PR for completed milestone
        milestone_pr = await workflow.create_milestone_pr(
            project_id="proj-123",
            milestone_id="milestone-1",
            deliverable_ids=["del-1", "del-2"],
            changes={"files": [...], "diff": "..."}
        )
        
        # Wait for gate approval
        approved = await workflow.wait_for_approval(milestone_pr.gate_id)
        
        # Merge if approved
        if approved:
            await workflow.merge_milestone_pr(milestone_pr)
    """
    
    def __init__(
        self,
        github_specialist: Optional[Any] = None,
        gate_manager: Optional[Any] = None,
        pr_generator: Optional[Any] = None,
        deliverable_tracker: Optional[Any] = None
    ):
        """Initialize milestone PR workflow."""
        self.github_specialist = github_specialist
        self.gate_manager = gate_manager
        self.pr_generator = pr_generator
        self.deliverable_tracker = deliverable_tracker
        logger.info("MilestonePRWorkflow initialized")
    
    async def create_milestone_pr(
        self,
        project_id: str,
        milestone_id: str,
        deliverable_ids: List[str],
        changes: dict,
        owner: str,
        repo: str,
        auto_trigger_gate: bool = True
    ) -> MilestonePR:
        """
        Create PR for completed milestone deliverables.
        
        Args:
            project_id: Project identifier
            milestone_id: Milestone identifier
            deliverable_ids: List of completed deliverable IDs
            changes: Dict with 'files', 'diff', 'commit_messages'
            owner: GitHub owner
            repo: GitHub repo
            auto_trigger_gate: Whether to automatically create gate
        
        Returns:
            MilestonePR with PR details and gate ID
        """
        logger.info(f"Creating milestone PR for {milestone_id}")
        
        # Generate branch name
        branch_name = f"milestone/{milestone_id}"
        
        # Generate PR description
        pr_description = await self._generate_milestone_pr_description(
            milestone_id, deliverable_ids, changes
        )
        
        # Create PR via GitHub Specialist
        pr_result = None
        pr_number = None
        pr_url = None
        
        if self.github_specialist:
            try:
                # Create branch and PR (simplified - would use git operations)
                pr_result = await self._create_github_pr(
                    owner, repo, branch_name, pr_description
                )
                pr_number = pr_result.get("number")
                pr_url = pr_result.get("html_url")
            except Exception as e:
                logger.error(f"Failed to create PR: {e}")
        
        # Create gate for review
        gate_id = None
        if auto_trigger_gate and self.gate_manager:
            gate_id = await self._create_review_gate(
                project_id, milestone_id, deliverable_ids, pr_url
            )
        
        milestone_pr = MilestonePR(
            milestone_id=milestone_id,
            deliverable_ids=deliverable_ids,
            pr_number=pr_number,
            pr_url=pr_url,
            branch_name=branch_name,
            status="open" if pr_number else "draft",
            gate_id=gate_id,
            created_at=datetime.utcnow().isoformat()
        )
        
        logger.info(f"Milestone PR created: {pr_url}, Gate: {gate_id}")
        return milestone_pr
    
    async def wait_for_approval(
        self,
        gate_id: str,
        timeout_seconds: int = 3600
    ) -> bool:
        """
        Wait for gate approval (blocking).
        
        Args:
            gate_id: Gate identifier
            timeout_seconds: Max time to wait
        
        Returns:
            True if approved, False if rejected or timeout
        """
        if not self.gate_manager:
            logger.warning("Gate manager not configured")
            return False
        
        try:
            # Poll gate status (simplified - would use async waiting)
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
                
                # Wait before polling again
                await asyncio.sleep(10)
        
        except Exception as e:
            logger.error(f"Error waiting for approval: {e}")
            return False
    
    async def merge_milestone_pr(
        self,
        milestone_pr: MilestonePR,
        owner: str,
        repo: str
    ) -> bool:
        """
        Merge approved milestone PR.
        
        Args:
            milestone_pr: MilestonePR to merge
            owner: GitHub owner
            repo: GitHub repo
        
        Returns:
            True if merged successfully
        """
        if not milestone_pr.pr_number:
            logger.error("No PR number to merge")
            return False
        
        if not self.github_specialist:
            logger.error("GitHub specialist not configured")
            return False
        
        try:
            # Merge PR via GitHub Specialist
            await self.github_specialist.merge_pr(
                owner=owner,
                repo=repo,
                pr_number=milestone_pr.pr_number
            )
            
            # Update deliverable status
            if self.deliverable_tracker:
                for deliverable_id in milestone_pr.deliverable_ids:
                    await self.deliverable_tracker.mark_merged(deliverable_id)
            
            logger.info(f"Merged milestone PR #{milestone_pr.pr_number}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to merge PR: {e}")
            return False
    
    async def handle_rejection(
        self,
        milestone_pr: MilestonePR,
        feedback: str,
        project_id: str
    ) -> dict:
        """
        Handle PR rejection - create revision task for agent.
        
        Args:
            milestone_pr: Rejected MilestonePR
            feedback: Human feedback
            project_id: Project identifier
        
        Returns:
            Dict with revision task details
        """
        logger.info(f"Handling rejection for milestone {milestone_pr.milestone_id}")
        
        return {
            "action": "revise",
            "milestone_id": milestone_pr.milestone_id,
            "deliverable_ids": milestone_pr.deliverable_ids,
            "feedback": feedback,
            "pr_url": milestone_pr.pr_url,
            "instructions": f"Revise deliverables based on feedback: {feedback}"
        }
    
    async def _generate_milestone_pr_description(
        self,
        milestone_id: str,
        deliverable_ids: List[str],
        changes: dict
    ) -> str:
        """Generate PR description for milestone."""
        if self.pr_generator:
            # Use PR generator if available
            try:
                pr_desc = await self.pr_generator.generate(
                    diff=changes.get("diff", ""),
                    commit_messages=changes.get("commit_messages", []),
                    files_changed=changes.get("files", [])
                )
                return pr_desc.full_description
            except Exception as e:
                logger.error(f"PR generator failed: {e}")
        
        # Fallback to simple description
        description = f"# Milestone: {milestone_id}\n\n"
        description += f"## Completed Deliverables\n\n"
        for del_id in deliverable_ids:
            description += f"- {del_id}\n"
        description += f"\n## Changes\n\n"
        description += f"Files changed: {len(changes.get('files', []))}\n"
        return description
    
    async def _create_github_pr(
        self,
        owner: str,
        repo: str,
        branch_name: str,
        description: str
    ) -> dict:
        """Create PR via GitHub API (simplified)."""
        # This would use github_specialist to create actual PR
        # For now, return placeholder
        return {
            "number": 1,
            "html_url": f"https://github.com/{owner}/{repo}/pull/1"
        }
    
    async def _create_review_gate(
        self,
        project_id: str,
        milestone_id: str,
        deliverable_ids: List[str],
        pr_url: Optional[str]
    ) -> str:
        """Create gate for PR review."""
        if not self.gate_manager:
            return "no-gate"
        
        try:
            gate = await self.gate_manager.create_gate(
                project_id=project_id,
                gate_type="milestone_pr_review",
                context={
                    "milestone_id": milestone_id,
                    "deliverable_ids": deliverable_ids,
                    "pr_url": pr_url,
                    "reason": f"Review completed deliverables for milestone {milestone_id}"
                }
            )
            return gate.gate_id
        except Exception as e:
            logger.error(f"Failed to create gate: {e}")
            return "gate-creation-failed"
