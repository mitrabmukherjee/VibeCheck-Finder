# Implementation Plan: Sentence-BERT Upgrade

## Overview

This implementation plan upgrades the VibeCheck Finder semantic search system from TF-IDF sparse vectorization to Sentence-BERT dense embeddings. The upgrade will enable true semantic understanding of search queries while maintaining API backward compatibility and system performance.

The implementation follows a phased approach:
1. Create the new SentenceBertVectorizer class
2. Update MLEngine to support both vectorizer types
3. Update FileVectorDatabase for 384-dimensional vectors
4. Create migration and validation scripts
5. Integrate with the FastAPI backend
6. Comprehensive testing and validation

## Tasks

- [ ] 1. Install Sentence-BERT dependencies and create vectorizer class
  - [x] 1.1 Install sentence-transformers library
    - Add sentence-transformers>=2.0.0 to requirements.txt
    - Verify installation and model download capability
    - _Requirements: 1.1_
  
  - [x] 1.2 Create SentenceBertVectorizer class in backend/ml_engine/sentence_bert_vectorizer.py
    - Implement __init__ method with model_name, cache_folder, and device parameters
    - Implement encode method for single and batch text encoding
    - Implement get_embedding_dimension method returning 384
    - Implement save and load methods for model configuration
    - Use all-MiniLM-L6-v2 as default model
    - Enable L2 normalization of embeddings by default
    - _Requirements: 1.2, 1.3, 1.4, 2.1, 2.2, 2.3_
  
  - [ ] 1.3 Write property test for embedding dimensionality invariant
    - **Property 1: Embedding Dimensionality Invariant**
    - **Validates: Requirements 1.4, 2.2, 2.3, 2.5, 3.3, 4.1, 9.3**
    - Use hypothesis with text strategy (min_size=1, max_size=1000)
    - Verify all encoded texts produce exactly 384-dimensional vectors
    - Use max_examples=10
  
  - [ ] 1.4 Write property test for finite embedding values
    - **Property 2: Finite Embedding Values**
    - **Validates: Requirements 9.4**
    - Use hypothesis with text strategy
    - Verify all embedding values are finite (no NaN or infinity)
    - Use max_examples=10
  
  - [ ] 1.5 Write property test for encoding idempotence
    - **Property 3: Encoding Idempotence**
    - **Validates: Requirements 9.5**
    - Use hypothesis with text strategy
    - Verify encoding same text multiple times produces identical embeddings
    - Use np.allclose for floating-point comparison
    - Use max_examples=10

- [ ] 2. Update MLEngine to support both vectorizer types
  - [x] 2.1 Update MLEngine.__init__ to accept vectorizer_type parameter
    - Add vectorizer_type parameter ("tfidf" or "sbert")
    - Add model_name parameter for Sentence-BERT model selection
    - Load appropriate vectorizer based on type
    - Maintain backward compatibility with existing TF-IDF code
    - _Requirements: 2.1, 5.1, 5.5_
  
  - [x] 2.2 Update MLEngine.vectorize_query to route to correct vectorizer
    - Check vectorizer_type and call appropriate encode method
    - Ensure output shape is (1, dimension) for both types
    - Maintain existing error handling and validation
    - _Requirements: 2.2, 2.3, 2.4, 5.3_
  
  - [x] 2.3 Update MLEngine.compute_embeddings to support batch encoding
    - Add batch_size parameter for Sentence-BERT encoding
    - Use batch encoding for efficiency with Sentence-BERT
    - Maintain existing interface for TF-IDF
    - Cache embeddings in corpus_vectors and corpus_ids
    - _Requirements: 3.2, 9.2, 9.3_
  
  - [ ] 2.4 Write unit tests for MLEngine with Sentence-BERT
    - Test initialization with vectorizer_type="sbert"
    - Test vectorize_query produces 384-dimensional vectors
    - Test compute_embeddings with batch processing
    - Test find_similar returns correct results
    - _Requirements: 2.1, 2.2, 5.3_

