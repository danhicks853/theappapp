"""
Tests for: backend/services/task_queue.py
Task: 1.1.2 - Implement synchronous task queue system
Coverage Target: 95%+ (critical module)

This test suite provides comprehensive coverage of the TaskQueue implementation,
including unit tests for all methods, edge cases, thread safety, and error handling.
"""

import pytest
import threading
from datetime import datetime, timedelta
from backend.services.task_queue import TaskQueue, Task, TaskStatus


class TestTaskDataclass:
    """Test suite for Task dataclass."""
    
    def test_task_creation_with_defaults(self):
        """Test task creation with default values."""
        task = Task(
            task_id="task-1",
            task_type="backend_development",
            agent_type="backend_developer"
        )
        
        assert task.task_id == "task-1"
        assert task.task_type == "backend_development"
        assert task.agent_type == "backend_developer"
        assert task.priority == 0
        assert task.status == TaskStatus.PENDING
        assert task.assigned_agent_id is None
        assert task.result is None
        assert task.payload == {}
        assert isinstance(task.created_at, datetime)
    
    def test_task_creation_with_all_fields(self):
        """Test task creation with all fields specified."""
        now = datetime.now()
        payload = {"requirement": "build API"}
        
        task = Task(
            task_id="task-2",
            task_type="testing",
            agent_type="qa_engineer",
            priority=5,
            payload=payload,
            created_at=now,
            status=TaskStatus.IN_PROGRESS,
            assigned_agent_id="agent-1",
            result={"status": "passed"}
        )
        
        assert task.task_id == "task-2"
        assert task.priority == 5
        assert task.payload == payload
        assert task.created_at == now
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.assigned_agent_id == "agent-1"
        assert task.result == {"status": "passed"}
    
    def test_task_comparison_by_creation_time(self):
        """Test task comparison for priority queue ordering."""
        task1 = Task(
            task_id="task-1",
            task_type="type1",
            agent_type="agent1",
            created_at=datetime.now()
        )
        
        # Create task2 with later creation time
        task2 = Task(
            task_id="task-2",
            task_type="type2",
            agent_type="agent2",
            created_at=datetime.now() + timedelta(seconds=1)
        )
        
        # task1 should be less than task2 (earlier creation time)
        assert task1 < task2
        assert not (task2 < task1)
    
    def test_task_comparison_with_non_task_raises_error(self):
        """Test that comparing task with non-task returns NotImplemented."""
        task = Task(
            task_id="task-1",
            task_type="type1",
            agent_type="agent1"
        )
        
        result = task.__lt__("not a task")
        assert result == NotImplemented


class TestTaskQueueInitialization:
    """Test suite for TaskQueue initialization."""
    
    def test_queue_initialization(self):
        """Test that queue initializes correctly."""
        queue = TaskQueue()
        
        assert queue.is_empty()
        assert queue.get_pending_count() == 0
        assert queue.peek() is None
        assert queue.dequeue() is None
    
    def test_queue_has_thread_safety_lock(self):
        """Test that queue has thread safety lock."""
        queue = TaskQueue()
        
        assert hasattr(queue, '_lock')
        # RLock is a factory function, check for the lock object type
        assert hasattr(queue._lock, 'acquire')
        assert hasattr(queue._lock, 'release')


class TestTaskQueueEnqueue:
    """Test suite for enqueue operation."""
    
    def test_enqueue_single_task(self):
        """Test enqueueing a single task."""
        queue = TaskQueue()
        task = Task(
            task_id="task-1",
            task_type="backend_development",
            agent_type="backend_developer"
        )
        
        queue.enqueue(task)
        
        assert queue.get_pending_count() == 1
        assert not queue.is_empty()
    
    def test_enqueue_multiple_tasks(self):
        """Test enqueueing multiple tasks."""
        queue = TaskQueue()
        tasks = [
            Task(task_id=f"task-{i}", task_type="type", agent_type="agent")
            for i in range(5)
        ]
        
        for task in tasks:
            queue.enqueue(task)
        
        assert queue.get_pending_count() == 5
    
    def test_enqueue_none_raises_error(self):
        """Test that enqueueing None raises ValueError."""
        queue = TaskQueue()
        
        with pytest.raises(ValueError, match="Task cannot be None"):
            queue.enqueue(None)
    
    def test_enqueue_non_task_raises_error(self):
        """Test that enqueueing non-Task object raises TypeError."""
        queue = TaskQueue()
        
        with pytest.raises(TypeError, match="Expected Task object"):
            queue.enqueue("not a task")
    
    def test_enqueue_task_without_id_raises_error(self):
        """Test that enqueueing task without ID raises ValueError."""
        queue = TaskQueue()
        task = Task(
            task_id="",
            task_type="type",
            agent_type="agent"
        )
        
        with pytest.raises(ValueError, match="valid task_id"):
            queue.enqueue(task)
    
    def test_enqueue_duplicate_task_id_raises_error(self):
        """Test that enqueueing duplicate task ID raises ValueError."""
        queue = TaskQueue()
        task1 = Task(
            task_id="task-1",
            task_type="type1",
            agent_type="agent1"
        )
        task2 = Task(
            task_id="task-1",  # Same ID
            task_type="type2",
            agent_type="agent2"
        )
        
        queue.enqueue(task1)
        
        with pytest.raises(ValueError, match="already in queue"):
            queue.enqueue(task2)


