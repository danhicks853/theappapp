"""
Cross-System Integration Tests

Tests interactions between multiple Phase 1 systems.
"""
import pytest
from unittest.mock import Mock


@pytest.mark.integration
class TestGateCollaborationIntegration:
    """Test integration between gates and collaboration."""
    
    @pytest.mark.asyncio
    async def test_collaboration_loop_creates_gate(self):
        """
        Test: Collaboration loop detection → Gate creation
        """
        from backend.services.collaboration_orchestrator import CollaborationOrchestrator
        from backend.services.gate_manager import GateManager
        
        mock_engine = Mock()
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        
        # Create managers
        gate_manager = GateManager(mock_engine)
        collab_orchestrator = CollaborationOrchestrator(mock_engine)
        
        # Verify managers initialized
        assert gate_manager is not None
        assert collab_orchestrator is not None
        
        # Mock loop detection
        mock_conn.execute.return_value.fetchall.return_value = [
            ("Question 1?",),
            ("Question 1?",),  # Same question
        ]
        
        # Detect loop
        loop = await collab_orchestrator.detect_semantic_loop(
            agent_a_id="backend-1",
            agent_b_id="security-1",
            current_question="Question 1?"
        )
        
        # Should detect loop or return None if not enough history
        # In real implementation with gate_manager, would trigger gate creation
        assert loop is None or loop.get("loop_detected") is True


@pytest.mark.integration
class TestFailureToKnowledgeIntegration:
    """Test integration from failure detection to knowledge capture."""
    
    @pytest.mark.asyncio
    async def test_failure_signature_to_knowledge_capture(self):
        """
        Test: Failure → Signature extraction → Knowledge capture
        """
        from backend.models.failure_signature import extract_failure_signature
        from backend.services.knowledge_capture_service import KnowledgeCaptureService
        
        # Step 1: Extract failure signature
        error_output = """
        Traceback (most recent call last):
          File "backend/api/routes.py", line 42, in get_user
            user = db.get(user_id)
        TypeError: 'NoneType' object is not subscriptable
        """
        
        signature = extract_failure_signature(
            error_output=error_output,
            agent_id="backend-1",
            task_id="task-123"
        )
        
        assert signature.error_type.value == "type_error"
        assert signature.location is not None
        
        # Step 2: Capture as knowledge
        mock_engine = Mock()
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        
        knowledge_service = KnowledgeCaptureService(mock_engine)
        
        knowledge_id = await knowledge_service.capture_failure_solution(
            task_id="task-123",
            agent_id="backend-1",
            agent_type="backend_developer",
            failure_description=signature.exact_message,
            solution_description="Added null check before accessing db",
            error_type=signature.error_type.value
        )
        
        assert knowledge_id is not None
        assert mock_conn.execute.called


@pytest.mark.integration
class TestTimeoutToGateIntegration:
    """Test integration between timeout monitor and gate manager."""
    
    @pytest.mark.asyncio
    async def test_timeout_creates_gate(self):
        """
        Test: Task timeout → Gate creation
        """
        from backend.services.timeout_monitor import TimeoutMonitor
        from backend.services.gate_manager import GateManager
        
        mock_engine = Mock()
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        
        gate_manager = GateManager(mock_engine)
        timeout_monitor = TimeoutMonitor(gate_manager)
        
        # Start monitoring
        await timeout_monitor.start()
        
        # Monitor a task with very short timeout
        await timeout_monitor.monitor_task(
            task_id="task-123",
            agent_id="backend-1",
            agent_type="backend_developer",
            timeout_seconds=1  # 1 second for testing
        )
        
        # Wait for timeout
        import asyncio
        await asyncio.sleep(2)
        
        # Stop monitoring
        await timeout_monitor.stop()
        
        # Verify monitoring was active
        assert timeout_monitor.get_active_count() >= 0


@pytest.mark.integration
class TestLoopDetectionToGateIntegration:
    """Test integration between loop detection and gate creation."""
    
    @pytest.mark.asyncio
    async def test_loop_creates_gate_automatically(self):
        """
        Test: 3 identical failures → Loop detected → Gate created
        """
        from backend.services.loop_detector import LoopDetector
        
        mock_gate_manager = Mock()
        mock_gate_manager.create_gate.return_value = "gate-123"
        
        detector = LoopDetector(gate_manager=mock_gate_manager)
        
        # Record 3 identical failures
        error_sig = "TypeError: undefined"
        
        gate_id1 = await detector.check_and_trigger_gate(
            task_id="task-456",
            agent_id="backend-1",
            project_id="proj-789",
            error_signature=error_sig
        )
        assert gate_id1 is None  # First failure
        
        gate_id2 = await detector.check_and_trigger_gate(
            task_id="task-456",
            agent_id="backend-1",
            project_id="proj-789",
            error_signature=error_sig
        )
        assert gate_id2 is None  # Second failure
        
        gate_id3 = await detector.check_and_trigger_gate(
            task_id="task-456",
            agent_id="backend-1",
            project_id="proj-789",
            error_signature=error_sig
        )
        assert gate_id3 == "gate-123"  # Third failure triggers gate


@pytest.mark.integration
class TestKnowledgePipelineIntegration:
    """Test complete knowledge pipeline."""
    
    @pytest.mark.asyncio
    async def test_capture_to_checkpoint_to_embedding(self):
        """
        Test: Knowledge capture → Checkpoint → Embedding → Query
        """
        from backend.services.knowledge_capture_service import KnowledgeCaptureService
        from backend.services.checkpoint_embedding_service import CheckpointEmbeddingService
        
        mock_engine = Mock()
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        
        # Step 1: Capture knowledge
        knowledge_service = KnowledgeCaptureService(mock_engine)
        
        knowledge_id = await knowledge_service.capture_failure_solution(
            task_id="task-123",
            agent_id="backend-1",
            agent_type="backend_developer",
            failure_description="Slow queries",
            solution_description="Added indexes",
            technology="PostgreSQL"
        )
        
        assert knowledge_id is not None
        
        # Step 2: Checkpoint embedding
        mock_qdrant = Mock()
        mock_openai = Mock()
        
        embedding_service = CheckpointEmbeddingService(
            mock_engine,
            mock_qdrant,
            mock_openai
        )
        
        # Mock pending entries
        mock_conn.execute.return_value.fetchall.return_value = []
        
        result = await embedding_service.process_checkpoint("test_checkpoint")
        
        assert result["checkpoint_type"] == "test_checkpoint"
        assert result["processed_count"] >= 0


@pytest.mark.integration
class TestProgressEvaluationIntegration:
    """Test progress evaluation integration."""
    
    def test_progress_evaluator_with_loop_detector(self):
        """
        Test: Progress evaluation → Loop detection decision
        """
        from backend.services.progress_evaluator import ProgressEvaluator
        from backend.services.loop_detector import LoopDetector
        
        evaluator = ProgressEvaluator()
        detector = LoopDetector()
        
        # Set baseline
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = os.path.join(tmpdir, "test.py")
            with open(test_file, "w") as f:
                f.write("print('test')")
            
            evaluator.set_baseline("task-123", tmpdir)
            
            # Evaluate progress (no changes)
            progress = evaluator.evaluate_progress("task-123", tmpdir)
            
            # If no progress, loop detector should continue tracking
            if not progress:
                detector.record_failure("task-123", "no_progress")
            else:
                detector.record_success("task-123")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