- [ ] 3. Update FileVectorDatabase for 384-dimensional vectors
  - [x] 3.1 Update FileVectorDatabase to support configurable vector_size
    - Modify __init__ to accept vector_size parameter (default 384 for sbert)
    - Update validation to check vector size matches configuration
    - Ensure backward compatibility with existing 5000-dim TF-IDF vectors
    - _Requirements: 4.1, 4.5_
  
  - [x] 3.2 Add vectorizer_type to embedding metadata
    - Store vectorizer_type ("tfidf" or "sbert") in metadata
    - Store model_version and embedding_date
    - Update insert method to accept and store metadata
    - _Requirements: 4.3, 18.1_
  
  - [ ] 3.3 Write property test for storage round-trip preservation
    - **Property 4: Storage Round-Trip Preservation**
    - **Validates: Requirements 4.4**
    - Use hypothesis to generate random 384-dimensional vectors
    - Verify storing and retrieving preserves vector values
    - Use np.allclose for floating-point comparison
    - Use max_examples=10
  
  - [ ] 3.4 Write property test for ID association preservation
    - **Property 5: ID Association Preservation**
    - **Validates: Requirements 4.3**
    - Use hypothesis to generate random media IDs and vectors
    - Verify storing with ID and retrieving by ID returns correct vector
    - Verify searching with vector returns correct ID
    - Use max_examples=10

- [ ] 4. Create migration script for embedding regeneration
  - [x] 4.1 Create backend/data_pipeline/migrate_to_sbert.py script
    - Implement migrate_to_sbert function with parameters from design
    - Load all media items from PostgreSQL or file-based storage
    - Generate Sentence-BERT embeddings in batches (batch_size=32)
    - Store embeddings in FileVectorDatabase with new vector_size=384
    - Create backup of existing TF-IDF embeddings before migration
    - Track progress and log detailed statistics
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 8.1, 8.2_
  
  - [x] 4.2 Add error handling and recovery to migration script
    - Catch and log errors for individual media items
    - Continue processing remaining items if one fails
    - Generate migration report with success/failure statistics
    - Support dry_run mode for validation without writing
    - _Requirements: 8.3, 10.3_
  
  - [x] 4.3 Implement backup and rollback mechanism
    - Create timestamped backup directory before migration
    - Copy existing vectors.npy, metadata.json, ids.json to backup
    - Implement rollback function to restore from backup
    - Verify backup integrity before proceeding with migration
    - _Requirements: 8.2, 8.3, 8.4, 8.5_
  
  - [ ] 4.4 Write property test for metadata preservation during migration
    - **Property 6: Metadata Preservation During Migration**
    - **Validates: Requirements 3.5**
    - Create test dataset with media items and metadata
    - Run migration on test dataset
    - Verify all metadata (title, description, genre) unchanged
    - Only vectorizer_type and embedding fields should change
    - Use max_examples=10
  
  - [ ] 4.5 Write property test for migration rollback round-trip
    - **Property 9: Migration Rollback Round-Trip**
    - **Validates: Requirements 8.5**
    - Create test dataset with TF-IDF embeddings
    - Run migration to Sentence-BERT
    - Run rollback to TF-IDF
    - Verify search results match original TF-IDF results
    - Use max_examples=10

- [x] 5. Checkpoint - Ensure core components work
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Create validation script for embedding quality
  - [x] 6.1 Create backend/data_pipeline/validate_sbert.py script
    - Implement validate_embeddings function from design
    - Define test queries for semantic understanding validation
    - Compare TF-IDF vs Sentence-BERT results for same queries
    - Generate validation report with quality metrics
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_
  
  - [x] 6.2 Add embedding quality checks to validation script
    - Verify all embeddings have exactly 384 dimensions
    - Verify all embedding values are finite (no NaN or infinity)
    - Test encoding idempotence for sample texts
    - Check similarity scores are in expected range (60-80%)
    - _Requirements: 9.3, 9.4, 9.5, 6.4_
  
  - [x] 6.3 Add semantic understanding tests to validation script
    - Test query: "little girl" → expect results about young girls, children
    - Test query: "romantic comedy" → expect results about love stories with humor
    - Test query: "space adventure" → expect results about sci-fi exploration
    - Verify Sentence-BERT scores higher than TF-IDF for semantic matches
    - Generate comparison report with top-k results for each query
    - _Requirements: 6.1, 6.2, 6.3, 6.5_
  
  - [ ] 6.4 Write property test for semantic improvement over TF-IDF
    - **Property 8: Semantic Improvement Over TF-IDF**
    - **Validates: Requirements 6.5**
    - Use hypothesis to generate test queries
    - Compare average top-k similarity scores for TF-IDF vs Sentence-BERT
    - Verify Sentence-BERT average score >= TF-IDF average score
    - Use max_examples=10
  
  - [ ] 6.5 Write property test for results sorted by similarity score
    - **Property 7: Results Sorted by Similarity Score**
    - **Validates: Requirements 5.4**
    - Use hypothesis to generate test queries
    - Verify returned results are sorted in descending order by score
    - Check score[i] >= score[i+1] for all adjacent pairs
    - Use max_examples=10