class TestTaskQueueDequeue:
    """Test suite for dequeue operation."""
    
    def test_dequeue_empty_queue_returns_none(self):
        """Test that dequeuing from empty queue returns None."""
        queue = TaskQueue()
        
        assert queue.dequeue() is None
    
    def test_dequeue_single_task(self):
        """Test dequeuing a single task."""
        queue = TaskQueue()
        task = Task(
            task_id="task-1",
            task_type="type",
            agent_type="agent"
        )
        
        queue.enqueue(task)
        dequeued = queue.dequeue()
        
        assert dequeued == task
        assert queue.is_empty()
    
    def test_dequeue_fifo_order_same_priority(self):
        """Test FIFO ordering for tasks with same priority."""
        queue = TaskQueue()
        tasks = [
            Task(task_id=f"task-{i}", task_type="type", agent_type="agent", priority=0)
            for i in range(3)
        ]
        
        for task in tasks:
            queue.enqueue(task)
        
        # Should dequeue in FIFO order (by creation time)
        for i in range(3):
            dequeued = queue.dequeue()
            assert dequeued.task_id == f"task-{i}"
    
    def test_dequeue_priority_order(self):
        """Test priority ordering - higher priority dequeued first."""
        queue = TaskQueue()
        
        # Enqueue tasks in reverse priority order
        task_low = Task(
            task_id="task-low",
            task_type="type",
            agent_type="agent",
            priority=1
        )
        task_high = Task(
            task_id="task-high",
            task_type="type",
            agent_type="agent",
            priority=10
        )
        task_medium = Task(
            task_id="task-medium",
            task_type="type",
            agent_type="agent",
            priority=5
        )
        
        queue.enqueue(task_low)
        queue.enqueue(task_high)
        queue.enqueue(task_medium)
        
        # Should dequeue in priority order: high, medium, low
        assert queue.dequeue().task_id == "task-high"
        assert queue.dequeue().task_id == "task-medium"
        assert queue.dequeue().task_id == "task-low"
    
    def test_dequeue_removes_from_task_map(self):
        """Test that dequeue removes task from internal task map."""
        queue = TaskQueue()
        task = Task(
            task_id="task-1",
            task_type="type",
            agent_type="agent"
        )
        
        queue.enqueue(task)
        assert queue.get_task_by_id("task-1") is not None
        
        queue.dequeue()
        assert queue.get_task_by_id("task-1") is None


class TestTaskQueuePeek:
    """Test suite for peek operation."""
    
    def test_peek_empty_queue_returns_none(self):
        """Test that peeking empty queue returns None."""
        queue = TaskQueue()
        
        assert queue.peek() is None
    
    def test_peek_does_not_remove_task(self):
        """Test that peek does not remove task from queue."""
        queue = TaskQueue()
        task = Task(
            task_id="task-1",
            task_type="type",
            agent_type="agent"
        )
        
        queue.enqueue(task)
        peeked = queue.peek()
        
        assert peeked == task
        assert queue.get_pending_count() == 1
        
        # Peek again should return same task
        peeked_again = queue.peek()
        assert peeked_again == task
        assert queue.get_pending_count() == 1
    
    def test_peek_returns_highest_priority_task(self):
        """Test that peek returns highest priority task."""
        queue = TaskQueue()
        
        task_low = Task(
            task_id="task-low",
            task_type="type",
            agent_type="agent",
            priority=1
        )
        task_high = Task(
            task_id="task-high",
            task_type="type",
            agent_type="agent",
            priority=10
        )
        
        queue.enqueue(task_low)
        queue.enqueue(task_high)
        
        peeked = queue.peek()
        assert peeked.task_id == "task-high"
        assert queue.get_pending_count() == 2


