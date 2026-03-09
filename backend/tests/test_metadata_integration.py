"""
Integration test for metadata storage in the data pipeline.

This test verifies that vectorizer_type, model_version, and embedding_date
are properly stored when embeddings are generated through the data pipeline.
"""

import pytest
import tempfile
import shutil
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch
from database.file_vector_db import FileVectorDatabase
from ml_engine.ml_engine import MLEngine


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    temp_base = tempfile.mkdtemp()
    temp_embeddings = Path(temp_base) / "embeddings"
    temp_models = Path(temp_base) / "models"
    
    temp_embeddings.mkdir(parents=True, exist_ok=True)
    temp_models.mkdir(parents=True, exist_ok=True)
    
    yield {
        "base": temp_base,
        "embeddings": str(temp_embeddings),
        "models": str(temp_models)
    }
    
    # Cleanup
    shutil.rmtree(temp_base, ignore_errors=True)


def test_metadata_stored_with_tfidf_embeddings(temp_dirs):
    """Test that metadata (vectorizer_type, model_version, embedding_date) is stored with TF-IDF embeddings."""
    # Create sample descriptions
    descriptions = [
        'A thrilling action movie with explosions',
        'A romantic comedy about love and laughter',
        'A documentary about space exploration'
    ]
    media_ids = ['movie-1', 'movie-2', 'movie-3']
    
    # Initialize ML Engine with TF-IDF
    ml_engine = MLEngine(
        vectorizer_path=temp_dirs["models"],
        embeddings_path=temp_dirs["embeddings"],
        vectorizer_type="tfidf"
    )
    
    # Train vectorizer
    ml_engine.train_vectorizer(descriptions, save=True)
    
    # Generate embeddings
    embeddings = ml_engine.compute_embeddings(descriptions, media_ids)
    
    # Initialize FileVectorDatabase
    db = FileVectorDatabase(
        storage_path=temp_dirs["embeddings"],
        vector_size=embeddings.shape[1]
    )
    
    # Store embeddings with metadata (simulating what data_pipeline does)
    from datetime import datetime, timezone
    model_version = ml_engine.get_model_version()
    vectorizer_type = ml_engine.vectorizer_type
    embedding_date = datetime.now(timezone.utc).isoformat()
    
    for idx, media_id in enumerate(media_ids):
        vector = embeddings[idx].tolist()
        metadata = {
            'model_version': model_version,
            'vectorizer_type': vectorizer_type,
            'embedding_date': embedding_date,
            'media_id': media_id
        }
        db.insert(media_id, vector, metadata)
    
    # Verify metadata for each media item
    for media_id in media_ids:
        metadata = db.get_metadata(media_id)
        
        assert metadata is not None, f"Metadata not found for {media_id}"
        assert 'vectorizer_type' in metadata, "vectorizer_type missing from metadata"
        assert 'model_version' in metadata, "model_version missing from metadata"
        assert 'embedding_date' in metadata, "embedding_date missing from metadata"
        assert 'media_id' in metadata, "media_id missing from metadata"
        
        # Verify values
        assert metadata['vectorizer_type'] == 'tfidf', f"Expected vectorizer_type='tfidf', got '{metadata['vectorizer_type']}'"
        assert metadata['media_id'] == media_id, f"Expected media_id='{media_id}', got '{metadata['media_id']}'"
        assert metadata['model_version'] is not None, "model_version should not be None"
        assert metadata['embedding_date'] is not None, "embedding_date should not be None"
        
        # Verify embedding_date is in ISO 8601 format (contains 'T' and timezone info)
        assert 'T' in metadata['embedding_date'], "embedding_date should be in ISO 8601 format"
    
    db.close()


def test_metadata_stored_with_sbert_embeddings(temp_dirs):
    """Test that metadata is correctly stored when using Sentence-BERT vectorizer."""
    # Create sample descriptions
    descriptions = [
        'A thrilling action movie',
        'A romantic comedy'
    ]
    media_ids = ['movie-1', 'movie-2']
    
    # Initialize ML Engine with Sentence-BERT
    ml_engine = MLEngine(
        vectorizer_path=temp_dirs["models"],
        embeddings_path=temp_dirs["embeddings"],
        vectorizer_type="sbert",
        model_name="all-MiniLM-L6-v2"
    )
    
    # Generate embeddings (no training needed for Sentence-BERT)
    embeddings = ml_engine.compute_embeddings(descriptions, media_ids)
    
    # Initialize FileVectorDatabase
    db = FileVectorDatabase(
        storage_path=temp_dirs["embeddings"],
        vector_size=384  # Sentence-BERT uses 384 dimensions
    )
    
    # Store embeddings with metadata
    from datetime import datetime, timezone
    model_version = ml_engine.get_model_version()
    vectorizer_type = ml_engine.vectorizer_type
    embedding_date = datetime.now(timezone.utc).isoformat()
    
    for idx, media_id in enumerate(media_ids):
        vector = embeddings[idx].tolist()
        metadata = {
            'model_version': model_version,
            'vectorizer_type': vectorizer_type,
            'embedding_date': embedding_date,
            'media_id': media_id
        }
        db.insert(media_id, vector, metadata)
    
    # Verify metadata for each media item
    for media_id in media_ids:
        metadata = db.get_metadata(media_id)
        
        assert metadata is not None, f"Metadata not found for {media_id}"
        assert metadata['vectorizer_type'] == 'sbert', f"Expected vectorizer_type='sbert', got '{metadata['vectorizer_type']}'"
        assert metadata['model_version'] == 'all-MiniLM-L6-v2', f"Expected model_version='all-MiniLM-L6-v2', got '{metadata['model_version']}'"
        assert metadata['media_id'] == media_id
        assert 'embedding_date' in metadata
        assert 'T' in metadata['embedding_date']
    
    db.close()
