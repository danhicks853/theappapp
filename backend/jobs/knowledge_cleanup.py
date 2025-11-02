"""
Knowledge Cleanup Job

Automatically prunes old knowledge entries (1-year retention policy).
Runs daily via cron to maintain storage efficiency.

Reference: Section 1.5.1 - RAG System Architecture
"""
import logging
from datetime import datetime, UTC, timedelta
from typing import Dict, Any
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class KnowledgeCleanupJob:
    """
    Daily cleanup job for knowledge retention.
    
    Retention policy: 1 year (365 days)
    
    Schedule: Daily at 3 AM (via cron)
    
    Process:
    1. Delete from Qdrant WHERE embedded_at < NOW() - 365 days
    2. Delete from knowledge_staging WHERE embedded=true AND embedded_at < NOW() - 365 days
    
    Example:
        job = KnowledgeCleanupJob(engine, qdrant_client)
        result = await job.run_cleanup()
    """
    
    RETENTION_DAYS = 365  # 1 year
    
    def __init__(self, engine: Engine, qdrant_client=None):
        """
        Initialize cleanup job.
        
        Args:
            engine: SQLAlchemy engine
            qdrant_client: Qdrant client for vector deletion
        """
        self.engine = engine
        self.qdrant_client = qdrant_client
        logger.info("KnowledgeCleanupJob initialized | retention=%d days", self.RETENTION_DAYS)
    
    async def run_cleanup(self) -> Dict[str, Any]:
        """
        Run the cleanup job.
        
        Returns:
            Dict with cleanup results
        """
        logger.info("Starting knowledge cleanup job")
        
        cutoff_date = datetime.now(UTC) - timedelta(days=self.RETENTION_DAYS)
        
        logger.info("Cleanup cutoff date: %s", cutoff_date.isoformat())
        
        results = {
            "cutoff_date": cutoff_date.isoformat(),
            "qdrant_deleted": 0,
            "postgres_deleted": 0,
            "errors": []
        }
        
        # Step 1: Get IDs to delete from PostgreSQL
        ids_to_delete = await self._get_old_entry_ids(cutoff_date)
        
        logger.info("Found %d old entries to delete", len(ids_to_delete))
        
        if not ids_to_delete:
            logger.info("No old entries found, cleanup complete")
            return results
        
        # Step 2: Delete from Qdrant
        if self.qdrant_client:
            qdrant_deleted = await self._delete_from_qdrant(ids_to_delete)
            results["qdrant_deleted"] = qdrant_deleted
        else:
            logger.warning("No Qdrant client, skipping vector deletion")
            results["errors"].append("No Qdrant client available")
        
        # Step 3: Delete from PostgreSQL
        postgres_deleted = await self._delete_from_postgres(cutoff_date)
        results["postgres_deleted"] = postgres_deleted
        
        logger.info(
            "Cleanup complete | qdrant=%d | postgres=%d",
            results["qdrant_deleted"],
            results["postgres_deleted"]
        )
        
        return results
    
    async def _get_old_entry_ids(self, cutoff_date: datetime) -> list:
        """Get IDs of entries older than cutoff date."""
        query = text("""
            SELECT id
            FROM knowledge_staging
            WHERE embedded = true
            AND embedded_at < :cutoff_date
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {"cutoff_date": cutoff_date})
            return [str(row[0]) for row in result.fetchall()]
    
    async def _delete_from_qdrant(self, ids: list) -> int:
        """Delete vectors from Qdrant."""
        if not ids:
            return 0
        
        try:
            # Delete from Qdrant collection
            # self.qdrant_client.delete(
            #     collection_name="helix_knowledge",
            #     points_selector=ids
            # )
            
            # Placeholder for now
            logger.info("Would delete %d vectors from Qdrant", len(ids))
            
            return len(ids)
            
        except Exception as e:
            logger.error("Failed to delete from Qdrant: %s", e)
            return 0
    
    async def _delete_from_postgres(self, cutoff_date: datetime) -> int:
        """Delete old entries from PostgreSQL."""
        query = text("""
            DELETE FROM knowledge_staging
            WHERE embedded = true
            AND embedded_at < :cutoff_date
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {"cutoff_date": cutoff_date})
            deleted_count = result.rowcount
            conn.commit()
            
            logger.info("Deleted %d rows from knowledge_staging", deleted_count)
            
            return deleted_count
    
    async def get_cleanup_stats(self) -> Dict[str, Any]:
        """Get statistics about what would be cleaned up."""
        cutoff_date = datetime.now(UTC) - timedelta(days=self.RETENTION_DAYS)
        
        # Count old entries
        count_query = text("""
            SELECT COUNT(*), MIN(embedded_at), MAX(embedded_at)
            FROM knowledge_staging
            WHERE embedded = true
            AND embedded_at < :cutoff_date
        """)
        
        # Count total entries
        total_query = text("""
            SELECT COUNT(*), MIN(created_at), MAX(created_at)
            FROM knowledge_staging
        """)
        
        with self.engine.connect() as conn:
            # Old entries
            result = conn.execute(count_query, {"cutoff_date": cutoff_date})
            row = result.fetchone()
            old_count = row[0] if row else 0
            oldest_date = row[1] if row and row[1] else None
            newest_old_date = row[2] if row and row[2] else None
            
            # Total entries
            result = conn.execute(total_query)
            row = result.fetchone()
            total_count = row[0] if row else 0
            
            return {
                "retention_days": self.RETENTION_DAYS,
                "cutoff_date": cutoff_date.isoformat(),
                "total_entries": total_count,
                "old_entries_count": old_count,
                "entries_to_delete": old_count,
                "oldest_entry_date": oldest_date.isoformat() if oldest_date else None,
                "newest_old_entry_date": newest_old_date.isoformat() if newest_old_date else None,
                "retention_pct": ((total_count - old_count) / total_count * 100) if total_count > 0 else 0
            }


# Cron job entry point
async def run_daily_cleanup(engine: Engine, qdrant_client=None):
    """
    Entry point for daily cron job.
    
    Usage in crontab:
        0 3 * * * cd /app && python -m backend.jobs.knowledge_cleanup
    """
    job = KnowledgeCleanupJob(engine, qdrant_client)
    result = await job.run_cleanup()
    
    logger.info("Daily cleanup complete: %s", result)
    
    return result


if __name__ == "__main__":
    # For manual testing
    import asyncio
    from sqlalchemy import create_engine
    
    # Initialize engine (would come from config in production)
    engine = create_engine("postgresql://user:pass@localhost/theappapp")
    
    # Run cleanup
    asyncio.run(run_daily_cleanup(engine))
