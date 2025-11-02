"""
Integration Tests for Loop Detection

Tests full agent workflow with loop detection, gate triggering, and recovery.

Reference: Section 1.4.1 - Loop Detection Algorithm
"""
import pytest

from backend.services.loop_detector import LoopDetector
from backend.services.loop_detection_service import LoopDetectionService, FailureCategory


@pytest.mark.asyncio
class TestLoopDetectionWorkflow:
    """Test complete loop detection workflow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock gate manager
        self.gates_created = []
        
        class MockGateManager:
            def __init__(self, test_instance):
                self.test = test_instance
            
            def create_gate(self, **kwargs):
                gate_id = f"gate-{len(self.test.gates_created) + 1}"
                self.test.gates_created.append({
                    "gate_id": gate_id,
                    **kwargs
                })
                return gate_id
        
        self.gate_manager = MockGateManager(self)
        self.detector = LoopDetector(gate_manager=self.gate_manager)
    
    @pytest.mark.asyncio
    async def test_agent_workflow_with_loop_detection(self):
        """
        Test: Agent fails 3 times → Loop detected → Gate created → Counter resets
        """
        task_id = "task-1"
        agent_id = "backend-dev-1"
        project_id = "proj-1"
        error_sig = "TypeError: cannot read property of undefined"
        
        # Simulate agent failing 3 times
        results = []
        for i in range(3):
            gate_id = await self.detector.check_and_trigger_gate(
                task_id=task_id,
                agent_id=agent_id,
                project_id=project_id,
                error_signature=error_sig
            )
            results.append(gate_id)
        
        # First 2 should not create gate
        assert results[0] is None
        assert results[1] is None
        
        # Third should create gate
        assert results[2] is not None
        assert len(self.gates_created) == 1
        
        # Verify gate details
        gate = self.gates_created[0]
        assert gate["project_id"] == project_id
        assert gate["agent_id"] == agent_id
        assert gate["gate_type"] == "loop_detected"
        assert "loop_type" in gate["context"]
    
    @pytest.mark.asyncio
    async def test_loop_reset_after_success(self):
        """
        Test: Loop counter resets after successful execution
        """
        task_id = "task-2"
        agent_id = "frontend-dev-1"
        
        # Fail twice
        await self.detector.check_and_trigger_gate(
            task_id=task_id,
            agent_id=agent_id,
            project_id="proj-1",
            error_signature="error-A"
        )
        await self.detector.check_and_trigger_gate(
            task_id=task_id,
            agent_id=agent_id,
            project_id="proj-1",
            error_signature="error-A"
        )
        
        # Success - reset
        self.detector.record_success(task_id)
        
        # Fail again - should not trigger loop (counter reset)
        gate_id = await self.detector.check_and_trigger_gate(
            task_id=task_id,
            agent_id=agent_id,
            project_id="proj-1",
            error_signature="error-A"
        )
        
        assert gate_id is None
        assert len(self.gates_created) == 0
    
    @pytest.mark.asyncio
    async def test_different_errors_no_loop(self):
        """
        Test: Different errors don't trigger loop detection
        """
        task_id = "task-3"
        agent_id = "qa-1"
        
        # Three different errors
        await self.detector.check_and_trigger_gate(
            task_id=task_id,
            agent_id=agent_id,
            project_id="proj-1",
            error_signature="TypeError"
        )
        await self.detector.check_and_trigger_gate(
            task_id=task_id,
            agent_id=agent_id,
            project_id="proj-1",
            error_signature="ValueError"
        )
        gate_id = await self.detector.check_and_trigger_gate(
            task_id=task_id,
            agent_id=agent_id,
            project_id="proj-1",
            error_signature="AttributeError"
        )
        
        # No loop
        assert gate_id is None
        assert len(self.gates_created) == 0


@pytest.mark.asyncio
class TestLoopDetectionServiceIntegration:
    """Test LoopDetectionService with edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.gates_created = []
        
        class MockGateManager:
            def __init__(self, test_instance):
                self.test = test_instance
            
            def create_gate(self, **kwargs):
                gate_id = f"gate-{len(self.test.gates_created) + 1}"
                self.test.gates_created.append({"gate_id": gate_id, **kwargs})
                return gate_id
        
        self.gate_manager = MockGateManager(self)
        self.service = LoopDetectionService(gate_manager=self.gate_manager)
    
    @pytest.mark.asyncio
    async def test_external_failure_not_counted_as_loop(self):
        """
        Test: External API/network failures don't count toward loop
        """
        task_id = "task-ext-1"
        agent_id = "backend-1"
        
        # Simulate 3 network errors
        for i in range(3):
            result = await self.service.record_failure(
                task_id=task_id,
                agent_id=agent_id,
                error_signature=f"conn-error-{i}",
                error_output="ConnectionError: Failed to connect to external API",
                agent_type="backend_developer",
                project_id="proj-1"
            )
            
            # Should be categorized as external
            assert result["category"] == FailureCategory.EXTERNAL.value
            assert not result["loop_detected"]
        
        # No gates should be created
        assert len(self.gates_created) == 0
    
    @pytest.mark.asyncio
    async def test_metrics_tracking(self):
        """
        Test: Service tracks loop metrics correctly
        """
        # Create a loop
        task_id = "task-metrics"
        agent_id = "backend-1"
        
        for _ in range(3):
            await self.service.record_failure(
                task_id=task_id,
                agent_id=agent_id,
                error_signature="type-error",
                error_output="TypeError: undefined",
                agent_type="backend_developer",
                project_id="proj-1"
            )
        
        # Check metrics
        metrics = self.service.get_metrics()
        
        assert metrics["total_loops_detected"] == 1
        assert "backend_developer" in metrics["loops_by_agent_type"]
        assert metrics["loops_by_agent_type"]["backend_developer"] == 1
    
    @pytest.mark.asyncio
    async def test_loop_resolution_tracking(self):
        """
        Test: Service tracks how loops are resolved
        """
        task_id = "task-resolved"
        agent_id = "frontend-1"
        
        # Record resolution
        self.service.record_loop_resolution(
            task_id=task_id,
            agent_id=agent_id,
            resolution="human_intervention",
            iterations_to_resolve=5,
            time_to_resolve_seconds=120.5
        )
        
        metrics = self.service.get_metrics()
        
        assert metrics["resolved_loops"] == 1
        assert metrics["average_iterations_to_resolve"] == 5.0
        assert metrics["average_resolution_time_seconds"] == 120.5


