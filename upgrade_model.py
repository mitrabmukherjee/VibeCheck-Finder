"""
Quick script to upgrade to all-mpnet-base-v2 model.

This will:
1. Backup existing embeddings
2. Regenerate embeddings with the new model
3. Update vector database
"""

import os
import sys

# Add backend to path
sys.path.insert(0, 'backend')

from backend.data_pipeline.migrate_to_sbert import migrate_to_sbert
from datetime import datetime
import json

if __name__ == "__main__":
    print("="*80)
    print("UPGRADING TO all-mpnet-base-v2 MODEL")
    print("="*80)
    print("\nThis will:")
    print("1. Backup your existing embeddings")
    print("2. Regenerate embeddings with the better model (768 dimensions)")
    print("3. This may take 10-15 minutes for 5,781 items")
    print("\nYour data will be safe - backups are created automatically!")
    print("="*80)
    
    response = input("\nProceed with upgrade? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        print("\nStarting upgrade...")
        
        report = migrate_to_sbert(
            data_file='data/netflix_media.csv',
            embeddings_path='backend/embeddings',
            vectorizer_path='backend/models',
            batch_size=32,
            backup=True,
            dry_run=False,
            model_name='all-mpnet-base-v2'  # Use the better model
        )
        
        # Save report
        report_path = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print("\n" + "="*80)
        if report['status'] == 'completed':
            print("UPGRADE COMPLETE!")
            print("="*80)
            print(f"\n✓ Successfully upgraded {report['successful']} items to all-mpnet-base-v2")
            print(f"✓ New embedding dimension: 768")
            print(f"✓ Duration: {report['duration_seconds']:.1f} seconds")
            print("\nRestart your backend to use the new model:")
            print("  cd backend")
            print("  python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000")
        else:
            print("UPGRADE FAILED!")
            print("="*80)
            print(f"\n✗ Migration status: {report['status']}")
            if report.get('backup_location'):
                print(f"\nTo rollback, run:")
                print(f"  python -c \"from backend.data_pipeline.migrate_to_sbert import rollback_migration; rollback_migration('{report['backup_location']}')\"")
    else:
        print("\nUpgrade cancelled.")
