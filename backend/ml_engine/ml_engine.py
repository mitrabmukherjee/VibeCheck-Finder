"""
ML Engine class for the Semantic Media Engine.

This module provides the MLEngine class that integrates all ML components
including text preprocessing, vectorization, and similarity search.
"""

import os
from typing import List, Tuple, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from .preprocessing import preprocess_text
from .vectorizer import (
    train_vectorizer as _train_vectorizer,
    save_vectorizer,
    load_vectorizer,
    vectorize_query as _vectorize_query,
    find_similar as _find_similar
)
from .sentence_bert_vectorizer import SentenceBertVectorizer


class MLEngine:
    """
    Machine Learning Engine for text vectorization and similarity matching.
    
    This class integrates all ML components to provide a unified interface for:
    - Training TF-IDF vectorizers on media description corpora
    - Vectorizing user queries
    - Computing embeddings for media descriptions
    - Finding similar media items based on vector similarity
    - Tracking and validating model versions
    
    Attributes:
        vectorizer_path: Directory path where the vectorizer model is stored
        embeddings_path: Directory path where embeddings are stored
        vectorizer: Loaded TfidfVectorizer instance (None until loaded)
        model_version: Version identifier of the loaded vectorizer
        corpus_vectors: Cached corpus embedding vectors
        corpus_ids: Cached media IDs corresponding to corpus vectors
    
    Requirements:
        - 2.5: Load the pre-trained vectorizer model at initialization
        - 18.1: Include model_version in embedding metadata
        - 18.3: Verify model version matches expected version when loading
    """
    
    def __init__(
        self,
        vectorizer_path: str,
        embeddings_path: str,
        expected_version: Optional[str] = None,
        vectorizer_type: str = "tfidf",
        model_name: Optional[str] = None
    ):
        """
        Initialize the ML Engine with paths to model and embeddings.

        Args:
            vectorizer_path: Directory path where the vectorizer model is stored
            embeddings_path: Directory path where embeddings are stored
            expected_version: Optional expected model version for validation
            vectorizer_type: Type of vectorizer to use ("tfidf" or "sbert")
            model_name: Model name for Sentence-BERT (e.g., "all-MiniLM-L6-v2")
                       Only used when vectorizer_type="sbert"

        Raises:
            ValueError: If paths are invalid or version mismatch occurs
            FileNotFoundError: If vectorizer files don't exist

        Requirements:
            - 2.1: Support both TF-IDF and Sentence-BERT vectorizers
            - 2.5: Load the pre-trained vectorizer model at initialization
            - 5.1: Maintain backward compatibility with existing TF-IDF code
            - 5.5: Ensure API functionality unchanged
            - 18.3: Verify model version matches expected version when loading
        """
        self.vectorizer_path = vectorizer_path
        self.embeddings_path = embeddings_path
        self.vectorizer_type = vectorizer_type
        self.model_name = model_name
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.sbert_vectorizer = None  # For Sentence-BERT vectorizer
        self.model_version: Optional[str] = None
        self.corpus_vectors: Optional[np.ndarray] = None
        self.corpus_ids: Optional[List[str]] = None
        self.expected_version = expected_version

        # Validate paths
        if not vectorizer_path:
            raise ValueError("vectorizer_path cannot be empty")
        if not embeddings_path:
            raise ValueError("embeddings_path cannot be empty")

        # Validate vectorizer_type
        if vectorizer_type not in ["tfidf", "sbert"]:
            raise ValueError(
                f"vectorizer_type must be 'tfidf' or 'sbert', got '{vectorizer_type}'"
            )

        # Load appropriate vectorizer based on type
        if vectorizer_type == "tfidf":
            # Load TF-IDF vectorizer if it exists
            if os.path.exists(os.path.join(vectorizer_path, 'tfidf_vectorizer.pkl')):
                self._load_vectorizer()
        elif vectorizer_type == "sbert":
            # Load or initialize Sentence-BERT vectorizer
            self._load_sbert_vectorizer()


    
    def _load_vectorizer(self) -> None:
        """
        Load the pre-trained vectorizer and validate version.
        
        Raises:
            ValueError: If version mismatch occurs
            FileNotFoundError: If vectorizer files don't exist
        
        Requirements:
            - 2.5: Load the pre-trained vectorizer model at initialization
            - 18.3: Verify model version matches expected version when loading
        """
        vectorizer, metadata = load_vectorizer(self.vectorizer_path)
        self.vectorizer = vectorizer
        self.model_version = metadata.get('version')
        
        # Validate version if expected_version is provided
        if self.expected_version is not None:
            if self.model_version != self.expected_version:
                raise ValueError(
                    f"Model version mismatch: expected '{self.expected_version}', "
                    f"but loaded version is '{self.model_version}'"
                )
    
    def _load_sbert_vectorizer(self) -> None:
        """
        Load or initialize Sentence-BERT vectorizer.
        
        This method attempts to load a saved Sentence-BERT configuration from disk.
        If no saved configuration exists, it initializes a new vectorizer with the
        specified model_name (or default "all-MiniLM-L6-v2").
        
        Raises:
            Exception: If model fails to load or download
        
        Requirements:
            - 2.1: Support Sentence-BERT vectorizer initialization
            - 5.1: Maintain backward compatibility with existing code
        """
        metadata_file = os.path.join(self.vectorizer_path, 'sbert_metadata.json')
        
        if os.path.exists(metadata_file):
            # Load from saved configuration
            self.sbert_vectorizer = SentenceBertVectorizer.load(self.vectorizer_path)
            # Read metadata to get model version
            import json
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            self.model_version = metadata.get('model_name', 'all-MiniLM-L6-v2')
        else:
            # Initialize new vectorizer with specified or default model
            model_name = self.model_name or "all-MiniLM-L6-v2"
            self.sbert_vectorizer = SentenceBertVectorizer(
                model_name=model_name,
                cache_folder=None,  # Use default cache
                device=None  # Auto-detect device
            )
            self.model_version = model_name
    
    def vectorize_query(self, query: str) -> np.ndarray:
        """
        Transform user query into an embedding vector.
        
        This method preprocesses the query text and transforms it into a
        numerical vector representation using the loaded vectorizer (TF-IDF or Sentence-BERT).
        
        Args:
            query: User's natural language search query
        
        Returns:
            numpy array of shape (1, dimension) containing the query embedding
            - For TF-IDF: shape (1, ~5000)
            - For Sentence-BERT: shape (1, 384) for all-MiniLM-L6-v2 or (1, 768) for all-mpnet-base-v2
        
        Raises:
            ValueError: If query is empty after preprocessing or vector has zero norm
            TypeError: If query is not a string
            RuntimeError: If vectorizer is not loaded
        
        Examples:
            >>> engine = MLEngine("backend/models", "backend/embeddings")  # doctest: +SKIP
            >>> vector = engine.vectorize_query("mystery detective novel")  # doctest: +SKIP
            >>> vector.shape  # doctest: +SKIP
            (1, 5000)
        
        Requirements:
            - 2.2: Transform preprocessed text into embedding vector
            - 2.3: Ensure all values in vector are finite floats
            - 2.4: Ensure vector has non-zero norm
            - 1.4: Forward valid query to ML_Engine for vectorization
            - 5.3: Route to appropriate vectorizer based on type
        """
        # Validate input type
        if not isinstance(query, str):
            raise TypeError(f"query must be a string, got {type(query).__name__}")
        
        # Route to appropriate vectorizer based on type
        if self.vectorizer_type == "sbert":
            return self._vectorize_query_sbert(query)
        elif self.vectorizer_type == "tfidf":
            return self._vectorize_query_tfidf(query)
        else:
            raise RuntimeError(f"Unknown vectorizer_type: {self.vectorizer_type}")
    
    def _vectorize_query_tfidf(self, query: str) -> np.ndarray:
        """
        Transform query using TF-IDF vectorizer.
        
        Args:
            query: User's natural language search query
        
        Returns:
            numpy array of shape (1, dimension) containing the query embedding
        
        Raises:
            ValueError: If query is empty after preprocessing or vector has zero norm
            RuntimeError: If vectorizer is not loaded
        """
        if self.vectorizer is None:
            raise RuntimeError(
                "Vectorizer not loaded. Ensure vectorizer exists at initialization "
                "or call train_vectorizer() first."
            )
        
        # Preprocess the query text using the same preprocessing as training
        preprocessed_query = preprocess_text(query)
        
        # Validate preprocessed query is non-empty
        if not preprocessed_query:
            raise ValueError(
                "Query must contain valid text after preprocessing. "
                "The query became empty after removing special characters and whitespace."
            )
        
        # Transform the preprocessed query into a vector using loaded vectorizer
        query_vector = self.vectorizer.transform([preprocessed_query])
        
        # Convert sparse matrix to dense numpy array
        query_vector_dense = query_vector.toarray()
        
        # Validate output vector shape
        assert query_vector_dense.shape[0] == 1, \
            f"Query vector must have shape (1, d), got shape {query_vector_dense.shape}"
        
        # Validate all values are finite floats
        if not np.all(np.isfinite(query_vector_dense)):
            raise ValueError(
                "Query vector contains non-finite values (NaN or Inf). "
                "This indicates an issue with the vectorizer or input text."
            )
        
        # Validate vector has non-zero norm
        vector_norm = np.linalg.norm(query_vector_dense)
        if vector_norm == 0.0:
            raise ValueError(
                "Query vector has zero norm. This may occur if the query contains "
                "only words not present in the vectorizer's vocabulary."
            )
        
        return query_vector_dense
    
    def _vectorize_query_sbert(self, query: str) -> np.ndarray:
        """
        Transform query using Sentence-BERT vectorizer.
        
        Args:
            query: User's natural language search query
        
        Returns:
            numpy array of shape (1, dimension) containing the query embedding
            - Dimension depends on the model (384 for all-MiniLM-L6-v2, 768 for all-mpnet-base-v2)
        
        Raises:
            ValueError: If query is empty or vector contains non-finite values
            RuntimeError: If Sentence-BERT vectorizer is not loaded
        """
        if self.sbert_vectorizer is None:
            raise RuntimeError(
                "Sentence-BERT vectorizer not loaded. Ensure vectorizer is initialized."
            )
        
        # Validate query is non-empty (no preprocessing needed for Sentence-BERT)
        if not query or not query.strip():
            raise ValueError(
                "Query must contain valid text. Empty queries are not allowed."
            )
        
        # Encode the query using Sentence-BERT
        # The encode method returns shape (1, dimension) for single text input
        query_vector = self.sbert_vectorizer.encode(
            query.strip(),
            normalize_embeddings=True
        )
        
        # Get expected dimension from the model
        expected_dim = self.sbert_vectorizer.get_embedding_dimension()
        
        # Validate output vector shape
        assert query_vector.shape[0] == 1, \
            f"Query vector must have shape (1, d), got shape {query_vector.shape}"
        assert query_vector.shape[1] == expected_dim, \
            f"Sentence-BERT vector must have {expected_dim} dimensions, got {query_vector.shape[1]}"
        
        # Validate all values are finite floats
        if not np.all(np.isfinite(query_vector)):
            raise ValueError(
                "Query vector contains non-finite values (NaN or Inf). "
                "This indicates an issue with the model or input text."
            )
        
        return query_vector
    
    def find_similar(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        similarity_metric: str = "cosine"
    ) -> List[Tuple[str, float]]:
        """
        Find top-k most similar media items based on vector similarity.
        
        This method computes similarity scores between a query vector and the
        corpus of media item vectors, returning the top-k most similar items.
        
        Args:
            query_vector: Query embedding vector of shape (1, dimension)
            top_k: Number of top results to return (default: 5)
            similarity_metric: Similarity metric to use (default: "cosine")
        
        Returns:
            List of (media_id, similarity_score) tuples sorted by score descending
        
        Raises:
            ValueError: If query_vector has invalid shape or top_k is invalid
            RuntimeError: If corpus vectors are not loaded
        
        Examples:
            >>> engine = MLEngine("backend/models", "backend/embeddings")  # doctest: +SKIP
            >>> query_vec = engine.vectorize_query("mystery novel")  # doctest: +SKIP
            >>> results = engine.find_similar(query_vec, top_k=5)  # doctest: +SKIP
            >>> len(results)  # doctest: +SKIP
            5
        
        Requirements:
            - 3.1: Search the Vector_DB for similar embeddings
            - 3.2: Use cosine similarity as the default metric
            - 3.3: Return scores in the range 0.0 to 1.0
            - 3.4: Return top-k most similar items sorted by score descending
        """
        if self.corpus_vectors is None or self.corpus_ids is None:
            raise RuntimeError(
                "Corpus vectors not loaded. Call load_corpus() or compute_embeddings() first."
            )
        
        return _find_similar(
            query_vector,
            self.corpus_vectors,
            self.corpus_ids,
            top_k,
            similarity_metric
        )
    
    def train_vectorizer(
        self,
        descriptions: List[str],
        max_features: Optional[int] = 5000,
        ngram_range: Tuple[int, int] = (1, 2),
        min_df: int = 1,
        max_df: float = 1.0,
        save: bool = True
    ) -> TfidfVectorizer:
        """
        Train a TF-IDF vectorizer on a corpus of media descriptions.
        
        This method creates and fits a new TF-IDF vectorizer, optionally saving
        it to disk with version metadata for future use.
        
        Args:
            descriptions: List of media description strings to train on
            max_features: Maximum number of features (vocabulary size)
            ngram_range: Range of n-grams to extract (min_n, max_n)
            min_df: Minimum document frequency for a term
            max_df: Maximum document frequency (as fraction) for a term
            save: Whether to save the trained vectorizer to disk
        
        Returns:
            Fitted TfidfVectorizer instance
        
        Raises:
            ValueError: If descriptions list is empty or invalid
            TypeError: If descriptions contains non-string elements
        
        Examples:
            >>> engine = MLEngine("backend/models", "backend/embeddings")  # doctest: +SKIP
            >>> descriptions = ["A mystery novel", "A sci-fi adventure"]  # doctest: +SKIP
            >>> vectorizer = engine.train_vectorizer(descriptions)  # doctest: +SKIP
        
        Requirements:
            - 8.2: Train a new TF-IDF vectorizer on all media descriptions
            - 8.3: Ensure the corpus contains at least one non-empty description
            - 8.4: Save trained vectorizer to disk for future use
            - 18.2: Assign unique version identifier when training new vectorizer
        """
        vectorizer = _train_vectorizer(
            descriptions,
            max_features,
            ngram_range,
            min_df,
            max_df
        )
        
        self.vectorizer = vectorizer
        
        if save:
            version = save_vectorizer(vectorizer, self.vectorizer_path)
            self.model_version = version
            # Reload to ensure metadata is properly loaded
            self._load_vectorizer()
        
        return vectorizer
    
    def compute_embeddings(
        self,
        descriptions: List[str],
        media_ids: List[str],
        batch_size: int = 32
    ) -> np.ndarray:
        """
        Generate embeddings for all media descriptions.

        This method transforms a list of media descriptions into embedding
        vectors using the loaded vectorizer (TF-IDF or Sentence-BERT).
        The embeddings are cached internally for use with find_similar().

        For Sentence-BERT, batch encoding is used for efficiency.
        For TF-IDF, the batch_size parameter is ignored.

        Args:
            descriptions: List of media description strings
            media_ids: List of media IDs corresponding to descriptions
            batch_size: Batch size for Sentence-BERT encoding (default: 32)

        Returns:
            numpy array of shape (n, dimension) containing embeddings

        Raises:
            ValueError: If descriptions and media_ids have different lengths
            RuntimeError: If vectorizer is not loaded
            TypeError: If descriptions contains non-string elements

        Examples:
            >>> engine = MLEngine("backend/models", "backend/embeddings")  # doctest: +SKIP
            >>> descriptions = ["A mystery novel", "A sci-fi adventure"]  # doctest: +SKIP
            >>> ids = ["id1", "id2"]  # doctest: +SKIP
            >>> embeddings = engine.compute_embeddings(descriptions, ids)  # doctest: +SKIP
            >>> embeddings.shape  # doctest: +SKIP
            (2, 384)  # For Sentence-BERT

        Requirements:
            - 3.2: Use batch encoding for efficiency with Sentence-BERT
            - 9.2: Ensure each embedding has the correct dimensionality
            - 9.3: Ensure all vector values are finite floats
            - 18.1: Include model_version in embedding metadata
        """
        # Check if appropriate vectorizer is loaded
        if self.vectorizer_type == "sbert":
            if self.sbert_vectorizer is None:
                raise RuntimeError(
                    "Sentence-BERT vectorizer not loaded. Ensure vectorizer exists at initialization."
                )
        else:
            if self.vectorizer is None:
                raise RuntimeError(
                    "Vectorizer not loaded. Ensure vectorizer exists at initialization "
                    "or call train_vectorizer() first."
                )

        if len(descriptions) != len(media_ids):
            raise ValueError(
                f"descriptions length ({len(descriptions)}) must match "
                f"media_ids length ({len(media_ids)})"
            )

        # Validate all descriptions are strings
        for i, desc in enumerate(descriptions):
            if not isinstance(desc, str):
                raise TypeError(
                    f"descriptions[{i}] must be a string, got {type(desc).__name__}"
                )

        # Route to appropriate vectorizer based on type
        if self.vectorizer_type == "sbert":
            # Use Sentence-BERT batch encoding
            embeddings_dense = self.sbert_vectorizer.encode(
                descriptions,
                batch_size=batch_size,
                show_progress_bar=False,
                normalize_embeddings=True
            )
        else:
            # Use TF-IDF vectorization (batch_size ignored)
            # Preprocess all descriptions
            preprocessed = [preprocess_text(desc) for desc in descriptions]

            # Transform descriptions into embeddings
            embeddings = self.vectorizer.transform(preprocessed)

            # Convert sparse matrix to dense numpy array
            embeddings_dense = embeddings.toarray()

        # Validate all values are finite
        if not np.all(np.isfinite(embeddings_dense)):
            raise ValueError(
                "Computed embeddings contain non-finite values (NaN or Inf). "
                "This may indicate invalid input text or vectorizer issues."
            )

        # Cache corpus vectors and IDs for similarity search
        self.corpus_vectors = embeddings_dense
        self.corpus_ids = media_ids

        return embeddings_dense


    
    def load_corpus(
        self,
        corpus_vectors: np.ndarray,
        corpus_ids: List[str]
    ) -> None:
        """
        Load pre-computed corpus embeddings for similarity search.
        
        This method allows loading embeddings that were computed and stored
        previously, avoiding the need to recompute them.
        
        Args:
            corpus_vectors: numpy array of shape (n, dimension) with embeddings
            corpus_ids: List of media IDs corresponding to embeddings
        
        Raises:
            ValueError: If corpus_vectors and corpus_ids have mismatched lengths
            ValueError: If corpus_vectors has invalid shape or values
        """
        if corpus_vectors.ndim != 2:
            raise ValueError(
                f"corpus_vectors must be 2-dimensional, got {corpus_vectors.ndim} dimensions"
            )
        
        if len(corpus_ids) != corpus_vectors.shape[0]:
            raise ValueError(
                f"corpus_ids length ({len(corpus_ids)}) must match "
                f"corpus_vectors rows ({corpus_vectors.shape[0]})"
            )
        
        if not np.all(np.isfinite(corpus_vectors)):
            raise ValueError(
                "corpus_vectors contain non-finite values (NaN or Inf)"
            )
        
        self.corpus_vectors = corpus_vectors
        self.corpus_ids = corpus_ids
    
    def get_model_version(self) -> Optional[str]:
        """
        Get the current model version.
        
        Returns:
            Model version string or None if no vectorizer is loaded
        
        Requirements:
            - 18.1: Track model version for embeddings
        """
        return self.model_version
    
    def validate_model_version(self, expected_version: str) -> bool:
        """
        Validate that the loaded model matches the expected version.
        
        Args:
            expected_version: Expected model version string
        
        Returns:
            True if versions match, False otherwise
        
        Requirements:
            - 18.3: Verify model version matches expected version
        """
        return self.model_version == expected_version
