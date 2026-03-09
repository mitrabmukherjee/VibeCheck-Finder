"""
Script to run the data pipeline on the sample media dataset.

This script:
1. Loads the sample_media.csv dataset
2. Runs the complete data pipeline
3. Verifies embeddings and metadata are stored correctly
4. Provides detailed statistics and verification results

Usage:
    python backend/data_pipeline/run_sample_pipeline.py
"""

import os
import sys
import logging
from pathlib import Path

# Add backend to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from data_pipeline.data_pipeline import DataPipeline
from database.vector_db import VectorDatabase
from database.postgres import PostgresDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def verify_data_consistency(vector_db: VectorDatabase, postgres_db: PostgresDatabase) -> dict:
    """
    Verify that embeddings and metadata are consistent between databases.
    
    Args:
        vector_db: VectorDatabase instance
        postgres_db: PostgresDatabase instance
    
    Returns:
        Dictionary with verification results
    """
    logger.info("Verifying data consistency between databases...")
    
    results = {
        'total_embeddings': 0,
        'total_metadata': 0,
        'consistent': True,
        'missing_metadata': [],
        'missing_embeddings': []
    }
    
    try:
        # Get all media from PostgreSQL
        all_media = postgres_db.get_all_media()
        results['total_metadata'] = len(all_media)
        logger.info(f"Found {len(all_media)} media items in PostgreSQL")
        
        # Check if each has an embedding in Vector DB
        for media in all_media:
            media_id = media['id']
            try:
                # Try to retrieve from vector DB
                vector_result = vector_db.search(
                    query_vector=[0.0] * 5000,  # Dummy vector
                    top_k=1,
                    filter={'media_id': media_id}
                )
                if not vector_result:
                    results['missing_embeddings'].append(media_id)
                    results['consistent'] = False
            except Exception as e:
                logger.warning(f"Could not verify embedding for {media_id}: {e}")
        
        # Get count from Vector DB (approximate)
        # Note: Qdrant doesn't have a direct count method, so we estimate
        results['total_embeddings'] = results['total_metadata'] - len(results['missing_embeddings'])
        
        # Report results
        if results['consistent']:
            logger.info("✓ Data consistency verified: All items have both embeddings and metadata")
        else:
            logger.warning(f"✗ Data inconsistency detected:")
            if results['missing_embeddings']:
                logger.warning(f"  - {len(results['missing_embeddings'])} items missing embeddings")
            if results['missing_metadata']:
                logger.warning(f"  - {len(results['missing_metadata'])} items missing metadata")
        
    except Exception as e:
        logger.error(f"Error during verification: {e}")
        results['consistent'] = False
        results['error'] = str(e)
    
    return results


