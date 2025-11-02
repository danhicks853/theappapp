"""
PR Description Generator Service

LLM-powered pull request description generation.
Analyzes code changes to generate comprehensive PR descriptions.

Reference: Phase 2.4 - GitHub Integration (deferred from Phase 3+)
"""
import logging
from typing import Optional, List, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PRDescription:
    """Generated PR description."""
    title: str
    summary: str
    changes: List[str]
    testing: str
    breaking_changes: Optional[str]
    related_issues: List[str]
    full_description: str


class PRDescriptionGenerator:
    """
    Service for generating comprehensive pull request descriptions.
    
    Features:
    - Analyzes code diff to understand changes
    - Generates structured PR description
    - Identifies breaking changes
    - Suggests testing approach
    - Links to related issues
    
    Example:
        generator = PRDescriptionGenerator(llm_client)
        
        # Generate PR description
        pr = await generator.generate(
            diff="...",
            commit_messages=["feat: add user service", "test: add user tests"],
            files_changed=["backend/services/user_service.py"]
        )
        print(pr.full_description)
    """
    
    def __init__(self, llm_client: Optional[Any] = None):
        """Initialize PR description generator."""
        self.llm_client = llm_client
        logger.info("PRDescriptionGenerator initialized")
    
    async def generate(
        self,
        diff: str,
        commit_messages: Optional[List[str]] = None,
        files_changed: Optional[List[str]] = None,
        branch_name: Optional[str] = None
    ) -> PRDescription:
        """
        Generate PR description from changes.
        
        Args:
            diff: Git diff
            commit_messages: List of commit messages in PR
            files_changed: List of changed files
            branch_name: Optional branch name
        
        Returns:
            PRDescription with structured content
        """
        logger.info("Generating PR description")
        
        if self.llm_client:
            return await self._generate_with_llm(
                diff, commit_messages, files_changed, branch_name
            )
        
        return self._generate_with_heuristics(
            diff, commit_messages, files_changed, branch_name
        )
    
    async def _generate_with_llm(
        self,
        diff: str,
        commit_messages: Optional[List[str]],
        files_changed: Optional[List[str]],
        branch_name: Optional[str]
    ) -> PRDescription:
        """Generate with LLM (TODO: implement)."""
        logger.info("LLM PR description generation not yet implemented")
        return self._generate_with_heuristics(
            diff, commit_messages, files_changed, branch_name
        )
    
    def _generate_with_heuristics(
        self,
        diff: str,
        commit_messages: Optional[List[str]],
        files_changed: Optional[List[str]],
        branch_name: Optional[str]
    ) -> PRDescription:
        """Generate with heuristics."""
        
        # Generate title from commits or branch
        title = self._generate_title(commit_messages, branch_name)
        
        # Generate summary
        summary = self._generate_summary(diff, commit_messages, files_changed)
        
        # List changes
        changes = self._list_changes(diff, files_changed)
        
        # Generate testing notes
        testing = self._generate_testing_notes(files_changed)
        
        # Check for breaking changes
        breaking_changes = self._detect_breaking_changes(diff)
        
        # Extract related issues
        related_issues = self._extract_issues(commit_messages, branch_name)
        
        # Build full description
        full_description = self._format_description(
            title, summary, changes, testing, breaking_changes, related_issues
        )
        
        return PRDescription(
            title=title,
            summary=summary,
            changes=changes,
            testing=testing,
            breaking_changes=breaking_changes,
            related_issues=related_issues,
            full_description=full_description
        )
    
    def _generate_title(
        self,
        commit_messages: Optional[List[str]],
        branch_name: Optional[str]
    ) -> str:
        """Generate PR title."""
        if commit_messages and len(commit_messages) == 1:
            # Single commit - use its message
            return commit_messages[0].split('\n')[0]
        
        if branch_name:
            # Use branch name
            return branch_name.replace("-", " ").replace("_", " ").title()
        
        return "Update codebase"
    
    def _generate_summary(
        self,
        diff: str,
        commit_messages: Optional[List[str]],
        files_changed: Optional[List[str]]
    ) -> str:
        """Generate summary of changes."""
        if commit_messages and len(commit_messages) > 1:
            return f"This PR includes {len(commit_messages)} commits with various improvements and fixes."
        
        additions = diff.count("\n+")
        deletions = diff.count("\n-")
        files_count = len(files_changed) if files_changed else 0
        
        return f"This PR modifies {files_count} file(s) with {additions} additions and {deletions} deletions."
    
    def _list_changes(
        self,
        diff: str,
        files_changed: Optional[List[str]]
    ) -> List[str]:
        """List key changes."""
        changes = []
        
        if not files_changed:
            return ["Code updates"]
        
        # Group by type
        backend_files = [f for f in files_changed if "backend/" in f]
        frontend_files = [f for f in files_changed if "frontend/" in f]
        test_files = [f for f in files_changed if "test" in f.lower()]
        doc_files = [f for f in files_changed if f.endswith(('.md', '.rst'))]
        
        if backend_files:
            changes.append(f"Backend changes in {len(backend_files)} file(s)")
        if frontend_files:
            changes.append(f"Frontend changes in {len(frontend_files)} file(s)")
        if test_files:
            changes.append(f"Test updates in {len(test_files)} file(s)")
        if doc_files:
            changes.append(f"Documentation updates")
        
        return changes or ["Code updates"]
    
    def _generate_testing_notes(
        self,
        files_changed: Optional[List[str]]
    ) -> str:
        """Generate testing notes."""
        if files_changed and any("test" in f.lower() for f in files_changed):
            return "Tests have been added/updated. Run the test suite to verify."
        
        return "Please test manually and add automated tests if needed."
    
    def _detect_breaking_changes(self, diff: str) -> Optional[str]:
        """Detect potential breaking changes."""
        breaking_keywords = [
            "breaking change",
            "BREAKING CHANGE",
            "deprecated",
            "removed",
            "renamed"
        ]
        
        for keyword in breaking_keywords:
            if keyword in diff:
                return f"⚠️ This PR may contain breaking changes. Review carefully."
        
        return None
    
    def _extract_issues(
        self,
        commit_messages: Optional[List[str]],
        branch_name: Optional[str]
    ) -> List[str]:
        """Extract related issue numbers."""
        import re
        issues = set()
        
        # Check commit messages
        if commit_messages:
            for msg in commit_messages:
                # Find patterns like #123, fixes #456, closes #789
                matches = re.findall(r'#(\d+)', msg)
                issues.update(matches)
        
        # Check branch name
        if branch_name:
            matches = re.findall(r'#?(\d+)', branch_name)
            issues.update(matches)
        
        return [f"#{issue}" for issue in sorted(issues)]
    
    def _format_description(
        self,
        title: str,
        summary: str,
        changes: List[str],
        testing: str,
        breaking_changes: Optional[str],
        related_issues: List[str]
    ) -> str:
        """Format complete PR description."""
        description = f"## Summary\n\n{summary}\n\n"
        
        description += "## Changes\n\n"
        for change in changes:
            description += f"- {change}\n"
        description += "\n"
        
        if breaking_changes:
            description += f"## ⚠️ Breaking Changes\n\n{breaking_changes}\n\n"
        
        description += f"## Testing\n\n{testing}\n\n"
        
        if related_issues:
            description += "## Related Issues\n\n"
            for issue in related_issues:
                description += f"- {issue}\n"
            description += "\n"
        
        description += "## Checklist\n\n"
        description += "- [ ] Tests pass locally\n"
        description += "- [ ] Code follows project style guidelines\n"
        description += "- [ ] Documentation updated (if needed)\n"
        description += "- [ ] No breaking changes (or documented above)\n"
        
        return description
