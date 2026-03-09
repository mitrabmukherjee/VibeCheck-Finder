#!/usr/bin/env python3
"""
End-to-End Test Script for Semantic Media Engine

This script performs automated E2E testing of the complete recommendation flow,
from API endpoint validation to query processing and result verification.

Requirements tested: 1.1, 1.4, 4.1, 5.1, 5.2, 5.4, 6.1

Usage:
    python test_e2e.py
    python test_e2e.py --verbose
    python test_e2e.py --backend-url http://localhost:8000
"""

import argparse
import sys
import time
import requests
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class TestResult:
    """Represents the result of a single test case."""
    name: str
    passed: bool
    message: str
    duration_ms: float


class E2ETestRunner:
    """Runs end-to-end tests for the Semantic Media Engine."""
    
    def __init__(self, backend_url: str, verbose: bool = False):
        self.backend_url = backend_url.rstrip('/')
        self.verbose = verbose
        self.results: List[TestResult] = []
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(f"[{level}] {message}")
    
    def test_backend_health(self) -> TestResult:
        """Test 1: Verify backend server is running and healthy."""
        test_name = "Backend Health Check"
        start_time = time.time()
        
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            duration_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    return TestResult(
                        name=test_name,
                        passed=True,
                        message="Backend is healthy and responding",
                        duration_ms=duration_ms
                    )
                else:
                    return TestResult(
                        name=test_name,
                        passed=False,
                        message=f"Unexpected health status: {data}",
                        duration_ms=duration_ms
                    )
            else:
                return TestResult(
                    name=test_name,
                    passed=False,
                    message=f"Health check returned status {response.status_code}",
                    duration_ms=duration_ms
                )
        except requests.exceptions.RequestException as e:
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                name=test_name,
                passed=False,
                message=f"Failed to connect to backend: {str(e)}",
                duration_ms=duration_ms
            )
    
    def test_basic_book_query(self) -> TestResult:
        """Test 2: Basic book query returns relevant results."""
        test_name = "Basic Book Query"
        query = "mystery book with detective"
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.backend_url}/recommend",
                json={"query": query, "top_k": 5},
                timeout=10
            )
            duration_ms = (time.time() - start_time) * 1000
            
            if response.status_code != 200:
                return TestResult(
                    name=test_name,
                    passed=False,
                    message=f"API returned status {response.status_code}: {response.text}",
                    duration_ms=duration_ms
                )
            
            data = response.json()
            
            # Validate response structure
            if "results" not in data:
                return TestResult(
                    name=test_name,
                    passed=False,
                    message="Response missing 'results' field",
                    duration_ms=duration_ms
                )
            
            if "query_time_ms" not in data:
                return TestResult(
                    name=test_name,
                    passed=False,
                    message="Response missing 'query_time_ms' field",
                    duration_ms=duration_ms
                )
            
            results = data["results"]
            
            # Check if we got results
            if len(results) == 0:
                return TestResult(
                    name=test_name,
                    passed=False,
                    message="No results returned for book query",
                    duration_ms=duration_ms
                )
            
            # Validate result structure
            first_result = results[0]
            required_fields = ["id", "title", "description", "metadata", "similarity_score"]
            missing_fields = [f for f in required_fields if f not in first_result]
            
            if missing_fields:
                return TestResult(
                    name=test_name,
                    passed=False,
                    message=f"Result missing fields: {missing_fields}",
                    duration_ms=duration_ms
                )
            
            # Check similarity scores are in valid range and sorted
            scores = [r["similarity_score"] for r in results]
            if not all(0.0 <= score <= 1.0 for score in scores):
                return TestResult(
                    name=test_name,
                    passed=False,
                    message=f"Similarity scores out of range [0, 1]: {scores}",
                    duration_ms=duration_ms
                )
            
            if scores != sorted(scores, reverse=True):
                return TestResult(
                    name=test_name,
                    passed=False,
                    message=f"Results not sorted by similarity score: {scores}",
                    duration_ms=duration_ms
                )
            
            self.log(f"Query returned {len(results)} results")
            self.log(f"Top result: {first_result['title']} ({scores[0]:.2%} match)")
            
            return TestResult(
                name=test_name,
                passed=True,
                message=f"Returned {len(results)} valid results, top score: {scores[0]:.2%}",
                duration_ms=duration_ms
            )
            
        except requests.exceptions.RequestException as e:
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                name=test_name,
                passed=False,
                message=f"Request failed: {str(e)}",
                duration_ms=duration_ms
            )
    
    def test_tv_show_query(self) -> TestResult:
        """Test 3: TV show query returns relevant results."""
        test_name = "TV Show Query"
        query = "science fiction show about time travel"
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.backend_url}/recommend",
                json={"query": query, "top_k": 5},
                timeout=10
            )
            duration_ms = (time.time() - start_time) * 1000
            
            if response.status_code != 200:
                return TestResult(
                    name=test_name,
                    passed=False,
                    message=f"API returned status {response.status_code}",
                    duration_ms=duration_ms
                )
            
            data = response.json()
            results = data.get("results", [])
            
            if len(results) == 0:
                return TestResult(
                    name=test_name,
                    passed=False,
                    message="No results returned for TV show query",
                    duration_ms=duration_ms
                )
            
            # Check if top results include TV shows
            tv_shows = [r for r in results if r.get("media_type") == "tv_show"]
            
            if len(tv_shows) == 0:
                return TestResult(
                    name=test_name,
                    passed=False,
                    message="No TV shows in results for TV show query",
                    duration_ms=duration_ms
                )
            
            top_result = results[0]
            self.log(f"Top result: {top_result['title']} ({top_result['media_type']})")
            
            return TestResult(
                name=test_name,
                passed=True,
                message=f"Returned {len(tv_shows)} TV shows out of {len(results)} results",
                duration_ms=duration_ms
            )
            
        except requests.exceptions.RequestException as e:
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                name=test_name,
                passed=False,
                message=f"Request failed: {str(e)}",
                duration_ms=duration_ms
            )
    
    def test_empty_query_validation(self) -> TestResult:
        """Test 4: Empty query is rejected with proper error."""
        test_name = "Empty Query Validation"
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.backend_url}/recommend",
                json={"query": "", "top_k": 5},
                timeout=10
            )
            duration_ms = (time.time() - start_time) * 1000
            
            # Empty query should be rejected (422 or 400)
            if response.status_code in [400, 422]:
                return TestResult(
                    name=test_name,
                    passed=True,
                    message=f"Empty query properly rejected with status {response.status_code}",
                    duration_ms=duration_ms
                )
            else:
                return TestResult(
                    name=test_name,
                    passed=False,
                    message=f"Empty query not rejected, got status {response.status_code}",
                    duration_ms=duration_ms
                )
            
        except requests.exceptions.RequestException as e:
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                name=test_name,
                passed=False,
                message=f"Request failed: {str(e)}",
                duration_ms=duration_ms
            )
    
    def test_top_k_parameter(self) -> TestResult:
        """Test 5: top_k parameter controls result count."""
        test_name = "Top-K Parameter"
        query = "fantasy adventure"
        top_k = 3
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.backend_url}/recommend",
                json={"query": query, "top_k": top_k},
                timeout=10
            )
            duration_ms = (time.time() - start_time) * 1000
            
            if response.status_code != 200:
                return TestResult(
                    name=test_name,
                    passed=False,
                    message=f"API returned status {response.status_code}",
                    duration_ms=duration_ms
                )
            
            data = response.json()
            results = data.get("results", [])
            
            if len(results) > top_k:
                return TestResult(
                    name=test_name,
                    passed=False,
                    message=f"Returned {len(results)} results, expected at most {top_k}",
                    duration_ms=duration_ms
                )
            
            return TestResult(
                name=test_name,
                passed=True,
                message=f"Correctly returned {len(results)} results (requested {top_k})",
                duration_ms=duration_ms
            )
            
        except requests.exceptions.RequestException as e:
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                name=test_name,
                passed=False,
                message=f"Request failed: {str(e)}",
                duration_ms=duration_ms
            )
    
    def test_performance(self) -> TestResult:
        """Test 6: Query performance meets acceptable thresholds."""
        test_name = "Performance Benchmark"
        query = "mystery thriller"
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.backend_url}/recommend",
                json={"query": query, "top_k": 5},
                timeout=10
            )
            duration_ms = (time.time() - start_time) * 1000
            
            if response.status_code != 200:
                return TestResult(
                    name=test_name,
                    passed=False,
                    message=f"API returned status {response.status_code}",
                    duration_ms=duration_ms
                )
            
            data = response.json()
            query_time_ms = data.get("query_time_ms", 0)
            
            # Performance thresholds
            EXCELLENT = 200  # < 200ms is excellent
            ACCEPTABLE = 1000  # < 1s is acceptable
            
            if query_time_ms < EXCELLENT:
                performance = "excellent"
            elif query_time_ms < ACCEPTABLE:
                performance = "acceptable"
            else:
                performance = "slow"
            
            passed = query_time_ms < ACCEPTABLE
            
            return TestResult(
                name=test_name,
                passed=passed,
                message=f"Query time: {query_time_ms:.1f}ms ({performance}), Total: {duration_ms:.1f}ms",
                duration_ms=duration_ms
            )
            
        except requests.exceptions.RequestException as e:
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                name=test_name,
                passed=False,
                message=f"Request failed: {str(e)}",
                duration_ms=duration_ms
            )
    
    def test_special_characters(self) -> TestResult:
        """Test 7: Queries with special characters are handled correctly."""
        test_name = "Special Characters Handling"
        query = "mystery!!! with @detective #crime"
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.backend_url}/recommend",
                json={"query": query, "top_k": 5},
                timeout=10
            )
            duration_ms = (time.time() - start_time) * 1000
            
            if response.status_code != 200:
                return TestResult(
                    name=test_name,
                    passed=False,
                    message=f"API returned status {response.status_code}",
                    duration_ms=duration_ms
                )
            
            data = response.json()
            results = data.get("results", [])
            
            # Should return results similar to "mystery detective crime"
            if len(results) == 0:
                return TestResult(
                    name=test_name,
                    passed=False,
                    message="No results returned for query with special characters",
                    duration_ms=duration_ms
                )
            
            return TestResult(
                name=test_name,
                passed=True,
                message=f"Special characters handled correctly, returned {len(results)} results",
                duration_ms=duration_ms
            )
            
        except requests.exceptions.RequestException as e:
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                name=test_name,
                passed=False,
                message=f"Request failed: {str(e)}",
                duration_ms=duration_ms
            )
    
    def test_result_uniqueness(self) -> TestResult:
        """Test 8: Results contain no duplicate media IDs."""
        test_name = "Result Uniqueness"
        query = "drama series"
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.backend_url}/recommend",
                json={"query": query, "top_k": 10},
                timeout=10
            )
            duration_ms = (time.time() - start_time) * 1000
            
            if response.status_code != 200:
                return TestResult(
                    name=test_name,
                    passed=False,
                    message=f"API returned status {response.status_code}",
                    duration_ms=duration_ms
                )
            
            data = response.json()
            results = data.get("results", [])
            
            if len(results) == 0:
                return TestResult(
                    name=test_name,
                    passed=True,
                    message="No results to check for duplicates",
                    duration_ms=duration_ms
                )
            
            # Check for duplicate IDs
            ids = [r["id"] for r in results]
            unique_ids = set(ids)
            
            if len(ids) != len(unique_ids):
                duplicates = [id for id in ids if ids.count(id) > 1]
                return TestResult(
                    name=test_name,
                    passed=False,
                    message=f"Found duplicate IDs: {set(duplicates)}",
                    duration_ms=duration_ms
                )
            
            return TestResult(
                name=test_name,
                passed=True,
                message=f"All {len(results)} results have unique IDs",
                duration_ms=duration_ms
            )
            
        except requests.exceptions.RequestException as e:
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                name=test_name,
                passed=False,
                message=f"Request failed: {str(e)}",
                duration_ms=duration_ms
            )
    
    def run_all_tests(self) -> Tuple[int, int]:
        """Run all E2E tests and return (passed, total) counts."""
        print("=" * 70)
        print("Semantic Media Engine - End-to-End Test Suite")
        print("=" * 70)
        print(f"Backend URL: {self.backend_url}")
        print(f"Verbose: {self.verbose}")
        print("=" * 70)
        print()
        
        tests = [
            self.test_backend_health,
            self.test_basic_book_query,
            self.test_tv_show_query,
            self.test_empty_query_validation,
            self.test_top_k_parameter,
            self.test_performance,
            self.test_special_characters,
            self.test_result_uniqueness,
        ]
        
        for i, test_func in enumerate(tests, 1):
            print(f"Running Test {i}/{len(tests)}: {test_func.__doc__.split(':')[0].strip()}")
            result = test_func()
            self.results.append(result)
            
            status = "✓ PASS" if result.passed else "✗ FAIL"
            print(f"  {status} - {result.message}")
            print(f"  Duration: {result.duration_ms:.1f}ms")
            print()
        
        # Summary
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        
        print("=" * 70)
        print("Test Summary")
        print("=" * 70)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {passed/total*100:.1f}%")
        print("=" * 70)
        
        if passed == total:
            print("✓ All tests passed!")
        else:
            print("✗ Some tests failed. See details above.")
            print("\nFailed tests:")
            for result in self.results:
                if not result.passed:
                    print(f"  - {result.name}: {result.message}")
        
        print()
        return passed, total


def main():
    """Main entry point for E2E test script."""
    parser = argparse.ArgumentParser(
        description="End-to-End Test Suite for Semantic Media Engine"
    )
    parser.add_argument(
        "--backend-url",
        default="http://localhost:8000",
        help="Backend API URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    runner = E2ETestRunner(
        backend_url=args.backend_url,
        verbose=args.verbose
    )
    
    passed, total = runner.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
