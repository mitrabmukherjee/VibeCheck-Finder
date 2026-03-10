"""
Validation script for Sentence-BERT embedding quality.

This script validates that Sentence-BERT embeddings are correctly generated
and compares search quality between TF-IDF and Sentence-BERT vectorizers.

Requirements:
    - 9.1: Provide validation script comparing TF-IDF and Sentence-BERT results
    - 9.2: Generate report showing similarity scores for both methods
    - 9.3: Verify all embeddings have exactly 384 dimensions
    - 9.4: Verify all embedding values are finite
    - 9.5: Verify encoding idempotence
    - 6.1-6.3: Test semantic understanding with example queries
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ml_engine.ml_engine import MLEngine
from ml_engine.sentence_bert_vectorizer import SentenceBertVectorizer
from database.file_vector_db import FileVectorDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Test queries for semantic understanding validation
TEST_QUERIES = [
    {
        "query": "little girl",
        "expected_concepts": ["young", "girl", "child", "daughter", "kid"],
        "description": "Should find content about young girls, children, daughters"
    },
    {
        "query": "romantic comedy",
        "expected_concepts": ["love", "romance", "funny", "humor", "comedy"],
        "description": "Should find content about love stories with humor"
    },
    {
        "query": "space adventure",
        "expected_concepts": ["space", "sci-fi", "science fiction", "astronaut", "exploration"],
        "description": "Should find content about sci-fi exploration"
    },
    {
        "query": "mystery detective",
        "expected_concepts": ["mystery", "detective", "crime", "investigation", "thriller"],
        "description": "Should find content about detective stories and investigations"
    },
    {
        "query": "family drama",
        "expected_concepts": ["family", "drama", "relationship", "emotional"],
        "description": "Should find content about family relationships and drama"
    }
]


def validate_embedding_dimensions(
    vectorizer: SentenceBertVectorizer,
    sample_texts: List[str]
) -> Dict[str, Any]:
    """
    Validate that all embeddings have exactly768  dimensions.
    
    Requirements: 9.3, 1.4, 2.2
    """
    logger.info("Validating embedding dimensions...")
    
    results = {
        "total_samples": len(sample_texts),
        "correct_dimension": 0,
        "incorrect_dimension": 0,
        "dimension_errors": []
    }
    
    for i, text in enumerate(sample_texts):
        embedding = vectorizer.encode(text)
        
        if embedding.shape == (1, 768):
            results["correct_dimension"] += 1
        else:
            results["incorrect_dimension"] += 1
            results["dimension_errors"].append({
                "index": i,
                "text": text[:50] + "..." if len(text) > 50 else text,
                "shape": embedding.shape
            })
    
    logger.info(f"Dimension validation: {results['correct_dimension']}/{results['total_samples']} correct")
    
    return results


def validate_finite_values(
    vectorizer: SentenceBertVectorizer,
    sample_texts: List[str]
) -> Dict[str, Any]:
    """
    Validate that all embedding values are finite (no NaN or infinity).
    
    Requirements: 9.4
    """
    logger.info("Validating finite embedding values...")
    
    results = {
        "total_samples": len(sample_texts),
        "all_finite": 0,
        "has_non_finite": 0,
        "non_finite_errors": []
    }
    
    for i, text in enumerate(sample_texts):
        embedding = vectorizer.encode(text)
        
        if np.all(np.isfinite(embedding)):
            results["all_finite"] += 1
        else:
            results["has_non_finite"] += 1
            results["non_finite_errors"].append({
                "index": i,
                "text": text[:50] + "..." if len(text) > 50 else text,
                "has_nan": np.any(np.isnan(embedding)),
                "has_inf": np.any(np.isinf(embedding))
            })
    
    logger.info(f"Finite value validation: {results['all_finite']}/{results['total_samples']} all finite")
    
    return results


def validate_encoding_idempotence(
    vectorizer: SentenceBertVectorizer,
    sample_texts: List[str]
) -> Dict[str, Any]:
    """
    Validate that encoding the same text multiple times produces identical embeddings.
    
    Requirements: 9.5
    """
    logger.info("Validating encoding idempotence...")
    
    results = {
        "total_samples": len(sample_texts),
        "idempotent": 0,
        "non_idempotent": 0,
        "idempotence_errors": []
    }
    
    for i, text in enumerate(sample_texts):
        # Encode the same text twice
        embedding1 = vectorizer.encode(text)
        embedding2 = vectorizer.encode(text)
        
        # Check if they are equal within floating-point precision
        if np.allclose(embedding1, embedding2, rtol=1e-7, atol=1e-9):
            results["idempotent"] += 1
        else:
            results["non_idempotent"] += 1
            max_diff = np.max(np.abs(embedding1 - embedding2))
            results["idempotence_errors"].append({
                "index": i,
                "text": text[:50] + "..." if len(text) > 50 else text,
                "max_difference": float(max_diff)
            })
    
    logger.info(f"Idempotence validation: {results['idempotent']}/{results['total_samples']} idempotent")
    
    return results


def compare_search_results(
    query: str,
    tfidf_engine: Optional[MLEngine],
    sbert_engine: MLEngine,
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Compare search results between TF-IDF and Sentence-BERT for a single query.
    
    Requirements: 9.1, 9.2, 6.5
    """
    results = {
        "query": query,
        "sbert_results": [],
        "tfidf_results": [],
        "sbert_top_score": 0.0,
        "tfidf_top_score": 0.0,
        "improvement": 0.0
    }
    
    # Get Sentence-BERT results
    try:
        sbert_vector = sbert_engine.vectorize_query(query)
        sbert_matches = sbert_engine.find_similar(sbert_vector, top_k=top_k)
        results["sbert_results"] = [
            {"id": media_id, "score": float(score)}
            for media_id, score in sbert_matches
        ]
        if sbert_matches:
            results["sbert_top_score"] = float(sbert_matches[0][1])
    except Exception as e:
        logger.error(f"Error getting Sentence-BERT results: {e}")
        results["sbert_error"] = str(e)
    
    # Get TF-IDF results if available
    if tfidf_engine is not None:
        try:
            tfidf_vector = tfidf_engine.vectorize_query(query)
            tfidf_matches = tfidf_engine.find_similar(tfidf_vector, top_k=top_k)
            results["tfidf_results"] = [
                {"id": media_id, "score": float(score)}
                for media_id, score in tfidf_matches
            ]
            if tfidf_matches:
                results["tfidf_top_score"] = float(tfidf_matches[0][1])
        except Exception as e:
            logger.error(f"Error getting TF-IDF results: {e}")
            results["tfidf_error"] = str(e)
    
    # Calculate improvement
    if results["tfidf_top_score"] > 0:
        results["improvement"] = results["sbert_top_score"] / results["tfidf_top_score"]
    
    return results


