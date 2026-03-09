"""
Unit tests for the Data Pipeline module.

Tests cover dataset loading, data cleaning, batch processing, embedding
generation, metadata storage, and the complete pipeline workflow.
"""

import os
import tempfile
import uuid
import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch, call

from data_pipeline.data_pipeline import DataPipeline


class TestDatasetLoading:
    """Tests for dataset loading functionality."""
    
    def test_load_valid_csv(self):
        """Test loading a valid CSV file with required columns."""
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id,title,description,media_type\n")
            f.write("1,Test Book,A great book,book\n")
            f.write("2,Test Show,A great show,tv_show\n")
            temp_path = f.name
        
        try:
            # Create pipeline with mocked dependencies
            with patch('data_pipeline.data_pipeline.MLEngine'), \
                 patch('data_pipeline.data_pipeline.VectorDatabase'), \
                 patch('data_pipeline.data_pipeline.PostgresDatabase'):
                
                pipeline = DataPipeline(
                    source_path=temp_path,
                    vectorizer_path="test/models",
                    embeddings_path="test/embeddings"
                )
                
                # Load dataset
                df = pipeline.load_dataset()
                
                # Verify
                assert len(df) == 2
                assert 'title' in df.columns
                assert 'description' in df.columns
                assert df.iloc[0]['title'] == 'Test Book'
                assert df.iloc[1]['title'] == 'Test Show'
        finally:
            os.unlink(temp_path)
    
    def test_load_missing_file(self):
        """Test loading a non-existent file raises FileNotFoundError."""
        with patch('data_pipeline.data_pipeline.MLEngine'), \
             patch('data_pipeline.data_pipeline.VectorDatabase'), \
             patch('data_pipeline.data_pipeline.PostgresDatabase'):
            
            pipeline = DataPipeline(
                source_path="nonexistent.csv",
                vectorizer_path="test/models",
                embeddings_path="test/embeddings"
            )
            
            with pytest.raises(FileNotFoundError):
                pipeline.load_dataset()
    
    def test_load_missing_required_columns(self):
        """Test loading CSV without required columns raises ValueError."""
        # Create CSV without description column
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id,title,media_type\n")
            f.write("1,Test Book,book\n")
            temp_path = f.name
        
        try:
            with patch('data_pipeline.data_pipeline.MLEngine'), \
                 patch('data_pipeline.data_pipeline.VectorDatabase'), \
                 patch('data_pipeline.data_pipeline.PostgresDatabase'):
                
                pipeline = DataPipeline(
                    source_path=temp_path,
                    vectorizer_path="test/models",
                    embeddings_path="test/embeddings"
                )
                
                with pytest.raises(ValueError, match="missing required columns"):
                    pipeline.load_dataset()
        finally:
            os.unlink(temp_path)
    
    def test_load_empty_csv(self):
        """Test loading an empty CSV raises ValueError."""
        # Create empty CSV with headers only
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id,title,description,media_type\n")
            temp_path = f.name
        
        try:
            with patch('data_pipeline.data_pipeline.MLEngine'), \
                 patch('data_pipeline.data_pipeline.VectorDatabase'), \
                 patch('data_pipeline.data_pipeline.PostgresDatabase'):
                
                pipeline = DataPipeline(
                    source_path=temp_path,
                    vectorizer_path="test/models",
                    embeddings_path="test/embeddings"
                )
                
                with pytest.raises(ValueError, match="Dataset is empty"):
                    pipeline.load_dataset()
        finally:
            os.unlink(temp_path)


