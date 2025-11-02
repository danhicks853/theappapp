"""
Failure Learner Service

Continuous learning from test failures using LLM analysis and RAG.
Wires together RAGService and FeedbackCollector to learn from failures.

Reference: Phase 3.3 - Quality Assurance System
"""
import logging
from typing import List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from backend.services.rag_service import RAGService, SearchResult
from backend.services.feedback_collector import FeedbackCollector

logger = logging.getLogger(__name__)


@dataclass
class FailurePattern:
    """Detected failure pattern."""
    pattern_id: str
    error_type: str
    description: str
    occurrence_count: int
    first_seen: str
    last_seen: str
    similar_failures: List[str]
    suggested_fix: Optional[str] = None


@dataclass
class FailureAnalysis:
    """Analysis of a test failure."""
    failure_id: str
    error_message: str
    stack_trace: str
    root_cause: str
    confidence: float  # 0.0-1.0
    similar_patterns: List[FailurePattern]
    prevention_steps: List[str]
    learning_captured: bool


class FailureLearner:
    """
    Service for learning from test failures using RAG and LLM analysis.
    
    Features:
    - Captures test failures with context
    - Analyzes failures with LLM to identify patterns
    - Stores patterns in RAG knowledge base
    - Searches for similar historical failures
    - Suggests preventive measures
    
    Wires together:
    - RAGService: For storing/searching failure patterns
    - FeedbackCollector: For pattern analysis and insights
    
    Example:
        learner = FailureLearner(rag_service, feedback_collector, llm_client)
        
        # When a test fails
        analysis = await learner.analyze_failure(
            error_message="AttributeError: 'NoneType' object has no attribute 'id'",
            stack_trace="...",
            code_context="user = get_user(user_id)\\nuser.id"
        )
        
        # Get prevention steps
        for step in analysis.prevention_steps:
            print(step)
    """
    
    def __init__(
        self,
        rag_service: RAGService,
        feedback_collector: FeedbackCollector,
        llm_client: Optional[Any] = None
    ):
        """
        Initialize failure learner.
        
        Args:
            rag_service: RAG service for pattern storage
            feedback_collector: Feedback collector for pattern analysis
            llm_client: Optional LLM client for analysis
        """
        self.rag = rag_service
        self.feedback = feedback_collector
        self.llm_client = llm_client
        logger.info("FailureLearner initialized")
    
    async def analyze_failure(
        self,
        error_message: str,
        stack_trace: str,
        code_context: Optional[str] = None,
        test_name: Optional[str] = None,
        agent_type: Optional[str] = None
    ) -> FailureAnalysis:
        """
        Analyze a test failure and learn from it.
        
        Args:
            error_message: The error message
            stack_trace: Full stack trace
            code_context: Optional code that caused the failure
            test_name: Optional test that failed
            agent_type: Optional agent type that generated the code
        
        Returns:
            FailureAnalysis with root cause and prevention steps
        """
        logger.info(f"Analyzing failure: {error_message[:100]}...")
        
        failure_id = self._generate_failure_id()
        
        # Search for similar historical failures
        similar_patterns = await self._find_similar_failures(
            error_message, stack_trace
        )
        
        # Analyze with LLM if available
        if self.llm_client:
            root_cause, confidence, prevention_steps = await self._analyze_with_llm(
                error_message, stack_trace, code_context, similar_patterns
            )
        else:
            root_cause, confidence, prevention_steps = self._analyze_with_heuristics(
                error_message, stack_trace
            )
        
        # Store this failure as a pattern for future learning
        learning_captured = await self._store_failure_pattern(
            failure_id=failure_id,
            error_message=error_message,
            stack_trace=stack_trace,
            root_cause=root_cause,
            code_context=code_context,
            agent_type=agent_type
        )
        
        # Collect feedback for continuous improvement
        await self.feedback.collect_feedback(
            gate_id=failure_id,  # Use failure_id as gate_id
            feedback_type="test_failure",
            feedback_text=f"{root_cause}\\n\\nError: {error_message}",
            agent_type=agent_type,
            tags=self._extract_tags(error_message),
            metadata={
                "test_name": test_name,
                "error_type": self._classify_error(error_message)
            }
        )
        
        return FailureAnalysis(
            failure_id=failure_id,
            error_message=error_message,
            stack_trace=stack_trace,
            root_cause=root_cause,
            confidence=confidence,
            similar_patterns=similar_patterns,
            prevention_steps=prevention_steps,
            learning_captured=learning_captured
        )
    
    async def _find_similar_failures(
        self,
        error_message: str,
        stack_trace: str
    ) -> List[FailurePattern]:
        """Find similar failures from historical data."""
        # Search RAG for similar error messages
        search_query = f"{error_message}\\n{stack_trace[:500]}"
        
        results: List[SearchResult] = await self.rag.search(
            query=search_query,
            specialist_id="failure_patterns",  # Special collection for failures
            top_k=5
        )
        
        patterns = []
        for result in results:
            if result.score > 0.7:  # High similarity threshold
                patterns.append(FailurePattern(
                    pattern_id=result.metadata.get("pattern_id", "unknown"),
                    error_type=result.metadata.get("error_type", "unknown"),
                    description=result.text,
                    occurrence_count=result.metadata.get("count", 1),
                    first_seen=result.metadata.get("first_seen", "unknown"),
                    last_seen=result.metadata.get("last_seen", "unknown"),
                    similar_failures=[],
                    suggested_fix=result.metadata.get("suggested_fix")
                ))
        
        return patterns
    
    async def _analyze_with_llm(
        self,
        error_message: str,
        stack_trace: str,
        code_context: Optional[str],
        similar_patterns: List[FailurePattern]
    ) -> tuple[str, float, List[str]]:
        """Analyze failure with LLM."""
        # TODO: Implement LLM analysis
        logger.info("LLM failure analysis not yet implemented")
        return self._analyze_with_heuristics(error_message, stack_trace)
    
    def _analyze_with_heuristics(
        self,
        error_message: str,
        stack_trace: str
    ) -> tuple[str, float, List[str]]:
        """Analyze failure with heuristics."""
        error_type = self._classify_error(error_message)
        
        # Pattern-based analysis
        if "AttributeError" in error_message and "NoneType" in error_message:
            root_cause = "Attempted to access attribute on None object - missing null check"
            prevention_steps = [
                "Add null/None checks before accessing attributes",
                "Use optional chaining or default values",
                "Validate input before processing"
            ]
            confidence = 0.9
        
        elif "KeyError" in error_message:
            root_cause = "Attempted to access missing dictionary key"
            prevention_steps = [
                "Use .get() with default value instead of []",
                "Validate required keys exist",
                "Add error handling for missing keys"
            ]
            confidence = 0.85
        
        elif "TypeError" in error_message:
            root_cause = "Type mismatch or invalid operation for type"
            prevention_steps = [
                "Add type hints and use mypy for static type checking",
                "Validate input types",
                "Convert types explicitly when needed"
            ]
            confidence = 0.8
        
        elif "IndexError" in error_message:
            root_cause = "Attempted to access index outside list bounds"
            prevention_steps = [
                "Check list length before accessing by index",
                "Use enumerate() or iterate safely",
                "Handle empty list case"
            ]
            confidence = 0.85
        
        elif "ConnectionError" in error_message or "timeout" in error_message.lower():
            root_cause = "Network/database connection issue"
            prevention_steps = [
                "Add retry logic with exponential backoff",
                "Increase timeout values",
                "Add connection pool management",
                "Test with mock data when service unavailable"
            ]
            confidence = 0.75
        
        else:
            root_cause = f"Unclassified {error_type} error"
            prevention_steps = [
                "Review error message and stack trace",
                "Add specific error handling",
                "Add logging for debugging"
            ]
            confidence = 0.5
        
        return root_cause, confidence, prevention_steps
    
    def _classify_error(self, error_message: str) -> str:
        """Classify error type from message."""
        error_types = [
            "AttributeError", "KeyError", "TypeError", "ValueError",
            "IndexError", "NameError", "ImportError", "ConnectionError",
            "TimeoutError", "AssertionError", "RuntimeError"
        ]
        
        for error_type in error_types:
            if error_type in error_message:
                return error_type
        
        return "UnknownError"
    
    def _extract_tags(self, error_message: str) -> List[str]:
        """Extract tags from error message for categorization."""
        tags = []
        
        error_type = self._classify_error(error_message)
        tags.append(error_type.lower())
        
        # Add contextual tags
        if "None" in error_message or "null" in error_message.lower():
            tags.append("null_handling")
        
        if "connection" in error_message.lower() or "timeout" in error_message.lower():
            tags.append("network")
        
        if "database" in error_message.lower() or "sql" in error_message.lower():
            tags.append("database")
        
        if "permission" in error_message.lower() or "auth" in error_message.lower():
            tags.append("security")
        
        return tags
    
    async def _store_failure_pattern(
        self,
        failure_id: str,
        error_message: str,
        stack_trace: str,
        root_cause: str,
        code_context: Optional[str],
        agent_type: Optional[str]
    ) -> bool:
        """Store failure pattern in RAG for future learning."""
        try:
            # Create document text
            document_text = f"""
Error: {error_message}

Root Cause: {root_cause}

Stack Trace:
{stack_trace[:1000]}

Code Context:
{code_context[:500] if code_context else 'N/A'}
"""
            
            # Store in RAG
            await self.rag.index_document(
                text=document_text,
                specialist_id="failure_patterns",
                metadata={
                    "pattern_id": failure_id,
                    "error_type": self._classify_error(error_message),
                    "error_message": error_message[:200],
                    "root_cause": root_cause,
                    "agent_type": agent_type,
                    "first_seen": datetime.utcnow().isoformat(),
                    "last_seen": datetime.utcnow().isoformat(),
                    "count": 1
                }
            )
            
            logger.info(f"Stored failure pattern: {failure_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to store failure pattern: {e}")
            return False
    
    async def get_common_patterns(
        self,
        agent_type: Optional[str] = None,
        error_type: Optional[str] = None,
        limit: int = 10
    ) -> List[FailurePattern]:
        """
        Get most common failure patterns.
        
        Args:
            agent_type: Filter by agent type
            error_type: Filter by error type
            limit: Maximum patterns to return
        
        Returns:
            List of common failure patterns
        """
        # Use FeedbackCollector to get pattern insights
        insights = await self.feedback.get_feedback_insights(agent_type)
        
        # Convert to FailurePattern format
        patterns = []
        for pattern_data in insights.get("common_patterns", [])[:limit]:
            if error_type and pattern_data.get("error_type") != error_type:
                continue
            
            patterns.append(FailurePattern(
                pattern_id=pattern_data.get("id", "unknown"),
                error_type=pattern_data.get("error_type", "unknown"),
                description=pattern_data.get("description", ""),
                occurrence_count=pattern_data.get("count", 0),
                first_seen=pattern_data.get("first_seen", ""),
                last_seen=pattern_data.get("last_seen", ""),
                similar_failures=[],
                suggested_fix=pattern_data.get("suggested_fix")
            ))
        
        return patterns
    
    def _generate_failure_id(self) -> str:
        """Generate unique failure ID."""
        import uuid
        return f"failure-{uuid.uuid4()}"
