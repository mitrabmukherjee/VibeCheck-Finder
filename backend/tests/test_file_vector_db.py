"""
Unit tests for FileVectorDatabase class.

Tests file-based vector database operations including insert, search, and backward compatibility.
"""

import pytest
import numpy as np
import tempfile
import shutil
from pathlib import Path
from database.file_vector_db import FileVectorDatabase


@pytest.fixture
def temp_storage():
    """Create a temporary storage directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_file_vector_db_initialization(temp_storage):
    """Test that FileVectorDatabase initializes correctly."""
    db = FileVectorDatabase(
        storage_path=temp_storage,
        vector_size=384
    )
    
    assert db.storage_path == Path(temp_storage)
    assert db.vector_size == 384
    assert len(db.ids) == 0
    assert len(db.vectors) == 0
    
    db.close()


def test_insert_and_search_384_dim(temp_storage):
    """Test inserting and searching 384-dimensional vectors (Sentence-BERT)."""
    db = FileVectorDatabase(
        storage_path=temp_storage,
        vector_size=384
    )
    
    # Insert a vector
    media_id = "test-media-1"
    vector = np.random.rand(384).tolist()
    metadata = {"model_version": "all-MiniLM-L6-v2", "vectorizer_type": "sbert"}
    
    db.insert(media_id=media_id, vector=vector, metadata=metadata)
    
    # Search for it
    results = db.search(query_vector=vector, top_k=1)
    
    assert len(results) == 1
    assert results[0]["id"] == media_id
    assert results[0]["score"] > 0.99  # Should be very close to 1.0
    
    db.close()


def test_insert_and_search_5000_dim(temp_storage):
    """Test inserting and searching 5000-dimensional vectors (TF-IDF)."""
    db = FileVectorDatabase(
        storage_path=temp_storage,
        vector_size=5000
    )
    
    # Insert a vector
    media_id = "test-media-2"
    vector = np.random.rand(5000).tolist()
    metadata = {"vectorizer_type": "tfidf"}
    
    db.insert(media_id=media_id, vector=vector, metadata=metadata)
    
    # Search for it
    results = db.search(query_vector=vector, top_k=1)
    
    assert len(results) == 1
    assert results[0]["id"] == media_id
    assert results[0]["score"] > 0.99
    
    db.close()


def test_vector_size_mismatch_insert(temp_storage):
    """Test that inserting a vector with wrong size raises ValueError."""
    db = FileVectorDatabase(
        storage_path=temp_storage,
        vector_size=384
    )
    
    # Try to insert a 5000-dim vector into a 384-dim database
    media_id = "test-media-3"
    vector = np.random.rand(5000).tolist()
    
    with pytest.raises(ValueError, match="Vector size mismatch"):
        db.insert(media_id=media_id, vector=vector)
    
    db.close()


def test_vector_size_mismatch_search(temp_storage):
    """Test that searching with wrong vector size raises ValueError."""
    db = FileVectorDatabase(
        storage_path=temp_storage,
        vector_size=384
    )
    
    # Insert a 384-dim vector
    media_id = "test-media-4"
    vector = np.random.rand(384).tolist()
    db.insert(media_id=media_id, vector=vector)
    
    # Try to search with a 5000-dim vector
    query_vector = np.random.rand(5000).tolist()
    
    with pytest.raises(ValueError, match="Query vector size mismatch"):
        db.search(query_vector=query_vector, top_k=1)
    
    db.close()


def test_backward_compatibility_with_existing_data(temp_storage):
    """Test that database adapts to existing vector size for backward compatibility."""
    # First, create a database with 5000-dim vectors (TF-IDF)
    db1 = FileVectorDatabase(
        storage_path=temp_storage,
        vector_size=5000
    )
    
    # Insert some 5000-dim vectors
    for i in range(3):
        vector = np.random.rand(5000).tolist()
        db1.insert(media_id=f"media-{i}", vector=vector)
    
    db1.close()
    
    # Now, try to open the same database with vector_size=384 (Sentence-BERT)
    # It should detect the existing 5000-dim vectors and adapt
    db2 = FileVectorDatabase(
        storage_path=temp_storage,
        vector_size=384  # This should be overridden by existing data
    )
    
    # The database should have adapted to the existing vector size
    assert db2.vector_size == 5000, "Database should adapt to existing vector size"
    assert len(db2.ids) == 3
    
    # Should be able to insert more 5000-dim vectors
    vector = np.random.rand(5000).tolist()
    db2.insert(media_id="media-3", vector=vector)
    
    # Should be able to search with 5000-dim vectors
    results = db2.search(query_vector=vector, top_k=1)
    assert len(results) == 1
    
    db2.close()


def test_upsert_vector(temp_storage):
    """Test that inserting with same ID updates the vector."""
    db = FileVectorDatabase(
        storage_path=temp_storage,
        vector_size=384
    )
    
    media_id = "test-media-5"
    vector1 = np.random.rand(384).tolist()
    vector2 = np.random.rand(384).tolist()
    
    # Insert first vector
    db.insert(media_id=media_id, vector=vector1, metadata={"version": "v1"})
    
    # Insert second vector with same ID (upsert)
    db.insert(media_id=media_id, vector=vector2, metadata={"version": "v2"})
    
    # Should only have one entry
    assert db.count() == 1
    
    # Search should return the updated vector
    results = db.search(query_vector=vector2, top_k=1)
    assert len(results) == 1
    assert results[0]["id"] == media_id
    
    db.close()


def test_search_returns_sorted_results(temp_storage):
    """Test that search results are sorted by score descending."""
    db = FileVectorDatabase(
        storage_path=temp_storage,
        vector_size=384
    )
    
    # Insert multiple vectors
    base_vector = np.random.rand(384)
    
    for i in range(5):
        # Create similar vectors by adding varying amounts of noise
        vector = (base_vector + np.random.rand(384) * (i * 0.1)).tolist()
        db.insert(media_id=f"media-{i}", vector=vector)
    
    # Search
    query_vector = base_vector.tolist()
    results = db.search(query_vector=query_vector, top_k=5)
    
    assert len(results) == 5
    
    # Verify results are sorted by score descending
    for i in range(len(results) - 1):
        assert results[i]["score"] >= results[i + 1]["score"]
    
    db.close()


def test_delete_vector(temp_storage):
    """Test deleting a vector from the database."""
    db = FileVectorDatabase(
        storage_path=temp_storage,
        vector_size=384
    )
    
    # Insert vectors
    for i in range(3):
        vector = np.random.rand(384).tolist()
        db.insert(media_id=f"media-{i}", vector=vector)
    
    assert db.count() == 3
    
    # Delete one vector
    result = db.delete(media_id="media-1")
    assert result is True
    assert db.count() == 2
    
    # Try to delete non-existent vector
    result = db.delete(media_id="media-999")
    assert result is False
    assert db.count() == 2
    
    db.close()


def test_clear_all_vectors(temp_storage):
    """Test clearing all vectors from the database."""
    db = FileVectorDatabase(
        storage_path=temp_storage,
        vector_size=384
    )
    
    # Insert vectors
    for i in range(5):
        vector = np.random.rand(384).tolist()
        db.insert(media_id=f"media-{i}", vector=vector)
    
    assert db.count() == 5
    
    # Clear all
    db.clear()
    assert db.count() == 0
    
    db.close()


def test_search_empty_database(temp_storage):
    """Test searching in an empty database."""
    db = FileVectorDatabase(
        storage_path=temp_storage,
        vector_size=384
    )
    
    query_vector = np.random.rand(384).tolist()
    results = db.search(query_vector=query_vector, top_k=5)
    
    assert len(results) == 0
    
    db.close()


def test_persistence_across_sessions(temp_storage):
    """Test that data persists across database sessions."""
    # Session 1: Insert data
    db1 = FileVectorDatabase(
        storage_path=temp_storage,
        vector_size=384
    )
    
    vectors = []
    for i in range(3):
        vector = np.random.rand(384).tolist()
        vectors.append(vector)
        db1.insert(media_id=f"media-{i}", vector=vector, metadata={"index": i})
    
    db1.close()
    
    # Session 2: Load and verify data
    db2 = FileVectorDatabase(
        storage_path=temp_storage,
        vector_size=384
    )
    
    assert db2.count() == 3
    
    # Search for one of the vectors
    results = db2.search(query_vector=vectors[0], top_k=1)
    assert len(results) == 1
    assert results[0]["id"] == "media-0"
    
    db2.close()


def test_metadata_storage_with_vectorizer_info(temp_storage):
    """Test storing and retrieving metadata with vectorizer_type, model_version, and embedding_date."""
    db = FileVectorDatabase(
        storage_path=temp_storage,
        vector_size=384
    )
    
    # Insert vector with complete metadata
    media_id = "test-media-sbert"
    vector = np.random.rand(384).tolist()
    metadata = {
        "vectorizer_type": "sbert",
        "model_version": "all-MiniLM-L6-v2",
        "embedding_date": "2024-01-15T10:30:00Z",
        "media_id": media_id
    }
    
    db.insert(media_id=media_id, vector=vector, metadata=metadata)
    
    # Retrieve metadata
    retrieved_metadata = db.get_metadata(media_id)
    
    assert retrieved_metadata is not None
    assert retrieved_metadata["vectorizer_type"] == "sbert"
    assert retrieved_metadata["model_version"] == "all-MiniLM-L6-v2"
    assert retrieved_metadata["embedding_date"] == "2024-01-15T10:30:00Z"
    assert retrieved_metadata["media_id"] == media_id
    
    db.close()


def test_get_metadata_nonexistent_id(temp_storage):
    """Test that get_metadata returns None for non-existent media_id."""
    db = FileVectorDatabase(
        storage_path=temp_storage,
        vector_size=384
    )
    
    # Try to get metadata for non-existent ID
    metadata = db.get_metadata("nonexistent-id")
    
    assert metadata is None
    
    db.close()


def test_metadata_persistence_across_sessions(temp_storage):
    """Test that metadata persists across database sessions."""
    # Session 1: Insert data with metadata
    db1 = FileVectorDatabase(
        storage_path=temp_storage,
        vector_size=384
    )
    
    media_id = "test-media-persist"
    vector = np.random.rand(384).tolist()
    metadata = {
        "vectorizer_type": "sbert",
        "model_version": "all-MiniLM-L6-v2",
        "embedding_date": "2024-01-15T10:30:00Z"
    }
    
    db1.insert(media_id=media_id, vector=vector, metadata=metadata)
    db1.close()
    
    # Session 2: Load and verify metadata
    db2 = FileVectorDatabase(
        storage_path=temp_storage,
        vector_size=384
    )
    
    retrieved_metadata = db2.get_metadata(media_id)
    
    assert retrieved_metadata is not None
    assert retrieved_metadata["vectorizer_type"] == "sbert"
    assert retrieved_metadata["model_version"] == "all-MiniLM-L6-v2"
    assert retrieved_metadata["embedding_date"] == "2024-01-15T10:30:00Z"
    
    db2.close()