class TestDataCleaning:
    """Tests for data cleaning and validation functionality."""
    
    def test_clean_removes_null_title(self):
        """Test that rows with null titles are removed."""
        df = pd.DataFrame({
            'title': ['Valid Title', None, 'Another Title'],
            'description': ['Desc 1', 'Desc 2', 'Desc 3']
        })
        
        with patch('data_pipeline.data_pipeline.MLEngine'), \
             patch('data_pipeline.data_pipeline.VectorDatabase'), \
             patch('data_pipeline.data_pipeline.PostgresDatabase'):
            
            pipeline = DataPipeline(
                source_path="test.csv",
                vectorizer_path="test/models",
                embeddings_path="test/embeddings"
            )
            
            df_clean = pipeline.clean_text(df)
            
            assert len(df_clean) == 2
            assert None not in df_clean['title'].values
    
    def test_clean_removes_empty_description(self):
        """Test that rows with empty descriptions are removed."""
        df = pd.DataFrame({
            'title': ['Title 1', 'Title 2', 'Title 3'],
            'description': ['Valid desc', '   ', 'Another desc']
        })
        
        with patch('data_pipeline.data_pipeline.MLEngine'), \
             patch('data_pipeline.data_pipeline.VectorDatabase'), \
             patch('data_pipeline.data_pipeline.PostgresDatabase'):
            
            pipeline = DataPipeline(
                source_path="test.csv",
                vectorizer_path="test/models",
                embeddings_path="test/embeddings"
            )
            
            df_clean = pipeline.clean_text(df)
            
            assert len(df_clean) == 2
            assert '   ' not in df_clean['description'].values
    
    def test_clean_validates_media_type(self):
        """Test that invalid media types are filtered out."""
        df = pd.DataFrame({
            'title': ['Title 1', 'Title 2', 'Title 3'],
            'description': ['Desc 1', 'Desc 2', 'Desc 3'],
            'media_type': ['book', 'invalid', 'tv_show']
        })
        
        with patch('data_pipeline.data_pipeline.MLEngine'), \
             patch('data_pipeline.data_pipeline.VectorDatabase'), \
             patch('data_pipeline.data_pipeline.PostgresDatabase'):
            
            pipeline = DataPipeline(
                source_path="test.csv",
                vectorizer_path="test/models",
                embeddings_path="test/embeddings"
            )
            
            df_clean = pipeline.clean_text(df)
            
            assert len(df_clean) == 2
            assert 'invalid' not in df_clean['media_type'].values
    
    def test_clean_validates_year_range(self):
        """Test that years outside valid range are filtered."""
        df = pd.DataFrame({
            'title': ['Title 1', 'Title 2', 'Title 3', 'Title 4'],
            'description': ['Desc 1', 'Desc 2', 'Desc 3', 'Desc 4'],
            'year': [2020, 1500, 2025, 2100]
        })
        
        with patch('data_pipeline.data_pipeline.MLEngine'), \
             patch('data_pipeline.data_pipeline.VectorDatabase'), \
             patch('data_pipeline.data_pipeline.PostgresDatabase'):
            
            pipeline = DataPipeline(
                source_path="test.csv",
                vectorizer_path="test/models",
                embeddings_path="test/embeddings"
            )
            
            df_clean = pipeline.clean_text(df)
            
            # Should keep 2020 and 2025, remove 1500 and 2100
            assert len(df_clean) == 2
            assert 1500 not in df_clean['year'].values
            assert 2100 not in df_clean['year'].values
    
    def test_clean_validates_rating_range(self):
        """Test that ratings outside 0-10 range are filtered."""
        df = pd.DataFrame({
            'title': ['Title 1', 'Title 2', 'Title 3', 'Title 4'],
            'description': ['Desc 1', 'Desc 2', 'Desc 3', 'Desc 4'],
            'rating': [5.5, -1.0, 10.0, 15.0]
        })
        
        with patch('data_pipeline.data_pipeline.MLEngine'), \
             patch('data_pipeline.data_pipeline.VectorDatabase'), \
             patch('data_pipeline.data_pipeline.PostgresDatabase'):
            
            pipeline = DataPipeline(
                source_path="test.csv",
                vectorizer_path="test/models",
                embeddings_path="test/embeddings"
            )
            
            df_clean = pipeline.clean_text(df)
            
            # Should keep 5.5 and 10.0, remove -1.0 and 15.0
            assert len(df_clean) == 2
            assert -1.0 not in df_clean['rating'].values
            assert 15.0 not in df_clean['rating'].values
    
    def test_clean_raises_error_if_all_removed(self):
        """Test that cleaning raises error if all rows are removed."""
        df = pd.DataFrame({
            'title': [None, None],
            'description': ['Desc 1', 'Desc 2']
        })
        
        with patch('data_pipeline.data_pipeline.MLEngine'), \
             patch('data_pipeline.data_pipeline.VectorDatabase'), \
             patch('data_pipeline.data_pipeline.PostgresDatabase'):
            
            pipeline = DataPipeline(
                source_path="test.csv",
                vectorizer_path="test/models",
                embeddings_path="test/embeddings"
            )
            
            with pytest.raises(ValueError, match="Dataset is empty after cleaning"):
                pipeline.clean_text(df)


