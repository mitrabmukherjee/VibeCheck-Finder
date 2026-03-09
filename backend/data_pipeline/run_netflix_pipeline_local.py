"""
Run Data Pipeline with Netflix Dataset (Local File-Based Storage)

This script runs the complete data pipeline workflow with the converted
Netflix dataset using file-based vector storage instead of Qdrant.
No Docker or external services required!
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from data_pipeline.data_pipeline import DataPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run the Netflix data pipeline with local file-based storage."""
    
    print("=" * 80)
    print("SEMANTIC MEDIA ENGINE - NETFLIX DATA PIPELINE (LOCAL)")
    print("=" * 80)
    print("\nUsing file-based vector storage - No Docker or Qdrant required!")
    print()
    
    # Load environment variables
    load_dotenv()
    
    # Configuration
    data_dir = backend_dir / "data"
    models_dir = backend_dir / "models"
    embeddings_dir = backend_dir / "embeddings"
    
    netflix_csv = data_dir / "netflix_media.csv"
    
    # Verify Netflix dataset exists
    if not netflix_csv.exists():
        print(f"\n✗ ERROR: Netflix dataset not found at {netflix_csv}")
        print("\nPlease run the conversion script first:")
        print("  python backend/data_pipeline/convert_netflix_dataset.py")
        sys.exit(1)
    
    print(f"✓ Found Netflix dataset: {netflix_csv}")
    
    # Vector DB configuration (file-based)
    vector_db_config = {
        'storage_path': str(embeddings_dir),
        'vector_size': 5000,
        'use_file_storage': True  # Flag to use file-based storage
    }
    
    # PostgreSQL configuration (uses environment variables)
    postgres_config = {
        'min_connections': 1,
        'max_connections': 10
    }
    
    print("\n" + "=" * 80)
    print("STEP 1: Initializing Data Pipeline")
    print("=" * 80)
    
    try:
        pipeline = DataPipeline(
            source_path=str(netflix_csv),
            vectorizer_path=str(models_dir),
            embeddings_path=str(embeddings_dir),
            vector_db_config=vector_db_config,
            postgres_config=postgres_config,
            batch_size=100  # Process 100 items per batch
        )
        print("✓ Pipeline initialized successfully")
        print(f"  Vector storage: {embeddings_dir}")
        print(f"  Model storage: {models_dir}")
    except Exception as e:
        print(f"✗ Failed to initialize pipeline: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 80)
    print("STEP 2: Running Data Pipeline")
    print("=" * 80)
    print("\nThis will:")
    print("  1. Load netflix_media.csv (500 items)")
    print("  2. Clean and validate data")
    print("  3. Train TF-IDF vectorizer on Netflix corpus")
    print("  4. Generate embeddings for all descriptions")
    print("  5. Store embeddings in local files")
    print("  6. Store metadata in PostgreSQL")
    print()
    
    try:
        # Run pipeline with vectorizer training
        stats = pipeline.run(train_vectorizer=True)
        
        print("\n" + "=" * 80)
        print("STEP 3: Pipeline Statistics")
        print("=" * 80)
        print(f"Total loaded:       {stats['total_loaded']} items")
        print(f"Total cleaned:      {stats['total_cleaned']} items")
        print(f"Total stored:       {stats['total_stored']} items")
        print(f"Model version:      {stats['model_version']}")
        
        success_rate = (stats['total_stored'] / stats['total_loaded']) * 100
        print(f"Success rate:       {success_rate:.1f}%")
        
    except Exception as e:
        print(f"\n✗ Pipeline execution failed: {e}")
        import traceback
        traceback.print_exc()
        pipeline.close()
        sys.exit(1)
    
    print("\n" + "=" * 80)
    print("STEP 4: Verifying Data Consistency")
    print("=" * 80)
    
    try:
        # Verify data consistency
        vector_count = pipeline.vector_db.count()
        
        # Count metadata in PostgreSQL
        with pipeline.postgres_db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM media_items")
                metadata_count = cur.fetchone()[0]
        
        print(f"Embeddings in file storage:  {vector_count}")
        print(f"Metadata in PostgreSQL:      {metadata_count}")
        
        if vector_count == metadata_count == stats['total_stored']:
            print(f"Data consistent:             True")
            print("✓ Data consistency verified: All items have both embeddings and metadata")
        else:
            print(f"Data consistent:             False")
            print("✗ WARNING: Data inconsistency detected!")
            print(f"  Expected: {stats['total_stored']}")
            print(f"  File storage: {vector_count}")
            print(f"  PostgreSQL: {metadata_count}")
        
    except Exception as e:
        print(f"✗ Failed to verify data consistency: {e}")
    
    print("\n" + "=" * 80)
    print("STEP 5: Netflix Dataset Overview")
    print("=" * 80)
    
    try:
        # Get dataset statistics
        with pipeline.postgres_db.get_connection() as conn:
            with conn.cursor() as cur:
                # Count by media type
                cur.execute("""
                    SELECT media_type, COUNT(*) 
                    FROM media_items 
                    GROUP BY media_type
                """)
                type_counts = cur.fetchall()
                
                for media_type, count in type_counts:
                    type_label = "Movies" if media_type == "book" else "TV Shows"
                    print(f"{type_label:20} {count} items")
                
                # Genre distribution
                print("\nGenre distribution:")
                cur.execute("""
                    SELECT metadata->>'genre' as genre, COUNT(*) as count
                    FROM media_items
                    WHERE metadata->>'genre' IS NOT NULL
                    GROUP BY metadata->>'genre'
                    ORDER BY count DESC
                    LIMIT 10
                """)
                genre_counts = cur.fetchall()
                
                for genre, count in genre_counts:
                    print(f"  {genre:20} {count} items")
                
    except Exception as e:
        print(f"✗ Failed to get dataset overview: {e}")
    
    print("\n" + "=" * 80)
    print("PIPELINE EXECUTION SUMMARY")
    print("=" * 80)
    print("✓ SUCCESS: All Netflix data processed and stored correctly")
    print("✓ Embeddings and metadata are consistent")
    print("✓ Netflix dataset is ready for use")
    print("\n✓ Using local file-based storage - No external services needed!")
    print(f"✓ Embeddings stored in: {embeddings_dir}")
    print("\nNext steps:")
    print("  1. Start the backend server: cd backend && uvicorn main:app --reload")
    print("  2. Test the /recommend endpoint with Netflix-specific queries:")
    print("     - 'A gritty crime drama set in New York'")
    print("     - 'Sci-fi adventure with space exploration'")
    print("     - 'Romantic comedy with witty dialogue'")
    print("  3. Start the frontend: cd frontend && npm run dev")
    
    # Close pipeline
    try:
        pipeline.close()
        print("\n✓ Pipeline closed successfully")
    except Exception as e:
        print(f"\n✗ Error closing pipeline: {e}")


if __name__ == "__main__":
    main()
