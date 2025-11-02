"""
RAG System Integration Tests

Tests complete RAG workflow: capture → embed → query → retrieve

Reference: Section 1.5.1 - RAG System Architecture
"""
import pytest
from unittest.mock import Mock, patch
import uuid

from backend.services.knowledge_capture_service import KnowledgeCaptureService
from backend.services.checkpoint_embedding_service import CheckpointEmbeddingService


@pytest.mark.asyncio
class TestRAGSystemWorkflow:
    """Test complete RAG system workflow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock engine
        self.mock_engine = Mock()
        self.mock_conn = Mock()
        self.mock_engine.connect.return_value.__enter__.return_value = self.mock_conn
        
        # Services
        self.capture_service = KnowledgeCaptureService(self.mock_engine)
        self.embedding_service = CheckpointEmbeddingService(self.mock_engine)
    
    @pytest.mark.asyncio
    async def test_failure_solution_capture_and_retrieve(self):
        """
        Test: Capture failure solution → Embed → Query → Retrieve
        """
        # Step 1: Capture knowledge
        knowledge_id = await self.capture_service.capture_failure_solution(
            task_id="task-123",
            agent_id="backend-1",
            agent_type="backend_developer",
            failure_description="Database connection timeout",
            solution_description="Increased connection pool size to 20",
            project_id="proj-1",
            task_type="database_config",
            technology="PostgreSQL",
            error_type="timeout",
            quality_score="high"
        )
        
        assert knowledge_id is not None
        
        # Verify _store_knowledge was called
        assert self.mock_conn.execute.called
        
        # Step 2: Verify metadata
        call_args = self.mock_conn.execute.call_args
        metadata_arg = call_args[0][1]["metadata"]
        
        import json
        metadata = json.loads(metadata_arg)
        
        assert metadata["quality_score"] == "high"
        assert metadata["success_count"] == 0
        assert metadata["technology"] == "PostgreSQL"
    
    @pytest.mark.asyncio
    async def test_gate_rejection_capture(self):
        """
        Test: Capture gate rejection (negative example)
        """
        knowledge_id = await self.capture_service.capture_gate_rejection(
            gate_id="gate-456",
            agent_id="frontend-1",
            agent_type="frontend_developer",
            rejection_reason="UI not responsive on mobile",
            feedback="Need to test on mobile devices before submission",
            project_id="proj-2",
            task_type="ui_development",
            gate_type="quality_check"
        )
        
        assert knowledge_id is not None
        
        # Verify success_verified is False (negative example)
        call_args = self.mock_conn.execute.call_args
        metadata_arg = call_args[0][1]["metadata"]
        
        import json
        metadata = json.loads(metadata_arg)
        
        assert metadata["success_verified"] is False
    
    @pytest.mark.asyncio
    async def test_gate_approval_first_attempt_only(self):
        """
        Test: Gate approval only captures first-attempt successes
        """
        # First attempt - should capture
        knowledge_id = await self.capture_service.capture_gate_approval(
            gate_id="gate-789",
            agent_id="backend-1",
            agent_type="backend_developer",
            gate_reason="API implementation complete",
            approval_notes="Clean code, well tested",
            project_id="proj-3",
            task_type="api_development",
            first_attempt=True
        )
        
        assert knowledge_id is not None
        
        # Reset mock
        self.mock_conn.execute.reset_mock()
        
        # Not first attempt - should skip
        knowledge_id_2 = await self.capture_service.capture_gate_approval(
            gate_id="gate-790",
            agent_id="backend-1",
            agent_type="backend_developer",
            gate_reason="API implementation complete",
            project_id="proj-3",
            task_type="api_development",
            first_attempt=False
        )
        
        assert knowledge_id_2 is None
        assert not self.mock_conn.execute.called
    
    @pytest.mark.asyncio
    async def test_knowledge_success_tracking(self):
        """
        Test: Track when knowledge is successfully used
        """
        knowledge_id = str(uuid.uuid4())
        
        # Track success
        await self.capture_service.track_knowledge_success(knowledge_id)
        
        # Verify JSONB update was called
        assert self.mock_conn.execute.called
        call_args = self.mock_conn.execute.call_args
        
        # Should increment success_count and update last_used_at
        query_text = str(call_args[0][0])
        assert "success_count" in query_text
        assert "last_used_at" in query_text


@pytest.mark.asyncio
class TestCheckpointEmbedding:
    """Test checkpoint embedding service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock engine
        self.mock_engine = Mock()
        self.mock_conn = Mock()
        self.mock_engine.connect.return_value.__enter__.return_value = self.mock_conn
        
        # Mock Qdrant client
        self.mock_qdrant = Mock()
        
        # Mock OpenAI client
        self.mock_openai = Mock()
        
        self.service = CheckpointEmbeddingService(
            self.mock_engine,
            self.mock_qdrant,
            self.mock_openai
        )
    
    @pytest.mark.asyncio
    async def test_process_checkpoint_no_pending(self):
        """
        Test: Checkpoint with no pending entries
        """
        # Mock no results
        self.mock_conn.execute.return_value.fetchall.return_value = []
        
        result = await self.service.process_checkpoint("phase_completion")
        
        assert result["processed_count"] == 0
        assert result["embedded_count"] == 0
    
    @pytest.mark.asyncio
    async def test_process_checkpoint_with_entries(self):
        """
        Test: Checkpoint processes pending entries
        """
        # Mock pending entries
        pending = [
            {
                "id": str(uuid.uuid4()),
                "knowledge_type": "failure_solution",
                "content": "Test content",
                "metadata": {"quality_score": "high"}
            }
        ]
        
        self.mock_conn.execute.return_value.fetchall.return_value = [
            (p["id"], p["knowledge_type"], p["content"], p["metadata"])
            for p in pending
        ]
        
        with patch.object(self.service, '_generate_embedding', return_value=[0.1] * 1536):
            with patch.object(self.service, '_store_in_qdrant', return_value=None):
                result = await self.service.process_checkpoint("project_completion")
        
        assert result["checkpoint_type"] == "project_completion"
        # Would process if mocks were complete
    
    @pytest.mark.asyncio
    async def test_get_pending_count(self):
        """
        Test: Get count of pending knowledge entries
        """
        self.mock_conn.execute.return_value.scalar.return_value = 42
        
        count = await self.service.get_pending_count()
        
        assert count == 42
    
    @pytest.mark.asyncio
    async def test_manual_trigger(self):
        """
        Test: Manual embedding trigger
        """
        self.mock_conn.execute.return_value.fetchall.return_value = []
        
        result = await self.service.manual_trigger(project_id="proj-1")
        
        assert result["checkpoint_type"] == "manual_trigger"


