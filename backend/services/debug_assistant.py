"""
Debug Assistant Service

Structured debugging process with LLM assistance.
Analyzes failures and generates debugging plans.

Reference: Phase 3.4 - Debugging & Failure Resolution
"""
import logging
from typing import List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DebugPlan:
    """Debugging plan with steps."""
    likely_cause: str
    confidence: float  # 0.0-1.0
    debug_steps: List[str]
    verification_steps: List[str]
    estimated_time_minutes: int


class DebugAssistant:
    """
    Service for structured debugging with LLM assistance.
    
    Process:
    1. Capture error message, stack trace, code context, recent changes
    2. Analyze with LLM to identify likely root cause
    3. Generate debugging steps
    4. Provide verification steps
    
    Example:
        assistant = DebugAssistant(llm_client)
        plan = await assistant.analyze_failure(
            error="Database connection timeout",
            stack_trace="...",
            code_context="...",
            recent_changes=["Added connection pooling"]
        )
        for step in plan.debug_steps:
            print(step)
    """
    
    def __init__(self, llm_client: Optional[Any] = None):
        """Initialize debug assistant."""
        self.llm_client = llm_client
        logger.info("DebugAssistant initialized")
    
    async def analyze_failure(
        self,
        error: str,
        stack_trace: Optional[str] = None,
        code_context: Optional[str] = None,
        recent_changes: Optional[List[str]] = None
    ) -> DebugPlan:
        """
        Analyze failure and generate debug plan.
        
        Args:
            error: Error message
            stack_trace: Stack trace
            code_context: Code that failed
            recent_changes: Recent code changes
        
        Returns:
            DebugPlan with steps
        """
        logger.info(f"Analyzing failure: {error[:100]}...")
        
        if self.llm_client:
            return await self._analyze_with_llm(
                error, stack_trace, code_context, recent_changes
            )
        
        return self._analyze_with_heuristics(error, stack_trace)
    
    async def _analyze_with_llm(
        self,
        error: str,
        stack_trace: Optional[str],
        code_context: Optional[str],
        recent_changes: Optional[List[str]]
    ) -> DebugPlan:
        """Analyze with LLM (TODO: implement)."""
        logger.info("LLM debug analysis not yet implemented")
        return self._analyze_with_heuristics(error, stack_trace)
    
    def _analyze_with_heuristics(
        self,
        error: str,
        stack_trace: Optional[str]
    ) -> DebugPlan:
        """Analyze with heuristics."""
        
        # Database connection issues
        if "connection" in error.lower() and "timeout" in error.lower():
            return DebugPlan(
                likely_cause="Database connection timeout",
                confidence=0.8,
                debug_steps=[
                    "Check database connection pool settings",
                    "Verify database server is running and accessible",
                    "Check for long-running queries blocking connections",
                    "Review network connectivity to database",
                    "Increase connection timeout value temporarily",
                ],
                verification_steps=[
                    "Monitor connection pool metrics",
                    "Run test query to verify connectivity",
                    "Check database logs for errors"
                ],
                estimated_time_minutes=30
            )
        
        # AttributeError with None
        elif "AttributeError" in error and "NoneType" in error:
            return DebugPlan(
                likely_cause="Attempted to access attribute on None object",
                confidence=0.9,
                debug_steps=[
                    "Identify which variable is None in the stack trace",
                    "Add null check before attribute access",
                    "Trace back to find where None is being assigned",
                    "Add logging to verify object creation",
                ],
                verification_steps=[
                    "Add assert statements to verify object is not None",
                    "Run test case that reproduces the error"
                ],
                estimated_time_minutes=15
            )
        
        # Import errors
        elif "ImportError" in error or "ModuleNotFoundError" in error:
            return DebugPlan(
                likely_cause="Missing or incorrect module import",
                confidence=0.95,
                debug_steps=[
                    "Verify module is installed: pip list | grep <module>",
                    "Check requirements.txt for missing dependency",
                    "Verify Python path includes module location",
                    "Check for typos in import statement",
                    "Install missing module: pip install <module>"
                ],
                verification_steps=[
                    "Run python -c 'import <module>' to verify",
                    "Re-run application"
                ],
                estimated_time_minutes=10
            )
        
        # Generic fallback
        else:
            return DebugPlan(
                likely_cause=f"Unclassified error: {error[:100]}",
                confidence=0.5,
                debug_steps=[
                    "Review complete error message and stack trace",
                    "Search error message in documentation and Stack Overflow",
                    "Add detailed logging around the failure point",
                    "Reproduce error in isolated test case",
                    "Use debugger to step through code"
                ],
                verification_steps=[
                    "Verify fix with test case",
                    "Check for similar errors in other parts of code"
                ],
                estimated_time_minutes=60
            )
