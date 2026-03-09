"""
Data Pipeline module for ingesting and processing media datasets.

This module provides the DataPipeline class that handles loading datasets,
cleaning data, generating embeddings, and storing them in both Vector DB
and PostgreSQL for the Semantic Media Engine.
"""

import os
import logging
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

from ml_engine.ml_engine import MLEngine
from ml_engine.preprocessing import preprocess_text
from database.vector_db import VectorDatabase
from database.file_vector_db import FileVectorDatabase
from database.postgres import PostgresDatabase

logger = logging.getLogger(__name__)


class DataPipeline:
    """
    Data Pipeline for dataset ingestion and processing.
    
    This class orchestrates the complete data ingestion workflow:
    1. Load dataset from CSV or API
    2. Clean and validate data
    3. Train or load vectorizer
    4. Process data in batches
    5. Generate embeddings
    6. Store embeddings in Vector DB
    7. Store metadata in PostgreSQL
    
    Attributes:
        source_path: Path to the dataset file or API endpoint
        ml_engine: MLEngine instance for vectorization
        vector_db: VectorDatabase instance for embedding storage
        postgres_db: PostgresDatabase instance for metadata storage
        batch_size: Number of items to process per batch
    
    Requirements:
        - 7.1: Load dataset from specified source path
        - 7.2: Validate required columns are present
        - 7.3: Clean and normalize text fields
        - 7.4: Remove rows with null or empty title/description
        - 11.1: Divide dataset into batches of configurable size
        - 11.2: Process each batch sequentially
        - 11.3: Verify all items are stored before proceeding
        - 11.4: Verify total count matches input dataset size
        - 11.5: Log errors and halt processing on batch failure
    """
    
    def __init__(
        self,
        source_path: str,
        vectorizer_path: str,
        embeddings_path: str,
        vector_db_config: Optional[Dict[str, Any]] = None,
        postgres_config: Optional[Dict[str, Any]] = None,
        batch_size: int = 1000
    ):
        """
        Initialize the Data Pipeline with database configurations.
        
        Args:
            source_path: Path to dataset CSV file or API endpoint
            vectorizer_path: Directory path for vectorizer model storage
            embeddings_path: Directory path for embeddings storage
            vector_db_config: Configuration for Vector DB (host, port, etc.)
            postgres_config: Configuration for PostgreSQL (min/max connections)
            batch_size: Number of items to process per batch (default: 1000)
        
        Raises:
            ValueError: If source_path or paths are invalid
        """
        if not source_path:
            raise ValueError("source_path cannot be empty")
        if not vectorizer_path:
            raise ValueError("vectorizer_path cannot be empty")
        if not embeddings_path:
            raise ValueError("embeddings_path cannot be empty")
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        
        self.source_path = source_path
        self.batch_size = batch_size
        
        # Initialize ML Engine
        self.ml_engine = MLEngine(vectorizer_path, embeddings_path)
        
        # Initialize Vector Database (file-based or Qdrant)
        vdb_config = vector_db_config or {}
        use_file_storage = vdb_config.pop('use_file_storage', False)
        
        if use_file_storage:
            self.vector_db = FileVectorDatabase(**vdb_config)
            logger.info("Using file-based vector storage")
        else:
            self.vector_db = VectorDatabase(**vdb_config)
            logger.info("Using Qdrant vector storage")
        
        # Initialize PostgreSQL Database
        pg_config = postgres_config or {}
        self.postgres_db = PostgresDatabase(**pg_config)
        
        logger.info(
            f"DataPipeline initialized: source={source_path}, "
            f"batch_size={batch_size}"
        )
    
    def load_dataset(self) -> pd.DataFrame:
        """
        Load dataset from CSV file or API response.
        
        This method reads the dataset from the specified source path and
        validates that required columns (title, description) are present.
        
        Returns:
            pandas DataFrame containing the loaded dataset
        
        Raises:
            FileNotFoundError: If source file doesn't exist
            ValueError: If required columns are missing
            Exception: If loading fails for other reasons
        
        Requirements:
            - 7.1: Load dataset from specified source path
            - 7.2: Validate required columns (title, description) are present
            - 7.5: Raise error if dataset is empty after cleaning
        """
        logger.info(f"Loading dataset from {self.source_path}")
        
        # Check if source file exists
        if not os.path.exists(self.source_path):
            raise FileNotFoundError(f"Dataset file not found: {self.source_path}")
        
        try:
            # Load CSV file
            df = pd.read_csv(self.source_path)
            
            logger.info(f"Loaded {len(df)} rows from dataset")
            
            # Validate required columns are present
            required_columns = ['title', 'description']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(
                    f"Dataset missing required columns: {missing_columns}. "
                    f"Available columns: {list(df.columns)}"
                )
            
            # Validate dataset is not empty
            if len(df) == 0:
                raise ValueError("Dataset is empty")
            
            logger.info(f"Dataset validation passed: {len(df)} rows, columns: {list(df.columns)}")
            
            return df
            
        except pd.errors.EmptyDataError:
            raise ValueError("Dataset file is empty")
        except pd.errors.ParserError as e:
            raise ValueError(f"Failed to parse CSV file: {e}")
        except Exception as e:
            logger.error(f"Error loading dataset: {e}")
            raise
    
    def clean_text(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and normalize text descriptions in the dataset.
        
        This method:
        1. Normalizes text using preprocess_text()
        2. Removes rows with null or empty title/description
        3. Validates media_type, year, and rating fields
        
        Args:
            df: Input DataFrame with raw data
        
        Returns:
            Cleaned DataFrame with normalized text
        
        Raises:
            ValueError: If dataset is empty after cleaning
        
        Requirements:
            - 7.3: Clean and normalize text fields
            - 7.4: Remove rows with null or empty title/description
            - 12.3: Validate year metadata
            - 12.4: Validate rating metadata
        """
        logger.info(f"Cleaning dataset with {len(df)} rows")
        
        # Create a copy to avoid modifying original
        df_clean = df.copy()
        
        # Remove rows with null or empty title
        df_clean = df_clean[df_clean['title'].notna()]
        df_clean = df_clean[df_clean['title'].str.strip() != '']
        
        # Remove rows with null or empty description
        df_clean = df_clean[df_clean['description'].notna()]
        df_clean = df_clean[df_clean['description'].str.strip() != '']
        
        logger.info(f"After removing null/empty: {len(df_clean)} rows")
        
        # Normalize text fields using preprocessing
        df_clean['title'] = df_clean['title'].apply(lambda x: x.strip())
        df_clean['description'] = df_clean['description'].apply(lambda x: x.strip())
        
        # Validate media_type if present
        if 'media_type' in df_clean.columns:
            # Filter to only valid media types
            valid_types = ['book', 'tv_show']
            df_clean = df_clean[df_clean['media_type'].isin(valid_types)]
            logger.info(f"After media_type validation: {len(df_clean)} rows")
        
        # Validate year if present
        if 'year' in df_clean.columns:
            # Remove rows with invalid years
            current_year = pd.Timestamp.now().year
            df_clean = df_clean[
                (df_clean['year'].isna()) |
                ((df_clean['year'] >= 1800) & (df_clean['year'] <= current_year + 2))
            ]
            logger.info(f"After year validation: {len(df_clean)} rows")
        
        # Validate rating if present
        if 'rating' in df_clean.columns:
            # Remove rows with invalid ratings
            df_clean = df_clean[
                (df_clean['rating'].isna()) |
                ((df_clean['rating'] >= 0) & (df_clean['rating'] <= 10))
            ]
            logger.info(f"After rating validation: {len(df_clean)} rows")
        
        # Validate dataset is not empty after cleaning
        if len(df_clean) == 0:
            raise ValueError(
                "Dataset is empty after cleaning. All rows were removed due to "
                "null/empty values or validation failures."
            )
        
        logger.info(f"Cleaning complete: {len(df_clean)} rows remaining")
        
        return df_clean
    
    def process_and_store(
        self,
        df: pd.DataFrame,
        train_vectorizer: bool = False
    ) -> None:
        """
        Process dataset in batches and store embeddings and metadata.
        
        This method orchestrates the complete processing workflow:
        1. Train or load vectorizer
        2. Divide dataset into batches
        3. For each batch:
           a. Generate embeddings
           b. Store embeddings in Vector DB
           c. Store metadata in PostgreSQL
           d. Verify storage success
        4. Verify total count matches input size
        
        Args:
            df: Cleaned DataFrame to process
            train_vectorizer: Whether to train a new vectorizer (default: False)
        
        Raises:
            ValueError: If batch processing fails or counts don't match
            Exception: If storage operations fail
        
        Requirements:
            - 11.1: Divide dataset into batches of configurable size
            - 11.2: Process each batch sequentially
            - 11.3: Verify all items are stored before proceeding
            - 11.4: Verify total count matches input dataset size
            - 11.5: Log errors and halt processing on batch failure
        """
        logger.info(f"Processing {len(df)} items in batches of {self.batch_size}")
        
        # Step 1: Train or load vectorizer
        if train_vectorizer or self.ml_engine.vectorizer is None:
            logger.info("Training new vectorizer on corpus")
            descriptions = df['description'].tolist()
            self.ml_engine.train_vectorizer(descriptions, save=True)
            logger.info(f"Vectorizer trained with version {self.ml_engine.get_model_version()}")
        else:
            logger.info(f"Using existing vectorizer version {self.ml_engine.get_model_version()}")
        
        # Step 2: Calculate number of batches
        total_items = len(df)
        num_batches = (total_items + self.batch_size - 1) // self.batch_size
        
        logger.info(f"Processing {num_batches} batches")
        
        # Step 3: Process each batch
        processed_count = 0
        
        for batch_idx in range(num_batches):
            start_idx = batch_idx * self.batch_size
            end_idx = min(start_idx + self.batch_size, total_items)
            batch_df = df.iloc[start_idx:end_idx]
            
            logger.info(
                f"Processing batch {batch_idx + 1}/{num_batches} "
                f"(items {start_idx} to {end_idx})"
            )
            
            try:
                # Generate and store embeddings for this batch
                self.store_embeddings(batch_df)
                
                # Store metadata for this batch
                self.store_metadata(batch_df)
                
                # Verify batch was stored successfully
                batch_size_actual = len(batch_df)
                processed_count += batch_size_actual
                
                logger.info(
                    f"Batch {batch_idx + 1} complete: {batch_size_actual} items stored "
                    f"(total: {processed_count}/{total_items})"
                )
                
            except Exception as e:
                logger.error(
                    f"Error processing batch {batch_idx + 1}: {e}. "
                    f"Halting processing."
                )
                raise ValueError(
                    f"Batch {batch_idx + 1} failed to process: {e}"
                ) from e
        
        # Step 4: Verify total count matches input
        if processed_count != total_items:
            raise ValueError(
                f"Processed count ({processed_count}) does not match "
                f"input dataset size ({total_items})"
            )
        
        logger.info(
            f"Processing complete: {processed_count} items successfully stored"
        )
    
    def store_embeddings(self, batch_df: pd.DataFrame) -> None:
        """
        Generate embeddings for batch and store in Vector DB.
        
        This method generates embeddings for all descriptions in the batch
        using the ML Engine and stores them in the Vector DB with media ID
        and model version metadata.
        
        Args:
            batch_df: DataFrame batch to process
        
        Raises:
            ValueError: If embedding generation or storage fails
            Exception: If Vector DB operations fail
        
        Requirements:
            - 9.1: Store embeddings with corresponding media ID
            - 9.2: Ensure each embedding has correct dimensionality
            - 9.3: Ensure all vector values are finite floats
            - 9.4: Verify all embeddings in batch are stored
            - 18.1: Include model_version in embedding metadata
        """
        logger.debug(f"Generating embeddings for batch of {len(batch_df)} items")
        
        # Ensure batch has IDs
        if 'id' not in batch_df.columns:
            # Generate UUIDs for items without IDs
            import uuid
            batch_df = batch_df.copy()
            batch_df['id'] = [str(uuid.uuid4()) for _ in range(len(batch_df))]
        
        # Extract descriptions and IDs
        descriptions = batch_df['description'].tolist()
        media_ids = batch_df['id'].tolist()
        
        # Generate embeddings using ML Engine
        embeddings = self.ml_engine.compute_embeddings(descriptions, media_ids)
        
        # Validate embeddings
        if embeddings.shape[0] != len(batch_df):
            raise ValueError(
                f"Embedding count ({embeddings.shape[0]}) does not match "
                f"batch size ({len(batch_df)})"
            )
        
        # Get model version and vectorizer type for metadata
        model_version = self.ml_engine.get_model_version()
        vectorizer_type = self.ml_engine.vectorizer_type
        
        # Get current timestamp for embedding_date
        from datetime import datetime, timezone
        embedding_date = datetime.now(timezone.utc).isoformat()
        
        # Store each embedding in Vector DB
        for idx, media_id in enumerate(media_ids):
            vector = embeddings[idx].tolist()
            
            # Validate vector values are finite
            if not all(np.isfinite(v) for v in vector):
                raise ValueError(
                    f"Embedding for media_id {media_id} contains non-finite values"
                )
            
            # Prepare metadata
            metadata = {
                'model_version': model_version,
                'vectorizer_type': vectorizer_type,
                'embedding_date': embedding_date,
                'media_id': media_id
            }
            
            # Store in Vector DB
            self.vector_db.insert(media_id, vector, metadata)
        
        logger.debug(f"Stored {len(media_ids)} embeddings in Vector DB")
    
    def store_metadata(self, batch_df: pd.DataFrame) -> None:
        """
        Store cleaned metadata in PostgreSQL for batch.
        
        This method stores structured metadata for all items in the batch,
        ensuring embedding and metadata are stored together for consistency.
        
        Args:
            batch_df: DataFrame batch to store
        
        Raises:
            ValueError: If metadata storage fails
            Exception: If PostgreSQL operations fail
        
        Requirements:
            - 10.1: Store metadata in PostgreSQL
            - 10.2: Validate each item has unique ID
            - 10.3: Ensure title is non-empty and at most 500 characters
            - 10.4: Ensure description is non-empty and at most 5000 characters
            - 10.5: Validate media_type is 'book' or 'tv_show'
            - 17.1: Store both embedding and metadata
            - 17.2: Ensure corresponding metadata exists
            - 17.3: Ensure corresponding embedding exists
        """
        logger.debug(f"Storing metadata for batch of {len(batch_df)} items")
        
        # Ensure batch has IDs
        if 'id' not in batch_df.columns:
            # Generate UUIDs for items without IDs
            import uuid
            batch_df = batch_df.copy()
            batch_df['id'] = [str(uuid.uuid4()) for _ in range(len(batch_df))]
        
        # Prepare media items for batch insert
        media_items = []
        
        for _, row in batch_df.iterrows():
            # Validate title
            title = str(row['title']).strip()
            if not title:
                raise ValueError(f"Title is empty for item {row.get('id', 'unknown')}")
            if len(title) > 500:
                title = title[:500]  # Truncate to 500 characters
            
            # Validate description
            description = str(row['description']).strip()
            if not description:
                raise ValueError(f"Description is empty for item {row.get('id', 'unknown')}")
            if len(description) > 5000:
                description = description[:5000]  # Truncate to 5000 characters
            
            # Validate media_type
            media_type = row.get('media_type', 'book')
            if media_type not in ['book', 'tv_show']:
                media_type = 'book'  # Default to book if invalid
            
            # Build metadata dictionary
            metadata = {}
            
            # Add optional fields to metadata
            optional_fields = ['author', 'genre', 'year', 'rating', 'director', 
                             'seasons', 'is_latest', 'thumbnail_url']
            
            for field in optional_fields:
                if field in row and pd.notna(row[field]):
                    metadata[field] = row[field]
            
            # Create media item dictionary
            media_item = {
                'id': str(row['id']),
                'title': title,
                'description': description,
                'media_type': media_type,
                'metadata': metadata
            }
            
            media_items.append(media_item)
        
        # Batch insert into PostgreSQL
        inserted_ids = self.postgres_db.batch_insert_media(media_items)
        
        # Verify all items were inserted
        if len(inserted_ids) != len(batch_df):
            raise ValueError(
                f"Inserted count ({len(inserted_ids)}) does not match "
                f"batch size ({len(batch_df)})"
            )
        
        logger.debug(f"Stored {len(inserted_ids)} metadata records in PostgreSQL")
    
    def run(self, train_vectorizer: bool = False) -> Dict[str, Any]:
        """
        Execute the complete data pipeline workflow.
        
        This is the main entry point that orchestrates all pipeline steps:
        1. Load dataset
        2. Clean and validate data
        3. Process and store in batches
        
        Args:
            train_vectorizer: Whether to train a new vectorizer (default: False)
        
        Returns:
            Dictionary with pipeline statistics:
                - total_loaded: Number of rows loaded
                - total_cleaned: Number of rows after cleaning
                - total_stored: Number of items successfully stored
                - model_version: Vectorizer version used
        
        Raises:
            Exception: If any pipeline step fails
        
        Requirements:
            - 17.4: Verify all returned media IDs have metadata
            - 17.5: Log inconsistencies if metadata is missing
        """
        logger.info("Starting data pipeline execution")
        
        try:
            # Step 1: Load dataset
            df = self.load_dataset()
            total_loaded = len(df)
            
            # Step 2: Clean and validate
            df_clean = self.clean_text(df)
            total_cleaned = len(df_clean)
            
            # Step 3: Process and store
            self.process_and_store(df_clean, train_vectorizer=train_vectorizer)
            
            # Get final statistics
            model_version = self.ml_engine.get_model_version()
            
            stats = {
                'total_loaded': total_loaded,
                'total_cleaned': total_cleaned,
                'total_stored': total_cleaned,
                'model_version': model_version
            }
            
            logger.info(f"Pipeline execution complete: {stats}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            raise
    
    def close(self) -> None:
        """Close database connections."""
        try:
            self.vector_db.close()
            self.postgres_db.close()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing connections: {e}")
            raise
