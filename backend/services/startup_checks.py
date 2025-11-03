"""
Startup Safety Checks

Validates that all required services are available before starting the application.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class StartupChecker:
    """Validates system dependencies at startup."""
    
    def __init__(self):
        self.checks_passed = False
        self.results: Dict[str, Any] = {}
    
    async def run_all_checks(self) -> bool:
        """
        Run all startup checks.
        
        Returns:
            bool: True if all checks pass, False otherwise
        """
        logger.info("=" * 80)
        logger.info("RUNNING STARTUP SAFETY CHECKS")
        logger.info("=" * 80)
        
        checks = [
            ("Docker", self._check_docker),
            ("Database", self._check_database),
            ("SearXNG", self._check_searxng),
            ("Qdrant", self._check_qdrant),
        ]
        
        all_passed = True
        
        for name, check_func in checks:
            try:
                result = await check_func()
                self.results[name] = result
                
                if result["available"]:
                    logger.info(f"✅ {name}: {result['message']}")
                else:
                    logger.warning(f"⚠️  {name}: {result['message']}")
                    if result.get("required", True):
                        all_passed = False
            except Exception as e:
                logger.error(f"❌ {name}: Check failed with error: {e}")
                self.results[name] = {
                    "available": False,
                    "message": str(e),
                    "required": True
                }
                all_passed = False
        
        logger.info("=" * 80)
        if all_passed:
            logger.info("✅ ALL STARTUP CHECKS PASSED - System ready")
        else:
            logger.error("❌ STARTUP CHECKS FAILED - Cannot start build")
            logger.error("   All services must be running: Docker, Database, SearXNG, Qdrant")
        logger.info("=" * 80)
        
        self.checks_passed = all_passed
        return all_passed
    
    async def _check_docker(self) -> Dict[str, Any]:
        """Check if Docker is available."""
        try:
            import docker
            client = docker.from_env()
            client.ping()
            
            return {
                "available": True,
                "message": "Docker daemon is running and accessible",
                "required": True
            }
        except Exception as e:
            return {
                "available": False,
                "message": f"Docker not available: {str(e)}",
                "required": True
            }
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check if PostgreSQL database is available."""
        try:
            from sqlalchemy import create_engine, text
            import os
            
            db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:55432/theappapp")
            # Override database name with _test suffix if not explicitly set
            if "DATABASE_URL" not in os.environ:
                # Use theappapp database (no _test suffix needed)
                db_url = "postgresql://postgres:postgres@localhost:55432/theappapp"
            engine = create_engine(db_url)
            
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            return {
                "available": True,
                "message": "PostgreSQL database is accessible",
                "required": True
            }
        except Exception as e:
            return {
                "available": False,
                "message": f"Database not available: {str(e)}",
                "required": True
            }
    
    async def _check_searxng(self) -> Dict[str, Any]:
        """Check if SearXNG web search is available."""
        import os
        searxng_url = os.getenv("SEARXNG_URL", "http://localhost:8080")
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                # Try root endpoint (SearXNG doesn't have /healthz by default)
                async with session.get(searxng_url, timeout=aiohttp.ClientTimeout(total=3)) as response:
                    if response.status == 200:
                        return {
                            "available": True,
                            "message": f"SearXNG is running at {searxng_url}",
                            "required": True
                        }
                    return {
                        "available": False,
                        "message": f"SearXNG returned status {response.status}",
                        "required": True
                    }
        except ImportError:
            return {
                "available": False,
                "message": "aiohttp not installed",
                "required": True
            }
        except Exception as e:
            # Handle all connection errors
            error_msg = str(e) if str(e) else type(e).__name__
            return {
                "available": False,
                "message": f"SearXNG not running at {searxng_url} ({error_msg})",
                "required": True
            }
    
    async def _check_qdrant(self) -> Dict[str, Any]:
        """Check if Qdrant vector database is available."""
        try:
            from qdrant_client import QdrantClient
            import os
            
            # Parse QDRANT_URL which might be "http://localhost:6333" or just "localhost"
            qdrant_url = os.getenv("QDRANT_URL", "127.0.0.1")
            
            # Strip protocol if present
            if "://" in qdrant_url:
                qdrant_url = qdrant_url.split("://")[1]  # Remove http:// or https://
            
            # Separate host and port from URL if both present
            if ":" in qdrant_url:
                host, port_str = qdrant_url.split(":", 1)
                qdrant_host = host
                qdrant_port = int(port_str)
            else:
                # No port in URL, use QDRANT_PORT env var or default
                qdrant_host = qdrant_url
                qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
            
            client = QdrantClient(host=qdrant_host, port=qdrant_port, timeout=10)
            # Try to get collections to verify connection
            client.get_collections()
            
            return {
                "available": True,
                "message": f"Qdrant is running at {qdrant_host}:{qdrant_port}",
                "required": True
            }
        except Exception as e:
            return {
                "available": False,
                "message": f"Qdrant not available: {str(e)}",
                "required": True
            }


async def run_startup_checks() -> bool:
    """
    Convenience function to run all startup checks.
    
    Returns:
        bool: True if all required checks pass
    """
    checker = StartupChecker()
    return await checker.run_all_checks()