class TestBatchProcessing:
    """Tests for batch processing logic."""
    
    def test_process_single_batch(self):
        """Test processing a dataset that fits in one batch."""
        df = pd.DataFrame({
            'id': ['1', '2', '3'],
            'title': ['Title 1', 'Title 2', 'Title 3'],
            'description': ['Desc 1', 'Desc 2', 'Desc 3'],
            'media_type': ['book', 'book', 'tv_show']
        })
        
        with patch('data_pipeline.data_pipeline.MLEngine') as MockMLEngine, \
             patch('data_pipeline.data_pipeline.VectorDatabase') as MockVectorDB, \
             patch('data_pipeline.data_pipeline.PostgresDatabase') as MockPostgresDB:
            
            # Setup mocks
            mock_ml = MockMLEngine.return_value
            mock_ml.vectorizer = Mock()
            mock_ml.get_model_version.return_value = 'v1.0.0'
            mock_ml.compute_embeddings.return_value = np.array([
                [0.1, 0.2, 0.3],
                [0.4, 0.5, 0.6],
                [0.7, 0.8, 0.9]
            ])
            
            mock_vdb = MockVectorDB.return_value
            mock_pg = MockPostgresDB.return_value
            mock_pg.batch_insert_media.return_value = ['1', '2', '3']
            
            pipeline = DataPipeline(
                source_path="test.csv",
                vectorizer_path="test/models",
                embeddings_path="test/embeddings",
                batch_size=10
            )
            
            # Process
            pipeline.process_and_store(df, train_vectorizer=False)
            
            # Verify embeddings were computed
            assert mock_ml.compute_embeddings.called
            
            # Verify Vector DB insert was called 3 times
            assert mock_vdb.insert.call_count == 3
            
            # Verify PostgreSQL batch insert was called once
            assert mock_pg.batch_insert_media.call_count == 1
    
    def test_process_multiple_batches(self):
        """Test processing a dataset across multiple batches."""
        df = pd.DataFrame({
            'id': [str(i) for i in range(5)],
            'title': [f'Title {i}' for i in range(5)],
            'description': [f'Desc {i}' for i in range(5)],
            'media_type': ['book'] * 5
        })
        
        with patch('data_pipeline.data_pipeline.MLEngine') as MockMLEngine, \
             patch('data_pipeline.data_pipeline.VectorDatabase') as MockVectorDB, \
             patch('data_pipeline.data_pipeline.PostgresDatabase') as MockPostgresDB:
            
            # Setup mocks
            mock_ml = MockMLEngine.return_value
            mock_ml.vectorizer = Mock()
            mock_ml.get_model_version.return_value = 'v1.0.0'
            
            # Return different embeddings for each batch
            def compute_embeddings_side_effect(descriptions, media_ids):
                return np.random.rand(len(descriptions), 3)
            
            mock_ml.compute_embeddings.side_effect = compute_embeddings_side_effect
            
            mock_vdb = MockVectorDB.return_value
            mock_pg = MockPostgresDB.return_value
            
            # Return IDs for each batch
            def batch_insert_side_effect(items):
                return [item['id'] for item in items]
            
            mock_pg.batch_insert_media.side_effect = batch_insert_side_effect
            
            pipeline = DataPipeline(
                source_path="test.csv",
                vectorizer_path="test/models",
                embeddings_path="test/embeddings",
                batch_size=2  # Process in batches of 2
            )
            
            # Process
            pipeline.process_and_store(df, train_vectorizer=False)
            
            # Verify compute_embeddings was called 3 times (5 items / 2 per batch = 3 batches)
            assert mock_ml.compute_embeddings.call_count == 3
            
            # Verify Vector DB insert was called 5 times (once per item)
            assert mock_vdb.insert.call_count == 5
            
            # Verify PostgreSQL batch insert was called 3 times (once per batch)
            assert mock_pg.batch_insert_media.call_count == 3
    
    def test_process_trains_vectorizer_if_requested(self):
        """Test that vectorizer is trained when train_vectorizer=True."""
        df = pd.DataFrame({
            'id': ['1'],
            'title': ['Title 1'],
            'description': ['Description 1'],
            'media_type': ['book']
        })
        
        with patch('data_pipeline.data_pipeline.MLEngine') as MockMLEngine, \
             patch('data_pipeline.data_pipeline.VectorDatabase') as MockVectorDB, \
             patch('data_pipeline.data_pipeline.PostgresDatabase') as MockPostgresDB:
            
            # Setup mocks
            mock_ml = MockMLEngine.return_value
            mock_ml.vectorizer = None  # No vectorizer initially
            mock_ml.get_model_version.return_value = 'v1.0.0'
            mock_ml.compute_embeddings.return_value = np.array([[0.1, 0.2, 0.3]])
            
            mock_vdb = MockVectorDB.return_value
            mock_pg = MockPostgresDB.return_value
            mock_pg.batch_insert_media.return_value = ['1']
            
            pipeline = DataPipeline(
                source_path="test.csv",
                vectorizer_path="test/models",
                embeddings_path="test/embeddings"
            )
            
            # Process with train_vectorizer=True
            pipeline.process_and_store(df, train_vectorizer=True)
            
            # Verify train_vectorizer was called
            assert mock_ml.train_vectorizer.called
    
    def test_process_halts_on_batch_failure(self):
        """Test that processing halts if a batch fails."""
        df = pd.DataFrame({
            'id': [str(i) for i in range(5)],
            'title': [f'Title {i}' for i in range(5)],
            'description': [f'Desc {i}' for i in range(5)],
            'media_type': ['book'] * 5
        })
        
        with patch('data_pipeline.data_pipeline.MLEngine') as MockMLEngine, \
             patch('data_pipeline.data_pipeline.VectorDatabase') as MockVectorDB, \
             patch('data_pipeline.data_pipeline.PostgresDatabase') as MockPostgresDB:
            
            # Setup mocks
            mock_ml = MockMLEngine.return_value
            mock_ml.vectorizer = Mock()
            mock_ml.get_model_version.return_value = 'v1.0.0'
            
            # First batch succeeds, second batch fails
            call_count = [0]
            
            def compute_embeddings_side_effect(descriptions, media_ids):
                call_count[0] += 1
                if call_count[0] == 2:
                    raise Exception("Batch processing error")
                return np.random.rand(len(descriptions), 3)
            
            mock_ml.compute_embeddings.side_effect = compute_embeddings_side_effect
            
            mock_vdb = MockVectorDB.return_value
            mock_pg = MockPostgresDB.return_value
            mock_pg.batch_insert_media.return_value = ['1', '2']
            
            pipeline = DataPipeline(
                source_path="test.csv",
                vectorizer_path="test/models",
                embeddings_path="test/embeddings",
                batch_size=2
            )
            
            # Process should raise error
            with pytest.raises(ValueError, match="Batch .* failed to process"):
                pipeline.process_and_store(df, train_vectorizer=False)


