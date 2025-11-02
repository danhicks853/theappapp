"""
Web Search Service (SearxNG Integration)

Provides scoped web search capabilities for specialists.
Integrates with SearxNG for privacy-respecting search.

Reference: MVP Demo Plan - Specialist web search
"""
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Web search result."""
    title: str
    url: str
    snippet: str
    engine: str


class SearchService:
    """
    Service for web search via SearxNG.
    
    Features:
    - Privacy-respecting search
    - Configurable search engines
    - Result filtering by specialist scope
    
    Example:
        search = SearchService(searxng_url="http://localhost:8080")
        results = await search.search(
            "PostgreSQL query optimization",
            scope="site:postgresql.org"
        )
    """
    
    def __init__(
        self,
        searxng_url: str = "http://localhost:8080",
        default_engines: Optional[List[str]] = None
    ):
        """
        Initialize search service.
        
        Args:
            searxng_url: SearxNG instance URL
            default_engines: Default search engines to use
        """
        self.searxng_url = searxng_url.rstrip('/')
        self.default_engines = default_engines or ["google", "duckduckgo"]
        self.client = httpx.AsyncClient(timeout=30.0)
        
        logger.info(f"Search service initialized: {searxng_url}")
    
    async def search(
        self,
        query: str,
        scope: Optional[str] = None,
        engines: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[SearchResult]:
        """
        Search the web with optional scope restriction.
        
        Args:
            query: Search query
            scope: Optional scope restriction (e.g., "site:postgresql.org")
            engines: Search engines to use (default: google, duckduckgo)
            limit: Maximum number of results
        
        Returns:
            List of search results
        """
        # Build full query with scope
        full_query = f"{query} {scope}" if scope else query
        
        logger.debug(f"Searching: {full_query}")
        
        try:
            # Call SearxNG API
            response = await self.client.get(
                f"{self.searxng_url}/search",
                params={
                    "q": full_query,
                    "format": "json",
                    "engines": ",".join(engines or self.default_engines),
                    "pageno": 1
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # Parse results
            results = []
            for item in data.get("results", [])[:limit]:
                result = SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    engine=item.get("engine", "unknown")
                )
                results.append(result)
            
            logger.info(f"Found {len(results)} search results")
            return results
            
        except httpx.HTTPError as e:
            logger.error(f"Search failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}")
            return []
    
    async def search_with_config(
        self,
        query: str,
        search_config: Dict[str, Any]
    ) -> List[SearchResult]:
        """
        Search using specialist-specific configuration.
        
        Args:
            query: Search query
            search_config: Specialist search configuration
                - scope: Domain/site restriction
                - engines: Preferred search engines
                - max_results: Result limit
        
        Returns:
            List of search results
        """
        scope = search_config.get("scope")
        engines = search_config.get("engines")
        limit = search_config.get("max_results", 10)
        
        return await self.search(
            query=query,
            scope=scope,
            engines=engines,
            limit=limit
        )
    
    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()
