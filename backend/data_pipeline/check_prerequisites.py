"""
Prerequisites checker for the data pipeline.

This script verifies that all required services and configurations
are in place before running the data pipeline.
"""

import os
import sys
from pathlib import Path

# Add backend to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


def check_env_file():
    """Check if .env file exists and has required variables."""
    print("Checking environment configuration...")
    
    env_path = backend_dir / ".env"
    if not env_path.exists():
        print("  ✗ .env file not found")
        print("    Create backend/.env with database configuration")
        return False
    
    print("  ✓ .env file exists")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv(env_path)
    
    required_vars = [
        "POSTGRES_HOST",
        "POSTGRES_PORT", 
        "POSTGRES_DB",
        "POSTGRES_USER",
        "QDRANT_HOST",
        "QDRANT_PORT"
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"  ✗ Missing environment variables: {', '.join(missing)}")
        return False
    
    print("  ✓ All required environment variables present")
    return True


def check_sample_data():
    """Check if sample dataset exists."""
    print("\nChecking sample dataset...")
    
    sample_path = backend_dir / "data" / "sample_media.csv"
    if not sample_path.exists():
        print("  ✗ sample_media.csv not found")
        print("    Expected at: backend/data/sample_media.csv")
        return False
    
    print("  ✓ sample_media.csv exists")
    
    # Check file size
    size = sample_path.stat().st_size
    if size < 100:
        print("  ✗ sample_media.csv appears to be empty or too small")
        return False
    
    print(f"  ✓ File size: {size:,} bytes")
    
    # Count lines
    with open(sample_path, 'r') as f:
        lines = len(f.readlines())
    
    if lines < 2:
        print("  ✗ sample_media.csv has no data rows")
        return False
    
    print(f"  ✓ Data rows: {lines - 1}")  # Subtract header
    return True


def check_postgres():
    """Check if PostgreSQL is accessible."""
    print("\nChecking PostgreSQL connection...")
    
    try:
        import psycopg2
        from dotenv import load_dotenv
        
        load_dotenv(backend_dir / ".env")
        
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            database=os.getenv("POSTGRES_DB", "semantic_media"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "")
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        print("  ✓ PostgreSQL connection successful")
        print(f"  ✓ Version: {version.split(',')[0]}")
        
        # Check if media_items table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'media_items'
            );
        """)
        
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            print("  ✓ media_items table exists")
            
            # Count existing items
            cursor.execute("SELECT COUNT(*) FROM media_items;")
            count = cursor.fetchone()[0]
            print(f"  ℹ Current items in database: {count}")
        else:
            print("  ✗ media_items table not found")
            print("    Run: python backend/database/migrate.py")
            cursor.close()
            conn.close()
            return False
        
        cursor.close()
        conn.close()
        return True
        
    except ImportError:
        print("  ✗ psycopg2 not installed")
        print("    Run: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"  ✗ PostgreSQL connection failed: {e}")
        print("    Check if PostgreSQL is running and credentials are correct")
        return False


def check_qdrant():
    """Check if Qdrant is accessible."""
    print("\nChecking Qdrant connection...")
    
    try:
        from qdrant_client import QdrantClient
        from dotenv import load_dotenv
        
        load_dotenv(backend_dir / ".env")
        
        host = os.getenv("QDRANT_HOST", "localhost")
        port = int(os.getenv("QDRANT_PORT", "6333"))
        
        client = QdrantClient(host=host, port=port)
        
        # Try to get collections
        collections = client.get_collections()
        
        print("  ✓ Qdrant connection successful")
        print(f"  ✓ Host: {host}:{port}")
        print(f"  ℹ Existing collections: {len(collections.collections)}")
        
        # Check if media_embeddings collection exists
        collection_names = [c.name for c in collections.collections]
        if "media_embeddings" in collection_names:
            info = client.get_collection("media_embeddings")
            print(f"  ℹ media_embeddings collection exists with {info.vectors_count} vectors")
        else:
            print("  ℹ media_embeddings collection will be created on first run")
        
        return True
        
    except ImportError:
        print("  ✗ qdrant-client not installed")
        print("    Run: pip install qdrant-client")
        return False
    except Exception as e:
        print(f"  ✗ Qdrant connection failed: {e}")
        print("    Check if Qdrant is running:")
        print("    docker run -p 6333:6333 qdrant/qdrant")
        return False


def check_dependencies():
    """Check if required Python packages are installed."""
    print("\nChecking Python dependencies...")
    
    required_packages = [
        "pandas",
        "numpy",
        "scikit-learn",
        "psycopg2",
        "qdrant-client",
        "python-dotenv"
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package}")
            missing.append(package)
    
    if missing:
        print(f"\n  Missing packages: {', '.join(missing)}")
        print("  Run: pip install -r backend/requirements.txt")
        return False
    
    return True


def check_directories():
    """Check if required directories exist."""
    print("\nChecking directories...")
    
    required_dirs = [
        backend_dir / "models",
        backend_dir / "embeddings",
        backend_dir / "data"
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        if dir_path.exists():
            print(f"  ✓ {dir_path.relative_to(backend_dir)}")
        else:
            print(f"  ℹ {dir_path.relative_to(backend_dir)} will be created")
            # Create directory
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"  ✓ Created {dir_path.relative_to(backend_dir)}")
    
    return True


def main():
    """Run all prerequisite checks."""
    print("=" * 80)
    print("DATA PIPELINE PREREQUISITES CHECKER")
    print("=" * 80)
    
    checks = [
        ("Environment Configuration", check_env_file),
        ("Sample Dataset", check_sample_data),
        ("Python Dependencies", check_dependencies),
        ("Directories", check_directories),
        ("PostgreSQL", check_postgres),
        ("Qdrant Vector DB", check_qdrant),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n  ✗ Unexpected error: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    all_passed = all(results.values())
    
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8s} {name}")
    
    print("=" * 80)
    
    if all_passed:
        print("\n✓ All prerequisites satisfied!")
        print("\nYou can now run the data pipeline:")
        print("  python backend/data_pipeline/run_sample_pipeline.py")
        return 0
    else:
        print("\n✗ Some prerequisites are not satisfied.")
        print("Please fix the issues above before running the pipeline.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
