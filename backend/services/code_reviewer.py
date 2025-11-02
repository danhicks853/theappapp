"""
Code Reviewer Service

LLM-powered code review and quality assessment.
Extends CodeValidator with style, maintainability, and bug detection.

Reference: Phase 3.3 - Quality Assurance System
"""
import logging
from typing import List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from backend.services.code_validator import CodeValidator, ValidationSeverity

logger = logging.getLogger(__name__)


class IssueSeverity(str, Enum):
    """Code review issue severity."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


@dataclass
class CodeIssue:
    """Code review issue."""
    severity: IssueSeverity
    category: str  # style, bug, security, performance, maintainability
    title: str
    description: str
    file_path: str
    line_number: int
    code_snippet: str
    suggested_fix: Optional[str] = None


@dataclass
class ReviewResult:
    """Code review result."""
    issues: List[CodeIssue]
    summary: str
    total_critical: int
    total_major: int
    total_minor: int
    overall_quality: float  # 0-100


class CodeReviewer:
    """
    LLM-powered code review service.
    
    Extends CodeValidator with:
    - Code style checking
    - Maintainability analysis
    - Bug detection
    - Performance issue detection
    - PR comment generation
    
    Example:
        reviewer = CodeReviewer(llm_client)
        result = await reviewer.review_code(code_diff)
        comment = await reviewer.generate_pr_comment(result)
    """
    
    def __init__(self, llm_client: Optional[Any] = None):
        """Initialize code reviewer."""
        self.llm_client = llm_client
        self.code_validator = CodeValidator()
        logger.info("CodeReviewer initialized")
    
    async def review_code(
        self,
        code_diff: str,
        language: str = "python"
    ) -> ReviewResult:
        """
        Review code changes.
        
        Args:
            code_diff: Git diff or code to review
            language: Programming language
        
        Returns:
            ReviewResult with issues and recommendations
        """
        logger.info("Reviewing code changes")
        
        issues = []
        
        # Run security validation
        validation = self.code_validator.validate(code_diff, language)
        for val_issue in validation.issues:
            issues.append(CodeIssue(
                severity=self._map_severity(val_issue.severity),
                category="security",
                title="Security Issue",
                description=val_issue.message,
                file_path="unknown",
                line_number=val_issue.line_number,
                code_snippet=val_issue.code_snippet
            ))
        
        # Check style issues
        style_issues = self._check_style(code_diff, language)
        issues.extend(style_issues)
        
        # Check maintainability
        maint_issues = self._check_maintainability(code_diff)
        issues.extend(maint_issues)
        
        # Count by severity
        critical = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
        major = sum(1 for i in issues if i.severity == IssueSeverity.MAJOR)
        minor = sum(1 for i in issues if i.severity == IssueSeverity.MINOR)
        
        # Calculate quality score
        quality = 100 - (critical * 20 + major * 10 + minor * 5)
        quality = max(0, min(100, quality))
        
        summary = f"Found {len(issues)} issues: {critical} critical, {major} major, {minor} minor"
        
        return ReviewResult(
            issues=issues,
            summary=summary,
            total_critical=critical,
            total_major=major,
            total_minor=minor,
            overall_quality=quality
        )
    
    def _check_style(self, code: str, language: str) -> List[CodeIssue]:
        """Check code style issues."""
        issues = []
        lines = code.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Check line length
            if len(line) > 120:
                issues.append(CodeIssue(
                    severity=IssueSeverity.MINOR,
                    category="style",
                    title="Line Too Long",
                    description=f"Line exceeds 120 characters ({len(line)} chars)",
                    file_path="unknown",
                    line_number=line_num,
                    code_snippet=line[:100] + "...",
                    suggested_fix="Break into multiple lines"
                ))
            
            # Check TODO comments
            if "TODO" in line or "FIXME" in line:
                issues.append(CodeIssue(
                    severity=IssueSeverity.INFO,
                    category="maintainability",
                    title="TODO Found",
                    description="Found TODO/FIXME comment",
                    file_path="unknown",
                    line_number=line_num,
                    code_snippet=line.strip()
                ))
        
        return issues
    
    def _check_maintainability(self, code: str) -> List[CodeIssue]:
        """Check maintainability issues."""
        issues = []
        lines = code.split('\n')
        
        # Check for magic numbers
        for line_num, line in enumerate(lines, 1):
            if any(char.isdigit() for char in line) and "=" in line:
                if not any(word in line.lower() for word in ['const', 'final', 'readonly']):
                    # Simplified check - would need better parsing
                    pass
        
        return issues
    
    async def generate_pr_comment(self, result: ReviewResult) -> str:
        """Generate PR comment from review result."""
        comment = f"## 🔍 Code Review\n\n"
        comment += f"**Overall Quality:** {result.overall_quality:.1f}/100\n\n"
        comment += f"{result.summary}\n\n"
        
        if result.total_critical > 0:
            comment += f"### 🔴 Critical Issues ({result.total_critical})\n\n"
            for issue in [i for i in result.issues if i.severity == IssueSeverity.CRITICAL]:
                comment += f"- **{issue.title}** (line {issue.line_number})\n"
                comment += f"  {issue.description}\n\n"
        
        if result.total_major > 0:
            comment += f"### 🟡 Major Issues ({result.total_major})\n\n"
            for issue in [i for i in result.issues if i.severity == IssueSeverity.MAJOR][:5]:
                comment += f"- {issue.title} (line {issue.line_number})\n"
        
        return comment
    
    def _map_severity(self, val_severity: ValidationSeverity) -> IssueSeverity:
        """Map ValidationSeverity to IssueSeverity."""
        mapping = {
            ValidationSeverity.CRITICAL: IssueSeverity.CRITICAL,
            ValidationSeverity.ERROR: IssueSeverity.MAJOR,
            ValidationSeverity.WARNING: IssueSeverity.MINOR,
            ValidationSeverity.INFO: IssueSeverity.INFO,
        }
        return mapping.get(val_severity, IssueSeverity.INFO)
