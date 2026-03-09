"""
Example usage of the DataPipeline for ingesting media datasets.

This script demonstrates how to use the DataPipeline class to:
1. Load a dataset from CSV
2. Clean and validate the data
3. Generate embeddings using the ML Engine
4. Store embeddings in Vector DB
5. Store metadata in PostgreSQL
"""

import logging
from data_pipeline import DataPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Run the data pipeline on a sample dataset."""
    
    # Configuration
    source_path = "backend/data/sample_media.csv"  # Path to your CSV file
    vectorizer_path = "backend/models"  # Where to save/load the vectorizer
    embeddings_path = "backend/embeddings"  # Where to save embeddings
    
    # Vector DB configuration (Qdrant)
    vector_db_config = {
        "host": "localhost",
        "port": 6333,
        "collection_name": "media_embeddings",
        "vector_size": 5000,  # Must match vectorizer max_features
    }
    
    # PostgreSQL configuration
    postgres_config = {
        "min_connections": 1,
        "max_connections": 10
    }
    
    # Batch size for processing
    batch_size = 1000
    
    try:
        # Initialize the pipeline
        logger.info("Initializing DataPipeline...")
        pipeline = DataPipeline(
            source_path=source_path,
            vectorizer_path=vectorizer_path,
            embeddings_path=embeddings_path,
            vector_db_config=vector_db_config,
            postgres_config=postgres_config,
            batch_size=batch_size
        )
        
        # Run the complete pipeline
        # Set train_vectorizer=True if this is the first run or you want to retrain
        logger.info("Running data pipeline...")
        stats = pipeline.run(train_vectorizer=True)
        
        # Display results
        logger.info("Pipeline execution complete!")
        logger.info(f"Statistics:")
        logger.info(f"  - Total loaded: {stats['total_loaded']}")
        logger.info(f"  - Total cleaned: {stats['total_cleaned']}")
        logger.info(f"  - Total stored: {stats['total_stored']}")
        logger.info(f"  - Model version: {stats['model_version']}")
        
        # Close connections
        pipeline.close()
        logger.info("Pipeline closed successfully")
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