class TestEmbeddingStorage:
    """Tests for embedding generation and storage."""
    
    def test_store_embeddings_generates_and_stores(self):
        """Test that embeddings are generated and stored correctly."""
        df = pd.DataFrame({
            'id': ['1', '2'],
            'description': ['Description 1', 'Description 2']
        })
        
        with patch('data_pipeline.data_pipeline.MLEngine') as MockMLEngine, \
             patch('data_pipeline.data_pipeline.VectorDatabase') as MockVectorDB, \
             patch('data_pipeline.data_pipeline.PostgresDatabase'):
            
            # Setup mocks
            mock_ml = MockMLEngine.return_value
            mock_ml.get_model_version.return_value = 'v1.0.0'
            mock_ml.compute_embeddings.return_value = np.array([
                [0.1, 0.2, 0.3],
                [0.4, 0.5, 0.6]
            ])
            
            mock_vdb = MockVectorDB.return_value
            
            pipeline = DataPipeline(
                source_path="test.csv",
                vectorizer_path="test/models",
                embeddings_path="test/embeddings"
            )
            
            # Store embeddings
            pipeline.store_embeddings(df)
            
            # Verify compute_embeddings was called
            mock_ml.compute_embeddings.assert_called_once()
            
            # Verify Vector DB insert was called twice
            assert mock_vdb.insert.call_count == 2
            
            # Verify metadata includes model_version
            calls = mock_vdb.insert.call_args_list
            assert calls[0][0][2]['model_version'] == 'v1.0.0'
            assert calls[1][0][2]['model_version'] == 'v1.0.0'
    
    def test_store_embeddings_validates_finite_values(self):
        """Test that non-finite embedding values raise error."""
        df = pd.DataFrame({
            'id': ['1'],
            'description': ['Description 1']
        })
        
        with patch('data_pipeline.data_pipeline.MLEngine') as MockMLEngine, \
             patch('data_pipeline.data_pipeline.VectorDatabase') as MockVectorDB, \
             patch('data_pipeline.data_pipeline.PostgresDatabase'):
            
            # Setup mocks
            mock_ml = MockMLEngine.return_value
            mock_ml.get_model_version.return_value = 'v1.0.0'
            mock_ml.compute_embeddings.return_value = np.array([
                [0.1, np.inf, 0.3]  # Contains infinity
            ])
            
            mock_vdb = MockVectorDB.return_value
            
            pipeline = DataPipeline(
                source_path="test.csv",
                vectorizer_path="test/models",
                embeddings_path="test/embeddings"
            )
            
            # Should raise error
            with pytest.raises(ValueError, match="contains non-finite values"):
                pipeline.store_embeddings(df)


