"""
Hourly Container Cleanup Job

Cleans up orphaned containers that are not tracked in active_containers.
Runs hourly via cron/scheduler to prevent container leaks.
"""
import asyncio
import logging
from datetime import datetime
from backend.services.container_manager import get_container_manager

logger = logging.getLogger(__name__)


async def cleanup_orphaned_containers():
    """
    Cleanup orphaned containers.
    
    Called hourly by job scheduler.
    Removes containers with theappapp-managed label that aren't actively tracked.
    """
    logger.info("Starting hourly container cleanup job")
    start_time = datetime.utcnow()
    
    try:
        container_manager = get_container_manager()
        
        result = await container_manager.cleanup_orphaned_containers()
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info(
            f"Container cleanup completed: "
            f"{result['cleaned']} containers cleaned, "
            f"{len(result['errors'])} errors, "
            f"duration: {duration:.2f}s"
        )
        
        if result['errors']:
            for error in result['errors']:
                logger.error(f"Cleanup error: {error}")
        
        return result
    
    except Exception as e:
        logger.error(f"Container cleanup job failed: {e}", exc_info=True)
        return {
            "cleaned": 0,
            "errors": [str(e)]
        }


if __name__ == "__main__":
    # For manual testing
    asyncio.run(cleanup_orphaned_containers())
