"""
Text preprocessing module for the Semantic Media Engine.

This module provides text preprocessing functions to ensure consistent
text normalization for both training and inference phases.
"""

import re


def preprocess_text(text: str) -> str:
    """
    Clean and normalize text for vectorization.
    
    This function applies consistent preprocessing transformations to ensure
    that both training descriptions and user queries are processed identically.
    
    Transformations applied:
    1. Convert to lowercase
    2. Remove special characters (keep only alphanumeric and spaces)
    3. Collapse multiple consecutive spaces to single space
    4. Remove leading and trailing whitespace
    
    Args:
        text: Input text string (may be empty)
    
    Returns:
        Cleaned and normalized text string
    
    Examples:
        >>> preprocess_text("Hello World!")
        'hello world'
        >>> preprocess_text("Multiple   Spaces")
        'multiple spaces'
        >>> preprocess_text("Special@#$Characters123")
        'specialcharacters123'
        >>> preprocess_text("  Leading and Trailing  ")
        'leading and trailing'
    
    Requirements:
        - 2.1: Preprocess text by converting to lowercase, removing special chars, normalizing whitespace
        - 19.1: Apply same transformations to both queries and descriptions
        - 19.2: Convert all text to lowercase
        - 19.3: Remove special characters except spaces and alphanumeric
        - 19.4: Collapse multiple consecutive spaces to single space
        - 19.5: Remove leading and trailing whitespace
    """
    if not isinstance(text, str):
        raise TypeError(f"Expected str, got {type(text).__name__}")
    
    # Step 1: Convert to lowercase
    text = text.lower()
    
    # Step 2: Remove special characters (keep only alphanumeric and spaces)
    # This regex keeps letters, numbers, and spaces
    text = re.sub(r'[^a-z0-9\s]', '', text)
    
    # Step 3: Collapse multiple consecutive spaces to single space
    text = re.sub(r'\s+', ' ', text)
    
    # Step 4: Remove leading and trailing whitespace
    text = text.strip()
    
    return text
