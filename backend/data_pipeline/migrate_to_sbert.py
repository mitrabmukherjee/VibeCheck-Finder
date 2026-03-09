"""
Migration script to upgrade from TF-IDF to Sentence-BERT embeddings.

This script regenerates all media item embeddings using Sentence-BERT instead
of TF-IDF, providing true semantic understanding of search queries. It handles
the full dataset efficiently with batch processing and provides detailed
progress tracking.

Features:
- Loads all media items from PostgreSQL or file-based storage
- Generates Sentence-BERT embeddings in batches (batch_size=32)
- Stores embeddings in FileVectorDatabase with new vector_size=384
- Creates backup of existing TF-IDF embeddings before migration
- Tracks progress and logs detailed statistics
- Supports dry-run mode for validation without writing
- Provides rollback capability to restore TF-IDF embeddings

Requirements:
    - 3.1: Provide migration script that regenerates embeddings
    - 3.2: Generate embeddings for all 5,832 media items
    - 3.3: Store new 384-dimensional embeddings in Vector Database
    - 3.4: Ensure Vector Database contains exactly 5,832 embeddings
    - 8.1: Provide migration script executable independently
    - 8.2: Preserve original TF-IDF vectors during migration
"""

import sys
import os
import shutil
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
from ml_engine.ml_engine import MLEngine
from ml_engine.sentence_bert_vectorizer import SentenceBertVectorizer
from database.file_vector_db import FileVectorDatabase
from database.postgres import PostgresDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_backup(
    embeddings_path: str,
    backup_dir: Optional[str] = None
) -> str:
    """
    Create backup of existing TF-IDF embeddings.
    
    This function creates a timestamped backup directory and copies all
    embedding-related files to preserve the current state before migration.
    The backup includes:
    - vectors.npy: The embedding vectors
    - metadata.json: Metadata about embeddings (if exists)
    - ids.json: Media IDs corresponding to vectors
    
    Args:
        embeddings_path: Path to embeddings directory
        backup_dir: Optional custom backup directory path
    
    Returns:
        Path to backup directory
    
    Raises:
        OSError: If backup creation fails
        RuntimeError: If no files are found to backup
    
    Requirements:
        - 8.2: Preserve original TF-IDF vectors during migration
        - 8.3: Create backup before migration
    """
    embeddings_path = Path(embeddings_path)
    
    # Create timestamped backup directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if backup_dir is None:
        backup_dir = embeddings_path.parent / "backups" / f"tfidf_{timestamp}"
    else:
        backup_dir = Path(backup_dir)
    
    logger.info("=" * 60)
    logger.info(f"Creating backup at: {backup_dir}")
    logger.info("=" * 60)
    
    # Create backup directory
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"✓ Backup directory created")
    except Exception as e:
        logger.error(f"Failed to create backup directory: {e}")
        raise OSError(f"Failed to create backup directory: {e}")
    
    # Files to backup
    files_to_backup = [
        "vectors.npy",
        "metadata.json",
        "ids.json"
    ]
    
    backed_up_files = []
    backup_sizes = {}
    
    for filename in files_to_backup:
        source = embeddings_path / filename
        if source.exists():
            try:
                dest = backup_dir / filename
                shutil.copy2(source, dest)
                
                # Verify the copy was successful
                if not dest.exists():
                    raise OSError(f"Backup file was not created: {filename}")
                
                source_size = source.stat().st_size
                dest_size = dest.stat().st_size
                
                if source_size != dest_size:
                    raise OSError(f"Backup file size mismatch: {filename} ({source_size} vs {dest_size} bytes)")
                
                backed_up_files.append(filename)
                backup_sizes[filename] = source_size
                
                # Format size for display
                size_mb = source_size / (1024 * 1024)
                logger.info(f"  ✓ Backed up {filename} ({size_mb:.2f} MB)")
                
            except Exception as e:
                logger.error(f"Failed to backup {filename}: {e}")
                raise OSError(f"Failed to backup {filename}: {e}")
    
    if not backed_up_files:
        logger.warning("No existing embeddings found to backup")
        logger.warning("This is expected for first-time migration")
    else:
        total_size_mb = sum(backup_sizes.values()) / (1024 * 1024)
        logger.info("=" * 60)
        logger.info(f"✓ Backup created successfully: {len(backed_up_files)} files ({total_size_mb:.2f} MB)")
        logger.info(f"✓ Backup location: {backup_dir}")
        logger.info("=" * 60)
    
    return str(backup_dir)


