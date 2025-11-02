"""
Specialists API Routes

Endpoints for creating and managing custom AI specialists.

Reference: MVP Demo Plan - Specialist Creation API
"""
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_db
from backend.services.specialist_service import SpecialistService
from backend.services.openai_adapter import OpenAIAdapter
from backend.services.rag_service import RAGService
from backend.models.agent_types import validate_specialist_name, is_built_in_agent
import os

router = APIRouter(prefix="/api/v1/specialists", tags=["specialists"])
logger = logging.getLogger(__name__)


# Pydantic models
class SpecialistCreate(BaseModel):
    """Request model for creating specialist."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1)
    system_prompt: str = Field(..., min_length=1)
    scope: str = Field(default="global", pattern="^(global|project)$")
    project_id: Optional[str] = None
    web_search_enabled: bool = False
    web_search_config: Optional[Dict[str, Any]] = None
    tools_enabled: Optional[Dict[str, Any]] = None


class SpecialistUpdate(BaseModel):
    """Request model for updating specialist."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1)
    system_prompt: Optional[str] = Field(None, min_length=1)
    web_search_enabled: Optional[bool] = None
    web_search_config: Optional[Dict[str, Any]] = None
    tools_enabled: Optional[Dict[str, Any]] = None


class SpecialistResponse(BaseModel):
    """Response model for specialist."""
    id: str
    name: str
    description: str
    system_prompt: str
    scope: str
    project_id: Optional[str]
    web_search_enabled: bool
    web_search_config: Optional[Dict[str, Any]]
    tools_enabled: Optional[Dict[str, Any]]
    created_at: str
    updated_at: str


class GeneratePromptRequest(BaseModel):
    """Request model for AI prompt generation."""
    name: str
    description: str
    role: str
    capabilities: List[str]
    constraints: Optional[List[str]] = None


class GeneratePromptResponse(BaseModel):
    """Response model for generated prompt."""
    system_prompt: str


class AIAssistRequest(BaseModel):
    """Request model for AI assistant (flexible for UI use)."""
    prompt: str = Field(..., description="User's request or description of what they want")
    context: Optional[str] = Field(None, description="Optional context (current content, agent type, etc)")


class AIAssistResponse(BaseModel):
    """Response model for AI assistant."""
    suggestion: str = Field(..., description="AI-generated suggestion or content")


# Dependency to get specialist service
def get_specialist_service():
    """Get specialist service with dependencies."""
    api_key = os.getenv("OPENAI_API_KEY")
    openai_adapter = OpenAIAdapter(api_key=api_key) if api_key else None
    rag_service = RAGService(openai_adapter) if openai_adapter else None
    return SpecialistService(openai_adapter=openai_adapter, rag_service=rag_service)


@router.post("", response_model=SpecialistResponse, status_code=201)
async def create_specialist(
    specialist: SpecialistCreate,
    db: AsyncSession = Depends(get_db),
    service: SpecialistService = Depends(get_specialist_service)
):
    """
    Create a new AI specialist.
    
    Creates a custom specialist with specified configuration including:
    - System prompt for LLM behavior
    - Scope (global or project-specific)
    - Web search configuration
    - Tool permissions
    """
    # Validate name doesn't conflict with built-in agents
    if not validate_specialist_name(specialist.name):
        raise HTTPException(
            status_code=400, 
            detail=f"The name '{specialist.name}' is reserved for a built-in agent. Please choose a different name."
        )
    
    try:
        created = await service.create_specialist(
            name=specialist.name,
            description=specialist.description,
            system_prompt=specialist.system_prompt,
            scope=specialist.scope,
            project_id=specialist.project_id,
            web_search_enabled=specialist.web_search_enabled,
            web_search_config=specialist.web_search_config,
            tools_enabled=specialist.tools_enabled,
            db=db
        )
        
        return SpecialistResponse(**created.__dict__)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[dict])
def list_specialists(
    scope: Optional[str] = None,
    project_id: Optional[str] = None,
):
    """
    List all specialists with optional filtering.
    
    Query parameters:
    - scope: Filter by 'global' or 'project'
    - project_id: Filter by project ID
    """
    from backend.api.dependencies import _engine
    from sqlalchemy import text
    
    if _engine is None:
        raise HTTPException(status_code=500, detail="Database engine not initialized")
    
    with _engine.connect() as conn:
        # Build query with filters
        where_clauses = []
        params = {}
        
        if scope:
            where_clauses.append("scope = :scope")
            params["scope"] = scope
        if project_id:
            where_clauses.append("project_id = :project_id")
            params["project_id"] = project_id
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        query = text(f"""
            SELECT id, name, description, system_prompt, scope, project_id,
                   web_search_enabled, web_search_config, tools_enabled,
                   created_at, updated_at, version, template_id, installed_from_store,
                   display_name, avatar, bio, interests, favorite_tool, quote, required,
                   status, tags, model, temperature, max_tokens
            FROM specialists
            {where_sql}
            ORDER BY required DESC, created_at DESC
        """)
        
        result = conn.execute(query, params)
        rows = result.fetchall()
        
        specialists = []
        for row in rows:
            specialists.append({
                "id": str(row[0]),
                "name": row[1],
                "description": row[2],
                "system_prompt": row[3],
                "scope": row[4] or "global",
                "project_id": str(row[5]) if row[5] else None,
                "web_search_enabled": row[6] or False,
                "web_search_config": row[7],
                "tools_enabled": row[8],
                "created_at": row[9].isoformat() if row[9] else None,
                "updated_at": row[10].isoformat() if row[10] else None,
                "version": row[11],
                "template_id": row[12],
                "installed_from_store": row[13] or False,
                "display_name": row[14],
                "avatar": row[15],
                "bio": row[16],
                "interests": row[17] if row[17] else [],
                "favorite_tool": row[18],
                "quote": row[19],
                "required": row[20] or False,
                "status": row[21] or "active",
                "tags": row[22] if row[22] else [],
                "model": row[23] or "gpt-4",
                "temperature": float(row[24]) if row[24] else 0.7,
                "max_tokens": row[25] or 4000,
            })
        
        # Filter out any specialists with built-in agent names (shouldn't exist but just in case)
        specialists = [s for s in specialists if not is_built_in_agent(s["name"])]
        
        return specialists


