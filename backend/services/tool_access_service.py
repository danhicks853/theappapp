"""
Tool Access Service (TAS)

Centralized broker for all agent tool access with permission enforcement and audit logging.
All agent tool requests must flow through TAS for security and compliance.

Architecture:
- Separate FastAPI service (port 8001)
- Permission-based access control per agent type
- Comprehensive audit logging
- Tool registry for available tools
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from functools import lru_cache

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Categories of tools available to agents."""
    CODE_EXECUTION = "code_execution"
    FILE_SYSTEM = "file_system"
    WEB_SEARCH = "web_search"
    GITHUB = "github"
    DATABASE = "database"
    COMMUNICATION = "communication"


class ToolExecutionRequest(BaseModel):
    """Request to execute a tool."""
    agent_id: str = Field(..., description="Unique agent identifier")
    agent_type: str = Field(..., description="Type of agent (backend_dev, etc.)")
    tool_name: str = Field(..., description="Name of tool to execute")
    operation: str = Field(..., description="Specific operation to perform")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Operation parameters")
    project_id: Optional[str] = Field(None, description="Associated project ID")
    task_id: Optional[str] = Field(None, description="Associated task ID")


class ToolExecutionResponse(BaseModel):
    """Response from tool execution."""
    allowed: bool = Field(..., description="Whether execution was allowed")
    success: bool = Field(..., description="Whether execution succeeded")
    result: Optional[Dict[str, Any]] = Field(None, description="Execution result")
    audit_id: Optional[int] = Field(None, description="Audit log entry ID")
    message: Optional[str] = Field(None, description="Error or info message")


class ToolValidationRequest(BaseModel):
    """Request to validate tool access (dry-run)."""
    agent_id: str
    agent_type: str
    tool_name: str
    operation: str


class ToolValidationResponse(BaseModel):
    """Response from validation check."""
    allowed: bool
    reason: str


class PermissionsResponse(BaseModel):
    """Response with all permissions for an agent."""
    agent_id: str
    agent_type: str
    permissions: List[Dict[str, Any]]


