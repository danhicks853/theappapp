"""
Task Queue System - Synchronous Task Management

Module: Task Queue Service
Purpose: Manage task queuing with FIFO ordering and priority support

Reference: Decision 67 - Orchestrator LLM Integration Architecture
Task: 1.1.2 - Implement synchronous task queue system

This module provides a thread-safe task queue implementation for the orchestrator.
Tasks are processed in priority order (higher priority first), then FIFO for same priority.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from queue import PriorityQueue
import threading


class TaskStatus(Enum):
    """Task lifecycle states."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class Task:
    """
    Represents a task in the system.
    
    Attributes:
        task_id: Unique identifier for the task
        task_type: Type of task (e.g., 'backend_development', 'testing')
        agent_type: Type of agent that should handle this task
        priority: Priority level (higher number = higher priority)
        payload: Task-specific data and requirements
        created_at: Timestamp when task was created
        status: Current status of the task
        assigned_agent_id: ID of agent assigned to this task (if any)
        result: Result data after task completion (if any)
    """
    task_id: str
    task_type: str
    agent_type: str
    priority: int = 0  # Higher number = higher priority
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    
    def __lt__(self, other: 'Task') -> bool:
        """
        Support comparison for PriorityQueue when priorities are equal.
        
        Args:
            other: Another Task object to compare with
            
        Returns:
            bool: True if this task's creation time is earlier than other's
        """
        if not isinstance(other, Task):
            return NotImplemented
        # Compare by creation time if priorities are equal
        return self.created_at < other.created_at


