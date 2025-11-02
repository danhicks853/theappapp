"""
Failure Signature Models

Models for extracting and storing failure signatures to detect loops.
Enables intelligent comparison of failures to identify repeated patterns.

Reference: Section 1.4.1 - Loop Detection Algorithm
"""
import hashlib
import re
from datetime import datetime, UTC
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class ErrorType(str, Enum):
    """Common error types for classification."""
    SYNTAX_ERROR = "syntax_error"
    TYPE_ERROR = "type_error"
    IMPORT_ERROR = "import_error"
    ATTRIBUTE_ERROR = "attribute_error"
    KEY_ERROR = "key_error"
    VALUE_ERROR = "value_error"
    INDEX_ERROR = "index_error"
    RUNTIME_ERROR = "runtime_error"
    ASSERTION_ERROR = "assertion_error"
    TIMEOUT_ERROR = "timeout_error"
    CONNECTION_ERROR = "connection_error"
    HTTP_ERROR = "http_error"
    DATABASE_ERROR = "database_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN = "unknown"


@dataclass
class FailureSignature:
    """
    Represents a unique failure signature for loop detection.
    
    Used to compare failures and detect when the same error occurs repeatedly.
    """
    exact_message: str
    error_type: ErrorType
    location: Optional[str]  # file:line format
    context_hash: str  # Hash of stack trace or error context
    timestamp: datetime
    agent_id: str
    task_id: str
    metadata: Dict[str, Any]
    
    @classmethod
    def from_error(
        cls,
        error_message: str,
        agent_id: str,
        task_id: str,
        stack_trace: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "FailureSignature":
        """
        Create a failure signature from an error.
        
        Args:
            error_message: The error message text
            agent_id: Agent that encountered the error
            task_id: Task being executed
            stack_trace: Optional stack trace
            metadata: Additional context
        
        Returns:
            FailureSignature instance
        """
        error_type = cls._classify_error(error_message)
        location = cls._extract_location(error_message, stack_trace)
        context_hash = cls._hash_context(error_message, stack_trace)
        
        return cls(
            exact_message=error_message.strip(),
            error_type=error_type,
            location=location,
            context_hash=context_hash,
            timestamp=datetime.now(UTC),
            agent_id=agent_id,
            task_id=task_id,
            metadata=metadata or {}
        )
    
    @staticmethod
    def _classify_error(error_message: str) -> ErrorType:
        """Classify error type from message."""
        msg_lower = error_message.lower()
        
        # Check for specific error types
        if "syntaxerror" in msg_lower or "syntax error" in msg_lower:
            return ErrorType.SYNTAX_ERROR
        elif "typeerror" in msg_lower or "type error" in msg_lower:
            return ErrorType.TYPE_ERROR
        elif "importerror" in msg_lower or "modulenotfounderror" in msg_lower:
            return ErrorType.IMPORT_ERROR
        elif "attributeerror" in msg_lower or "attribute error" in msg_lower:
            return ErrorType.ATTRIBUTE_ERROR
        elif "keyerror" in msg_lower or "key error" in msg_lower:
            return ErrorType.KEY_ERROR
        elif "valueerror" in msg_lower or "value error" in msg_lower:
            return ErrorType.VALUE_ERROR
        elif "indexerror" in msg_lower or "index error" in msg_lower:
            return ErrorType.INDEX_ERROR
        elif "assertionerror" in msg_lower or "assertion" in msg_lower:
            return ErrorType.ASSERTION_ERROR
        elif "timeout" in msg_lower:
            return ErrorType.TIMEOUT_ERROR
        elif "connection" in msg_lower or "network" in msg_lower:
            return ErrorType.CONNECTION_ERROR
        elif "http" in msg_lower or "status code" in msg_lower:
            return ErrorType.HTTP_ERROR
        elif "database" in msg_lower or "sql" in msg_lower:
            return ErrorType.DATABASE_ERROR
        elif "validation" in msg_lower:
            return ErrorType.VALIDATION_ERROR
        else:
            return ErrorType.UNKNOWN
    
    @staticmethod
    def _extract_location(
        error_message: str,
        stack_trace: Optional[str]
    ) -> Optional[str]:
        """Extract file:line location from error or stack trace."""
        # Try to find file:line patterns
        # Pattern: "file.py", line 123
        pattern1 = r'"([^"]+\.py)",\s+line\s+(\d+)'
        # Pattern: File "file.py", line 123
        pattern2 = r'File\s+"([^"]+\.py)",\s+line\s+(\d+)'
        # Pattern: at file.py:123
        pattern3 = r'at\s+([^:\s]+\.py):(\d+)'
        
        text = (stack_trace or "") + "\n" + error_message
        
        for pattern in [pattern1, pattern2, pattern3]:
            match = re.search(pattern, text)
            if match:
                return f"{match.group(1)}:{match.group(2)}"
        
        return None
    
    @staticmethod
    def _hash_context(error_message: str, stack_trace: Optional[str]) -> str:
        """
        Create hash of error context for comparison.
        
        Uses stack trace if available, otherwise uses error message.
        Removes line numbers and variable values for fuzzy matching.
        """
        # Combine stack trace and error message
        text = (stack_trace or "") + "\n" + error_message
        
        # Normalize: remove line numbers and memory addresses
        normalized = re.sub(r'\b\d+\b', 'N', text)  # Replace numbers
        normalized = re.sub(r'0x[0-9a-fA-F]+', '0xADDR', normalized)  # Memory addresses
        normalized = re.sub(r'"[^"]*"', '"STR"', normalized)  # String literals
        normalized = normalized.lower().strip()
        
        # Create hash
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def is_identical_to(self, other: "FailureSignature") -> bool:
        """
        Check if this failure is identical to another.
        
        Used for loop detection - identical failures indicate a loop.
        """
        return (
            self.error_type == other.error_type and
            self.context_hash == other.context_hash
        )
    
    def is_similar_to(self, other: "FailureSignature") -> bool:
        """
        Check if this failure is similar to another.
        
        More lenient than is_identical_to, allows for minor variations.
        """
        if self.error_type != other.error_type:
            return False
        
        # Check if messages are very similar
        msg1_words = set(self.exact_message.lower().split())
        msg2_words = set(other.exact_message.lower().split())
        
        if not msg1_words or not msg2_words:
            return False
        
        # Jaccard similarity
        intersection = msg1_words.intersection(msg2_words)
        union = msg1_words.union(msg2_words)
        similarity = len(intersection) / len(union) if union else 0
        
        return similarity > 0.7  # 70% similar
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "exact_message": self.exact_message,
            "error_type": self.error_type.value,
            "location": self.location,
            "context_hash": self.context_hash,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "metadata": self.metadata
        }
    
    def __str__(self) -> str:
        """String representation."""
        location_str = f" at {self.location}" if self.location else ""
        return f"{self.error_type.value}: {self.exact_message[:100]}{location_str}"


def extract_failure_signature(
    error_output: str,
    agent_id: str,
    task_id: str
) -> FailureSignature:
    """
    Convenience function to extract failure signature from error output.
    
    Args:
        error_output: Raw error output (may include stack trace)
        agent_id: Agent that encountered the error
        task_id: Task being executed
    
    Returns:
        FailureSignature instance
    """
    # Try to split error output into message and stack trace
    lines = error_output.strip().split('\n')
    
    # Last non-empty line is usually the error message
    error_message = next((line for line in reversed(lines) if line.strip()), error_output)
    
    # Everything else is stack trace
    stack_trace = '\n'.join(lines[:-1]) if len(lines) > 1 else None
    
    return FailureSignature.from_error(
        error_message=error_message,
        agent_id=agent_id,
        task_id=task_id,
        stack_trace=stack_trace
    )
