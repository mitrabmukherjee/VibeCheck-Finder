# Requirements Document: Semantic Media Engine

## Introduction

The Semantic Media Engine is a content-based recommendation system that enables users to discover books and TV shows through natural language queries. The system vectorizes media descriptions and user queries, then uses similarity matching to return relevant recommendations. This document specifies the functional requirements derived from the technical design.

## Glossary

- **System**: The complete Semantic Media Engine application
- **Frontend**: The Next.js web interface component
- **Backend**: The FastAPI server component
- **ML_Engine**: The machine learning vectorization and similarity computation component
- **Vector_DB**: The vector database storing embeddings
- **PostgreSQL**: The relational database storing structured metadata
- **Data_Pipeline**: The component that ingests and processes media datasets
- **Query**: A natural language search string provided by the user
- **Embedding**: A numerical vector representation of text
- **Similarity_Score**: A numerical value (0.0 to 1.0) indicating how similar two items are
- **Media_Item**: A book or TV show with associated metadata
- **Vectorizer**: The TF-IDF model that transforms text into embeddings

## Requirements

### Requirement 1: User Query Processing

**User Story:** As a user, I want to enter natural language queries, so that I can find books and TV shows that match my interests without using specific keywords.

#### Acceptance Criteria

1. WHEN a user submits a query, THE Frontend SHALL send the query to the Backend via HTTP POST
2. WHEN a query is received, THE Backend SHALL validate that the query is non-empty and contains 1000 or fewer characters
3. WHEN a query is invalid, THE Backend SHALL return an error response with a descriptive message
4. WHEN a valid query is received, THE Backend SHALL forward it to the ML_Engine for vectorization
5. WHEN the Frontend sends a request, THE System SHALL update the loading state to indicate processing

### Requirement 2: Text Vectorization

**User Story:** As a developer, I want queries and descriptions to be converted into numerical vectors, so that I can perform mathematical similarity comparisons.

#### Acceptance Criteria

1. WHEN the ML_Engine receives a query, THE ML_Engine SHALL preprocess the text by converting to lowercase, removing special characters, and normalizing whitespace
2. WHEN text is preprocessed, THE ML_Engine SHALL transform it into an embedding vector using the trained TF-IDF vectorizer
3. WHEN a vector is generated, THE ML_Engine SHALL ensure all values are finite floats
4. WHEN a vector is generated, THE ML_Engine SHALL ensure the vector has non-zero norm
5. THE ML_Engine SHALL load the pre-trained vectorizer model at initialization

### Requirement 3: Similarity Search

**User Story:** As a user, I want the system to find media items similar to my query, so that I receive relevant recommendations.

#### Acceptance Criteria

1. WHEN the ML_Engine has a query vector, THE ML_Engine SHALL search the Vector_DB for similar embeddings
2. WHEN performing similarity search, THE ML_Engine SHALL use cosine similarity as the default metric
3. WHEN similarity scores are computed, THE ML_Engine SHALL return scores in the range 0.0 to 1.0
4. WHEN multiple matches are found, THE ML_Engine SHALL return the top-k most similar items sorted by score descending
5. WHEN the top_k parameter is provided, THE System SHALL validate it is between 1 and 50

### Requirement 4: Metadata Retrieval

**User Story:** As a user, I want to see detailed information about recommended items, so that I can make informed decisions about what to read or watch.

#### Acceptance Criteria

1. WHEN the ML_Engine identifies similar media items, THE Backend SHALL retrieve full metadata from PostgreSQL using the media IDs
2. WHEN retrieving metadata, THE PostgreSQL SHALL return title, description, media_type, and all available metadata fields
3. WHEN metadata is retrieved, THE Backend SHALL merge it with similarity scores to create complete recommendation objects
4. WHEN all media IDs exist in the database, THE System SHALL return metadata for all requested IDs
5. WHEN a media ID does not exist, THE System SHALL handle the error gracefully and log the missing ID

### Requirement 5: Response Formatting

**User Story:** As a frontend developer, I want consistent JSON responses, so that I can reliably display recommendations to users.

#### Acceptance Criteria

1. WHEN the Backend completes processing, THE Backend SHALL return a JSON response containing a results array
2. WHEN returning results, THE Backend SHALL include query_time_ms indicating processing duration
3. WHEN formatting recommendations, THE Backend SHALL include id, title, description, metadata, and similarity_score for each item
4. WHEN returning results, THE Backend SHALL ensure they are sorted by similarity_score in descending order
5. WHEN no results are found, THE Backend SHALL return an empty results array with a 200 status code

### Requirement 6: Frontend Display

**User Story:** As a user, I want to see recommendations displayed clearly, so that I can easily browse and select items of interest.

#### Acceptance Criteria

