"""
Load the full Netflix dataset into the system.

This script:
1. Clears existing data
2. Loads all items from netflix_media.csv
3. Trains new vectorizer
4. Generates embeddings
5. Stores in PostgreSQL and Vector DB
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import logging
from database.postgres import PostgresDatabase
from database.file_vector_db import FileVectorDatabase
from ml_engine.ml_engine import MLEngine
import json
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clear_existing_data():
    """Clear existing data from databases."""
    logger.info("Clearing existing data...")
    
    # Clear PostgreSQL
    try:
        db = PostgresDatabase()
        db.execute("DELETE FROM media")
        db.close()
        logger.info("✓ PostgreSQL cleared")
    except Exception as e:
        logger.warning(f"Could not clear PostgreSQL: {e}")
    
    # Clear Vector DB files
    try:
        embeddings_dir = 'embeddings'
        for file in ['vectors.npy', 'ids.json', 'metadata.json']:
            filepath = os.path.join(embeddings_dir, file)
            if os.path.exists(filepath):
                os.remove(filepath)
        logger.info("✓ Vector DB cleared")
    except Exception as e:
        logger.warning(f"Could not clear Vector DB: {e}")


def load_and_clean_data(csv_path='data/netflix_media.csv'):
    """Load and clean the Netflix dataset."""
    logger.info(f"Loading data from {csv_path}...")
    
    df = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df)} items")
    
    # Clean data
    df = df[df['title'].notna()]
    df = df[df['description'].notna()]
    df = df[df['title'].str.strip() != '']
    df = df[df['description'].str.strip() != '']
    
    logger.info(f"After cleaning: {len(df)} items")
    
    return df


def train_vectorizer(df, ml_engine):
    """Train TF-IDF vectorizer on all descriptions."""
    logger.info("Training vectorizer...")
    
    descriptions = df['description'].tolist()
    
    # Train with optimized parameters
    vectorizer = ml_engine.train_vectorizer(
        descriptions=descriptions,
        max_features=10000,  # Increased for larger dataset
        ngram_range=(1, 3),
        min_df=2,
        max_df=0.8,
        save=True
    )
    
    logger.info(f"✓ Vectorizer trained")
    logger.info(f"  Version: {ml_engine.get_model_version()}")
    logger.info(f"  Vocabulary size: {len(vectorizer.vocabulary_)}")
    
    return vectorizer


def generate_embeddings(df, ml_engine):
    """Generate embeddings for all items."""
    logger.info("Generating embeddings...")
    
    descriptions = df['description'].tolist()
    media_ids = df['id'].tolist()
    
    embeddings = ml_engine.compute_embeddings(descriptions, media_ids)
    
    logger.info(f"✓ Generated {embeddings.shape[0]} embeddings")
    logger.info(f"  Dimension: {embeddings.shape[1]}")
    
    return embeddings


def store_embeddings(embeddings, media_ids, ml_engine):
    """Store embeddings in Vector DB."""
    logger.info("Storing embeddings in Vector DB...")
    
    embeddings_dir = 'embeddings'
    os.makedirs(embeddings_dir, exist_ok=True)
    
    # Save vectors
    vectors_path = os.path.join(embeddings_dir, 'vectors.npy')
    np.save(vectors_path, embeddings)
    
    # Save IDs
    ids_path = os.path.join(embeddings_dir, 'ids.json')
    with open(ids_path, 'w') as f:
        json.dump(media_ids, f)
    
    # Save metadata
    metadata = {
        'model_version': ml_engine.get_model_version(),
        'vector_size': embeddings.shape[1],
        'num_vectors': embeddings.shape[0]
    }
    metadata_path = os.path.join(embeddings_dir, 'metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"✓ Embeddings stored")


def store_metadata(df):
    """Store metadata in PostgreSQL."""
    logger.info("Storing metadata in PostgreSQL...")
    
    db = PostgresDatabase()
    
    media_items = []
    for _, row in df.iterrows():
        # Build metadata dictionary
        metadata = {}
        optional_fields = ['author', 'genre', 'year', 'rating', 'director', 
                         'seasons', 'is_latest', 'thumbnail_url']
        
        for field in optional_fields:
            if field in row and pd.notna(row[field]):
                metadata[field] = row[field]
        
        # Create media item
        media_item = {
            'id': str(row['id']),
            'title': str(row['title'])[:500],
            'description': str(row['description'])[:5000],
            'media_type': row.get('media_type', 'book'),
            'metadata': metadata
        }
        
        media_items.append(media_item)
    
    # Batch insert
    inserted_ids = db.batch_insert_media(media_items)
    db.close()
    
    logger.info(f"✓ Stored {len(inserted_ids)} items in PostgreSQL")


def update_env_file(vector_size):
    """Update .env file with new vector size."""
    env_path = '.env'
    
    if not os.path.exists(env_path):
        logger.warning(".env file not found, skipping update")
        return
    
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    updated = False
    for i, line in enumerate(lines):
        if line.startswith('VECTOR_SIZE='):
            lines[i] = f'VECTOR_SIZE={vector_size}\n'
            updated = True
            break
    
    if updated:
        with open(env_path, 'w') as f:
            f.writelines(lines)
        logger.info(f"✓ Updated .env: VECTOR_SIZE={vector_size}")


def main():
    """Main execution function."""
    logger.info("=" * 60)
    logger.info("Loading Full Netflix Dataset")
    logger.info("=" * 60)
    
    try:
        # Step 1: Clear existing data
        clear_existing_data()
        
        # Step 2: Load and clean data
        df = load_and_clean_data()
        
        # Step 3: Initialize ML Engine
        ml_engine = MLEngine('models', 'embeddings')
        
        # Step 4: Train vectorizer
        vectorizer = train_vectorizer(df, ml_engine)
        
        # Step 5: Generate embeddings
        embeddings = generate_embeddings(df, ml_engine)
        
        # Step 6: Store embeddings
        media_ids = df['id'].tolist()
        store_embeddings(embeddings, media_ids, ml_engine)
        
        # Step 7: Store metadata
        store_metadata(df)
        
        # Step 8: Update .env file
        update_env_file(embeddings.shape[1])
        
        # Summary
        logger.info("")
        logger.info("=" * 60)
        logger.info("✓ LOADING COMPLETE!")
        logger.info("=" * 60)
        logger.info(f"Total items loaded: {len(df)}")
        logger.info(f"Vector dimension: {embeddings.shape[1]}")
        logger.info(f"Model version: {ml_engine.get_model_version()}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Restart the backend server")
        logger.info("2. Test search with more queries")
        logger.info("3. Enjoy better search results!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error during loading: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
