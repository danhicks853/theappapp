"""
Timeout Monitor Service

Monitors agent tasks for timeouts and triggers gates when tasks exceed time limits.
Prevents agents from running indefinitely on stuck tasks.

Reference: Section 1.4 - Failure Handling & Recovery
"""
import logging
import asyncio
from datetime import datetime, UTC
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TaskMonitor:
    """Represents a monitored task."""
    task_id: str
    agent_id: str
    started_at: datetime
    timeout_seconds: int
    on_timeout: Optional[Callable] = None
    metadata: Dict[str, Any] = None


class TimeoutMonitor:
    """
    Monitors agent tasks for timeouts and triggers gates.
    
    Features:
    - Configurable timeouts per agent type
    - Automatic gate creation on timeout
    - Non-blocking monitoring
    - Task cancellation support
    
    Example:
        monitor = TimeoutMonitor(gate_manager)
        
        # Start monitoring a task
        await monitor.monitor_task(
            task_id="task-123",
            agent_id="backend-1",
            timeout_seconds=600,  # 10 minutes
            on_timeout=lambda: create_gate("Task timeout")
        )
        
        # Task completes
        monitor.complete_task("task-123")
    """
    
    # Default timeouts by agent type (in seconds)
    DEFAULT_TIMEOUTS = {
        "orchestrator": 1800,        # 30 minutes
        "backend_developer": 900,    # 15 minutes
        "frontend_developer": 900,   # 15 minutes
        "qa_engineer": 600,          # 10 minutes
        "security_expert": 1200,     # 20 minutes
        "devops_engineer": 1800,     # 30 minutes
        "documentation_expert": 600, # 10 minutes
        "uiux_designer": 900,        # 15 minutes
        "github_specialist": 600,    # 10 minutes
        "workshopper": 900,          # 15 minutes
        "project_manager": 600,      # 10 minutes
    }
    
    def __init__(self, gate_manager=None):
        """Initialize timeout monitor."""
        self.gate_manager = gate_manager
        self._active_monitors: Dict[str, TaskMonitor] = {}
        self._check_interval = 10  # Check every 10 seconds
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        logger.info("TimeoutMonitor initialized")
    
    async def start(self):
        """Start the monitoring loop."""
        if self._running:
            logger.warning("TimeoutMonitor already running")
            return
        
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitor_loop())
        logger.info("TimeoutMonitor started")
    
    async def stop(self):
        """Stop the monitoring loop."""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("TimeoutMonitor stopped")
    
    async def monitor_task(
        self,
        task_id: str,
        agent_id: str,
        agent_type: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        on_timeout: Optional[Callable] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Start monitoring a task for timeout.
        
        Args:
            task_id: Unique task identifier
            agent_id: Agent executing the task
            agent_type: Type of agent (for default timeout)
            timeout_seconds: Override timeout (uses default if None)
            on_timeout: Optional callback when timeout occurs
            metadata: Additional context about the task
        """
        # Determine timeout
        if timeout_seconds is None:
            timeout_seconds = self.DEFAULT_TIMEOUTS.get(agent_type, 600)  # 10 min default
        
        monitor = TaskMonitor(
            task_id=task_id,
            agent_id=agent_id,
            started_at=datetime.now(UTC),
            timeout_seconds=timeout_seconds,
            on_timeout=on_timeout,
            metadata=metadata or {}
        )
        
        self._active_monitors[task_id] = monitor
        
        logger.info(
            "Monitoring task | task_id=%s | agent=%s | timeout=%ds",
            task_id,
            agent_id,
            timeout_seconds
        )
        
        # Start monitoring loop if not already running
        if not self._running:
            await self.start()
    
    def complete_task(self, task_id: str) -> None:
        """
        Mark a task as completed and stop monitoring.
        
        Args:
            task_id: Task that completed
        """
        if task_id in self._active_monitors:
            monitor = self._active_monitors.pop(task_id)
            elapsed = (datetime.now(UTC) - monitor.started_at).total_seconds()
            
            logger.info(
                "Task completed | task_id=%s | elapsed=%.1fs | timeout=%ds",
                task_id,
                elapsed,
                monitor.timeout_seconds
            )
    
    def get_active_count(self) -> int:
        """Get count of actively monitored tasks."""
        return len(self._active_monitors)
    
    def get_task_elapsed(self, task_id: str) -> Optional[float]:
        """Get elapsed time for a task in seconds."""
        monitor = self._active_monitors.get(task_id)
        if monitor:
            return (datetime.now(UTC) - monitor.started_at).total_seconds()
        return None
    
    async def _monitor_loop(self):
        """Main monitoring loop that checks for timeouts."""
        while self._running:
            try:
                await self._check_timeouts()
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in monitoring loop: %s", e)
                await asyncio.sleep(self._check_interval)
    
    async def _check_timeouts(self):
        """Check all monitored tasks for timeouts."""
        now = datetime.now(UTC)
        timed_out = []
        
        for task_id, monitor in self._active_monitors.items():
            elapsed = (now - monitor.started_at).total_seconds()
            
            if elapsed >= monitor.timeout_seconds:
                timed_out.append((task_id, monitor, elapsed))
        
        # Handle timeouts
        for task_id, monitor, elapsed in timed_out:
            await self._handle_timeout(task_id, monitor, elapsed)
    
    async def _handle_timeout(
        self,
        task_id: str,
        monitor: TaskMonitor,
        elapsed: float
    ):
        """Handle a timed-out task."""
        logger.warning(
            "Task timeout detected | task_id=%s | agent=%s | elapsed=%.1fs | timeout=%ds",
            task_id,
            monitor.agent_id,
            elapsed,
            monitor.timeout_seconds
        )
        
        # Remove from active monitors
        self._active_monitors.pop(task_id, None)
        
        # Call custom timeout handler if provided
        if monitor.on_timeout:
            try:
                if asyncio.iscoroutinefunction(monitor.on_timeout):
                    await monitor.on_timeout()
                else:
                    monitor.on_timeout()
            except Exception as e:
                logger.error("Error in timeout callback: %s", e)
        
        # Create gate via gate_manager
        if self.gate_manager:
            try:
                gate_id = await self._create_timeout_gate(monitor, elapsed)
                logger.info(
                    "Timeout gate created | task_id=%s | gate_id=%s",
                    task_id,
                    gate_id
                )
            except Exception as e:
                logger.error("Failed to create timeout gate: %s", e)
    
    async def _create_timeout_gate(
        self,
        monitor: TaskMonitor,
        elapsed: float
    ) -> str:
        """Create a gate for the timeout."""
        reason = f"Task timeout after {elapsed:.1f} seconds (limit: {monitor.timeout_seconds}s)"
        
        context = {
            "task_id": monitor.task_id,
            "agent_id": monitor.agent_id,
            "elapsed_seconds": elapsed,
            "timeout_seconds": monitor.timeout_seconds,
            "started_at": monitor.started_at.isoformat(),
            "timeout_type": "task_timeout",
            **(monitor.metadata or {})
        }
        
        if hasattr(self.gate_manager, 'create_gate'):
            # Sync or async call
            result = self.gate_manager.create_gate(
                project_id=context.get("project_id", "unknown"),
                reason=reason,
                context=context,
                agent_id=monitor.agent_id,
                gate_type="timeout"
            )
            
            # Await if coroutine
            if asyncio.iscoroutine(result):
                return await result
            return result
        
        # Fallback: return a UUID
        import uuid
        return str(uuid.uuid4())
    
    def get_monitor_stats(self) -> Dict[str, Any]:
        """Get statistics about monitored tasks."""
        now = datetime.now(UTC)
        
        stats = {
            "active_count": len(self._active_monitors),
            "running": self._running,
            "tasks": []
        }
        
        for task_id, monitor in self._active_monitors.items():
            elapsed = (now - monitor.started_at).total_seconds()
            remaining = monitor.timeout_seconds - elapsed
            
            stats["tasks"].append({
                "task_id": task_id,
                "agent_id": monitor.agent_id,
                "elapsed_seconds": elapsed,
                "remaining_seconds": max(0, remaining),
                "timeout_seconds": monitor.timeout_seconds,
                "progress_pct": min(100, (elapsed / monitor.timeout_seconds) * 100)
            })
        
        return stats
