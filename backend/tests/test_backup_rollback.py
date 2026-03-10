"""
Tests for backup and rollback mechanism in migration script.

This test suite validates that the migration script:
- Creates timestamped backup directory before migration
- Copies existing vectors.npy, metadata.json, ids.json to backup
- Verifies backup integrity before proceeding with migration
- Implements rollback function to restore from backup

Requirements:
    - 8.2: Preserve original TF-IDF vectors during migration
    - 8.3: Create backup before migration
    - 8.4: Verify backup integrity before proceeding
    - 8.5: Provide rollback mechanism to restore TF-IDF functionality
"""

import pytest
import tempfile
import shutil
import os
import json
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
from data_pipeline.migrate_to_sbert import (
    create_backup,
    verify_backup,
    rollback_migration,
    migrate_to_sbert
)


def create_test_embeddings(embeddings_path: Path, num_items: int = 10, vector_dim: int = 5000):
    """Helper function to create test embedding files."""
    embeddings_path.mkdir(parents=True, exist_ok=True)
    
    # Create test vectors
    vectors = np.random.randn(num_items, vector_dim).astype(np.float32)
    np.save(embeddings_path / "vectors.npy", vectors)
    
    # Create test IDs
    ids = [f"media_{i}" for i in range(num_items)]
    with open(embeddings_path / "ids.json", 'w') as f:
        json.dump(ids, f)
    
    # Create test metadata
    metadata = {
        "vectorizer_type": "tfidf",
        "vector_size": vector_dim,
        "total_items": num_items
    }
    with open(embeddings_path / "metadata.json", 'w') as f:
        json.dump(metadata, f)
    
    return vectors, ids, metadata


def test_create_backup_creates_timestamped_directory(tmp_path):
    """
    Test that create_backup creates a timestamped backup directory.
    
    Validates:
        - Backup directory is created with timestamp
        - Directory is in backups/ subdirectory
        - Function returns path to backup directory
    
    Requirements: 8.2, 8.3
    """
    embeddings_path = tmp_path / "embeddings"
    vectors, ids, metadata = create_test_embeddings(embeddings_path)
    
    # Create backup
    backup_dir = create_backup(str(embeddings_path))
    
    # Verify backup directory exists
    assert os.path.exists(backup_dir)
    
    # Verify it's in backups/ subdirectory
    assert "backups" in backup_dir
    assert "tfidf_" in backup_dir
    
    # Verify it's a directory
    assert os.path.isdir(backup_dir)


def test_create_backup_copies_all_files(tmp_path):
    """
    Test that create_backup copies all embedding files.
    
    Validates:
        - vectors.npy is copied
        - ids.json is copied
        - metadata.json is copied
        - File sizes match original
    
    Requirements: 8.2, 8.3
    """
    embeddings_path = tmp_path / "embeddings"
    vectors, ids, metadata = create_test_embeddings(embeddings_path)
    
    # Create backup
    backup_dir = create_backup(str(embeddings_path))
    backup_path = Path(backup_dir)
    
    # Verify all files are copied
    assert (backup_path / "vectors.npy").exists()
    assert (backup_path / "ids.json").exists()
    assert (backup_path / "metadata.json").exists()
    
    # Verify file sizes match
    original_vectors_size = (embeddings_path / "vectors.npy").stat().st_size
    backup_vectors_size = (backup_path / "vectors.npy").stat().st_size
    assert original_vectors_size == backup_vectors_size
    
    original_ids_size = (embeddings_path / "ids.json").stat().st_size
    backup_ids_size = (backup_path / "ids.json").stat().st_size
    assert original_ids_size == backup_ids_size


def test_create_backup_preserves_data_integrity(tmp_path):
    """
    Test that create_backup preserves data integrity.
    
    Validates:
        - Backed up vectors match original vectors
        - Backed up IDs match original IDs
        - Backed up metadata matches original metadata
    
    Requirements: 8.2, 8.3
    """
    embeddings_path = tmp_path / "embeddings"
    original_vectors, original_ids, original_metadata = create_test_embeddings(embeddings_path)
    
    # Create backup
    backup_dir = create_backup(str(embeddings_path))
    backup_path = Path(backup_dir)
    
    # Load backed up data
    backup_vectors = np.load(backup_path / "vectors.npy")
    with open(backup_path / "ids.json", 'r') as f:
        backup_ids = json.load(f)
    with open(backup_path / "metadata.json", 'r') as f:
        backup_metadata = json.load(f)
    
    # Verify data matches
    np.testing.assert_array_equal(original_vectors, backup_vectors)
    assert original_ids == backup_ids
    assert original_metadata == backup_metadata


