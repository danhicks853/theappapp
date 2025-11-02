"""
Qdrant Collection Setup

Sets up the helix_knowledge collection in Qdrant with proper configuration.

Reference: Section 1.5.1 - RAG System Architecture
"""
import logging
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    ScalarQuantizationConfig,
    ScalarType,
    PayloadSchemaType
)

logger = logging.getLogger(__name__)


class QdrantSetup:
    """
    Setup and configuration for Qdrant collections.
    
    Collection: helix_knowledge
    - Vector size: 1536 (text-embedding-3-small)
    - Distance: Cosine
    - Quantization: Scalar (for performance)
    - Indexes: agent_type, task_type, technology, success_verified
    
    Example:
        setup = QdrantSetup(qdrant_client)
        await setup.create_knowledge_collection()
    """
    
    COLLECTION_NAME = "helix_knowledge"
    VECTOR_SIZE = 1536  # text-embedding-3-small dimension
    
    def __init__(self, client: Optional[QdrantClient] = None):
        """
        Initialize Qdrant setup.
        
        Args:
            client: Qdrant client instance (if None, creates new)
        """
        self.client = client or QdrantClient(host="localhost", port=6333)
        logger.info("QdrantSetup initialized | collection=%s", self.COLLECTION_NAME)
    
    async def create_knowledge_collection(self, recreate: bool = False) -> bool:
        """
        Create the helix_knowledge collection.
        
        Args:
            recreate: If True, deletes existing collection first
        
        Returns:
            True if created/already exists, False on error
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            exists = any(c.name == self.COLLECTION_NAME for c in collections)
            
            if exists:
                if recreate:
                    logger.warning("Deleting existing collection | collection=%s", self.COLLECTION_NAME)
                    self.client.delete_collection(self.COLLECTION_NAME)
                else:
                    logger.info("Collection already exists | collection=%s", self.COLLECTION_NAME)
                    return True
            
            # Create collection
            logger.info(
                "Creating collection | collection=%s | vector_size=%d",
                self.COLLECTION_NAME,
                self.VECTOR_SIZE
            )
            
            self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=self.VECTOR_SIZE,
                    distance=Distance.COSINE  # Cosine similarity for embeddings
                ),
                # Scalar quantization for better performance
                quantization_config=ScalarQuantizationConfig(
                    type=ScalarType.INT8,
                    quantile=0.99,
                    always_ram=True
                )
            )
            
            logger.info("Collection created successfully | collection=%s", self.COLLECTION_NAME)
            
            # Create payload indexes
            await self._create_payload_indexes()
            
            return True
            
        except Exception as e:
            logger.error("Failed to create collection: %s", e)
            return False
    
    async def _create_payload_indexes(self) -> None:
        """Create indexes on payload fields for faster filtering."""
        indexes = [
            ("agent_type", PayloadSchemaType.KEYWORD),
            ("task_type", PayloadSchemaType.KEYWORD),
            ("technology", PayloadSchemaType.KEYWORD),
            ("success_verified", PayloadSchemaType.BOOL),
            ("knowledge_type", PayloadSchemaType.KEYWORD),
        ]
        
        for field_name, field_type in indexes:
            try:
                self.client.create_payload_index(
                    collection_name=self.COLLECTION_NAME,
                    field_name=field_name,
                    field_schema=field_type
                )
                logger.info(
                    "Created payload index | field=%s | type=%s",
                    field_name,
                    field_type
                )
            except Exception as e:
                logger.warning("Failed to create index for %s: %s", field_name, e)
    
    def get_collection_info(self) -> Optional[dict]:
        """Get information about the knowledge collection."""
        try:
            info = self.client.get_collection(self.COLLECTION_NAME)
            
            return {
                "name": info.config.name if hasattr(info.config, 'name') else self.COLLECTION_NAME,
                "vector_size": info.config.params.vectors.size,
                "distance": info.config.params.vectors.distance,
                "points_count": info.points_count if hasattr(info, 'points_count') else 0,
                "status": info.status.value if hasattr(info, 'status') else "unknown"
            }
        except Exception as e:
            logger.error("Failed to get collection info: %s", e)
            return None
    
    def test_vector_insertion(self) -> bool:
        """Test inserting a dummy vector to verify setup."""
        try:
            import uuid
            
            test_id = str(uuid.uuid4())
            test_vector = [0.1] * self.VECTOR_SIZE
            test_payload = {
                "content": "Test knowledge entry",
                "agent_type": "test_agent",
                "task_type": "test_task",
                "technology": "test",
                "success_verified": True,
                "knowledge_type": "test"
            }
            
            # Insert test point
            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[{
                    "id": test_id,
                    "vector": test_vector,
                    "payload": test_payload
                }]
            )
            
            logger.info("Test vector inserted successfully | id=%s", test_id)
            
            # Delete test point
            self.client.delete(
                collection_name=self.COLLECTION_NAME,
                points_selector=[test_id]
            )
            
            logger.info("Test vector deleted | id=%s", test_id)
            
            return True
            
        except Exception as e:
            logger.error("Test vector insertion failed: %s", e)
            return False
    
    async def setup_complete_system(self) -> dict:
        """
        Complete setup process.
        
        1. Create collection
        2. Create indexes
        3. Test insertion
        
        Returns:
            Dict with setup status
        """
        logger.info("Starting complete Qdrant setup")
        
        results = {
            "collection_created": False,
            "indexes_created": False,
            "test_passed": False,
            "errors": []
        }
        
        # Create collection
        if await self.create_knowledge_collection():
            results["collection_created"] = True
            results["indexes_created"] = True  # Created in create_knowledge_collection
        else:
            results["errors"].append("Failed to create collection")
            return results
        
        # Test insertion
        if self.test_vector_insertion():
            results["test_passed"] = True
        else:
            results["errors"].append("Test insertion failed")
        
        logger.info("Qdrant setup complete | results=%s", results)
        
        return results


# Convenience function for quick setup
async def setup_qdrant(qdrant_client: Optional[QdrantClient] = None) -> bool:
    """
    Convenience function to set up Qdrant collection.
    
    Args:
        qdrant_client: Optional Qdrant client instance
    
    Returns:
        True if setup succeeded
    """
    setup = QdrantSetup(qdrant_client)
    results = await setup.setup_complete_system()
    
    return results["collection_created"] and results["test_passed"]
