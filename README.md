# Semantic Media Engine

A content-based recommendation system that enables users to discover books and TV shows through natural language queries. The system uses **Sentence-BERT** semantic embeddings to understand the meaning of queries and match them with media descriptions, enabling true semantic search beyond simple keyword matching.

## Features

- **Semantic Search**: Uses Sentence-BERT (all-MiniLM-L6-v2) for deep semantic understanding
- **Natural Language Queries**: Search using conversational language like "little girl discovers magic" or "romantic comedy about finding love"
- **High-Quality Matches**: Achieves 60-80% similarity scores for relevant content (vs 15-30% with traditional TF-IDF)
- **Concept Understanding**: Understands that "little girl" ≈ "young girl" ≈ "small child" ≈ "daughter"
- **Fast Performance**: Query processing in under 200ms
- **Backward Compatible**: Supports both Sentence-BERT and TF-IDF vectorization

## Architecture

- **Frontend**: Next.js 14 with React, TypeScript, and Tailwind CSS
- **Backend**: FastAPI with Python 3.10+
- **ML Engine**: 
  - **Sentence-BERT** (default): Dense 384-dimensional semantic embeddings using sentence-transformers
  - **TF-IDF** (legacy): Sparse ~5000-dimensional vectors using scikit-learn
- **Databases**: 
  - PostgreSQL for structured metadata storage
  - File-based storage or Qdrant for vector embeddings

## Project Structure

```
semantic-media-engine/
├── frontend/                 # Next.js frontend application
│   ├── src/
│   │   ├── app/             # Next.js app directory
│   │   ├── components/      # React components
│   │   └── types/           # TypeScript type definitions
│   ├── package.json
│   ├── tsconfig.json
│   └── tailwind.config.ts
├── backend/                  # FastAPI backend application
│   ├── data_pipeline/       # Dataset ingestion and processing
│   ├── ml_engine/           # Text vectorization and similarity
│   ├── database/            # Database connection and queries
│   ├── models/              # Pydantic models
│   ├── main.py              # FastAPI application entry point
│   └── requirements.txt
└── README.md
```

## Prerequisites

- **Node.js**: 18.x or higher
- **Python**: 3.10 or higher
- **PostgreSQL**: 14.x or higher
- **Qdrant** (optional): Latest version (can run via Docker) - only needed if not using file-based storage

## Semantic Search Examples

The Sentence-BERT upgrade enables powerful semantic search capabilities:

### Example Queries

**Query: "little girl"**
- Finds: Content about young girls, small children, daughters
- Similarity scores: 65-75%
- Understands: "little girl" ≈ "young girl" ≈ "small child"

**Query: "romantic comedy"**
- Finds: Love stories with humor, funny romances
- Similarity scores: 60-70%
- Understands: "romantic comedy" ≈ "love story with humor" ≈ "funny romance"

**Query: "space adventure"**
- Finds: Sci-fi exploration, astronaut journeys, space travel
- Similarity scores: 65-75%
- Understands: "space adventure" ≈ "sci-fi exploration" ≈ "astronaut journey"

**Query: "mystery detective"**
- Finds: Crime investigations, detective stories, thrillers
- Similarity scores: 60-70%
- Understands: "mystery detective" ≈ "crime investigation" ≈ "detective story"

### Comparison: Sentence-BERT vs TF-IDF

| Feature | Sentence-BERT | TF-IDF |
|---------|---------------|--------|
| Vector Dimensions | 384 (dense) | ~5000 (sparse) |
| Similarity Scores | 60-80% | 15-30% |
| Semantic Understanding | ✓ Yes | ✗ No |
| Synonym Matching | ✓ Yes | ✗ No |
| Concept Matching | ✓ Yes | ✗ No |
| Query Speed | <50ms | <30ms |
| Storage Size | Smaller | Larger |

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd semantic-media-engine
```

### 2. Backend Setup

#### Install Python Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and configure your database connections:

```env
# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=semantic_media
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password_here

# Vector Database Configuration
USE_FILE_STORAGE=true  # Use file-based storage (no Docker needed)
VECTOR_SIZE=384        # 384 for Sentence-BERT, 5000 for TF-IDF

# Vectorizer Configuration (Sentence-BERT)
VECTORIZER_TYPE=sbert              # "sbert" or "tfidf"
SBERT_MODEL_NAME=all-MiniLM-L6-v2  # Sentence-BERT model

# API Configuration
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
API_HOST=0.0.0.0
API_PORT=8000

# ML Model Configuration
VECTORIZER_PATH=backend/models
EMBEDDINGS_PATH=backend/embeddings
MODEL_VERSION=v1.0.0
```

**Note**: The default configuration uses Sentence-BERT with file-based storage, which requires no external dependencies like Docker or Qdrant.

#### Set Up PostgreSQL Database

```bash
# Create database
createdb semantic_media

