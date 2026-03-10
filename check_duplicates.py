"""Check for duplicate entries in the database."""

import sys
sys.path.insert(0, 'backend')

from dotenv import load_dotenv
load_dotenv('backend/.env')

from backend.database.postgres import PostgresDatabase

def main():
    print("Checking for duplicate entries...")
    
    db = PostgresDatabase()
    media = db.get_all_media()
    
    # Group by title
    titles = {}
    for item in media:
        title = item['title']
        if title not in titles:
            titles[title] = []
        titles[title].append(item['id'])
    
    # Find duplicates
    duplicates = {title: ids for title, ids in titles.items() if len(ids) > 1}
    
    print(f"\nTotal items: {len(media)}")
    print(f"Unique titles: {len(titles)}")
    print(f"Duplicate titles: {len(duplicates)}")
    
    if duplicates:
        print(f"\nTop 10 duplicates:")
        sorted_dupes = sorted(duplicates.items(), key=lambda x: -len(x[1]))
        for title, ids in sorted_dupes[:10]:
            print(f"  {title}: {len(ids)} copies")
            print(f"    IDs: {ids[:3]}...")  # Show first 3 IDs
    
    db.close()

if __name__ == "__main__":
    main()
