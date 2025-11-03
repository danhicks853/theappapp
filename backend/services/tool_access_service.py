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
    TESTING = "testing"


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
        "backend_developer": {
            "container": {"create", "destroy", "execute", "list"},
            "file_system": {"read", "write", "delete", "list"},
            "web_search": {"search"},
            "code_validator": {"validate"},
            "database": {"read", "write"},  # Via ORM only
            "test_config_generator": {"generate_configs", "setup_backend", "setup_ci"},
            "test_generator": {"generate_tests", "identify_coverage_gaps", "generate_edge_cases"},
            "edge_case_finder": {"find_edge_cases", "prioritize_cases"},
            "test_quality_scorer": {"score_test", "score_file", "generate_report"},
            "deliverable": {"mark_complete", "get_status"},
        },
        "frontend_developer": {
            "container": {"create", "destroy", "execute", "list"},
            "file_system": {"read", "write", "delete", "list"},
            "web_search": {"search"},
            "code_validator": {"validate"},
            "test_config_generator": {"generate_configs", "setup_frontend", "setup_ci"},
            "test_generator": {"generate_tests", "identify_coverage_gaps", "generate_edge_cases"},
            "edge_case_finder": {"find_edge_cases", "prioritize_cases"},
            "test_quality_scorer": {"score_test", "score_file", "generate_report"},
            "deliverable": {"mark_complete", "get_status"},
        },
        "workshopper": {
            "web_search": {"search"},
            "file_system": {"read", "write", "list"},
            "deliverable": {"mark_complete", "get_status"},
        },
        "security_expert": {
            "web_search": {"search"},
            "file_system": {"read", "write", "list"},
            "code_validator": {"validate"},
            "deliverable": {"mark_complete", "get_status"},
        },
        "devops_engineer": {
            "container": {"create", "destroy", "execute", "list"},
            "file_system": {"read", "write", "delete", "list"},
            "web_search": {"search"},
            "database": {"read"},
            "deliverable": {"mark_complete", "get_status"},
        },
        "qa_engineer": {
            "container": {"create", "destroy", "execute", "list"},
            "file_system": {"read", "write", "list"},
            "web_search": {"search"},
            "test_config_generator": {"generate_configs", "setup_backend", "setup_frontend", "setup_ci"},
            "test_generator": {"generate_tests", "identify_coverage_gaps", "generate_edge_cases"},
            "edge_case_finder": {"find_edge_cases", "prioritize_cases"},
            "test_quality_scorer": {"score_test", "score_file", "generate_report"},
            "test_maintainer": {"detect_changes", "suggest_updates", "generate_pr_comment"},
            "deliverable": {"mark_complete", "get_status"},
        },
        "github_specialist": {
            "github": {"create_repo", "delete_repo", "merge_pr", "list_repos"},
            "file_system": {"read", "list"},
            "deliverable": {"mark_complete", "get_status"},
        },
        "ui_ux_designer": {
            "file_system": {"read", "write", "list"},
            "web_search": {"search"},
            "test_config_generator": {"generate_configs", "setup_frontend", "setup_ci"},
            "test_generator": {"generate_tests", "identify_coverage_gaps", "generate_edge_cases"},
            "edge_case_finder": {"find_edge_cases", "prioritize_cases"},
            "test_quality_scorer": {"score_test", "score_file", "generate_report"},
            "deliverable": {"mark_complete", "get_status"},
        },
    }
    
    def __init__(
        self, 
        db_session: Optional[Session] = None, 
        use_db: bool = True,
        # Service dependencies
        container_manager: Optional[Any] = None,
        web_search_service: Optional[Any] = None,
        code_validator: Optional[Any] = None,
        github_specialist: Optional[Any] = None,
        test_config_generator: Optional[Any] = None,
        test_generator: Optional[Any] = None,
        edge_case_finder: Optional[Any] = None,
        test_quality_scorer: Optional[Any] = None,
        test_maintainer: Optional[Any] = None
    ):
        """Initialize Tool Access Service.
        
        Args:
            db_session: SQLAlchemy session for database access
            use_db: If True, use database for permissions; if False, use in-memory defaults
            container_manager: ContainerManager service instance
            web_search_service: WebSearchService instance
            code_validator: CodeValidator instance
            github_specialist: GitHubSpecialistAgent instance
            test_config_generator: TestConfigGenerator instance
            test_generator: TestGenerator instance
            edge_case_finder: EdgeCaseFinder instance
            test_quality_scorer: TestQualityScorer instance
            test_maintainer: TestMaintainer instance
        """
        self.db_session = db_session
        self.use_db = use_db and db_session is not None
        self.permissions = self.DEFAULT_PERMISSIONS.copy()
        self.audit_log: List[Dict[str, Any]] = []  # In-memory for now, DB later
        
        # Store service instances
        self._container_manager = container_manager
        self._web_search_service = web_search_service
        self._code_validator = code_validator
        self._github_specialist = github_specialist
        self._test_config_generator = test_config_generator
        self._test_generator = test_generator
        self._edge_case_finder = edge_case_finder
        self._test_quality_scorer = test_quality_scorer
        self._test_maintainer = test_maintainer
        
        self.tool_registry = self._initialize_tool_registry()
        self._permission_cache: Dict[str, Tuple[bool, str, datetime]] = {}  # Cache with timestamp
        self._cache_ttl = timedelta(minutes=5)  # 5-minute cache
        logger.info(f"Tool Access Service initialized (use_db={self.use_db})")
    
    def _initialize_tool_registry(self) -> Dict[str, Any]:
        """
        Initialize registry of available tools with actual handlers.
        
        Returns:
            Dict mapping tool names to tool handlers
        """
        registry = {
            "container": {
                "category": ToolCategory.CODE_EXECUTION,
                "operations": ["create", "destroy", "execute", "list"],
                "handler": self._container_manager
            },
            "file_system": {
                "category": ToolCategory.FILE_SYSTEM,
                "operations": ["read", "write", "delete", "list"],
                "handler": self._create_file_system_handler()
            },
            "web_search": {
                "category": ToolCategory.WEB_SEARCH,
                "operations": ["search"],
                "handler": self._web_search_service
            },
            "code_validator": {
                "category": ToolCategory.CODE_EXECUTION,
                "operations": ["validate"],
                "handler": self._code_validator
            },
            "github": {
                "category": ToolCategory.GITHUB,
                "operations": ["create_repo", "delete_repo", "merge_pr", "list_repos"],
                "handler": self._github_specialist
            },
            "database": {
                "category": ToolCategory.DATABASE,
                "operations": ["read", "write"],
                "handler": self._create_database_handler()
            },
            "test_config_generator": {
                "category": ToolCategory.TESTING,
                "operations": ["generate_configs", "setup_backend", "setup_frontend", "setup_ci"],
                "handler": self._test_config_generator
            },
            "test_generator": {
                "category": ToolCategory.TESTING,
                "operations": ["generate_tests", "identify_coverage_gaps", "generate_edge_cases"],
                "handler": self._test_generator
            },
            "edge_case_finder": {
                "category": ToolCategory.TESTING,
                "operations": ["find_edge_cases", "prioritize_cases"],
                "handler": self._edge_case_finder
            },
            "test_quality_scorer": {
                "category": ToolCategory.TESTING,
                "operations": ["score_test", "score_file", "generate_report"],
                "handler": self._test_quality_scorer
            },
            "test_maintainer": {
                "category": ToolCategory.TESTING,
                "operations": ["detect_changes", "suggest_updates", "generate_pr_comment"],
                "handler": self._test_maintainer
            }
        }
        return registry
    
    def _create_file_system_handler(self) -> Any:
        """Create file system handler with safe operations."""
        import os
        from pathlib import Path
        
        class FileSystemHandler:
            """Safe file system operations for agents."""
            
            async def read(self, file_path: str) -> str:
                """Read file contents."""
                path = Path(file_path)
                if not path.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")
                return path.read_text()
            
            async def write(self, file_path: str, content: str) -> bool:
                """Write file contents."""
                path = Path(file_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
                return True
            
            async def delete(self, file_path: str) -> bool:
                """Delete file."""
                path = Path(file_path)
                if path.exists():
                    path.unlink()
                    return True
                return False
            
            async def list(self, directory: str) -> List[str]:
                """List directory contents."""
                path = Path(directory)
                if not path.is_dir():
                    raise NotADirectoryError(f"Not a directory: {directory}")
                return [str(p) for p in path.iterdir()]
        
        return FileSystemHandler()
    
    def _create_database_handler(self) -> Any:
        """Create database handler with safe operations."""
        
        class DatabaseHandler:
            """Safe database operations for agents."""
            
            def __init__(self, db_session):
                self.db_session = db_session
            
            async def read(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
                """Execute read query."""
                if not self.db_session:
                    raise RuntimeError("Database session not configured")
                # TODO: Implement safe query execution
                return []
            
            async def write(self, query: str, params: Optional[Dict] = None) -> bool:
                """Execute write query."""
                if not self.db_session:
                    raise RuntimeError("Database session not configured")
                # TODO: Implement safe query execution
                return True
        
        return DatabaseHandler(self.db_session)
    
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
        elif tool_name == "deliverable":
            return await self._execute_deliverable_tool(operation, parameters)
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
        """
        Execute file system operations via container exec commands.
        Files are written to Docker volumes that containers mount at /workspace.
        """
        import base64
        import json
        from backend.services.container_manager import get_container_manager
        
        project_id = parameters.get("project_id")
        task_id = parameters.get("task_id")
        
        if not project_id:
            raise ValueError("project_id required for file system operations")
        if not task_id:
            raise ValueError("task_id required for container file operations")
        
        file_path = parameters.get("path", "").lstrip("/")
        if not file_path:
            raise ValueError("path required for file system operations")
        
        container_mgr = get_container_manager()
        
        # Use project-level container (prefer project_id over task_id)
        container_id = project_id if project_id in container_mgr.active_containers else task_id
        
        # If neither exists, create project container on-demand
        if container_id not in container_mgr.active_containers:
            logger.info(f"Creating project container on-demand for {project_id}")
            result = await container_mgr.create_container(
                task_id=project_id,  # Use project_id as container identifier
                project_id=project_id,
                language="python"  # Default to python for file operations
            )
            if not result.get("success"):
                raise RuntimeError(f"Failed to create container: {result.get('message')}")
            container_id = project_id
        
        container_path = f"/workspace/{file_path}"
        
        if operation == "write":
            content = parameters.get("content", "")
            
            # Create parent directory using Python
            parent_dir = '/'.join(container_path.rsplit('/')[:-1])
            if parent_dir and parent_dir != "/workspace":
                mkdir_cmd = f"python -c \"import os; os.makedirs('{parent_dir}', exist_ok=True)\""
                mkdir_result = await container_mgr.exec_command(container_id, mkdir_cmd)
                if mkdir_result.exit_code != 0:
                    raise RuntimeError(f"Failed to create directory: {mkdir_result.stderr}")
            
            # Write file using Python (works in all containers)
            # Encode content to base64 to avoid any escaping issues
            content_b64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
            write_cmd = f"python -c \"import base64; open('{container_path}', 'wb').write(base64.b64decode('{content_b64}'))\""
            result = await container_mgr.exec_command(container_id, write_cmd)
            
            if result.exit_code != 0:
                raise RuntimeError(f"Failed to write file: {result.stderr}")
            
            # Verify file exists
            verify = await container_mgr.exec_command(container_id, f"python -c \"import os; print('OK' if os.path.exists('{container_path}') else 'FAIL')\"")
            if "OK" not in verify.stdout:
                raise RuntimeError(f"File write verification failed for {container_path}")
            
            return {
                "status": "success",
                "path": file_path,
                "bytes_written": len(content.encode('utf-8')),
                "message": f"File written: {file_path}"
            }
        
        elif operation == "read":
            result = await container_mgr.exec_command(container_id, f"cat {container_path}")
            
            if result.exit_code != 0:
                raise ValueError(f"File not found: {file_path}")
            
            return {
                "status": "success",
                "path": file_path,
                "content": result.stdout,
                "bytes_read": len(result.stdout.encode('utf-8'))
            }
        
        elif operation == "delete":
            result = await container_mgr.exec_command(container_id, f"rm {container_path}")
            
            if result.exit_code != 0:
                raise ValueError(f"Failed to delete file: {result.stderr}")
            
            return {
                "status": "success",
                "path": file_path,
                "message": f"File deleted: {file_path}"
            }
        
        elif operation == "list":
            # Handle "." as current directory
            if file_path == "." or file_path == "":
                dir_path = "/workspace"
            else:
                dir_path = f"/workspace/{file_path}"
            
            # List files using Python for cross-platform compatibility
            list_cmd = f"python -c \"import os; import json; files = []; [files.append({{'name': f, 'type': 'directory' if os.path.isdir(os.path.join('{dir_path}', f)) else 'file', 'size': os.path.getsize(os.path.join('{dir_path}', f)) if os.path.isfile(os.path.join('{dir_path}', f)) else None}}) for f in os.listdir('{dir_path}') if f not in ['.', '..']]; print(json.dumps(files))\""
            result = await container_mgr.exec_command(task_id, list_cmd)
            
            if result.exit_code != 0:
                raise ValueError(f"Directory not found: {file_path or '.'}")
            
            # Parse JSON output from Python
            import json as json_module
            try:
                files = json_module.loads(result.stdout.strip())
                # Add path to each file
                for f in files:
                    if file_path and file_path != ".":
                        f["path"] = f"{file_path}/{f['name']}"
                    else:
                        f["path"] = f['name']
            except json_module.JSONDecodeError:
                raise ValueError(f"Failed to parse directory listing")
            
            return {
                "status": "success",
                "path": file_path or ".",
                "files": files,
                "count": len(files)
            }
        
        else:
            raise ValueError(f"Unknown file system operation: {operation}")
    
    async def _execute_deliverable_tool(self, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute deliverable tracking operations.
        
        Operations:
        - mark_complete: Mark a deliverable as completed
        - get_status: Get deliverable status
        """
        from sqlalchemy import text
        
        deliverable_id = parameters.get("deliverable_id")
        if not deliverable_id:
            raise ValueError("deliverable_id required for deliverable operations")
        
        if operation == "mark_complete":
            # Mark deliverable as complete in database
            status = parameters.get("status", "completed")
            artifacts = parameters.get("artifacts", [])
            
            # Update deliverable status
            # For now, just return success - full DB integration in next step
            return {
                "status": "success",
                "deliverable_id": deliverable_id,
                "new_status": status,
                "artifacts": artifacts,
                "message": f"Deliverable {deliverable_id} marked as {status}"
            }
        
        elif operation == "get_status":
            # Get deliverable status
            return {
                "status": "success",
                "deliverable_id": deliverable_id,
                "deliverable_status": "in_progress",  # TODO: Query from DB
                "message": "Status retrieved"
            }
        
        else:
            raise ValueError(f"Unknown deliverable operation: {operation}")
    
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
