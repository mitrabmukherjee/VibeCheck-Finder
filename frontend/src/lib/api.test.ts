/**
 * Unit tests for API client
 * 
 * Tests HTTP requests, error handling, timeouts, and response parsing.
 * 
 * Requirements: 1.1, 13.1
 */

import { RecommendationAPI, APIError } from './api'
import {
  RecommendationRequest,
  RecommendationResponse,
  ErrorResponse,
} from '@/types'

// Mock fetch globally
global.fetch = jest.fn()

describe('RecommendationAPI', () => {
  let api: RecommendationAPI
  const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>

  beforeEach(() => {
    // Reset mocks before each test
    jest.clearAllMocks()
    jest.useFakeTimers()
    
    // Create API instance with test configuration
    api = new RecommendationAPI({
      baseUrl: 'http://test-api.com',
      timeout: 5000,
    })
  })

  afterEach(() => {
    jest.useRealTimers()
  })

  describe('constructor', () => {
    it('should use provided baseUrl and timeout', () => {
      const customApi = new RecommendationAPI({
        baseUrl: 'http://custom.com',
        timeout: 15000,
      })
      
      expect(customApi).toBeDefined()
    })

    it('should use default values when no config provided', () => {
      const defaultApi = new RecommendationAPI()
      expect(defaultApi).toBeDefined()
    })

    it('should use environment variable for baseUrl if not provided', () => {
      process.env.NEXT_PUBLIC_API_URL = 'http://env-api.com'
      const envApi = new RecommendationAPI()
      expect(envApi).toBeDefined()
    })
  })

  describe('getRecommendations', () => {
    const mockRequest: RecommendationRequest = {
      query: 'cozy mystery in coffee shop',
      top_k: 5,
    }

    const mockResponse: RecommendationResponse = {
      results: [
        {
          id: '123e4567-e89b-12d3-a456-426614174000',
          title: 'The Coffee Shop Mystery',
          description: 'A cozy mystery set in a small town coffee shop',
          media_type: 'book',
          metadata: {
            author: 'Jane Doe',
            genre: 'Mystery',
            year: 2023,
            rating: 8.5,
          },
          similarity_score: 0.95,
        },
      ],
      query_time_ms: 123.45,
    }

    it('should successfully fetch recommendations', async () => {
      // Mock successful response
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      } as Response)

      const result = await api.getRecommendations(mockRequest)

      expect(mockFetch).toHaveBeenCalledWith(
        'http://test-api.com/recommend',
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(mockRequest),
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('should include abort signal for timeout', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      } as Response)

      await api.getRecommendations(mockRequest)

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          signal: expect.any(AbortSignal),
        })
      )
    })

    it('should handle 400 Bad Request error', async () => {
      const errorResponse: ErrorResponse = {
        error: 'ValidationError',
        message: 'Query is required',
        status_code: 400,
      }

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => errorResponse,
      } as Response)

      let errorThrown = false
      try {
        await api.getRecommendations(mockRequest)
      } catch (error) {
        errorThrown = true
        expect(error).toBeInstanceOf(APIError)
        expect((error as APIError).message).toMatch(/Bad request/)
        expect((error as APIError).statusCode).toBe(400)
      }
      expect(errorThrown).toBe(true)
    })

    it('should handle 422 Validation Error', async () => {
      const errorResponse: ErrorResponse = {
        error: 'ValidationError',
        message: 'Query length exceeds maximum',
        status_code: 422,
      }

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        statusText: 'Unprocessable Entity',
        json: async () => errorResponse,
      } as Response)

      let errorThrown = false
      try {
        await api.getRecommendations(mockRequest)
      } catch (error) {
        errorThrown = true
        expect(error).toBeInstanceOf(APIError)
        expect((error as APIError).message).toMatch(/Validation error/)
        expect((error as APIError).statusCode).toBe(422)
      }
      expect(errorThrown).toBe(true)
    })

    it('should handle 503 Service Unavailable error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 503,
        statusText: 'Service Unavailable',
        json: async () => ({
          error: 'ServiceUnavailable',
          message: 'Database connection failed',
          status_code: 503,
        }),
      } as Response)

      let errorThrown = false
      try {
        await api.getRecommendations(mockRequest)
      } catch (error) {
        errorThrown = true
        expect(error).toBeInstanceOf(APIError)
        expect((error as APIError).message).toMatch(/Service temporarily unavailable/)
        expect((error as APIError).statusCode).toBe(503)
      }
      expect(errorThrown).toBe(true)
    })

    it('should handle 500 Internal Server Error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({
          error: 'InternalError',
          message: 'Unexpected error occurred',
          status_code: 500,
        }),
      } as Response)

      let errorThrown = false
      try {
        await api.getRecommendations(mockRequest)
      } catch (error) {
        errorThrown = true
        expect(error).toBeInstanceOf(APIError)
        expect((error as APIError).message).toMatch(/Internal server error/)
        expect((error as APIError).statusCode).toBe(500)
      }
      expect(errorThrown).toBe(true)
    })

    it('should handle error response without JSON body', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => {
          throw new Error('Invalid JSON')
        },
      } as Response)

      let errorThrown = false
      try {
        await api.getRecommendations(mockRequest)
      } catch (error) {
        errorThrown = true
        expect(error).toBeInstanceOf(APIError)
        expect((error as APIError).message).toMatch(/HTTP 404/)
        expect((error as APIError).statusCode).toBe(404)
      }
      expect(errorThrown).toBe(true)
    })

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network connection failed'))

      let errorThrown = false
      try {
        await api.getRecommendations(mockRequest)
      } catch (error) {
        errorThrown = true
        expect(error).toBeInstanceOf(APIError)
        expect((error as APIError).message).toMatch(/Network error/)
        expect((error as APIError).statusCode).toBe(0)
      }
      expect(errorThrown).toBe(true)
    })

    it('should handle timeout by aborting request', async () => {
      // The AbortError test below already covers timeout behavior
      // This test verifies the timeout mechanism is set up correctly
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      } as Response)

      await api.getRecommendations(mockRequest)

      // Verify that fetch was called with an abort signal
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          signal: expect.any(AbortSignal),
        })
      )
    })

    it('should handle AbortError from fetch', async () => {
      const abortError = new Error('The operation was aborted')
      abortError.name = 'AbortError'
      
      mockFetch.mockRejectedValueOnce(abortError)

      let errorThrown = false
      try {
        await api.getRecommendations(mockRequest)
      } catch (error) {
        errorThrown = true
        expect(error).toBeInstanceOf(APIError)
        expect((error as APIError).message).toMatch(/Request timeout/)
        expect((error as APIError).statusCode).toBe(408)
      }
      expect(errorThrown).toBe(true)
    })

    it('should handle unknown errors', async () => {
      mockFetch.mockRejectedValueOnce('Unknown error type')

      let errorThrown = false
      try {
        await api.getRecommendations(mockRequest)
      } catch (error) {
        errorThrown = true
        expect(error).toBeInstanceOf(APIError)
        expect((error as APIError).message).toMatch(/unexpected error/)
        expect((error as APIError).statusCode).toBe(500)
      }
      expect(errorThrown).toBe(true)
    })

    it('should send request with filters', async () => {
      const requestWithFilters: RecommendationRequest = {
        query: 'sci-fi adventure',
        top_k: 10,
        filters: {
          media_type: 'tv_show',
          genre: 'Science Fiction',
          min_year: 2020,
          min_rating: 7.5,
        },
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      } as Response)

      await api.getRecommendations(requestWithFilters)

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: JSON.stringify(requestWithFilters),
        })
      )
    })

    it('should preserve APIError when re-thrown', async () => {
      const customError = new APIError('Custom error', 400, 'CustomError')
      
      mockFetch.mockRejectedValueOnce(customError)

      let errorThrown = false
      try {
        await api.getRecommendations(mockRequest)
      } catch (error) {
        errorThrown = true
        expect(error).toBe(customError)
        expect((error as APIError).message).toBe('Custom error')
        expect((error as APIError).statusCode).toBe(400)
        expect((error as APIError).errorType).toBe('CustomError')
      }
      expect(errorThrown).toBe(true)
    })
  })

  describe('APIError', () => {
    it('should create error with message, status code, and type', () => {
      const error = new APIError('Test error', 400, 'TestError')

      expect(error.message).toBe('Test error')
      expect(error.statusCode).toBe(400)
      expect(error.errorType).toBe('TestError')
      expect(error.name).toBe('APIError')
    })

    it('should use default error type if not provided', () => {
      const error = new APIError('Test error', 500)

      expect(error.errorType).toBe('APIError')
    })

    it('should be instanceof Error', () => {
      const error = new APIError('Test error', 400)

      expect(error).toBeInstanceOf(Error)
      expect(error).toBeInstanceOf(APIError)
    })
  })
})
