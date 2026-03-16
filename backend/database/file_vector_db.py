"""
File-based Vector Database implementation.

This module provides a simple file-based alternative to Qdrant for storing
and searching vector embeddings. Embeddings are stored in numpy files on disk.

Expected Metadata Structure:
    When inserting embeddings, the following metadata fields are recommended:
    - vectorizer_type (str): Type of vectorizer used ("tfidf" or "sbert")
    - model_version (str): Version or name of the model (e.g., "all-MiniLM-L6-v2")
    - embedding_date (str): ISO 8601 timestamp when embedding was created
    - media_id (str): Unique identifier for the media item
    
    Additional custom fields can be included as needed.
"""

import os
import json
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class FileVectorDatabase:
    """
    File-based vector database for storing and searching embeddings.
    
    This class provides a simple alternative to Qdrant that stores embeddings
    in numpy files on the local filesystem. It supports:
    - Inserting embeddings with metadata
    - Searching for similar embeddings using cosine similarity
    - Counting total embeddings
    - Deleting embeddings
    
    Storage structure:
    - embeddings/vectors.npy: numpy array of all vectors
    - embeddings/metadata.json: list of metadata for each vector
    - embeddings/ids.json: list of media IDs
    """
    
    def __init__(
        self,
        storage_path: str = "backend/embeddings",
        vector_size: int = 5000,
        **kwargs
    ):
        """
        Initialize file-based vector database.
        
        Args:
            storage_path: Directory path for storing embeddings
            vector_size: Dimensionality of vectors (default 5000 for TF-IDF,
                        use 384 for Sentence-BERT)
            **kwargs: Additional arguments (ignored, for compatibility)
        """
        self.storage_path = Path(storage_path)
        self.vector_size = vector_size
        
        # Create storage directory if it doesn't exist
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.vectors_file = self.storage_path / "vectors.npy"
        self.metadata_file = self.storage_path / "metadata.json"
        self.ids_file = self.storage_path / "ids.json"
        
        # Load existing data
        self._load_data()
        
        logger.info(f"FileVectorDatabase initialized: {self.storage_path}")
        logger.info(f"Vector size configured: {self.vector_size}")
        logger.info(f"Loaded {len(self.ids)} existing embeddings")
    
    def _load_data(self) -> None:
        """Load existing embeddings and metadata from disk."""
        if self.vectors_file.exists():
            self.vectors = np.load(str(self.vectors_file))
            
            # Validate that existing vectors match configured vector_size
            if len(self.vectors) > 0:
                existing_vector_size = self.vectors.shape[1]
                if existing_vector_size != self.vector_size:
                    logger.warning(
                        f"Vector size mismatch detected! "
                        f"Configured: {self.vector_size}, "
                        f"Existing data: {existing_vector_size}. "
                        f"Using existing vector size for backward compatibility."
                    )
                    # Update vector_size to match existing data for backward compatibility
                    self.vector_size = existing_vector_size
        else:
            self.vectors = np.empty((0, self.vector_size), dtype=np.float32)
        
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = []
        
        if self.ids_file.exists():
            with open(self.ids_file, 'r') as f:
                self.ids = json.load(f)
        else:
            self.ids = []
    
    def _save_data(self) -> None:
        """Save embeddings and metadata to disk."""
        np.save(str(self.vectors_file), self.vectors)
        
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f)
        
        with open(self.ids_file, 'w') as f:
            json.dump(self.ids, f)
    
    def batch_insert(self, items: list) -> None:
        """
        Insert or update multiple vectors efficiently in a single disk write.

        Args:
            items: List of (media_id, vector, metadata) tuples.
        """
        for media_id, vector, metadata in items:
            if len(vector) != self.vector_size:
                raise ValueError(
                    f"Vector size mismatch for {media_id}: "
                    f"expected {self.vector_size}, got {len(vector)}"
                )
            vector_array = np.array(vector, dtype=np.float32).reshape(1, -1)
            if media_id in self.ids:
                idx = self.ids.index(media_id)
                self.vectors[idx] = vector_array[0]
                self.metadata[idx] = metadata or {}
            else:
                self.vectors = np.vstack([self.vectors, vector_array])
                self.ids.append(media_id)
                self.metadata.append(metadata or {})
        self._save_data()

    def insert(
        self,
        media_id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Insert a vector embedding with metadata.
        
        Args:
            media_id: Unique identifier for the media item
            vector: Embedding vector as list of floats
            metadata: Optional metadata dictionary. Recommended fields:
                - vectorizer_type (str): "tfidf" or "sbert"
                - model_version (str): Model name/version (e.g., "all-MiniLM-L6-v2")
                - embedding_date (str): ISO 8601 timestamp
                - media_id (str): Media item identifier
                Additional custom fields can be included as needed.
        
        Raises:
            ValueError: If vector size doesn't match expected size
        """
        # Validate vector size
        if len(vector) != self.vector_size:
            raise ValueError(
                f"Vector size mismatch: provided vector has {len(vector)} dimensions, "
                f"but database is configured for {self.vector_size} dimensions. "
                f"Ensure the vectorizer type matches the database configuration "
                f"(TF-IDF: ~5000 dims, Sentence-BERT: 384 dims)."
            )
        
        # Convert to numpy array
        vector_array = np.array(vector, dtype=np.float32).reshape(1, -1)
        
        # Check if media_id already exists
        if media_id in self.ids:
            # Update existing embedding
            idx = self.ids.index(media_id)
            self.vectors[idx] = vector_array[0]
            self.metadata[idx] = metadata or {}
        else:
            # Append new embedding
            self.vectors = np.vstack([self.vectors, vector_array])
            self.ids.append(media_id)
            self.metadata.append(metadata or {})
        
        # Save to disk
        self._save_data()
    
    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        filter: Optional[Dict[str, Any]] = None  # Added for compatibility
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors using cosine similarity.
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            score_threshold: Minimum similarity score (0.0 to 1.0)
            filter: Optional filter (ignored in file-based storage, for compatibility)
        
        Returns:
            List of dictionaries with 'id' and 'score' keys, sorted by score descending
        
        Raises:
            ValueError: If query vector size doesn't match
        """
        if len(query_vector) != self.vector_size:
            raise ValueError(
                f"Query vector size mismatch: provided vector has {len(query_vector)} dimensions, "
                f"but database is configured for {self.vector_size} dimensions. "
                f"Ensure the vectorizer type matches the database configuration "
                f"(TF-IDF: ~5000 dims, Sentence-BERT: 384 dims)."
            )
        
        if len(self.vectors) == 0:
            return []
        
        # Convert query to numpy array
        query_array = np.array(query_vector, dtype=np.float32).reshape(1, -1)
        
        # Compute cosine similarity
        # cosine_similarity = dot(A, B) / (norm(A) * norm(B))
        query_norm = np.linalg.norm(query_array)
        vectors_norm = np.linalg.norm(self.vectors, axis=1)
        
        # Avoid division by zero
        if query_norm == 0:
            return []
        
        dot_products = np.dot(self.vectors, query_array.T).flatten()
        similarities = dot_products / (vectors_norm * query_norm + 1e-10)
        
        # Apply score threshold if specified
        if score_threshold is not None:
            valid_indices = np.where(similarities >= score_threshold)[0]
            similarities = similarities[valid_indices]
            valid_ids = [self.ids[i] for i in valid_indices]
        else:
            valid_indices = np.arange(len(similarities))
            valid_ids = self.ids
        
        # Get top k results
        if len(similarities) == 0:
            return []
        
        top_k = min(top_k, len(similarities))
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        # Return as list of dictionaries (compatible with Qdrant format)
        results = [
            {
                "id": valid_ids[idx],
                "score": float(similarities[idx])
            }
            for idx in top_indices
        ]
        
        return results
    
    def count(self) -> int:
        """
        Get total number of embeddings stored.
        
        Returns:
            Number of embeddings
        """
        return len(self.ids)
    
    def get_metadata(self, media_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific media item.
        
        Args:
            media_id: ID of the media item
        
        Returns:
            Metadata dictionary if found, None otherwise
        """
        if media_id not in self.ids:
            return None
        
        idx = self.ids.index(media_id)
        return self.metadata[idx]
    
    def delete(self, media_id: str) -> bool:
        """
        Delete an embedding by media ID.
        
        Args:
            media_id: ID of the media item to delete
        
        Returns:
            True if deleted, False if not found
        """
        if media_id not in self.ids:
            return False
        
        idx = self.ids.index(media_id)
        
        # Remove from arrays
        self.vectors = np.delete(self.vectors, idx, axis=0)
        self.ids.pop(idx)
        self.metadata.pop(idx)
        
        # Save to disk
        self._save_data()
        
        return True
    
    def clear(self) -> None:
        """Delete all embeddings."""
        self.vectors = np.empty((0, self.vector_size), dtype=np.float32)
        self.ids = []
        self.metadata = []
        self._save_data()
        logger.info("Cleared all embeddings")
    
    def close(self) -> None:
        """Close the database (no-op for file-based storage)."""
        logger.info("FileVectorDatabase closed")
