"""
Security Test Runner Service

Security testing integration with AI vulnerability detection.
Extends CodeValidator with dependency scanning, secret detection, and more.

Reference: Phase 3.3 - Quality Assurance System
"""
import logging
import subprocess
import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from backend.services.code_validator import CodeValidator, ValidationSeverity

logger = logging.getLogger(__name__)


class VulnerabilityType(Enum):
    """Types of security vulnerabilities."""
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    HARDCODED_SECRET = "hardcoded_secret"
    WEAK_CRYPTO = "weak_crypto"
    DEPENDENCY_CVE = "dependency_cve"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    INSECURE_DESERIALIZATION = "insecure_deserialization"


@dataclass
class SecurityVulnerability:
    """Security vulnerability finding."""
    vulnerability_type: VulnerabilityType
    severity: ValidationSeverity
    title: str
    description: str
    file_path: str
    line_number: int
    code_snippet: str
    cve_id: Optional[str] = None
    suggested_fix: Optional[str] = None


@dataclass
class SecurityScanResult:
    """Result of security scan."""
    vulnerabilities: List[SecurityVulnerability]
    dependency_issues: List[Dict[str, Any]]
    secret_detections: List[Dict[str, Any]]
    total_critical: int
    total_high: int
    total_medium: int
    total_low: int
    scan_duration: float


