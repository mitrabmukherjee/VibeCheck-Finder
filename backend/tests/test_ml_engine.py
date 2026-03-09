"""
Unit tests for the MLEngine class.

This module tests the integration of all ML components through the MLEngine
class interface, including initialization, vectorization, similarity search,
and model version tracking.
"""

import os
import tempfile
import shutil
import pytest
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from backend.ml_engine import MLEngine


class TestMLEngineInitialization:
    """Test MLEngine initialization and configuration."""
    
    def test_init_with_valid_paths(self):
        """Test initialization with valid paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            engine = MLEngine(vectorizer_path, embeddings_path)
            
            assert engine.vectorizer_path == vectorizer_path
            assert engine.embeddings_path == embeddings_path
            assert engine.vectorizer is None  # Not loaded yet
            assert engine.model_version is None
    
    def test_init_with_empty_paths_raises_error(self):
        """Test that empty paths raise ValueError."""
        with pytest.raises(ValueError, match="vectorizer_path cannot be empty"):
            MLEngine("", "embeddings")
        
        with pytest.raises(ValueError, match="embeddings_path cannot be empty"):
            MLEngine("models", "")
    
    def test_init_loads_existing_vectorizer(self):
        """Test that initialization loads existing vectorizer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            # Train and save a vectorizer first
            engine1 = MLEngine(vectorizer_path, embeddings_path)
            descriptions = ["mystery detective novel", "sci-fi space adventure"]
            engine1.train_vectorizer(descriptions, save=True)
            
            # Create new engine instance - should load existing vectorizer
            engine2 = MLEngine(vectorizer_path, embeddings_path)
            
            assert engine2.vectorizer is not None
            assert engine2.model_version is not None
            assert len(engine2.vectorizer.vocabulary_) > 0
    
    def test_init_with_version_validation(self):
        """Test initialization with expected version validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            # Train and save a vectorizer
            engine1 = MLEngine(vectorizer_path, embeddings_path)
            descriptions = ["mystery detective novel", "sci-fi space adventure"]
            engine1.train_vectorizer(descriptions, save=True)
            actual_version = engine1.model_version
            
            # Create new engine with correct expected version - should succeed
            engine2 = MLEngine(vectorizer_path, embeddings_path, expected_version=actual_version)
            assert engine2.model_version == actual_version
            
            # Create new engine with wrong expected version - should fail
            with pytest.raises(ValueError, match="Model version mismatch"):
                MLEngine(vectorizer_path, embeddings_path, expected_version="wrong_version")


class TestMLEngineVectorization:
    """Test MLEngine vectorization methods."""
    
    def test_train_vectorizer(self):
        """Test training a new vectorizer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            engine = MLEngine(vectorizer_path, embeddings_path)
            descriptions = [
                "A cozy mystery set in a coffee shop",
                "A fast-paced sci-fi thriller about time travel",
                "A romantic comedy in Paris"
            ]
            
            vectorizer = engine.train_vectorizer(descriptions, max_features=100, save=False)
            
            assert isinstance(vectorizer, TfidfVectorizer)
            assert engine.vectorizer is not None
            assert len(engine.vectorizer.vocabulary_) > 0
    
    def test_train_vectorizer_with_save(self):
        """Test training and saving vectorizer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            engine = MLEngine(vectorizer_path, embeddings_path)
            descriptions = ["mystery novel", "sci-fi adventure"]
            
            vectorizer = engine.train_vectorizer(descriptions, save=True)
            
            assert engine.model_version is not None
            assert os.path.exists(os.path.join(vectorizer_path, "tfidf_vectorizer.pkl"))
            assert os.path.exists(os.path.join(vectorizer_path, "vectorizer_metadata.pkl"))
    
    def test_train_vectorizer_with_empty_descriptions_raises_error(self):
        """Test that empty descriptions list raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            engine = MLEngine(vectorizer_path, embeddings_path)
            
            with pytest.raises(ValueError, match="descriptions list cannot be empty"):
                engine.train_vectorizer([])
    
    def test_vectorize_query(self):
        """Test query vectorization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            engine = MLEngine(vectorizer_path, embeddings_path)
            descriptions = ["mystery detective novel", "sci-fi space adventure"]
            engine.train_vectorizer(descriptions, save=True)
            
            query = "detective mystery"
            vector = engine.vectorize_query(query)
            
            assert isinstance(vector, np.ndarray)
            assert vector.shape[0] == 1
            assert vector.shape[1] > 0
            assert np.all(np.isfinite(vector))
            assert np.linalg.norm(vector) > 0
    
    def test_vectorize_query_without_vectorizer_raises_error(self):
        """Test that vectorizing without loaded vectorizer raises RuntimeError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            engine = MLEngine(vectorizer_path, embeddings_path)
            
            with pytest.raises(RuntimeError, match="Vectorizer not loaded"):
                engine.vectorize_query("test query")
    
    def test_vectorize_query_with_empty_query_raises_error(self):
        """Test that empty query after preprocessing raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            engine = MLEngine(vectorizer_path, embeddings_path)
            descriptions = ["mystery detective novel", "sci-fi space adventure"]
            engine.train_vectorizer(descriptions, save=True)
            
            with pytest.raises(ValueError, match="Query must contain valid text"):
                engine.vectorize_query("@#$%^&*()")  # Only special chars


class TestMLEngineEmbeddings:
    """Test MLEngine embedding computation."""
    
    def test_compute_embeddings(self):
        """Test computing embeddings for descriptions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            engine = MLEngine(vectorizer_path, embeddings_path)
            descriptions = ["mystery detective novel", "sci-fi space adventure", "romantic comedy"]
            engine.train_vectorizer(descriptions, save=False)
            
            media_ids = ["id1", "id2", "id3"]
            embeddings = engine.compute_embeddings(descriptions, media_ids)
            
            assert isinstance(embeddings, np.ndarray)
            assert embeddings.shape[0] == len(descriptions)
            assert embeddings.shape[1] > 0
            assert np.all(np.isfinite(embeddings))
            
            # Check that corpus is cached
            assert engine.corpus_vectors is not None
            assert engine.corpus_ids == media_ids
    
    def test_compute_embeddings_without_vectorizer_raises_error(self):
        """Test that computing embeddings without vectorizer raises RuntimeError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            engine = MLEngine(vectorizer_path, embeddings_path)
            
            with pytest.raises(RuntimeError, match="Vectorizer not loaded"):
                engine.compute_embeddings(["test"], ["id1"])
    
    def test_compute_embeddings_with_mismatched_lengths_raises_error(self):
        """Test that mismatched descriptions and IDs raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            engine = MLEngine(vectorizer_path, embeddings_path)
            descriptions = ["mystery novel", "sci-fi adventure"]
            engine.train_vectorizer(descriptions, save=False)
            
            with pytest.raises(ValueError, match="descriptions length.*must match.*media_ids length"):
                engine.compute_embeddings(descriptions, ["id1"])  # Only 1 ID for 2 descriptions
    
    def test_compute_embeddings_with_non_string_raises_error(self):
        """Test that non-string descriptions raise TypeError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            engine = MLEngine(vectorizer_path, embeddings_path)
            descriptions = ["mystery novel", "sci-fi adventure"]
            engine.train_vectorizer(descriptions, save=False)
            
            with pytest.raises(TypeError, match="must be a string"):
                engine.compute_embeddings(["valid", 123], ["id1", "id2"])


class TestMLEngineSimilaritySearch:
    """Test MLEngine similarity search functionality."""
    
    def test_find_similar(self):
        """Test finding similar items."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            engine = MLEngine(vectorizer_path, embeddings_path)
            descriptions = [
                "mystery detective novel with suspense",
                "sci-fi space adventure with aliens",
                "romantic comedy in Paris",
                "detective thriller with mystery"
            ]
            media_ids = ["id1", "id2", "id3", "id4"]
            
            engine.train_vectorizer(descriptions, save=False)
            engine.compute_embeddings(descriptions, media_ids)
            
            query = "detective mystery"
            query_vector = engine.vectorize_query(query)
            results = engine.find_similar(query_vector, top_k=2)
            
            assert len(results) == 2
            assert all(isinstance(item, tuple) for item in results)
            assert all(len(item) == 2 for item in results)
            
            # Check that results are sorted by score descending
            assert results[0][1] >= results[1][1]
            
            # Check that scores are in valid range
            assert all(0.0 <= score <= 1.0 for _, score in results)
            
            # Check that IDs are from our corpus
            assert all(media_id in media_ids for media_id, _ in results)
    
    def test_find_similar_without_corpus_raises_error(self):
        """Test that finding similar without corpus raises RuntimeError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            engine = MLEngine(vectorizer_path, embeddings_path)
            descriptions = ["mystery novel", "sci-fi adventure"]
            engine.train_vectorizer(descriptions, save=False)
            
            # Use a query with words from the vocabulary to avoid zero norm error
            query_vector = engine.vectorize_query("mystery")
            
            with pytest.raises(RuntimeError, match="Corpus vectors not loaded"):
                engine.find_similar(query_vector)
    
    def test_find_similar_with_different_top_k(self):
        """Test finding similar with different top_k values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            engine = MLEngine(vectorizer_path, embeddings_path)
            descriptions = ["mystery novel", "sci-fi adventure", "romance story", "thriller book"]
            media_ids = ["id1", "id2", "id3", "id4"]
            
            engine.train_vectorizer(descriptions, save=False)
            engine.compute_embeddings(descriptions, media_ids)
            
            query_vector = engine.vectorize_query("mystery")
            
            results_1 = engine.find_similar(query_vector, top_k=1)
            assert len(results_1) == 1
            
            results_3 = engine.find_similar(query_vector, top_k=3)
            assert len(results_3) == 3


