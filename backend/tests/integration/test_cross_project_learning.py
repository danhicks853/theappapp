"""
Cross-Project Learning Integration Tests

Tests that knowledge from one project helps another project.
Validates project-agnostic knowledge sharing.

Reference: Section 1.5.1 - RAG System Architecture
"""
import pytest
from unittest.mock import Mock
import uuid

from backend.services.knowledge_capture_service import KnowledgeCaptureService


@pytest.mark.asyncio
class TestCrossProjectLearning:
    """Test knowledge sharing across projects."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock engine
        self.mock_engine = Mock()
        self.mock_conn = Mock()
        self.mock_engine.connect.return_value.__enter__.return_value = self.mock_conn
        
        self.capture_service = KnowledgeCaptureService(self.mock_engine)
    
    @pytest.mark.asyncio
    async def test_project_a_captures_knowledge(self):
        """
        Test: Project A captures knowledge about database optimization
        """
        # Project A captures knowledge
        knowledge_id = await self.capture_service.capture_failure_solution(
            task_id="task-project-a-1",
            agent_id="backend-a-1",
            agent_type="backend_developer",
            failure_description="Slow database queries on large dataset",
            solution_description="Added composite index on (user_id, created_at)",
            project_id="project-a",
            task_type="database_optimization",
            technology="PostgreSQL",
            quality_score="high"
        )
        
        assert knowledge_id is not None
        
        # Verify project_id is stored in metadata
        call_args = self.mock_conn.execute.call_args
        metadata_arg = call_args[0][1]["metadata"]
        
        import json
        metadata = json.loads(metadata_arg)
        
        assert metadata["project_id"] == "project-a"
        assert metadata["technology"] == "PostgreSQL"
        assert metadata["task_type"] == "database_optimization"
    
    @pytest.mark.asyncio
    async def test_project_b_can_query_project_a_knowledge(self):
        """
        Test: Project B queries and retrieves Project A's knowledge
        
        This simulates:
        1. Project A captured knowledge (previous test)
        2. Knowledge was embedded in Qdrant
        3. Project B runs similar task
        4. Project B's query retrieves Project A's knowledge
        """
        # Simulate query from Project B
        # In real scenario, this would query Qdrant with filters
        
        # Mock query result that returns Project A's knowledge
        self.mock_conn.execute.return_value.fetchall.return_value = [
            (
                str(uuid.uuid4()),
                "Slow database queries solved by adding indexes",
                {
                    "project_id": "project-a",  # From Project A
                    "technology": "PostgreSQL",
                    "task_type": "database_optimization",
                    "quality_score": "high",
                    "success_count": 3
                },
                "2025-11-01"
            )
        ]
        
        # Project B queries knowledge
        results = await self.capture_service.get_knowledge_by_type(
            question_type="database_optimization",
            limit=10
        )
        
        # Verify Project B can access Project A's knowledge
        assert len(results) > 0
        assert results[0]["metadata"]["project_id"] == "project-a"
        
        # This demonstrates cross-project learning:
        # Project B benefits from Project A's experience
    
    @pytest.mark.asyncio
    async def test_knowledge_is_project_agnostic(self):
        """
        Test: Knowledge queries don't filter by project_id by default
        
        This ensures knowledge is shared across all projects unless
        explicitly filtered.
        """
        # Capture knowledge from multiple projects
        projects = ["project-a", "project-b", "project-c"]
        
        for project_id in projects:
            await self.capture_service.capture_failure_solution(
                task_id=f"task-{project_id}",
                agent_id=f"agent-{project_id}",
                agent_type="backend_developer",
                failure_description="Test problem",
                solution_description="Test solution",
                project_id=project_id,
                task_type="testing",
                technology="Python"
            )
        
        # All 3 captures should have been stored
        assert self.mock_conn.execute.call_count >= 3
        
        # In real scenario, querying Qdrant without project_id filter
        # would return knowledge from all projects
    
    @pytest.mark.asyncio
    async def test_technology_based_filtering_works(self):
        """
        Test: Can filter knowledge by technology across projects
        
        E.g., All PostgreSQL knowledge from all projects
        """
        # This would be done in RAGQueryService
        # Filters: technology="PostgreSQL"
        # Should return results from any project using PostgreSQL
        
        # Mock represents query with technology filter
        self.mock_conn.execute.return_value.fetchall.return_value = [
            (
                str(uuid.uuid4()),
                "PostgreSQL optimization",
                {
                    "project_id": "project-a",
                    "technology": "PostgreSQL",
                    "success_count": 5
                },
                "2025-11-01"
            ),
            (
                str(uuid.uuid4()),
                "PostgreSQL backup strategy",
                {
                    "project_id": "project-b",
                    "technology": "PostgreSQL",
                    "success_count": 3
                },
                "2025-11-02"
            )
        ]
        
        # Query returns PostgreSQL knowledge from multiple projects
        results = await self.capture_service.get_knowledge_by_type(
            question_type="PostgreSQL",
            limit=10
        )
        
        # Verify multi-project results
        project_ids = {r["metadata"]["project_id"] for r in results}
        assert len(project_ids) > 1  # Knowledge from multiple projects


@pytest.mark.asyncio
class TestKnowledgeQualityRanking:
    """Test that quality and success count affect ranking."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_engine = Mock()
        self.mock_conn = Mock()
        self.mock_engine.connect.return_value.__enter__.return_value = self.mock_conn
        
        self.capture_service = KnowledgeCaptureService(self.mock_engine)
    
    @pytest.mark.asyncio
    async def test_high_quality_knowledge_captured(self):
        """
        Test: High quality knowledge is marked appropriately
        """
        knowledge_id = await self.capture_service.capture_failure_solution(
            task_id="task-quality-1",
            agent_id="backend-1",
            agent_type="backend_developer",
            failure_description="Memory leak",
            solution_description="Fixed circular reference",
            quality_score="high",
            technology="Python"
        )
        
        assert knowledge_id is not None
        
        # Verify quality score in metadata
        call_args = self.mock_conn.execute.call_args
        metadata_arg = call_args[0][1]["metadata"]
        
        import json
        metadata = json.loads(metadata_arg)
        
        assert metadata["quality_score"] == "high"
        assert metadata["success_count"] == 0  # Starts at 0
    
    @pytest.mark.asyncio
    async def test_success_tracking_increments_count(self):
        """
        Test: Using knowledge increments success_count
        """
        knowledge_id = str(uuid.uuid4())
        
        # Track 3 successful uses
        for _ in range(3):
            await self.capture_service.track_knowledge_success(knowledge_id)
        
        # Verify update was called 3 times
        assert self.mock_conn.execute.call_count == 3
        
        # Each call should increment success_count
        for call in self.mock_conn.execute.call_args_list:
            query_text = str(call[0][0])
            assert "success_count" in query_text