def verify_backup(backup_dir: str) -> bool:
    """
    Verify backup integrity.
    
    This function performs comprehensive validation of the backup:
    1. Checks that backup directory exists
    2. Verifies all required files are present
    3. Validates files are not empty
    4. Attempts to load numpy arrays to ensure they're valid
    5. Validates JSON files can be parsed
    
    Args:
        backup_dir: Path to backup directory
    
    Returns:
        True if backup is valid, False otherwise
    
    Requirements:
        - 8.2: Verify backup integrity before proceeding
        - 8.4: Verify backup integrity before proceeding with migration
    """
    backup_path = Path(backup_dir)
    
    logger.info(f"Verifying backup integrity: {backup_dir}")
    
    # Check 1: Backup directory exists
    if not backup_path.exists():
        logger.error(f"Backup directory does not exist: {backup_dir}")
        return False
    
    # Check 2: Required files are present
    required_files = ["vectors.npy", "ids.json"]
    
    for filename in required_files:
        file_path = backup_path / filename
        if not file_path.exists():
            logger.error(f"Backup missing required file: {filename}")
            return False
        
        # Check 3: File is not empty
        if file_path.stat().st_size == 0:
            logger.error(f"Backup file is empty: {filename}")
            return False
    
    # Check 4: Validate numpy array can be loaded
    try:
        vectors_path = backup_path / "vectors.npy"
        vectors = np.load(vectors_path)
        logger.info(f"  ✓ vectors.npy: shape {vectors.shape}, dtype {vectors.dtype}")
        
        # Verify it's a valid 2D array
        if vectors.ndim != 2:
            logger.error(f"vectors.npy has invalid dimensions: {vectors.ndim} (expected 2)")
            return False
        
        # Verify it contains finite values
        if not np.all(np.isfinite(vectors)):
            logger.error("vectors.npy contains non-finite values (NaN or infinity)")
            return False
            
    except Exception as e:
        logger.error(f"Failed to load vectors.npy: {e}")
        return False
    
    # Check 5: Validate JSON files can be parsed
    try:
        ids_path = backup_path / "ids.json"
        with open(ids_path, 'r') as f:
            ids = json.load(f)
        logger.info(f"  ✓ ids.json: {len(ids)} IDs")
        
        # Verify IDs is a list
        if not isinstance(ids, list):
            logger.error(f"ids.json has invalid format: expected list, got {type(ids)}")
            return False
        
        # Verify vector count matches ID count
        if len(ids) != vectors.shape[0]:
            logger.error(f"ID count mismatch: {len(ids)} IDs vs {vectors.shape[0]} vectors")
            return False
            
    except Exception as e:
        logger.error(f"Failed to load ids.json: {e}")
        return False
    
    # Check 6: Validate metadata.json if present (optional)
    metadata_path = backup_path / "metadata.json"
    if metadata_path.exists():
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            logger.info(f"  ✓ metadata.json: {len(metadata)} entries")
        except Exception as e:
            logger.warning(f"Failed to load metadata.json (non-critical): {e}")
    
    logger.info("✓ Backup verification passed - all checks successful")
    return True


def load_media_from_postgres(postgres_db: PostgresDatabase) -> List[Dict[str, Any]]:
    """
    Load all media items from PostgreSQL database.
    
    Args:
        postgres_db: PostgresDatabase instance
    
    Returns:
        List of media item dictionaries
    
    Raises:
        Exception: If database query fails
    """
    logger.info("Loading media items from PostgreSQL...")
    
    try:
        media_items = postgres_db.get_all_media()
        logger.info(f"Loaded {len(media_items)} media items from PostgreSQL")
        return media_items
    except Exception as e:
        logger.error(f"Failed to load media from PostgreSQL: {e}")
        raise