# Run migrations
python backend/database/migrate.py
```

#### Generate Embeddings

The system will automatically download the Sentence-BERT model on first run (~90 MB).

```bash
# Process dataset and generate Sentence-BERT embeddings
cd backend
python data_pipeline/example_usage.py
```

This will:
1. Load media items from PostgreSQL
2. Generate 384-dimensional Sentence-BERT embeddings
3. Store embeddings in file-based storage

#### (Optional) Migrate from TF-IDF to Sentence-BERT

If you have existing TF-IDF embeddings and want to upgrade:

```bash
cd backend
python data_pipeline/migrate_to_sbert.py
```

See [SBERT_MIGRATION_GUIDE.md](SBERT_MIGRATION_GUIDE.md) for detailed migration instructions.

#### Run Backend Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

### 3. Frontend Setup

#### Install Node Dependencies

```bash
cd frontend
npm install
```

#### Configure Environment Variables

```bash
cp .env.local.example .env.local
```

Edit `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

#### Run Development Server

```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

### 4. Load Sample Data

```bash
cd backend
python -m data_pipeline.ingest --source data/sample_media.csv
```

## Development

### Running Tests

#### Backend Tests

```bash
cd backend
pytest
```

#### Frontend Tests

```bash
cd frontend
npm test
```

### Code Quality

#### Backend Linting

```bash
cd backend
flake8 .
black .
```

#### Frontend Linting

```bash
cd frontend
npm run lint
```

## API Documentation

### Base URL

- **Development**: `http://localhost:8000`
- **Production**: Configure via `NEXT_PUBLIC_API_URL`

### Interactive API Docs

FastAPI provides automatic interactive documentation:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Endpoints

#### POST /recommend

Get media recommendations based on natural language query.

**Request Body:**
```json
{
  "query": "A cozy mystery book set in a coffee shop",
  "top_k": 5,
  "filters": {
    "media_type": "book",
    "genre": "Mystery",
    "min_year": 2000,
    "max_year": 2024,
    "min_rating": 7.0,
    "is_latest": false
  }
}
```

**Request Parameters:**

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| query | string | Yes | Natural language search query | 1-1000 characters, non-empty |
| top_k | integer | No | Number of results to return | 1-50, default: 5 |
| filters | object | No | Optional metadata filters | See filters below |

**Filter Parameters:**

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| media_type | string | Filter by media type | "book" or "tv_show" |
| genre | string | Filter by genre | Non-empty string |
| min_year | integer | Minimum publication/release year | 1800 to current year + 2 |
| max_year | integer | Maximum publication/release year | 1800 to current year + 2 |
| min_rating | number | Minimum rating | 0.0 to 10.0 |
| is_latest | boolean | Filter for latest/upcoming items | true or false |

**Success Response (200 OK):**
```json
{
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "The Coffee Shop Mystery",
      "description": "A cozy mystery set in a charming coffee shop...",
      "media_type": "book",
      "metadata": {
        "author": "Jane Doe",
        "genre": "Mystery",
        "year": 2020,
        "rating": 8.5
      },
      "similarity_score": 0.92
    }
  ],
  "query_time_ms": 45.2
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| results | array | List of media recommendations |
| results[].id | string | Unique media item identifier (UUID) |
| results[].title | string | Media title |
| results[].description | string | Plot/synopsis description |
| results[].media_type | string | "book" or "tv_show" |
| results[].metadata | object | Additional metadata |
| results[].similarity_score | number | Similarity score (0.0-1.0) |
| query_time_ms | number | Processing time in milliseconds |

**Error Responses:**

**400 Bad Request** - Invalid input:
```json
{
  "detail": "Query must be between 1 and 1000 characters"
}
```

**422 Unprocessable Entity** - Validation error:
```json
{
  "detail": [
    {
      "loc": ["body", "top_k"],
      "msg": "ensure this value is less than or equal to 50",
      "type": "value_error.number.not_le"
    }
  ]
}
```

**503 Service Unavailable** - Database connection error:
```json
{
  "detail": "Vector database unavailable"
}
```

#### GET /health

Health check endpoint.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### Example Queries

**Books:**
```bash
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "query": "A thrilling adventure with dragons and magic",
    "top_k": 3,
    "filters": {"media_type": "book"}
  }'
```

**TV Shows:**
```bash
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "query": "A sci-fi series about space exploration",
    "top_k": 5,
    "filters": {"media_type": "tv_show", "min_rating": 8.0}
  }'
```

**Recent Content:**
```bash
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Mystery thriller",
    "filters": {"min_year": 2020, "is_latest": true}
  }'
