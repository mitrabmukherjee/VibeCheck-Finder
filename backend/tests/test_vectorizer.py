"""
Unit tests for vectorizer training and management functions.

Tests verify that:
- Vectorizer training works with valid corpora
- Input validation catches invalid inputs
- Vectorizer can be saved and loaded with metadata
- Version tracking works correctly
"""

import os
import tempfile
import shutil
import pytest
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from ml_engine.vectorizer import train_vectorizer, save_vectorizer, load_vectorizer


class TestTrainVectorizer:
    """Test suite for train_vectorizer function."""
    
    def test_train_with_valid_corpus(self):
        """Test that vectorizer trains successfully with valid descriptions."""
        descriptions = [
            "A thrilling mystery novel",
            "A science fiction adventure",
            "A romantic comedy story"
        ]
        
        vectorizer = train_vectorizer(descriptions, max_features=100)
        
        # Verify vectorizer is fitted
        assert hasattr(vectorizer, 'vocabulary_')
        assert len(vectorizer.vocabulary_) > 0
        
        # Verify it can transform text
        result = vectorizer.transform(["mystery novel"])
        assert result.shape[0] == 1
        assert result.shape[1] == len(vectorizer.vocabulary_)
    
    def test_train_with_configurable_parameters(self):
        """Test that vectorizer respects configurable parameters."""
        descriptions = [
            "word one two three",
            "word four five six",
            "word seven eight nine"
        ]
        
        # Test with different max_features
        vectorizer = train_vectorizer(descriptions, max_features=5)
        assert len(vectorizer.vocabulary_) <= 5
        
        # Test with different ngram_range
        vectorizer = train_vectorizer(descriptions, ngram_range=(1, 1))
        assert vectorizer.ngram_range == (1, 1)
        
        vectorizer = train_vectorizer(descriptions, ngram_range=(1, 3))
        assert vectorizer.ngram_range == (1, 3)
    
    def test_train_with_single_description(self):
        """Test that vectorizer works with a single description."""
        descriptions = ["A single description with some words"]
        
        vectorizer = train_vectorizer(descriptions, max_features=100)
        
        assert hasattr(vectorizer, 'vocabulary_')
        assert len(vectorizer.vocabulary_) > 0
    
    def test_train_with_large_corpus(self):
        """Test that vectorizer handles larger corpora efficiently."""
        descriptions = [
            f"This is description number {i} with some unique content"
            for i in range(100)
        ]
        
        vectorizer = train_vectorizer(descriptions, max_features=500)
        
        assert hasattr(vectorizer, 'vocabulary_')
        assert len(vectorizer.vocabulary_) > 0
    
    def test_empty_descriptions_list_raises_error(self):
        """Test that empty descriptions list raises ValueError."""
        with pytest.raises(ValueError, match="descriptions list cannot be empty"):
            train_vectorizer([])
    
    def test_all_empty_descriptions_raises_error(self):
        """Test that corpus with only empty descriptions raises ValueError."""
        descriptions = ["", "   ", "\t\n"]
        
        with pytest.raises(ValueError, match="at least one non-empty description"):
            train_vectorizer(descriptions)
    
    def test_all_special_characters_raises_error(self):
        """Test that corpus with only special characters raises ValueError."""
        descriptions = ["@#$%", "!!!", "..."]
        
        with pytest.raises(ValueError, match="at least one non-empty description"):
            train_vectorizer(descriptions)
    
    def test_mixed_empty_and_valid_descriptions(self):
        """Test that vectorizer works when some descriptions are empty."""
        descriptions = [
            "Valid description one",
            "",
            "Valid description two",
            "   ",
            "Valid description three"
        ]
        
        vectorizer = train_vectorizer(descriptions, max_features=100)
        
        # Should succeed because there are valid descriptions
        assert hasattr(vectorizer, 'vocabulary_')
        assert len(vectorizer.vocabulary_) > 0
    
    def test_non_list_input_raises_error(self):
        """Test that non-list input raises TypeError."""
        with pytest.raises(TypeError, match="descriptions must be a list"):
            train_vectorizer("not a list")
        
        with pytest.raises(TypeError, match="descriptions must be a list"):
            train_vectorizer(None)
        
        with pytest.raises(TypeError, match="descriptions must be a list"):
            train_vectorizer(123)
    
    def test_non_string_elements_raise_error(self):
        """Test that list with non-string elements raises TypeError."""
        with pytest.raises(TypeError, match="must be a string"):
            train_vectorizer(["valid", 123, "valid"])
        
        with pytest.raises(TypeError, match="must be a string"):
            train_vectorizer([None, "valid"])
        
        with pytest.raises(TypeError, match="must be a string"):
            train_vectorizer(["valid", ["nested"]])
    
    def test_preprocessing_consistency(self):
        """Test that vectorizer uses preprocessed text consistently."""
        descriptions = [
            "Hello, World!",
            "HELLO WORLD",
            "hello world"
        ]
        
        vectorizer = train_vectorizer(descriptions, max_features=100)
        
        # All three should be treated as the same after preprocessing
        # So vocabulary should be small (just "hello" and "world")
        assert len(vectorizer.vocabulary_) <= 3  # "hello", "world", maybe "hello world"
    
    def test_special_characters_removed_during_training(self):
        """Test that special characters are removed during preprocessing."""
        descriptions = [
            "test@email.com",
            "price: $19.99",
            "hello-world!"
        ]
        
        vectorizer = train_vectorizer(descriptions, max_features=100)
        
        # Verify vectorizer was trained (special chars removed but words remain)
        assert hasattr(vectorizer, 'vocabulary_')
        assert len(vectorizer.vocabulary_) > 0
    
    def test_real_world_media_descriptions(self):
        """Test with realistic media descriptions."""
        descriptions = [
            "A gripping mystery novel set in Victorian London, featuring a brilliant detective.",
            "An epic science fiction saga spanning multiple galaxies and centuries.",
            "A heartwarming romantic comedy about two people who meet by chance.",
            "A thrilling action series with intense fight scenes and plot twists.",
            "A thought-provoking drama exploring themes of identity and belonging."
        ]
        
        vectorizer = train_vectorizer(descriptions, max_features=200, ngram_range=(1, 2))
        
        assert hasattr(vectorizer, 'vocabulary_')
        assert len(vectorizer.vocabulary_) > 0
        
        # Test that it can transform a query
        query = "mystery detective london"
        result = vectorizer.transform([query])
        assert result.shape[0] == 1
    
    def test_train_with_very_long_descriptions(self):
        """Test that training with very long descriptions works correctly."""
        # Create descriptions with 500+ characters each
        long_text = "mystery detective thriller suspense action adventure " * 10
        descriptions = [
            long_text + " novel",
            long_text + " story",
            long_text + " book"
        ]
        
        vectorizer = train_vectorizer(descriptions, max_features=200)
        
        assert hasattr(vectorizer, 'vocabulary_')
        assert len(vectorizer.vocabulary_) > 0
    
    def test_train_with_numbers_in_descriptions(self):
        """Test that descriptions with numbers are handled correctly."""
        descriptions = [
            "A novel from 2020 with 5 star rating",
            "Published in 1984 by George Orwell",
            "Season 3 episode 7 of the series"
        ]
        
        vectorizer = train_vectorizer(descriptions, max_features=100)
        
        # Numbers should be removed, but text should remain
        assert hasattr(vectorizer, 'vocabulary_')
        assert len(vectorizer.vocabulary_) > 0
    
    def test_train_with_duplicate_descriptions(self):
        """Test that training with duplicate descriptions works correctly."""
        descriptions = [
            "mystery novel",
            "mystery novel",  # Duplicate
            "science fiction",
            "science fiction"  # Duplicate
        ]
        
        vectorizer = train_vectorizer(descriptions, max_features=100)
        
        # Should train successfully despite duplicates
        assert hasattr(vectorizer, 'vocabulary_')
        assert len(vectorizer.vocabulary_) > 0
    
    def test_train_with_very_short_descriptions(self):
        """Test that training with very short descriptions (1-2 words) works."""
        descriptions = [
            "mystery",
            "thriller",
            "romance",
            "comedy",
            "drama"
        ]
        
        vectorizer = train_vectorizer(descriptions, max_features=100)
        
        assert hasattr(vectorizer, 'vocabulary_')
        assert len(vectorizer.vocabulary_) > 0
        
        # Should be able to transform queries
        result = vectorizer.transform(["mystery"])
        assert result.shape[0] == 1


