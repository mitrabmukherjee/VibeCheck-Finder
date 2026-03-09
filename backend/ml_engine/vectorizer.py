"""
Vectorizer training and management module for the Semantic Media Engine.

This module provides functions to train TF-IDF vectorizers on media description
corpora and save them to disk with version metadata for future use.
"""

import os
import pickle
from datetime import datetime
from typing import List, Optional, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .preprocessing import preprocess_text


def train_vectorizer(
    descriptions: List[str],
    max_features: Optional[int] = 5000,
    ngram_range: Tuple[int, int] = (1, 2),
    min_df: int = 1,
    max_df: float = 1.0
) -> TfidfVectorizer:
    """
    Train a TF-IDF vectorizer on a corpus of media descriptions.
    
    This function creates and fits a TF-IDF vectorizer with configurable parameters,
    ensuring the corpus is valid before training. The vectorizer uses preprocessed
    text to ensure consistency between training and inference.
    
    Args:
        descriptions: List of media description strings to train on
        max_features: Maximum number of features (vocabulary size). None for unlimited.
        ngram_range: Range of n-grams to extract (min_n, max_n). Default (1, 2) for unigrams and bigrams.
        min_df: Minimum document frequency for a term to be included
        max_df: Maximum document frequency (as fraction) for a term to be included
    
    Returns:
        Fitted TfidfVectorizer instance ready for transforming new text
    
    Raises:
        ValueError: If descriptions list is empty or contains no non-empty descriptions after preprocessing
        TypeError: If descriptions is not a list or contains non-string elements
    
    Examples:
        >>> descriptions = ["A mystery novel", "A sci-fi adventure", "A romance story"]
        >>> vectorizer = train_vectorizer(descriptions, max_features=100)
        >>> vectorizer.vocabulary_  # doctest: +SKIP
        {'mystery': 5, 'novel': 6, 'scifi': 7, ...}
    
    Requirements:
        - 8.2: Train a new TF-IDF vectorizer on all media descriptions
        - 8.3: Ensure the corpus contains at least one non-empty description
    """
    # Validate input type
    if not isinstance(descriptions, list):
        raise TypeError(f"descriptions must be a list, got {type(descriptions).__name__}")
    
    if len(descriptions) == 0:
        raise ValueError("descriptions list cannot be empty")
    
    # Validate all elements are strings
    for i, desc in enumerate(descriptions):
        if not isinstance(desc, str):
            raise TypeError(f"descriptions[{i}] must be a string, got {type(desc).__name__}")
    
    # Preprocess all descriptions to ensure consistency
    preprocessed = [preprocess_text(desc) for desc in descriptions]
    
    # Validate corpus has at least one non-empty description after preprocessing
    non_empty_count = sum(1 for desc in preprocessed if desc)
    if non_empty_count == 0:
        raise ValueError(
            "Corpus must contain at least one non-empty description after preprocessing. "
            f"All {len(descriptions)} descriptions became empty after preprocessing."
        )
    
    # Create and fit the TF-IDF vectorizer
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=ngram_range,
        min_df=min_df,
        max_df=max_df,
        lowercase=False,  # Already handled by preprocessing
        strip_accents=None,  # Already handled by preprocessing
        token_pattern=r'\b\w+\b',  # Standard word tokenization
        stop_words=None  # No stop words removal (keep all terms)
    )
    
    # Fit the vectorizer on preprocessed descriptions
    vectorizer.fit(preprocessed)
    
    return vectorizer


def save_vectorizer(
    vectorizer: TfidfVectorizer,
    save_path: str,
    version: Optional[str] = None
) -> str:
    """
    Save a trained vectorizer to disk with version metadata.
    
    This function serializes the vectorizer and stores it with metadata including
    a version identifier for tracking model updates. The version is automatically
    generated if not provided.
    
    Args:
        vectorizer: Fitted TfidfVectorizer instance to save
        save_path: Directory path where the vectorizer should be saved
        version: Optional version identifier. If None, generates timestamp-based version.
    
    Returns:
        The version identifier assigned to the saved vectorizer
    
    Raises:
        ValueError: If vectorizer is not fitted or save_path is invalid
        OSError: If unable to create directory or write file
    
    Examples:
        >>> vectorizer = train_vectorizer(["sample text"])  # doctest: +SKIP
        >>> version = save_vectorizer(vectorizer, "backend/models")  # doctest: +SKIP
        >>> print(version)  # doctest: +SKIP
        'v1.0.0_20240101_120000'
    
    Requirements:
        - 8.4: Save trained vectorizer to disk for future use
        - 18.2: Assign unique version identifier when training new vectorizer
    """
    # Validate vectorizer is fitted
    if not hasattr(vectorizer, 'vocabulary_'):
        raise ValueError("Vectorizer must be fitted before saving")
    
    # Generate version if not provided
    if version is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version = f"v1.0.0_{timestamp}"
    
    # Create save directory if it doesn't exist
    os.makedirs(save_path, exist_ok=True)
    
    # Create metadata dictionary
    metadata = {
        'version': version,
        'created_at': datetime.now().isoformat(),
        'vocabulary_size': len(vectorizer.vocabulary_),
        'max_features': vectorizer.max_features,
        'ngram_range': vectorizer.ngram_range,
        'min_df': vectorizer.min_df,
        'max_df': vectorizer.max_df
    }
    
    # Save vectorizer and metadata as a single pickle file
    vectorizer_file = os.path.join(save_path, 'tfidf_vectorizer.pkl')
    metadata_file = os.path.join(save_path, 'vectorizer_metadata.pkl')
    
    with open(vectorizer_file, 'wb') as f:
        pickle.dump(vectorizer, f)
    
    with open(metadata_file, 'wb') as f:
        pickle.dump(metadata, f)
    
    return version


