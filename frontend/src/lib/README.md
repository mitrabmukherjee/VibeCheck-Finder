# API Client Library

This directory contains the API client for communicating with the Semantic Media Engine backend.

## Files

- `api.ts` - Main API client implementation
- `api.test.ts` - Comprehensive unit tests for the API client

## Usage

### Basic Usage

```typescript
import { apiClient } from '@/lib/api'

// Get recommendations
try {
  const response = await apiClient.getRecommendations({
    query: 'cozy mystery in coffee shop',
    top_k: 5,
  })
  
  console.log(response.results)
  console.log(`Query took ${response.query_time_ms}ms`)
} catch (error) {
  if (error instanceof APIError) {
    console.error(`API Error (${error.statusCode}): ${error.message}`)
  }
}
```

### With Filters

```typescript
const response = await apiClient.getRecommendations({
  query: 'sci-fi adventure',
  top_k: 10,
  filters: {
    media_type: 'tv_show',
    genre: 'Science Fiction',
    min_year: 2020,
    min_rating: 7.5,
  },
})
```

### Custom Configuration

```typescript
import { RecommendationAPI } from '@/lib/api'

const customApi = new RecommendationAPI({
  baseUrl: 'https://api.example.com',
  timeout: 15000, // 15 seconds
})

const response = await customApi.getRecommendations({
  query: 'fantasy adventure',
})
```

## Error Handling

The API client throws `APIError` instances for all errors:

```typescript
import { APIError } from '@/lib/api'

try {
  const response = await apiClient.getRecommendations({ query: 'test' })
} catch (error) {
  if (error instanceof APIError) {
    switch (error.statusCode) {
      case 400:
        // Bad request - invalid input
        break
      case 422:
        // Validation error
        break
      case 503:
        // Service unavailable
        break
      case 408:
        // Timeout
        break
      case 0:
        // Network error (no response from server)
        break
      default:
        // Other errors
        break
    }
  }
}
```

## Environment Variables

The API client reads the backend URL from the `NEXT_PUBLIC_API_URL` environment variable:

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Features

- ✅ Typed requests and responses using TypeScript interfaces
- ✅ Comprehensive error handling (HTTP errors, network failures, timeouts)
- ✅ Configurable request timeout (default: 10 seconds)
- ✅ User-friendly error messages
- ✅ Automatic JSON parsing
- ✅ Abort controller for timeout management
- ✅ Support for optional filters

## Testing

Run the tests:

```bash
npm test -- api.test.ts
```

The test suite includes:
- Constructor configuration tests
- Successful request handling
- HTTP error handling (400, 422, 503, 500, 404)
- Network error handling
- Timeout handling
- Filter support
- Error preservation