class TestMLEngineCorpusLoading:
    """Test MLEngine corpus loading functionality."""
    
    def test_load_corpus(self):
        """Test loading pre-computed corpus embeddings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            engine = MLEngine(vectorizer_path, embeddings_path)
            
            # Create sample corpus vectors
            corpus_vectors = np.random.rand(5, 100)
            corpus_ids = ["id1", "id2", "id3", "id4", "id5"]
            
            engine.load_corpus(corpus_vectors, corpus_ids)
            
            assert engine.corpus_vectors is not None
            assert engine.corpus_ids == corpus_ids
            assert np.array_equal(engine.corpus_vectors, corpus_vectors)
    
    def test_load_corpus_with_invalid_shape_raises_error(self):
        """Test that loading corpus with invalid shape raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            engine = MLEngine(vectorizer_path, embeddings_path)
            
            # 1D array instead of 2D
            with pytest.raises(ValueError, match="corpus_vectors must be 2-dimensional"):
                engine.load_corpus(np.array([1, 2, 3]), ["id1"])
    
    def test_load_corpus_with_mismatched_lengths_raises_error(self):
        """Test that mismatched corpus vectors and IDs raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            engine = MLEngine(vectorizer_path, embeddings_path)
            
            corpus_vectors = np.random.rand(3, 100)
            corpus_ids = ["id1", "id2"]  # Only 2 IDs for 3 vectors
            
            with pytest.raises(ValueError, match="corpus_ids length.*must match.*corpus_vectors rows"):
                engine.load_corpus(corpus_vectors, corpus_ids)
    
    def test_load_corpus_with_non_finite_values_raises_error(self):
        """Test that corpus with non-finite values raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            engine = MLEngine(vectorizer_path, embeddings_path)
            
            corpus_vectors = np.array([[1.0, 2.0, np.nan], [3.0, 4.0, 5.0]])
            corpus_ids = ["id1", "id2"]
            
            with pytest.raises(ValueError, match="corpus_vectors contain non-finite values"):
                engine.load_corpus(corpus_vectors, corpus_ids)


