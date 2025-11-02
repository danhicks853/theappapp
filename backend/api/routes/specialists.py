"""
Specialists API Routes

Endpoints for creating and managing custom AI specialists.

Reference: MVP Demo Plan - Specialist Creation API
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_db
from backend.services.specialist_service import SpecialistService, Specialist
from backend.services.openai_adapter import OpenAIAdapter
from backend.services.rag_service import RAGService
import os

router = APIRouter(prefix="/api/v1/specialists", tags=["specialists"])


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


@router.get("", response_model=List[SpecialistResponse])
async def list_specialists(
    scope: Optional[str] = None,
    project_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    service: SpecialistService = Depends(get_specialist_service)
):
    """
    List all specialists with optional filtering.
    
    Query parameters:
    - scope: Filter by 'global' or 'project'
    - project_id: Filter by project ID
    """
    specialists = await service.list_specialists(
        scope=scope,
        project_id=project_id,
        db=db
    )
    
    return [SpecialistResponse(**s.__dict__) for s in specialists]


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
