"""
Retrain the TF-IDF vectorizer with optimized parameters for Netflix dataset.

This script retrains the vectorizer with parameters tuned for better similarity matching:
- Increased max_features for richer vocabulary
- Higher min_df to filter out rare words
- Lower max_df to filter out overly common words
- Trigrams for better phrase matching
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from ml_engine.ml_engine import MLEngine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def retrain_vectorizer():
    """Retrain vectorizer with optimized parameters."""
    
    # Load the Netflix dataset
    data_path = 'data/netflix_media.csv'
    logger.info(f"Loading dataset from {data_path}")
    df = pd.read_csv(data_path)
    
    logger.info(f"Loaded {len(df)} items")
    
    # Extract descriptions
    descriptions = df['description'].tolist()
    
    # Initialize ML Engine
    vectorizer_path = 'models'
    embeddings_path = 'embeddings'
    ml_engine = MLEngine(vectorizer_path, embeddings_path)
    
    # Train with optimized parameters
    logger.info("Training vectorizer with optimized parameters:")
    logger.info("  - max_features: 10000 (increased from 5000)")
    logger.info("  - ngram_range: (1, 3) (added trigrams)")
    logger.info("  - min_df: 2 (filter rare words)")
    logger.info("  - max_df: 0.8 (filter common words)")
    
    vectorizer = ml_engine.train_vectorizer(
        descriptions=descriptions,
        max_features=10000,  # Increased vocabulary size
        ngram_range=(1, 3),  # Unigrams, bigrams, and trigrams
        min_df=2,  # Word must appear in at least 2 documents
        max_df=0.8,  # Word must appear in at most 80% of documents
        save=True
    )
    
    logger.info(f"Vectorizer trained successfully!")
    logger.info(f"Version: {ml_engine.get_model_version()}")
    logger.info(f"Vocabulary size: {len(vectorizer.vocabulary_)}")
    
    # Now regenerate embeddings with the new vectorizer
    logger.info("\nRegenerating embeddings with new vectorizer...")
    
    # Extract IDs and descriptions
    media_ids = df['id'].tolist()
    
    # Generate embeddings
    embeddings = ml_engine.compute_embeddings(descriptions, media_ids)
    
    logger.info(f"Generated {embeddings.shape[0]} embeddings with dimension {embeddings.shape[1]}")
    
    # Save embeddings to file
    import numpy as np
    import json
    
    embeddings_dir = embeddings_path
    os.makedirs(embeddings_dir, exist_ok=True)
    
    # Save vectors
    vectors_path = os.path.join(embeddings_dir, 'vectors.npy')
    np.save(vectors_path, embeddings)
    logger.info(f"Saved vectors to {vectors_path}")
    
    # Save IDs
    ids_path = os.path.join(embeddings_dir, 'ids.json')
    with open(ids_path, 'w') as f:
        json.dump(media_ids, f)
    logger.info(f"Saved IDs to {ids_path}")
    
    # Save metadata
    metadata = {
        'model_version': ml_engine.get_model_version(),
        'vector_size': embeddings.shape[1],
        'num_vectors': embeddings.shape[0]
    }
    metadata_path = os.path.join(embeddings_dir, 'metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Saved metadata to {metadata_path}")
    
    logger.info("\n✓ Vectorizer retraining complete!")
    logger.info("✓ Embeddings regenerated and saved!")
    logger.info("\nRestart the backend server to use the new vectorizer.")


if __name__ == '__main__':
    retrain_vectorizer()
