"""
Vector Database module for storing and searching media embeddings.

This module provides a VectorDatabase class that interfaces with Qdrant
for storing embeddings and performing similarity searches.
"""

from typing import List, Dict, Any, Optional
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

logger = logging.getLogger(__name__)


class VectorDatabase:
    """
    Interface for vector similarity search using Qdrant.
    
    This class manages the connection to Qdrant and provides methods for
    inserting embeddings, searching for similar vectors, and deleting entries.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection_name: str = "media_embeddings",
        vector_size: int = 512,
        distance_metric: Distance = Distance.COSINE,
    ):
        """
        Initialize Qdrant client and ensure collection exists.
        
        Args:
            host: Qdrant server host
            port: Qdrant server port
            collection_name: Name of the collection to use
            vector_size: Dimensionality of the vectors
            distance_metric: Similarity metric (COSINE, EUCLID, DOT)
        """
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.distance_metric = distance_metric
        
        # Initialize Qdrant client
        self.client = QdrantClient(host=host, port=port)
        
        # Create collection if it doesn't exist
        self._ensure_collection_exists()
        
        logger.info(
            f"VectorDatabase initialized: {host}:{port}, "
            f"collection={collection_name}, size={vector_size}"
        )
    
    def _ensure_collection_exists(self) -> None:
        """Create collection if it doesn't exist."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=self.distance_metric,
                    ),
                )
                logger.info(f"Created collection: {self.collection_name}")
            else:
                logger.info(f"Collection already exists: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise
    
    def insert(
        self,
        id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Insert or update a vector embedding in the database.
        
        Args:
            id: Unique identifier for the media item
            vector: Embedding vector (must match vector_size)
            metadata: Optional metadata to store with the vector
        
        Raises:
            ValueError: If vector size doesn't match expected size
            Exception: If insertion fails
        """
        if len(vector) != self.vector_size:
            raise ValueError(
                f"Vector size mismatch: expected {self.vector_size}, "
                f"got {len(vector)}"
            )
        
        # Validate all values are finite
        if not all(isinstance(v, (int, float)) and abs(v) != float('inf') for v in vector):
            raise ValueError("Vector must contain only finite float values")
        
        try:
            point = PointStruct(
                id=id,
                vector=vector,
                payload=metadata or {},
            )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point],
            )
            
            logger.debug(f"Inserted vector for media_id: {id}")
        except Exception as e:
            logger.error(f"Error inserting vector for {id}: {e}")
            raise
    
    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in the database.
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filter: Optional metadata filters
        
        Returns:
            List of dictionaries containing:
                - id: Media item ID
                - score: Similarity score (0.0 to 1.0 for cosine)
                - metadata: Associated metadata
        
        Raises:
            ValueError: If query_vector size doesn't match expected size
            Exception: If search fails
        """
        if len(query_vector) != self.vector_size:
            raise ValueError(
                f"Query vector size mismatch: expected {self.vector_size}, "
                f"got {len(query_vector)}"
            )
        
        try:
            # Build filter if provided
            query_filter = None
            if filter:
                conditions = []
                for key, value in filter.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value),
                        )
                    )
                if conditions:
                    query_filter = Filter(must=conditions)
            
            # Perform search
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=query_filter,
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.id,
                    "score": result.score,
                    "metadata": result.payload,
                })
            
            logger.debug(f"Search returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching vectors: {e}")
            raise
    
    def delete(self, id: str) -> None:
        """
        Delete a vector from the database.
        
        Args:
            id: Media item ID to delete
        
        Raises:
            Exception: If deletion fails
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[id],
            )
            logger.debug(f"Deleted vector for media_id: {id}")
        except Exception as e:
            logger.error(f"Error deleting vector for {id}: {e}")
            raise
    
    def count(self) -> int:
        """
        Get the total number of vectors in the collection.
        
        Returns:
            Number of vectors stored
        """
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return collection_info.points_count
        except Exception as e:
            logger.error(f"Error getting collection count: {e}")
            raise
    
    def close(self) -> None:
        """Close the connection to Qdrant."""
        try:
            self.client.close()
            logger.info("VectorDatabase connection closed")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
            raise