class TestTaskQueueGetPendingCount:
    """Test suite for get_pending_count operation."""
    
    def test_pending_count_empty_queue(self):
        """Test pending count for empty queue."""
        queue = TaskQueue()
        
        assert queue.get_pending_count() == 0
    
    def test_pending_count_after_enqueue(self):
        """Test pending count increases after enqueue."""
        queue = TaskQueue()
        
        for i in range(5):
            task = Task(
                task_id=f"task-{i}",
                task_type="type",
                agent_type="agent"
            )
            queue.enqueue(task)
            assert queue.get_pending_count() == i + 1
    
    def test_pending_count_after_dequeue(self):
        """Test pending count decreases after dequeue."""
        queue = TaskQueue()
        tasks = [
            Task(task_id=f"task-{i}", task_type="type", agent_type="agent")
            for i in range(5)
        ]
        
        for task in tasks:
            queue.enqueue(task)
        
        for i in range(5):
            queue.dequeue()
            assert queue.get_pending_count() == 4 - i


class TestTaskQueuePrioritizeTask:
    """Test suite for prioritize_task operation."""
    
    def test_prioritize_nonexistent_task_returns_false(self):
        """Test that prioritizing nonexistent task returns False."""
        queue = TaskQueue()
        
        result = queue.prioritize_task("nonexistent", 10)
        assert result is False
    
    def test_prioritize_existing_task_returns_true(self):
        """Test that prioritizing existing task returns True."""
        queue = TaskQueue()
        task = Task(
            task_id="task-1",
            task_type="type",
            agent_type="agent",
            priority=1
        )
        
        queue.enqueue(task)
        result = queue.prioritize_task("task-1", 10)
        
        assert result is True
        assert task.priority == 10
    
    def test_prioritize_changes_dequeue_order(self):
        """Test that prioritizing changes dequeue order."""
        queue = TaskQueue()
        
        task1 = Task(
            task_id="task-1",
            task_type="type",
            agent_type="agent",
            priority=1
        )
        task2 = Task(
            task_id="task-2",
            task_type="type",
            agent_type="agent",
            priority=2
        )
        
        queue.enqueue(task1)
        queue.enqueue(task2)
        
        # Initially task2 has higher priority
        assert queue.peek().task_id == "task-2"
        
        # Prioritize task1
        queue.prioritize_task("task-1", 10)
        
        # Now task1 should be first
        assert queue.peek().task_id == "task-1"
        assert queue.dequeue().task_id == "task-1"
        assert queue.dequeue().task_id == "task-2"
    
    def test_prioritize_negative_priority_raises_error(self):
        """Test that negative priority raises ValueError."""
        queue = TaskQueue()
        task = Task(
            task_id="task-1",
            task_type="type",
            agent_type="agent"
        )
        
        queue.enqueue(task)
        
        with pytest.raises(ValueError, match="cannot be negative"):
            queue.prioritize_task("task-1", -1)


class TestTaskQueueGetTaskById:
    """Test suite for get_task_by_id operation."""
    
    def test_get_nonexistent_task_returns_none(self):
        """Test that getting nonexistent task returns None."""
        queue = TaskQueue()
        
        assert queue.get_task_by_id("nonexistent") is None
    
    def test_get_existing_task_returns_task(self):
        """Test that getting existing task returns the task."""
        queue = TaskQueue()
        task = Task(
            task_id="task-1",
            task_type="type",
            agent_type="agent"
        )
        
        queue.enqueue(task)
        retrieved = queue.get_task_by_id("task-1")
        
        assert retrieved == task
    
    def test_get_task_does_not_remove_from_queue(self):
        """Test that getting task does not remove it from queue."""
        queue = TaskQueue()
        task = Task(
            task_id="task-1",
            task_type="type",
            agent_type="agent"
        )
        
        queue.enqueue(task)
        queue.get_task_by_id("task-1")
        
        assert queue.get_pending_count() == 1


