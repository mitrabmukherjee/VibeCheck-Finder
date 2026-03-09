/**
 * API Client for Semantic Media Engine Backend
 * 
 * Provides a typed interface for communicating with the FastAPI backend.
 * Handles HTTP requests, error handling, timeouts, and response parsing.
 * 
 * Requirements: 1.1, 13.1
 */

import {
  RecommendationRequest,
  RecommendationResponse,
  ErrorResponse,
} from '@/types'

/**
 * Custom error class for API-related errors
 */
export class APIError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public errorType: string = 'APIError'
  ) {
    super(message)
    this.name = 'APIError'
  }
}

/**
 * Configuration options for API requests
 */
export interface APIConfig {
  /** Base URL for the API (defaults to NEXT_PUBLIC_API_URL) */
  baseUrl?: string
  /** Request timeout in milliseconds (default: 10000) */
  timeout?: number
}

/**
 * API client for backend communication
 * 
 * Handles HTTP requests to the FastAPI backend with comprehensive error handling,
 * timeout configuration, and typed responses.
 */
export class RecommendationAPI {
  private readonly baseUrl: string
  private readonly timeout: number

  /**
   * Initialize the API client
   * 
   * @param config - Optional configuration for base URL and timeout
   */
  constructor(config: APIConfig = {}) {
    this.baseUrl = config.baseUrl || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    this.timeout = config.timeout || 10000 // Default: 10 seconds
  }

  /**
   * Get recommendations from the backend
   * 
   * Sends a query to the /recommend endpoint and returns matching media items
   * sorted by similarity score.
   * 
   * @param request - Recommendation request with query and optional parameters
   * @returns Promise resolving to recommendation response
   * @throws APIError for HTTP errors or network failures
   * 
   * Requirements: 1.1, 13.1
   */
  async getRecommendations(
    request: RecommendationRequest
  ): Promise<RecommendationResponse> {
    const url = `${this.baseUrl}/recommend`

    try {
      // Create abort controller for timeout
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), this.timeout)

      // Make HTTP POST request
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
        signal: controller.signal,
      })

      // Clear timeout
      clearTimeout(timeoutId)

      // Handle HTTP errors
      if (!response.ok) {
        await this.handleErrorResponse(response)
      }

      // Parse and return successful response
      const data: RecommendationResponse = await response.json()
      return data
    } catch (error) {
      // Handle network errors and timeouts
      if (error instanceof APIError) {
        throw error
      }

      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new APIError(
            `Request timeout after ${this.timeout}ms`,
            408,
            'TimeoutError'
          )
        }

        // Network error (no response from server)
        throw new APIError(
          `Network error: ${error.message}`,
          0,
          'NetworkError'
        )
      }

      // Unknown error
      throw new APIError(
        'An unexpected error occurred',
        500,
        'UnknownError'
      )
    }
  }

  /**
   * Handle error responses from the backend
   * 
   * Parses error response and throws appropriate APIError with descriptive message.
   * 
   * @param response - HTTP response object
   * @throws APIError with status code and error message
   */
  private async handleErrorResponse(response: Response): Promise<never> {
    const statusCode = response.status
    let errorMessage = `HTTP ${statusCode}: ${response.statusText}`
    let errorType = 'HTTPError'

    try {
      // Try to parse error response body
      const errorData: ErrorResponse = await response.json()
      errorMessage = errorData.message || errorMessage
      errorType = errorData.error || errorType
    } catch {
      // If parsing fails, use default error message
      // This handles cases where the response body is not JSON
    }

    // Provide user-friendly messages for common error codes
    switch (statusCode) {
      case 400:
        errorMessage = `Bad request: ${errorMessage}`
        break
      case 422:
        errorMessage = `Validation error: ${errorMessage}`
        break
      case 503:
        errorMessage = 'Service temporarily unavailable. Please try again later.'
        break
      case 500:
        errorMessage = 'Internal server error. Please try again later.'
        break
    }

    throw new APIError(errorMessage, statusCode, errorType)
  }
}

/**
 * Default API client instance
 * 
 * Singleton instance for use throughout the application.
 */
export const apiClient = new RecommendationAPI()
