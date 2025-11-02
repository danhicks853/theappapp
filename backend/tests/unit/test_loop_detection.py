"""
Unit Tests for Loop Detection

Tests the core loop detection algorithm and edge cases.

Reference: Section 1.4.1 - Loop Detection Algorithm
"""
import pytest
from backend.services.loop_detector import LoopDetector
from backend.models.agent_state import TaskState


class TestLoopDetector:
    """Test suite for LoopDetector class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = LoopDetector(window_size=3)
    
    def test_initialization(self):
        """Test detector initializes correctly."""
        assert self.detector.window_size == 3
        assert len(self.detector._failures) == 0
    
    def test_record_single_failure(self):
        """Test recording a single failure."""
        self.detector.record_failure("task-1", "error-A")
        
        assert "task-1" in self.detector._failures
        assert len(self.detector._failures["task-1"]) == 1
        assert self.detector._failures["task-1"][0] == "error-A"
    
    def test_record_multiple_different_failures(self):
        """Test recording different failures doesn't trigger loop."""
        self.detector.record_failure("task-1", "error-A")
        self.detector.record_failure("task-1", "error-B")
        self.detector.record_failure("task-1", "error-C")
        
        # Mock TaskState for is_looping check
        state = TaskState(task_id="task-1", last_errors=[])
        
        assert not self.detector.is_looping(state)
    
    def test_three_identical_errors_triggers_loop(self):
        """Test 3 identical errors triggers loop detection."""
        self.detector.record_failure("task-1", "error-A")
        self.detector.record_failure("task-1", "error-A")
        self.detector.record_failure("task-1", "error-A")
        
        state = TaskState(task_id="task-1", last_errors=[])
        
        assert self.detector.is_looping(state)
    
    def test_two_identical_one_different_no_loop(self):
        """Test 2 identical + 1 different doesn't trigger loop."""
        self.detector.record_failure("task-1", "error-A")
        self.detector.record_failure("task-1", "error-A")
        self.detector.record_failure("task-1", "error-B")
        
        state = TaskState(task_id="task-1", last_errors=[])
        
        assert not self.detector.is_looping(state)
    
    def test_window_size_limit(self):
        """Test bounded deque limits history to window size."""
        self.detector.record_failure("task-1", "error-A")
        self.detector.record_failure("task-1", "error-B")
        self.detector.record_failure("task-1", "error-C")
        self.detector.record_failure("task-1", "error-D")  # Should push out error-A
        
        history = list(self.detector._failures["task-1"])
        assert len(history) == 3
        assert "error-A" not in history
        assert history == ["error-B", "error-C", "error-D"]
    
    def test_record_success_clears_history(self):
        """Test recording success clears failure history."""
        self.detector.record_failure("task-1", "error-A")
        self.detector.record_failure("task-1", "error-A")
        
        self.detector.record_success("task-1")
        
        assert "task-1" not in self.detector._failures
    
    def test_reset_clears_history(self):
        """Test explicit reset clears failure history."""
        self.detector.record_failure("task-1", "error-A")
        self.detector.record_failure("task-1", "error-A")
        
        self.detector.reset("task-1")
        
        assert "task-1" not in self.detector._failures
    
    def test_empty_signature_ignored(self):
        """Test empty/None signatures are ignored."""
        self.detector.record_failure("task-1", None)
        self.detector.record_failure("task-1", "")
        
        assert "task-1" not in self.detector._failures
    
    def test_multiple_tasks_independent(self):
        """Test different tasks maintain independent histories."""
        self.detector.record_failure("task-1", "error-A")
        self.detector.record_failure("task-2", "error-B")
        
        assert "task-1" in self.detector._failures
        assert "task-2" in self.detector._failures
        assert self.detector._failures["task-1"][0] == "error-A"
        assert self.detector._failures["task-2"][0] == "error-B"
    
    def test_loop_detection_with_task_state_history(self):
        """Test is_looping uses TaskState.last_errors as fallback."""
        # Don't record in detector, use TaskState history
        state = TaskState(
            task_id="task-1",
            last_errors=["error-X", "error-X", "error-X"]
        )
        
        assert self.detector.is_looping(state)
    
    def test_insufficient_history_no_loop(self):
        """Test that < 3 errors never triggers loop."""
        self.detector.record_failure("task-1", "error-A")
        self.detector.record_failure("task-1", "error-A")  # Only 2
        
        state = TaskState(task_id="task-1", last_errors=[])
        
        assert not self.detector.is_looping(state)
    
    def test_alternating_errors_no_loop(self):
        """Test alternating errors don't trigger loop."""
        self.detector.record_failure("task-1", "error-A")
        self.detector.record_failure("task-1", "error-B")
        self.detector.record_failure("task-1", "error-A")
        
        state = TaskState(task_id="task-1", last_errors=[])
        
        assert not self.detector.is_looping(state)
    
    def test_loop_after_success_and_new_failures(self):
        """Test loop detection after success clears and new failures."""
        # First loop
        self.detector.record_failure("task-1", "error-A")
        self.detector.record_failure("task-1", "error-A")
        self.detector.record_failure("task-1", "error-A")
        
        # Clear with success
        self.detector.record_success("task-1")
        
        # New failures
        self.detector.record_failure("task-1", "error-B")
        self.detector.record_failure("task-1", "error-B")
        
        state = TaskState(task_id="task-1", last_errors=[])
        
        # Not looping yet (only 2)
        assert not self.detector.is_looping(state)
        
        # Add third
        self.detector.record_failure("task-1", "error-B")
        assert self.detector.is_looping(state)


