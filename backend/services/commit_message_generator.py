"""
Commit Message Generator Service

LLM-powered commit message generation following conventional commits.
Analyzes code diffs to generate semantic, descriptive commit messages.

Reference: Phase 2.4 - GitHub Integration (deferred from Phase 3+)
"""
import logging
from typing import Optional, List, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CommitMessage:
    """Generated commit message."""
    type: str  # feat, fix, docs, style, refactor, test, chore
    scope: Optional[str]
    subject: str
    body: Optional[str]
    footer: Optional[str]
    full_message: str


class CommitMessageGenerator:
    """
    Service for generating conventional commit messages with LLM.
    
    Follows Conventional Commits specification:
    <type>[optional scope]: <description>
    
    [optional body]
    
    [optional footer(s)]
    
    Example:
        generator = CommitMessageGenerator(llm_client)
        
        # Generate from diff
        commit = await generator.generate_from_diff(
            diff="+ def new_function():\\n+     pass",
            context="Added utility function"
        )
        print(commit.full_message)
        # Output: "feat(utils): add helper function for processing"
    """
    
    COMMIT_TYPES = {
        "feat": "A new feature",
        "fix": "A bug fix",
        "docs": "Documentation only changes",
        "style": "Changes that don't affect code meaning (formatting, etc.)",
        "refactor": "Code change that neither fixes a bug nor adds a feature",
        "perf": "Performance improvement",
        "test": "Adding or updating tests",
        "build": "Changes to build system or dependencies",
        "ci": "CI configuration changes",
        "chore": "Other changes that don't modify src or test files",
        "revert": "Reverts a previous commit",
    }
    
    def __init__(self, llm_client: Optional[Any] = None):
        """Initialize commit message generator."""
        self.llm_client = llm_client
        logger.info("CommitMessageGenerator initialized")
    
    async def generate_from_diff(
        self,
        diff: str,
        context: Optional[str] = None,
        files_changed: Optional[List[str]] = None
    ) -> CommitMessage:
        """
        Generate commit message from git diff.
        
        Args:
            diff: Git diff output
            context: Optional context about the changes
            files_changed: Optional list of changed files
        
        Returns:
            CommitMessage with conventional format
        """
        logger.info("Generating commit message from diff")
        
        if self.llm_client:
            return await self._generate_with_llm(diff, context, files_changed)
        
        return self._generate_with_heuristics(diff, files_changed)
    
    async def _generate_with_llm(
        self,
        diff: str,
        context: Optional[str],
        files_changed: Optional[List[str]]
    ) -> CommitMessage:
        """Generate with LLM (TODO: implement)."""
        logger.info("LLM commit message generation not yet implemented")
        return self._generate_with_heuristics(diff, files_changed)
    
    def _generate_with_heuristics(
        self,
        diff: str,
        files_changed: Optional[List[str]]
    ) -> CommitMessage:
        """Generate with heuristics."""
        
        # Analyze diff to determine type
        commit_type = self._determine_type(diff, files_changed)
        scope = self._determine_scope(files_changed) if files_changed else None
        subject = self._generate_subject(diff, commit_type, files_changed)
        
        full_message = f"{commit_type}"
        if scope:
            full_message += f"({scope})"
        full_message += f": {subject}"
        
        return CommitMessage(
            type=commit_type,
            scope=scope,
            subject=subject,
            body=None,
            footer=None,
            full_message=full_message
        )
    
    def _determine_type(
        self,
        diff: str,
        files_changed: Optional[List[str]]
    ) -> str:
        """Determine commit type from diff."""
        diff_lower = diff.lower()
        
        # Check for test files
        if files_changed and any("test" in f for f in files_changed):
            if "+def test_" in diff or "+it(" in diff or "+describe(" in diff:
                return "test"
        
        # Check for documentation
        if files_changed and any(f.endswith(('.md', '.rst', '.txt')) for f in files_changed):
            return "docs"
        
        # Check for CI/build files
        if files_changed and any(f in ['.github', 'Dockerfile', 'docker-compose', 'requirements.txt', 'package.json'] for f in files_changed):
            return "ci" if ".github" in str(files_changed) else "build"
        
        # Check for fixes
        if any(word in diff_lower for word in ["fix", "bug", "issue", "error", "crash"]):
            return "fix"
        
        # Check for performance
        if any(word in diff_lower for word in ["performance", "optimize", "faster", "cache"]):
            return "perf"
        
        # Check for refactoring
        if any(word in diff_lower for word in ["refactor", "restructure", "cleanup"]):
            return "refactor"
        
        # Check if only formatting/style
        if all(line.startswith(("-", "+")) and not any(c.isalnum() for c in line[1:]) for line in diff.split('\n') if line.strip()):
            return "style"
        
        # Default to feat for new code
        if diff.count("+") > diff.count("-"):
            return "feat"
        
        # Default to chore
        return "chore"
    
    def _determine_scope(self, files_changed: List[str]) -> Optional[str]:
        """Determine scope from changed files."""
        if not files_changed:
            return None
        
        # Extract common directory or module
        first_file = files_changed[0]
        
        # Backend modules
        if "backend/services/" in first_file:
            return first_file.split("backend/services/")[1].split("/")[0].replace(".py", "")
        if "backend/api/" in first_file:
            return "api"
        if "backend/agents/" in first_file:
            return "agents"
        
        # Frontend modules
        if "frontend/src/components/" in first_file:
            return "components"
        if "frontend/src/pages/" in first_file:
            return "pages"
        if "frontend/src/services/" in first_file:
            return "services"
        
        # Infrastructure
        if "docker" in first_file or "Dockerfile" in first_file:
            return "docker"
        if ".github" in first_file:
            return "ci"
        
        # Tests
        if "tests/" in first_file or "test_" in first_file:
            return "tests"
        
        return None
    
    def _generate_subject(
        self,
        diff: str,
        commit_type: str,
        files_changed: Optional[List[str]]
    ) -> str:
        """Generate commit subject line."""
        
        # Count additions and deletions
        additions = diff.count("\n+")
        deletions = diff.count("\n-")
        
        # Generate based on type
        if commit_type == "feat":
            if files_changed and len(files_changed) == 1:
                filename = files_changed[0].split("/")[-1].replace(".py", "").replace(".ts", "").replace(".tsx", "")
                return f"add {filename} implementation"
            return f"add new functionality"
        
        elif commit_type == "fix":
            return "fix issue"
        
        elif commit_type == "docs":
            return "update documentation"
        
        elif commit_type == "test":
            if additions > deletions:
                return "add tests"
            return "update tests"
        
        elif commit_type == "refactor":
            return "refactor code structure"
        
        elif commit_type == "perf":
            return "improve performance"
        
        elif commit_type == "style":
            return "format code"
        
        elif commit_type == "build":
            return "update dependencies"
        
        elif commit_type == "ci":
            return "update CI configuration"
        
        else:
            return "update codebase"
    
    def validate_message(self, message: str) -> bool:
        """
        Validate commit message follows conventional commits.
        
        Args:
            message: Commit message to validate
        
        Returns:
            True if valid
        """
        # Check format: type(scope): subject
        import re
        pattern = r'^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?: .{1,72}'
        return bool(re.match(pattern, message))
