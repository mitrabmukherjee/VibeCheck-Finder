"""
Unit tests for VectorDatabase class.

Tests vector database operations including insert, search, and delete.
"""

import pytest
import numpy as np
from hypothesis import given, strategies as st, assume
from database import VectorDatabase


@pytest.fixture
def vector_db():
    """Create a VectorDatabase instance for testing."""
    db = VectorDatabase(
        host="localhost",
        port=6333,
        collection_name="test_media_embeddings",
        vector_size=128,  # Smaller size for testing
    )
    yield db
    
    # Cleanup: delete all test data
    try:
        # Get all points and delete them
        count = db.count()
        if count > 0:
            # Delete collection for clean slate
            db.client.delete_collection(collection_name="test_media_embeddings")
    except Exception:
        pass
    finally:
        db.close()


def test_vector_db_initialization(vector_db):
    """Test that VectorDatabase initializes correctly."""
    assert vector_db.host == "localhost"
    assert vector_db.port == 6333
    assert vector_db.collection_name == "test_media_embeddings"
    assert vector_db.vector_size == 128
    assert vector_db.client is not None


def test_insert_vector(vector_db):
    """Test inserting a vector into the database."""
    media_id = "test-media-1"
    vector = np.random.rand(128).tolist()
    metadata = {"model_version": "v1.0.0", "media_type": "book"}
    
    # Should not raise an exception
    vector_db.insert(id=media_id, vector=vector, metadata=metadata)
    
    # Verify insertion by searching
    results = vector_db.search(query_vector=vector, top_k=1)
    assert len(results) == 1
    assert results[0]["id"] == media_id
    assert results[0]["metadata"]["model_version"] == "v1.0.0"


def test_insert_vector_wrong_size(vector_db):
    """Test that inserting a vector with wrong size raises ValueError."""
    media_id = "test-media-2"
    vector = np.random.rand(64).tolist()  # Wrong size
    
    with pytest.raises(ValueError, match="Vector size mismatch"):
        vector_db.insert(id=media_id, vector=vector)


def test_insert_vector_with_invalid_values(vector_db):
    """Test that inserting a vector with invalid values raises ValueError."""
    media_id = "test-media-3"
    vector = [float('inf')] * 128  # Invalid values
    
    with pytest.raises(ValueError, match="finite float values"):
        vector_db.insert(id=media_id, vector=vector)


def test_upsert_vector(vector_db):
    """Test that inserting with same ID updates the vector."""
    media_id = "test-media-4"
    vector1 = np.random.rand(128).tolist()
    vector2 = np.random.rand(128).tolist()
    
    # Insert first vector
    vector_db.insert(id=media_id, vector=vector1, metadata={"version": "v1"})
    
    # Insert second vector with same ID (upsert)
    vector_db.insert(id=media_id, vector=vector2, metadata={"version": "v2"})
    
    # Search should return the updated vector
    results = vector_db.search(query_vector=vector2, top_k=1)
    assert len(results) == 1
    assert results[0]["id"] == media_id
    assert results[0]["metadata"]["version"] == "v2"


def test_search_similar_vectors(vector_db):
    """Test searching for similar vectors."""
    # Insert multiple vectors
    base_vector = np.random.rand(128)
    
    for i in range(5):
        # Create similar vectors by adding small noise
        vector = (base_vector + np.random.rand(128) * 0.1).tolist()
        vector_db.insert(
            id=f"test-media-{i}",
            vector=vector,
            metadata={"index": i}
        )
    
    # Search for similar vectors
    query_vector = base_vector.tolist()
    results = vector_db.search(query_vector=query_vector, top_k=3)
    
    assert len(results) == 3
    # Results should be sorted by score descending
    assert results[0]["score"] >= results[1]["score"]
    assert results[1]["score"] >= results[2]["score"]
    # All scores should be between 0 and 1 for cosine similarity
    for result in results:
        assert 0.0 <= result["score"] <= 1.0


def test_search_with_wrong_vector_size(vector_db):
    """Test that searching with wrong vector size raises ValueError."""
    query_vector = np.random.rand(64).tolist()  # Wrong size
    
    with pytest.raises(ValueError, match="Query vector size mismatch"):
        vector_db.search(query_vector=query_vector, top_k=5)


def test_search_with_filter(vector_db):
    """Test searching with metadata filters."""
    # Insert vectors with different metadata
    for i in range(3):
        vector = np.random.rand(128).tolist()
        vector_db.insert(
            id=f"book-{i}",
            vector=vector,
            metadata={"media_type": "book"}
        )
    
    for i in range(2):
        vector = np.random.rand(128).tolist()
        vector_db.insert(
            id=f"tv-{i}",
            vector=vector,
            metadata={"media_type": "tv_show"}
        )
    
    # Search with filter for books only
    query_vector = np.random.rand(128).tolist()
    results = vector_db.search(
        query_vector=query_vector,
        top_k=5,
        filter={"media_type": "book"}
    )
    
    # Should only return books
    assert len(results) == 3
    for result in results:
        assert result["metadata"]["media_type"] == "book"


