"""
Knowledge Capture Service

Captures valuable knowledge for RAG storage including:
- Successful agent collaborations
- Failure solutions
- Gate rejections with feedback
- Gate approvals (first-attempt successes)

Reference: Decision 68 - RAG System Architecture, Decision 70 - Agent Collaboration Protocol
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
            source_id=collaboration_id,
            content=content,
            knowledge_type="collaboration",
            metadata={
                "agent_pair": agent_pair,
                "question_type": question_type,
                "resolution_approach": resolution_approach or "unknown",
                "success_verified": True
            }
        )
        
        logger.info(
            "Knowledge captured successfully | knowledge_id=%s | type=%s",
            knowledge_id,
            question_type
        )
        
        return knowledge_id
    
    async def capture_failure_solution(
        self,
        task_id: str,
        agent_id: str,
        agent_type: str,
        failure_description: str,
        solution_description: str,
        *,
        project_id: Optional[str] = None,
        task_type: Optional[str] = None,
        technology: Optional[str] = None,
        error_type: Optional[str] = None,
        quality_score: str = "high"
    ) -> str:
        """
        Capture a failure and its solution for future reference.
        
        Triggered when a task fails but eventually succeeds, capturing
        the learning for future similar situations.
        
        Args:
            task_id: Task that failed then succeeded
            agent_id: Agent that solved it
            agent_type: Type of agent
            failure_description: What went wrong
            solution_description: How it was fixed
            project_id: Project context
            task_type: Type of task
            technology: Technology involved
            error_type: Type of error encountered
        
        Returns:
            Knowledge entry ID
        """
        knowledge_id = str(uuid.uuid4())
        
        logger.info(
            "Capturing failure solution | knowledge_id=%s | task_id=%s | agent=%s",
            knowledge_id,
            task_id,
            agent_type
        )
        
        # Format content
        content = f"""# Failure Solution

## Problem
{failure_description}

## Solution
{solution_description}

## Context
- Agent: {agent_type}
- Task Type: {task_type or 'unknown'}
- Technology: {technology or 'unknown'}
- Error Type: {error_type or 'unknown'}

## Tags
- Source: Failure Solution
- Captured: {datetime.now(UTC).isoformat()}
"""
        
        # Store in knowledge_staging
        await self._store_knowledge(
            knowledge_id=knowledge_id,
            source_id=task_id,
            content=content,
            knowledge_type="failure_solution",
            metadata={
                "project_id": project_id or "unknown",
                "agent_type": agent_type,
                "task_type": task_type or "unknown",
                "technology": technology or "unknown",
                "error_type": error_type or "unknown",
                "success_verified": True,
                "quality_score": quality_score,
                "success_count": 0,
                "last_used_at": None
            }
        )
        
        return knowledge_id
    
    async def capture_gate_rejection(
        self,
        gate_id: str,
        agent_id: str,
        agent_type: str,
        rejection_reason: str,
        feedback: str,
        *,
        project_id: Optional[str] = None,
        task_type: Optional[str] = None,
        gate_type: Optional[str] = None
    ) -> str:
        """
        Capture human gate rejection with feedback.
        
        When a human rejects an agent's work, capture the feedback
        as a learning example of what NOT to do.
        
        Args:
            gate_id: Gate that was rejected
            agent_id: Agent whose work was rejected
            agent_type: Type of agent
            rejection_reason: Why gate was created
            feedback: Human feedback on what was wrong
            project_id: Project context
            task_type: Type of task
            gate_type: Type of gate
        
        Returns:
            Knowledge entry ID
        """
        knowledge_id = str(uuid.uuid4())
        
        logger.info(
            "Capturing gate rejection | knowledge_id=%s | gate_id=%s | agent=%s",
            knowledge_id,
            gate_id,
            agent_type
        )
        
        # Format content
        content = f"""# Gate Rejection Learning

## What Was Attempted
{rejection_reason}

## Why It Was Rejected
{feedback}

## Lesson
This approach should be avoided or improved in similar situations.

## Context
- Agent: {agent_type}
- Task Type: {task_type or 'unknown'}
- Gate Type: {gate_type or 'unknown'}