@pytest.mark.asyncio
class TestFullAgentWorkflow:
    """Test complete agent workflow with loop detection and recovery."""
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        """
        Complete workflow:
        1. Agent starts task
        2. Encounters error 3 times
        3. Loop detected
        4. Gate created
        5. Human approves
        6. Counter resets
        7. Agent continues
        """
        # Mock components
        gates = []
        
        class MockGateManager:
            def create_gate(self, **kwargs):
                gate_id = f"gate-{len(gates) + 1}"
                gates.append({"id": gate_id, "status": "pending", **kwargs})
                return gate_id
            
            def approve_gate(self, gate_id):
                for gate in gates:
                    if gate["id"] == gate_id:
                        gate["status"] = "approved"
                        return True
                return False
        
        gate_manager = MockGateManager()
        service = LoopDetectionService(gate_manager=gate_manager)
        
        # Workflow
        task_id = "integration-task-1"
        agent_id = "backend-1"
        project_id = "proj-1"
        
        # Step 1: Agent starts (no errors yet)
        assert service.get_metrics()["total_loops_detected"] == 0
        
        # Step 2 & 3: Agent encounters same error 3 times
        results = []
        for i in range(3):
            result = await service.record_failure(
                task_id=task_id,
                agent_id=agent_id,
                error_signature="syntax-error",
                error_output="SyntaxError: Unexpected token",
                agent_type="backend_developer",
                project_id=project_id
            )
            results.append(result)
        
        # Step 4: Loop detected on 3rd failure
        assert not results[0]["loop_detected"]
        assert not results[1]["loop_detected"]
        assert results[2]["loop_detected"]
        
        # Step 4: Gate created
        assert len(gates) == 1
        assert gates[0]["status"] == "pending"
        gate_id = gates[0]["id"]
        
        # Step 5: Human approves gate
        gate_manager.approve_gate(gate_id)
        assert gates[0]["status"] == "approved"
        
        # Step 6: Counter resets (simulated by recording success)
        service.reset_task(task_id)
        
        # Step 7: Agent continues with new attempt
        result = await service.record_failure(
            task_id=task_id,
            agent_id=agent_id,
            error_signature="syntax-error",  # Same error again
            error_output="SyntaxError: Unexpected token",
            agent_type="backend_developer",
            project_id=project_id
        )
        
        # Should not trigger loop immediately (counter was reset)
        assert not result["loop_detected"]
        
        # Verify metrics
        metrics = service.get_metrics()
        assert metrics["total_loops_detected"] == 1
        assert metrics["loops_by_agent_type"]["backend_developer"] == 1


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