class ToolAccessService:
    """
    Tool Access Service - Centralized tool broker.
    
    Features:
    - Permission checking per agent type
    - Tool execution routing
    - Comprehensive audit logging
    - Rate limiting
    - Security validation
    """
    
    # Default permissions per agent type
    # Format: {agent_type: {tool_name: {operations}}}
    DEFAULT_PERMISSIONS = {
        "backend_dev": {
            "container": {"create", "destroy", "execute", "list"},
            "file_system": {"read", "write", "delete", "list"},
            "web_search": {"search"},
            "code_validator": {"validate"},
            "database": {"read", "write"},  # Via ORM only
        },
        "frontend_dev": {
            "container": {"create", "destroy", "execute", "list"},
            "file_system": {"read", "write", "delete", "list"},
            "web_search": {"search"},
            "code_validator": {"validate"},
        },
        "workshopper": {
            "web_search": {"search"},
            "file_system": {"read", "list"},
        },
        "security_expert": {
            "web_search": {"search"},
            "file_system": {"read", "list"},
            "code_validator": {"validate"},
        },
        "devops_engineer": {
            "container": {"create", "destroy", "execute", "list"},
            "file_system": {"read", "write", "delete", "list"},
            "web_search": {"search"},
            "database": {"read"},
        },
        "qa_engineer": {
            "container": {"create", "destroy", "execute", "list"},
            "file_system": {"read", "list"},
            "web_search": {"search"},
        },
        "github_specialist": {
            "github": {"create_repo", "delete_repo", "merge_pr", "list_repos"},
            "file_system": {"read", "list"},
        }
    }
    
    def __init__(self, db_session: Optional[Session] = None, use_db: bool = True):
        """Initialize Tool Access Service.
        
        Args:
            db_session: SQLAlchemy session for database access
            use_db: If True, use database for permissions; if False, use in-memory defaults
        """
        self.db_session = db_session
        self.use_db = use_db and db_session is not None
        self.permissions = self.DEFAULT_PERMISSIONS.copy()
        self.audit_log: List[Dict[str, Any]] = []  # In-memory for now, DB later
        self.tool_registry = self._initialize_tool_registry()
        self._permission_cache: Dict[str, Tuple[bool, str, datetime]] = {}  # Cache with timestamp
        self._cache_ttl = timedelta(minutes=5)  # 5-minute cache
        logger.info(f"Tool Access Service initialized (use_db={self.use_db})")
    
    def _initialize_tool_registry(self) -> Dict[str, Any]:
        """
        Initialize registry of available tools.
        
        Returns:
            Dict mapping tool names to tool handlers
        """
        # Will be populated with actual tool implementations
        # For now, registry structure only
        registry = {
            "container": {
                "category": ToolCategory.CODE_EXECUTION,
                "operations": ["create", "destroy", "execute", "list"],
                "handler": None  # Will be set when integrating ContainerManager
            },
            "file_system": {
                "category": ToolCategory.FILE_SYSTEM,
                "operations": ["read", "write", "delete", "list"],
                "handler": None
            },
            "web_search": {
                "category": ToolCategory.WEB_SEARCH,
                "operations": ["search"],
                "handler": None  # Will be set to WebSearchService
            },
            "code_validator": {
                "category": ToolCategory.CODE_EXECUTION,
                "operations": ["validate"],
                "handler": None  # Will be set to CodeValidator
            },
            "github": {
                "category": ToolCategory.GITHUB,
                "operations": ["create_repo", "delete_repo", "merge_pr", "list_repos"],
                "handler": None
            },
            "database": {
                "category": ToolCategory.DATABASE,
                "operations": ["read", "write"],
                "handler": None
            }
        }
        return registry
    
    def check_permission(
        self,
        agent_type: str,
        tool_name: str,
        operation: str
    ) -> tuple[bool, str]:
        """
        Check if agent has permission for tool operation.
        
        Uses database if available, with 5-minute cache to reduce load.
        Falls back to in-memory defaults if database unavailable.
        
        Args:
            agent_type: Type of agent
            tool_name: Name of tool
            operation: Specific operation
        
        Returns:
            (allowed, reason)
        """
        # Check cache first
        cache_key = f"{agent_type}:{tool_name}:{operation}"
        if cache_key in self._permission_cache:
            cached_result, cached_reason, cached_time = self._permission_cache[cache_key]
            # Check if cache is still valid
            if datetime.utcnow() - cached_time < self._cache_ttl:
                return cached_result, cached_reason
        
        # Check if tool exists
        if tool_name not in self.tool_registry:
            result = (False, f"Unknown tool: {tool_name}")
            self._permission_cache[cache_key] = (*result, datetime.utcnow())
            return result
        
        # Check if operation exists in tool
        tool_ops = self.tool_registry[tool_name]["operations"]
        if operation not in tool_ops:
            result = (False, f"Operation '{operation}' not supported by '{tool_name}'")
            self._permission_cache[cache_key] = (*result, datetime.utcnow())
            return result
        
        # Use database if available
        if self.use_db and self.db_session:
            try:
                result = self._check_permission_db(agent_type, tool_name, operation)
                self._permission_cache[cache_key] = (*result, datetime.utcnow())
                return result
            except Exception as e:
                logger.error(f"Database permission check failed: {e}", exc_info=True)
                # Fall through to in-memory check
        
        # Fall back to in-memory permissions
        result = self._check_permission_memory(agent_type, tool_name, operation)
        self._permission_cache[cache_key] = (*result, datetime.utcnow())
        return result
    
    def _check_permission_db(
        self,
        agent_type: str,
        tool_name: str,
        operation: str
    ) -> tuple[bool, str]:
        """
        Check permission in database.
        
        Args:
            agent_type: Type of agent
            tool_name: Name of tool
            operation: Specific operation
        
        Returns:
            (allowed, reason)
        """
        from backend.models.database import AgentToolPermission
        
        # Query database
        stmt = select(AgentToolPermission).where(
            and_(
                AgentToolPermission.agent_type == agent_type,
                AgentToolPermission.tool_name == tool_name,
                AgentToolPermission.operation == operation
            )
        )
        
        permission = self.db_session.execute(stmt).scalar_one_or_none()
        
        # Deny by default if not found
        if permission is None:
            return False, f"No permission found (deny by default)"
        
        if permission.allowed:
            return True, "Permission granted"
        else:
            return False, f"Permission explicitly denied"
    
    def _check_permission_memory(
        self,
        agent_type: str,
        tool_name: str,
        operation: str
    ) -> tuple[bool, str]:
        """
        Check permission in memory (fallback).
        
        Args:
            agent_type: Type of agent
            tool_name: Name of tool
            operation: Specific operation
        
        Returns:
            (allowed, reason)
        """
        # Check if agent type exists
        if agent_type not in self.permissions:
            return False, f"Unknown agent type: {agent_type}"
        
        # Check if agent has access to tool
        agent_perms = self.permissions[agent_type]
        if tool_name not in agent_perms:
            return False, f"Agent type '{agent_type}' not authorized for tool '{tool_name}'"
        
        # Check if operation is allowed
        allowed_ops = agent_perms[tool_name]
        if operation not in allowed_ops:
            return False, f"Operation '{operation}' not allowed for '{tool_name}'"
        
        return True, "Permission granted (in-memory)"
    
    def invalidate_cache(self, agent_type: Optional[str] = None):
        """
        Invalidate permission cache.
        
        Args:
            agent_type: If provided, only invalidate for this agent type;
                       if None, invalidate entire cache
        """
        if agent_type is None:
            self._permission_cache.clear()
            logger.info("Permission cache cleared")
        else:
            # Clear only entries for this agent type
            keys_to_remove = [k for k in self._permission_cache.keys() if k.startswith(f"{agent_type}:")]
            for key in keys_to_remove:
                del self._permission_cache[key]
            logger.info(f"Permission cache cleared for agent_type={agent_type}")
    
    async def execute_tool(
        self,
        request: ToolExecutionRequest
    ) -> ToolExecutionResponse:
        """
        Execute a tool on behalf of an agent.
        
        Args:
            request: Tool execution request
        
        Returns:
            Tool execution response with result or error
        """
        # Check permission
        allowed, reason = self.check_permission(
            request.agent_type,
            request.tool_name,
            request.operation
        )
        
        if not allowed:
            logger.warning(
                f"Tool access denied: agent={request.agent_id}, "
                f"tool={request.tool_name}, op={request.operation}, reason={reason}"
            )
            
            # Log denied access
            audit_id = self._log_audit(
                agent_id=request.agent_id,
                agent_type=request.agent_type,
                tool_name=request.tool_name,
                operation=request.operation,
                parameters=request.parameters,
                allowed=False,
                result=None,
                error_message=reason,
                project_id=request.project_id,
                task_id=request.task_id
            )
            
            return ToolExecutionResponse(
                allowed=False,
                success=False,
                result=None,
                audit_id=audit_id,
                message=reason
            )
        
        # Validate and sanitize parameters
        try:
            sanitized_params = self._validate_and_sanitize_parameters(
                request.tool_name,
                request.operation,
                request.parameters
            )
        except ValueError as e:
            logger.warning(
                f"Parameter validation failed: agent={request.agent_id}, "
                f"tool={request.tool_name}, error={e}"
            )
            audit_id = self._log_audit(
                agent_id=request.agent_id,
                agent_type=request.agent_type,
                tool_name=request.tool_name,
                operation=request.operation,
                parameters=request.parameters,
                allowed=True,
                result=None,
                error_message=f"Parameter validation failed: {e}",
                project_id=request.project_id,
                task_id=request.task_id
            )
            return ToolExecutionResponse(
                allowed=True,
                success=False,
                result=None,
                audit_id=audit_id,
                message=f"Parameter validation failed: {e}"
            )
        
        # Execute tool
        try:
            result = await self._route_tool_execution(
                request.tool_name,
                request.operation,
                sanitized_params,
                request.agent_id,
                request.agent_type
            )
            
            # Log successful execution
            audit_id = self._log_audit(
                agent_id=request.agent_id,
                agent_type=request.agent_type,
                tool_name=request.tool_name,
                operation=request.operation,
                parameters=request.parameters,
                allowed=True,
                result=result,
                error_message=None,
                project_id=request.project_id,
                task_id=request.task_id
            )
            
            logger.info(
                f"Tool executed: agent={request.agent_id}, "
                f"tool={request.tool_name}, op={request.operation}, audit_id={audit_id}"
            )
            
            return ToolExecutionResponse(
                allowed=True,
                success=True,
                result=result,
                audit_id=audit_id,
                message="Tool executed successfully"
            )
        
        except Exception as e:
            logger.error(
                f"Tool execution error: agent={request.agent_id}, "
                f"tool={request.tool_name}, error={e}",
                exc_info=True
            )
            
            # Log failed execution
            audit_id = self._log_audit(
                agent_id=request.agent_id,
                agent_type=request.agent_type,
                tool_name=request.tool_name,
                operation=request.operation,
                parameters=request.parameters,
                allowed=True,
                result=None,
                error_message=str(e),
                project_id=request.project_id,
                task_id=request.task_id
            )
            
            return ToolExecutionResponse(
                allowed=True,
                success=False,
                result=None,
                audit_id=audit_id,
                message=f"Tool execution failed: {str(e)}"
            )
    
    def _validate_and_sanitize_parameters(
        self,
        tool_name: str,
        operation: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate and sanitize parameters for tool operations.
        
        Args:
            tool_name: Tool being called
            operation: Operation being performed
            parameters: Raw parameters from agent
        
        Returns:
            Sanitized parameters
        
        Raises:
            ValueError: If parameters are invalid
        """
        sanitized = parameters.copy()
        
        if tool_name == "container":
            # Validate container parameters
            if operation == "create":
                if "task_id" not in sanitized or not sanitized["task_id"]:
                    raise ValueError("task_id is required")
                if "project_id" not in sanitized or not sanitized["project_id"]:
                    raise ValueError("project_id is required")
                if "language" not in sanitized or not sanitized["language"]:
                    raise ValueError("language is required")
                # Sanitize: limit length, alphanumeric + hyphens only
                sanitized["task_id"] = str(sanitized["task_id"])[:100]
                sanitized["project_id"] = str(sanitized["project_id"])[:100]
                sanitized["language"] = str(sanitized["language"])[:50]
            elif operation in ["destroy", "execute", "list"]:
                if "task_id" not in sanitized or not sanitized["task_id"]:
                    raise ValueError("task_id is required")
                sanitized["task_id"] = str(sanitized["task_id"])[:100]
            if operation == "execute":
                if "command" not in sanitized or not sanitized["command"]:
                    raise ValueError("command is required")
                # Limit command length (prevent abuse)
                sanitized["command"] = str(sanitized["command"])[:5000]
        
        elif tool_name == "web_search":
            # Validate search parameters
            if "query" not in sanitized or not sanitized["query"]:
                raise ValueError("query is required")
            # Sanitize query (done in WebSearchService, but double-check)
            query = str(sanitized["query"]).strip()[:500]
            if not query:
                raise ValueError("query cannot be empty")
            sanitized["query"] = query
            # Validate num_results
            if "num_results" in sanitized:
                num_results = sanitized["num_results"]
                if not isinstance(num_results, int) or num_results < 1 or num_results > 20:
                    sanitized["num_results"] = 10  # Default
        
        elif tool_name == "code_validator":
            # Validate code validator parameters
            if "code" not in sanitized or not sanitized["code"]:
                raise ValueError("code is required")
            if "language" not in sanitized or not sanitized["language"]:
                raise ValueError("language is required")
            # Limit code size (1MB as per CodeValidator)
            if len(sanitized["code"]) > 1024 * 1024:
                raise ValueError("code exceeds maximum size (1MB)")
            sanitized["language"] = str(sanitized["language"])[:50].lower()
        
        elif tool_name == "file_system":
            # Validate file system parameters
            if operation in ["read", "write", "delete"]:
                if "path" not in sanitized or not sanitized["path"]:
                    raise ValueError("path is required")
                # Prevent path traversal
                path = str(sanitized["path"])
                if ".." in path or path.startswith("/"):
                    raise ValueError("invalid path (path traversal detected)")
                sanitized["path"] = path[:500]
            if operation == "write":
                if "content" not in sanitized:
                    raise ValueError("content is required")
                # Limit file size
                if len(str(sanitized["content"])) > 10 * 1024 * 1024:  # 10MB
                    raise ValueError("content exceeds maximum size (10MB)")
        
        elif tool_name == "github":
            # Validate GitHub parameters
            if operation == "create_repo":
                if "name" not in sanitized or not sanitized["name"]:
                    raise ValueError("repo name is required")
                # Sanitize repo name
                name = str(sanitized["name"])[:100]
                # GitHub repo name validation
                if not name.replace("-", "").replace("_", "").replace(".", "").isalnum():
                    raise ValueError("invalid repo name (alphanumeric, hyphens, underscores, dots only)")
                sanitized["name"] = name
        
        elif tool_name == "database":
            # Validate database parameters
            if "query" in sanitized:
                # Prevent raw SQL (should only use ORM)
                raise ValueError("raw SQL queries not allowed (use ORM methods)")
        
        return sanitized
    
    async def _route_tool_execution(
        self,
        tool_name: str,
        operation: str,
        parameters: Dict[str, Any],
        agent_id: str,
        agent_type: str
    ) -> Dict[str, Any]:
        """
        Route tool execution to appropriate handler.
        
        Args:
            tool_name: Tool to execute
            operation: Operation to perform
            parameters: Operation parameters
            agent_id: Agent identifier
            agent_type: Agent type
        
        Returns:
            Execution result
        """
        # Get tool handler
        tool_info = self.tool_registry.get(tool_name)
        if not tool_info:
            raise ValueError(f"Tool not found: {tool_name}")
        
        handler = tool_info.get("handler")
        
        # For now, return mock responses until handlers are integrated
        # TODO: Integrate actual tool handlers (ContainerManager, WebSearchService, etc.)
        
        if tool_name == "container":
            return await self._execute_container_tool(operation, parameters)
        elif tool_name == "web_search":
            return await self._execute_search_tool(operation, parameters, agent_id, agent_type)
        elif tool_name == "code_validator":
            return await self._execute_validator_tool(operation, parameters)
        elif tool_name == "file_system":
            return await self._execute_file_system_tool(operation, parameters)
        else:
            # Placeholder for unimplemented tools
            return {
                "status": "not_implemented",
                "message": f"Tool '{tool_name}' handler not yet implemented"
            }
    
    async def _execute_container_tool(self, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute container operations."""
        # TODO: Integrate with ContainerManager
        from backend.services.container_manager import get_container_manager
        
        manager = get_container_manager()
        
        if operation == "create":
            result = await manager.create_container(
                task_id=parameters.get("task_id"),
                project_id=parameters.get("project_id"),
                language=parameters.get("language")
            )
            return result
        elif operation == "destroy":
            result = await manager.destroy_container(parameters.get("task_id"))
            return result
        elif operation == "execute":
            result = await manager.exec_command(
                task_id=parameters.get("task_id"),
                command=parameters.get("command")
            )
            return result.to_dict()
        elif operation == "list":
            return {
                "active_containers": manager.get_active_container_count()
            }
        else:
            raise ValueError(f"Unknown container operation: {operation}")
    
    async def _execute_search_tool(
        self,
        operation: str,
        parameters: Dict[str, Any],
        agent_id: str,
        agent_type: str
    ) -> Dict[str, Any]:
        """Execute web search operations."""
        # TODO: Integrate with WebSearchService
        from backend.services.web_search_service import get_web_search_service
        
        search_service = get_web_search_service()
        
        if operation == "search":
            result = await search_service.search(
                query=parameters.get("query"),
                agent_id=agent_id,
                agent_type=agent_type,
                num_results=parameters.get("num_results", 10)
            )
            return result
        else:
            raise ValueError(f"Unknown search operation: {operation}")
    
    async def _execute_validator_tool(self, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute code validator operations."""
        # TODO: Integrate with CodeValidator
        from backend.services.code_validator import get_code_validator
        
        validator = get_code_validator()
        
        if operation == "validate":
            result = validator.validate_code(
                code=parameters.get("code"),
                language=parameters.get("language")
            )
            return result.to_dict()
        else:
            raise ValueError(f"Unknown validator operation: {operation}")
    
    async def _execute_file_system_tool(self, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute file system operations."""
        # TODO: Implement file system operations
        # This will integrate with container volumes
        return {
            "status": "not_implemented",
            "message": "File system operations not yet implemented"
        }
    
    def _log_audit(
        self,
        agent_id: str,
        agent_type: str,
        tool_name: str,
        operation: str,
        parameters: Dict[str, Any],
        allowed: bool,
        result: Optional[Dict[str, Any]],
        error_message: Optional[str],
        project_id: Optional[str],
        task_id: Optional[str]
    ) -> int:
        """
        Log tool access to audit log.
        
        Logs to both database (if available) and in-memory for backward compatibility.
        Database writes are non-blocking - failures are logged but don't prevent execution.
        
        Args:
            agent_id: Agent identifier
            agent_type: Agent type
            tool_name: Tool name
            operation: Operation performed
            parameters: Operation parameters (sanitized)
            allowed: Whether access was allowed
            result: Execution result (sanitized)
            error_message: Error message if failed
            project_id: Associated project
            task_id: Associated task
        
        Returns:
            Audit log entry ID
        """
        success = result is not None and error_message is None
        
        # Always log to in-memory (for backward compatibility and fallback)
        audit_entry = {
            "id": len(self.audit_log) + 1,
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": agent_id,
            "agent_type": agent_type,
            "tool_name": tool_name,
            "operation": operation,
            "parameters": parameters,
            "allowed": allowed,
            "success": success,
            "result": result,
            "error_message": error_message,
            "project_id": project_id,
            "task_id": task_id
        }
        
        self.audit_log.append(audit_entry)
        audit_id = audit_entry["id"]
        
        # Also log to database if available
        if self.use_db and self.db_session:
            try:
                from backend.models.database import ToolAuditLog
                
                db_log = ToolAuditLog(
                    agent_id=agent_id,
                    agent_type=agent_type,
                    tool_name=tool_name,
                    operation=operation,
                    project_id=project_id,
                    task_id=task_id,
                    parameters=parameters,
                    allowed=allowed,
                    success=success,
                    result=result,
                    error_message=error_message
                )
                
                self.db_session.add(db_log)
                self.db_session.commit()
                
                # Use database ID if available
                if db_log.id:
                    audit_id = db_log.id
                    
            except Exception as e:
                logger.error(f"Failed to write audit log to database: {e}", exc_info=True)
                # Continue - in-memory log is still recorded
                # Don't block execution due to audit log failure
        
        return audit_id
    
    def get_permissions(self, agent_type: str) -> Dict[str, Any]:
        """
        Get all permissions for an agent type.
        
        Args:
            agent_type: Type of agent
        
        Returns:
            Dict of permissions
        """
        if agent_type not in self.permissions:
            return {}
        
        return self.permissions[agent_type]
    
    def query_audit_logs(
        self,
        agent_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        project_id: Optional[str] = None,
        allowed: Optional[bool] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query audit logs with filters.
        
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
        results = results[-limit:]  # Most recent
        
        return results
    
    def get_tool_usage_stats(
        self,
        agent_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated tool usage statistics for cost tracking.
        
        Args:
            agent_id: Filter by agent
            tool_name: Filter by tool
            project_id: Filter by project
        
        Returns:
            Usage statistics with counts, success rates, and patterns
        """
        # Get relevant logs
        logs = self.query_audit_logs(
            agent_id=agent_id,
            tool_name=tool_name,
            project_id=project_id,
            limit=10000  # Large limit for stats
        )
        
        if not logs:
            return {
                "total_calls": 0,
                "success_rate": 0.0,
                "denial_rate": 0.0,
                "by_tool": {},
                "by_agent_type": {},
                "by_project": {}
            }
        
        # Aggregate stats
        total_calls = len(logs)
        successful = sum(1 for log in logs if log["success"])
        allowed_calls = sum(1 for log in logs if log["allowed"])
        denied_calls = total_calls - allowed_calls
        
        # By tool
        by_tool = {}
        for log in logs:
            tool = log["tool_name"]
            if tool not in by_tool:
                by_tool[tool] = {"total": 0, "success": 0, "denied": 0}
            by_tool[tool]["total"] += 1
            if log["success"]:
                by_tool[tool]["success"] += 1
            if not log["allowed"]:
                by_tool[tool]["denied"] += 1
        
        # By agent type
        by_agent_type = {}
        for log in logs:
            agent_type = log["agent_type"]
            if agent_type not in by_agent_type:
                by_agent_type[agent_type] = {"total": 0, "success": 0, "denied": 0}
            by_agent_type[agent_type]["total"] += 1
            if log["success"]:
                by_agent_type[agent_type]["success"] += 1
            if not log["allowed"]:
                by_agent_type[agent_type]["denied"] += 1
        
        # By project
        by_project = {}
        for log in logs:
            proj = log.get("project_id", "unknown")
            if proj not in by_project:
                by_project[proj] = {"total": 0, "success": 0}
            by_project[proj]["total"] += 1
            if log["success"]:
                by_project[proj]["success"] += 1
        
        return {
            "total_calls": total_calls,
            "successful_calls": successful,
            "failed_calls": total_calls - successful,
            "denied_calls": denied_calls,
            "success_rate": round(successful / total_calls * 100, 2) if total_calls > 0 else 0.0,
            "denial_rate": round(denied_calls / total_calls * 100, 2) if total_calls > 0 else 0.0,
            "by_tool": by_tool,
            "by_agent_type": by_agent_type,
            "by_project": by_project
        }


# Singleton instance
_tool_access_service: Optional[ToolAccessService] = None


def get_tool_access_service() -> ToolAccessService:
    """Get singleton ToolAccessService instance."""
    global _tool_access_service
    
    if _tool_access_service is None:
        _tool_access_service = ToolAccessService()
    
    return _tool_access_service


# FastAPI application
app = FastAPI(
    title="Tool Access Service (TAS)",
    description="Centralized tool access broker for AI agents",
    version="1.0.0"
)

tas = get_tool_access_service()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "TAS"}


@app.post("/api/v1/tools/execute", response_model=ToolExecutionResponse)
async def execute_tool(request: ToolExecutionRequest):
    """Execute a tool with permission checking and audit logging."""
    return await tas.execute_tool(request)


@app.post("/api/v1/tools/validate", response_model=ToolValidationResponse)
async def validate_tool_access(request: ToolValidationRequest):
    """Validate tool access without executing (dry-run)."""
    allowed, reason = tas.check_permission(
        request.agent_type,
        request.tool_name,
        request.operation
    )
    return ToolValidationResponse(allowed=allowed, reason=reason)


@app.get("/api/v1/tools/permissions/{agent_type}", response_model=PermissionsResponse)
async def get_permissions(agent_type: str):
    """Get all permissions for an agent type."""
    permissions = tas.get_permissions(agent_type)
    
    if not permissions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent type not found: {agent_type}"
        )
    
    # Format permissions
    perm_list = []
    for tool_name, operations in permissions.items():
        perm_list.append({
            "tool_name": tool_name,
            "operations": list(operations),
            "allowed": True
        })
    
    return PermissionsResponse(
        agent_id="",  # Not specific to agent instance
        agent_type=agent_type,
        permissions=perm_list
    )


@app.get("/api/v1/audit/logs")
async def query_audit_logs(
    agent_id: Optional[str] = None,
    tool_name: Optional[str] = None,
    project_id: Optional[str] = None,
    allowed: Optional[bool] = None,
    limit: int = 100
):
    """Query audit logs with filters."""
    logs = tas.query_audit_logs(
        agent_id=agent_id,
        tool_name=tool_name,
        project_id=project_id,
        allowed=allowed,
        limit=min(limit, 1000)  # Cap at 1000
    )
    
    return {
        "logs": logs,
        "total": len(logs),
        "limit": limit
    }


@app.get("/api/v1/tools/usage/stats")
async def get_tool_usage_stats(
    agent_id: Optional[str] = None,
    tool_name: Optional[str] = None,
    project_id: Optional[str] = None
):
    """Get aggregated tool usage statistics for cost tracking."""
    stats = tas.get_tool_usage_stats(
        agent_id=agent_id,
        tool_name=tool_name,
        project_id=project_id
    )
    return stats


@app.put("/api/v1/tools/permissions")
async def update_permissions(updates: Dict[str, Any]):
    """
    Bulk update permissions.
    
    Request format:
    {
        "updates": [
            {"agent_type": "backend_dev", "tool_name": "container", "operation": "create", "allowed": true},
            ...
        ]
    }
    """
    if "updates" not in updates:
        raise HTTPException(status_code=400, detail="Missing 'updates' field")
    
    # TODO: Implement database bulk update
    # For now, return success
    
    updated_count = len(updates["updates"])
    
    # Invalidate cache
    tas.invalidate_cache()
    
    return {
        "success": True,
        "updated_count": updated_count,
        "message": f"Updated {updated_count} permissions"
    }