## Tags
- Source: Gate Rejection
- Captured: {datetime.now(UTC).isoformat()}
"""
        
        # Store in knowledge_staging
        await self._store_knowledge(
            knowledge_id=knowledge_id,
            source_id=gate_id,
            content=content,
            knowledge_type="gate_rejection",
            metadata={
                "project_id": project_id or "unknown",
                "agent_type": agent_type,
                "task_type": task_type or "unknown",
                "gate_type": gate_type or "unknown",
                "success_verified": False  # This is a negative example
            }
        )
        
        return knowledge_id
    
    async def capture_gate_approval(
        self,
        gate_id: str,
        agent_id: str,
        agent_type: str,
        gate_reason: str,
        approval_notes: Optional[str] = None,
        *,
        project_id: Optional[str] = None,
        task_type: Optional[str] = None,
        first_attempt: bool = False
    ) -> str:
        """
        Capture first-attempt gate approval as successful pattern.
        
        When agent work is approved on the first try without iterations,
        capture it as a successful pattern to replicate.
        
        Args:
            gate_id: Gate that was approved
            agent_id: Agent whose work was approved
            agent_type: Type of agent
            gate_reason: Why gate was created
            approval_notes: Optional approval notes
            project_id: Project context
            task_type: Type of task
            first_attempt: Was this approved on first try?
        
        Returns:
            Knowledge entry ID or None if not worth capturing
        """
        # Only capture first-attempt approvals
        if not first_attempt:
            logger.debug("Skipping gate approval (not first attempt)")
            return None
        
        knowledge_id = str(uuid.uuid4())
        
        logger.info(
            "Capturing gate approval (first attempt) | knowledge_id=%s | gate_id=%s | agent=%s",
            knowledge_id,
            gate_id,
            agent_type
        )
        
        # Format content
        notes_section = f"\n## Approval Notes\n{approval_notes}" if approval_notes else ""
        
        content = f"""# Successful First-Attempt Approval

## What Was Done
{gate_reason}

## Why It Was Approved on First Try
This approach worked correctly without needing revisions.{notes_section}

## Lesson
This pattern can be replicated in similar situations.

## Context
- Agent: {agent_type}
- Task Type: {task_type or 'unknown'}

## Tags
- Source: Gate Approval (First Attempt)
- Captured: {datetime.now(UTC).isoformat()}
"""
        
        # Store in knowledge_staging
        await self._store_knowledge(
            knowledge_id=knowledge_id,
            source_id=gate_id,
            content=content,
            knowledge_type="gate_approval",
            metadata={
                "project_id": project_id or "unknown",
                "agent_type": agent_type,
                "task_type": task_type or "unknown",
                "first_attempt": True,
                "success_verified": True  # Positive example
            }
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
        source_id: str,
        content: str,
        knowledge_type: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Store knowledge entry in staging table."""
        import json
        
        query = text("""
            INSERT INTO knowledge_staging
            (id, knowledge_type, content, metadata, embedded, created_at)
            VALUES
            (:id, :knowledge_type, :content, :metadata, :embedded, :created_at)
        """)
        
        with self.engine.connect() as conn:
            conn.execute(query, {
                "id": knowledge_id,
                "knowledge_type": knowledge_type,
                "content": content,
                "metadata": json.dumps(metadata),  # Proper JSON
                "embedded": False,
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
    
    async def track_knowledge_success(self, knowledge_id: str) -> None:
        """
        Track successful use of knowledge.
        
        Increments success_count and updates last_used_at when
        knowledge pattern is retrieved and leads to task success.
        
        Args:
            knowledge_id: ID of knowledge that was useful
        """
        query = text("""
            UPDATE knowledge_staging
            SET metadata = jsonb_set(
                jsonb_set(
                    metadata,
                    '{success_count}',
                    to_jsonb(COALESCE((metadata->>'success_count')::int, 0) + 1)
                ),
                '{last_used_at}',
                to_jsonb(:last_used::text)
            )
            WHERE id = :id
        """)
        
        with self.engine.connect() as conn:
            conn.execute(query, {
                "id": knowledge_id,
                "last_used": datetime.now(UTC).isoformat()
            })
            conn.commit()
        
        logger.info("Knowledge success tracked | knowledge_id=%s", knowledge_id)
    
    async def get_pending_knowledge_count(self) -> int:
        """Get count of pending knowledge entries."""
        query = text("""
            SELECT COUNT(*)
            FROM knowledge_staging
            WHERE embedded = false
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query)
            return result.scalar() or 0