def test_verify_backup_validates_directory_exists(tmp_path):
    """
    Test that verify_backup checks if backup directory exists.
    
    Validates:
        - Returns False if directory doesn't exist
        - Logs appropriate error message
    
    Requirements: 8.4
    """
    non_existent_dir = str(tmp_path / "non_existent_backup")
    
    result = verify_backup(non_existent_dir)
    
    assert result is False


def test_verify_backup_validates_required_files(tmp_path):
    """
    Test that verify_backup checks for required files.
    
    Validates:
        - Returns False if vectors.npy is missing
        - Returns False if ids.json is missing
        - Logs appropriate error messages
    
    Requirements: 8.4
    """
    backup_path = tmp_path / "backup"
    backup_path.mkdir()
    
    # Test with no files
    result = verify_backup(str(backup_path))
    assert result is False
    
    # Test with only vectors.npy
    np.save(backup_path / "vectors.npy", np.random.randn(10, 768))
    result = verify_backup(str(backup_path))
    assert result is False
    
    # Test with only ids.json
    (backup_path / "vectors.npy").unlink()
    with open(backup_path / "ids.json", 'w') as f:
        json.dump(["id1", "id2"], f)
    result = verify_backup(str(backup_path))
    assert result is False


def test_verify_backup_validates_file_not_empty(tmp_path):
    """
    Test that verify_backup checks files are not empty.
    
    Validates:
        - Returns False if vectors.npy is empty
        - Returns False if ids.json is empty
    
    Requirements: 8.4
    """
    backup_path = tmp_path / "backup"
    backup_path.mkdir()
    
    # Create empty files
    (backup_path / "vectors.npy").touch()
    (backup_path / "ids.json").touch()
    
    result = verify_backup(str(backup_path))
    assert result is False


def test_verify_backup_validates_numpy_array(tmp_path):
    """
    Test that verify_backup validates numpy arrays can be loaded.
    
    Validates:
        - Returns False if vectors.npy is corrupted
        - Returns False if vectors.npy has invalid dimensions
        - Returns False if vectors.npy contains non-finite values
    
    Requirements: 8.4
    """
    backup_path = tmp_path / "backup"
    backup_path.mkdir()
    
    # Test with corrupted numpy file
    with open(backup_path / "vectors.npy", 'wb') as f:
        f.write(b"corrupted data")
    with open(backup_path / "ids.json", 'w') as f:
        json.dump(["id1"], f)
    
    result = verify_backup(str(backup_path))
    assert result is False
    
    # Test with 1D array (invalid dimensions)
    np.save(backup_path / "vectors.npy", np.array([1, 2, 3]))
    result = verify_backup(str(backup_path))
    assert result is False
    
    # Test with non-finite values
    vectors_with_nan = np.array([[1.0, 2.0, np.nan], [4.0, 5.0, 6.0]])
    np.save(backup_path / "vectors.npy", vectors_with_nan)
    with open(backup_path / "ids.json", 'w') as f:
        json.dump(["id1", "id2"], f)
    result = verify_backup(str(backup_path))
    assert result is False


def test_verify_backup_validates_json_format(tmp_path):
    """
    Test that verify_backup validates JSON files can be parsed.
    
    Validates:
        - Returns False if ids.json is invalid JSON
        - Returns False if ids.json is not a list
    
    Requirements: 8.4
    """
    backup_path = tmp_path / "backup"
    backup_path.mkdir()
    
    # Create valid vectors
    np.save(backup_path / "vectors.npy", np.random.randn(2, 768))
    
    # Test with invalid JSON
    with open(backup_path / "ids.json", 'w') as f:
        f.write("invalid json {")
    
    result = verify_backup(str(backup_path))
    assert result is False
    
    # Test with non-list JSON
    with open(backup_path / "ids.json", 'w') as f:
        json.dump({"not": "a list"}, f)
    
    result = verify_backup(str(backup_path))
    assert result is False


