"""
Integration Tests for Tool Access Service (TAS)

Tests TAS functionality with real service instances.
"""
import pytest
from backend.services.tool_access_service import (
    ToolAccessService,
    ToolExecutionRequest,
    get_tool_access_service
)

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def tas():
    """Get TAS instance without database (in-memory mode)."""
    return ToolAccessService(db_session=None, use_db=False)


class TestPermissionChecking:
    """Test permission checking logic."""
    
    def test_check_valid_permission(self, tas):
        """Test checking a valid permission."""
        # backend_dev should have container create permission
        allowed, reason = tas.check_permission("backend_dev", "container", "create")
        assert allowed is True
        assert "granted" in reason.lower()
    
    def test_check_invalid_agent_type(self, tas):
        """Test checking permission for unknown agent type."""
        allowed, reason = tas.check_permission("unknown_agent", "container", "create")
        assert allowed is False
        assert "unknown" in reason.lower() or "not authorized" in reason.lower()
    
    def test_check_invalid_tool(self, tas):
        """Test checking permission for unknown tool."""
        allowed, reason = tas.check_permission("backend_dev", "invalid_tool", "create")
        assert allowed is False
        assert "unknown tool" in reason.lower()
    
    def test_check_invalid_operation(self, tas):
        """Test checking permission for unsupported operation."""
        allowed, reason = tas.check_permission("backend_dev", "container", "invalid_op")
        assert allowed is False
        assert "not supported" in reason.lower()
    
    def test_check_unauthorized_operation(self, tas):
        """Test checking permission agent doesn't have."""
        # workshopper shouldn't have container create permission
        allowed, reason = tas.check_permission("workshopper", "container", "create")
        assert allowed is False
        assert "not authorized" in reason.lower() or "not allowed" in reason.lower()
    
    def test_permission_caching(self, tas):
        """Test that permissions are cached."""
        # First call
        allowed1, reason1 = tas.check_permission("backend_dev", "container", "create")
        
        # Second call (should use cache)
        allowed2, reason2 = tas.check_permission("backend_dev", "container", "create")
        
        assert allowed1 == allowed2
        assert reason1 == reason2
    
    def test_cache_invalidation(self, tas):
        """Test cache invalidation."""
        # Check permission
        tas.check_permission("backend_dev", "container", "create")
        
        # Invalidate cache
        tas.invalidate_cache()
        
        # Should still work after invalidation
        allowed, reason = tas.check_permission("backend_dev", "container", "create")
        assert allowed is True


class TestToolExecution:
    """Test tool execution via TAS."""
    
    @pytest.mark.asyncio
    async def test_execute_allowed_tool(self, tas):
        """Test executing a tool with proper permissions."""
        request = ToolExecutionRequest(
            agent_id="test-agent-1",
            agent_type="backend_dev",
            tool_name="container",
            operation="list",
            parameters={},
            project_id="test-project",
            task_id="test-task"
        )
        
        response = await tas.execute_tool(request)
        
        assert response.allowed is True
        assert response.success is True
        assert response.result is not None
        assert response.audit_id is not None
    
    @pytest.mark.asyncio
    async def test_execute_denied_tool(self, tas):
        """Test executing a tool without proper permissions."""
        request = ToolExecutionRequest(
            agent_id="test-agent-2",
            agent_type="workshopper",
            tool_name="container",
            operation="create",
            parameters={
                "task_id": "test",
                "project_id": "test",
                "language": "python"
            },
            project_id="test-project"
        )
        
        response = await tas.execute_tool(request)
        
        assert response.allowed is False
        assert response.success is False
        assert response.result is None
        assert response.audit_id is not None
        assert "not authorized" in response.message.lower() or "not allowed" in response.message.lower()
    
    @pytest.mark.asyncio
    async def test_execute_with_invalid_parameters(self, tas):
        """Test execution with invalid parameters."""
        request = ToolExecutionRequest(
            agent_id="test-agent-3",
            agent_type="backend_dev",
            tool_name="container",
            operation="create",
            parameters={
                # Missing required parameters
            },
            project_id="test-project"
        )
        
        response = await tas.execute_tool(request)
        
        # Should be allowed but fail validation
        assert response.allowed is True
        assert response.success is False
        assert "validation" in response.message.lower() or "required" in response.message.lower()