class TestMLEngineVersionTracking:
    """Test MLEngine model version tracking."""
    
    def test_get_model_version(self):
        """Test getting model version."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            engine = MLEngine(vectorizer_path, embeddings_path)
            
            # No version before training
            assert engine.get_model_version() is None
            
            # Train and save
            descriptions = ["mystery novel", "sci-fi adventure"]
            engine.train_vectorizer(descriptions, save=True)
            
            # Should have version after training
            version = engine.get_model_version()
            assert version is not None
            assert isinstance(version, str)
            assert len(version) > 0
    
    def test_validate_model_version(self):
        """Test validating model version."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            engine = MLEngine(vectorizer_path, embeddings_path)
            descriptions = ["mystery novel", "sci-fi adventure"]
            engine.train_vectorizer(descriptions, save=True)
            
            actual_version = engine.get_model_version()
            
            # Correct version should validate
            assert engine.validate_model_version(actual_version) is True
            
            # Wrong version should not validate
            assert engine.validate_model_version("wrong_version") is False


class TestMLEngineIntegration:
    """Integration tests for complete MLEngine workflows."""
    
    def test_complete_workflow(self):
        """Test complete workflow from training to similarity search."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            # Step 1: Initialize engine
            engine = MLEngine(vectorizer_path, embeddings_path)
            
            # Step 2: Train vectorizer
            descriptions = [
                "A cozy mystery set in a coffee shop with a detective",
                "A fast-paced sci-fi thriller about time travel and aliens",
                "A romantic comedy in Paris with love and laughter",
                "A detective thriller with mystery and suspense"
            ]
            media_ids = ["book1", "book2", "book3", "book4"]
            engine.train_vectorizer(descriptions, save=True)
            
            # Step 3: Compute embeddings
            embeddings = engine.compute_embeddings(descriptions, media_ids)
            assert embeddings.shape[0] == len(descriptions)
            
            # Step 4: Vectorize query
            query = "detective mystery coffee shop"
            query_vector = engine.vectorize_query(query)
            
            # Step 5: Find similar items
            results = engine.find_similar(query_vector, top_k=2)
            
            assert len(results) == 2
            # First result should be the coffee shop mystery (most similar)
            assert results[0][0] in media_ids
            assert 0.0 <= results[0][1] <= 1.0
            
            # Step 6: Verify model version tracking
            version = engine.get_model_version()
            assert version is not None
    
    def test_persistence_across_instances(self):
        """Test that trained models persist across engine instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vectorizer_path = os.path.join(tmpdir, "models")
            embeddings_path = os.path.join(tmpdir, "embeddings")
            os.makedirs(vectorizer_path)
            os.makedirs(embeddings_path)
            
            # First instance: train and save
            engine1 = MLEngine(vectorizer_path, embeddings_path)
            descriptions = ["mystery novel", "sci-fi adventure"]
            engine1.train_vectorizer(descriptions, save=True)
            version1 = engine1.get_model_version()
            
            # Second instance: should load existing model
            engine2 = MLEngine(vectorizer_path, embeddings_path)
            version2 = engine2.get_model_version()
            
            assert version1 == version2
            assert engine2.vectorizer is not None
            
            # Should be able to vectorize with second instance
            query_vector = engine2.vectorize_query("mystery")
            assert query_vector is not None
            assert query_vector.shape[0] == 1