@router.get("/{specialist_id}", response_model=SpecialistResponse)
async def get_specialist(
    specialist_id: str,
    db: AsyncSession = Depends(get_db),
    service: SpecialistService = Depends(get_specialist_service)
):
    """Get a specific specialist by ID."""
    specialist = await service.get_specialist(specialist_id, db)
    
    if not specialist:
        raise HTTPException(status_code=404, detail="Specialist not found")
    
    return SpecialistResponse(**specialist.__dict__)


@router.put("/{specialist_id}", response_model=SpecialistResponse)
async def update_specialist(
    specialist_id: str,
    updates: SpecialistUpdate,
    db: AsyncSession = Depends(get_db),
    service: SpecialistService = Depends(get_specialist_service)
):
    """Update specialist configuration."""
    # Convert to dict, excluding None values
    update_dict = {k: v for k, v in updates.dict().items() if v is not None}
    
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updated = await service.update_specialist(specialist_id, update_dict, db)
    
    if not updated:
        raise HTTPException(status_code=404, detail="Specialist not found")
    
    return SpecialistResponse(**updated.__dict__)


@router.post("/generate-prompt", response_model=GeneratePromptResponse)
async def generate_prompt(
    request: GeneratePromptRequest,
    service: SpecialistService = Depends(get_specialist_service)
):
    """
    Generate system prompt using AI.
    
    Takes specialist details and uses GPT-4 to generate
    a comprehensive, well-structured system prompt.
    """
    try:
        prompt = await service.generate_system_prompt(
            name=request.name,
            description=request.description,
            role=request.role,
            capabilities=request.capabilities,
            constraints=request.constraints
        )
        
        return GeneratePromptResponse(system_prompt=prompt)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai-assist", response_model=AIAssistResponse)
async def ai_assist(
    request: AIAssistRequest,
    service: SpecialistService = Depends(get_specialist_service)
):
    """
    Flexible AI assistant endpoint for UI help.
    
    This endpoint is designed to be used throughout the UI wherever users
    need AI assistance. It takes a simple prompt and optional context.
    
    Use cases:
    - Prompt editing assistance
    - Content generation
    - Text improvement suggestions
    - Writing help
    
    Example requests:
    - "Add error handling guidelines"
    - "Make this more concise"
    - "Add examples for API usage"
    """
    try:
        if not service.openai:
            raise HTTPException(
                status_code=503,
                detail="AI service not configured. Please set OPENAI_API_KEY."
            )
        
        # Build messages for AI
        system_content = """You are a helpful AI assistant specializing in writing clear, 
comprehensive technical content. You help users improve prompts, documentation, and 
guidelines for AI agents. Provide direct, actionable suggestions."""
        
        user_content = request.prompt
        if request.context:
            user_content = f"Context: {request.context}\n\nRequest: {request.prompt}"
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]
        
        response = await service.openai.chat_completion(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        suggestion = response.choices[0].message.content.strip()
        
        return AIAssistResponse(suggestion=suggestion)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI assist error: {e}")
        raise HTTPException(status_code=500, detail=f"AI assistance failed: {str(e)}")


@router.delete("/{specialist_id}", status_code=204)
def delete_specialist(
    specialist_id: str,
):
    """
    Delete a specialist.
    
    Cannot delete required specialists (frontend_developer, backend_developer, orchestrator).
    """
    from backend.api.dependencies import _engine
    from sqlalchemy import text
    
    if _engine is None:
        raise HTTPException(status_code=500, detail="Database engine not initialized")
    
    with _engine.connect() as conn:
        # Check if specialist is required
        result = conn.execute(
            text("SELECT required FROM specialists WHERE id = :id"),
            {"id": specialist_id}
        )
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Specialist not found")
        
        if row[0]:  # required is True
            raise HTTPException(
                status_code=403, 
                detail="Cannot delete required specialists. Frontend Dev, Backend Dev, and Orchestrator are core to TheAppApp."
            )
        
        # Delete the specialist
        conn.execute(
            text("DELETE FROM specialists WHERE id = :id"),
            {"id": specialist_id}
        )
        conn.commit()
    
    return None


@router.post("/{specialist_id}/documents", status_code=202)
async def upload_documents(
    specialist_id: str,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    service: SpecialistService = Depends(get_specialist_service)
):
    """
    Upload documents for specialist's knowledge base (RAG).
    
    Uploads and indexes documents so the specialist can
    reference them when answering questions.
    """
    # Verify specialist exists
    specialist = await service.get_specialist(specialist_id, db)
    if not specialist:
        raise HTTPException(status_code=404, detail="Specialist not found")
    
    # Read and index documents
    documents = []
    for file in files:
        content = await file.read()
        text = content.decode('utf-8')  # Assume UTF-8 text files
        documents.append(text)
    
    total_chunks = await service.index_documents(
        specialist_id=specialist_id,
        documents=documents,
        metadata={"filenames": [f.filename for f in files]}
    )
    
    return {
        "status": "accepted",
        "files_uploaded": len(files),
        "chunks_indexed": total_chunks,
        "specialist_id": specialist_id
    }
