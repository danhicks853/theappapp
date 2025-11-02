"""
Mock Tool Access Service for Unit Tests

Provides a fast, in-memory TAS implementation for testing without database dependencies.
"""
from typing import Dict, List, Set, Any, Optional
from datetime import datetime


class MockToolAccessService:
    """Mock TAS for unit testing.
    
    Features:
    - Configurable permissions (no database)
    - Audit log capture
    - Fast and deterministic
    - Drop-in replacement for real TAS
    """
    
    def __init__(self, allow_all: bool = False):
        """
        Initialize mock TAS.
        
        Args:
            allow_all: If True, all permissions granted (useful for testing non-TAS logic)
        """
        self.allow_all = allow_all
        self.permissions: Dict[str, Dict[str, Set[str]]] = {}
        self.audit_log: List[Dict[str, Any]] = []
        self.tool_registry = {
            "container": {"operations": ["create", "destroy", "execute", "list"]},
            "file_system": {"operations": ["read", "write", "delete", "list"]},
            "web_search": {"operations": ["search"]},
            "code_validator": {"operations": ["validate"]},
            "github": {"operations": ["create_repo", "delete_repo", "merge_pr", "list_repos"]},
            "database": {"operations": ["read", "write"]},
        }
        
        # Initialize with empty permissions
        if not allow_all:
            self.permissions = {}
    
    def set_permissions(
        self,
        agent_type: str,
        tool_name: str,
        operations: List[str]
    ):
        """Set permissions for an agent type.
        
        Args:
            agent_type: Type of agent
            tool_name: Tool name
            operations: List of allowed operations
        """
        if agent_type not in self.permissions:
            self.permissions[agent_type] = {}
        self.permissions[agent_type][tool_name] = set(operations)
    
    def grant_permission(
        self,
        agent_type: str,
        tool_name: str,
        operation: str
    ):
        """Grant a specific permission.
        
        Args:
            agent_type: Type of agent
            tool_name: Tool name
            operation: Operation to allow
        """
        if agent_type not in self.permissions:
            self.permissions[agent_type] = {}
        if tool_name not in self.permissions[agent_type]:
            self.permissions[agent_type][tool_name] = set()
        self.permissions[agent_type][tool_name].add(operation)
    
    def revoke_permission(
        self,
        agent_type: str,
        tool_name: str,
        operation: str
    ):
        """Revoke a specific permission.
        
        Args:
            agent_type: Type of agent
            tool_name: Tool name
            operation: Operation to revoke
        """
        if agent_type in self.permissions:
            if tool_name in self.permissions[agent_type]:
                self.permissions[agent_type][tool_name].discard(operation)
    
    def check_permission(
        self,
        agent_type: str,
        tool_name: str,
        operation: str
    ) -> tuple[bool, str]:
        """Check if agent has permission.
        
        Args:
            agent_type: Type of agent
            tool_name: Tool name
            operation: Operation to check
        
        Returns:
            (allowed, reason)
        """
        if self.allow_all:
            return True, "All permissions granted (mock)"
        
        # Check if agent type exists
        if agent_type not in self.permissions:
            return False, f"Unknown agent type: {agent_type}"
        
        # Check if tool exists
        if tool_name not in self.tool_registry:
            return False, f"Unknown tool: {tool_name}"
        
        # Check if agent has access to tool
        if tool_name not in self.permissions[agent_type]:
            return False, f"Agent type '{agent_type}' not authorized for tool '{tool_name}'"
        
        # Check if operation is allowed
        allowed_ops = self.permissions[agent_type][tool_name]
        if operation not in allowed_ops:
            return False, f"Operation '{operation}' not allowed for '{tool_name}'"
        
        return True, "Permission granted"
    
    async def execute_tool(self, request: Any) -> Any:
        """Execute a tool (mock implementation).
        
        Args:
            request: Tool execution request
        
        Returns:
            Mock execution response
        """
        from backend.services.tool_access_service import ToolExecutionResponse
        
        # Check permission
        allowed, reason = self.check_permission(
            request.agent_type,
            request.tool_name,
            request.operation
        )
        
        # Log audit entry
        audit_entry = {
            "id": len(self.audit_log) + 1,
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": request.agent_id,
            "agent_type": request.agent_type,
            "tool_name": request.tool_name,
            "operation": request.operation,
            "parameters": request.parameters,
            "allowed": allowed,
            "success": allowed,  # Mock: success if allowed
            "result": {"mock": True, "tool": request.tool_name} if allowed else None,
            "error_message": None if allowed else reason,
            "project_id": request.project_id,
            "task_id": request.task_id
        }
        self.audit_log.append(audit_entry)
        
        if not allowed:
            return ToolExecutionResponse(
                allowed=False,
                success=False,
                result=None,
                audit_id=audit_entry["id"],
                message=reason
            )
        
        # Mock successful execution
        return ToolExecutionResponse(
            allowed=True,
            success=True,
            result={"mock": True, "tool": request.tool_name, "operation": request.operation},
            audit_id=audit_entry["id"],
            message="Mock execution successful"
        )
    
    def get_permissions(self, agent_type: str) -> Dict[str, Any]:
        """Get all permissions for an agent type.
        
        Args:
            agent_type: Type of agent
        
        Returns:
            Dict of permissions
        """
        if self.allow_all:
            # Return all permissions for all tools
            return {
                tool: set(info["operations"])
                for tool, info in self.tool_registry.items()
            }
        
        return self.permissions.get(agent_type, {})
    
    def query_audit_logs(
        self,
        agent_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        project_id: Optional[str] = None,
        allowed: Optional[bool] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query audit logs.
        
        Args:
            agent_id: Filter by agent
            tool_name: Filter by tool
            project_id: Filter by project
            allowed: Filter by allowed status
            limit: Max results
        
        Returns:
            List of audit log entries
        """
        results = self.audit_log.copy()
        
        # Apply filters
        if agent_id:
            results = [r for r in results if r["agent_id"] == agent_id]
        if tool_name:
            results = [r for r in results if r["tool_name"] == tool_name]
        if project_id:
            results = [r for r in results if r["project_id"] == project_id]
        if allowed is not None:
            results = [r for r in results if r["allowed"] == allowed]
        
        # Limit results
        results = results[-limit:]
        
        return results
    
    def get_tool_usage_stats(
        self,
        agent_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get tool usage statistics.
        
        Args:
            agent_id: Filter by agent
            tool_name: Filter by tool
            project_id: Filter by project
        
        Returns:
            Usage statistics
        """
        logs = self.query_audit_logs(
            agent_id=agent_id,
            tool_name=tool_name,
            project_id=project_id,
            limit=10000
        )
        
        if not logs:
            return {
                "total_calls": 0,
                "success_rate": 0.0,
                "denial_rate": 0.0,
                "by_tool": {},
                "by_agent_type": {}
            }
        
        total_calls = len(logs)
        successful = sum(1 for log in logs if log["success"])
        denied_calls = sum(1 for log in logs if not log["allowed"])
        
        return {
            "total_calls": total_calls,
            "successful_calls": successful,
            "failed_calls": total_calls - successful,
            "denied_calls": denied_calls,
            "success_rate": round(successful / total_calls * 100, 2) if total_calls > 0 else 0.0,
            "denial_rate": round(denied_calls / total_calls * 100, 2) if total_calls > 0 else 0.0,
            "by_tool": {},  # Can expand if needed
            "by_agent_type": {}  # Can expand if needed
        }
    
    def reset(self):
        """Reset mock state (useful between tests)."""
        if not self.allow_all:
            self.permissions = {}
        self.audit_log = []
    
    def get_audit_count(self) -> int:
        """Get total audit log entries (test helper)."""
        return len(self.audit_log)
    
    def assert_permission_checked(
        self,
        agent_type: str,
        tool_name: str,
        operation: str
    ) -> bool:
        """Assert that a permission was checked (test helper).
        
        Args:
            agent_type: Expected agent type
            tool_name: Expected tool name
            operation: Expected operation
        
        Returns:
            True if found in audit log
        """
        for log in self.audit_log:
            if (log["agent_type"] == agent_type and
                log["tool_name"] == tool_name and
                log["operation"] == operation):
                return True
        return False
    
    def assert_permission_denied(
        self,
        agent_type: str,
        tool_name: str,
        operation: str
    ) -> bool:
        """Assert that a permission was denied (test helper).
        
        Args:
            agent_type: Expected agent type
            tool_name: Expected tool name
            operation: Expected operation
        
        Returns:
            True if denied in audit log
        """
        for log in self.audit_log:
            if (log["agent_type"] == agent_type and
                log["tool_name"] == tool_name and
                log["operation"] == operation and
                not log["allowed"]):
                return True
        return False


def create_mock_tas(allow_all: bool = False) -> MockToolAccessService:
    """Factory function to create mock TAS.
    
    Args:
        allow_all: If True, all permissions granted
    
    Returns:
        MockToolAccessService instance
    """
    return MockToolAccessService(allow_all=allow_all)