def load_vectorizer(load_path: str) -> Tuple[TfidfVectorizer, dict]:
    """
    Load a trained vectorizer from disk with its metadata.
    
    Args:
        load_path: Directory path where the vectorizer is stored
    
    Returns:
        Tuple of (vectorizer, metadata) where metadata contains version info
    
    Raises:
        FileNotFoundError: If vectorizer files don't exist at load_path
        OSError: If unable to read files
    
    Examples:
        >>> vectorizer, metadata = load_vectorizer("backend/models")  # doctest: +SKIP
        >>> print(metadata['version'])  # doctest: +SKIP
        'v1.0.0_20240101_120000'
    """
    vectorizer_file = os.path.join(load_path, 'tfidf_vectorizer.pkl')
    metadata_file = os.path.join(load_path, 'vectorizer_metadata.pkl')
    
    if not os.path.exists(vectorizer_file):
        raise FileNotFoundError(f"Vectorizer file not found at {vectorizer_file}")
    
    if not os.path.exists(metadata_file):
        raise FileNotFoundError(f"Metadata file not found at {metadata_file}")
    
    with open(vectorizer_file, 'rb') as f:
        vectorizer = pickle.load(f)
    
    with open(metadata_file, 'rb') as f:
        metadata = pickle.load(f)
    
    return vectorizer, metadata


def vectorize_query(query: str, vectorizer_path: str) -> np.ndarray:
    """
    Transform user query into an embedding vector.
    
    This function loads a pre-trained vectorizer, preprocesses the query text
    using the same preprocessing pipeline as training, and transforms it into
    a numerical vector representation. The output is validated to ensure it
    has the correct shape, contains only finite values, and has non-zero norm.
    
    Args:
        query: User's natural language search query
        vectorizer_path: Directory path where the trained vectorizer is stored
    
    Returns:
        numpy array of shape (1, dimension) containing the query embedding
    
    Raises:
        ValueError: If query is empty after preprocessing, or if vector has zero norm
        FileNotFoundError: If vectorizer files don't exist at vectorizer_path
        TypeError: If query is not a string
    
    Examples:
        >>> # Assuming a vectorizer is trained and saved
        >>> vector = vectorize_query("mystery detective novel", "backend/models")  # doctest: +SKIP
        >>> vector.shape  # doctest: +SKIP
        (1, 5000)
        >>> np.all(np.isfinite(vector))  # doctest: +SKIP
        True
        >>> np.linalg.norm(vector) > 0  # doctest: +SKIP
        True
    
    Requirements:
        - 2.2: Transform preprocessed text into embedding vector using trained TF-IDF vectorizer
        - 2.3: Ensure all values in vector are finite floats
        - 2.4: Ensure vector has non-zero norm
        - 1.4: Forward valid query to ML_Engine for vectorization
    """
    # Validate input type
    if not isinstance(query, str):
        raise TypeError(f"query must be a string, got {type(query).__name__}")
    
    # Preprocess the query text using the same preprocessing as training
    preprocessed_query = preprocess_text(query)
    
    # Validate preprocessed query is non-empty
    if not preprocessed_query:
        raise ValueError(
            "Query must contain valid text after preprocessing. "
            "The query became empty after removing special characters and whitespace."
        )
    
    # Load the trained vectorizer
    vectorizer, metadata = load_vectorizer(vectorizer_path)
    
    # Transform the preprocessed query into a vector
    query_vector = vectorizer.transform([preprocessed_query])
    
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