class TestSaveVectorizer:
    """Test suite for save_vectorizer function."""
    
    def setup_method(self):
        """Create a temporary directory for each test."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up temporary directory after each test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_save_fitted_vectorizer(self):
        """Test that fitted vectorizer can be saved successfully."""
        descriptions = ["test description one", "test description two"]
        vectorizer = train_vectorizer(descriptions)
        
        version = save_vectorizer(vectorizer, self.temp_dir)
        
        # Verify version was returned
        assert version is not None
        assert isinstance(version, str)
        assert version.startswith("v1.0.0_")
        
        # Verify files were created
        assert os.path.exists(os.path.join(self.temp_dir, 'tfidf_vectorizer.pkl'))
        assert os.path.exists(os.path.join(self.temp_dir, 'vectorizer_metadata.pkl'))
    
    def test_save_with_custom_version(self):
        """Test that custom version identifier is used when provided."""
        descriptions = ["test description"]
        vectorizer = train_vectorizer(descriptions)
        
        custom_version = "v2.5.1_custom"
        version = save_vectorizer(vectorizer, self.temp_dir, version=custom_version)
        
        assert version == custom_version
        
        # Verify metadata contains custom version
        _, metadata = load_vectorizer(self.temp_dir)
        assert metadata['version'] == custom_version
    
    def test_save_creates_directory_if_not_exists(self):
        """Test that save_vectorizer creates directory if it doesn't exist."""
        descriptions = ["test description"]
        vectorizer = train_vectorizer(descriptions)
        
        new_dir = os.path.join(self.temp_dir, 'nested', 'path')
        assert not os.path.exists(new_dir)
        
        save_vectorizer(vectorizer, new_dir)
        
        assert os.path.exists(new_dir)
        assert os.path.exists(os.path.join(new_dir, 'tfidf_vectorizer.pkl'))
    
    def test_save_unfitted_vectorizer_raises_error(self):
        """Test that saving unfitted vectorizer raises ValueError."""
        vectorizer = TfidfVectorizer()
        
        with pytest.raises(ValueError, match="Vectorizer must be fitted"):
            save_vectorizer(vectorizer, self.temp_dir)
    
    def test_metadata_contains_required_fields(self):
        """Test that saved metadata contains all required fields."""
        descriptions = ["test description one", "test description two"]
        vectorizer = train_vectorizer(descriptions, max_features=100, ngram_range=(1, 2))
        
        save_vectorizer(vectorizer, self.temp_dir)
        
        _, metadata = load_vectorizer(self.temp_dir)
        
        # Verify required fields
        assert 'version' in metadata
        assert 'created_at' in metadata
        assert 'vocabulary_size' in metadata
        assert 'max_features' in metadata
        assert 'ngram_range' in metadata
        assert 'min_df' in metadata
        assert 'max_df' in metadata
        
        # Verify values
        assert metadata['vocabulary_size'] == len(vectorizer.vocabulary_)
        assert metadata['max_features'] == 100
        assert metadata['ngram_range'] == (1, 2)
    
    def test_version_uniqueness(self):
        """Test that automatically generated versions are unique."""
        descriptions = ["test description"]
        vectorizer = train_vectorizer(descriptions)
        
        version1 = save_vectorizer(vectorizer, os.path.join(self.temp_dir, 'v1'))
        
        # Small delay to ensure different timestamp (1 second for timestamp precision)
        import time
        time.sleep(1.1)
        
        version2 = save_vectorizer(vectorizer, os.path.join(self.temp_dir, 'v2'))
        
        # Versions should be different due to timestamp
        assert version1 != version2


