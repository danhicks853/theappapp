"""
Sandbox Monitor Service

Monitors and logs all container/sandbox activity for AI operations.
Tracks resource usage, command execution, and errors.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class CommandExecution:
    """Record of a command execution."""
    timestamp: str
    task_id: str
    project_id: str
    agent_id: str
    command: str
    exit_code: int
    stdout_length: int
    stderr_length: int
    duration_ms: float
    success: bool


class SandboxMonitor:
    """
    Monitors sandbox/container activity.
    
    Features:
    - Log all command executions
    - Track resource usage
    - Alert on anomalies
    - Maintain execution history
    """
    
    def __init__(self):
        """Initialize the SandboxMonitor."""
        self.execution_history: list[CommandExecution] = []
        self.max_history = 1000  # Keep last 1000 executions in memory
        logger.info("SandboxMonitor initialized")
    
    def log_command_execution(
        self,
        task_id: str,
        project_id: str,
        agent_id: str,
        command: str,
        exit_code: int,
        stdout: str,
        stderr: str,
        duration_ms: float
    ):
        """
        Log a command execution.
        
        Args:
            task_id: Task identifier
            project_id: Project identifier
            agent_id: Agent identifier
            command: Command that was executed
            exit_code: Command exit code
            stdout: Standard output
            stderr: Standard error
            duration_ms: Execution duration in milliseconds
        """
        execution = CommandExecution(
            timestamp=datetime.utcnow().isoformat(),
            task_id=task_id,
            project_id=project_id,
            agent_id=agent_id,
            command=command[:500],  # Truncate long commands
            exit_code=exit_code,
            stdout_length=len(stdout),
            stderr_length=len(stderr),
            duration_ms=duration_ms,
            success=(exit_code == 0)
        )
        
        # Add to history
        self.execution_history.append(execution)
        
        # Trim history if too large
        if len(self.execution_history) > self.max_history:
            self.execution_history = self.execution_history[-self.max_history:]
        
        # Log to standard logger
        log_level = logging.INFO if execution.success else logging.WARNING
        logger.log(
            log_level,
            f"Command execution: task={task_id}, exit={exit_code}, "
            f"duration={duration_ms:.2f}ms, stdout={len(stdout)}b, stderr={len(stderr)}b"
        )
        
        # Alert on errors
        if exit_code != 0:
            self._alert_on_error(execution, stderr)
    
    def _alert_on_error(self, execution: CommandExecution, stderr: str):
        """
        Alert on command execution errors.
        
        Args:
            execution: Command execution record
            stderr: Standard error output
        """
        # Log error details
        logger.error(
            f"Command failed: task={execution.task_id}, "
            f"exit_code={execution.exit_code}, "
            f"stderr_preview={stderr[:200]}"
        )
        
        # Check for critical errors
        critical_patterns = [
            "segmentation fault",
            "out of memory",
            "killed",
            "core dumped",
            "permission denied"
        ]
        
        stderr_lower = stderr.lower()
        for pattern in critical_patterns:
            if pattern in stderr_lower:
                logger.critical(
                    f"CRITICAL ERROR in task {execution.task_id}: "
                    f"Detected '{pattern}' in stderr"
                )
                break
    
    def get_task_execution_history(
        self,
        task_id: str
    ) -> list[Dict[str, Any]]:
        """
        Get execution history for a specific task.
        
        Args:
            task_id: Task identifier
        
        Returns:
            List of execution records
        """
        history = [
            asdict(exec)
            for exec in self.execution_history
            if exec.task_id == task_id
        ]
        
        logger.info(f"Retrieved {len(history)} executions for task {task_id}")
        return history
    
    def get_project_execution_history(
        self,
        project_id: str
    ) -> list[Dict[str, Any]]:
        """
        Get execution history for a specific project.
        
        Args:
            project_id: Project identifier
        
        Returns:
            List of execution records
        """
        history = [
            asdict(exec)
            for exec in self.execution_history
            if exec.project_id == project_id
        ]
        
        logger.info(f"Retrieved {len(history)} executions for project {project_id}")
        return history
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics.
        
        Returns:
            dict: Statistics about command executions
        """
        if not self.execution_history:
            return {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "success_rate": 0.0,
                "average_duration_ms": 0.0
            }
        
        total = len(self.execution_history)
        successful = sum(1 for e in self.execution_history if e.success)
        failed = total - successful
        
        avg_duration = sum(e.duration_ms for e in self.execution_history) / total
        
        return {
            "total_executions": total,
            "successful_executions": successful,
            "failed_executions": failed,
            "success_rate": (successful / total) * 100,
            "average_duration_ms": avg_duration,
            "history_size": len(self.execution_history),
            "max_history": self.max_history
        }
    
    def log_container_lifecycle_event(
        self,
        event_type: str,
        task_id: str,
        project_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log container lifecycle events.
        
        Args:
            event_type: Type of event (created, destroyed, etc.)
            task_id: Task identifier
            project_id: Project identifier
            details: Additional event details
        """
        logger.info(
            f"Container lifecycle: {event_type}, "
            f"task={task_id}, project={project_id}, "
            f"details={details or {}}"
        )
    
    def check_resource_limits(
        self,
        task_id: str
    ) -> Dict[str, Any]:
        """
        Check if a task is hitting resource limits.
        
        Args:
            task_id: Task identifier
        
        Returns:
            dict: Resource limit status
        """
        # Get executions for this task
        task_execs = [
            e for e in self.execution_history
            if e.task_id == task_id
        ]
        
        if not task_execs:
            return {
                "task_id": task_id,
                "warnings": [],
                "status": "ok"
            }
        
        warnings = []
        
        # Check for excessive failures
        recent_execs = task_execs[-10:]  # Last 10 executions
        if len(recent_execs) >= 5:
            failure_rate = sum(1 for e in recent_execs if not e.success) / len(recent_execs)
            if failure_rate > 0.5:
                warnings.append(f"High failure rate: {failure_rate * 100:.1f}%")
        
        # Check for slow executions
        avg_duration = sum(e.duration_ms for e in task_execs) / len(task_execs)
        if avg_duration > 30000:  # 30 seconds
            warnings.append(f"Slow execution average: {avg_duration:.0f}ms")
        
        # Check for excessive executions
        if len(task_execs) > 100:
            warnings.append(f"High execution count: {len(task_execs)}")
        
        status = "warning" if warnings else "ok"
        
        if warnings:
            logger.warning(f"Task {task_id} resource warnings: {warnings}")
        
        return {
            "task_id": task_id,
            "warnings": warnings,
            "status": status,
            "execution_count": len(task_execs),
            "average_duration_ms": avg_duration
        }


# Singleton instance
_sandbox_monitor: Optional[SandboxMonitor] = None


def get_sandbox_monitor() -> SandboxMonitor:
    """Get singleton SandboxMonitor instance."""
    global _sandbox_monitor
    
    if _sandbox_monitor is None:
        _sandbox_monitor = SandboxMonitor()
    
    return _sandbox_monitor
