"""
Hybrid Search Engine combining TF-IDF and Sentence-BERT.

This module implements a hybrid search approach that combines:
1. TF-IDF for exact keyword/title matching
2. Sentence-BERT for semantic understanding

The hybrid approach ensures both exact matches (like movie titles) and
semantic matches (like plot descriptions) are captured effectively.
"""

import numpy as np
from typing import List, Dict, Any, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from .preprocessing import preprocess_text


class HybridSearchEngine:
    """
    Hybrid search combining TF-IDF and Sentence-BERT.
    
    This engine uses:
    - TF-IDF: For exact keyword matching (good for titles, names)
    - Sentence-BERT: For semantic understanding (good for descriptions)
    - Weighted combination: Balances both approaches
    """
    
    def __init__(
        self,
        sbert_vectorizer,
        tfidf_weight: float = 0.3,
        sbert_weight: float = 0.7
    ):
        """
        Initialize hybrid search engine.
        
        Args:
            sbert_vectorizer: Sentence-BERT vectorizer instance
            tfidf_weight: Weight for TF-IDF scores (0.0 to 1.0)
            sbert_weight: Weight for Sentence-BERT scores (0.0 to 1.0)
        """
        self.sbert_vectorizer = sbert_vectorizer
        self.tfidf_vectorizer = None
        self.tfidf_weight = tfidf_weight
        self.sbert_weight = sbert_weight
        
        # Cached corpus data
        self.corpus_texts = None
        self.corpus_ids = None
        self.sbert_embeddings = None
        self.tfidf_embeddings = None
    
    def fit_tfidf(self, texts: List[str]):
        """
        Fit TF-IDF vectorizer on corpus.
        
        Args:
            texts: List of text documents (titles + descriptions)
        """
        # Preprocess texts for TF-IDF
        preprocessed = [preprocess_text(text) for text in texts]
        
        # Create and fit TF-IDF vectorizer
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95
        )
        self.tfidf_vectorizer.fit(preprocessed)
    
    def index_corpus(
        self,
        texts: List[str],
        media_ids: List[str],
        batch_size: int = 32
    ):
        """
        Index corpus with both TF-IDF and Sentence-BERT.
        
        Args:
            texts: List of text documents (titles + descriptions)
            media_ids: List of media IDs
            batch_size: Batch size for Sentence-BERT encoding
        """
        self.corpus_texts = texts
        self.corpus_ids = media_ids
        
        # Fit and transform with TF-IDF
        self.fit_tfidf(texts)
        preprocessed = [preprocess_text(text) for text in texts]
        self.tfidf_embeddings = self.tfidf_vectorizer.transform(preprocessed).toarray()
        
        # Encode with Sentence-BERT
        self.sbert_embeddings = self.sbert_vectorizer.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True
        )
    
    def search(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining TF-IDF and Sentence-BERT.
        
        Args:
            query: Search query
            top_k: Number of results to return
        
        Returns:
            List of dicts with 'id' and 'score' keys
        """
        if self.tfidf_vectorizer is None or self.sbert_embeddings is None:
            raise RuntimeError("Corpus not indexed. Call index_corpus() first.")
        
        # TF-IDF search
        preprocessed_query = preprocess_text(query)
        tfidf_query_vec = self.tfidf_vectorizer.transform([preprocessed_query]).toarray()
        tfidf_scores = np.dot(self.tfidf_embeddings, tfidf_query_vec.T).flatten()
        
        # Normalize TF-IDF scores to 0-1 range
        if tfidf_scores.max() > 0:
            tfidf_scores = tfidf_scores / tfidf_scores.max()
        
        # Sentence-BERT search
        sbert_query_vec = self.sbert_vectorizer.encode(
            query,
            normalize_embeddings=True
        )
        sbert_scores = np.dot(self.sbert_embeddings, sbert_query_vec.T).flatten()
        
        # Combine scores with weights
        combined_scores = (
            self.tfidf_weight * tfidf_scores +
            self.sbert_weight * sbert_scores
        )
        
        # Get top-k results
        top_indices = np.argsort(combined_scores)[-top_k:][::-1]
        
        results = [
            {
                "id": self.corpus_ids[idx],
                "score": float(combined_scores[idx])
            }
            for idx in top_indices
        ]
        
        return results
