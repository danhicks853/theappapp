"""
Code Validator Service

Pre-execution validation and security scanning for AI-generated code.
Catches obvious security issues and syntax errors before execution.
"""
import re
import logging
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity level for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Single validation issue."""
    severity: ValidationSeverity
    message: str
    line_number: int = 0
    code_snippet: str = ""


@dataclass
class ValidationResult:
    """Result of code validation."""
    valid: bool
    issues: List[ValidationIssue]
    language: str
    code_length: int
    
    def has_errors(self) -> bool:
        """Check if there are any error-level issues."""
        return any(
            issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]
            for issue in self.issues
        )
    
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return any(
            issue.severity == ValidationSeverity.WARNING
            for issue in self.issues
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "language": self.language,
            "code_length": self.code_length,
            "issues": [
                {
                    "severity": issue.severity.value,
                    "message": issue.message,
                    "line_number": issue.line_number,
                    "code_snippet": issue.code_snippet
                }
                for issue in self.issues
            ]
        }


class CodeValidator:
    """
    Validates AI-generated code for security and syntax issues.
    
    Features:
    - Dangerous pattern detection (eval, exec, system calls)
    - Size limits (prevent memory exhaustion)
    - Basic syntax validation
    - Language-specific checks
    
    Note: This is a lightweight validation layer, not a comprehensive security scanner.
    """
    
    # Maximum code size (1MB)
    MAX_CODE_SIZE = 1024 * 1024
    
    # Dangerous patterns for Python
    PYTHON_DANGEROUS_PATTERNS = [
        (r'\beval\s*\(', "Use of eval() - potential code injection"),
        (r'\bexec\s*\(', "Use of exec() - potential code injection"),
        (r'\b__import__\s*\(', "Use of __import__() - potential security risk"),
        (r'\bcompile\s*\(', "Use of compile() - potential code injection"),
        (r'\bos\.system\s*\(', "Use of os.system() - use subprocess instead"),
        (r'\bsubprocess\.call\s*\([^,]+shell\s*=\s*True', "subprocess with shell=True - command injection risk"),
        (r'\bpickle\.loads?\s*\(', "Use of pickle - potential code execution"),
        (r'\byaml\.load\s*\([^,]+Loader\s*=\s*yaml\.Loader', "Unsafe YAML loading"),
        (r'\binput\s*\(.*\bpassword\b', "Avoid using input() for passwords"),
    ]
    
    # Dangerous patterns for JavaScript/Node
    JAVASCRIPT_DANGEROUS_PATTERNS = [
        (r'\beval\s*\(', "Use of eval() - potential code injection"),
        (r'\bFunction\s*\(', "Use of Function() constructor - code injection risk"),
        (r'\bsetTimeout\s*\(\s*["\']', "setTimeout with string - use function instead"),
        (r'\bsetInterval\s*\(\s*["\']', "setInterval with string - use function instead"),
        (r'\.innerHTML\s*=', "Use of innerHTML - XSS risk, use textContent"),
        (r'document\.write\s*\(', "Use of document.write() - security risk"),
        (r'dangerouslySetInnerHTML', "Use of dangerouslySetInnerHTML - XSS risk"),
        (r'\bchild_process\.exec\s*\(', "Use of child_process.exec - command injection risk"),
    ]
    
    # Suspicious patterns (warnings, not errors)
    SUSPICIOUS_PATTERNS = [
        (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password detected"),
        (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key detected"),
        (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret detected"),
        (r'token\s*=\s*["\'][^"\']+["\']', "Hardcoded token detected"),
        (r'TODO|FIXME|HACK|XXX', "Code contains TODO/FIXME comment"),
    ]
    
    def validate_code(
        self,
        code: str,
        language: str
    ) -> ValidationResult:
        """
        Validate code for security and syntax issues.
        
        Args:
            code: Source code to validate
            language: Programming language (python, javascript, etc.)
        
        Returns:
            ValidationResult with issues found
        """
        language_lower = language.lower()
        issues: List[ValidationIssue] = []
        
        # Check code size
        code_length = len(code)
        if code_length == 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Empty code provided"
            ))
            return ValidationResult(
                valid=False,
                issues=issues,
                language=language,
                code_length=0
            )
        
        if code_length > self.MAX_CODE_SIZE:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Code size ({code_length} bytes) exceeds maximum ({self.MAX_CODE_SIZE} bytes)"
            ))
            return ValidationResult(
                valid=False,
                issues=issues,
                language=language,
                code_length=code_length
            )
        
        # Language-specific dangerous patterns
        if language_lower in ["python", "py"]:
            issues.extend(self._check_patterns(
                code,
                self.PYTHON_DANGEROUS_PATTERNS,
                ValidationSeverity.WARNING
            ))
        elif language_lower in ["javascript", "js", "node", "nodejs", "typescript", "ts"]:
            issues.extend(self._check_patterns(
                code,
                self.JAVASCRIPT_DANGEROUS_PATTERNS,
                ValidationSeverity.WARNING
            ))
        
        # Check for suspicious patterns (all languages)
        issues.extend(self._check_patterns(
            code,
            self.SUSPICIOUS_PATTERNS,
            ValidationSeverity.INFO
        ))
        
        # Basic syntax checks
        syntax_issues = self._check_syntax(code, language_lower)
        issues.extend(syntax_issues)
        
        # Determine if code is valid
        # We warn on dangerous patterns but don't block (agents might have legitimate use)
        valid = not any(
            issue.severity == ValidationSeverity.ERROR
            for issue in issues
        )
        
        if issues:
            logger.info(
                f"Code validation for {language}: {len(issues)} issues found "
                f"(valid={valid})"
            )
        
        return ValidationResult(
            valid=valid,
            issues=issues,
            language=language,
            code_length=code_length
        )
    
    def _check_patterns(
        self,
        code: str,
        patterns: List[tuple],
        severity: ValidationSeverity
    ) -> List[ValidationIssue]:
        """
        Check code for dangerous patterns.
        
        Args:
            code: Source code
            patterns: List of (regex, message) tuples
            severity: Severity level for matches
        
        Returns:
            List of ValidationIssues
        """
        issues = []
        lines = code.split('\n')
        
        for pattern, message in patterns:
            for line_num, line in enumerate(lines, start=1):
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(ValidationIssue(
                        severity=severity,
                        message=message,
                        line_number=line_num,
                        code_snippet=line.strip()[:100]  # First 100 chars
                    ))
        
        return issues
    
    def _check_syntax(
        self,
        code: str,
        language: str
    ) -> List[ValidationIssue]:
        """
        Basic syntax validation.
        
        Note: This is lightweight validation. Full syntax checking happens
        during execution in the container.
        
        Args:
            code: Source code
            language: Programming language
        
        Returns:
            List of ValidationIssues
        """
        issues = []
        
        # Python syntax check
        if language in ["python", "py"]:
            try:
                compile(code, '<string>', 'exec')
            except SyntaxError as e:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Python syntax error: {e.msg}",
                    line_number=e.lineno or 0,
                    code_snippet=e.text.strip() if e.text else ""
                ))
        
        # JavaScript/TypeScript - basic checks
        elif language in ["javascript", "js", "typescript", "ts", "node", "nodejs"]:
            # Check for common syntax errors
            if code.count('{') != code.count('}'):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message="Mismatched curly braces - possible syntax error"
                ))
            if code.count('(') != code.count(')'):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message="Mismatched parentheses - possible syntax error"
                ))
            if code.count('[') != code.count(']'):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message="Mismatched square brackets - possible syntax error"
                ))
        
        return issues


# Singleton instance
_code_validator: CodeValidator = None


def get_code_validator() -> CodeValidator:
    """Get singleton CodeValidator instance."""
    global _code_validator
    
    if _code_validator is None:
        _code_validator = CodeValidator()
    
    return _code_validator
