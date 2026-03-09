"""
Netflix Dataset Converter

This script converts the Netflix Kaggle dataset to the format expected by
the Semantic Media Engine data pipeline.

Usage:
    python convert_netflix_dataset.py              # Convert all items (5,850)
    python convert_netflix_dataset.py --limit 500  # Convert only 500 items
    python convert_netflix_dataset.py --limit 2000 # Convert 2,000 items

Netflix Dataset Format:
- titles.csv: id, title, type, description, release_year, age_certification, 
              runtime, genres, production_countries, seasons, imdb_id, 
              imdb_score, imdb_votes, tmdb_popularity, tmdb_score
- credits.csv: person_id, id, name, character, role

Expected Output Format:
- id, title, description, media_type, author, director, genre, year, rating, seasons
"""

import pandas as pd
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_directors(credits_df: pd.DataFrame) -> Dict[str, str]:
    """
    Extract directors from credits dataset.
    
    Args:
        credits_df: DataFrame with credits data
    
    Returns:
        Dictionary mapping media_id to director name
    """
    logger.info("Extracting directors from credits...")
    
    # Filter for directors only
    directors_df = credits_df[credits_df['role'] == 'DIRECTOR']
    
    # Group by media ID and concatenate director names
    directors_dict = {}
    for media_id, group in directors_df.groupby('id'):
        # Take first director or concatenate multiple directors
        director_names = group['name'].tolist()
        if len(director_names) > 0:
            directors_dict[media_id] = director_names[0]  # Use first director
    
    logger.info(f"Extracted {len(directors_dict)} directors")
    return directors_dict


def parse_genres(genres_str: str) -> str:
    """
    Parse genres from JSON-like string format.
    
    Args:
        genres_str: String like "['drama', 'crime']"
    
    Returns:
        Comma-separated genre string or empty string
    """
    if pd.isna(genres_str) or not genres_str:
        return ""
    
    try:
        # Parse as JSON array
        genres_list = json.loads(genres_str.replace("'", '"'))
        if genres_list and len(genres_list) > 0:
            # Capitalize first genre
            return genres_list[0].capitalize()
    except:
        pass
    
    return ""