class TestLoadVectorizer:
    """Test suite for load_vectorizer function."""
    
    def setup_method(self):
        """Create a temporary directory and save a vectorizer for each test."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create and save a test vectorizer
        descriptions = ["test description one", "test description two"]
        self.original_vectorizer = train_vectorizer(descriptions, max_features=50)
        self.version = save_vectorizer(self.original_vectorizer, self.temp_dir, version="v1.0.0_test")
    
    def teardown_method(self):
        """Clean up temporary directory after each test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_load_saved_vectorizer(self):
        """Test that saved vectorizer can be loaded successfully."""
        vectorizer, metadata = load_vectorizer(self.temp_dir)
        
        # Verify vectorizer is loaded
        assert vectorizer is not None
        assert hasattr(vectorizer, 'vocabulary_')
        
        # Verify metadata is loaded
        assert metadata is not None
        assert metadata['version'] == "v1.0.0_test"
    
    def test_loaded_vectorizer_has_same_vocabulary(self):
        """Test that loaded vectorizer has same vocabulary as original."""
        vectorizer, _ = load_vectorizer(self.temp_dir)
        
        assert len(vectorizer.vocabulary_) == len(self.original_vectorizer.vocabulary_)
        assert vectorizer.vocabulary_ == self.original_vectorizer.vocabulary_
    
    def test_loaded_vectorizer_can_transform(self):
        """Test that loaded vectorizer can transform text."""
        vectorizer, _ = load_vectorizer(self.temp_dir)
        
        result = vectorizer.transform(["test description"])
        
        assert result.shape[0] == 1
        assert result.shape[1] == len(vectorizer.vocabulary_)
    
    def test_loaded_vectorizer_produces_same_output(self):
        """Test that loaded vectorizer produces same output as original."""
        vectorizer, _ = load_vectorizer(self.temp_dir)
        
        test_text = ["test description"]
        original_output = self.original_vectorizer.transform(test_text)
        loaded_output = vectorizer.transform(test_text)
        
        # Outputs should be identical
        assert (original_output.toarray() == loaded_output.toarray()).all()
    
    def test_load_nonexistent_vectorizer_raises_error(self):
        """Test that loading from nonexistent path raises FileNotFoundError."""
        nonexistent_path = os.path.join(self.temp_dir, 'nonexistent')
        
        with pytest.raises(FileNotFoundError, match="Vectorizer file not found"):
            load_vectorizer(nonexistent_path)
    
    def test_load_with_missing_metadata_raises_error(self):
        """Test that loading with missing metadata file raises FileNotFoundError."""
        # Remove metadata file
        metadata_file = os.path.join(self.temp_dir, 'vectorizer_metadata.pkl')
        os.remove(metadata_file)
        
        with pytest.raises(FileNotFoundError, match="Metadata file not found"):
            load_vectorizer(self.temp_dir)
    
    def test_metadata_contains_correct_values(self):
        """Test that loaded metadata contains correct values."""
        _, metadata = load_vectorizer(self.temp_dir)
        
        assert metadata['version'] == "v1.0.0_test"
        assert metadata['vocabulary_size'] == len(self.original_vectorizer.vocabulary_)
        assert metadata['max_features'] == 50
        assert 'created_at' in metadata