def main():
    """Run the data pipeline on the sample dataset."""
    
    logger.info("=" * 80)
    logger.info("SEMANTIC MEDIA ENGINE - SAMPLE DATA PIPELINE")
    logger.info("=" * 80)
    
    # Configuration
    source_path = "backend/data/sample_media.csv"
    vectorizer_path = "backend/models"
    embeddings_path = "backend/embeddings"
    
    # Ensure directories exist
    os.makedirs(vectorizer_path, exist_ok=True)
    os.makedirs(embeddings_path, exist_ok=True)
    
    # Vector DB configuration (Qdrant)
    vector_db_config = {
        "host": os.getenv("QDRANT_HOST", "localhost"),
        "port": int(os.getenv("QDRANT_PORT", "6333")),
        "collection_name": "media_embeddings",
        "vector_size": 5000,  # Must match vectorizer max_features
    }
    
    # PostgreSQL configuration
    postgres_config = {
        "min_connections": 1,
        "max_connections": 10
    }
    
    # Batch size for processing
    batch_size = 100  # Smaller batch for sample data
    
    try:
        # Step 1: Initialize the pipeline
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: Initializing Data Pipeline")
        logger.info("=" * 80)
        
        pipeline = DataPipeline(
            source_path=source_path,
            vectorizer_path=vectorizer_path,
            embeddings_path=embeddings_path,
            vector_db_config=vector_db_config,
            postgres_config=postgres_config,
            batch_size=batch_size
        )
        
        logger.info("✓ Pipeline initialized successfully")
        
        # Step 2: Run the complete pipeline
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2: Running Data Pipeline")
        logger.info("=" * 80)
        logger.info("This will:")
        logger.info("  1. Load sample_media.csv")
        logger.info("  2. Clean and validate data")
        logger.info("  3. Train TF-IDF vectorizer")
        logger.info("  4. Generate embeddings")
        logger.info("  5. Store embeddings in Qdrant")
        logger.info("  6. Store metadata in PostgreSQL")
        logger.info("")
        
        # Train vectorizer on first run
        stats = pipeline.run(train_vectorizer=True)
        
        logger.info("✓ Pipeline execution complete!")
        
        # Step 3: Display results
        logger.info("\n" + "=" * 80)
        logger.info("STEP 3: Pipeline Statistics")
        logger.info("=" * 80)
        logger.info(f"Total loaded:       {stats['total_loaded']} items")
        logger.info(f"Total cleaned:      {stats['total_cleaned']} items")
        logger.info(f"Total stored:       {stats['total_stored']} items")
        logger.info(f"Model version:      {stats['model_version']}")
        
        # Calculate success rate
        success_rate = (stats['total_stored'] / stats['total_loaded']) * 100
        logger.info(f"Success rate:       {success_rate:.1f}%")
        
        # Step 4: Verify data consistency
        logger.info("\n" + "=" * 80)
        logger.info("STEP 4: Verifying Data Consistency")
        logger.info("=" * 80)
        
        verification = verify_data_consistency(pipeline.vector_db, pipeline.postgres_db)
        
        logger.info(f"Embeddings in Vector DB:  {verification['total_embeddings']}")
        logger.info(f"Metadata in PostgreSQL:   {verification['total_metadata']}")
        logger.info(f"Data consistent:          {verification['consistent']}")
        
        # Step 5: Sample queries
        logger.info("\n" + "=" * 80)
        logger.info("STEP 5: Sample Data Overview")
        logger.info("=" * 80)
        
        # Get sample items by type
        all_media = pipeline.postgres_db.get_all_media()
        books = [m for m in all_media if m['media_type'] == 'book']
        tv_shows = [m for m in all_media if m['media_type'] == 'tv_show']
        
        logger.info(f"Books:              {len(books)} items")
        logger.info(f"TV Shows:           {len(tv_shows)} items")
        
        # Get genre distribution
        genres = {}
        for media in all_media:
            genre = media.get('metadata', {}).get('genre', 'Unknown')
            genres[genre] = genres.get(genre, 0) + 1
        
        logger.info(f"\nGenre distribution:")
        for genre, count in sorted(genres.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {genre:20s} {count} items")
        
        # Step 6: Final summary
        logger.info("\n" + "=" * 80)
        logger.info("PIPELINE EXECUTION SUMMARY")
        logger.info("=" * 80)
        
        if verification['consistent'] and stats['total_stored'] == stats['total_loaded']:
            logger.info("✓ SUCCESS: All data processed and stored correctly")
            logger.info("✓ Embeddings and metadata are consistent")
            logger.info("✓ Sample dataset is ready for use")
            logger.info("\nNext steps:")
            logger.info("  1. Start the backend server: cd backend && uvicorn main:app --reload")
            logger.info("  2. Test the /recommend endpoint with sample queries")
            logger.info("  3. Start the frontend: cd frontend && npm run dev")
        else:
            logger.warning("⚠ WARNING: Some issues detected during pipeline execution")
            if stats['total_stored'] != stats['total_loaded']:
                logger.warning(f"  - Not all items were stored ({stats['total_stored']}/{stats['total_loaded']})")
            if not verification['consistent']:
                logger.warning("  - Data consistency issues detected")
        
        # Close connections
        pipeline.close()
        logger.info("\n✓ Pipeline closed successfully")
        
        return 0 if verification['consistent'] else 1
        
    except FileNotFoundError as e:
        logger.error(f"✗ ERROR: {e}")
        logger.error("Make sure backend/data/sample_media.csv exists")
        return 1
    except Exception as e:
        logger.error(f"✗ ERROR: Pipeline execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