def load_media_from_file(data_path: str) -> List[Dict[str, Any]]:
    """
    Load media items from CSV file as fallback.
    
    Args:
        data_path: Path to CSV file
    
    Returns:
        List of media item dictionaries
    
    Raises:
        FileNotFoundError: If CSV file doesn't exist
    """
    logger.info(f"Loading media items from file: {data_path}")
    
    import pandas as pd
    
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Data file not found: {data_path}")
    
    df = pd.read_csv(data_path)
    
    # Convert to list of dictionaries
    media_items = []
    for _, row in df.iterrows():
        media_items.append({
            'id': str(row['id']),
            'title': row['title'],
            'description': row['description'],
            'media_type': row.get('type', 'tv_show')
        })
    
    logger.info(f"Loaded {len(media_items)} media items from file")
    return media_items


def migrate_to_sbert(
    postgres_conn_string: Optional[str] = None,
    data_file: Optional[str] = None,
    embeddings_path: str = "backend/embeddings",
    vectorizer_path: str = "backend/models",
    batch_size: int = 32,
    backup: bool = True,
    dry_run: bool = False,
    model_name: str = "all-MiniLM-L6-v2"
) -> Dict[str, Any]:
    """
    Migrate all embeddings from TF-IDF to Sentence-BERT.
    
    This function performs the complete migration process:
    1. Creates backup of existing TF-IDF embeddings
    2. Loads all media items from PostgreSQL or file
    3. Generates Sentence-BERT embeddings in batches
    4. Stores embeddings in FileVectorDatabase
    5. Tracks progress and generates detailed report
    
    Args:
        postgres_conn_string: PostgreSQL connection string (optional)
        data_file: Path to CSV file as fallback (optional)
        embeddings_path: Path to embeddings directory
        vectorizer_path: Path to vectorizer models directory
        batch_size: Batch size for encoding (default: 32)
        backup: Whether to backup existing embeddings (default: True)
        dry_run: If True, validate without writing (default: False)
        model_name: Sentence-BERT model name (default: "all-MiniLM-L6-v2")
    
    Returns:
        Migration report dictionary with statistics and any errors:
        {
            'status': 'completed' | 'partial' | 'failed',
            'total_items': int,
            'successful': int,
            'failed': int,
            'duration_seconds': float,
            'errors': List[str],  # Error messages
            'failed_items': List[Dict],  # Detailed failure info
            'backup_location': str | None,
            'new_collection': str,
            'old_collection': str,
            'dry_run': bool
        }
    
    Raises:
        Exception: If migration fails critically
    
    Requirements:
        - 3.1: Provide migration script that regenerates embeddings
        - 3.2: Generate embeddings for all media items
        - 3.3: Store new 384-dimensional embeddings
        - 3.4: Ensure Vector Database contains all embeddings
        - 8.1: Execute independently of main application
        - 8.2: Preserve original TF-IDF vectors during migration
    """
    start_time = datetime.now()
    report = {
        'status': 'started',
        'total_items': 0,
        'successful': 0,
        'failed': 0,
        'duration_seconds': 0.0,
        'errors': [],
        'failed_items': [],
        'backup_location': None,
        'new_collection': 'file_vector_db_sbert',
        'old_collection': 'file_vector_db_tfidf',
        'dry_run': dry_run
    }
    
    try:
        # Step 1: Create backup if requested
        if backup and not dry_run:
            logger.info("=" * 60)
            logger.info("STEP 1: Creating backup of existing embeddings")
            logger.info("=" * 60)
            
            backup_dir = create_backup(embeddings_path)
            report['backup_location'] = backup_dir
            
            # Verify backup integrity (allow empty backup for first-time migration)
            # Check if any files were backed up
            backup_path = Path(backup_dir)
            has_files = any((backup_path / f).exists() for f in ["vectors.npy", "ids.json", "metadata.json"])
            
            if has_files:
                # Verify backup if files exist
                if not verify_backup(backup_dir):
                    raise RuntimeError("Backup verification failed")
            else:
                logger.info("✓ Empty backup (no existing embeddings) - proceeding with migration")
        else:
            if dry_run:
                logger.info("Dry run mode: Skipping backup creation")
            else:
                logger.info("Backup disabled: Skipping backup creation")
        
        # Step 2: Load media items
        logger.info("=" * 60)
        logger.info("STEP 2: Loading media items")
        logger.info("=" * 60)
        
        media_items = []
        
        # Try PostgreSQL first
        if postgres_conn_string or os.getenv("POSTGRES_HOST"):
            try:
                postgres_db = PostgresDatabase()
                media_items = load_media_from_postgres(postgres_db)
                postgres_db.close()
            except Exception as e:
                logger.warning(f"PostgreSQL load failed: {e}")
                if data_file:
                    logger.info("Falling back to file-based loading")
                    media_items = load_media_from_file(data_file)
                else:
                    raise
        elif data_file:
            media_items = load_media_from_file(data_file)
        else:
            raise ValueError(
                "Must provide either postgres_conn_string or data_file"
            )
        
        report['total_items'] = len(media_items)
        
        if len(media_items) == 0:
            raise ValueError("No media items found to migrate")
        
        # Step 3: Initialize Sentence-BERT vectorizer
        logger.info("=" * 60)
        logger.info("STEP 3: Initializing Sentence-BERT vectorizer")
        logger.info("=" * 60)
        
        logger.info(f"Model: {model_name}")
        logger.info(f"Expected embedding dimension: 384")
        
        ml_engine = MLEngine(
            vectorizer_path=vectorizer_path,
            embeddings_path=embeddings_path,
            vectorizer_type="sbert",
            model_name=model_name
        )
        
        logger.info("Sentence-BERT vectorizer initialized successfully")
        
        # Step 4: Generate embeddings in batches with error handling
        logger.info("=" * 60)
        logger.info("STEP 4: Generating Sentence-BERT embeddings")
        logger.info("=" * 60)
        
        logger.info(f"Batch size: {batch_size}")
        logger.info(f"Total items: {len(media_items)}")
        logger.info(f"Estimated batches: {(len(media_items) + batch_size - 1) // batch_size}")
        
        # Process items with individual error handling
        successful_embeddings = []
        successful_ids = []
        failed_items = []
        
        # Process in batches for efficiency
        for batch_start in range(0, len(media_items), batch_size):
            batch_end = min(batch_start + batch_size, len(media_items))
            batch_items = media_items[batch_start:batch_end]
            
            batch_descriptions = []
            batch_ids = []
            batch_indices = []
            
            # Prepare batch, validating each item
            for i, item in enumerate(batch_items):
                try:
                    # Validate item has required fields
                    if 'id' not in item:
                        raise ValueError("Media item missing 'id' field")
                    if 'description' not in item:
                        raise ValueError("Media item missing 'description' field")
                    
                    # Validate description is not empty or NaN
                    description = item['description']
                    
                    # Check for pandas NaN
                    if description is None or (isinstance(description, float) and np.isnan(description)):
                        raise ValueError("Media item has empty description")
                    
                    description = str(description).strip()
                    if not description or description.lower() == 'nan':
                        raise ValueError("Media item has empty description")
                        raise ValueError("Media item has empty description")
                    
                    batch_descriptions.append(description)
                    batch_ids.append(str(item['id']))
                    batch_indices.append(batch_start + i)
                    
                except Exception as e:
                    error_msg = f"Item validation failed for ID {item.get('id', 'unknown')}: {str(e)}"
                    logger.warning(error_msg)
                    failed_items.append({
                        'id': item.get('id', 'unknown'),
                        'error': str(e),
                        'stage': 'validation'
                    })
                    report['errors'].append(error_msg)
            
            # Skip empty batches
            if not batch_descriptions:
                continue
            
            # Generate embeddings for this batch
            try:
                logger.info(f"Processing batch {batch_start // batch_size + 1}: items {batch_start + 1}-{batch_end}")
                
                batch_embeddings = ml_engine.compute_embeddings(
                    descriptions=batch_descriptions,
                    media_ids=batch_ids,
                    batch_size=len(batch_descriptions)  # Process all at once
                )
                
                # Validate batch embeddings
                if batch_embeddings.shape[0] != len(batch_descriptions):
                    raise ValueError(
                        f"Embedding count mismatch: expected {len(batch_descriptions)}, got {batch_embeddings.shape[0]}"
                    )
                
                if batch_embeddings.shape[1] != 384:
                    raise ValueError(
                        f"Expected 384-dimensional embeddings, got {batch_embeddings.shape[1]}"
                    )
                
                # Validate each embedding individually
                for i, (media_id, embedding) in enumerate(zip(batch_ids, batch_embeddings)):
                    try:
                        # Check for non-finite values
                        if not np.all(np.isfinite(embedding)):
                            raise ValueError("Embedding contains non-finite values (NaN or infinity)")
                        
                        # Check dimensionality
                        if embedding.shape[0] != 384:
                            raise ValueError(f"Expected 384 dimensions, got {embedding.shape[0]}")
                        
                        successful_embeddings.append(embedding)
                        successful_ids.append(media_id)
                        
                    except Exception as e:
                        error_msg = f"Embedding validation failed for ID {media_id}: {str(e)}"
                        logger.warning(error_msg)
                        failed_items.append({
                            'id': media_id,
                            'error': str(e),
                            'stage': 'embedding_validation'
                        })
                        report['errors'].append(error_msg)
                
                logger.info(f"  Successfully processed {len(batch_ids)} items")
                
            except Exception as e:
                # Batch-level error - try processing items individually
                error_msg = f"Batch encoding failed for items {batch_start + 1}-{batch_end}: {str(e)}"
                logger.warning(error_msg)
                logger.info("  Attempting individual item processing...")
                
                # Process items one by one
                for i, (description, media_id) in enumerate(zip(batch_descriptions, batch_ids)):
                    try:
                        individual_embedding = ml_engine.compute_embeddings(
                            descriptions=[description],
                            media_ids=[media_id],
                            batch_size=1
                        )
                        
                        # Validate individual embedding
                        if individual_embedding.shape != (1, 384):
                            raise ValueError(f"Expected shape (1, 384), got {individual_embedding.shape}")
                        
                        if not np.all(np.isfinite(individual_embedding)):
                            raise ValueError("Embedding contains non-finite values")
                        
                        successful_embeddings.append(individual_embedding[0])
                        successful_ids.append(media_id)
                        
                    except Exception as item_error:
                        error_msg = f"Individual encoding failed for ID {media_id}: {str(item_error)}"
                        logger.warning(error_msg)
                        failed_items.append({
                            'id': media_id,
                            'error': str(item_error),
                            'stage': 'encoding'
                        })
                        report['errors'].append(error_msg)
        
        # Convert to numpy array
        if successful_embeddings:
            embeddings = np.array(successful_embeddings)
            media_ids = successful_ids
            
            logger.info(f"Generated {embeddings.shape[0]} embeddings successfully")
            logger.info(f"Embedding dimension: {embeddings.shape[1]}")
            logger.info(f"Failed items: {len(failed_items)}")
            
            report['successful'] = len(embeddings)
            report['failed'] = len(failed_items)
            report['failed_items'] = failed_items
        else:
            raise ValueError("No embeddings were generated successfully")
        
        # Step 5: Store embeddings in FileVectorDatabase
        if not dry_run:
            logger.info("=" * 60)
            logger.info("STEP 5: Storing embeddings in FileVectorDatabase")
            logger.info("=" * 60)
            
            # Initialize FileVectorDatabase with 384-dimensional vectors
            vector_db = FileVectorDatabase(
                storage_path=embeddings_path,
                vector_size=384
            )
            
            # Clear existing embeddings
            logger.info("Clearing existing embeddings...")
            vector_db.clear()
            
            # Insert new embeddings with metadata
            logger.info("Inserting new embeddings...")
            embedding_date = datetime.now().isoformat()
            
            insertion_errors = []
            for i, (media_id, embedding) in enumerate(zip(media_ids, embeddings)):
                try:
                    metadata = {
                        'vectorizer_type': 'sbert',
                        'model_version': model_name,
                        'embedding_date': embedding_date,
                        'media_id': media_id
                    }
                    
                    vector_db.insert(
                        media_id=media_id,
                        vector=embedding.tolist(),
                        metadata=metadata
                    )
                    
                    # Log progress every 1000 items
                    if (i + 1) % 1000 == 0:
                        logger.info(f"  Inserted {i + 1}/{len(media_ids)} embeddings")
                
                except Exception as e:
                    error_msg = f"Failed to insert embedding for ID {media_id}: {str(e)}"
                    logger.warning(error_msg)
                    insertion_errors.append({
                        'id': media_id,
                        'error': str(e),
                        'stage': 'insertion'
                    })
                    report['errors'].append(error_msg)
            
            logger.info(f"Inserted {len(media_ids) - len(insertion_errors)}/{len(media_ids)} embeddings")
            
            if insertion_errors:
                logger.warning(f"{len(insertion_errors)} embeddings failed to insert")
                report['failed'] += len(insertion_errors)
                report['successful'] -= len(insertion_errors)
                report['failed_items'].extend(insertion_errors)
            
            # Verify count
            final_count = vector_db.count()
            logger.info(f"Final embedding count: {final_count}")
            
            if final_count != (len(media_ids) - len(insertion_errors)):
                logger.warning(
                    f"Embedding count mismatch: expected {len(media_ids) - len(insertion_errors)}, got {final_count}"
                )
            
            vector_db.close()
        else:
            logger.info("=" * 60)
            logger.info("STEP 5: Dry run validation")
            logger.info("=" * 60)
            logger.info("Dry run mode: Skipping database write")
            logger.info(f"✓ Would insert {len(media_ids)} embeddings")
            logger.info(f"✓ Embedding dimension: 384")
            logger.info(f"✓ All embeddings validated successfully")
            
            # Provide sample of what would be stored
            if len(media_ids) > 0:
                logger.info("\nSample embedding metadata:")
                logger.info(f"  Media ID: {media_ids[0]}")
                logger.info(f"  Vector shape: {embeddings[0].shape}")
                logger.info(f"  Vector sample: [{embeddings[0][0]:.6f}, {embeddings[0][1]:.6f}, ...]")
                logger.info(f"  Model: {model_name}")
                logger.info(f"  Vectorizer type: sbert")
        
        # Step 6: Generate report
        logger.info("=" * 60)
        logger.info("STEP 6: Migration complete")
        logger.info("=" * 60)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        report['duration_seconds'] = duration
        
        # Determine final status
        if report['failed'] == 0:
            report['status'] = 'completed'
        elif report['successful'] > 0:
            report['status'] = 'partial'
        else:
            report['status'] = 'failed'
        
        logger.info(f"Status: {report['status']}")
        logger.info(f"Total items: {report['total_items']}")
        logger.info(f"Successful: {report['successful']}")
        logger.info(f"Failed: {report['failed']}")
        logger.info(f"Success rate: {report['successful'] / report['total_items'] * 100:.1f}%")
        logger.info(f"Duration: {duration:.2f} seconds")
        
        if report['failed'] > 0:
            logger.warning(f"\n{report['failed']} items failed to process:")
            for failed_item in report['failed_items'][:10]:  # Show first 10
                logger.warning(f"  - ID {failed_item['id']}: {failed_item['error']} (stage: {failed_item['stage']})")
            if len(report['failed_items']) > 10:
                logger.warning(f"  ... and {len(report['failed_items']) - 10} more (see report file)")
        
        if report['backup_location']:
            logger.info(f"Backup location: {report['backup_location']}")
        
        return report
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        report['status'] = 'failed'
        report['duration_seconds'] = duration
        report['errors'].append(str(e))
        
        return report


