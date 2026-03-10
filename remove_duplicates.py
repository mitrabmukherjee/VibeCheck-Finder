"""
Remove duplicate entries from the database.

Strategy: Keep the first occurrence of each title, delete the rest.
"""

import sys
sys.path.insert(0, 'backend')

from dotenv import load_dotenv
load_dotenv('backend/.env')

from backend.database.postgres import PostgresDatabase
from backend.database.file_vector_db import FileVectorDatabase

def main():
    print("="*80)
    print("DUPLICATE REMOVAL TOOL")
    print("="*80)
    
    db = PostgresDatabase()
    vector_db = FileVectorDatabase(storage_path='backend/embeddings', vector_size=768)
    
    # Get all media
    media = db.get_all_media()
    print(f"\nTotal items in database: {len(media)}")
    
    # Group by title
    titles = {}
    for item in media:
        title = item['title']
        if title not in titles:
            titles[title] = []
        titles[title].append(item)
    
    # Find duplicates
    duplicates = {title: items for title, items in titles.items() if len(items) > 1}
    
    print(f"Unique titles: {len(titles)}")
    print(f"Duplicate titles: {len(duplicates)}")
    
    if not duplicates:
        print("\n✓ No duplicates found!")
        return
    
    # Calculate total items to remove
    total_to_remove = sum(len(items) - 1 for items in duplicates.values())
    print(f"\nItems to remove: {total_to_remove}")
    
    print("\nTop 10 duplicates:")
    sorted_dupes = sorted(duplicates.items(), key=lambda x: -len(x[1]))
    for title, items in sorted_dupes[:10]:
        print(f"  {title}: {len(items)} copies")
    
    response = input(f"\nRemove {total_to_remove} duplicate entries? (yes/no): ")
    
    if response.lower() not in ['yes', 'y']:
        print("Cancelled.")
        return
    
    print("\nRemoving duplicates...")
    removed_count = 0
    
    for title, items in duplicates.items():
        # Keep the first item (usually oldest), remove the rest
        items_sorted = sorted(items, key=lambda x: x['created_at'])
        keep_item = items_sorted[0]
        remove_items = items_sorted[1:]
        
        for item in remove_items:
            try:
                # Remove from PostgreSQL
                db.delete_media(item['id'])
                
                # Remove from vector database
                vector_db.delete(item['id'])
                
                removed_count += 1
                if removed_count % 100 == 0:
                    print(f"  Removed {removed_count}/{total_to_remove}...")
            except Exception as e:
                print(f"  Error removing {item['id']}: {e}")
    
    print(f"\n✓ Removed {removed_count} duplicate entries!")
    print(f"✓ Database now has {len(media) - removed_count} unique items")
    
    # Verify
    media_after = db.get_all_media()
    titles_after = {}
    for item in media_after:
        title = item['title']
        titles_after[title] = titles_after.get(title, 0) + 1
    
    dupes_after = {t: c for t, c in titles_after.items() if c > 1}
    print(f"✓ Remaining duplicates: {len(dupes_after)}")
    
    db.close()
    vector_db.close()
    
    print("\n" + "="*80)
    print("CLEANUP COMPLETE!")
    print("="*80)
    print("\nRestart your backend to see the changes:")
    print("  cd backend")
    print("  python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000")

if __name__ == "__main__":
    main()