def test_verify_backup_validates_count_match(tmp_path):
    """
    Test that verify_backup validates vector count matches ID count.
    
    Validates:
        - Returns False if number of vectors doesn't match number of IDs
    
    Requirements: 8.4
    """
    backup_path = tmp_path / "backup"
    backup_path.mkdir()
    
    # Create 5 vectors but only 3 IDs
    np.save(backup_path / "vectors.npy", np.random.randn(5, 768))
    with open(backup_path / "ids.json", 'w') as f:
        json.dump(["id1", "id2", "id3"], f)
    
    result = verify_backup(str(backup_path))
    assert result is False


def test_verify_backup_passes_with_valid_backup(tmp_path):
    """
    Test that verify_backup passes with valid backup.
    
    Validates:
        - Returns True for valid backup
        - All validation checks pass
    
    Requirements: 8.4
    """
    backup_path = tmp_path / "backup"
    backup_path.mkdir()
    
    # Create valid backup
    num_items = 10
    vectors = np.random.randn(num_items, 768).astype(np.float32)
    np.save(backup_path / "vectors.npy", vectors)
    
    ids = [f"media_{i}" for i in range(num_items)]
    with open(backup_path / "ids.json", 'w') as f:
        json.dump(ids, f)
    
    result = verify_backup(str(backup_path))
    assert result is True


def test_rollback_migration_restores_files(tmp_path):
    """
    Test that rollback_migration restores files from backup.
    
    Validates:
        - All files are restored from backup
        - Restored files match backup files
        - Function returns True on success
    
    Requirements: 8.5
    """
    embeddings_path = tmp_path / "embeddings"
    backup_path = tmp_path / "backup"
    
    # Create backup with test data
    backup_path.mkdir()
    original_vectors = np.random.randn(10, 5000).astype(np.float32)
    np.save(backup_path / "vectors.npy", original_vectors)
    
    original_ids = [f"media_{i}" for i in range(10)]
    with open(backup_path / "ids.json", 'w') as f:
        json.dump(original_ids, f)
    
    # Create different data in embeddings directory (simulating migration)
    embeddings_path.mkdir()
    new_vectors = np.random.randn(10, 768).astype(np.float32)
    np.save(embeddings_path / "vectors.npy", new_vectors)
    
    new_ids = [f"new_media_{i}" for i in range(10)]
    with open(embeddings_path / "ids.json", 'w') as f:
        json.dump(new_ids, f)
    
    # Perform rollback
    result = rollback_migration(str(backup_path), str(embeddings_path))
    
    # Verify rollback succeeded
    assert result is True
    
    # Verify files were restored
    restored_vectors = np.load(embeddings_path / "vectors.npy")
    with open(embeddings_path / "ids.json", 'r') as f:
        restored_ids = json.load(f)
    
    np.testing.assert_array_equal(original_vectors, restored_vectors)
    assert original_ids == restored_ids


def test_rollback_migration_verifies_backup_before_restore(tmp_path):
    """
    Test that rollback_migration verifies backup before restoring.
    
    Validates:
        - Returns False if backup is invalid
        - Does not modify embeddings directory if backup is invalid
    
    Requirements: 8.4, 8.5
    """
    embeddings_path = tmp_path / "embeddings"
    backup_path = tmp_path / "backup"
    
    # Create invalid backup (missing files)
    backup_path.mkdir()
    
    # Create embeddings directory with data
    embeddings_path.mkdir()
    original_vectors = np.random.randn(10, 768).astype(np.float32)
    np.save(embeddings_path / "vectors.npy", original_vectors)
    
    # Attempt rollback with invalid backup
    result = rollback_migration(str(backup_path), str(embeddings_path))
    
    # Verify rollback failed
    assert result is False
    
    # Verify embeddings directory was not modified
    vectors_still_there = np.load(embeddings_path / "vectors.npy")
    np.testing.assert_array_equal(original_vectors, vectors_still_there)