class TestVectorizerIntegration:
    """Integration tests for complete train-save-load workflow."""
    
    def setup_method(self):
        """Create a temporary directory for each test."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up temporary directory after each test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_complete_workflow(self):
        """Test complete workflow: train -> save -> load -> use."""
        # Step 1: Train vectorizer
        descriptions = [
            "A mystery novel with detective",
            "A science fiction adventure",
            "A romantic comedy story"
        ]
        vectorizer = train_vectorizer(descriptions, max_features=100, ngram_range=(1, 2))
        
        # Step 2: Save vectorizer
        version = save_vectorizer(vectorizer, self.temp_dir, version="v1.0.0")
        assert version == "v1.0.0"
        
        # Step 3: Load vectorizer
        loaded_vectorizer, metadata = load_vectorizer(self.temp_dir)
        assert metadata['version'] == "v1.0.0"
        
        # Step 4: Use loaded vectorizer
        query = "mystery detective"
        result = loaded_vectorizer.transform([query])
        
        assert result.shape[0] == 1
        assert result.shape[1] > 0
    
    def test_multiple_save_load_cycles(self):
        """Test that vectorizer can be saved and loaded multiple times."""
        descriptions = ["test description"]
        vectorizer = train_vectorizer(descriptions)
        
        # Save and load multiple times
        for i in range(3):
            save_path = os.path.join(self.temp_dir, f'cycle_{i}')
            save_vectorizer(vectorizer, save_path, version=f"v1.0.{i}")
            
            loaded_vectorizer, metadata = load_vectorizer(save_path)
            assert metadata['version'] == f"v1.0.{i}"
            
            # Verify it still works
            result = loaded_vectorizer.transform(["test"])
            assert result.shape[0] == 1



class TestVectorizeQuery:
    """Test suite for vectorize_query function."""
    
    def setup_method(self):
        """Create a temporary directory and train/save a vectorizer for each test."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create and save a test vectorizer with realistic corpus
        self.descriptions = [
            "A thrilling mystery novel with detective",
            "A science fiction adventure in space",
            "A romantic comedy story about love",
            "An action packed thriller with suspense",
            "A historical drama set in ancient times"
        ]
        self.vectorizer = train_vectorizer(self.descriptions, max_features=100, ngram_range=(1, 2))
        self.version = save_vectorizer(self.vectorizer, self.temp_dir, version="v1.0.0_test")
    
    def teardown_method(self):
        """Clean up temporary directory after each test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_vectorize_valid_query(self):
        """Test that valid query is vectorized successfully."""
        from ml_engine.vectorizer import vectorize_query
        
        query = "mystery detective novel"
        vector = vectorize_query(query, self.temp_dir)
        
        # Verify shape
        assert vector.shape[0] == 1
        assert vector.shape[1] > 0
        
        # Verify all values are finite
        assert np.all(np.isfinite(vector))
        
        # Verify non-zero norm
        assert np.linalg.norm(vector) > 0
    
    def test_vectorize_query_with_special_characters(self):
        """Test that query with special characters is preprocessed correctly."""
        from ml_engine.vectorizer import vectorize_query
        
        query = "mystery! detective? novel..."
        vector = vectorize_query(query, self.temp_dir)
        
        # Should work because special chars are removed during preprocessing
        assert vector.shape[0] == 1
        assert np.all(np.isfinite(vector))
        assert np.linalg.norm(vector) > 0
    
    def test_vectorize_query_with_uppercase(self):
        """Test that query with uppercase is normalized correctly."""
        from ml_engine.vectorizer import vectorize_query
        
        query = "MYSTERY DETECTIVE NOVEL"
        vector = vectorize_query(query, self.temp_dir)
        
        # Should work because text is lowercased during preprocessing
        assert vector.shape[0] == 1
        assert np.all(np.isfinite(vector))
        assert np.linalg.norm(vector) > 0
    
    def test_vectorize_query_with_extra_whitespace(self):
        """Test that query with extra whitespace is normalized correctly."""
        from ml_engine.vectorizer import vectorize_query
        
        query = "  mystery   detective   novel  "
        vector = vectorize_query(query, self.temp_dir)
        
        # Should work because whitespace is normalized during preprocessing
        assert vector.shape[0] == 1
        assert np.all(np.isfinite(vector))
        assert np.linalg.norm(vector) > 0
    
    def test_vectorize_query_output_shape(self):
        """Test that output vector has correct shape (1, dimension)."""
        from ml_engine.vectorizer import vectorize_query
        
        query = "science fiction space"
        vector = vectorize_query(query, self.temp_dir)
        
        # Shape should be (1, vocabulary_size)
        assert vector.shape[0] == 1
        assert vector.shape[1] == len(self.vectorizer.vocabulary_)
    
    def test_vectorize_query_finite_values(self):
        """Test that all vector values are finite floats."""
        from ml_engine.vectorizer import vectorize_query
        
        query = "romantic comedy love"
        vector = vectorize_query(query, self.temp_dir)
        
        # All values should be finite (no NaN or Inf)
        assert np.all(np.isfinite(vector))
        
        # All values should be floats
        assert vector.dtype in [np.float32, np.float64]
    
    def test_vectorize_query_non_zero_norm(self):
        """Test that vector has non-zero norm."""
        from ml_engine.vectorizer import vectorize_query
        
        query = "action thriller suspense"
        vector = vectorize_query(query, self.temp_dir)
        
        # Vector norm should be greater than zero
        norm = np.linalg.norm(vector)
        assert norm > 0
        assert np.isfinite(norm)
    
    def test_vectorize_empty_query_raises_error(self):
        """Test that empty query raises ValueError."""
        from ml_engine.vectorizer import vectorize_query
        
        with pytest.raises(ValueError, match="Query must contain valid text"):
            vectorize_query("", self.temp_dir)
    
    def test_vectorize_whitespace_only_query_raises_error(self):
        """Test that whitespace-only query raises ValueError."""
        from ml_engine.vectorizer import vectorize_query
        
        with pytest.raises(ValueError, match="Query must contain valid text"):
            vectorize_query("   \t\n   ", self.temp_dir)
    
    def test_vectorize_special_characters_only_raises_error(self):
        """Test that query with only special characters raises ValueError."""
        from ml_engine.vectorizer import vectorize_query
        
        with pytest.raises(ValueError, match="Query must contain valid text"):
            vectorize_query("@#$%^&*()", self.temp_dir)
    
    def test_vectorize_non_string_query_raises_error(self):
        """Test that non-string query raises TypeError."""
        from ml_engine.vectorizer import vectorize_query
        
        with pytest.raises(TypeError, match="query must be a string"):
            vectorize_query(123, self.temp_dir)
        
        with pytest.raises(TypeError, match="query must be a string"):
            vectorize_query(None, self.temp_dir)
        
        with pytest.raises(TypeError, match="query must be a string"):
            vectorize_query(["query"], self.temp_dir)
    
    def test_vectorize_nonexistent_vectorizer_path_raises_error(self):
        """Test that nonexistent vectorizer path raises FileNotFoundError."""
        from ml_engine.vectorizer import vectorize_query
        
        nonexistent_path = os.path.join(self.temp_dir, 'nonexistent')
        
        with pytest.raises(FileNotFoundError, match="Vectorizer file not found"):
            vectorize_query("test query", nonexistent_path)
    
    def test_vectorize_query_with_unknown_words(self):
        """Test that query with words not in vocabulary still produces valid vector."""
        from ml_engine.vectorizer import vectorize_query
        
        # Use words that are unlikely to be in the vocabulary
        query = "xyzabc qwerty asdfgh"
        
        # This should raise ValueError because all words are unknown
        # and the resulting vector will have zero norm
        with pytest.raises(ValueError, match="zero norm"):
            vectorize_query(query, self.temp_dir)
    
    def test_vectorize_query_with_mixed_known_unknown_words(self):
        """Test that query with mix of known and unknown words works."""
        from ml_engine.vectorizer import vectorize_query
        
        # Mix known words from corpus with unknown words
        query = "mystery xyzabc detective qwerty"
        vector = vectorize_query(query, self.temp_dir)
        
        # Should work because some words are in vocabulary
        assert vector.shape[0] == 1
        assert np.all(np.isfinite(vector))
        assert np.linalg.norm(vector) > 0
    
    def test_vectorize_same_query_produces_same_vector(self):
        """Test that vectorizing the same query twice produces identical vectors."""
        from ml_engine.vectorizer import vectorize_query
        
        query = "science fiction adventure"
        
        vector1 = vectorize_query(query, self.temp_dir)
        vector2 = vectorize_query(query, self.temp_dir)
        
        # Vectors should be identical
        assert np.array_equal(vector1, vector2)
    
    def test_vectorize_similar_queries_produce_similar_vectors(self):
        """Test that similar queries produce vectors with similar values."""
        from ml_engine.vectorizer import vectorize_query
        
        query1 = "mystery detective"
        query2 = "detective mystery"
        
        vector1 = vectorize_query(query1, self.temp_dir)
        vector2 = vectorize_query(query2, self.temp_dir)
        
        # Vectors should be identical (word order doesn't matter in TF-IDF)
        assert np.array_equal(vector1, vector2)
    
    def test_vectorize_long_query(self):
        """Test that long query is vectorized successfully."""
        from ml_engine.vectorizer import vectorize_query
        
        query = " ".join(["mystery detective novel"] * 50)  # Repeat to make it long
        vector = vectorize_query(query, self.temp_dir)
        
        assert vector.shape[0] == 1
        assert np.all(np.isfinite(vector))
        assert np.linalg.norm(vector) > 0
    
    def test_vectorize_single_word_query(self):
        """Test that single word query works."""
        from ml_engine.vectorizer import vectorize_query
        
        query = "mystery"
        vector = vectorize_query(query, self.temp_dir)
        
        assert vector.shape[0] == 1
        assert np.all(np.isfinite(vector))
        assert np.linalg.norm(vector) > 0
    
    def test_vectorize_query_preprocessing_consistency(self):
        """Test that preprocessing is consistent with training."""
        from ml_engine.vectorizer import vectorize_query
        
        # These should all produce the same vector after preprocessing
        queries = [
            "Mystery Detective",
            "mystery detective",
            "MYSTERY DETECTIVE",
            "mystery! detective?",
            "  mystery   detective  "
        ]
        
        vectors = [vectorize_query(q, self.temp_dir) for q in queries]
        
        # All vectors should be identical
        for i in range(1, len(vectors)):
            assert np.array_equal(vectors[0], vectors[i])
    
    def test_vectorize_real_world_queries(self):
        """Test with realistic user queries."""
        from ml_engine.vectorizer import vectorize_query
        
        queries = [
            "A cozy mystery book set in a coffee shop",
            "Fast-paced sci-fi show about time travel",
            "Romantic comedy with witty dialogue",
            "Historical drama about ancient civilizations",
            "Thriller with unexpected plot twists"
        ]
        
        for query in queries:
            vector = vectorize_query(query, self.temp_dir)
            
            # Verify basic properties
            assert vector.shape[0] == 1
            assert np.all(np.isfinite(vector))
            assert np.linalg.norm(vector) > 0
    
    def test_vectorize_very_long_text(self):
        """Test that very long text (1000+ characters) is handled correctly."""
        from ml_engine.vectorizer import vectorize_query
        
        # Create a very long query (over 1000 characters)
        base_text = "mystery detective novel thriller suspense action adventure "
        query = base_text * 20  # Creates ~1200 character string
        
        assert len(query) > 1000, "Query should be over 1000 characters"
        
        vector = vectorize_query(query, self.temp_dir)
        
        # Verify it handles long text correctly
        assert vector.shape[0] == 1
        assert np.all(np.isfinite(vector))
        assert np.linalg.norm(vector) > 0
    
    def test_vectorize_query_with_numbers(self):
        """Test that queries with numbers are handled correctly."""
        from ml_engine.vectorizer import vectorize_query
        
        query = "mystery novel from 2020 with 5 stars"
        vector = vectorize_query(query, self.temp_dir)
        
        # Numbers should be removed during preprocessing, but text should remain
        assert vector.shape[0] == 1
        assert np.all(np.isfinite(vector))
        assert np.linalg.norm(vector) > 0
    
    def test_vectorize_query_with_mixed_alphanumeric(self):
        """Test that mixed alphanumeric content is handled correctly."""
        from ml_engine.vectorizer import vectorize_query
        
        query = "sci-fi 2049 blade runner style mystery"
        vector = vectorize_query(query, self.temp_dir)
        
        assert vector.shape[0] == 1
        assert np.all(np.isfinite(vector))
        assert np.linalg.norm(vector) > 0
    
    def test_vectorize_query_with_unicode_characters(self):
        """Test that unicode/international characters are handled gracefully."""
        from ml_engine.vectorizer import vectorize_query
        
        # Mix English with unicode characters
        query = "mystery café naïve résumé"
        vector = vectorize_query(query, self.temp_dir)
        
        # Should work - unicode chars may be removed but English words remain
        assert vector.shape[0] == 1
        assert np.all(np.isfinite(vector))
        assert np.linalg.norm(vector) > 0
    
    def test_vectorize_query_with_repeated_words(self):
        """Test that queries with repeated words are handled correctly."""
        from ml_engine.vectorizer import vectorize_query
        
        query = "mystery mystery mystery detective detective"
        vector = vectorize_query(query, self.temp_dir)
        
        # TF-IDF should handle repeated words appropriately
        assert vector.shape[0] == 1
        assert np.all(np.isfinite(vector))
        assert np.linalg.norm(vector) > 0
    
    def test_vectorize_query_with_newlines_and_tabs(self):
        """Test that queries with newlines and tabs are normalized."""
        from ml_engine.vectorizer import vectorize_query
        
        query = "mystery\ndetective\tnovel\r\nthriller"
        vector = vectorize_query(query, self.temp_dir)
        
        # Newlines and tabs should be normalized to spaces
        assert vector.shape[0] == 1
        assert np.all(np.isfinite(vector))
        assert np.linalg.norm(vector) > 0
    
    def test_vectorize_query_consistency_across_calls(self):
        """Test that multiple calls with same query produce identical results."""
        from ml_engine.vectorizer import vectorize_query
        
        query = "science fiction space adventure"
        
        # Vectorize multiple times
        vectors = [vectorize_query(query, self.temp_dir) for _ in range(5)]
        
        # All vectors should be identical
        for i in range(1, len(vectors)):
            assert np.array_equal(vectors[0], vectors[i])
    
    def test_train_vectorizer_with_duplicate_descriptions(self):
        """Test that training with duplicate descriptions works correctly."""
        descriptions = [
            "mystery novel",
            "mystery novel",  # Duplicate
            "science fiction",
            "science fiction"  # Duplicate
        ]
        
        vectorizer = train_vectorizer(descriptions, max_features=100)
        
        # Should train successfully despite duplicates
        assert hasattr(vectorizer, 'vocabulary_')
        assert len(vectorizer.vocabulary_) > 0
    
    def test_train_vectorizer_with_very_short_descriptions(self):
        """Test that training with very short descriptions (1-2 words) works."""
        descriptions = [
            "mystery",
            "thriller",
            "romance",
            "comedy",
            "drama"
        ]
        
        vectorizer = train_vectorizer(descriptions, max_features=100)
        
        assert hasattr(vectorizer, 'vocabulary_')
        assert len(vectorizer.vocabulary_) > 0
        
        # Should be able to transform queries
        result = vectorizer.transform(["mystery"])
        assert result.shape[0] == 1



class TestFindSimilar:
    """Test suite for find_similar function."""
    
    def test_find_similar_basic_functionality(self):
        """Test that find_similar returns correct number of results."""
        from ml_engine.vectorizer import find_similar
        
        # Create simple test vectors
        query_vector = np.array([[1.0, 0.0, 0.0]])
        corpus_vectors = np.array([
            [1.0, 0.0, 0.0],  # Perfect match
            [0.9, 0.1, 0.0],  # High similarity
            [0.5, 0.5, 0.0],  # Medium similarity
            [0.0, 1.0, 0.0],  # Low similarity
            [0.0, 0.0, 1.0],  # No similarity
        ])
        corpus_ids = ["id1", "id2", "id3", "id4", "id5"]
        
        results = find_similar(query_vector, corpus_vectors, corpus_ids, top_k=3)
        
        # Should return exactly 3 results
        assert len(results) == 3
        
        # Results should be tuples of (media_id, score)
        for media_id, score in results:
            assert isinstance(media_id, str)
            assert isinstance(score, (float, np.floating))
    
    def test_find_similar_scores_descending(self):
        """Test that results are sorted by score in descending order."""
        from ml_engine.vectorizer import find_similar
        
        query_vector = np.array([[1.0, 0.0, 0.0]])
        corpus_vectors = np.array([
            [0.5, 0.5, 0.0],  # Medium similarity
            [1.0, 0.0, 0.0],  # Perfect match
            [0.0, 1.0, 0.0],  # Low similarity
            [0.9, 0.1, 0.0],  # High similarity
        ])
        corpus_ids = ["id1", "id2", "id3", "id4"]
        
        results = find_similar(query_vector, corpus_vectors, corpus_ids, top_k=4)
        
        # Verify scores are in descending order
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)
        
        # First result should be the perfect match (id2)
        assert results[0][0] == "id2"
        assert results[0][1] > 0.99  # Should be very close to 1.0
    
    def test_find_similar_scores_in_valid_range(self):
        """Test that all scores are in range [0.0, 1.0]."""
        from ml_engine.vectorizer import find_similar
        
        query_vector = np.array([[0.5, 0.5, 0.0]])
        corpus_vectors = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.5, 0.5, 0.0],
            [0.3, 0.7, 0.0],
        ])
        corpus_ids = ["id1", "id2", "id3", "id4"]
        
        results = find_similar(query_vector, corpus_vectors, corpus_ids, top_k=4)
        
        # All scores should be in [0.0, 1.0]
        for _, score in results:
            assert 0.0 <= score <= 1.0
    
    def test_find_similar_scores_are_finite(self):
        """Test that all scores are finite (no NaN or Inf)."""
        from ml_engine.vectorizer import find_similar
        
        query_vector = np.array([[0.5, 0.5, 0.0]])
        corpus_vectors = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.5, 0.5, 0.0],
        ])
        corpus_ids = ["id1", "id2", "id3"]
        
        results = find_similar(query_vector, corpus_vectors, corpus_ids, top_k=3)
        
        # All scores should be finite
        for _, score in results:
            assert np.isfinite(score)
    
    def test_find_similar_with_top_k_1(self):
        """Test that top_k=1 returns only the best match."""
        from ml_engine.vectorizer import find_similar
        
        query_vector = np.array([[1.0, 0.0, 0.0]])
        corpus_vectors = np.array([
            [0.5, 0.5, 0.0],
            [1.0, 0.0, 0.0],  # Best match
            [0.0, 1.0, 0.0],
        ])
        corpus_ids = ["id1", "id2", "id3"]
        
        results = find_similar(query_vector, corpus_vectors, corpus_ids, top_k=1)
        
        assert len(results) == 1
        assert results[0][0] == "id2"
    
    def test_find_similar_with_all_results(self):
        """Test that top_k equal to corpus size returns all results."""
        from ml_engine.vectorizer import find_similar
        
        query_vector = np.array([[1.0, 0.0, 0.0]])
        corpus_vectors = np.array([
            [1.0, 0.0, 0.0],
            [0.5, 0.5, 0.0],
            [0.0, 1.0, 0.0],
        ])
        corpus_ids = ["id1", "id2", "id3"]
        
        results = find_similar(query_vector, corpus_vectors, corpus_ids, top_k=3)
        
        assert len(results) == 3
        # All IDs should be present
        result_ids = [media_id for media_id, _ in results]
        assert set(result_ids) == set(corpus_ids)
    
    def test_find_similar_deduplication(self):
        """Test that duplicate media IDs are deduplicated, keeping highest score."""
        from ml_engine.vectorizer import find_similar
        
        query_vector = np.array([[1.0, 0.0, 0.0]])
        corpus_vectors = np.array([
            [1.0, 0.0, 0.0],  # Perfect match
            [0.9, 0.1, 0.0],  # High similarity
            [0.8, 0.2, 0.0],  # Medium similarity
        ])
        # Duplicate IDs: id1 appears twice
        corpus_ids = ["id1", "id2", "id1"]
        
        results = find_similar(query_vector, corpus_vectors, corpus_ids, top_k=3)
        
        # Should have only 2 unique IDs (id1 and id2)
        result_ids = [media_id for media_id, _ in results]
        assert len(result_ids) == len(set(result_ids))  # No duplicates
        
        # id1 should have the highest score (from the first occurrence)
        id1_score = next(score for media_id, score in results if media_id == "id1")
        assert id1_score > 0.99  # Should be close to 1.0 (the higher score)
    
    def test_find_similar_no_duplicates_in_results(self):
        """Test that results contain no duplicate media IDs."""
        from ml_engine.vectorizer import find_similar
        
        query_vector = np.array([[0.5, 0.5, 0.0]])
        corpus_vectors = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.5, 0.5, 0.0],
            [0.3, 0.7, 0.0],
        ])
        corpus_ids = ["id1", "id2", "id3", "id4"]
        
        results = find_similar(query_vector, corpus_vectors, corpus_ids, top_k=4)
        
        # Extract media IDs
        result_ids = [media_id for media_id, _ in results]
        
        # No duplicates
        assert len(result_ids) == len(set(result_ids))
    
    def test_find_similar_invalid_query_vector_shape(self):
        """Test that invalid query_vector shape raises ValueError."""
        from ml_engine.vectorizer import find_similar
        
        # Wrong shape: (3,) instead of (1, 3)
        query_vector = np.array([1.0, 0.0, 0.0])
        corpus_vectors = np.array([[1.0, 0.0, 0.0]])
        corpus_ids = ["id1"]
        
        with pytest.raises(ValueError, match="query_vector must have shape"):
            find_similar(query_vector, corpus_vectors, corpus_ids, top_k=1)
        
        # Wrong shape: (2, 3) instead of (1, 3)
        query_vector = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        
        with pytest.raises(ValueError, match="query_vector must have shape"):
            find_similar(query_vector, corpus_vectors, corpus_ids, top_k=1)
    
    def test_find_similar_invalid_corpus_vectors_shape(self):
        """Test that invalid corpus_vectors shape raises ValueError."""
        from ml_engine.vectorizer import find_similar
        
        query_vector = np.array([[1.0, 0.0, 0.0]])
        
        # Wrong shape: 1D instead of 2D
        corpus_vectors = np.array([1.0, 0.0, 0.0])
        corpus_ids = ["id1"]
        
        with pytest.raises(ValueError, match="corpus_vectors must be 2-dimensional"):
            find_similar(query_vector, corpus_vectors, corpus_ids, top_k=1)
    
    def test_find_similar_mismatched_corpus_ids_length(self):
        """Test that mismatched corpus_ids length raises ValueError."""
        from ml_engine.vectorizer import find_similar
        
        query_vector = np.array([[1.0, 0.0, 0.0]])
        corpus_vectors = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ])
        # Only 1 ID for 2 vectors
        corpus_ids = ["id1"]
        
        with pytest.raises(ValueError, match="corpus_ids length.*must match"):
            find_similar(query_vector, corpus_vectors, corpus_ids, top_k=1)
    
    def test_find_similar_mismatched_dimensions(self):
        """Test that mismatched vector dimensions raise ValueError."""
        from ml_engine.vectorizer import find_similar
        
        # Query vector has 3 dimensions
        query_vector = np.array([[1.0, 0.0, 0.0]])
        # Corpus vectors have 4 dimensions
        corpus_vectors = np.array([[1.0, 0.0, 0.0, 0.0]])
        corpus_ids = ["id1"]
        
        with pytest.raises(ValueError, match="dimension.*must match"):
            find_similar(query_vector, corpus_vectors, corpus_ids, top_k=1)
    
    def test_find_similar_invalid_top_k_zero(self):
        """Test that top_k=0 raises ValueError."""
        from ml_engine.vectorizer import find_similar
        
        query_vector = np.array([[1.0, 0.0, 0.0]])
        corpus_vectors = np.array([[1.0, 0.0, 0.0]])
        corpus_ids = ["id1"]
        
        with pytest.raises(ValueError, match="top_k must be positive"):
            find_similar(query_vector, corpus_vectors, corpus_ids, top_k=0)
    
    def test_find_similar_invalid_top_k_negative(self):
        """Test that negative top_k raises ValueError."""
        from ml_engine.vectorizer import find_similar
        
        query_vector = np.array([[1.0, 0.0, 0.0]])
        corpus_vectors = np.array([[1.0, 0.0, 0.0]])
        corpus_ids = ["id1"]
        
        with pytest.raises(ValueError, match="top_k must be positive"):
            find_similar(query_vector, corpus_vectors, corpus_ids, top_k=-1)
    
    def test_find_similar_top_k_exceeds_corpus_size(self):
        """Test that top_k exceeding corpus size raises ValueError."""
        from ml_engine.vectorizer import find_similar
        
        query_vector = np.array([[1.0, 0.0, 0.0]])
        corpus_vectors = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ])
        corpus_ids = ["id1", "id2"]
        
        with pytest.raises(ValueError, match="top_k.*cannot exceed corpus size"):
            find_similar(query_vector, corpus_vectors, corpus_ids, top_k=5)
    
    def test_find_similar_unsupported_metric(self):
        """Test that unsupported similarity metric raises ValueError."""
        from ml_engine.vectorizer import find_similar
        
        query_vector = np.array([[1.0, 0.0, 0.0]])
        corpus_vectors = np.array([[1.0, 0.0, 0.0]])
        corpus_ids = ["id1"]
        
        with pytest.raises(ValueError, match="similarity_metric must be one of"):
            find_similar(query_vector, corpus_vectors, corpus_ids, top_k=1, similarity_metric="euclidean")
    
    def test_find_similar_with_zero_vectors(self):
        """Test behavior with zero vectors (edge case)."""
        from ml_engine.vectorizer import find_similar
        
        query_vector = np.array([[0.0, 0.0, 0.0]])
        corpus_vectors = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
        ])
        corpus_ids = ["id1", "id2"]
        
        # This should work but may produce NaN scores
        # The function should handle this gracefully
        try:
            results = find_similar(query_vector, corpus_vectors, corpus_ids, top_k=2)
            # If it succeeds, verify scores are valid
            for _, score in results:
                assert np.isfinite(score)
                assert 0.0 <= score <= 1.0
        except ValueError as e:
            # It's acceptable to raise an error for non-finite scores
            assert "non-finite" in str(e).lower()
    
    def test_find_similar_with_normalized_vectors(self):
        """Test with L2-normalized vectors (common for cosine similarity)."""
        from ml_engine.vectorizer import find_similar
        
        # Create normalized vectors
        query_vector = np.array([[0.6, 0.8, 0.0]])
        query_vector = query_vector / np.linalg.norm(query_vector)
        
        corpus_vectors = np.array([
            [0.6, 0.8, 0.0],
            [0.8, 0.6, 0.0],
            [0.0, 1.0, 0.0],
        ])
        # Normalize each corpus vector
        corpus_vectors = corpus_vectors / np.linalg.norm(corpus_vectors, axis=1, keepdims=True)
        
        corpus_ids = ["id1", "id2", "id3"]
        
        results = find_similar(query_vector, corpus_vectors, corpus_ids, top_k=3)
        
        # All scores should be in [0.0, 1.0]
        for _, score in results:
            assert 0.0 <= score <= 1.0
            assert np.isfinite(score)
        
        # First result should be id1 (identical vector)
        assert results[0][0] == "id1"
        assert results[0][1] > 0.99
    
    def test_find_similar_with_realistic_tfidf_vectors(self):
        """Test with realistic TF-IDF vectors from trained vectorizer."""
        from ml_engine.vectorizer import find_similar
        
        # Create a simple TF-IDF vectorizer
        descriptions = [
            "mystery detective novel",
            "science fiction space adventure",
            "romantic comedy love story",
            "thriller suspense action"
        ]
        vectorizer = train_vectorizer(descriptions, max_features=50)
        
        # Transform descriptions to get corpus vectors
        corpus_vectors = vectorizer.transform(descriptions).toarray()
        corpus_ids = ["id1", "id2", "id3", "id4"]
        
        # Create a query vector
        query = "detective mystery"
        query_vector = vectorizer.transform([query]).toarray()
        
        results = find_similar(query_vector, corpus_vectors, corpus_ids, top_k=2)
        
        # Should return 2 results
        assert len(results) == 2
        
        # First result should be id1 (mystery detective novel)
        assert results[0][0] == "id1"
        
        # All scores should be valid
        for _, score in results:
            assert 0.0 <= score <= 1.0
            assert np.isfinite(score)
    
    def test_find_similar_with_large_corpus(self):
        """Test with a larger corpus to verify performance and correctness."""
        from ml_engine.vectorizer import find_similar
        
        # Create a larger corpus
        np.random.seed(42)
        query_vector = np.random.rand(1, 100)
        corpus_vectors = np.random.rand(1000, 100)
        corpus_ids = [f"id{i}" for i in range(1000)]
        
        results = find_similar(query_vector, corpus_vectors, corpus_ids, top_k=10)
        
        # Should return exactly 10 results
        assert len(results) == 10
        
        # All scores should be valid
        for _, score in results:
            assert 0.0 <= score <= 1.0
            assert np.isfinite(score)
        
        # Scores should be in descending order
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)
        
        # No duplicate IDs
        result_ids = [media_id for media_id, _ in results]
        assert len(result_ids) == len(set(result_ids))
    
    def test_find_similar_perfect_match(self):
        """Test that identical vectors produce score of 1.0."""
        from ml_engine.vectorizer import find_similar
        
        query_vector = np.array([[0.5, 0.5, 0.5]])
        corpus_vectors = np.array([
            [0.5, 0.5, 0.5],  # Identical
            [0.4, 0.4, 0.4],  # Similar but not identical
        ])
        corpus_ids = ["id1", "id2"]
        
        results = find_similar(query_vector, corpus_vectors, corpus_ids, top_k=2)
        
        # First result should be the identical vector with score ~1.0
        assert results[0][0] == "id1"
        assert results[0][1] > 0.99  # Should be very close to 1.0
    
    def test_find_similar_orthogonal_vectors(self):
        """Test that orthogonal vectors produce score of 0.0."""
        from ml_engine.vectorizer import find_similar
        
        query_vector = np.array([[1.0, 0.0, 0.0]])
        corpus_vectors = np.array([
            [0.0, 1.0, 0.0],  # Orthogonal
            [0.0, 0.0, 1.0],  # Orthogonal
        ])
        corpus_ids = ["id1", "id2"]
        
        results = find_similar(query_vector, corpus_vectors, corpus_ids, top_k=2)
        
        # Both scores should be 0.0 (orthogonal vectors)
        for _, score in results:
            assert score < 0.01  # Should be very close to 0.0
    
    def test_find_similar_consistency(self):
        """Test that calling find_similar multiple times produces identical results."""
        from ml_engine.vectorizer import find_similar
        
        query_vector = np.array([[0.5, 0.5, 0.0]])
        corpus_vectors = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.5, 0.5, 0.0],
        ])
        corpus_ids = ["id1", "id2", "id3"]
        
        # Call multiple times
        results1 = find_similar(query_vector, corpus_vectors, corpus_ids, top_k=3)
        results2 = find_similar(query_vector, corpus_vectors, corpus_ids, top_k=3)
        results3 = find_similar(query_vector, corpus_vectors, corpus_ids, top_k=3)
        
        # All results should be identical
        assert results1 == results2 == results3
