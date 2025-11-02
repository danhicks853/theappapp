"""
Web Search Service

Provides web search capabilities for AI agents via SearXNG.
Includes result processing, filtering, and access controls.
"""
import logging
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SearchResultQuality(Enum):
    """Quality rating for search results."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class SearchResult:
    """Single search result."""
    title: str
    url: str
    snippet: str
    engine: str  # Which search engine provided this result
    score: float = 0.0  # Relevance score (0-1)
    quality: SearchResultQuality = SearchResultQuality.MEDIUM
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "engine": self.engine,
            "score": self.score,
            "quality": self.quality.value
        }


class WebSearchService:
    """
    Web search service for AI agents.
    
    Features:
    - Integrates with SearXNG metasearch engine
    - Rate limiting per agent (10 searches/minute)
    - Result filtering and deduplication
    - Access control (only specific agents can search)
    - Comprehensive logging
    """
    
    # SearXNG configuration
    SEARXNG_URL = "http://searxng:8080"  # Docker internal network
    SEARXNG_URL_LOCAL = "http://localhost:8080"  # For local testing
    
    # Rate limiting
    MAX_SEARCHES_PER_MINUTE = 10
    
    # Allowed agent types
    ALLOWED_AGENTS = {
        "backend_dev",
        "frontend_dev", 
        "workshopper",
        "security_expert",
        "devops_engineer"
    }
    
    # URL patterns to prioritize for technical content
    TECHNICAL_DOMAINS = {
        "stackoverflow.com",
        "github.com",
        "docs.python.org",
        "developer.mozilla.org",
        "pypi.org",
        "npmjs.com",
        "medium.com",
        "dev.to",
        "hackernoon.com"
    }
    
    def __init__(self, searxng_url: Optional[str] = None):
        """
        Initialize web search service.
        
        Args:
            searxng_url: Optional custom SearXNG URL (defaults to Docker internal)
        """
        self.searxng_url = searxng_url or self.SEARXNG_URL
        self.search_history: Dict[str, List[datetime]] = {}  # agent_id -> timestamps
        logger.info(f"WebSearchService initialized with URL: {self.searxng_url}")
    
    async def search(
        self,
        query: str,
        agent_id: str,
        agent_type: str,
        num_results: int = 10,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform web search for an agent.
        
        Args:
            query: Search query
            agent_id: Unique agent identifier
            agent_type: Type of agent (backend_dev, frontend_dev, etc.)
            num_results: Number of results to return (max 20)
            category: Optional category filter (it, science, etc.)
        
        Returns:
            dict: {
                "success": bool,
                "query": str,
                "results": List[SearchResult],
                "result_count": int,
                "message": str (if error)
            }
        """
        # Validate access
        if not self._check_access(agent_type):
            logger.warning(f"Search denied for agent {agent_id} (type: {agent_type})")
            return {
                "success": False,
                "query": query,
                "results": [],
                "result_count": 0,
                "message": f"Agent type '{agent_type}' not authorized for web search"
            }
        
        # Check rate limiting
        if not self._check_rate_limit(agent_id):
            logger.warning(f"Rate limit exceeded for agent {agent_id}")
            return {
                "success": False,
                "query": query,
                "results": [],
                "result_count": 0,
                "message": "Rate limit exceeded (max 10 searches per minute)"
            }
        
        # Validate and sanitize query
        query = self._sanitize_query(query)
        if not query:
            return {
                "success": False,
                "query": "",
                "results": [],
                "result_count": 0,
                "message": "Invalid or empty query"
            }
        
        # Limit num_results
        num_results = min(num_results, 20)
        
        logger.info(f"Search request: agent={agent_id}, query='{query}', num_results={num_results}")
        
        try:
            # Call SearXNG API
            results = await self._call_searxng(query, num_results, category)
            
            # Process and filter results
            processed_results = self._process_results(results)
            
            # Log search
            self._log_search(agent_id, agent_type, query, len(processed_results))
            
            logger.info(f"Search completed: {len(processed_results)} results returned")
            
            return {
                "success": True,
                "query": query,
                "results": [r.to_dict() for r in processed_results],
                "result_count": len(processed_results),
                "message": "Search completed successfully"
            }
        
        except httpx.TimeoutException:
            logger.error(f"Search timeout for query: {query}")
            return {
                "success": False,
                "query": query,
                "results": [],
                "result_count": 0,
                "message": "Search request timed out"
            }
        except Exception as e:
            logger.error(f"Search error: {e}", exc_info=True)
            return {
                "success": False,
                "query": query,
                "results": [],
                "result_count": 0,
                "message": f"Search error: {str(e)}"
            }
    
    async def _call_searxng(
        self,
        query: str,
        num_results: int,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Call SearXNG API.
        
        Args:
            query: Search query
            num_results: Number of results
            category: Optional category
        
        Returns:
            List of raw search results from SearXNG
        """
        params = {
            "q": query,
            "format": "json",
            "pageno": 1
        }
        
        if category:
            params["category"] = category
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{self.searxng_url}/search", params=params)
                response.raise_for_status()
                data = response.json()
                
                # SearXNG returns results in 'results' key
                raw_results = data.get("results", [])
                return raw_results[:num_results]
            
            except httpx.HTTPStatusError as e:
                logger.error(f"SearXNG HTTP error: {e.response.status_code}")
                # Fallback to localhost if Docker network fails
                if self.searxng_url != self.SEARXNG_URL_LOCAL:
                    logger.info("Attempting localhost fallback")
                    response = await client.get(f"{self.SEARXNG_URL_LOCAL}/search", params=params)
                    response.raise_for_status()
                    data = response.json()
                    raw_results = data.get("results", [])
                    return raw_results[:num_results]
                raise
    
    def _process_results(self, raw_results: List[Dict[str, Any]]) -> List[SearchResult]:
        """
        Process and filter search results.
        
        Args:
            raw_results: Raw results from SearXNG
        
        Returns:
            Processed and filtered SearchResult objects
        """
        processed = []
        seen_urls = set()
        
        for result in raw_results:
            url = result.get("url", "")
            title = result.get("title", "")
            snippet = result.get("content", "")
            engine = result.get("engine", "unknown")
            
            # Skip if missing essential fields
            if not url or not title:
                continue
            
            # Deduplicate by URL
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            # Calculate quality score
            quality, score = self._calculate_quality(url, title, snippet)
            
            # Filter out very low quality results
            if quality == SearchResultQuality.LOW and score < 0.3:
                continue
            
            processed.append(SearchResult(
                title=title,
                url=url,
                snippet=snippet[:500],  # Limit snippet length
                engine=engine,
                score=score,
                quality=quality
            ))
        
        # Sort by score (highest first)
        processed.sort(key=lambda r: r.score, reverse=True)
        
        return processed
    
    def _calculate_quality(self, url: str, title: str, snippet: str) -> tuple[SearchResultQuality, float]:
        """
        Calculate quality rating and relevance score for a result.
        
        Args:
            url: Result URL
            title: Result title
            snippet: Result snippet
        
        Returns:
            (quality_rating, relevance_score)
        """
        score = 0.5  # Base score
        
        # Boost technical domains
        for domain in self.TECHNICAL_DOMAINS:
            if domain in url:
                score += 0.3
                break
        
        # Boost if title contains technical keywords
        technical_keywords = ["tutorial", "documentation", "guide", "example", "api", "reference"]
        title_lower = title.lower()
        for keyword in technical_keywords:
            if keyword in title_lower:
                score += 0.1
                break
        
        # Penalize short snippets (likely low content)
        if len(snippet) < 50:
            score -= 0.2
        
        # Penalize certain domains (ads, clickbait)
        spam_domains = ["pinterest.com", "quora.com"]
        for domain in spam_domains:
            if domain in url:
                score -= 0.3
                break
        
        # Clamp score to 0-1
        score = max(0.0, min(1.0, score))
        
        # Determine quality
        if score >= 0.7:
            quality = SearchResultQuality.HIGH
        elif score >= 0.4:
            quality = SearchResultQuality.MEDIUM
        else:
            quality = SearchResultQuality.LOW
        
        return quality, score
    
    def _check_access(self, agent_type: str) -> bool:
        """Check if agent type is allowed to search."""
        return agent_type in self.ALLOWED_AGENTS
    
    def _check_rate_limit(self, agent_id: str) -> bool:
        """
        Check if agent is within rate limits.
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            True if within limits, False if exceeded
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=1)
        
        # Get recent searches for this agent
        if agent_id not in self.search_history:
            self.search_history[agent_id] = []
        
        # Filter to last minute
        recent = [ts for ts in self.search_history[agent_id] if ts > cutoff]
        self.search_history[agent_id] = recent
        
        # Check limit
        if len(recent) >= self.MAX_SEARCHES_PER_MINUTE:
            return False
        
        # Record this search
        self.search_history[agent_id].append(now)
        return True
    
    def _sanitize_query(self, query: str) -> str:
        """Sanitize and validate search query."""
        if not query:
            return ""
        
        # Strip whitespace
        query = query.strip()
        
        # Limit length
        query = query[:500]
        
        # Remove potentially dangerous characters
        # (SearXNG handles most, but be safe)
        dangerous_chars = ["<", ">", "{", "}"]
        for char in dangerous_chars:
            query = query.replace(char, "")
        
        return query
    
    def _log_search(self, agent_id: str, agent_type: str, query: str, result_count: int):
        """Log search to database/logs."""
        # TODO: Log to database when audit table is ready
        logger.info(
            f"SEARCH_LOG: agent_id={agent_id}, agent_type={agent_type}, "
            f"query='{query}', results={result_count}"
        )
    
    async def summarize_results(
        self,
        results: List[SearchResult],
        max_results: int = 5
    ) -> str:
        """
        Create a concise summary of search results.
        
        Args:
            results: List of search results
            max_results: Maximum results to include (default 5)
        
        Returns:
            Markdown-formatted summary with key points and sources
        """
        if not results:
            return "No search results found."
        
        # Take top N results
        top_results = results[:max_results]
        
        # Build summary
        summary_lines = ["## Search Results Summary\n"]
        
        for i, result in enumerate(top_results, 1):
            summary_lines.append(f"### {i}. {result.title}")
            summary_lines.append(f"**Source**: {result.url}")
            summary_lines.append(f"**Snippet**: {result.snippet[:200]}...")
            summary_lines.append(f"**Quality**: {result.quality.value} (score: {result.score:.2f})")
            summary_lines.append("")  # Blank line
        
        return "\n".join(summary_lines)


# Singleton instance
_web_search_service: Optional[WebSearchService] = None


def get_web_search_service() -> WebSearchService:
    """Get singleton WebSearchService instance."""
    global _web_search_service
    
    if _web_search_service is None:
        _web_search_service = WebSearchService()
    
    return _web_search_service