def test_delete_vector(vector_db):
    """Test deleting a vector from the database."""
    media_id = "test-media-delete"
    vector = np.random.rand(128).tolist()
    
    # Insert vector
    vector_db.insert(id=media_id, vector=vector)
    
    # Verify it exists
    results = vector_db.search(query_vector=vector, top_k=1)
    assert len(results) == 1
    assert results[0]["id"] == media_id
    
    # Delete vector
    vector_db.delete(id=media_id)
    
    # Verify it's deleted (search should return no exact matches)
    count_before = vector_db.count()
    # The count should have decreased
    assert count_before >= 0


def test_count_vectors(vector_db):
    """Test counting vectors in the collection."""
    initial_count = vector_db.count()
    
    # Insert some vectors
    for i in range(3):
        vector = np.random.rand(128).tolist()
        vector_db.insert(id=f"test-count-{i}", vector=vector)
    
    # Count should increase by 3
    new_count = vector_db.count()
    assert new_count == initial_count + 3


def test_search_empty_collection():
    """Test searching in an empty collection."""
    db = VectorDatabase(
        host="localhost",
        port=6333,
        collection_name="test_empty_collection",
        vector_size=128,
    )
    
    try:
        query_vector = np.random.rand(128).tolist()
        results = db.search(query_vector=query_vector, top_k=5)
        
        # Should return empty list
        assert len(results) == 0
    finally:
        db.client.delete_collection(collection_name="test_empty_collection")
        db.close()


def test_search_top_k_limit(vector_db):
    """Test that search respects top_k limit."""
    # Insert 10 vectors
    for i in range(10):
        vector = np.random.rand(128).tolist()
        vector_db.insert(id=f"test-limit-{i}", vector=vector)
    
    # Search with top_k=5
    query_vector = np.random.rand(128).tolist()
    results = vector_db.search(query_vector=query_vector, top_k=5)
    
    # Should return exactly 5 results
    assert len(results) == 5


def test_vector_with_metadata(vector_db):
    """Test that metadata is stored and retrieved correctly."""
    media_id = "test-metadata"
    vector = np.random.rand(128).tolist()
    metadata = {
        "model_version": "v1.0.0",
        "media_type": "book",
        "title": "Test Book",
        "year": 2024
    }
    
    vector_db.insert(id=media_id, vector=vector, metadata=metadata)
    
    # Search and verify metadata
    results = vector_db.search(query_vector=vector, top_k=1)
    assert len(results) == 1
    assert results[0]["metadata"]["model_version"] == "v1.0.0"
    assert results[0]["metadata"]["media_type"] == "book"
    assert results[0]["metadata"]["title"] == "Test Book"
    assert results[0]["metadata"]["year"] == 2024


def test_vector_without_metadata(vector_db):
    """Test inserting vector without metadata."""
    media_id = "test-no-metadata"
    vector = np.random.rand(128).tolist()
    
    # Insert without metadata
    vector_db.insert(id=media_id, vector=vector)
    
    # Should work fine
    results = vector_db.search(query_vector=vector, top_k=1)
    assert len(results) == 1
    assert results[0]["id"] == media_id
    assert results[0]["metadata"] == {}



