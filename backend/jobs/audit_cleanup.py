"""
Audit Log Cleanup Job

Deletes tool audit logs older than 1 year to maintain database performance.
Should be scheduled to run daily at 2 AM via cron or similar scheduler.
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy import delete, func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AuditCleanupJob:
    """
    Daily job to cleanup old audit logs.
    
    Retention Policy:
    - Keep audit logs for 1 year (365 days)
    - Delete records older than 365 days
    - Run daily at 2 AM
    """
    
    RETENTION_DAYS = 365
    
    def __init__(self, db_session: Session):
        """
        Initialize cleanup job.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db_session = db_session
    
    def run(self) -> dict:
        """
        Run the cleanup job.
        
        Returns:
            dict with job results (deleted_count, execution_time, etc.)
        """
        start_time = datetime.utcnow()
        logger.info("Starting audit log cleanup job")
        
        try:
            # Calculate cutoff date
            cutoff_date = datetime.utcnow() - timedelta(days=self.RETENTION_DAYS)
            
            logger.info(f"Deleting audit logs older than {cutoff_date.isoformat()}")
            
            # Delete old records
            deleted_count = self._delete_old_logs(cutoff_date)
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(
                f"Audit log cleanup completed: "
                f"deleted={deleted_count}, "
                f"execution_time={execution_time:.2f}s"
            )
            
            return {
                "success": True,
                "deleted_count": deleted_count,
                "cutoff_date": cutoff_date.isoformat(),
                "execution_time": execution_time,
                "completed_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Audit log cleanup failed: {e}", exc_info=True)
            
            return {
                "success": False,
                "error": str(e),
                "completed_at": datetime.utcnow().isoformat()
            }
    
    def _delete_old_logs(self, cutoff_date: datetime) -> int:
        """
        Delete audit logs older than cutoff date.
        
        Args:
            cutoff_date: Delete logs older than this date
        
        Returns:
            Number of records deleted
        """
        from backend.models.database import ToolAuditLog
        
        # Build delete statement
        stmt = delete(ToolAuditLog).where(
            ToolAuditLog.timestamp < cutoff_date
        )
        
        # Execute deletion
        result = self.db_session.execute(stmt)
        self.db_session.commit()
        
        # Return number of deleted rows
        return result.rowcount
    
    def dry_run(self) -> dict:
        """
        Perform a dry run to see how many logs would be deleted.
        
        Returns:
            dict with count of logs that would be deleted
        """
        from backend.models.database import ToolAuditLog
        
        cutoff_date = datetime.utcnow() - timedelta(days=self.RETENTION_DAYS)
        
        # Count logs that would be deleted
        count = self.db_session.query(func.count(ToolAuditLog.id)).filter(
            ToolAuditLog.timestamp < cutoff_date
        ).scalar()
        
        return {
            "would_delete": count,
            "cutoff_date": cutoff_date.isoformat(),
            "retention_days": self.RETENTION_DAYS
        }


def run_audit_cleanup(db_session: Session) -> dict:
    """
    Convenience function to run audit cleanup.
    
    Args:
        db_session: SQLAlchemy database session
    
    Returns:
        Job execution results
    """
    job = AuditCleanupJob(db_session)
    return job.run()


def dry_run_audit_cleanup(db_session: Session) -> dict:
    """
    Convenience function to perform dry run.
    
    Args:
        db_session: SQLAlchemy database session
    
    Returns:
        Dry run results
    """
    job = AuditCleanupJob(db_session)
    return job.dry_run()


# Example cron configuration:
# 
# To run daily at 2 AM, add to crontab:
# 0 2 * * * /path/to/venv/bin/python -c "from backend.jobs.audit_cleanup import run_audit_cleanup; from backend.database import get_db_session; run_audit_cleanup(get_db_session())"
#
# Or use a scheduler like APScheduler in your FastAPI app:
#
# from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from backend.jobs.audit_cleanup import run_audit_cleanup
# from backend.database import get_db_session
#
# scheduler = AsyncIOScheduler()
# scheduler.add_job(
#     lambda: run_audit_cleanup(get_db_session()),
#     'cron',
#     hour=2,
#     minute=0
# )
# scheduler.start()
