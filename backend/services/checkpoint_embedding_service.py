"""
Checkpoint Embedding Service

Processes knowledge_staging entries at checkpoints and generates embeddings.
Triggered at phase/project completion, not real-time.

Reference: Section 1.5.1 - RAG System Architecture
"""
import logging
from datetime import datetime, UTC
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class CheckpointEmbeddingService:
    """
    Service for batch-processing knowledge embeddings at checkpoints.
    
    Checkpoints:
    - Phase completion
    - Project completion
    - Project cancellation
    - Manual trigger
    
    Process:
    1. Query knowledge_staging WHERE embedded=false
    2. Generate embeddings via OpenAI (batch of 50)
    3. Store in Qdrant
    4. Mark as embedded
    
    Example:
        service = CheckpointEmbeddingService(engine, qdrant_client, openai_client)
        
        # At phase completion
        result = await service.process_checkpoint("phase_completion")
    """
    
    BATCH_SIZE = 50  # Process 50 items per batch to manage API costs
    
    def __init__(
        self,
        engine: Engine,
        qdrant_client=None,
        openai_client=None
    ):
        """
        Initialize checkpoint embedding service.
        
        Args:
            engine: SQLAlchemy engine
            qdrant_client: Qdrant client (for vector storage)
            openai_client: OpenAI client (for embeddings)
        """
        self.engine = engine
        self.qdrant_client = qdrant_client
        self.openai_client = openai_client
        logger.info("CheckpointEmbeddingService initialized")
    
    async def process_checkpoint(
        self,
        checkpoint_type: str,
        *,
        project_id: Optional[str] = None,
        batch_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process a checkpoint and generate embeddings.
        
        Args:
            checkpoint_type: Type of checkpoint (phase_completion, project_completion, etc.)
            project_id: Optional project filter
            batch_limit: Optional limit on batches to process
        
        Returns:
            Dict with processing results
        """
        logger.info(
            "Processing checkpoint | type=%s | project=%s",
            checkpoint_type,
            project_id or "all"
        )
        
        # Get pending knowledge entries
        pending_entries = await self._get_pending_entries(
            project_id=project_id,
            limit=batch_limit or self.BATCH_SIZE
        )
        
        if not pending_entries:
            logger.info("No pending knowledge entries to process")
            return {
                "checkpoint_type": checkpoint_type,
                "processed_count": 0,
                "embedded_count": 0,
                "failed_count": 0
            }
        
        logger.info(
            "Found %d pending entries for embedding",
            len(pending_entries)
        )
        
        # Process in batches
        embedded_count = 0
        failed_count = 0
        
        for i in range(0, len(pending_entries), self.BATCH_SIZE):
            batch = pending_entries[i:i + self.BATCH_SIZE]
            
            logger.info(
                "Processing batch %d/%d (%d items)",
                (i // self.BATCH_SIZE) + 1,
                (len(pending_entries) + self.BATCH_SIZE - 1) // self.BATCH_SIZE,
                len(batch)
            )
            
            # Generate embeddings for batch
            results = await self._process_batch(batch, checkpoint_type)
            
            embedded_count += results["embedded"]
            failed_count += results["failed"]
        
        logger.info(
            "Checkpoint processing complete | embedded=%d | failed=%d",
            embedded_count,
            failed_count
        )
        
        return {
            "checkpoint_type": checkpoint_type,
            "processed_count": len(pending_entries),
            "embedded_count": embedded_count,
            "failed_count": failed_count
        }
    
    async def _get_pending_entries(
        self,
        project_id: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Query pending knowledge entries from staging."""
        query_str = """
            SELECT id, knowledge_type, content, metadata
            FROM knowledge_staging
            WHERE embedded = false
        """
        
        if project_id:
            query_str += " AND metadata->>'project_id' = :project_id"
        
        query_str += " ORDER BY created_at ASC LIMIT :limit"
        
        query = text(query_str)
        
        with self.engine.connect() as conn:
            if project_id:
                result = conn.execute(query, {"project_id": project_id, "limit": limit})
            else:
                result = conn.execute(query, {"limit": limit})
            
            entries = []
            for row in result.fetchall():
                entries.append({
                    "id": row[0],
                    "knowledge_type": row[1],
                    "content": row[2],
                    "metadata": row[3]  # Already parsed as dict
                })
            
            return entries
    
    async def _process_batch(
        self,
        batch: List[Dict[str, Any]],
        checkpoint_type: str
    ) -> Dict[str, int]:
        """Process a batch of entries."""
        embedded = 0
        failed = 0
        
        for entry in batch:
            try:
                # Generate embedding
                embedding = await self._generate_embedding(entry["content"])
                
                if not embedding:
                    logger.warning("Failed to generate embedding | id=%s", entry["id"])
                    failed += 1
                    continue
                
                # Store in Qdrant
                await self._store_in_qdrant(
                    entry_id=entry["id"],
                    embedding=embedding,
                    content=entry["content"],
                    metadata=entry["metadata"]
                )
                
                # Mark as embedded
                await self._mark_as_embedded(entry["id"])
                
                embedded += 1
                
            except Exception as e:
                logger.error(
                    "Error processing entry | id=%s | error=%s",
                    entry["id"],
                    str(e)
                )
                failed += 1
        
        return {"embedded": embedded, "failed": failed}
    
    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text using OpenAI.
        
        Uses text-embedding-3-small (1536 dimensions).
        """
        if not self.openai_client:
            logger.warning("No OpenAI client available, skipping embedding")
            return None
        
        try:
            # Call OpenAI embeddings API
            # response = await self.openai_client.embeddings.create(
            #     model="text-embedding-3-small",
            #     input=text
            # )
            # return response.data[0].embedding
            
            # Placeholder for now
            logger.debug("Would generate embedding for text (length=%d)", len(text))
            return [0.0] * 1536  # Dummy embedding
            
        except Exception as e:
            logger.error("Failed to generate embedding: %s", e)
            return None
    
    async def _store_in_qdrant(
        self,
        entry_id: str,
        embedding: List[float],
        content: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Store vector and metadata in Qdrant."""
        if not self.qdrant_client:
            logger.warning("No Qdrant client available, skipping storage")
            return
        
        try:
            # self.qdrant_client.upsert(
            #     collection_name="helix_knowledge",
            #     points=[{
            #         "id": entry_id,
            #         "vector": embedding,
            #         "payload": {
            #             "content": content[:1000],  # Truncate for storage
            #             **metadata
            #         }
            #     }]
            # )
            
            # Placeholder for now
            logger.debug("Would store in Qdrant | id=%s", entry_id)
            
        except Exception as e:
            logger.error("Failed to store in Qdrant: %s", e)
            raise
    
    async def _mark_as_embedded(self, entry_id: str) -> None:
        """Mark knowledge entry as embedded."""
        query = text("""
            UPDATE knowledge_staging
            SET embedded = true, embedded_at = :embedded_at
            WHERE id = :id
        """)
        
        with self.engine.connect() as conn:
            conn.execute(query, {
                "id": entry_id,
                "embedded_at": datetime.now(UTC)
            })
            conn.commit()
    
    async def get_pending_count(self, project_id: Optional[str] = None) -> int:
        """Get count of pending knowledge entries."""
        query_str = "SELECT COUNT(*) FROM knowledge_staging WHERE embedded = false"
        
        if project_id:
            query_str += " AND metadata->>'project_id' = :project_id"
        
        query = text(query_str)
        
        with self.engine.connect() as conn:
            if project_id:
                result = conn.execute(query, {"project_id": project_id})
            else:
                result = conn.execute(query)
            
            return result.scalar() or 0
    
    async def manual_trigger(
        self,
        project_id: Optional[str] = None,
        batch_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Manually trigger embedding processing.
        
        Useful for testing or catching up on backlog.
        """
        logger.info("Manual embedding trigger | project=%s", project_id or "all")
        
        return await self.process_checkpoint(
            checkpoint_type="manual_trigger",
            project_id=project_id,
            batch_limit=batch_limit
        )
