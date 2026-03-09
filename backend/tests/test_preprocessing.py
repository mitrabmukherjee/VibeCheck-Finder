"""
Unit tests for text preprocessing functions.

Tests verify that preprocessing correctly handles:
- Lowercase conversion
- Special character removal
- Whitespace normalization
- Edge cases (empty strings, special characters only, etc.)
"""

import pytest
from hypothesis import given, strategies as st
from ml_engine.preprocessing import preprocess_text


class TestPreprocessText:
    """Test suite for preprocess_text function."""
    
    def test_lowercase_conversion(self):
        """Test that text is converted to lowercase."""
        assert preprocess_text("HELLO WORLD") == "hello world"
        assert preprocess_text("MiXeD CaSe") == "mixed case"
        assert preprocess_text("ABC123") == "abc123"
    
    def test_special_character_removal(self):
        """Test that special characters are removed."""
        assert preprocess_text("hello@world!") == "helloworld"
        assert preprocess_text("test#$%^&*()") == "test"
        assert preprocess_text("email@example.com") == "emailexamplecom"
        assert preprocess_text("price: $19.99") == "price 1999"
    
    def test_whitespace_normalization(self):
        """Test that multiple spaces are collapsed to single space."""
        assert preprocess_text("hello    world") == "hello world"
        assert preprocess_text("multiple   spaces   here") == "multiple spaces here"
        assert preprocess_text("tab\t\tspaces") == "tab spaces"
        assert preprocess_text("newline\n\nspaces") == "newline spaces"
    
    def test_leading_trailing_whitespace_removal(self):
        """Test that leading and trailing whitespace is removed."""
        assert preprocess_text("  hello world  ") == "hello world"
        assert preprocess_text("\t\nhello\n\t") == "hello"
        assert preprocess_text("   spaces   ") == "spaces"
    
    def test_combined_transformations(self):
        """Test that all transformations work together correctly."""
        text = "  Hello, World!  This is a TEST.  "
        expected = "hello world this is a test"
        assert preprocess_text(text) == expected
        
        text = "Special@#$Characters   AND   Multiple123Spaces"
        expected = "specialcharacters and multiple123spaces"
        assert preprocess_text(text) == expected
    
    def test_empty_string(self):
        """Test that empty string returns empty string."""
        assert preprocess_text("") == ""
        assert preprocess_text("   ") == ""
        assert preprocess_text("\t\n") == ""
    
    def test_only_special_characters(self):
        """Test that string with only special characters returns empty."""
        assert preprocess_text("@#$%^&*()") == ""
        assert preprocess_text("!!!???") == ""
        assert preprocess_text(".,;:") == ""
    
    def test_alphanumeric_preserved(self):
        """Test that alphanumeric characters are preserved."""
        assert preprocess_text("abc123xyz789") == "abc123xyz789"
        assert preprocess_text("test 123 data") == "test 123 data"
    
    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        # Unicode characters should be removed (not alphanumeric ASCII)
        assert preprocess_text("café") == "caf"
        assert preprocess_text("naïve") == "nave"
        assert preprocess_text("hello 世界") == "hello"
    
    def test_real_world_examples(self):
        """Test with realistic media descriptions."""
        # Book description
        text = "A thrilling mystery novel set in 1920's Paris!"
        expected = "a thrilling mystery novel set in 1920s paris"
        assert preprocess_text(text) == expected
        
        # TV show description
        text = "An action-packed sci-fi series about time travel & parallel universes."
        expected = "an actionpacked scifi series about time travel parallel universes"
        assert preprocess_text(text) == expected
        
        # Query with punctuation
        text = "Looking for: cozy mystery, coffee shop setting"
        expected = "looking for cozy mystery coffee shop setting"
        assert preprocess_text(text) == expected
    
    def test_idempotence(self):
        """Test that preprocessing is idempotent (applying twice gives same result)."""
        text = "Hello, World! This is a TEST."
        processed_once = preprocess_text(text)
        processed_twice = preprocess_text(processed_once)
        assert processed_once == processed_twice
    
    def test_type_error_on_non_string(self):
        """Test that non-string input raises TypeError."""
        with pytest.raises(TypeError):
            preprocess_text(None)
        
        with pytest.raises(TypeError):
            preprocess_text(123)
        
        with pytest.raises(TypeError):
            preprocess_text(['list'])
    
    def test_consistency_requirement(self):
        """
        Test that preprocessing is consistent for both queries and descriptions.
        This ensures the same text produces the same output regardless of context.
        """
        query = "A cozy mystery in a coffee shop"
        description = "A cozy mystery in a coffee shop"
        
        assert preprocess_text(query) == preprocess_text(description)
        
        # Test with variations
        query_with_punctuation = "A cozy mystery in a coffee shop!"
        description_with_punctuation = "A cozy mystery in a coffee shop."
        
        assert preprocess_text(query_with_punctuation) == preprocess_text(description_with_punctuation)



class TestPreprocessingProperties:
    """
    Property-based tests for text preprocessing.
    
    These tests use Hypothesis to verify universal properties that should hold
    for all possible inputs, ensuring the preprocessing function behaves correctly
    across a wide range of text inputs.
    """
    
    @given(st.text())
    def test_preprocessing_idempotence(self, text: str):
        """
        **Property 1: Preprocessing idempotence**
        
        Test that applying preprocessing twice produces the same result as applying it once.
        This ensures that preprocess_text is idempotent: preprocess_text(preprocess_text(x)) == preprocess_text(x)
        
        This property is critical because:
        1. It ensures preprocessing is stable and doesn't introduce artifacts
        2. It guarantees that preprocessed text can be safely preprocessed again
        3. It validates that all transformations reach a fixed point
        
        **Validates: Requirements 19.1, 19.2, 19.3, 19.4, 19.5**
        - 19.1: Apply same transformations to both queries and descriptions
        - 19.2: Convert all text to lowercase
        - 19.3: Remove special characters except spaces and alphanumeric
        - 19.4: Collapse multiple consecutive spaces to single space
        - 19.5: Remove leading and trailing whitespace
        """
        # Apply preprocessing once
        processed_once = preprocess_text(text)
        
        # Apply preprocessing twice (to the already processed text)
        processed_twice = preprocess_text(processed_once)
        
        # The results should be identical (idempotence property)
        assert processed_once == processed_twice, (
            f"Preprocessing is not idempotent!\n"
            f"Original: {repr(text)}\n"
            f"Processed once: {repr(processed_once)}\n"
            f"Processed twice: {repr(processed_twice)}"
        )
