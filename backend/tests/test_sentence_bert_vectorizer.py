"""
Unit tests for SentenceBertVectorizer class.

Tests the basic functionality of the Sentence-BERT vectorizer including
initialization, encoding, dimension checking, and save/load operations.
"""

import os
import tempfile
import shutil
import numpy as np
import pytest

from ml_engine.sentence_bert_vectorizer import SentenceBertVectorizer


class TestSentenceBertVectorizer:
    """Test suite for SentenceBertVectorizer class."""
    
    def test_initialization_default_model(self):
        """Test initialization with default model name."""
        vectorizer = SentenceBertVectorizer()
        assert vectorizer.model_name == "all-MiniLM-L6-v2"
        assert vectorizer.get_embedding_dimension() == 384
    
    def test_initialization_custom_model(self):
        """Test initialization with custom model name."""
        # Using the same model but explicitly specified
        vectorizer = SentenceBertVectorizer(model_name="all-MiniLM-L6-v2")
        assert vectorizer.model_name == "all-MiniLM-L6-v2"
        assert vectorizer.get_embedding_dimension() == 384
    
    def test_encode_single_text(self):
        """Test encoding a single text string."""
        vectorizer = SentenceBertVectorizer()
        text = "A mystery detective novel"
        embedding = vectorizer.encode(text)
        
        # Check shape is (1, 384)
        assert embedding.shape == (1, 384)
        
        # Check all values are finite
        assert np.all(np.isfinite(embedding))
        
        # Check embedding is normalized (L2 norm should be close to 1)
        norm = np.linalg.norm(embedding)
        assert np.isclose(norm, 1.0, atol=1e-5)
    
    def test_encode_multiple_texts(self):
        """Test encoding multiple texts in batch."""
        vectorizer = SentenceBertVectorizer()
        texts = [
            "A mystery detective novel",
            "A romantic comedy film",
            "A science fiction adventure"
        ]
        embeddings = vectorizer.encode(texts)
        
        # Check shape is (3, 384)
        assert embeddings.shape == (3, 384)
        
        # Check all values are finite
        assert np.all(np.isfinite(embeddings))
        
        # Check each embedding is normalized
        for i in range(len(texts)):
            norm = np.linalg.norm(embeddings[i])
            assert np.isclose(norm, 1.0, atol=1e-5)
    
    def test_encode_empty_list_raises_error(self):
        """Test that encoding empty list raises ValueError."""
        vectorizer = SentenceBertVectorizer()
        with pytest.raises(ValueError, match="texts cannot be empty"):
            vectorizer.encode([])
    
    def test_encode_without_normalization(self):
        """Test encoding without L2 normalization."""
        vectorizer = SentenceBertVectorizer()
        text = "A mystery detective novel"
        embedding = vectorizer.encode(text, normalize_embeddings=False)
        
        # Check shape is still (1, 384)
        assert embedding.shape == (1, 384)
        
        # Check all values are finite
        assert np.all(np.isfinite(embedding))
        
        # Without normalization, norm may not be 1.0
        norm = np.linalg.norm(embedding)
        assert norm > 0  # But should still be non-zero
    
    def test_get_embedding_dimension(self):
        """Test get_embedding_dimension returns 384."""
        vectorizer = SentenceBertVectorizer()
        assert vectorizer.get_embedding_dimension() == 384
    
    def test_save_and_load(self):
        """Test saving and loading model configuration."""
        # Create temporary directory for testing
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create and save vectorizer
            vectorizer = SentenceBertVectorizer(model_name="all-MiniLM-L6-v2")
            vectorizer.save(temp_dir)
            
            # Check metadata file exists
            metadata_file = os.path.join(temp_dir, 'sbert_metadata.json')
            assert os.path.exists(metadata_file)
            
            # Load vectorizer from saved configuration
            loaded_vectorizer = SentenceBertVectorizer.load(temp_dir)
            
            # Check loaded configuration matches original
            assert loaded_vectorizer.model_name == vectorizer.model_name
            assert loaded_vectorizer.get_embedding_dimension() == 384
            
            # Test that loaded vectorizer can encode
            text = "Test text"
            embedding = loaded_vectorizer.encode(text)
            assert embedding.shape == (1, 384)
            
        finally:
            # Clean up temporary directory
            shutil.rmtree(temp_dir)
    
    def test_load_nonexistent_path_raises_error(self):
        """Test that loading from nonexistent path raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            SentenceBertVectorizer.load("/nonexistent/path")
    
    def test_encoding_idempotence(self):
        """Test that encoding same text multiple times produces identical results."""
        vectorizer = SentenceBertVectorizer()
        text = "A mystery detective novel"
        
        # Encode the same text three times
        embedding1 = vectorizer.encode(text)
        embedding2 = vectorizer.encode(text)
        embedding3 = vectorizer.encode(text)
        
        # Check all embeddings are identical
        assert np.allclose(embedding1, embedding2, atol=1e-7)
        assert np.allclose(embedding2, embedding3, atol=1e-7)
        assert np.allclose(embedding1, embedding3, atol=1e-7)
    
    def test_encode_special_characters(self):
        """Test encoding text with special characters and non-ASCII."""
        vectorizer = SentenceBertVectorizer()
        texts = [
            "Hello, world!",
            "Café résumé",
            "日本語テキスト",
            "Emoji test 😀🎉"
        ]
        
        for text in texts:
            embedding = vectorizer.encode(text)
            assert embedding.shape == (1, 384)
            assert np.all(np.isfinite(embedding))
    
    def test_encode_very_short_text(self):
        """Test encoding very short text."""
        vectorizer = SentenceBertVectorizer()
        short_texts = ["a", "hi", "ok"]
        
        for text in short_texts:
            embedding = vectorizer.encode(text)
            assert embedding.shape == (1, 384)
            assert np.all(np.isfinite(embedding))
    
    def test_encode_long_text(self):
        """Test encoding long text (model will truncate to 512 tokens)."""
        vectorizer = SentenceBertVectorizer()
        # Create a very long text
        long_text = " ".join(["word"] * 1000)
        
        embedding = vectorizer.encode(long_text)
        assert embedding.shape == (1, 384)
        assert np.all(np.isfinite(embedding))