- [ ] 7. Update FastAPI backend for Sentence-BERT integration
  - [x] 7.1 Update backend/main.py to initialize MLEngine with vectorizer_type
    - Add VECTORIZER_TYPE environment variable (default: "sbert")
    - Add SBERT_MODEL_NAME environment variable (default: "all-MiniLM-L6-v2")
    - Initialize MLEngine with vectorizer_type from environment
    - Update FileVectorDatabase initialization with vector_size=384 for sbert
    - _Requirements: 2.1, 5.1, 5.5_
  
  - [x] 7.2 Ensure API endpoints maintain backward compatibility
    - Verify /recommend endpoint request format unchanged
    - Verify /recommend endpoint response format unchanged
    - Test pagination, filtering, and sorting still work
    - Ensure similarity scores are returned as percentages (0-100)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  
  - [ ] 7.3 Write integration tests for end-to-end search flow
    - Test submitting query via /recommend endpoint
    - Verify query is encoded with Sentence-BERT
    - Verify search returns results ranked by score
    - Verify response format matches specification
    - Test with sample queries from requirements
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ] 8. Add error handling for edge cases
  - [x] 8.1 Add validation for empty queries
    - Check for empty string before processing
    - Return HTTP 400 with descriptive error message
    - _Requirements: 10.1_
  
  - [x] 8.2 Add handling for long queries (>512 tokens)
    - Detect queries exceeding 512 tokens
    - Truncate to first 512 tokens
    - Log warning for truncated queries
    - Process normally without user-visible error
    - _Requirements: 10.2_
  
  - [x] 8.3 Add error handling for model loading failures
    - Catch exceptions during SentenceTransformer initialization
    - Log detailed error with model name and cache path
    - Return HTTP 503 Service Unavailable
    - Provide user-friendly error message
    - _Requirements: 10.3_
  
  - [x] 8.4 Add error handling for database unavailability
    - Catch connection exceptions in FileVectorDatabase methods
    - Log error with storage path details
    - Return HTTP 503 Service Unavailable
    - Provide user-friendly error message
    - _Requirements: 10.4_
  
  - [x] 8.5 Add handling for special characters and non-ASCII text
    - Test with emoji, CJK characters, accented characters
    - Ensure Sentence-BERT handles Unicode natively
    - Verify no errors during encoding
    - _Requirements: 10.5_
  
  - [ ]* 8.6 Write unit tests for edge cases
    - Test empty query returns error
    - Test very long query is truncated
    - Test special characters are handled correctly
    - Test non-ASCII text (emoji, CJK) is processed correctly
    - _Requirements: 10.1, 10.2, 10.5_

- [ ] 9. Performance optimization and caching
  - [x] 9.1 Implement model caching in SentenceBertVectorizer
    - Load model once during initialization
    - Cache model in memory for reuse
    - Avoid repeated model loading on each request
    - _Requirements: 7.4_
  
  - [x] 9.2 Optimize batch encoding for migration
    - Use batch_size=32 for efficient encoding
    - Show progress bar during migration
    - Log encoding speed (items/second)
    - _Requirements: 3.2, 7.2_
  
  - [ ]* 9.3 Write performance tests for search latency
    - Measure end-to-end search time for /recommend endpoint
    - Verify total latency < 200ms
    - Measure query encoding time < 50ms
    - Measure similarity search time < 100ms
    - Test with full 5,832 item dataset
    - _Requirements: 7.1, 7.2, 7.3_

- [x] 10. Final checkpoint - Run full validation
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Documentation and deployment preparation
  - [x] 11.1 Update backend/.env.example with new environment variables
    - Add VECTORIZER_TYPE with default "sbert"
    - Add SBERT_MODEL_NAME with default "all-MiniLM-L6-v2"
    - Add VECTOR_SIZE with default 384
    - Document migration process
  
  - [x] 11.2 Create migration guide document
    - Document step-by-step migration process
    - Include backup and rollback instructions
    - Provide validation checklist
    - Include troubleshooting tips
  
  - [x] 11.3 Update README.md with Sentence-BERT information
    - Document new semantic search capabilities
    - Explain difference between TF-IDF and Sentence-BERT
    - Provide example queries demonstrating semantic understanding
    - Document expected similarity score ranges

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using hypothesis with max_examples=10
- Unit tests validate specific examples and edge cases
- The system uses file-based storage (FileVectorDatabase), not Docker/Qdrant
- Migration script must handle 5,832 Netflix media items
- All property-based tests should be tagged with: **Feature: sentence-bert-upgrade, Property {number}: {property_text}**
- Maintain backward compatibility throughout implementation
- Performance target: <200ms search latency, <50ms encoding time
