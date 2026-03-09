# Understanding Similarity Scores

## Why Are Scores Around 20-30%?

The similarity scores you're seeing (typically 15-30%) are actually **normal and expected** for TF-IDF-based semantic search on a dataset of this size. Here's why:

### TF-IDF Characteristics

1. **Sparse Representations**: TF-IDF creates sparse vectors where most values are zero. This means even good matches often have relatively low cosine similarity scores.

2. **Dataset Size**: With 500 Netflix items, the vocabulary is limited. Larger datasets (10,000+ items) typically show higher similarity scores because there's more overlap in vocabulary.

3. **Content Diversity**: Netflix content spans many genres, styles, and themes. This diversity means fewer exact word matches between queries and descriptions.

### What Do These Scores Mean?

- **20-30%**: Strong match - The content is highly relevant to your query
- **15-20%**: Good match - The content is relevant with some shared themes
- **10-15%**: Moderate match - Some relevance but less direct connection
- **<10%**: Weak match - Limited relevance

### Example

Query: "romantic comedy about love and relationships"
Result: "Dil Chahta Hai" - 21% similarity

This 21% score is actually a **strong match** because:
- The description mentions "fall in love" and "relationships"
- It's categorized as Romance genre
- The themes align with the query

## How to Improve Similarity Scores

If you want higher similarity scores, you have several options:

### Option 1: Use More Data (Recommended)
Load the full Netflix dataset (5,850 items instead of 500):
```bash
cd backend
python data_pipeline/convert_netflix_dataset.py --limit 5850
python data_pipeline/run_netflix_pipeline_local.py
```

### Option 2: Use Dense Embeddings (Advanced)
Replace TF-IDF with dense embeddings like:
- Sentence-BERT (sentence-transformers)
- OpenAI embeddings
- Universal Sentence Encoder

Dense embeddings typically show 40-80% similarity scores for good matches.

### Option 3: Normalize Scores for Display
The UI can rescale scores to make them more intuitive:
- Map 20%+ → 80-100% (Excellent)
- Map 15-20% → 60-80% (Good)
- Map 10-15% → 40-60% (Fair)
- Map <10% → 0-40% (Poor)

## Current Status

✓ Your system is working correctly
✓ Results are ranked properly (best matches first)
✓ The 20-30% scores indicate strong semantic matches
✓ The recommendations are relevant to your queries

The scores reflect the mathematical reality of TF-IDF similarity, not the quality of the recommendations themselves.