class TestTaskQueueRemoveTask:
    """Test suite for remove_task operation."""
    
    def test_remove_nonexistent_task_returns_false(self):
        """Test that removing nonexistent task returns False."""
        queue = TaskQueue()
        
        result = queue.remove_task("nonexistent")
        assert result is False
    
    def test_remove_existing_task_returns_true(self):
        """Test that removing existing task returns True."""
        queue = TaskQueue()
        task = Task(
            task_id="task-1",
            task_type="type",
            agent_type="agent"
        )
        
        queue.enqueue(task)
        result = queue.remove_task("task-1")
        
        assert result is True
        assert queue.is_empty()
    
    def test_remove_task_removes_from_queue(self):
        """Test that removing task removes it from queue."""
        queue = TaskQueue()
        tasks = [
            Task(task_id=f"task-{i}", task_type="type", agent_type="agent")
            for i in range(3)
        ]
        
        for task in tasks:
            queue.enqueue(task)
        
        queue.remove_task("task-1")
        
        assert queue.get_pending_count() == 2
        assert queue.get_task_by_id("task-1") is None
    
    def test_remove_task_preserves_order(self):
        """Test that removing task preserves order of remaining tasks."""
        queue = TaskQueue()
        
        task1 = Task(task_id="task-1", task_type="type", agent_type="agent", priority=1)
        task2 = Task(task_id="task-2", task_type="type", agent_type="agent", priority=2)
        task3 = Task(task_id="task-3", task_type="type", agent_type="agent", priority=3)
        
        queue.enqueue(task1)
        queue.enqueue(task2)
        queue.enqueue(task3)
        
        queue.remove_task("task-2")
        
        assert queue.dequeue().task_id == "task-3"
        assert queue.dequeue().task_id == "task-1"


class TestTaskQueueClear:
    """Test suite for clear operation."""
    
    def test_clear_empty_queue(self):
        """Test clearing empty queue."""
        queue = TaskQueue()
        queue.clear()
        
        assert queue.is_empty()
    
    def test_clear_removes_all_tasks(self):
        """Test that clear removes all tasks."""
        queue = TaskQueue()
        tasks = [
            Task(task_id=f"task-{i}", task_type="type", agent_type="agent")
            for i in range(5)
        ]
        
        for task in tasks:
            queue.enqueue(task)
        
        queue.clear()
        
        assert queue.is_empty()
        assert queue.get_pending_count() == 0
    
    def test_clear_clears_task_map(self):
        """Test that clear removes tasks from internal map."""
        queue = TaskQueue()
        task = Task(
            task_id="task-1",
            task_type="type",
            agent_type="agent"
        )
        
        queue.enqueue(task)
        queue.clear()
        
        assert queue.get_task_by_id("task-1") is None


class TestTaskQueueIsEmpty:
    """Test suite for is_empty operation."""
    
    def test_is_empty_on_new_queue(self):
        """Test that new queue is empty."""
        queue = TaskQueue()
        
        assert queue.is_empty()
    
    def test_is_empty_after_enqueue(self):
        """Test that queue is not empty after enqueue."""
        queue = TaskQueue()
        task = Task(
            task_id="task-1",
            task_type="type",
            agent_type="agent"
        )
        
        queue.enqueue(task)
        assert not queue.is_empty()
    
    def test_is_empty_after_dequeue(self):
        """Test that queue is empty after dequeuing all tasks."""
        queue = TaskQueue()
        task = Task(
            task_id="task-1",
            task_type="type",
            agent_type="agent"
        )
        
        queue.enqueue(task)
        queue.dequeue()
        
        assert queue.is_empty()


class TestTaskQueueGetAllTasks:
    """Test suite for get_all_tasks operation."""
    
    def test_get_all_tasks_empty_queue(self):
        """Test getting all tasks from empty queue."""
        queue = TaskQueue()
        
        tasks = queue.get_all_tasks()
        assert tasks == []
    
    def test_get_all_tasks_returns_all_tasks(self):
        """Test that get_all_tasks returns all tasks."""
        queue = TaskQueue()
        original_tasks = [
            Task(task_id=f"task-{i}", task_type="type", agent_type="agent")
            for i in range(3)
        ]
        
        for task in original_tasks:
            queue.enqueue(task)
        
        retrieved_tasks = queue.get_all_tasks()
        
        assert len(retrieved_tasks) == 3
        retrieved_ids = [t.task_id for t in retrieved_tasks]
        assert "task-0" in retrieved_ids
        assert "task-1" in retrieved_ids
        assert "task-2" in retrieved_ids
    
    def test_get_all_tasks_returns_in_priority_order(self):
        """Test that get_all_tasks returns tasks in priority order."""
        queue = TaskQueue()
        
        task_low = Task(
            task_id="task-low",
            task_type="type",
            agent_type="agent",
            priority=1
        )
        task_high = Task(
            task_id="task-high",
            task_type="type",
            agent_type="agent",
            priority=10
        )
        task_medium = Task(
            task_id="task-medium",
            task_type="type",
            agent_type="agent",
            priority=5
        )
        
        queue.enqueue(task_low)
        queue.enqueue(task_high)
        queue.enqueue(task_medium)
        
        tasks = queue.get_all_tasks()
        
        # Should be in priority order: high, medium, low
        assert tasks[0].task_id == "task-high"
        assert tasks[1].task_id == "task-medium"
        assert tasks[2].task_id == "task-low"
    
    def test_get_all_tasks_does_not_remove_tasks(self):
        """Test that get_all_tasks does not remove tasks from queue."""
        queue = TaskQueue()
        task = Task(
            task_id="task-1",
            task_type="type",
            agent_type="agent"
        )
        
        queue.enqueue(task)
        queue.get_all_tasks()
        
        assert queue.get_pending_count() == 1