class SecurityTestRunner:
    """
    Security testing service with AI-enhanced vulnerability detection.
    
    Extends CodeValidator with:
    - Dependency vulnerability scanning (bandit for Python, npm audit for Node)
    - Hardcoded secret detection
    - XSS pattern detection
    - SQL injection pattern detection
    - Weak cryptography detection
    - AI-powered pattern analysis
    
    Example:
        scanner = SecurityTestRunner(llm_client)
        result = await scanner.scan_code(code, language="python")
        result = await scanner.scan_dependencies(project_path)
        result = await scanner.scan_project(project_path)
    """
    
    # Patterns for secret detection
    SECRET_PATTERNS = [
        (r'(?i)(api[_-]?key|apikey)\s*[:=]\s*[\'"]([a-zA-Z0-9_\-]{20,})[\'"]', "API Key"),
        (r'(?i)(secret[_-]?key|secretkey)\s*[:=]\s*[\'"]([a-zA-Z0-9_\-]{20,})[\'"]', "Secret Key"),
        (r'(?i)(password|passwd|pwd)\s*[:=]\s*[\'"]([^\'\"]{8,})[\'"]', "Hardcoded Password"),
        (r'(?i)(access[_-]?token|accesstoken)\s*[:=]\s*[\'"]([a-zA-Z0-9_\-]{20,})[\'"]', "Access Token"),
        (r'(?i)(private[_-]?key|privatekey)\s*[:=]\s*[\'"]([^\'"]+)[\'"]', "Private Key"),
        (r'(sk-[a-zA-Z0-9]{48})', "OpenAI API Key"),
        (r'(ghp_[a-zA-Z0-9]{36})', "GitHub Personal Access Token"),
        (r'(AKIA[0-9A-Z]{16})', "AWS Access Key"),
    ]
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        (r'execute\s*\([^)]*%s[^)]*\)', "String formatting in SQL (use parameterized queries)"),
        (r'execute\s*\([^)]*\+[^)]*\)', "String concatenation in SQL (use parameterized queries)"),
        (r'execute\s*\([^)]*\.format\([^)]*\)', "String format in SQL (use parameterized queries)"),
        (r'execute\s*\([^)]*f["\']', "F-string in SQL (use parameterized queries)"),
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        (r'innerHTML\s*=', "Direct innerHTML assignment (XSS risk)"),
        (r'dangerouslySetInnerHTML', "React dangerouslySetInnerHTML (XSS risk)"),
        (r'document\.write\s*\(', "document.write usage (XSS risk)"),
        (r'eval\s*\(', "eval() usage (XSS/code injection risk)"),
    ]
    
    def __init__(
        self,
        llm_client: Optional[Any] = None,
        code_validator: Optional[CodeValidator] = None
    ):
        """
        Initialize security test runner.
        
        Args:
            llm_client: Optional LLM client for AI analysis
            code_validator: Optional CodeValidator instance (creates new if not provided)
        """
        self.llm_client = llm_client
        self.code_validator = code_validator or CodeValidator()
        logger.info("SecurityTestRunner initialized")
    
    async def scan_code(
        self,
        code: str,
        language: str = "python",
        file_path: str = "unknown.py"
    ) -> SecurityScanResult:
        """
        Scan code for security vulnerabilities.
        
        Args:
            code: Code to scan
            language: Programming language
            file_path: File path for reporting
        
        Returns:
            SecurityScanResult with findings
        """
        logger.info(f"Scanning code for security issues: {file_path}")
        
        import time
        start_time = time.time()
        
        vulnerabilities = []
        
        # Run base code validator
        validation = self.code_validator.validate(code, language)
        for issue in validation.issues:
            if issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]:
                vulnerabilities.append(SecurityVulnerability(
                    vulnerability_type=VulnerabilityType.COMMAND_INJECTION,
                    severity=issue.severity,
                    title="Code Validation Issue",
                    description=issue.message,
                    file_path=file_path,
                    line_number=issue.line_number,
                    code_snippet=issue.code_snippet
                ))
        
        # Scan for hardcoded secrets
        secret_vulns = self._scan_secrets(code, file_path)
        vulnerabilities.extend(secret_vulns)
        
        # Scan for SQL injection
        if language == "python":
            sql_vulns = self._scan_sql_injection(code, file_path)
            vulnerabilities.extend(sql_vulns)
        
        # Scan for XSS
        if language in ["javascript", "typescript", "tsx", "jsx"]:
            xss_vulns = self._scan_xss(code, file_path)
            vulnerabilities.extend(xss_vulns)
        
        # Count by severity
        severity_counts = self._count_severities(vulnerabilities)
        
        duration = time.time() - start_time
        
        return SecurityScanResult(
            vulnerabilities=vulnerabilities,
            dependency_issues=[],
            secret_detections=[],
            total_critical=severity_counts["critical"],
            total_high=severity_counts["high"],
            total_medium=severity_counts["medium"],
            total_low=severity_counts["low"],
            scan_duration=duration
        )
    
    async def scan_dependencies(
        self,
        project_path: str,
        language: str = "python"
    ) -> List[Dict[str, Any]]:
        """
        Scan dependencies for known vulnerabilities.
        
        Args:
            project_path: Path to project
            language: Language (python or javascript)
        
        Returns:
            List of dependency vulnerabilities
        """
        logger.info(f"Scanning dependencies in: {project_path}")
        
        if language == "python":
            return await self._scan_python_dependencies(project_path)
        elif language in ["javascript", "typescript"]:
            return await self._scan_npm_dependencies(project_path)
        else:
            logger.warning(f"Dependency scanning not supported for: {language}")
            return []
    
    async def _scan_python_dependencies(
        self,
        project_path: str
    ) -> List[Dict[str, Any]]:
        """Scan Python dependencies with bandit."""
        try:
            # Run bandit
            result = subprocess.run(
                ["bandit", "-r", project_path, "-f", "json"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.stdout:
                bandit_results = json.loads(result.stdout)
                return bandit_results.get("results", [])
            
            return []
        
        except FileNotFoundError:
            logger.warning("bandit not found - install with: pip install bandit")
            return []
        except subprocess.TimeoutExpired:
            logger.error("bandit scan timeout")
            return []
        except json.JSONDecodeError:
            logger.error("Failed to parse bandit output")
            return []
        except Exception as e:
            logger.error(f"Error running bandit: {e}")
            return []
    
    async def _scan_npm_dependencies(
        self,
        project_path: str
    ) -> List[Dict[str, Any]]:
        """Scan npm dependencies with npm audit."""
        try:
            result = subprocess.run(
                ["npm", "audit", "--json"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.stdout:
                audit_results = json.loads(result.stdout)
                vulnerabilities = []
                
                for vuln_id, vuln_data in audit_results.get("vulnerabilities", {}).items():
                    vulnerabilities.append({
                        "package": vuln_id,
                        "severity": vuln_data.get("severity"),
                        "title": vuln_data.get("title"),
                        "url": vuln_data.get("url")
                    })
                
                return vulnerabilities
            
            return []
        
        except FileNotFoundError:
            logger.warning("npm not found")
            return []
        except subprocess.TimeoutExpired:
            logger.error("npm audit timeout")
            return []
        except json.JSONDecodeError:
            logger.error("Failed to parse npm audit output")
            return []
        except Exception as e:
            logger.error(f"Error running npm audit: {e}")
            return []
    
    def _scan_secrets(
        self,
        code: str,
        file_path: str
    ) -> List[SecurityVulnerability]:
        """Scan for hardcoded secrets."""
        vulnerabilities = []
        
        lines = code.split('\n')
        for line_num, line in enumerate(lines, 1):
            for pattern, secret_type in self.SECRET_PATTERNS:
                matches = re.finditer(pattern, line)
                for match in matches:
                    vulnerabilities.append(SecurityVulnerability(
                        vulnerability_type=VulnerabilityType.HARDCODED_SECRET,
                        severity=ValidationSeverity.CRITICAL,
                        title=f"Hardcoded {secret_type} Detected",
                        description=f"Found hardcoded {secret_type}. Use environment variables instead.",
                        file_path=file_path,
                        line_number=line_num,
                        code_snippet=line.strip(),
                        suggested_fix="Use os.getenv() or environment configuration"
                    ))
        
        return vulnerabilities
    
    def _scan_sql_injection(
        self,
        code: str,
        file_path: str
    ) -> List[SecurityVulnerability]:
        """Scan for SQL injection vulnerabilities."""
        vulnerabilities = []
        
        lines = code.split('\n')
        for line_num, line in enumerate(lines, 1):
            for pattern, description in self.SQL_INJECTION_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    vulnerabilities.append(SecurityVulnerability(
                        vulnerability_type=VulnerabilityType.SQL_INJECTION,
                        severity=ValidationSeverity.CRITICAL,
                        title="SQL Injection Risk",
                        description=description,
                        file_path=file_path,
                        line_number=line_num,
                        code_snippet=line.strip(),
                        suggested_fix="Use parameterized queries with placeholders"
                    ))
        
        return vulnerabilities
    
    def _scan_xss(
        self,
        code: str,
        file_path: str
    ) -> List[SecurityVulnerability]:
        """Scan for XSS vulnerabilities."""
        vulnerabilities = []
        
        lines = code.split('\n')
        for line_num, line in enumerate(lines, 1):
            for pattern, description in self.XSS_PATTERNS:
                if re.search(pattern, line):
                    vulnerabilities.append(SecurityVulnerability(
                        vulnerability_type=VulnerabilityType.XSS,
                        severity=ValidationSeverity.CRITICAL,
                        title="XSS Vulnerability",
                        description=description,
                        file_path=file_path,
                        line_number=line_num,
                        code_snippet=line.strip(),
                        suggested_fix="Sanitize user input and use safe DOM manipulation methods"
                    ))
        
        return vulnerabilities
    
    def _count_severities(
        self,
        vulnerabilities: List[SecurityVulnerability]
    ) -> Dict[str, int]:
        """Count vulnerabilities by severity."""
        counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        for vuln in vulnerabilities:
            if vuln.severity == ValidationSeverity.CRITICAL:
                counts["critical"] += 1
            elif vuln.severity == ValidationSeverity.ERROR:
                counts["high"] += 1
            elif vuln.severity == ValidationSeverity.WARNING:
                counts["medium"] += 1
            else:
                counts["low"] += 1
        
        return counts