def test_rollback_migration_creates_backup_of_current_state(tmp_path):
    """
    Test that rollback_migration creates backup of current state before rollback.
    
    Validates:
        - Current state is backed up before rollback
        - Backup can be used to undo rollback if needed
    
    Requirements: 8.5
    """
    embeddings_path = tmp_path / "embeddings"
    backup_path = tmp_path / "backup"
    
    # Create valid backup
    backup_path.mkdir()
    old_vectors = np.random.randn(10, 5000).astype(np.float32)
    np.save(backup_path / "vectors.npy", old_vectors)
    
    old_ids = [f"old_media_{i}" for i in range(10)]
    with open(backup_path / "ids.json", 'w') as f:
        json.dump(old_ids, f)
    
    # Create current embeddings
    embeddings_path.mkdir()
    current_vectors = np.random.randn(10, 768).astype(np.float32)
    np.save(embeddings_path / "vectors.npy", current_vectors)
    
    current_ids = [f"current_media_{i}" for i in range(10)]
    with open(embeddings_path / "ids.json", 'w') as f:
        json.dump(current_ids, f)
    
    # Perform rollback
    result = rollback_migration(str(backup_path), str(embeddings_path))
    
    # Verify rollback succeeded
    assert result is True
    
    # Verify a pre_rollback backup was created
    backups_dir = tmp_path / "backups"
    assert backups_dir.exists()
    
    # Find the pre_rollback backup
    pre_rollback_backups = list(backups_dir.glob("pre_rollback_*"))
    assert len(pre_rollback_backups) > 0


def test_rollback_migration_handles_nonexistent_backup(tmp_path):
    """
    Test that rollback_migration handles non-existent backup directory.
    
    Validates:
        - Returns False if backup directory doesn't exist
        - Logs appropriate error message
    
    Requirements: 8.5
    """
    embeddings_path = tmp_path / "embeddings"
    embeddings_path.mkdir()
    
    non_existent_backup = str(tmp_path / "non_existent_backup")
    
    result = rollback_migration(non_existent_backup, str(embeddings_path))
    
    assert result is False


def test_migration_creates_backup_by_default(tmp_path, monkeypatch):
    """
    Test that migrate_to_sbert creates backup by default.
    
    Validates:
        - Backup is created before migration
        - Backup location is included in report
    
    Requirements: 8.2, 8.3
    """
    # Disable PostgreSQL
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    
    embeddings_path = tmp_path / "embeddings"
    
    # Create existing embeddings to backup
    create_test_embeddings(embeddings_path)
    
    # Create test data file
    data_file = tmp_path / "test_data.csv"
    data_file.write_text(
        "id,title,description,type\n"
        "1,Test Movie,A test movie description,movie\n"
    )
    
    vectorizer_path = tmp_path / "models"
    vectorizer_path.mkdir()
    
    # Run migration with backup enabled (NOT dry_run, so backup is actually created)
    report = migrate_to_sbert(
        postgres_conn_string=None,
        data_file=str(data_file),
        embeddings_path=str(embeddings_path),
        vectorizer_path=str(vectorizer_path),
        batch_size=1,
        backup=True,
        dry_run=False  # Changed from True to False so backup is created
    )
    
    # Verify backup was created
    assert report['backup_location'] is not None
    assert os.path.exists(report['backup_location'])
    
    # Verify backup contains files
    backup_path = Path(report['backup_location'])
    assert (backup_path / "vectors.npy").exists()
    assert (backup_path / "ids.json").exists()


def test_migration_skips_backup_when_disabled(tmp_path, monkeypatch):
    """
    Test that migrate_to_sbert skips backup when disabled.
    
    Validates:
        - No backup is created when backup=False
        - backup_location is None in report
    
    Requirements: 8.2
    """
    # Disable PostgreSQL
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    
    embeddings_path = tmp_path / "embeddings"
    embeddings_path.mkdir()
    
    # Create test data file
    data_file = tmp_path / "test_data.csv"
    data_file.write_text(
        "id,title,description,type\n"
        "1,Test Movie,A test movie description,movie\n"
    )
    
    vectorizer_path = tmp_path / "models"
    vectorizer_path.mkdir()
    
    # Run migration with backup disabled
    report = migrate_to_sbert(
        postgres_conn_string=None,
        data_file=str(data_file),
        embeddings_path=str(embeddings_path),
        vectorizer_path=str(vectorizer_path),
        batch_size=1,
        backup=False,
        dry_run=True
    )
    
    # Verify no backup was created
    assert report['backup_location'] is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