class TestTaskQueueThreadSafety:
    """Test suite for thread safety."""
    
    def test_concurrent_enqueue_operations(self):
        """Test that concurrent enqueue operations are thread-safe."""
        queue = TaskQueue()
        num_threads = 10
        tasks_per_thread = 10
        
        def enqueue_tasks(thread_id):
            for i in range(tasks_per_thread):
                task = Task(
                    task_id=f"task-{thread_id}-{i}",
                    task_type="type",
                    agent_type="agent"
                )
                queue.enqueue(task)
        
        threads = [
            threading.Thread(target=enqueue_tasks, args=(i,))
            for i in range(num_threads)
        ]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should have all tasks
        assert queue.get_pending_count() == num_threads * tasks_per_thread
    
    def test_concurrent_enqueue_dequeue_operations(self):
        """Test that concurrent enqueue and dequeue are thread-safe."""
        queue = TaskQueue()
        num_tasks = 100
        dequeued_tasks = []
        lock = threading.Lock()
        
        # Pre-enqueue all tasks
        for i in range(num_tasks):
            task = Task(
                task_id=f"task-{i}",
                task_type="type",
                agent_type="agent"
            )
            queue.enqueue(task)
        
        def dequeue_tasks():
            while True:
                task = queue.dequeue()
                if task is None:
                    break
                with lock:
                    dequeued_tasks.append(task.task_id)
        
        threads = [threading.Thread(target=dequeue_tasks) for _ in range(5)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All tasks should be dequeued exactly once
        assert len(dequeued_tasks) == num_tasks
        assert len(set(dequeued_tasks)) == num_tasks  # No duplicates


class TestTaskQueueEdgeCases:
    """Test suite for edge cases and boundary conditions."""
    
    def test_large_number_of_tasks(self):
        """Test queue with large number of tasks."""
        queue = TaskQueue()
        num_tasks = 1000
        
        # Enqueue
        for i in range(num_tasks):
            task = Task(
                task_id=f"task-{i}",
                task_type="type",
                agent_type="agent"
            )
            queue.enqueue(task)
        
        assert queue.get_pending_count() == num_tasks
        
        # Dequeue
        for i in range(num_tasks):
            task = queue.dequeue()
            assert task is not None
        
        assert queue.is_empty()
    
    def test_priority_zero_tasks(self):
        """Test tasks with priority 0."""
        queue = TaskQueue()
        
        task1 = Task(
            task_id="task-1",
            task_type="type",
            agent_type="agent",
            priority=0
        )
        task2 = Task(
            task_id="task-2",
            task_type="type",
            agent_type="agent",
            priority=0
        )
        
        queue.enqueue(task1)
        queue.enqueue(task2)
        
        # Should dequeue in FIFO order
        assert queue.dequeue().task_id == "task-1"
        assert queue.dequeue().task_id == "task-2"
    
    def test_very_high_priority_values(self):
        """Test tasks with very high priority values."""
        queue = TaskQueue()
        
        task1 = Task(
            task_id="task-1",
            task_type="type",
            agent_type="agent",
            priority=999999
        )
        task2 = Task(
            task_id="task-2",
            task_type="type",
            agent_type="agent",
            priority=1
        )
        
        queue.enqueue(task2)
        queue.enqueue(task1)
        
        assert queue.dequeue().task_id == "task-1"
        assert queue.dequeue().task_id == "task-2"
    
    def test_task_with_large_payload(self):
        """Test task with large payload."""
        queue = TaskQueue()
        
        large_payload = {f"key-{i}": f"value-{i}" * 100 for i in range(100)}
        
        task = Task(
            task_id="task-1",
            task_type="type",
            agent_type="agent",
            payload=large_payload
        )
        
        queue.enqueue(task)
        dequeued = queue.dequeue()
        
        assert dequeued.payload == large_payload
