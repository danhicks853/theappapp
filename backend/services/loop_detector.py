"""Loop detection service for agent execution loops.

Implements the lightweight detection strategy mandated by Decision 74:
Loop Detection Algorithm. The detector focuses on identifying three
consecutive identical failures per task within sub-millisecond
thresholds to prevent fake agent loops while maintaining low runtime
overhead.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, Dict, Iterable, List, Optional

from backend.models.agent_state import TaskState

_LOOP_WINDOW = 3


class LoopDetector:
    """Detect repeated failure patterns for task execution loops.

    The detector maintains a bounded history of error signatures per task
    and flags a loop when the last three signatures are identical. It is
    intentionally lightweight (<1ms operations) so it can run on every
    iteration without impacting agent responsiveness.
    """

    def __init__(self, window_size: int = _LOOP_WINDOW) -> None:
        self.window_size = window_size
        self._failures: Dict[str, Deque[str]] = {}

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