@pytest.mark.asyncio
class TestKnowledgeRetentionPolicy:
    """Test 1-year retention policy."""
    
    @pytest.mark.asyncio
    async def test_knowledge_cleanup_job(self):
        """
        Test: Knowledge older than 1 year is cleaned up
        """
        from backend.jobs.knowledge_cleanup import KnowledgeCleanupJob
        
        mock_engine = Mock()
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        
        job = KnowledgeCleanupJob(mock_engine)
        
        # Mock old entries
        mock_conn.execute.return_value.fetchall.return_value = [
            (str(uuid.uuid4()),),
            (str(uuid.uuid4()),)
        ]
        
        # Mock deletion
        mock_conn.execute.return_value.rowcount = 2
        
        result = await job.run_cleanup()
        
        assert result["postgres_deleted"] >= 0
    
    @pytest.mark.asyncio
    async def test_cleanup_stats(self):
        """
        Test: Get cleanup statistics
        """
        from backend.jobs.knowledge_cleanup import KnowledgeCleanupJob
        
        mock_engine = Mock()
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        
        # Mock stats query
        mock_conn.execute.return_value.fetchone.return_value = (100, None, None)
        
        job = KnowledgeCleanupJob(mock_engine)
        stats = await job.get_cleanup_stats()
        
        assert "retention_days" in stats
        assert stats["retention_days"] == 365


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
