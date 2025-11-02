"""Loop detection service for agent execution loops.

Implements the lightweight detection strategy mandated by Decision 74:
Loop Detection Algorithm. The detector focuses on identifying three
consecutive identical failures per task within sub-millisecond
thresholds to prevent fake agent loops while maintaining low runtime
overhead.

Enhanced with gate triggering support for Section 1.4.
"""

from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, UTC
from typing import Deque, Dict, Iterable, List, Optional, Any

from backend.models.agent_state import TaskState

logger = logging.getLogger(__name__)

_LOOP_WINDOW = 3


class LoopDetector:
    """Detect repeated failure patterns for task execution loops.

    The detector maintains a bounded history of error signatures per task
    and flags a loop when the last three signatures are identical. It is
    intentionally lightweight (<1ms operations) so it can run on every
    iteration without impacting agent responsiveness.
    """

    def __init__(self, window_size: int = _LOOP_WINDOW, gate_manager=None) -> None:
        self.window_size = window_size
        self._failures: Dict[str, Deque[str]] = {}
        self.gate_manager = gate_manager
        self._loop_events: Dict[str, Dict[str, Any]] = {}  # Track loop events

    def record_failure(self, task_id: str, signature: Optional[str]) -> None:
        """Record a failure signature for the specified task."""

        if not signature:
            return

        history = self._failures.setdefault(
            task_id, deque(maxlen=self.window_size)
        )
        history.append(signature)

    def record_success(self, task_id: str) -> None:
        """Clear failure history on successful progress."""

        self._failures.pop(task_id, None)

    def reset(self, task_id: str) -> None:
        """Explicitly reset loop tracking for a task."""

        self._failures.pop(task_id, None)

    def is_looping(self, state: TaskState) -> bool:
        """Return True if the task state indicates a loop condition."""

        recent = list(self._failures.get(state.task_id, []))
        if len(recent) < self.window_size:
            recent = _tail(state.last_errors, self.window_size)

        return len(recent) == self.window_size and len(set(recent)) == 1
    
    async def check_and_trigger_gate(
        self,
        task_id: str,
        agent_id: str,
        project_id: str,
        error_signature: str
    ) -> Optional[str]:
        """
        Check for loop and trigger gate if detected.
        
        This is the enhanced method for Section 1.4.1 that automatically
        creates gates when loops are detected.
        
        Args:
            task_id: Task being executed
            agent_id: Agent executing the task
            project_id: Project context
            error_signature: Current error signature
        
        Returns:
            Gate ID if loop detected and gate created, None otherwise
        """
        # Record the failure
        self.record_failure(task_id, error_signature)
        
        # Check if we're in a loop
        recent = list(self._failures.get(task_id, []))
        is_loop = len(recent) == self.window_size and len(set(recent)) == 1
        
        if not is_loop:
            return None
        
        # Loop detected!
        logger.warning(
            "Loop detected | task_id=%s | agent=%s | signature=%s",
            task_id,
            agent_id,
            error_signature[:50]
        )
        
        # Check if we already created a gate for this loop
        if task_id in self._loop_events:
            event = self._loop_events[task_id]
            if event.get("gate_id"):
                logger.info("Gate already exists for this loop | gate_id=%s", event["gate_id"])
                return event["gate_id"]
        
        # Create gate via gate_manager
        gate_id = None
        if self.gate_manager:
            try:
                gate_id = await self._create_loop_gate(
                    task_id=task_id,
                    agent_id=agent_id,
                    project_id=project_id,
                    error_signature=error_signature
                )
                
                # Track the loop event
                self._loop_events[task_id] = {
                    "gate_id": gate_id,
                    "detected_at": datetime.now(UTC),
                    "signature": error_signature,
                    "agent_id": agent_id
                }
                
                logger.info(
                    "Loop gate created | task_id=%s | gate_id=%s",
                    task_id,
                    gate_id
                )
            except Exception as e:
                logger.error("Failed to create loop gate: %s", e)
        
        return gate_id
    
    async def _create_loop_gate(
        self,
        task_id: str,
        agent_id: str,
        project_id: str,
        error_signature: str
    ) -> str:
        """Create a gate for detected loop."""
        reason = f"Agent loop detected after {self.window_size} identical failures"
        
        context = {
            "task_id": task_id,
            "agent_id": agent_id,
            "loop_type": "execution_loop",
            "window_size": self.window_size,
            "error_signature": error_signature[:200],  # Limit size
            "detected_at": datetime.now(UTC).isoformat()
        }
        
        if hasattr(self.gate_manager, 'create_gate'):
            import asyncio
            # Sync or async call
            result = self.gate_manager.create_gate(
                project_id=project_id,
                reason=reason,
                context=context,
                agent_id=agent_id,
                gate_type="loop_detected"
            )
            
            # Await if coroutine
            if asyncio.iscoroutine(result):
                return await result
            return result
        
        # Fallback: return a UUID
        import uuid
        return str(uuid.uuid4())
    
    def get_loop_stats(self) -> Dict[str, Any]:
        """Get statistics about detected loops."""
        return {
            "active_tasks": len(self._failures),
            "detected_loops": len(self._loop_events),
            "window_size": self.window_size,
            "loop_events": [
                {
                    "task_id": task_id,
                    "gate_id": event["gate_id"],
                    "detected_at": event["detected_at"].isoformat(),
                    "agent_id": event["agent_id"]
                }
                for task_id, event in self._loop_events.items()
            ]
        }


def _tail(values: Iterable[str], size: int) -> List[str]:
    """Return the last ``size`` values from ``values`` as a list."""

    if size <= 0:
        return []

    if isinstance(values, list):
        return values[-size:]

    buffer: Deque[str] = deque(maxlen=size)
    for value in values:
        buffer.append(value)
    return list(buffer)


__all__ = ["LoopDetector"]
