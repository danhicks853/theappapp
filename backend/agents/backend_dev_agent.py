"""
Backend Developer Agent

Specializes in Python backend development, API creation, and database operations.
Inherits full execution framework from BaseAgent.

Reference: MVP Demo Plan - Built-in agents
"""
from typing import Any, Optional
from backend.agents.base_agent import BaseAgent


BACKEND_DEV_SYSTEM_PROMPT = """You are an expert Python backend developer specializing in:
- FastAPI and Flask application development
- RESTful API design and implementation  
- SQL database schema design and queries (PostgreSQL)
- Async Python programming
- Error handling and logging best practices
- Unit testing with pytest
- Code quality and PEP 8 compliance

Your responsibilities:
1. Write clean, efficient, production-ready Python code
2. Create comprehensive unit tests for all code
3. Follow best practices for API design
4. Optimize database queries
5. Handle errors gracefully with proper logging
6. Document code with clear docstrings

When given a task:
1. Analyze requirements carefully
2. Break down into logical steps
3. Write code with tests
4. Validate implementation against requirements
5. Provide clear explanations of your approach

Output format:
- Code blocks with language tags
- Inline comments for complex logic
- Docstrings for all functions/classes
- Test cases covering edge cases
"""


class BackendDevAgent(BaseAgent):
    """
    Backend Developer specialist agent.
    
    Capabilities:
    - Python/FastAPI development
    - Database design and queries
    - API endpoint creation
    - Unit test writing
    - Code review and optimization
    
    Example:
        agent = BackendDevAgent(
            agent_id="backend-dev-1",
            orchestrator=orchestrator,
            llm_client=llm_client,
            openai_adapter=openai_adapter
        )
        result = await agent.run_task(task)
    """
    
    def __init__(
        self,
        agent_id: str,
        orchestrator: Any,
        llm_client: Any,
        *,
        openai_adapter: Optional[Any] = None,
        rag_service: Optional[Any] = None,
        search_service: Optional[Any] = None,
        **kwargs
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="backend_dev",
            orchestrator=orchestrator,
            llm_client=llm_client,
            openai_adapter=openai_adapter,
            rag_service=rag_service,
            search_service=search_service,
            system_prompt=BACKEND_DEV_SYSTEM_PROMPT,
            **kwargs
        )
    
    async def _execute_internal_action(self, action: Any, state: Any, attempt: int):
        """
        Execute action directly (without tools).
        
        For backend dev, this means writing code, analyzing requirements, etc.
        MVP: Return action description as output (simulates work being done)
        """
        from backend.models.agent_state import Result
        
        # Simulate successful execution
        # In production, this would actually write files, run code, etc.
        return Result(
            success=True,
            output={
                "action": action.description,
                "operation": action.operation,
                "result": f"Completed: {action.description}"
            },
            error=None,
            metadata={"attempt": attempt},
            attempt=attempt
        )
