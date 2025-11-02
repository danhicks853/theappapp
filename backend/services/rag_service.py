"""
RAG (Retrieval-Augmented Generation) Service

Manages document indexing and semantic search using Qdrant vector database.
Integrates with OpenAI for embeddings.

Reference: MVP Demo Plan - Specialist knowledge base
"""
import logging
import uuid
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from backend.services.openai_adapter import OpenAIAdapter

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """Represents a chunk of a document."""
    id: str
    text: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


@dataclass
class SearchResult:
    """Search result with relevance score."""
    text: str
    score: float
    metadata: Dict[str, Any]


class RAGService:
    """
    Service for document indexing and semantic search.
    
    Features:
    - Document chunking
    - Embedding generation via OpenAI
    - Vector storage in Qdrant
    - Semantic search
    
    Example:
        rag = RAGService(openai_adapter, qdrant_url="http://localhost:6333")
        await rag.index_document(
            "PostgreSQL docs",
            specialist_id="specialist-123",
            metadata={"source": "postgres.pdf"}
        )
        results = await rag.search("How to optimize queries?", specialist_id="specialist-123")
    """
    
    CHUNK_SIZE = 500  # Characters per chunk
    CHUNK_OVERLAP = 50  # Overlap between chunks
    EMBEDDING_DIM = 1536  # OpenAI text-embedding-3-small dimension
    
    def __init__(
        self,
        openai_adapter: OpenAIAdapter,
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "specialist_documents"
    ):
        """
        Initialize RAG service.
        
        Args:
            openai_adapter: OpenAI adapter for embeddings
            qdrant_url: Qdrant server URL
            collection_name: Name of Qdrant collection
        """
        self.openai = openai_adapter
        self.qdrant = QdrantClient(url=qdrant_url)
        self.collection_name = collection_name
        
        # Create collection if it doesn't exist
        self._ensure_collection()
        
        logger.info(f"RAG service initialized with collection: {collection_name}")
    
    def _ensure_collection(self) -> None:
        """Create Qdrant collection if it doesn't exist."""
        try:
            self.qdrant.get_collection(self.collection_name)
            logger.debug(f"Collection {self.collection_name} already exists")
        except Exception:
            logger.info(f"Creating collection: {self.collection_name}")
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.EMBEDDING_DIM,
                    distance=Distance.COSINE
                )
            )
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Text to chunk
        
        Returns:
            List of text chunks
        """
        if len(text) <= self.CHUNK_SIZE:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.CHUNK_SIZE
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - self.CHUNK_OVERLAP
        
        logger.debug(f"Chunked text into {len(chunks)} chunks")
        return chunks
    
    async def index_document(
        self,
        text: str,
        specialist_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Index a document for a specialist.
        
        Args:
            text: Document text
            specialist_id: ID of specialist this document belongs to
            metadata: Optional metadata (filename, source, etc.)
        
        Returns:
            Number of chunks indexed
        """
        logger.info(f"Indexing document for specialist {specialist_id}")
        
        # Chunk the text
        chunks = self.chunk_text(text)
        
        # Generate embeddings and create points
        points = []
        for i, chunk_text in enumerate(chunks):
            # Generate embedding
            embedding = await self.openai.embed_text(chunk_text)
            
            # Create point
            point_id = str(uuid.uuid4())
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "text": chunk_text,
                    "specialist_id": specialist_id,
                    "chunk_index": i,
                    **(metadata or {})
                }
            )
            points.append(point)
        
        # Upsert to Qdrant
        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        logger.info(f"Indexed {len(chunks)} chunks for specialist {specialist_id}")
        return len(chunks)
    
    async def search(
        self,
        query: str,
        specialist_id: str,
        limit: int = 5,
        score_threshold: float = 0.7
    ) -> List[SearchResult]:
        """
        Search for relevant document chunks.
        
        Args:
            query: Search query
            specialist_id: Filter by specialist ID
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0-1)
        
        Returns:
            List of search results with relevance scores
        """
        logger.debug(f"Searching for: {query} (specialist: {specialist_id})")
        
        # Generate query embedding
        query_embedding = await self.openai.embed_text(query)
        
        # Search Qdrant
        search_results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter={
                "must": [
                    {"key": "specialist_id", "match": {"value": specialist_id}}
                ]
            },
            limit=limit,
            score_threshold=score_threshold
        )
        
        # Convert to SearchResult objects
        results = [
            SearchResult(
                text=hit.payload["text"],
                score=hit.score,
                metadata={k: v for k, v in hit.payload.items() if k != "text"}
            )
            for hit in search_results
        ]
        
        logger.info(f"Found {len(results)} results for query")
        return results
    
    async def delete_specialist_documents(self, specialist_id: str) -> None:
        """
        Delete all documents for a specialist.
        
        Args:
            specialist_id: Specialist ID
        """
        logger.info(f"Deleting all documents for specialist {specialist_id}")
        
        self.qdrant.delete(
            collection_name=self.collection_name,
            points_selector={
                "filter": {
                    "must": [
                        {"key": "specialist_id", "match": {"value": specialist_id}}
                    ]
                }
            }
        )
