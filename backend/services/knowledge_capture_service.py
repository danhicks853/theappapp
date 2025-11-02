"""
Knowledge Capture Service

Captures valuable collaborations and other knowledge for RAG storage.
Stores successful agent collaborations as learnings for future reference.

Reference: Decision 70 - Agent Collaboration Protocol
"""
import logging
import uuid
from datetime import datetime, UTC
from typing import Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class KnowledgeCaptureService:
    """
    Service for capturing valuable knowledge into RAG storage.
    
    Focuses on successful collaborations that should be preserved
    for future agent reference.
    
    Example:
        service = KnowledgeCaptureService(engine)
        
        await service.capture_collaboration_success(
            collaboration_id="collab-123",
            question="How do I prevent SQL injection?",
            answer="Use parameterized queries...",
            context={"agent_pair": "backend_dev->security_expert"}
        )
    """
    
    def __init__(self, engine: Engine):
        """Initialize knowledge capture service."""
        self.engine = engine
        logger.info("KnowledgeCaptureService initialized")
    
    async def capture_collaboration_success(
        self,
        collaboration_id: str,
        question: str,
        answer: str,
        *,
        agent_pair: str,
        question_type: str,
        resolution_approach: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Capture a successful collaboration for RAG storage.
        
        This method is triggered when a collaboration is marked as
        valuable_for_rag=True in the outcome.
        
        Args:
            collaboration_id: ID of the collaboration
            question: The original question asked
            answer: The specialist's response
            agent_pair: e.g., "backend_dev->security_expert"
            question_type: Type of question (from CollaborationRequestType)
            resolution_approach: How it was resolved
            context: Additional context
        
        Returns:
            Knowledge entry ID
        """
        knowledge_id = str(uuid.uuid4())
        
        logger.info(
            "Capturing collaboration knowledge | knowledge_id=%s | collaboration_id=%s | type=%s",
            knowledge_id,
            collaboration_id,
            question_type
        )
        
        # Create knowledge content
        content = self._format_knowledge_content(
            question=question,
            answer=answer,
            resolution_approach=resolution_approach,
            context=context
        )
        
        # Store in knowledge_staging table
        await self._store_knowledge(
            knowledge_id=knowledge_id,
            collaboration_id=collaboration_id,
            content=content,
            metadata={
                "agent_pair": agent_pair,
                "question_type": question_type,
                "resolution_approach": resolution_approach or "unknown",
                "source": "collaboration"
            }
        )
        
        logger.info(
            "Knowledge captured successfully | knowledge_id=%s | type=%s",
            knowledge_id,
            question_type
        )
        
        return knowledge_id
    
    def _format_knowledge_content(
        self,
        question: str,
        answer: str,
        resolution_approach: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """
        Format collaboration into structured knowledge content.
        
        Creates a markdown-formatted knowledge entry that's
        optimized for RAG retrieval.
        """
        parts = [
            "# Agent Collaboration Knowledge",
            "",
            "## Question",
            question,
            "",
            "## Answer",
            answer,
        ]
        
        if resolution_approach:
            parts.extend([
                "",
                "## Resolution Approach",
                resolution_approach,
            ])
        
        if context:
            parts.extend([
                "",
                "## Context",
                str(context),
            ])
        
        parts.extend([
            "",
            "## Tags",
            "- Source: Agent Collaboration",
            f"- Captured: {datetime.now(UTC).isoformat()}",
        ])
        
        return "\n".join(parts)
    
    async def _store_knowledge(
        self,
        knowledge_id: str,
        collaboration_id: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Store knowledge entry in staging table."""
        query = text("""
            INSERT INTO knowledge_staging
            (id, source_type, source_id, content, metadata, status, created_at)
            VALUES
            (:id, :source_type, :source_id, :content, :metadata, :status, :created_at)
        """)
        
        with self.engine.connect() as conn:
            conn.execute(query, {
                "id": knowledge_id,
                "source_type": "collaboration",
                "source_id": collaboration_id,
                "content": content,
                "metadata": str(metadata),  # JSON as text
                "status": "pending",
                "created_at": datetime.now(UTC)
            })
            conn.commit()
    
    async def get_knowledge_by_type(
        self,
        question_type: str,
        limit: int = 10
    ) -> list[Dict[str, Any]]:
        """
        Retrieve knowledge entries by question type.
        
        Useful for agents to look up similar past collaborations.
        
        Args:
            question_type: Type to filter by
            limit: Max entries to return
        
        Returns:
            List of knowledge entries
        """
        query = text("""
            SELECT id, content, metadata, created_at
            FROM knowledge_staging
            WHERE source_type = 'collaboration'
            AND metadata LIKE :question_type
            AND status = 'approved'
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                "question_type": f"%{question_type}%",
                "limit": limit
            })
            
            entries = []
            for row in result.fetchall():
                entries.append({
                    "id": row[0],
                    "content": row[1],
                    "metadata": row[2],
                    "created_at": row[3]
                })
            
            return entries
    
    async def mark_knowledge_approved(self, knowledge_id: str) -> None:
        """Approve a knowledge entry for RAG indexing."""
        query = text("""
            UPDATE knowledge_staging
            SET status = 'approved', approved_at = :approved_at
            WHERE id = :id
        """)
        
        with self.engine.connect() as conn:
            conn.execute(query, {
                "id": knowledge_id,
                "approved_at": datetime.now(UTC)
            })
            conn.commit()
        
        logger.info("Knowledge approved | knowledge_id=%s", knowledge_id)
    
    async def get_pending_knowledge_count(self) -> int:
        """Get count of pending knowledge entries."""
        query = text("""
            SELECT COUNT(*)
            FROM knowledge_staging
            WHERE status = 'pending'
            AND source_type = 'collaboration'
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query)
            return result.scalar() or 0