def validate_semantic_understanding(
    sbert_engine: MLEngine,
    test_queries: List[Dict[str, Any]],
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Validate semantic understanding with test queries.
    
    Requirements: 6.1, 6.2, 6.3
    """
    logger.info("Validating semantic understanding...")
    
    results = []
    
    for test_case in test_queries:
        query = test_case["query"]
        expected_concepts = test_case["expected_concepts"]
        description = test_case["description"]
        
        logger.info(f"Testing query: '{query}'")
        
        try:
            # Get search results
            query_vector = sbert_engine.vectorize_query(query)
            matches = sbert_engine.find_similar(query_vector, top_k=top_k)
            
            # Calculate average score
            avg_score = np.mean([score for _, score in matches]) if matches else 0.0
            
            # Check if scores are in expected range (60-80%)
            in_expected_range = 0.6 <= avg_score <= 0.8
            
            result = {
                "query": query,
                "description": description,
                "expected_concepts": expected_concepts,
                "top_results": [
                    {"id": media_id, "score": float(score)}
                    for media_id, score in matches
                ],
                "avg_score": float(avg_score),
                "in_expected_range": in_expected_range,
                "top_score": float(matches[0][1]) if matches else 0.0
            }
            
            results.append(result)
            
            logger.info(f"  Average score: {avg_score:.3f} (expected: 0.60-0.80)")
            logger.info(f"  In expected range: {in_expected_range}")
            
        except Exception as e:
            logger.error(f"Error testing query '{query}': {e}")
            results.append({
                "query": query,
                "description": description,
                "error": str(e)
            })
    
    return results


def validate_embeddings(
    storage_path: str = "backend/embeddings",
    vectorizer_path: str = "backend/models",
    compare_tfidf: bool = True,
    output_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validate Sentence-BERT embedding quality.
    
    This function performs comprehensive validation of Sentence-BERT embeddings:
    1. Validates embedding dimensions (768)
    2. Validates all values are finite
    3. Validates encoding idempotence
    4. Compares search results with TF-IDF (if available)
    5. Tests semantic understanding with example queries
    
    Args:
        storage_path: Path to embeddings storage
        vectorizer_path: Path to vectorizer models
        compare_tfidf: Whether to compare with TF-IDF results
        output_file: Optional path to save validation report JSON
    
    Returns:
        Validation report dictionary
    
    Requirements:
        - 9.1: Provide validation script comparing TF-IDF and Sentence-BERT
        - 9.2: Generate report showing similarity scores
        - 9.3: Verify all embeddings have exactly 768 dimensions
        - 9.4: Verify all embedding values are finite
        - 9.5: Verify encoding idempotence
        - 6.1-6.3: Test semantic understanding
    """
    logger.info("=" * 60)
    logger.info("Starting Sentence-BERT Validation")
    logger.info("=" * 60)
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "storage_path": storage_path,
        "vectorizer_path": vectorizer_path,
        "validation_checks": {},
        "query_comparisons": [],
        "semantic_tests": []
    }
    
    # Initialize Sentence-BERT vectorizer
    logger.info("\nInitializing Sentence-BERT vectorizer...")
    try:
        sbert_vectorizer = SentenceBertVectorizer()
        logger.info(f"Model: {sbert_vectorizer.model_name}")
        logger.info(f"Embedding dimension: {sbert_vectorizer.get_embedding_dimension()}")
    except Exception as e:
        logger.error(f"Failed to initialize Sentence-BERT vectorizer: {e}")
        report["error"] = str(e)
        return report
    
    # Initialize Sentence-BERT engine
    logger.info("\nInitializing Sentence-BERT ML Engine...")
    try:
        sbert_engine = MLEngine(
            vectorizer_path=vectorizer_path,
            embeddings_path=storage_path,
            vectorizer_type="sbert"
        )
        
        # Load embeddings from file-based storage
        vector_db = FileVectorDatabase(storage_path=storage_path, vector_size=768)
        
        if vector_db.count() > 0:
            # Load corpus into engine
            sbert_engine.corpus_vectors = vector_db.vectors
            sbert_engine.corpus_ids = vector_db.ids
            logger.info(f"Loaded {len(sbert_engine.corpus_ids)} embeddings")
        else:
            logger.warning("No embeddings found in storage")
            
    except Exception as e:
        logger.error(f"Failed to initialize Sentence-BERT engine: {e}")
        report["error"] = str(e)
        return report
    
    # Initialize TF-IDF engine if comparison requested
    tfidf_engine = None
    if compare_tfidf:
        logger.info("\nInitializing TF-IDF ML Engine for comparison...")
        try:
            # Check if TF-IDF vectorizer exists
            tfidf_vectorizer_file = os.path.join(vectorizer_path, 'tfidf_vectorizer.pkl')
            if os.path.exists(tfidf_vectorizer_file):
                tfidf_engine = MLEngine(
                    vectorizer_path=vectorizer_path,
                    embeddings_path=storage_path,
                    vectorizer_type="tfidf"
                )
                
                # Load TF-IDF embeddings
                tfidf_vector_db = FileVectorDatabase(storage_path=storage_path, vector_size=5000)
                if tfidf_vector_db.count() > 0:
                    tfidf_engine.corpus_vectors = tfidf_vector_db.vectors
                    tfidf_engine.corpus_ids = tfidf_vector_db.ids
                    logger.info(f"Loaded {len(tfidf_engine.corpus_ids)} TF-IDF embeddings")
                else:
                    logger.warning("No TF-IDF embeddings found")
                    tfidf_engine = None
            else:
                logger.info("TF-IDF vectorizer not found, skipping comparison")
        except Exception as e:
            logger.warning(f"Could not load TF-IDF engine: {e}")
            tfidf_engine = None
    
    # Generate sample texts for validation
    sample_texts = [
        "A young girl discovers magic",
        "Romantic comedy about finding love",
        "Space exploration and adventure",
        "Mystery detective solving crimes",
        "Family drama with emotional depth",
        "Action thriller with suspense",
        "Documentary about nature",
        "Horror movie with supernatural elements",
        "Historical drama set in ancient times",
        "Science fiction with time travel"
    ]
    
    # Validation Check 1: Embedding Dimensions
    logger.info("\n" + "=" * 60)
    logger.info("Validation Check 1: Embedding Dimensions")
    logger.info("=" * 60)
    dimension_results = validate_embedding_dimensions(sbert_vectorizer, sample_texts)
    report["validation_checks"]["embedding_dimensions"] = dimension_results
    
    # Validation Check 2: Finite Values
    logger.info("\n" + "=" * 60)
    logger.info("Validation Check 2: Finite Embedding Values")
    logger.info("=" * 60)
    finite_results = validate_finite_values(sbert_vectorizer, sample_texts)
    report["validation_checks"]["finite_values"] = finite_results
    
    # Validation Check 3: Encoding Idempotence
    logger.info("\n" + "=" * 60)
    logger.info("Validation Check 3: Encoding Idempotence")
    logger.info("=" * 60)
    idempotence_results = validate_encoding_idempotence(sbert_vectorizer, sample_texts)
    report["validation_checks"]["encoding_idempotence"] = idempotence_results
    
    # Query Comparisons
    if sbert_engine.corpus_vectors is not None and len(sbert_engine.corpus_ids) > 0:
        logger.info("\n" + "=" * 60)
        logger.info("Query Comparisons: TF-IDF vs Sentence-BERT")
        logger.info("=" * 60)
        
        for test_case in TEST_QUERIES:
            query = test_case["query"]
            logger.info(f"\nComparing results for: '{query}'")
            
            comparison = compare_search_results(
                query,
                tfidf_engine,
                sbert_engine,
                top_k=5
            )
            report["query_comparisons"].append(comparison)
            
            logger.info(f"  Sentence-BERT top score: {comparison['sbert_top_score']:.3f}")
            if tfidf_engine:
                logger.info(f"  TF-IDF top score: {comparison['tfidf_top_score']:.3f}")
                logger.info(f"  Improvement: {comparison['improvement']:.2f}x")
        
        # Semantic Understanding Tests
        logger.info("\n" + "=" * 60)
        logger.info("Semantic Understanding Tests")
        logger.info("=" * 60)
        
        semantic_results = validate_semantic_understanding(
            sbert_engine,
            TEST_QUERIES,
            top_k=5
        )
        report["semantic_tests"] = semantic_results
    else:
        logger.warning("\nSkipping query comparisons - no embeddings loaded")
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Validation Summary")
    logger.info("=" * 60)
    
    all_checks_passed = True
    
    if dimension_results["incorrect_dimension"] > 0:
        logger.error(f"❌ Dimension check FAILED: {dimension_results['incorrect_dimension']} embeddings with wrong dimensions")
        all_checks_passed = False
    else:
        logger.info(f"✓ Dimension check PASSED: All {dimension_results['correct_dimension']} embeddings have 768 dimensions")
    
    if finite_results["has_non_finite"] > 0:
        logger.error(f"❌ Finite value check FAILED: {finite_results['has_non_finite']} embeddings with non-finite values")
        all_checks_passed = False
    else:
        logger.info(f"✓ Finite value check PASSED: All {finite_results['all_finite']} embeddings have finite values")
    
    if idempotence_results["non_idempotent"] > 0:
        logger.error(f"❌ Idempotence check FAILED: {idempotence_results['non_idempotent']} embeddings not idempotent")
        all_checks_passed = False
    else:
        logger.info(f"✓ Idempotence check PASSED: All {idempotence_results['idempotent']} embeddings are idempotent")
    
    if report["semantic_tests"]:
        avg_scores = [t["avg_score"] for t in report["semantic_tests"] if "avg_score" in t]
        if avg_scores:
            overall_avg = np.mean(avg_scores)
            logger.info(f"\nSemantic understanding average score: {overall_avg:.3f}")
            if 0.6 <= overall_avg <= 0.8:
                logger.info("✓ Scores are in expected range (0.60-0.80)")
            else:
                logger.warning(f"⚠ Scores outside expected range (0.60-0.80)")
    
    report["all_checks_passed"] = all_checks_passed
    
    # Save report if output file specified
    if output_file:
        logger.info(f"\nSaving validation report to: {output_file}")
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
    
    logger.info("\n" + "=" * 60)
    logger.info("Validation Complete")
    logger.info("=" * 60)
    
    return report


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate Sentence-BERT embedding quality")
    parser.add_argument(
        "--storage-path",
        default="backend/embeddings",
        help="Path to embeddings storage"
    )
    parser.add_argument(
        "--vectorizer-path",
        default="backend/models",
        help="Path to vectorizer models"
    )
    parser.add_argument(
        "--no-tfidf-comparison",
        action="store_true",
        help="Skip TF-IDF comparison"
    )
    parser.add_argument(
        "--output",
        help="Path to save validation report JSON"
    )
    
    args = parser.parse_args()
    
    report = validate_embeddings(
        storage_path=args.storage_path,
        vectorizer_path=args.vectorizer_path,
        compare_tfidf=not args.no_tfidf_comparison,
        output_file=args.output
    )
    
    # Exit with error code if validation failed
    if not report.get("all_checks_passed", False):
        sys.exit(1)