class TestMetadataStorage:
    """Tests for metadata storage."""
    
    def test_store_metadata_validates_and_stores(self):
        """Test that metadata is validated and stored correctly."""
        df = pd.DataFrame({
            'id': ['1', '2'],
            'title': ['Title 1', 'Title 2'],
            'description': ['Desc 1', 'Desc 2'],
            'media_type': ['book', 'tv_show'],
            'author': ['Author 1', None],
            'genre': ['Mystery', 'Sci-Fi']
        })
        
        with patch('data_pipeline.data_pipeline.MLEngine'), \
             patch('data_pipeline.data_pipeline.VectorDatabase'), \
             patch('data_pipeline.data_pipeline.PostgresDatabase') as MockPostgresDB:
            
            # Setup mocks
            mock_pg = MockPostgresDB.return_value
            mock_pg.batch_insert_media.return_value = ['1', '2']
            
            pipeline = DataPipeline(
                source_path="test.csv",
                vectorizer_path="test/models",
                embeddings_path="test/embeddings"
            )
            
            # Store metadata
            pipeline.store_metadata(df)
            
            # Verify batch_insert_media was called
            mock_pg.batch_insert_media.assert_called_once()
            
            # Verify the items passed to batch_insert
            items = mock_pg.batch_insert_media.call_args[0][0]
            assert len(items) == 2
            assert items[0]['title'] == 'Title 1'
            assert items[0]['media_type'] == 'book'
            assert items[0]['metadata']['author'] == 'Author 1'
            assert items[1]['title'] == 'Title 2'
            assert items[1]['media_type'] == 'tv_show'
    
    def test_store_metadata_truncates_long_fields(self):
        """Test that long titles and descriptions are truncated."""
        df = pd.DataFrame({
            'id': ['1'],
            'title': ['A' * 600],  # Longer than 500 chars
            'description': ['B' * 6000],  # Longer than 5000 chars
            'media_type': ['book']
        })
        
        with patch('data_pipeline.data_pipeline.MLEngine'), \
             patch('data_pipeline.data_pipeline.VectorDatabase'), \
             patch('data_pipeline.data_pipeline.PostgresDatabase') as MockPostgresDB:
            
            # Setup mocks
            mock_pg = MockPostgresDB.return_value
            mock_pg.batch_insert_media.return_value = ['1']
            
            pipeline = DataPipeline(
                source_path="test.csv",
                vectorizer_path="test/models",
                embeddings_path="test/embeddings"
            )
            
            # Store metadata
            pipeline.store_metadata(df)
            
            # Verify truncation
            items = mock_pg.batch_insert_media.call_args[0][0]
            assert len(items[0]['title']) == 500
            assert len(items[0]['description']) == 5000


