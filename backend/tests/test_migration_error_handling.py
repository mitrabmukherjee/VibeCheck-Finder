"""
Tests for migration script error handling and recovery.

This test suite validates that the migration script:
- Catches and logs errors for individual media items
- Continues processing remaining items if one fails
- Generates migration report with success/failure statistics
- Supports dry_run mode for validation without writing

Requirements:
    - 8.3: Migration logs detailed error messages
    - 10.3: System handles errors gracefully
"""

import pytest
import tempfile
import shutil
import os
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_pipeline.migrate_to_sbert import migrate_to_sbert


def test_migration_handles_empty_descriptions(tmp_path, monkeypatch):
    """
    Test that migration handles media items with empty descriptions gracefully.
    
    Validates:
        - Items with empty descriptions are logged as failures
        - Other items continue to be processed
        - Migration report includes failed items
    """
    # Disable PostgreSQL
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    
    # Create temporary data file with some empty descriptions
    data_file = tmp_path / "test_data.csv"
    data_file.write_text(
        "id,title,description,type\n"
        "1,Valid Movie,A great movie about adventure,movie\n"
        "2,Empty Desc Movie,,movie\n"
        "3,Another Valid,Another great movie,movie\n"
    )
    
    embeddings_path = tmp_path / "embeddings"
    embeddings_path.mkdir()
    
    vectorizer_path = tmp_path / "models"
    vectorizer_path.mkdir()
    
    # Run migration
    report = migrate_to_sbert(
        postgres_conn_string=None,  # Explicitly disable PostgreSQL
        data_file=str(data_file),
        embeddings_path=str(embeddings_path),
        vectorizer_path=str(vectorizer_path),
        batch_size=2,
        backup=False,
        dry_run=False
    )
    
    # Verify report
    assert report['total_items'] == 3
    assert report['successful'] == 2  # Only 2 valid items
    assert report['failed'] == 1  # 1 item with empty description
    assert report['status'] == 'partial'
    assert len(report['failed_items']) == 1
    assert report['failed_items'][0]['id'] == '2'
    assert 'empty description' in report['failed_items'][0]['error'].lower()


def test_migration_dry_run_mode(tmp_path, monkeypatch):
    """
    Test that dry_run mode validates without writing to database.
    
    Validates:
        - Embeddings are generated
        - No files are written to disk
        - Report indicates dry_run mode
    """
    # Disable PostgreSQL
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    
    # Create temporary data file
    data_file = tmp_path / "test_data.csv"
    data_file.write_text(
        "id,title,description,type\n"
        "1,Test Movie,A test movie description,movie\n"
        "2,Another Movie,Another test description,movie\n"
    )
    
    embeddings_path = tmp_path / "embeddings"
    embeddings_path.mkdir()
    
    vectorizer_path = tmp_path / "models"
    vectorizer_path.mkdir()
    
    # Run migration in dry_run mode
    report = migrate_to_sbert(
        postgres_conn_string=None,  # Explicitly disable PostgreSQL
        data_file=str(data_file),
        embeddings_path=str(embeddings_path),
        vectorizer_path=str(vectorizer_path),
        batch_size=2,
        backup=False,
        dry_run=True
    )
    
    # Verify report
    assert report['dry_run'] is True
    assert report['total_items'] == 2
    assert report['successful'] == 2
    assert report['failed'] == 0
    assert report['status'] == 'completed'
    
    # Verify no files were written
    assert not (embeddings_path / "vectors.npy").exists()
    assert not (embeddings_path / "ids.json").exists()
    assert not (embeddings_path / "metadata.json").exists()


def test_migration_report_structure(tmp_path, monkeypatch):
    """
    Test that migration report has correct structure.
    
    Validates:
        - Report contains all required fields
        - Failed items include detailed error information
    """
    # Disable PostgreSQL
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    
    # Create temporary data file
    data_file = tmp_path / "test_data.csv"
    data_file.write_text(
        "id,title,description,type\n"
        "1,Valid Movie,A great movie,movie\n"
    )
    
    embeddings_path = tmp_path / "embeddings"
    embeddings_path.mkdir()
    
    vectorizer_path = tmp_path / "models"
    vectorizer_path.mkdir()
    
    # Run migration
    report = migrate_to_sbert(
        postgres_conn_string=None,  # Explicitly disable PostgreSQL
        data_file=str(data_file),
        embeddings_path=str(embeddings_path),
        vectorizer_path=str(vectorizer_path),
        batch_size=1,
        backup=False,
        dry_run=True
    )
    
    # Verify report structure
    assert 'status' in report
    assert 'total_items' in report
    assert 'successful' in report
    assert 'failed' in report
    assert 'duration_seconds' in report
    assert 'errors' in report
    assert 'failed_items' in report
    assert 'backup_location' in report
    assert 'new_collection' in report
    assert 'old_collection' in report
    assert 'dry_run' in report
    
    # Verify types
    assert isinstance(report['status'], str)
    assert isinstance(report['total_items'], int)
    assert isinstance(report['successful'], int)
    assert isinstance(report['failed'], int)
    assert isinstance(report['duration_seconds'], float)
    assert isinstance(report['errors'], list)
    assert isinstance(report['failed_items'], list)
    assert isinstance(report['dry_run'], bool)


def test_migration_continues_after_individual_failures(tmp_path, monkeypatch):
    """
    Test that migration continues processing after individual item failures.
    
    Validates:
        - Failed items don't stop the entire migration
        - Successful items are still processed
        - Report accurately reflects partial success
    """
    # Disable PostgreSQL
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    
    # Create temporary data file with mix of valid and invalid items
    data_file = tmp_path / "test_data.csv"
    data_file.write_text(
        "id,title,description,type\n"
        "1,Valid Movie 1,First valid movie,movie\n"
        "2,Empty Desc,,movie\n"
        "3,Valid Movie 2,Second valid movie,movie\n"
        "4,Another Empty,,movie\n"
        "5,Valid Movie 3,Third valid movie,movie\n"
    )
    
    embeddings_path = tmp_path / "embeddings"
    embeddings_path.mkdir()
    
    vectorizer_path = tmp_path / "models"
    vectorizer_path.mkdir()
    
    # Run migration
    report = migrate_to_sbert(
        postgres_conn_string=None,  # Explicitly disable PostgreSQL
        data_file=str(data_file),
        embeddings_path=str(embeddings_path),
        vectorizer_path=str(vectorizer_path),
        batch_size=2,
        backup=False,
        dry_run=True
    )
    
    # Verify partial success
    assert report['total_items'] == 5
    assert report['successful'] == 3  # 3 valid items
    assert report['failed'] == 2  # 2 items with empty descriptions
    assert report['status'] == 'partial'
    assert len(report['failed_items']) == 2
    
    # Verify failed items are tracked
    failed_ids = [item['id'] for item in report['failed_items']]
    assert '2' in failed_ids
    assert '4' in failed_ids


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