def find_similar(
    query_vector: np.ndarray,
    corpus_vectors: np.ndarray,
    corpus_ids: List[str],
    top_k: int = 5,
    similarity_metric: str = "cosine"
) -> List[Tuple[str, float]]:
    """
    Find top-k most similar media items based on vector similarity.
    
    This function computes similarity scores between a query vector and a corpus
    of media item vectors, returning the top-k most similar items sorted by
    score in descending order. The function ensures all scores are in the valid
    range [0.0, 1.0] for cosine similarity and that all values are finite.
    
    Args:
        query_vector: Query embedding vector of shape (1, dimension)
        corpus_vectors: Corpus embedding vectors of shape (n, dimension)
        corpus_ids: List of media IDs corresponding to corpus vectors
        top_k: Number of top results to return (default: 5)
        similarity_metric: Similarity metric to use (default: "cosine")
    
    Returns:
        List of (media_id, similarity_score) tuples sorted by score descending
    
    Raises:
        ValueError: If query_vector or corpus_vectors have invalid shapes
        ValueError: If corpus_ids length doesn't match corpus_vectors
        ValueError: If top_k is not positive or exceeds corpus size
        ValueError: If similarity_metric is not supported
        ValueError: If any computed scores are non-finite
    
    Examples:
        >>> query_vec = np.array([[0.5, 0.5, 0.0]])
        >>> corpus_vecs = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.5, 0.5, 0.0]])
        >>> ids = ["id1", "id2", "id3"]
        >>> results = find_similar(query_vec, corpus_vecs, ids, top_k=2)
        >>> len(results)
        2
        >>> results[0][1] >= results[1][1]  # Scores are descending
        True
        >>> all(0.0 <= score <= 1.0 for _, score in results)  # Scores in valid range
        True
    
    Requirements:
        - 3.1: Search the Vector_DB for similar embeddings
        - 3.2: Use cosine similarity as the default metric
        - 3.3: Return scores in the range 0.0 to 1.0
        - 3.4: Return top-k most similar items sorted by score descending
        - 20.1: Ensure no duplicate media IDs are present
        - 20.2: Deduplicate if necessary, keeping highest score
        - 20.3: Keep entry with highest similarity score when deduplicating
    """
    # Validate query_vector shape
    if query_vector.ndim != 2 or query_vector.shape[0] != 1:
        raise ValueError(
            f"query_vector must have shape (1, d), got shape {query_vector.shape}"
        )
    
    # Validate corpus_vectors shape
    if corpus_vectors.ndim != 2:
        raise ValueError(
            f"corpus_vectors must be 2-dimensional, got {corpus_vectors.ndim} dimensions"
        )
    
    # Validate corpus_ids length matches corpus_vectors
    if len(corpus_ids) != corpus_vectors.shape[0]:
        raise ValueError(
            f"corpus_ids length ({len(corpus_ids)}) must match "
            f"corpus_vectors rows ({corpus_vectors.shape[0]})"
        )
    
    # Validate dimensions match
    if query_vector.shape[1] != corpus_vectors.shape[1]:
        raise ValueError(
            f"query_vector dimension ({query_vector.shape[1]}) must match "
            f"corpus_vectors dimension ({corpus_vectors.shape[1]})"
        )
    
    # Validate top_k
    if top_k <= 0:
        raise ValueError(f"top_k must be positive, got {top_k}")
    
    if top_k > len(corpus_ids):
        raise ValueError(
            f"top_k ({top_k}) cannot exceed corpus size ({len(corpus_ids)})"
        )
    
    # Validate similarity_metric
    supported_metrics = ["cosine"]
    if similarity_metric not in supported_metrics:
        raise ValueError(
            f"similarity_metric must be one of {supported_metrics}, "
            f"got '{similarity_metric}'"
        )
    
    # Compute similarity scores
    if similarity_metric == "cosine":
        # Compute cosine similarity
        # sklearn's cosine_similarity returns values in [-1, 1]
        # For text embeddings (TF-IDF), values are typically in [0, 1]
        similarity_scores = cosine_similarity(query_vector, corpus_vectors)[0]
    else:
        # This should never be reached due to validation above
        raise ValueError(f"Unsupported similarity metric: {similarity_metric}")
    
    # Validate all scores are finite
    if not np.all(np.isfinite(similarity_scores)):
        raise ValueError(
            "Computed similarity scores contain non-finite values (NaN or Inf). "
            "This may indicate invalid input vectors."
        )
    
    # Clip scores to [0.0, 1.0] range for cosine similarity
    # This handles any numerical precision issues
    similarity_scores = np.clip(similarity_scores, 0.0, 1.0)
    
    # Create list of (media_id, score) tuples
    results = list(zip(corpus_ids, similarity_scores))
    
    # Deduplicate by media_id, keeping the highest score
    # (This handles Requirement 20.2 and 20.3)
    seen_ids = {}
    for media_id, score in results:
        if media_id not in seen_ids or score > seen_ids[media_id]:
            seen_ids[media_id] = score
    
    # Convert back to list of tuples
    deduplicated_results = [(media_id, score) for media_id, score in seen_ids.items()]
    
    # Sort by score in descending order
    deduplicated_results.sort(key=lambda x: x[1], reverse=True)
    
    # Return top-k results
    top_results = deduplicated_results[:top_k]
    
    # Final validation: ensure all scores are in [0.0, 1.0] and finite
    for media_id, score in top_results:
        if not (0.0 <= score <= 1.0):
            raise ValueError(
                f"Score {score} for media_id {media_id} is outside valid range [0.0, 1.0]"
            )
        if not np.isfinite(score):
            raise ValueError(
                f"Score {score} for media_id {media_id} is not finite"
            )
    
    return top_results