class TaskQueue:
    """
    Thread-safe task queue with priority support.
    
    Implements FIFO ordering with priority queue support. Tasks with higher
    priority values are processed first. Tasks with equal priority are
    processed in FIFO order (by creation time).
    
    This queue is thread-safe and can be used in concurrent environments.
    
    Attributes:
        _queue: Internal PriorityQueue for task storage
        _lock: Threading lock for thread-safe operations
        _task_map: Dictionary mapping task_id to task for O(1) lookups
    """
    
    def __init__(self):
        """
        Initialize the task queue.
        
        Creates an empty thread-safe queue ready to accept tasks.
        """
        self._queue: PriorityQueue = PriorityQueue()
        self._lock = threading.RLock()
        self._task_map: Dict[str, Task] = {}
    
    def enqueue(self, task: Task) -> None:
        """
        Add a task to the queue.
        
        Tasks are stored in priority order (higher priority first),
        then FIFO for same priority. This operation is thread-safe.
        
        Args:
            task: Task object to enqueue
            
        Raises:
            ValueError: If task is None or task_id is empty
            TypeError: If task is not a Task object
        """
        if task is None:
            raise ValueError("Task cannot be None")
        
        if not isinstance(task, Task):
            raise TypeError(f"Expected Task object, got {type(task)}")
        
        if not task.task_id:
            raise ValueError("Task must have a valid task_id")
        
        with self._lock:
            # Prevent duplicate task IDs
            if task.task_id in self._task_map:
                raise ValueError(f"Task with id {task.task_id} already in queue")
            
            # Store in map for lookups
            self._task_map[task.task_id] = task
            
            # Add to priority queue
            # Negate priority so higher numbers = higher priority
            self._queue.put((-task.priority, task.created_at.timestamp(), task))
    
    def dequeue(self) -> Optional[Task]:
        """
        Remove and return the next task from the queue.
        
        Returns the highest priority task. If multiple tasks have the same
        priority, returns the oldest task (FIFO). This operation is thread-safe.
        
        Returns:
            Next task in queue, or None if queue is empty
        """
        with self._lock:
            if self._queue.empty():
                return None
            
            _, _, task = self._queue.get()
            
            # Remove from task map
            if task.task_id in self._task_map:
                del self._task_map[task.task_id]
            
            return task
    
    def peek(self) -> Optional[Task]:
        """
        View the next task without removing it from the queue.
        
        Returns the highest priority task without modifying the queue.
        This operation is thread-safe.
        
        Returns:
            Next task in queue, or None if queue is empty
        """
        with self._lock:
            if self._queue.empty():
                return None
            
            # Get the task
            priority_tuple = self._queue.get()
            _, _, task = priority_tuple
            
            # Put it back immediately
            self._queue.put(priority_tuple)
            
            return task
    
    def get_pending_count(self) -> int:
        """
        Get the number of pending tasks in the queue.
        
        Returns the count of tasks currently waiting to be assigned.
        This operation is thread-safe.
        
        Returns:
            Number of tasks waiting in queue
        """
        with self._lock:
            return self._queue.qsize()
    
    def prioritize_task(self, task_id: str, new_priority: int) -> bool:
        """
        Change the priority of a task in the queue.
        
        Finds a task by ID and updates its priority. This requires rebuilding
        the queue to maintain priority ordering. This operation is thread-safe.
        
        Args:
            task_id: ID of task to prioritize
            new_priority: New priority value (higher = more urgent)
            
        Returns:
            bool: True if task found and updated, False if task not found
            
        Raises:
            ValueError: If new_priority is negative
        """
        if new_priority < 0:
            raise ValueError("Priority cannot be negative")
        
        with self._lock:
            # Check if task exists
            if task_id not in self._task_map:
                return False
            
            task = self._task_map[task_id]
            
            # Update priority
            task.priority = new_priority
            
            # Rebuild queue with new priority
            # Extract all tasks from queue
            temp_tasks = []
            while not self._queue.empty():
                _, _, t = self._queue.get()
                temp_tasks.append(t)
            
            # Re-enqueue all tasks (will be sorted by new priorities)
            for t in temp_tasks:
                self._queue.put((-t.priority, t.created_at.timestamp(), t))
            
            return True
    
    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """
        Retrieve a task by its ID without removing it from the queue.
        
        This is useful for checking task status or properties without
        dequeuing. This operation is thread-safe.
        
        Args:
            task_id: ID of task to retrieve
            
        Returns:
            Task object if found, None otherwise
        """
        with self._lock:
            return self._task_map.get(task_id)
    
    def remove_task(self, task_id: str) -> bool:
        """
        Remove a specific task from the queue by ID.
        
        This is useful for canceling tasks. Note: This requires rebuilding
        the queue. This operation is thread-safe.
        
        Args:
            task_id: ID of task to remove
            
        Returns:
            bool: True if task found and removed, False if task not found
        """
        with self._lock:
            # Check if task exists
            if task_id not in self._task_map:
                return False
            
            # Remove from map
            del self._task_map[task_id]
            
            # Rebuild queue without this task
            temp_tasks = []
            while not self._queue.empty():
                _, _, task = self._queue.get()
                if task.task_id != task_id:
                    temp_tasks.append(task)
            
            # Re-enqueue remaining tasks
            for task in temp_tasks:
                self._queue.put((-task.priority, task.created_at.timestamp(), task))
            
            return True
    
    def clear(self) -> None:
        """
        Remove all tasks from the queue.
        
        This operation is thread-safe.
        """
        with self._lock:
            # Clear the queue
            while not self._queue.empty():
                self._queue.get()
            
            # Clear the task map
            self._task_map.clear()
    
    def is_empty(self) -> bool:
        """
        Check if the queue is empty.
        
        This operation is thread-safe.
        
        Returns:
            bool: True if queue is empty, False otherwise
        """
        with self._lock:
            return self._queue.empty()
    
    def get_all_tasks(self) -> List[Task]:
        """
        Get all tasks currently in the queue.
        
        Returns tasks in priority order. This operation is thread-safe.
        
        Returns:
            List of all tasks in the queue, ordered by priority
        """
        with self._lock:
            # Extract all tasks
            temp_tasks = []
            while not self._queue.empty():
                _, _, task = self._queue.get()
                temp_tasks.append(task)
            
            # Re-enqueue all tasks
            for task in temp_tasks:
                self._queue.put((-task.priority, task.created_at.timestamp(), task))
            
            # Sort by priority (descending) then by creation time (ascending)
            temp_tasks.sort(key=lambda t: (-t.priority, t.created_at.timestamp()))
            
            return temp_tasks
