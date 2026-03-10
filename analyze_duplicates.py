"""
Analyze duplicate entries to determine if they're true duplicates or different items with same title.
"""

import sys
import json
sys.path.insert(0, 'backend')

from dotenv import load_dotenv
load_dotenv('backend/.env')

from backend.database.postgres import PostgresDatabase

def items_are_identical(item1, item2):
    """Check if two items are truly identical (not just same title)."""
    # Compare key fields
    if item1['description'] != item2['description']:
        return False
    if item1['media_type'] != item2['media_type']:
        return False
    
    # Compare metadata (excluding timestamps)
    meta1 = item1.get('metadata', {})
    meta2 = item2.get('metadata', {})
    
    # Compare relevant metadata fields
    for key in ['year', 'rating', 'genre']:
        if meta1.get(key) != meta2.get(key):
            return False
    
    return True

def main():
    print("="*80)
    print("DUPLICATE ANALYSIS TOOL")
    print("="*80)
    
    db = PostgresDatabase()
    media = db.get_all_media()
    
    print(f"\nTotal items: {len(media)}")
    
    # Group by title
    titles = {}
    for item in media:
        title = item['title']
        if title not in titles:
            titles[title] = []
        titles[title].append(item)
    
    # Analyze duplicates
    duplicates = {title: items for title, items in titles.items() if len(items) > 1}
    
    print(f"Duplicate titles: {len(duplicates)}")
    
    # Categorize duplicates
    true_duplicates = []  # Identical in all fields
    different_content = []  # Same title, different content
    
    for title, items in duplicates.items():
        # Check if all items are identical
        first_item = items[0]
        all_identical = all(items_are_identical(first_item, item) for item in items[1:])
        
        if all_identical:
            true_duplicates.append((title, items))
        else:
            different_content.append((title, items))
    
    print(f"\n{'='*80}")
    print("ANALYSIS RESULTS")
    print(f"{'='*80}")
    print(f"\nTrue Duplicates (same title + content): {len(true_duplicates)}")
    print(f"Different Content (same title, different metadata): {len(different_content)}")
    
    # Show examples of true duplicates
    if true_duplicates:
        print(f"\n{'='*80}")
        print("TRUE DUPLICATES (Safe to Remove)")
        print(f"{'='*80}")
        for title, items in sorted(true_duplicates, key=lambda x: -len(x[1]))[:5]:
            print(f"\n{title}: {len(items)} identical copies")
            item = items[0]
            print(f"  Type: {item['media_type']}")
            print(f"  Year: {item.get('metadata', {}).get('year', 'N/A')}")
            print(f"  Genre: {item.get('metadata', {}).get('genre', 'N/A')}")
            print(f"  Description: {item['description'][:80]}...")
    
    # Show examples of different content
    if different_content:
        print(f"\n{'='*80}")
        print("DIFFERENT CONTENT (Keep All - Different Movies/Shows)")
        print(f"{'='*80}")
        for title, items in sorted(different_content, key=lambda x: -len(x[1]))[:5]:
            print(f"\n{title}: {len(items)} different versions")
            for i, item in enumerate(items, 1):
                print(f"\n  Version {i}:")
                print(f"    Type: {item['media_type']}")
                print(f"    Year: {item.get('metadata', {}).get('year', 'N/A')}")
                print(f"    Genre: {item.get('metadata', {}).get('genre', 'N/A')}")
                print(f"    Rating: {item.get('metadata', {}).get('rating', 'N/A')}")
                print(f"    Description: {item['description'][:80]}...")
    
    # Summary
    total_removable = sum(len(items) - 1 for _, items in true_duplicates)
    
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Items that can be safely removed: {total_removable}")
    print(f"Items with same title but different content: {len(different_content)} titles")
    print(f"  (These should be kept as they're different movies/shows)")
    
    db.close()

if __name__ == "__main__":
    main()