def convert_netflix_to_media_format(
    titles_path: str,
    credits_path: str,
    output_path: str,
    max_items: int = None
) -> None:
    """
    Convert Netflix dataset to Semantic Media Engine format.
    
    Args:
        titles_path: Path to Netflix titles.csv
        credits_path: Path to Netflix credits.csv
        output_path: Path to output CSV file
        max_items: Maximum number of items to convert (None = all)
    """
    import uuid
    
    logger.info("=" * 80)
    logger.info("NETFLIX DATASET CONVERTER")
    logger.info("=" * 80)
    
    # Load titles dataset
    logger.info(f"\nLoading titles from: {titles_path}")
    titles_df = pd.read_csv(titles_path)
    logger.info(f"Loaded {len(titles_df)} titles")
    
    # Load credits dataset
    logger.info(f"\nLoading credits from: {credits_path}")
    credits_df = pd.read_csv(credits_path)
    logger.info(f"Loaded {len(credits_df)} credits")
    
    # Extract directors
    directors_dict = extract_directors(credits_df)
    
    # Filter for movies and shows only
    logger.info("\nFiltering for MOVIE and SHOW types...")
    titles_df = titles_df[titles_df['type'].isin(['MOVIE', 'SHOW'])]
    logger.info(f"After filtering: {len(titles_df)} items")
    
    # Remove items without descriptions
    logger.info("\nRemoving items without descriptions...")
    titles_df = titles_df[titles_df['description'].notna()]
    titles_df = titles_df[titles_df['description'].str.strip() != '']
    logger.info(f"After removing empty descriptions: {len(titles_df)} items")
    
    # Limit items if specified
    if max_items:
        logger.info(f"\nLimiting to {max_items} items...")
        titles_df = titles_df.head(max_items)
    
    # Convert to expected format
    logger.info("\nConverting to Semantic Media Engine format...")
    
    converted_data = []
    
    for idx, row in titles_df.iterrows():
        # Map media type
        media_type = 'tv_show' if row['type'] == 'SHOW' else 'book'
        
        # Get director from credits
        director = directors_dict.get(row['id'], '')
        
        # Parse genres
        genre = parse_genres(row.get('genres', ''))
        
        # Get rating (use imdb_score if available)
        rating = row.get('imdb_score', None)
        if pd.notna(rating):
            rating = float(rating)
        else:
            rating = None
        
        # Get year
        year = row.get('release_year', None)
        if pd.notna(year):
            year = int(year)
        else:
            year = None
        
        # Get seasons (for TV shows)
        seasons = row.get('seasons', None)
        if pd.notna(seasons):
            seasons = int(float(seasons))
        else:
            seasons = None
        
        # Create converted row with UUID
        converted_row = {
            'id': str(uuid.uuid4()),  # Generate UUID instead of using Netflix ID
            'title': row['title'].strip(),
            'description': row['description'].strip(),
            'media_type': media_type,
            'author': '',  # Netflix doesn't have author info
            'director': director,
            'genre': genre,
            'year': year,
            'rating': rating,
            'seasons': seasons if media_type == 'tv_show' else None
        }
        
        converted_data.append(converted_row)
    
    # Create output DataFrame
    output_df = pd.DataFrame(converted_data)
    
    # Save to CSV
    logger.info(f"\nSaving converted dataset to: {output_path}")
    output_df.to_csv(output_path, index=False)
    
    # Display statistics
    logger.info("\n" + "=" * 80)
    logger.info("CONVERSION STATISTICS")
    logger.info("=" * 80)
    logger.info(f"Total items converted: {len(output_df)}")
    logger.info(f"Movies (as books): {len(output_df[output_df['media_type'] == 'book'])}")
    logger.info(f"TV Shows: {len(output_df[output_df['media_type'] == 'tv_show'])}")
    logger.info(f"Items with directors: {len(output_df[output_df['director'] != ''])}")
    logger.info(f"Items with genres: {len(output_df[output_df['genre'] != ''])}")
    logger.info(f"Items with ratings: {len(output_df[output_df['rating'].notna()])}")
    logger.info(f"Items with years: {len(output_df[output_df['year'].notna()])}")
    
    # Display genre distribution
    logger.info("\nGenre distribution:")
    genre_counts = output_df[output_df['genre'] != '']['genre'].value_counts()
    for genre, count in genre_counts.head(10).items():
        logger.info(f"  {genre}: {count} items")
    
    # Display sample items
    logger.info("\nSample converted items:")
    for idx, row in output_df.head(3).iterrows():
        logger.info(f"\n  {idx + 1}. {row['title']} ({row['year']})")
        logger.info(f"     Type: {row['media_type']}")
        logger.info(f"     Genre: {row['genre']}")
        logger.info(f"     Director: {row['director']}")
        logger.info(f"     Rating: {row['rating']}")
        logger.info(f"     Description: {row['description'][:100]}...")
    
    logger.info("\n" + "=" * 80)
    logger.info("✓ CONVERSION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"\nNext steps:")
    logger.info(f"  1. Review the converted dataset: {output_path}")
    logger.info(f"  2. Run the data pipeline: python backend/data_pipeline/run_sample_pipeline.py")
    logger.info(f"  3. Test recommendations with Netflix-specific queries")


if __name__ == "__main__":
    import os
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Convert Netflix dataset to media format')
    parser.add_argument('--limit', type=int, default=None, 
                       help='Maximum number of items to convert (default: all items)')
    args = parser.parse_args()
    
    # Configuration
    NETFLIX_DIR = r"C:\Users\Steora\Downloads\netflix"
    TITLES_PATH = f"{NETFLIX_DIR}\\titles.csv"
    CREDITS_PATH = f"{NETFLIX_DIR}\\credits.csv"
    
    # Get absolute path for output
    script_dir = Path(__file__).parent
    output_dir = script_dir.parent / "data"
    OUTPUT_PATH = str(output_dir / "netflix_media.csv")
    
    # Log configuration
    if args.limit:
        logger.info(f"Converting up to {args.limit} items...")
    else:
        logger.info("Converting ALL items (full dataset)...")
    
    # Convert dataset
    convert_netflix_to_media_format(
        titles_path=TITLES_PATH,
        credits_path=CREDITS_PATH,
        output_path=OUTPUT_PATH,
        max_items=args.limit  # None = all items, or specified limit
    )