class TestAuditLogging:
    """Test audit logging functionality."""
    
    @pytest.mark.asyncio
    async def test_audit_log_on_success(self, tas):
        """Test that successful executions are logged."""
        initial_count = len(tas.audit_log)
        
        request = ToolExecutionRequest(
            agent_id="test-agent-4",
            agent_type="backend_dev",
            tool_name="container",
            operation="list",
            parameters={},
            project_id="test-project"
        )
        
        await tas.execute_tool(request)
        
        # Audit log should have one more entry
        assert len(tas.audit_log) == initial_count + 1
        
        # Check log entry
        log_entry = tas.audit_log[-1]
        assert log_entry["agent_id"] == "test-agent-4"
        assert log_entry["agent_type"] == "backend_dev"
        assert log_entry["tool_name"] == "container"
        assert log_entry["operation"] == "list"
        assert log_entry["allowed"] is True
        assert log_entry["success"] is True
    
    @pytest.mark.asyncio
    async def test_audit_log_on_denial(self, tas):
        """Test that denials are logged."""
        initial_count = len(tas.audit_log)
        
        request = ToolExecutionRequest(
            agent_id="test-agent-5",
            agent_type="workshopper",
            tool_name="container",
            operation="create",
            parameters={},
            project_id="test-project"
        )
        
        await tas.execute_tool(request)
        
        # Should be logged even though denied
        assert len(tas.audit_log) == initial_count + 1
        
        log_entry = tas.audit_log[-1]
        assert log_entry["allowed"] is False
        assert log_entry["success"] is False
    
    def test_query_audit_logs(self, tas):
        """Test querying audit logs with filters."""
        # Query all logs
        logs = tas.query_audit_logs()
        assert isinstance(logs, list)
        
        # Query by agent_id
        logs = tas.query_audit_logs(agent_id="test-agent-4")
        if logs:
            assert all(log["agent_id"] == "test-agent-4" for log in logs)
        
        # Query by tool_name
        logs = tas.query_audit_logs(tool_name="container")
        if logs:
            assert all(log["tool_name"] == "container" for log in logs)
        
        # Query with limit
        logs = tas.query_audit_logs(limit=2)
        assert len(logs) <= 2
    
    def test_tool_usage_stats(self, tas):
        """Test getting tool usage statistics."""
        stats = tas.get_tool_usage_stats()
        
        assert "total_calls" in stats
        assert "successful_calls" in stats
        assert "failed_calls" in stats
        assert "success_rate" in stats
        assert "denial_rate" in stats
        assert "by_tool" in stats
        assert "by_agent_type" in stats
        
        # Should have some calls from previous tests
        assert stats["total_calls"] > 0


class TestParameterValidation:
    """Test parameter validation logic."""
    
    @pytest.mark.asyncio
    async def test_container_parameter_validation(self, tas):
        """Test container parameter validation."""
        # Test missing task_id
        request = ToolExecutionRequest(
            agent_id="test-agent-6",
            agent_type="backend_dev",
            tool_name="container",
            operation="create",
            parameters={
                "project_id": "test",
                "language": "python"
                # Missing task_id
            }
        )
        
        response = await tas.execute_tool(request)
        assert response.success is False
        assert "task_id" in response.message.lower()
    
    @pytest.mark.asyncio
    async def test_web_search_parameter_validation(self, tas):
        """Test web search parameter validation."""
        # Test missing query
        request = ToolExecutionRequest(
            agent_id="test-agent-7",
            agent_type="backend_dev",
            tool_name="web_search",
            operation="search",
            parameters={
                # Missing query
            }
        )
        
        response = await tas.execute_tool(request)
        assert response.success is False
        assert "query" in response.message.lower()
    
    @pytest.mark.asyncio
    async def test_path_traversal_prevention(self, tas):
        """Test that path traversal is prevented."""
        request = ToolExecutionRequest(
            agent_id="test-agent-8",
            agent_type="backend_dev",
            tool_name="file_system",
            operation="read",
            parameters={
                "path": "../../../etc/passwd"  # Path traversal attempt
            }
        )
        
        response = await tas.execute_tool(request)
        assert response.success is False
        assert "path traversal" in response.message.lower() or "invalid path" in response.message.lower()


class TestGetPermissions:
    """Test getting permissions for agent types."""
    
    def test_get_permissions_valid_agent(self, tas):
        """Test getting permissions for valid agent type."""
        perms = tas.get_permissions("backend_dev")
        
        assert isinstance(perms, dict)
        assert "container" in perms
        assert "file_system" in perms
        assert "web_search" in perms
    
    def test_get_permissions_invalid_agent(self, tas):
        """Test getting permissions for invalid agent type."""
        perms = tas.get_permissions("invalid_agent")
        
        assert isinstance(perms, dict)
        assert len(perms) == 0


class TestSingleton:
    """Test that TAS uses singleton pattern correctly."""
    
    def test_get_tool_access_service_returns_same_instance(self):
        """Test that get_tool_access_service returns same instance."""
        tas1 = get_tool_access_service()
        tas2 = get_tool_access_service()
        
        assert tas1 is tas2


# Note: API endpoint tests would require FastAPI TestClient
# and are better suited for separate API integration tests
