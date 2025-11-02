"""
Specialist Service

Business logic for creating and managing custom AI specialists.
Handles specialist CRUD, AI prompt generation, and document indexing.

Reference: MVP Demo Plan - Specialist Creation (Killer Feature)
"""
import logging
import uuid
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.openai_adapter import OpenAIAdapter
from backend.services.rag_service import RAGService

logger = logging.getLogger(__name__)


@dataclass
class Specialist:
    """Specialist data model."""
    id: str
    name: str
    description: str
    system_prompt: str
    scope: str  # 'global' or 'project'
    project_id: Optional[str]
    web_search_enabled: bool
    web_search_config: Optional[Dict[str, Any]]
    tools_enabled: Optional[Dict[str, Any]]
    created_at: str
    updated_at: str


class SpecialistService:
    """
    Service for managing AI specialists.
    
    Features:
    - Create custom specialists
    - Generate AI-powered system prompts
    - Index specialist documentation (RAG)
    - List and retrieve specialists
    - Update specialist configuration
    """
    
    def __init__(
        self,
        openai_adapter: Optional[OpenAIAdapter] = None,
        rag_service: Optional[RAGService] = None
    ):
        """
        Initialize specialist service.
        
        Args:
            openai_adapter: For AI prompt generation
            rag_service: For document indexing
        """
        self.openai = openai_adapter
        self.rag = rag_service
        logger.info("Specialist service initialized")
    
    async def create_specialist(
        self,
        name: str,
        description: str,
        system_prompt: str,
        scope: str = "global",
        project_id: Optional[str] = None,
        web_search_enabled: bool = False,
        web_search_config: Optional[Dict[str, Any]] = None,
        tools_enabled: Optional[Dict[str, Any]] = None,
        db: AsyncSession = None
    ) -> Specialist:
        """
        Create a new specialist.
        
        Args:
            name: Specialist name
            description: Brief description
            system_prompt: Full system prompt for LLM
            scope: 'global' or 'project'
            project_id: Required if scope='project'
            web_search_enabled: Enable web search
            web_search_config: Search configuration (scope, engines, etc.)
            tools_enabled: Tool permissions
            db: Database session
        
        Returns:
            Created specialist
        """
        logger.info(f"Creating specialist: {name}")
        
        specialist_id = str(uuid.uuid4())
        
        query = text("""
            INSERT INTO specialists (
                id, name, description, system_prompt, scope, project_id,
                web_search_enabled, web_search_config, tools_enabled,
                created_at, updated_at
            ) VALUES (
                :id, :name, :description, :system_prompt, :scope, :project_id,
                :web_search_enabled, :web_search_config, :tools_enabled,
                NOW(), NOW()
            )
            RETURNING id, name, description, system_prompt, scope, project_id,
                      web_search_enabled, web_search_config, tools_enabled,
                      created_at, updated_at
        """)
        
        result = await db.execute(query, {
            "id": specialist_id,
            "name": name,
            "description": description,
            "system_prompt": system_prompt,
            "scope": scope,
            "project_id": project_id,
            "web_search_enabled": web_search_enabled,
            "web_search_config": web_search_config,
            "tools_enabled": tools_enabled
        })
        
        await db.commit()
        row = result.first()
        
        specialist = self._row_to_specialist(row)
        logger.info(f"Specialist created: {specialist_id}")
        
        return specialist
    
    async def get_specialist(self, specialist_id: str, db: AsyncSession) -> Optional[Specialist]:
        """Get specialist by ID."""
        query = text("""
            SELECT id, name, description, system_prompt, scope, project_id,
                   web_search_enabled, web_search_config, tools_enabled,
                   created_at, updated_at
            FROM specialists
            WHERE id = :id
        """)
        
        result = await db.execute(query, {"id": specialist_id})
        row = result.first()
        
        if not row:
            return None
        
        return self._row_to_specialist(row)
    
    async def list_specialists(
        self,
        scope: Optional[str] = None,
        project_id: Optional[str] = None,
        db: AsyncSession = None
    ) -> List[Specialist]:
        """
        List specialists with optional filtering.
        
        Args:
            scope: Filter by scope ('global', 'project')
            project_id: Filter by project
            db: Database session
        
        Returns:
            List of specialists
        """
        conditions = []
        params = {}
        
        if scope:
            conditions.append("scope = :scope")
            params["scope"] = scope
        
        if project_id:
            conditions.append("project_id = :project_id")
            params["project_id"] = project_id
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        query = text(f"""
            SELECT id, name, description, system_prompt, scope, project_id,
                   web_search_enabled, web_search_config, tools_enabled,
                   created_at, updated_at
            FROM specialists
            {where_clause}
            ORDER BY created_at DESC
        """)
        
        result = await db.execute(query, params)
        rows = result.fetchall()
        
        specialists = [self._row_to_specialist(row) for row in rows]
        logger.info(f"Listed {len(specialists)} specialists")
        
        return specialists
    
    async def update_specialist(
        self,
        specialist_id: str,
        updates: Dict[str, Any],
        db: AsyncSession
    ) -> Optional[Specialist]:
        """
        Update specialist configuration.
        
        Args:
            specialist_id: Specialist ID
            updates: Fields to update
            db: Database session
        
        Returns:
            Updated specialist or None if not found
        """
        # Build SET clause
        set_parts = []
        params = {"id": specialist_id}
        
        for field in ["name", "description", "system_prompt", "web_search_enabled",
                      "web_search_config", "tools_enabled"]:
            if field in updates:
                set_parts.append(f"{field} = :{field}")
                params[field] = updates[field]
        
        if not set_parts:
            return await self.get_specialist(specialist_id, db)
        
        set_clause = ", ".join(set_parts)
        
        query = text(f"""
            UPDATE specialists
            SET {set_clause}, updated_at = NOW()
            WHERE id = :id
            RETURNING id, name, description, system_prompt, scope, project_id,
                      web_search_enabled, web_search_config, tools_enabled,
                      created_at, updated_at
        """)
        
        result = await db.execute(query, params)
        await db.commit()
        
        row = result.first()
        if not row:
            return None
        
        logger.info(f"Specialist updated: {specialist_id}")
        return self._row_to_specialist(row)
    
    async def index_documents(
        self,
        specialist_id: str,
        documents: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Index documents for specialist's RAG knowledge base.
        
        Args:
            specialist_id: Specialist ID
            documents: List of document texts
            metadata: Optional metadata for documents
        
        Returns:
            Number of chunks indexed
        """
        if not self.rag:
            logger.warning("RAG service not configured")
            return 0
        
        total_chunks = 0
        for doc in documents:
            chunks = await self.rag.index_document(
                text=doc,
                specialist_id=specialist_id,
                metadata=metadata
            )
            total_chunks += chunks
        
        logger.info(f"Indexed {total_chunks} chunks for specialist {specialist_id}")
        return total_chunks
    
    async def generate_system_prompt(
        self,
        name: str,
        description: str,
        role: str,
        capabilities: List[str],
        constraints: Optional[List[str]] = None
    ) -> str:
        """
        Generate system prompt using AI.
        
        Args:
            name: Specialist name
            description: What this specialist does
            role: Specialist's role
            capabilities: What specialist can do
            constraints: What specialist cannot do
        
        Returns:
            Generated system prompt
        """
        if not self.openai:
            logger.warning("OpenAI adapter not configured")
            return self._fallback_prompt(name, description, role, capabilities)
        
        logger.info(f"Generating system prompt for: {name}")
        
        # Build prompt for GPT-4
        caps_list = "\n".join(f"- {cap}" for cap in capabilities)
        constraints_text = ""
        if constraints:
            constraints_list = "\n".join(f"- {c}" for c in constraints)
            constraints_text = f"\n\nConstraints:\n{constraints_list}"
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert at creating AI agent system prompts. Create clear, detailed system prompts that define agent behavior, expertise, and output format."
            },
            {
                "role": "user",
                "content": f"""Create a system prompt for an AI specialist with these details:

Name: {name}
Role: {role}
Description: {description}

Capabilities:
{caps_list}{constraints_text}

Create a comprehensive system prompt that:
1. Defines the specialist's expertise and role
2. Lists their capabilities and responsibilities
3. Specifies output format and style
4. Sets clear expectations for quality

Return ONLY the system prompt text, no explanations."""
            }
        ]
        
        response = await self.openai.chat_completion(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7
        )
        
        prompt = response.choices[0].message.content.strip()
        logger.info(f"Generated {len(prompt)} character prompt")
        
        return prompt
    
    def _fallback_prompt(
        self,
        name: str,
        description: str,
        role: str,
        capabilities: List[str]
    ) -> str:
        """Generate basic prompt without AI."""
        caps = "\n".join(f"- {cap}" for cap in capabilities)
        return f"""You are {name}, {role}.

{description}

Your capabilities:
{caps}

Provide clear, professional responses that leverage your expertise."""
    
    def _row_to_specialist(self, row) -> Specialist:
        """Convert database row to Specialist object."""
        return Specialist(
            id=str(row[0]),
            name=row[1],
            description=row[2],
            system_prompt=row[3],
            scope=row[4],
            project_id=str(row[5]) if row[5] else None,
            web_search_enabled=row[6],
            web_search_config=row[7],
            tools_enabled=row[8],
            created_at=row[9].isoformat() if row[9] else None,
            updated_at=row[10].isoformat() if row[10] else None
        )
