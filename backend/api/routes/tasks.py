"""
Tasks API Routes

Endpoints for executing tasks with agents.

Reference: MVP Demo - Task Execution
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import os
import uuid

from backend.api.dependencies import get_db
from backend.services.orchestrator import Orchestrator, Agent, Task, AgentType
from backend.services.openai_adapter import OpenAIAdapter
from backend.services.agent_llm_client import AgentLLMClient
from backend.agents.backend_dev_agent import BackendDevAgent
from backend.agents.frontend_dev_agent import FrontendDevAgent

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


# Pydantic models
class TaskExecuteRequest(BaseModel):
    """Request model for task execution."""
    goal: str = Field(..., min_length=1)
    description: Optional[str] = None
    agent_type: str = Field(..., pattern="^(backend_dev|frontend_dev)$")
    project_id: Optional[str] = None
    max_steps: int = Field(default=10, ge=1, le=50)
    acceptance_criteria: List[str] = Field(default_factory=list)


class TaskExecuteResponse(BaseModel):
    """Response model for task execution."""
    task_id: str
    status: str
    message: str


class TaskResultResponse(BaseModel):
    """Response model for task result."""
    task_id: str
    success: bool
    steps_taken: int
    confidence: Optional[float]
    artifacts: Dict[str, Any]
    errors: List[str]
    reasoning: List[str]


# In-memory task storage (MVP - would be DB in production)
task_results = {}


async def execute_task_async(
    task_id: str,
    goal: str,
    description: str,
    agent_type: str,
    project_id: str,
    max_steps: int,
    acceptance_criteria: List[str]
):
    """Execute task asynchronously."""
    try:
        # Create services
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            task_results[task_id] = {
                "success": False,
                "error": "OpenAI API key not configured"
            }
            return
        
        openai_adapter = OpenAIAdapter(api_key=api_key)
        llm_client = AgentLLMClient(openai_adapter)
        
        # Create mock orchestrator (simplified for MVP)
        class SimpleOrchestrator:
            async def execute_tool(self, payload):
                return {"status": "success", "result": "Tool executed"}
            
            async def create_gate(self, reason, context, agent_id):
                return str(uuid.uuid4())
            
            async def evaluate_confidence(self, payload):
                return 0.8
        
        orchestrator = SimpleOrchestrator()
        
        # Create appropriate agent
        if agent_type == "backend_dev":
            agent = BackendDevAgent(
                agent_id=f"backend-dev-{task_id[:8]}",
                orchestrator=orchestrator,
                llm_client=llm_client,
                openai_adapter=openai_adapter
            )
        else:  # frontend_dev
            agent = FrontendDevAgent(
                agent_id=f"frontend-dev-{task_id[:8]}",
                orchestrator=orchestrator,
                llm_client=llm_client,
                openai_adapter=openai_adapter
            )
        
        # Create task
        task = {
            "task_id": task_id,
            "project_id": project_id or str(uuid.uuid4()),
            "payload": {
                "goal": goal,
                "description": description,
                "acceptance_criteria": acceptance_criteria,
                "max_steps": max_steps,
                "constraints": {}
            }
        }
        
        # Execute task
        result = await agent.run_task(task)
        
        # Store result
        task_results[task_id] = {
            "success": result.success,
            "steps_taken": len(result.steps),
            "confidence": result.confidence,
            "artifacts": result.artifacts,
            "errors": result.errors,
            "reasoning": result.reasoning
        }
        
    except Exception as e:
        task_results[task_id] = {
            "success": False,
            "error": str(e),
            "steps_taken": 0,
            "artifacts": {},
            "errors": [str(e)],
            "reasoning": []
        }


@router.post("/execute", response_model=TaskExecuteResponse, status_code=202)
async def execute_task(
    request: TaskExecuteRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Execute a task with an agent.
    
    Creates and executes a task asynchronously. Returns immediately
    with task ID. Use GET /tasks/{task_id}/result to get the result.
    
    Supported agent types:
    - backend_dev: Python/FastAPI development
    - frontend_dev: React/TypeScript development
    """
    task_id = str(uuid.uuid4())
    
    # Initialize result
    task_results[task_id] = {
        "status": "running",
        "success": None
    }
    
    # Execute in background
    background_tasks.add_task(
        execute_task_async,
        task_id=task_id,
        goal=request.goal,
        description=request.description or "",
        agent_type=request.agent_type,
        project_id=request.project_id or str(uuid.uuid4()),
        max_steps=request.max_steps,
        acceptance_criteria=request.acceptance_criteria
    )
    
    return TaskExecuteResponse(
        task_id=task_id,
        status="accepted",
        message=f"Task execution started. Check /tasks/{task_id}/result for progress."
    )


@router.get("/{task_id}/result", response_model=TaskResultResponse)
async def get_task_result(task_id: str):
    """
    Get the result of a task execution.
    
    Returns the current status and results of the task.
    If task is still running, success will be None.
    """
    if task_id not in task_results:
        raise HTTPException(status_code=404, detail="Task not found")
    
    result = task_results[task_id]
    
    if result.get("status") == "running":
        raise HTTPException(
            status_code=202,
            detail="Task still running. Check back later."
        )
    
    return TaskResultResponse(
        task_id=task_id,
        success=result.get("success", False),
        steps_taken=result.get("steps_taken", 0),
        confidence=result.get("confidence"),
        artifacts=result.get("artifacts", {}),
        errors=result.get("errors", []),
        reasoning=result.get("reasoning", [])
    )
