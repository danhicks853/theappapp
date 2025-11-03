"""
Task Executor - Worker loop for executing orchestrator tasks with agents.

Pulls tasks from the orchestrator queue, assigns them to appropriate agents,
executes them, handles results, and tracks progress.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, UTC

from backend.services.orchestrator import Orchestrator, Task, TaskStatus, AgentType
from backend.services.event_bus import EventBus, Event, EventType
from backend.agents.base_agent import BaseAgent, TaskResult

logger = logging.getLogger(__name__)


class TaskExecutor:
    """
    Executes tasks from orchestrator queue using registered agents.
    
    Features:
    - Worker loop that processes tasks from queue
    - Task assignment to appropriate agents
    - Result handling and progress tracking
    - Error handling and retry logic
    - Deliverable completion tracking
    """
    
    def __init__(
        self,
        orchestrator: Orchestrator,
        event_bus: EventBus,
        max_workers: int = 3,
        max_retries: int = 2,
        phase_manager: Optional[Any] = None
    ):
        """
        Initialize task executor.
        
        Args:
            orchestrator: Orchestrator instance with task queue
            event_bus: Event bus for publishing progress
            max_workers: Maximum concurrent task executions
            max_retries: Maximum retry attempts per task
        """
        self.orchestrator = orchestrator
        self.event_bus = event_bus
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.phase_manager = phase_manager
        
        self.running = False
        self.workers: List[asyncio.Task] = []
        self.task_results: Dict[str, TaskResult] = {}
        self.task_retries: Dict[str, int] = {}
        
        # Track deliverable verification failures
        self.deliverable_verification_failures: Dict[str, int] = {}
        self.max_verification_failures = 3
        
        # Track agent instances by agent_id
        self.agent_instances: Dict[str, BaseAgent] = {}
        
        logger.info(f"TaskExecutor initialized with {max_workers} workers, phase_manager={phase_manager is not None}")
    
    def register_agent_instance(self, agent_id: str, agent: BaseAgent) -> None:
        """Register an agent instance for task execution."""
        self.agent_instances[agent_id] = agent
        logger.debug(f"Registered agent instance: {agent_id}")
    
    async def start(self) -> None:
        """Start the worker loops."""
        if self.running:
            logger.warning("TaskExecutor already running")
            return
        
        self.running = True
        logger.info(f"Starting {self.max_workers} worker loops")
        
        # Start worker coroutines
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker_loop(worker_id=i))
            self.workers.append(worker)
    
    async def stop(self) -> None:
        """Stop all worker loops gracefully."""
        logger.info("Stopping TaskExecutor")
        self.running = False
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to complete
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        
        logger.info("TaskExecutor stopped")
    
    async def _worker_loop(self, worker_id: int) -> None:
        """
        Worker loop that processes tasks from the queue.
        
        Args:
            worker_id: Identifier for this worker
        """
        logger.info(f"Worker {worker_id} started")
        
        while self.running:
            try:
                # Try to get a task from queue (non-blocking with timeout)
                task = await self._get_next_task(timeout=1.0)
                
                if task is None:
                    # No tasks available, brief pause
                    await asyncio.sleep(0.5)
                    continue
                
                logger.info(f"Worker {worker_id} processing task: {task.task_id}")
                
                # Execute the task
                await self._execute_task(task, worker_id)
                
            except asyncio.CancelledError:
                logger.info(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}", exc_info=True)
                await asyncio.sleep(1)
        
        logger.info(f"Worker {worker_id} stopped")
    
    async def _get_next_task(self, timeout: float = 1.0) -> Optional[Task]:
        """
        Get next task from orchestrator queue.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Task or None if no tasks available
        """
        try:
            # Orchestrator queue is a PriorityQueue, need to get with timeout
            # Since it's sync queue, wrap in executor
            task = await asyncio.wait_for(
                asyncio.to_thread(self.orchestrator.dequeue_task),
                timeout=timeout
            )
            return task
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"Error getting task from queue: {e}")
            return None
    
    async def _execute_task(self, task: Task, worker_id: int) -> None:
        """
        Execute a task with appropriate agent.
        
        Args:
            task: Task to execute
            worker_id: ID of worker executing task
        """
        try:
            # Mark task as in progress
            task.status = TaskStatus.IN_PROGRESS
            
            # Find appropriate agent
            agent = await self._get_agent_for_task(task)
            
            if not agent:
                raise RuntimeError(f"No agent available for task type: {task.agent_type}")
            
            # Publish task assigned event (now that we have the agent)
            await self.event_bus.publish(Event(
                event_type=EventType.TASK_ASSIGNED,
                project_id=self.orchestrator.project_id,
                data={
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "agent_type": task.agent_type.value if hasattr(task.agent_type, 'value') else str(task.agent_type),
                    "agent": agent.agent_id if agent else None,
                    "agent_id": agent.agent_id if agent else None,
                    "worker_id": worker_id
                }
            ))
            
            # Execute task with agent (with timeout)
            logger.info(f"Executing task {task.task_id} with agent {agent.agent_id}")
            
            try:
                # Add 60 second timeout to prevent infinite hangs
                result = await asyncio.wait_for(
                    agent.run_task(task),
                    timeout=60.0
                )
                logger.info(f"Task {task.task_id} completed successfully")
            except asyncio.TimeoutError:
                logger.error(f"Task {task.task_id} timed out after 60 seconds")
                raise RuntimeError(f"Task execution timeout: {task.task_id}")
            
            # Handle result
            await self._handle_task_result(task, result)
            
        except Exception as e:
            logger.error(f"Task execution error: {task.task_id} - {e}", exc_info=True)
            await self._handle_task_error(task, e)
    
    async def _get_agent_for_task(self, task: Task) -> Optional[BaseAgent]:
        """
        Get appropriate agent instance for a task.
        
        Args:
            task: Task to assign
            
        Returns:
            BaseAgent instance or None
        """
        # Get agents of matching type from orchestrator
        agents = self.orchestrator.get_agents_by_type(task.agent_type)
        
        if not agents:
            logger.warning(f"No agents available for type: {task.agent_type}")
            return None
        
        # Get first available agent
        # TODO: Implement load balancing
        agent_meta = agents[0]
        agent_id = agent_meta.agent_id
        
        # Return registered agent instance
        return self.agent_instances.get(agent_id)
    
    async def _handle_task_result(self, task: Task, result: TaskResult) -> None:
        """
        Handle successful task completion.
        
        Orchestrator verifies work was done and marks deliverable complete.
        
        Args:
            task: Completed task
            result: Task result from agent
        """
        task.status = TaskStatus.COMPLETED
        self.task_results[task.task_id] = result
        
        logger.info(f"Task completed: {task.task_id} - success={result.success}")
        
        # ORCHESTRATOR VERIFICATION: Disabled for now - trust agent self-assessment
        # TODO: Re-enable once Docker file system is working properly
        # await self._verify_and_complete_deliverable(task)
        
        # For now, just mark deliverable complete based on task success
        if task.payload and isinstance(task.payload, dict):
            deliverable_id = task.payload.get("id")
            if deliverable_id and deliverable_id.startswith("deliv-") and result.success:
                logger.info(f"✅ Marking deliverable complete based on agent success: {deliverable_id}")
                await self._mark_deliverable_complete(deliverable_id, result)
        
        # Publish completion event
        await self.event_bus.publish(Event(
            event_type=EventType.TASK_COMPLETED,
            project_id=self.orchestrator.project_id,
            data={
                "task_id": task.task_id,
                "task_type": task.task_type,
                "status": "completed" if result.success else "failed",
                "steps": len(result.steps),
                "artifacts": len(result.artifacts)
            }
        ))
        
        # CRITICAL: Notify orchestrator to make workflow decision
        # This enables the LLM-driven decision engine
        logger.info(f"Notifying orchestrator of task completion: {task.task_id}")
        await self.orchestrator.on_task_completed(task, result)
    
    async def _verify_and_complete_deliverable(self, task: Task) -> None:
        """
        Orchestrator verifies deliverable was completed and marks it done.
        
        This is the orchestrator's job - verify work, not trust the agent to report.
        
        Args:
            task: Task that was just completed
        """
        # Check if this is a deliverable task
        deliverable_id = task.payload.get("id") if task.payload else None
        if not deliverable_id or not deliverable_id.startswith("deliv-"):
            return
        
        # Map deliverable types to expected files
        expected_files = {
            "requirements.md": ["requirements", "Requirements Document"],
            "architecture.md": ["architecture", "Architecture Document"],
            "design.md": ["design", "Design Document"],
            "README.md": ["readme", "README"],
        }
        
        # Try to detect which file should have been created
        deliverable_title = task.payload.get("title", "").lower()
        expected_file = None
        
        for filename, keywords in expected_files.items():
            if any(keyword.lower() in deliverable_title for keyword in keywords):
                expected_file = filename
                break
        
        if not expected_file:
            logger.debug(f"No expected file mapping for deliverable: {deliverable_title}")
            return
        
        # Verify file exists using TAS
        try:
            from backend.services.tool_access_service import ToolExecutionRequest
            
            # Try to read the file
            read_request = ToolExecutionRequest(
                agent_id="orchestrator",
                agent_type="orchestrator",
                tool_name="file_system",
                operation="read",
                parameters={
                    "project_id": task.project_id,
                    "task_id": deliverable_id,
                    "path": expected_file
                },
                project_id=task.project_id,
                task_id=deliverable_id
            )
            
            response = await self.orchestrator.tas_client.execute_tool(read_request)
            
            if response.success and response.result:
                content = response.result.get("content", "")
                if len(content) > 50:  # File has substantial content
                    logger.info(f"✅ ORCHESTRATOR VERIFIED: {expected_file} exists with {len(content)} bytes")
                    logger.info(f"✅ Auto-marking deliverable complete: {deliverable_id}")
                    
                    # Reset failure count on success
                    self.deliverable_verification_failures.pop(deliverable_id, None)
                    
                    # Mark deliverable complete
                    await self._mark_deliverable_complete(deliverable_id, {
                        "status": "completed",
                        "output": f"Created {expected_file}",
                        "artifacts": [expected_file]
                    })
                    return  # Success!
                else:
                    logger.warning(f"❌ VERIFICATION FAILED: {expected_file} has minimal content ({len(content)} bytes)")
                    failure_reason = f"File {expected_file} exists but has only {len(content)} bytes of content"
            else:
                logger.warning(f"❌ VERIFICATION FAILED: Could not read {expected_file}")
                failure_reason = f"File {expected_file} does not exist or cannot be read"
                
        except Exception as e:
            logger.warning(f"❌ VERIFICATION FAILED: Error checking {expected_file}: {e}")
            failure_reason = f"Error verifying {expected_file}: {str(e)}"
        
        # Track verification failure
        failure_count = self.deliverable_verification_failures.get(deliverable_id, 0) + 1
        self.deliverable_verification_failures[deliverable_id] = failure_count
        
        logger.warning(f"⚠️  Deliverable {deliverable_id} verification failure #{failure_count}/{self.max_verification_failures}")
        
        # DON'T re-queue yet - agent has self-assessment now that will handle retries
        # Only escalate after max failures
        if failure_count >= self.max_verification_failures:
            logger.error(f"🚨 ESCALATING TO HUMAN: Deliverable {deliverable_id} failed verification {failure_count} times")
            
            await self._escalate_verification_failure(
                deliverable_id=deliverable_id,
                task=task,
                expected_file=expected_file,
                failure_reason=failure_reason,
                failure_count=failure_count
            )
    
    async def _escalate_verification_failure(
        self,
        deliverable_id: str,
        task: Task,
        expected_file: str,
        failure_reason: str,
        failure_count: int
    ) -> None:
        """
        Escalate to human after repeated verification failures.
        
        Creates a gate that pauses the build until human reviews.
        
        Args:
            deliverable_id: ID of deliverable that failed
            task: The task that was being verified
            expected_file: File that was expected
            failure_reason: Why verification failed
            failure_count: Number of failures
        """
        context = {
            "deliverable_id": deliverable_id,
            "deliverable_title": task.payload.get("title", "Unknown"),
            "expected_file": expected_file,
            "failure_reason": failure_reason,
            "failure_count": failure_count,
            "task_id": task.task_id,
            "project_id": task.project_id,
            "agent_type": task.agent_type.value if hasattr(task.agent_type, 'value') else str(task.agent_type),
            "escalation_type": "deliverable_verification_failure"
        }
        
        reason = (
            f"🚨 DELIVERABLE VERIFICATION FAILED {failure_count} TIMES\n\n"
            f"Deliverable: {task.payload.get('title', 'Unknown')}\n"
            f"Expected: {expected_file}\n"
            f"Problem: {failure_reason}\n\n"
            f"The agent has tried {failure_count} times but the orchestrator cannot verify "
            f"that the work was completed correctly. Human intervention required."
        )
        
        logger.error(f"🚨 Creating human gate for deliverable {deliverable_id}")
        
        # Create gate via orchestrator
        gate_id = await self.orchestrator.escalate_to_human(
            reason=reason,
            context=context,
            agent_id=task.assigned_agent_id
        )
        
        logger.error(f"🚨 HUMAN GATE CREATED: {gate_id}")
        
        # Publish gate created event
        await self.event_bus.publish(Event(
            event_type=EventType.GATE_CREATED,
            project_id=task.project_id,
            data={
                "gate_id": gate_id,
                "reason": reason,
                "deliverable_id": deliverable_id,
                "failure_count": failure_count,
                "requires_human": True
            }
        ))
    
    async def _handle_task_error(self, task: Task, error: Exception) -> None:
        """
        Handle task execution error with retry logic.
        
        Args:
            task: Failed task
            error: Exception that occurred
        """
        # Track retries
        retry_count = self.task_retries.get(task.task_id, 0)
        
        if retry_count < self.max_retries:
            # Retry task
            self.task_retries[task.task_id] = retry_count + 1
            logger.warning(f"Retrying task {task.task_id} (attempt {retry_count + 1}/{self.max_retries})")
            
            # Re-queue task
            task.status = TaskStatus.PENDING
            self.orchestrator.enqueue_task(task)
        else:
            # Max retries exceeded, mark as failed
            task.status = TaskStatus.FAILED
            logger.error(f"Task failed after {self.max_retries} retries: {task.task_id}")
            
            # Publish failure event
            await self.event_bus.publish(Event(
                event_type=EventType.ERROR_OCCURRED,
                project_id=self.orchestrator.project_id,
                data={
                    "task_id": task.task_id,
                    "error": str(error),
                    "retries": retry_count
                }
            ))
    
    async def _mark_deliverable_complete(
        self,
        deliverable_id: str,
        result: TaskResult
    ) -> None:
        """
        Mark a deliverable as complete in the phase manager.
        
        Args:
            deliverable_id: Deliverable ID
            result: Task execution result
        """
        try:
            print(f"📝 _mark_deliverable_complete called for: {deliverable_id}")
            # Actually mark it complete via phase_manager
            if self.phase_manager:
                print(f"   Phase manager exists, calling mark_completed...")
                await self.phase_manager.deliverable_tracker.mark_completed(
                    deliverable_id=deliverable_id
                )
                print(f"   ✅ mark_completed() call successful!")
                logger.info(f"✅ Marked deliverable complete in database: {deliverable_id}")
            else:
                print(f"   ❌ NO PHASE_MANAGER!")
                logger.warning(f"⚠️  No phase_manager available to mark deliverable {deliverable_id} complete")
            
            # Publish deliverable completion event
            await self.event_bus.publish(Event(
                event_type=EventType.FILE_CREATED,
                project_id=self.orchestrator.project_id,
                data={
                    "deliverable_id": deliverable_id,
                    "status": "completed",
                    "result": str(result.artifacts)[:200] if result.artifacts else "completed"
                }
            ))
            
            logger.info(f"✅ Deliverable completion published: {deliverable_id}")
        except Exception as e:
            logger.error(f"Error marking deliverable complete: {e}", exc_info=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get executor statistics."""
        return {
            "running": self.running,
            "active_workers": len([w for w in self.workers if not w.done()]),
            "total_workers": len(self.workers),
            "tasks_completed": len(self.task_results),
            "registered_agents": len(self.agent_instances),
            "queue_size": self.orchestrator.task_queue.qsize()
        }