def rollback_migration(
    backup_dir: str,
    embeddings_path: str = "backend/embeddings"
) -> bool:
    """
    Rollback migration by restoring TF-IDF embeddings from backup.
    
    This function safely restores the previous TF-IDF embeddings from a backup
    directory. It performs the following steps:
    1. Verifies the backup directory exists and is valid
    2. Validates backup integrity before restoration
    3. Creates a backup of current state (in case rollback needs to be undone)
    4. Restores all files from the backup
    5. Verifies the restoration was successful
    
    Args:
        backup_dir: Path to backup directory
        embeddings_path: Path to embeddings directory
    
    Returns:
        True if rollback successful, False otherwise
    
    Requirements:
        - 8.4: Provide rollback mechanism to restore TF-IDF functionality
        - 8.5: When rollback is executed, restore previous TF-IDF vectors
    """
    logger.info("=" * 60)
    logger.info("ROLLBACK: Restoring TF-IDF embeddings from backup")
    logger.info("=" * 60)
    
    try:
        backup_path = Path(backup_dir)
        embeddings_path = Path(embeddings_path)
        
        # Step 1: Verify backup directory exists
        if not backup_path.exists():
            logger.error(f"✗ Backup directory not found: {backup_dir}")
            return False
        
        logger.info(f"Backup directory: {backup_dir}")
        
        # Step 2: Verify backup integrity before restoring
        logger.info("\nStep 1: Verifying backup integrity...")
        if not verify_backup(backup_dir):
            logger.error("✗ Backup verification failed, cannot rollback")
            logger.error("✗ The backup may be corrupted or incomplete")
            return False
        
        # Step 3: Create backup of current state (in case we need to undo rollback)
        logger.info("\nStep 2: Creating backup of current state...")
        try:
            current_backup = create_backup(
                embeddings_path=str(embeddings_path),
                backup_dir=str(embeddings_path.parent / "backups" / f"pre_rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            )
            logger.info(f"✓ Current state backed up to: {current_backup}")
        except Exception as e:
            logger.warning(f"⚠ Failed to backup current state: {e}")
            logger.warning("⚠ Continuing with rollback anyway...")
        
        # Step 4: Restore files from backup
        logger.info("\nStep 3: Restoring files from backup...")
        
        files_to_restore = [
            "vectors.npy",
            "metadata.json",
            "ids.json"
        ]
        
        restored_files = []
        for filename in files_to_restore:
            source = backup_path / filename
            if source.exists():
                try:
                    dest = embeddings_path / filename
                    
                    # Ensure destination directory exists
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(source, dest)
                    
                    # Verify copy was successful
                    if not dest.exists():
                        raise OSError(f"Restored file was not created: {filename}")
                    
                    source_size = source.stat().st_size
                    dest_size = dest.stat().st_size
                    
                    if source_size != dest_size:
                        raise OSError(f"Restored file size mismatch: {filename}")
                    
                    restored_files.append(filename)
                    size_mb = source_size / (1024 * 1024)
                    logger.info(f"  ✓ Restored {filename} ({size_mb:.2f} MB)")
                    
                except Exception as e:
                    logger.error(f"  ✗ Failed to restore {filename}: {e}")
                    raise
        
        if not restored_files:
            logger.error("✗ No files were restored")
            return False
        
        # Step 5: Verify restoration was successful
        logger.info("\nStep 4: Verifying restoration...")
        try:
            # Load and validate the restored vectors
            vectors_path = embeddings_path / "vectors.npy"
            vectors = np.load(vectors_path)
            logger.info(f"  ✓ Loaded vectors: shape {vectors.shape}, dtype {vectors.dtype}")
            
            # Load and validate the restored IDs
            ids_path = embeddings_path / "ids.json"
            with open(ids_path, 'r') as f:
                ids = json.load(f)
            logger.info(f"  ✓ Loaded IDs: {len(ids)} entries")
            
            # Verify counts match
            if len(ids) != vectors.shape[0]:
                raise ValueError(f"ID count mismatch: {len(ids)} IDs vs {vectors.shape[0]} vectors")
            
            logger.info(f"  ✓ Verification passed: {len(ids)} embeddings restored")
            
        except Exception as e:
            logger.error(f"✗ Restoration verification failed: {e}")
            return False
        
        # Success!
        logger.info("=" * 60)
        logger.info("✓ Rollback completed successfully!")
        logger.info("=" * 60)
        logger.info(f"✓ Restored {len(restored_files)} files from backup")
        logger.info(f"✓ {len(ids)} TF-IDF embeddings have been restored")
        logger.info("\nNext steps:")
        logger.info("  1. Restart the backend server with VECTORIZER_TYPE=tfidf")
        logger.info("  2. Verify search functionality works as expected")
        logger.info(f"  3. If needed, you can undo this rollback using: {current_backup}")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"✗ Rollback failed: {e}")
        logger.error("=" * 60)
        logger.error("The system may be in an inconsistent state.")
        logger.error("Please check the embeddings directory and restore manually if needed.")
        return False


def main():
    """Main entry point for migration script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate embeddings from TF-IDF to Sentence-BERT"
    )
    parser.add_argument(
        '--data-file',
        type=str,
        default='data/netflix_media.csv',
        help='Path to CSV file (fallback if PostgreSQL unavailable)'
    )
    parser.add_argument(
        '--embeddings-path',
        type=str,
        default='backend/embeddings',
        help='Path to embeddings directory'
    )
    parser.add_argument(
        '--vectorizer-path',
        type=str,
        default='backend/models',
        help='Path to vectorizer models directory'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='Batch size for encoding'
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Skip backup creation'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate without writing to database'
    )
    parser.add_argument(
        '--model-name',
        type=str,
        default='all-MiniLM-L6-v2',
        help='Sentence-BERT model name'
    )
    parser.add_argument(
        '--rollback',
        type=str,
        metavar='BACKUP_DIR',
        help='Rollback migration from backup directory'
    )
    
    args = parser.parse_args()
    
    # Handle rollback
    if args.rollback:
        success = rollback_migration(
            backup_dir=args.rollback,
            embeddings_path=args.embeddings_path
        )
        sys.exit(0 if success else 1)
    
    # Run migration
    logger.info("=" * 60)
    logger.info("SENTENCE-BERT MIGRATION SCRIPT")
    logger.info("=" * 60)
    logger.info(f"Data file: {args.data_file}")
    logger.info(f"Embeddings path: {args.embeddings_path}")
    logger.info(f"Vectorizer path: {args.vectorizer_path}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Backup: {not args.no_backup}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info(f"Model: {args.model_name}")
    logger.info("=" * 60)
    
    report = migrate_to_sbert(
        data_file=args.data_file,
        embeddings_path=args.embeddings_path,
        vectorizer_path=args.vectorizer_path,
        batch_size=args.batch_size,
        backup=not args.no_backup,
        dry_run=args.dry_run,
        model_name=args.model_name
    )
    
    # Save report to file
    report_path = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"\nMigration report saved to: {report_path}")
    
    # Exit with appropriate code
    if report['status'] == 'completed':
        logger.info("\n✓ Migration completed successfully!")
        logger.info("✓ All items processed without errors")
        logger.info("✓ Restart the backend server with VECTORIZER_TYPE=sbert")
        sys.exit(0)
    elif report['status'] == 'partial':
        logger.warning("\n⚠ Migration completed with errors!")
        logger.warning(f"⚠ {report['successful']} items succeeded, {report['failed']} items failed")
        logger.warning(f"⚠ Success rate: {report['successful'] / report['total_items'] * 100:.1f}%")
        logger.info("✓ You can still use the successfully migrated embeddings")
        logger.info("✓ Restart the backend server with VECTORIZER_TYPE=sbert")
        logger.info(f"✓ Review failed items in: {report_path}")
        sys.exit(0)  # Exit successfully for partial migration
    else:
        logger.error("\n✗ Migration failed!")
        logger.error(f"✗ No items were successfully processed")
        logger.error(f"Errors: {report['errors'][:5]}")  # Show first 5 errors
        if report['backup_location']:
            logger.info(f"\nTo rollback, run:")
            logger.info(f"  python migrate_to_sbert.py --rollback {report['backup_location']}")
        sys.exit(1)


if __name__ == '__main__':
    main()
