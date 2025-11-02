"""
Loop Detection Service

Enhanced loop detection with edge case handling, monitoring, and metrics.
Wraps the core LoopDetector with additional features for production use.

Reference: Section 1.4.1 - Loop Detection Algorithm
"""
import logging
from datetime import datetime, UTC
from typing import Dict, Any, Optional, List
from collections import defaultdict
from enum import Enum

from backend.services.loop_detector import LoopDetector
from backend.models.failure_signature import FailureSignature, ErrorType

logger = logging.getLogger(__name__)


class FailureCategory(str, Enum):
    """Categories of failures for edge case handling."""
    INTERNAL = "internal"  # Code/logic errors
    EXTERNAL = "external"  # API, network, database failures
    INTERMITTENT = "intermittent"  # Sometimes works, sometimes fails
    DEGRADING = "degrading"  # Different errors each time


class LoopDetectionService:
    """
    Production loop detection service with edge case handling and metrics.
    
    Features:
    - Edge case detection (external failures, progressive degradation)
    - Loop metrics and monitoring
    - Failure categorization
    - Statistics tracking
    
    Example:
        service = LoopDetectionService(gate_manager)
        
        # Record a failure
        result = await service.record_failure(
            task_id="task-123",
            agent_id="backend-1",
            error_signature=signature,
            error_output=error_text
        )
        
        if result["loop_detected"]:
            print(f"Loop! Gate: {result['gate_id']}")
    """
    
    def __init__(self, gate_manager=None):
        """Initialize loop detection service."""
        self.detector = LoopDetector(gate_manager=gate_manager)
        
        # Metrics tracking
        self._total_loops_detected = 0
        self._loops_by_agent_type: Dict[str, int] = defaultdict(int)
        self._loops_by_error_type: Dict[str, int] = defaultdict(int)
        self._loop_resolutions: List[Dict[str, Any]] = []
        
        # Edge case tracking
        self._external_failures: Dict[str, List[str]] = defaultdict(list)
        self._failure_categories: Dict[str, FailureCategory] = {}
        
        logger.info("LoopDetectionService initialized")
    
    async def record_failure(
        self,
        task_id: str,
        agent_id: str,
        error_signature: str,
        error_output: str,
        *,
        agent_type: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record a failure with edge case detection.
        
        Args:
            task_id: Task that failed
            agent_id: Agent that encountered error
            error_signature: Error signature/hash
            error_output: Full error output
            agent_type: Type of agent
            project_id: Project context
        
        Returns:
            Dict with loop_detected, category, gate_id (if loop)
        """
        # Categorize the failure
        failure_sig = FailureSignature.from_error(
            error_message=error_output,
            agent_id=agent_id,
            task_id=task_id
        )
        
        category = self._categorize_failure(failure_sig)
        
        # Handle based on category
        if category == FailureCategory.EXTERNAL:
            # Don't count external failures as loops
            self._external_failures[task_id].append(error_signature)
            
            logger.info(
                "External failure recorded (not loop) | task_id=%s | error=%s",
                task_id,
                failure_sig.error_type.value
            )
            
            return {
                "loop_detected": False,
                "category": category.value,
                "gate_id": None,
                "reason": "External failure - not counted as loop"
            }
        
        elif category == FailureCategory.DEGRADING:
            # Progressive degradation - reset counter
            self.detector.reset(task_id)
            
            logger.info(
                "Progressive degradation detected, resetting | task_id=%s",
                task_id
            )
            
            return {
                "loop_detected": False,
                "category": category.value,
                "gate_id": None,
                "reason": "Different errors - progressive degradation"
            }
        
        # For internal/intermittent failures, check for loop
        gate_id = await self.detector.check_and_trigger_gate(
            task_id=task_id,
            agent_id=agent_id,
            project_id=project_id or "unknown",
            error_signature=error_signature
        )
        
        if gate_id:
            # Loop detected!
            self._record_loop_metrics(
                agent_id=agent_id,
                agent_type=agent_type,
                error_type=failure_sig.error_type.value
            )
            
            return {
                "loop_detected": True,
                "category": category.value,
                "gate_id": gate_id,
                "reason": "Loop detected after 3 identical failures"
            }
        
        return {
            "loop_detected": False,
            "category": category.value,
            "gate_id": None,
            "reason": "Failure recorded, not yet a loop"
        }
    
    def _categorize_failure(self, failure_sig: FailureSignature) -> FailureCategory:
        """
        Categorize failure for edge case handling.
        
        Categories:
        - EXTERNAL: Network, API, database connection errors
        - INTERMITTENT: Same error but not consistent
        - DEGRADING: Different errors each attempt
        - INTERNAL: Code/logic errors (default)
        """
        # Check error type for external failures
        external_types = {
            ErrorType.CONNECTION_ERROR,
            ErrorType.HTTP_ERROR,
            ErrorType.TIMEOUT_ERROR,
            ErrorType.DATABASE_ERROR
        }
        
        if failure_sig.error_type in external_types:
            return FailureCategory.EXTERNAL
        
        # Check for intermittent patterns
        # (Would need more history to determine - simplified for now)
        
        # Check for progressive degradation
        # (Would need to compare with recent errors - simplified for now)
        
        # Default: internal error
        return FailureCategory.INTERNAL
    
    def _record_loop_metrics(
        self,
        agent_id: str,
        agent_type: Optional[str],
        error_type: str
    ) -> None:
        """Record metrics for detected loop."""
        self._total_loops_detected += 1
        
        if agent_type:
            self._loops_by_agent_type[agent_type] += 1
        
        self._loops_by_error_type[error_type] += 1
        
        logger.info(
            "Loop metrics updated | total=%d | agent_type=%s | error_type=%s",
            self._total_loops_detected,
            agent_type,
            error_type
        )
    
    def record_loop_resolution(
        self,
        task_id: str,
        agent_id: str,
        resolution: str,
        *,
        iterations_to_resolve: int,
        time_to_resolve_seconds: float
    ) -> None:
        """
        Record how a loop was resolved.
        
        Args:
            task_id: Task that was looping
            agent_id: Agent that was looping
            resolution: How it was resolved (e.g., "human_intervention", "code_fix")
            iterations_to_resolve: How many iterations in loop
            time_to_resolve_seconds: Time from detection to resolution
        """
        self._loop_resolutions.append({
            "task_id": task_id,
            "agent_id": agent_id,
            "resolution": resolution,
            "iterations": iterations_to_resolve,
            "time_seconds": time_to_resolve_seconds,
            "resolved_at": datetime.now(UTC)
        })
        
        logger.info(
            "Loop resolution recorded | task_id=%s | resolution=%s | iterations=%d",
            task_id,
            resolution,
            iterations_to_resolve
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get loop detection metrics.
        
        Returns:
            Dict with comprehensive loop metrics
        """
        # Calculate average resolution time
        avg_resolution_time = 0.0
        avg_iterations = 0.0
        
        if self._loop_resolutions:
            avg_resolution_time = sum(
                r["time_seconds"] for r in self._loop_resolutions
            ) / len(self._loop_resolutions)
            
            avg_iterations = sum(
                r["iterations"] for r in self._loop_resolutions
            ) / len(self._loop_resolutions)
        
        # Get detector stats
        detector_stats = self.detector.get_loop_stats()
        
        return {
            "total_loops_detected": self._total_loops_detected,
            "loops_by_agent_type": dict(self._loops_by_agent_type),
            "loops_by_error_type": dict(self._loops_by_error_type),
            "active_tasks": detector_stats["active_tasks"],
            "currently_detected_loops": detector_stats["detected_loops"],
            "total_external_failures": sum(len(v) for v in self._external_failures.values()),
            "resolved_loops": len(self._loop_resolutions),
            "average_resolution_time_seconds": avg_resolution_time,
            "average_iterations_to_resolve": avg_iterations,
            "recent_resolutions": self._loop_resolutions[-10:]  # Last 10
        }
    
    def get_loop_events(self) -> List[Dict[str, Any]]:
        """Get all detected loop events."""
        stats = self.detector.get_loop_stats()
        return stats.get("loop_events", [])
    
    def reset_task(self, task_id: str) -> None:
        """Reset loop detection for a task."""
        self.detector.reset(task_id)
        
        # Clear external failures
        self._external_failures.pop(task_id, None)
        self._failure_categories.pop(task_id, None)
        
        logger.info("Loop detection reset | task_id=%s", task_id)