1. WHEN the Frontend receives recommendations, THE Frontend SHALL display them as cards with title, description, and metadata
2. WHEN displaying recommendations, THE Frontend SHALL show the similarity score for each item
3. WHEN loading recommendations, THE Frontend SHALL display a loading indicator
4. WHEN an error occurs, THE Frontend SHALL display an error message to the user
5. WHEN recommendations are displayed, THE Frontend SHALL clear the loading state

### Requirement 7: Data Ingestion

**User Story:** As a system administrator, I want to load media datasets into the system, so that users have content to search through.

#### Acceptance Criteria

1. WHEN the Data_Pipeline starts, THE Data_Pipeline SHALL load the dataset from the specified source path
2. WHEN loading data, THE Data_Pipeline SHALL validate that required columns (title, description) are present
3. WHEN data is loaded, THE Data_Pipeline SHALL clean and normalize text fields
4. WHEN cleaning data, THE Data_Pipeline SHALL remove rows with null or empty title or description fields
5. WHEN the dataset is empty after cleaning, THE Data_Pipeline SHALL raise an error

### Requirement 8: Vectorizer Training

**User Story:** As a developer, I want the system to train a vectorizer on the media corpus, so that queries and descriptions can be compared in the same vector space.

#### Acceptance Criteria

1. WHEN processing a new dataset, THE Data_Pipeline SHALL check if a trained vectorizer exists
2. IF no vectorizer exists, THEN THE Data_Pipeline SHALL train a new TF-IDF vectorizer on all media descriptions
3. WHEN training a vectorizer, THE ML_Engine SHALL ensure the corpus contains at least one non-empty description
4. WHEN a vectorizer is trained, THE Data_Pipeline SHALL save it to disk for future use
5. IF a vectorizer exists, THEN THE Data_Pipeline SHALL load the existing vectorizer

### Requirement 9: Embedding Storage

**User Story:** As a developer, I want media embeddings stored in a vector database, so that similarity searches can be performed efficiently.

#### Acceptance Criteria

1. WHEN the Data_Pipeline generates embeddings, THE Data_Pipeline SHALL store them in the Vector_DB with the corresponding media ID
2. WHEN storing embeddings, THE System SHALL ensure each embedding has the correct dimensionality
3. WHEN storing embeddings, THE System SHALL ensure all vector values are finite floats
4. WHEN processing in batches, THE Data_Pipeline SHALL verify all embeddings in a batch are stored before proceeding
5. WHEN an embedding already exists for a media ID, THE Vector_DB SHALL update it with the new vector

### Requirement 10: Metadata Storage

**User Story:** As a developer, I want structured metadata stored in PostgreSQL, so that detailed information can be retrieved efficiently.

#### Acceptance Criteria

1. WHEN the Data_Pipeline processes media items, THE Data_Pipeline SHALL store metadata in PostgreSQL
2. WHEN storing metadata, THE PostgreSQL SHALL validate that each item has a unique ID
3. WHEN storing metadata, THE PostgreSQL SHALL ensure title is non-empty and at most 500 characters
4. WHEN storing metadata, THE PostgreSQL SHALL ensure description is non-empty and at most 5000 characters
5. WHEN storing metadata, THE PostgreSQL SHALL validate that media_type is either "book" or "tv_show"

### Requirement 11: Batch Processing

**User Story:** As a system administrator, I want large datasets processed in batches, so that memory usage remains manageable.

#### Acceptance Criteria

1. WHEN processing a dataset, THE Data_Pipeline SHALL divide it into batches of configurable size
2. WHEN processing batches, THE Data_Pipeline SHALL process each batch sequentially
3. WHEN a batch is processed, THE Data_Pipeline SHALL verify all items are stored before proceeding to the next batch
4. WHEN all batches are processed, THE Data_Pipeline SHALL verify the total count matches the input dataset size
5. IF a batch fails to process, THEN THE Data_Pipeline SHALL log the error and halt processing

### Requirement 12: Input Validation

**User Story:** As a developer, I want all inputs validated, so that the system handles invalid data gracefully.

#### Acceptance Criteria

1. WHEN validating a query, THE Backend SHALL reject queries longer than 1000 characters
2. WHEN validating top_k, THE Backend SHALL reject values less than 1 or greater than 50
3. WHEN validating year metadata, THE System SHALL reject years before 1800 or more than 2 years in the future
4. WHEN validating rating metadata, THE System SHALL reject ratings outside the range 0 to 10
5. WHEN validation fails, THE System SHALL return a descriptive error message

### Requirement 13: Error Handling

**User Story:** As a user, I want errors handled gracefully, so that I receive helpful feedback when something goes wrong.

#### Acceptance Criteria