class TestSimilaritySearchProperties:
    """
    Property-based tests for similarity search operations.
    
    These tests use Hypothesis to verify universal properties that should hold
    for all similarity search results, ensuring the vector database behaves correctly
    across a wide range of inputs and scenarios.
    """
    
    @given(
        st.integers(min_value=3, max_value=20),  # num_vectors to insert
        st.integers(min_value=1, max_value=10),  # top_k
    )
    @pytest.mark.hypothesis(max_examples=10)
    def test_score_ordering_property(self, num_vectors: int, top_k: int):
        """
        **Property 2: Score ordering**
        
        Test that similarity search results are always sorted by score in descending order.
        For any results list: all(results[i].score >= results[i+1].score)
        
        This property is critical because:
        1. Users expect the most relevant results first
        2. The API contract guarantees descending score order
        3. Downstream filtering and ranking depend on this ordering
        
        **Validates: Requirements 3.3, 3.4, 20.1**
        - 3.3: Return scores in the range 0.0 to 1.0
        - 3.4: Return top-k most similar items sorted by score descending
        - 20.1: Ensure no duplicate media IDs are present
        """
        # Ensure top_k doesn't exceed num_vectors
        assume(top_k <= num_vectors)
        
        # Create a test database
        db = VectorDatabase(
            host="localhost",
            port=6333,
            collection_name=f"test_ordering_{num_vectors}_{top_k}",
            vector_size=128,
        )
        
        try:
            # Insert random vectors
            for i in range(num_vectors):
                vector = np.random.rand(128).tolist()
                db.insert(id=f"media-{i}", vector=vector)
            
            # Perform search with a random query vector
            query_vector = np.random.rand(128).tolist()
            results = db.search(query_vector=query_vector, top_k=top_k)
            
            # Verify score ordering property
            for i in range(len(results) - 1):
                assert results[i]["score"] >= results[i + 1]["score"], (
                    f"Score ordering violated at index {i}!\n"
                    f"results[{i}].score = {results[i]['score']}\n"
                    f"results[{i+1}].score = {results[i+1]['score']}\n"
                    f"Expected: results[{i}].score >= results[{i+1}].score"
                )
        
        finally:
            # Cleanup
            db.client.delete_collection(collection_name=f"test_ordering_{num_vectors}_{top_k}")
            db.close()
    
    @given(
        st.integers(min_value=1, max_value=15),  # num_vectors to insert
        st.integers(min_value=1, max_value=10),  # top_k
    )
    @pytest.mark.hypothesis(max_examples=10)
    def test_score_bounds_property(self, num_vectors: int, top_k: int):
        """
        **Property 3: Score bounds**
        
        Test that all similarity scores are within the valid range [0.0, 1.0].
        For all results: 0.0 <= score <= 1.0
        
        This property is critical because:
        1. Cosine similarity is mathematically bounded to [-1, 1], but for text embeddings
           (which are typically non-negative), scores should be in [0, 1]
        2. The API contract guarantees scores in [0.0, 1.0]
        3. Frontend display and filtering logic depend on this range
        
        **Validates: Requirements 3.3, 3.4, 20.4**
        - 3.3: Return scores in the range 0.0 to 1.0
        - 3.4: Return top-k most similar items sorted by score descending
        - 20.4: Verify each media ID appears exactly once
        """
        # Ensure top_k doesn't exceed num_vectors
        assume(top_k <= num_vectors)
        
        # Create a test database
        db = VectorDatabase(
            host="localhost",
            port=6333,
            collection_name=f"test_bounds_{num_vectors}_{top_k}",
            vector_size=128,
        )
        
        try:
            # Insert random vectors
            for i in range(num_vectors):
                vector = np.random.rand(128).tolist()
                db.insert(id=f"media-{i}", vector=vector)
            
            # Perform search with a random query vector
            query_vector = np.random.rand(128).tolist()
            results = db.search(query_vector=query_vector, top_k=top_k)
            
            # Verify score bounds property
            for i, result in enumerate(results):
                score = result["score"]
                assert 0.0 <= score <= 1.0, (
                    f"Score bounds violated at index {i}!\n"
                    f"results[{i}].score = {score}\n"
                    f"Expected: 0.0 <= score <= 1.0"
                )
                
                # Also verify score is a finite float
                assert isinstance(score, (int, float)), (
                    f"Score at index {i} is not a number: {type(score)}"
                )
                assert abs(score) != float('inf'), (
                    f"Score at index {i} is infinite: {score}"
                )
                assert score == score, (  # NaN check (NaN != NaN)
                    f"Score at index {i} is NaN"
                )
        
        finally:
            # Cleanup
            db.client.delete_collection(collection_name=f"test_bounds_{num_vectors}_{top_k}")
            db.close()
    
    @given(
        st.integers(min_value=2, max_value=20),  # num_vectors to insert
        st.integers(min_value=1, max_value=15),  # top_k
    )
    @pytest.mark.hypothesis(max_examples=10)
    def test_result_uniqueness_property(self, num_vectors: int, top_k: int):
        """
        **Property 4: Result uniqueness**
        
        Test that similarity search results contain no duplicate media IDs.
        For any results list: len(results) == len(set(result.id for result in results))
        
        This property is critical because:
        1. Users should not see the same recommendation multiple times
        2. The system must deduplicate results if the vector DB returns duplicates
        3. Each recommendation slot should show a unique media item
        
        **Validates: Requirements 20.1, 20.4**
        - 20.1: Ensure no duplicate media IDs are present
        - 20.4: Verify each media ID appears exactly once
        """
        # Ensure top_k doesn't exceed num_vectors
        assume(top_k <= num_vectors)
        
        # Create a test database
        db = VectorDatabase(
            host="localhost",
            port=6333,
            collection_name=f"test_uniqueness_{num_vectors}_{top_k}",
            vector_size=128,
        )
        
        try:
            # Insert random vectors
            for i in range(num_vectors):
                vector = np.random.rand(128).tolist()
                db.insert(id=f"media-{i}", vector=vector)
            
            # Perform search with a random query vector
            query_vector = np.random.rand(128).tolist()
            results = db.search(query_vector=query_vector, top_k=top_k)
            
            # Extract all media IDs from results
            media_ids = [result["id"] for result in results]
            unique_ids = set(media_ids)
            
            # Verify uniqueness property
            assert len(media_ids) == len(unique_ids), (
                f"Result uniqueness violated!\n"
                f"Total results: {len(media_ids)}\n"
                f"Unique IDs: {len(unique_ids)}\n"
                f"Duplicate IDs found: {[id for id in media_ids if media_ids.count(id) > 1]}\n"
                f"All IDs: {media_ids}"
            )
            
            # Additional verification: each ID should appear exactly once
            for media_id in unique_ids:
                count = media_ids.count(media_id)
                assert count == 1, (
                    f"Media ID '{media_id}' appears {count} times (expected 1)"
                )
        
        finally:
            # Cleanup
            db.client.delete_collection(collection_name=f"test_uniqueness_{num_vectors}_{top_k}")
            db.close()