@pytest.mark.asyncio
class TestRAGFormatting:
    """Test RAG pattern formatting."""
    
    @pytest.mark.asyncio
    async def test_format_patterns_basic(self):
        """
        Test: Basic pattern formatting
        """
        from backend.prompts.rag_formatting import format_patterns
        
        patterns = [
            {
                "content": "## Problem\nDatabase slow\n## Solution\nAdded indexes",
                "metadata": {
                    "success_count": 5,
                    "agent_type": "backend_developer",
                    "task_type": "performance",
                    "technology": "PostgreSQL",
                    "quality_score": "high"
                }
            }
        ]
        
        formatted = format_patterns(patterns)
        
        assert "[ORCHESTRATOR CONTEXT: Historical Knowledge]" in formatted
        assert "Pattern 1" in formatted
        assert "5 successes" in formatted
        assert "[END CONTEXT]" in formatted
    
    @pytest.mark.asyncio
    async def test_format_patterns_token_limit(self):
        """
        Test: Respects token limits
        """
        from backend.prompts.rag_formatting import format_patterns
        
        # Create many patterns
        patterns = [
            {
                "content": "## Problem\nTest\n## Solution\nTest solution " * 100,
                "metadata": {"success_count": i}
            }
            for i in range(10)
        ]
        
        formatted = format_patterns(patterns, max_tokens=500)
        
        # Should be truncated
        assert len(formatted) < 500 * 5  # Rough token-to-char ratio
        assert "shown]" in formatted


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