1. WHEN a network error occurs, THE Frontend SHALL display a user-friendly error message
2. WHEN the Backend encounters an error, THE Backend SHALL log the error details
3. WHEN the Backend encounters an error, THE Backend SHALL return an appropriate HTTP status code
4. WHEN the Vector_DB is unavailable, THE Backend SHALL return a 503 Service Unavailable response
5. WHEN PostgreSQL is unavailable, THE Backend SHALL return a 503 Service Unavailable response

### Requirement 14: CORS Configuration

**User Story:** As a frontend developer, I want the API to accept requests from the Next.js origin, so that the frontend can communicate with the backend.

#### Acceptance Criteria

1. WHEN the Backend starts, THE Backend SHALL configure CORS middleware
2. WHEN configuring CORS, THE Backend SHALL allow requests from the Next.js origin
3. WHEN a preflight request is received, THE Backend SHALL respond with appropriate CORS headers
4. WHEN a cross-origin request is received, THE Backend SHALL include CORS headers in the response
5. THE Backend SHALL allow POST requests to the /recommend endpoint

### Requirement 15: Optional Filtering

**User Story:** As a user, I want to filter recommendations by metadata, so that I can narrow results to specific categories.

#### Acceptance Criteria

1. WHERE filters are provided, THE Backend SHALL apply them to the recommendation results
2. WHERE a media_type filter is provided, THE Backend SHALL return only items matching that type
3. WHERE a genre filter is provided, THE Backend SHALL return only items matching that genre
4. WHERE year range filters are provided, THE Backend SHALL return only items within that range
5. WHERE a min_rating filter is provided, THE Backend SHALL return only items with rating greater than or equal to the minimum

### Requirement 16: Performance Monitoring

**User Story:** As a developer, I want to track query performance, so that I can identify and optimize slow operations.

#### Acceptance Criteria

1. WHEN processing a query, THE Backend SHALL measure the total processing time
2. WHEN returning a response, THE Backend SHALL include query_time_ms in the response
3. WHEN processing a query, THE Backend SHALL log request metrics
4. WHEN logging metrics, THE Backend SHALL include timestamp, query length, and processing time
5. THE Backend SHALL log all requests to the /recommend endpoint

### Requirement 17: Data Consistency

**User Story:** As a developer, I want embeddings and metadata to remain synchronized, so that all media items can be fully retrieved.

#### Acceptance Criteria

1. WHEN storing a media item, THE Data_Pipeline SHALL store both the embedding and metadata
2. WHEN an embedding is stored, THE System SHALL ensure the corresponding metadata exists in PostgreSQL
3. WHEN metadata is stored, THE System SHALL ensure the corresponding embedding exists in Vector_DB
4. WHEN retrieving recommendations, THE System SHALL verify all returned media IDs have metadata
5. IF metadata is missing for a media ID, THEN THE System SHALL log the inconsistency

### Requirement 18: Model Versioning

**User Story:** As a developer, I want to track which vectorizer version generated each embedding, so that I can manage model updates.

#### Acceptance Criteria

1. WHEN storing an embedding, THE Vector_DB SHALL include the model_version in the metadata
2. WHEN training a new vectorizer, THE Data_Pipeline SHALL assign it a unique version identifier
3. WHEN loading a vectorizer, THE ML_Engine SHALL verify the model version matches the expected version
4. WHEN embeddings exist with different model versions, THE System SHALL log a warning
5. THE System SHALL store the current model_version in the vectorizer metadata

### Requirement 19: Text Preprocessing Consistency

**User Story:** As a developer, I want text preprocessing to be consistent between training and inference, so that vectorization produces accurate results.

#### Acceptance Criteria

1. WHEN preprocessing text, THE ML_Engine SHALL apply the same transformations to both queries and descriptions
2. WHEN preprocessing text, THE ML_Engine SHALL convert all text to lowercase
3. WHEN preprocessing text, THE ML_Engine SHALL remove special characters except spaces and alphanumeric characters
4. WHEN preprocessing text, THE ML_Engine SHALL collapse multiple consecutive spaces to a single space
5. WHEN preprocessing text, THE ML_Engine SHALL remove leading and trailing whitespace

### Requirement 20: Result Uniqueness

**User Story:** As a user, I want each recommendation to appear only once, so that I don't see duplicate results.

#### Acceptance Criteria

1. WHEN returning recommendations, THE System SHALL ensure no duplicate media IDs are present
2. WHEN the Vector_DB returns duplicate IDs, THE ML_Engine SHALL deduplicate them
3. WHEN deduplicating, THE ML_Engine SHALL keep the entry with the highest similarity score
4. WHEN merging scores with metadata, THE Backend SHALL verify each media ID appears exactly once
5. THE System SHALL return at most top_k unique recommendations