class TestPipelineIntegration:
    """Integration tests for the complete pipeline."""
    
    def test_run_complete_pipeline(self):
        """Test running the complete pipeline end-to-end."""
        # Create temporary CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id,title,description,media_type\n")
            f.write("1,Book 1,Description 1,book\n")
            f.write("2,Show 1,Description 2,tv_show\n")
            temp_path = f.name
        
        try:
            with patch('data_pipeline.data_pipeline.MLEngine') as MockMLEngine, \
                 patch('data_pipeline.data_pipeline.VectorDatabase') as MockVectorDB, \
                 patch('data_pipeline.data_pipeline.PostgresDatabase') as MockPostgresDB:
                
                # Setup mocks
                mock_ml = MockMLEngine.return_value
                mock_ml.vectorizer = Mock()
                mock_ml.get_model_version.return_value = 'v1.0.0'
                mock_ml.compute_embeddings.return_value = np.array([
                    [0.1, 0.2, 0.3],
                    [0.4, 0.5, 0.6]
                ])
                
                mock_vdb = MockVectorDB.return_value
                mock_pg = MockPostgresDB.return_value
                mock_pg.batch_insert_media.return_value = ['1', '2']
                
                pipeline = DataPipeline(
                    source_path=temp_path,
                    vectorizer_path="test/models",
                    embeddings_path="test/embeddings"
                )
                
                # Run pipeline
                stats = pipeline.run(train_vectorizer=False)
                
                # Verify statistics
                assert stats['total_loaded'] == 2
                assert stats['total_cleaned'] == 2
                assert stats['total_stored'] == 2
                assert stats['model_version'] == 'v1.0.0'
        finally:
            os.unlink(temp_path)
    
    def test_pipeline_initialization_validation(self):
        """Test that pipeline initialization validates parameters."""
        with patch('data_pipeline.data_pipeline.MLEngine'), \
             patch('data_pipeline.data_pipeline.VectorDatabase'), \
             patch('data_pipeline.data_pipeline.PostgresDatabase'):
            
            # Empty source_path
            with pytest.raises(ValueError, match="source_path cannot be empty"):
                DataPipeline(
                    source_path="",
                    vectorizer_path="test/models",
                    embeddings_path="test/embeddings"
                )
            
            # Empty vectorizer_path
            with pytest.raises(ValueError, match="vectorizer_path cannot be empty"):
                DataPipeline(
                    source_path="test.csv",
                    vectorizer_path="",
                    embeddings_path="test/embeddings"
                )
            
            # Invalid batch_size
            with pytest.raises(ValueError, match="batch_size must be positive"):
                DataPipeline(
                    source_path="test.csv",
                    vectorizer_path="test/models",
                    embeddings_path="test/embeddings",
                    batch_size=0
                )