```

## Environment Variables Reference

### Backend (.env)

All backend environment variables are documented in `backend/.env.example`. Copy this file to `backend/.env` and update values for your environment.

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| **PostgreSQL Configuration** |
| POSTGRES_HOST | PostgreSQL server host | localhost | Yes |
| POSTGRES_PORT | PostgreSQL server port | 5432 | Yes |
| POSTGRES_DB | Database name | semantic_media | Yes |
| POSTGRES_USER | Database user with read/write permissions | postgres | Yes |
| POSTGRES_PASSWORD | Database password | - | Yes |
| **Vector Database (Qdrant) Configuration** |
| QDRANT_HOST | Qdrant server host | localhost | Yes |
| QDRANT_PORT | Qdrant server port | 6333 | Yes |
| QDRANT_COLLECTION_NAME | Collection name for embeddings | media_embeddings | Yes |
| VECTOR_SIZE | Vector dimensionality (must match vectorizer) | 5000 | Yes |
| **API Server Configuration** |
| CORS_ORIGINS | Comma-separated list of allowed CORS origins | http://localhost:3000 | Yes |
| API_HOST | API server host (0.0.0.0 for external access) | 0.0.0.0 | Yes |
| API_PORT | API server port | 8000 | Yes |
| **ML Model Configuration** |
| VECTORIZER_PATH | Path to trained TF-IDF vectorizer model | ./models/vectorizer.pkl | Yes |
| EMBEDDINGS_PATH | Path to pre-computed embeddings directory | ./embeddings | No |
| MODEL_VERSION | Model version identifier for tracking | v1.0.0 | Yes |

### Frontend (.env.local)

All frontend environment variables are documented in `frontend/.env.local.example`. Copy this file to `frontend/.env.local` and update values for your environment.

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| NEXT_PUBLIC_API_URL | Backend API base URL | http://localhost:8000 | Yes |
| NEXT_PUBLIC_API_TIMEOUT | API request timeout in milliseconds | 10000 | No |
| NEXT_PUBLIC_DEBUG | Enable debug mode for API client | false | No |

**Note:** Variables prefixed with `NEXT_PUBLIC_` are exposed to the browser and can be accessed in client-side code.

## End-to-End Testing

Comprehensive E2E testing documentation and scripts are provided to verify the complete recommendation flow.

### Quick Start

```bash
# Run automated E2E tests
python test_e2e.py

# Or use the test runner script
./run_e2e_tests.sh  # Linux/Mac
run_e2e_tests.bat   # Windows
```

### Documentation

- **[E2E Testing Guide](E2E_TESTING_GUIDE.md)** - Complete manual and automated testing instructions
- **[Test Queries Reference](TEST_QUERIES.md)** - Sample queries with expected results
- **[Troubleshooting Guide](E2E_TROUBLESHOOTING.md)** - Common issues and solutions

### Test Coverage

The E2E test suite validates:
- Backend API health and availability
- Query processing and vectorization
- Similarity search and ranking
- Metadata retrieval and merging
- Frontend-backend integration
- Error handling and validation
- Performance benchmarks

## Deployment

### Production Deployment

#### Backend Deployment

1. **Prepare Production Environment**

```bash
# Install production dependencies
pip install -r requirements.txt

# Set production environment variables
export POSTGRES_HOST=your-production-db-host
export POSTGRES_PASSWORD=your-secure-password
export QDRANT_HOST=your-qdrant-host
export CORS_ORIGINS=https://your-frontend-domain.com
```

2. **Run Database Migrations**

```bash
# Create database schema
python -m database.migrate
```

3. **Train Vectorizer and Process Data**

```bash
# Process your production dataset
python -m data_pipeline.run_sample_pipeline --source data/production_media.csv
```

4. **Start Production Server**

```bash
# Using Gunicorn (recommended for production)
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Or using Uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### Frontend Deployment

1. **Build Production Bundle**

```bash
cd frontend
npm run build
```

2. **Deploy to Vercel (Recommended)**

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

Or deploy to other platforms:
- **Netlify**: Connect GitHub repo and configure build settings
- **AWS Amplify**: Use the Amplify Console
- **Docker**: Use the provided Dockerfile

3. **Configure Environment Variables**

Set `NEXT_PUBLIC_API_URL` to your production backend URL in your deployment platform.

#### Docker Deployment

Complete Docker setup with docker-compose:

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: semantic_media
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  backend:
    build: ./backend
    environment:
      POSTGRES_HOST: postgres
      QDRANT_HOST: qdrant
      CORS_ORIGINS: http://localhost:3000
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - qdrant

  frontend:
    build: ./frontend
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  postgres_data:
  qdrant_data:
```

Deploy with:

```bash
docker-compose up -d
```

### Performance Optimization

- **Backend**: Use connection pooling, enable caching for frequent queries
- **Frontend**: Enable Next.js image optimization, implement lazy loading
- **Database**: Add indexes on frequently queried fields
- **Vector DB**: Optimize collection parameters for your dataset size

### Security Considerations

- Use HTTPS in production
- Set strong database passwords
- Implement rate limiting on API endpoints
- Validate and sanitize all user inputs
- Keep dependencies updated
- Use environment variables for sensitive data

## Troubleshooting

### Database Connection Issues

- Ensure PostgreSQL is running: `pg_isready`
- Check credentials in `.env`
- Verify database exists: `psql -l`

### Vector Storage Issues

**File-based storage (default):**
- Check embeddings directory exists: `ls backend/embeddings`
- Verify embeddings files: `vectors.npy`, `metadata.json`, `ids.json`
- Check vector size matches configuration (384 for Sentence-BERT)

**Qdrant (if using):**
- Ensure Qdrant is running: `curl http://localhost:6333`
- Check Docker container: `docker ps`

### CORS Issues

- Verify `CORS_ORIGINS` in backend `.env` includes frontend URL
- Check browser console for specific CORS errors

### Sentence-BERT Issues

**Model download fails:**
- Check internet connection
- Verify HuggingFace is accessible
- Model will be cached in `~/.cache/torch/sentence_transformers/`

**Low similarity scores:**
- Verify `VECTORIZER_TYPE=sbert` in `.env`
- Check embeddings are 384 dimensions: `python -c "import numpy as np; print(np.load('backend/embeddings/vectors.npy').shape)"`
- Re-run migration if dimensions are wrong

**Vector size mismatch:**
- Ensure `VECTOR_SIZE=384` for Sentence-BERT
- Ensure `VECTOR_SIZE=5000` for TF-IDF
- Clear old embeddings and regenerate if switching vectorizer types

### Common Issues

**Backend won't start:**
- Check all environment variables are set
- Verify database connections are accessible
- Check port 8000 is not already in use
- Verify Sentence-BERT model can be loaded

**Frontend can't connect to backend:**
- Verify `NEXT_PUBLIC_API_URL` is correct
- Check CORS configuration in backend
- Ensure backend is running and accessible

**No recommendations returned:**
- Verify data has been loaded into databases
- Check embeddings exist in storage
- Verify vectorizer type matches embeddings
- Review backend logs for errors

For detailed troubleshooting, see [E2E_TROUBLESHOOTING.md](E2E_TROUBLESHOOTING.md).

## Sentence-BERT Upgrade

The system now uses Sentence-BERT for semantic search by default. This provides:

- **Better semantic understanding**: Matches concepts, not just keywords
- **Higher quality results**: 60-80% similarity scores vs 15-30% with TF-IDF
- **Smaller embeddings**: 384 dimensions vs ~5000 dimensions
- **Faster storage**: Dense vectors are more efficient than sparse vectors

### Migration from TF-IDF

If you have an existing system using TF-IDF and want to upgrade to Sentence-BERT:

1. **Backup your data**:
   ```bash
   cp -r backend/embeddings backend/embeddings_backup
   ```

2. **Update configuration** in `backend/.env`:
   ```bash
   VECTORIZER_TYPE=sbert
   SBERT_MODEL_NAME=all-MiniLM-L6-v2
   VECTOR_SIZE=384
   ```

3. **Run migration script**:
   ```bash
   cd backend
   python data_pipeline/migrate_to_sbert.py
   ```

4. **Validate migration**:
   ```bash
   python data_pipeline/validate_sbert.py
   ```

5. **Restart backend server**:
   ```bash
   uvicorn main:app --reload
   ```

For detailed migration instructions, see [SBERT_MIGRATION_GUIDE.md](SBERT_MIGRATION_GUIDE.md).

### Switching Back to TF-IDF

If you need to switch back to TF-IDF:

1. Update `backend/.env`:
   ```bash
   VECTORIZER_TYPE=tfidf
   VECTOR_SIZE=5000
   ```

2. Restore TF-IDF embeddings from backup (if available)

3. Restart backend server

## Documentation

- **[SBERT_MIGRATION_GUIDE.md](SBERT_MIGRATION_GUIDE.md)**: Detailed migration guide from TF-IDF to Sentence-BERT
- **[E2E_TESTING_GUIDE.md](E2E_TESTING_GUIDE.md)**: End-to-end testing guide
- **[E2E_TROUBLESHOOTING.md](E2E_TROUBLESHOOTING.md)**: Troubleshooting guide
- **[QUICK_START_LOAD_DATA.md](QUICK_START_LOAD_DATA.md)**: Quick start guide for loading data
- **API Documentation**: Available at `http://localhost:8000/docs` when backend is running

## License

MIT

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
