"""
Sentence-BERT vectorizer for semantic text embeddings.

This module provides a wrapper around the sentence-transformers library
to generate dense embeddings with the same interface as the TF-IDF vectorizer
for compatibility with the existing MLEngine infrastructure.
"""

import os
import json
from datetime import datetime
from typing import Union, List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer


class SentenceBertVectorizer:
    """
    Sentence-BERT vectorizer for semantic text embeddings.
    
    Wraps the sentence-transformers library to provide dense embeddings
    with the same interface as the TF-IDF vectorizer for compatibility.
    
    This class produces 384-dimensional dense embeddings using the
    all-MiniLM-L6-v2 pretrained model by default. Embeddings are L2-normalized
    to ensure consistent similarity scores.
    
    Requirements:
        - 1.2: Use sentence-transformers library with all-MiniLM-L6-v2 model
        - 1.3: Download model weights if not cached locally
        - 1.4: Produce 384-dimensional dense embeddings
        - 2.1: Replace TF-IDF vectorizer with Sentence-BERT
        - 2.2: Generate 384-dimensional dense embedding vectors
        - 2.3: Encode queries and descriptions in same embedding space
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        cache_folder: Optional[str] = None,
        device: Optional[str] = None
    ):
        """
        Initialize Sentence-BERT model.
        
        Args:
            model_name: Pretrained model name from sentence-transformers.
                       Default is "all-MiniLM-L6-v2" which produces 384-dim embeddings.
            cache_folder: Directory to cache model weights. If None, uses default cache.
            device: Device to run model on ('cpu', 'cuda', or None for auto-detection).
        
        Raises:
            Exception: If model fails to load or download
        """
        self.model_name = model_name
        self.cache_folder = cache_folder
        self.device = device
        
        # Load the sentence-transformers model
        # This will download the model if not already cached
        self.model = SentenceTransformer(
            model_name,
            cache_folder=cache_folder,
            device=device
        )
        
        # Store embedding dimension for validation
        self._embedding_dimension = self.model.get_sentence_embedding_dimension()

    
    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        show_progress_bar: bool = False,
        normalize_embeddings: bool = True
    ) -> np.ndarray:
        """
        Encode text(s) into embedding vector(s).
        
        This method transforms text into dense 384-dimensional embeddings.
        It handles both single strings and lists of strings, returning
        appropriately shaped numpy arrays.
        
        Args:
            texts: Single text string or list of texts to encode
            batch_size: Batch size for encoding (used when texts is a list)
            show_progress_bar: Whether to show progress bar during encoding
            normalize_embeddings: Whether to L2-normalize embeddings (default: True)
        
        Returns:
            numpy array of shape (n, 384) for n texts, or (1, 384) for single text
        
        Raises:
            ValueError: If texts is empty or contains invalid data
        
        Examples:
            >>> vectorizer = SentenceBertVectorizer()
            >>> # Single text
            >>> embedding = vectorizer.encode("A mystery novel")
            >>> embedding.shape
            (1, 384)
            >>> # Multiple texts
            >>> embeddings = vectorizer.encode(["Text 1", "Text 2"])
            >>> embeddings.shape
            (2, 384)
        
        Requirements:
            - 2.2: Generate 384-dimensional dense embedding vectors
            - 2.3: Encode queries and descriptions in same embedding space
        """
        # Handle single string input by converting to list
        if isinstance(texts, str):
            texts = [texts]
            single_input = True
        else:
            single_input = False
        
        # Validate input
        if not texts:
            raise ValueError("texts cannot be empty")
        
        # Encode texts using the sentence-transformers model
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress_bar,
            normalize_embeddings=normalize_embeddings,
            convert_to_numpy=True
        )
        
        # Ensure embeddings is 2D array
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimensionality of embeddings.
        
        Returns:
            384 for the all-MiniLM-L6-v2 model
        
        Requirements:
            - 1.4: Produce 384-dimensional dense embeddings
        """
        return self._embedding_dimension
    
    def save(self, path: str) -> None:
        """
        Save model configuration and metadata.
        
        This method saves the model configuration (model name, cache folder, device)
        and metadata (embedding dimension, creation date) to a JSON file.
        The actual model weights are managed by sentence-transformers cache.
        
        Args:
            path: Directory path where configuration should be saved
        
        Raises:
            OSError: If unable to create directory or write file
        
        Requirements:
            - 2.1: Support saving model configuration for persistence
        """
        # Create directory if it doesn't exist
        os.makedirs(path, exist_ok=True)
        
        # Create metadata dictionary
        metadata = {
            'model_name': self.model_name,
            'cache_folder': self.cache_folder,
            'device': self.device,
            'embedding_dimension': self._embedding_dimension,
            'vectorizer_type': 'sbert',
            'created_at': datetime.now().isoformat(),
            'library_version': 'sentence-transformers>=2.0.0'
        }
        
        # Save metadata to JSON file
        metadata_file = os.path.join(path, 'sbert_metadata.json')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    @classmethod
    def load(cls, path: str) -> "SentenceBertVectorizer":
        """
        Load model from saved configuration.
        
        This method loads the model configuration from a JSON file and
        initializes a new SentenceBertVectorizer instance with those settings.
        
        Args:
            path: Directory path where configuration is stored
        
        Returns:
            New SentenceBertVectorizer instance with loaded configuration
        
        Raises:
            FileNotFoundError: If metadata file doesn't exist at path
            ValueError: If metadata is invalid or corrupted
        
        Requirements:
            - 2.1: Support loading model configuration from disk
        """
        metadata_file = os.path.join(path, 'sbert_metadata.json')
        
        if not os.path.exists(metadata_file):
            raise FileNotFoundError(f"Metadata file not found at {metadata_file}")
        
        # Load metadata from JSON file
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Validate metadata
        if 'model_name' not in metadata:
            raise ValueError("Invalid metadata: missing 'model_name' field")
        
        # Create new instance with loaded configuration
        return cls(
            model_name=metadata['model_name'],
            cache_folder=metadata.get('cache_folder'),
            device=metadata.get('device')
        )