class TestLoopDetectorEdgeCases:
    """Test edge cases and special scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = LoopDetector()
    
    def test_very_long_error_signature(self):
        """Test handling of very long error signatures."""
        long_error = "A" * 10000
        
        self.detector.record_failure("task-1", long_error)
        self.detector.record_failure("task-1", long_error)
        self.detector.record_failure("task-1", long_error)
        
        state = TaskState(task_id="task-1", last_errors=[])
        assert self.detector.is_looping(state)
    
    def test_unicode_error_signatures(self):
        """Test handling of Unicode in error signatures."""
        unicode_error = "错误: 无法连接"
        
        self.detector.record_failure("task-1", unicode_error)
        self.detector.record_failure("task-1", unicode_error)
        self.detector.record_failure("task-1", unicode_error)
        
        state = TaskState(task_id="task-1", last_errors=[])
        assert self.detector.is_looping(state)
    
    def test_special_characters_in_signatures(self):
        """Test handling of special characters."""
        special_error = "Error: \n\t[SPECIAL]\r\n$%^&*()"
        
        self.detector.record_failure("task-1", special_error)
        self.detector.record_failure("task-1", special_error)
        self.detector.record_failure("task-1", special_error)
        
        state = TaskState(task_id="task-1", last_errors=[])
        assert self.detector.is_looping(state)
    
    def test_custom_window_size(self):
        """Test custom window sizes work correctly."""
        detector_5 = LoopDetector(window_size=5)
        
        # Record 4 identical errors
        for _ in range(4):
            detector_5.record_failure("task-1", "error-A")
        
        state = TaskState(task_id="task-1", last_errors=[])
        
        # Should not loop with window_size=5
        assert not detector_5.is_looping(state)
        
        # Add 5th
        detector_5.record_failure("task-1", "error-A")
        assert detector_5.is_looping(state)
    
    def test_concurrent_task_isolation(self):
        """Test that concurrent tasks don't interfere."""
        # Simulate concurrent tasks
        self.detector.record_failure("task-1", "error-A")
        self.detector.record_failure("task-2", "error-B")
        self.detector.record_failure("task-1", "error-A")
        self.detector.record_failure("task-2", "error-B")
        self.detector.record_failure("task-1", "error-A")
        self.detector.record_failure("task-2", "error-B")
        
        state1 = TaskState(task_id="task-1", last_errors=[])
        state2 = TaskState(task_id="task-2", last_errors=[])
        
        # Both should be looping independently
        assert self.detector.is_looping(state1)
        assert self.detector.is_looping(state2)


@pytest.mark.asyncio
class TestLoopDetectorWithGateManager:
    """Test loop detector integration with gate manager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.gate_created = False
        self.gate_context = None
        
        # Mock gate manager
        class MockGateManager:
            def __init__(self, test_instance):
                self.test = test_instance
            
            def create_gate(self, **kwargs):
                self.test.gate_created = True
                self.test.gate_context = kwargs
                return "gate-123"
        
        self.gate_manager = MockGateManager(self)
        self.detector = LoopDetector(gate_manager=self.gate_manager)
    
    @pytest.mark.asyncio
    async def test_gate_created_on_loop(self):
        """Test gate is created when loop detected."""
        gate_id = await self.detector.check_and_trigger_gate(
            task_id="task-1",
            agent_id="agent-1",
            project_id="proj-1",
            error_signature="error-A"
        )
        
        # First call - no loop
        assert gate_id is None
        assert not self.gate_created
        
        # Second and third
        await self.detector.check_and_trigger_gate(
            task_id="task-1",
            agent_id="agent-1",
            project_id="proj-1",
            error_signature="error-A"
        )
        
        gate_id = await self.detector.check_and_trigger_gate(
            task_id="task-1",
            agent_id="agent-1",
            project_id="proj-1",
            error_signature="error-A"
        )
        
        # Third call - loop!
        assert gate_id == "gate-123"
        assert self.gate_created
        assert self.gate_context["project_id"] == "proj-1"
        assert self.gate_context["agent_id"] == "agent-1"
        assert self.gate_context["gate_type"] == "loop_detected"
    
    @pytest.mark.asyncio
    async def test_no_duplicate_gates(self):
        """Test that duplicate gates aren't created for same loop."""
        # Create first loop
        for _ in range(3):
            await self.detector.check_and_trigger_gate(
                task_id="task-1",
                agent_id="agent-1",
                project_id="proj-1",
                error_signature="error-A"
            )
        
        first_gate = self.gate_created
        assert first_gate
        
        # Reset flag
        self.gate_created = False
        
        # Try to create another (should return existing gate ID)
        gate_id = await self.detector.check_and_trigger_gate(
            task_id="task-1",
            agent_id="agent-1",
            project_id="proj-1",
            error_signature="error-A"
        )
        
        # Should not create new gate
        assert not self.gate_created
        assert gate_id is not None  # Returns existing


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
