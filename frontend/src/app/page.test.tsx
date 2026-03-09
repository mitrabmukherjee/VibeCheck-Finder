/**
 * Component tests for SearchPage
 * 
 * Tests search input, debouncing, loading states, results rendering,
 * error handling, and empty states.
 * 
 * Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Home from './page'
import { apiClient } from '@/lib/api'
import { MediaRecommendation } from '@/types'

// Mock the API client
jest.mock('@/lib/api', () => ({
  apiClient: {
    getRecommendations: jest.fn(),
  },
}))

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>

describe('SearchPage Component', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    jest.useFakeTimers()
  })

  afterEach(() => {
    jest.useRealTimers()
  })

  describe('Initial Render', () => {
    it('should render the page title and description', () => {
      render(<Home />)

      expect(screen.getByText('Semantic Media Engine')).toBeInTheDocument()
      expect(
        screen.getByText('Discover books and TV shows through natural language queries')
      ).toBeInTheDocument()
    })

    it('should render search input with placeholder', () => {
      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      expect(input).toBeInTheDocument()
      expect(input).toHaveAttribute(
        'placeholder',
        'e.g., A cozy mystery book set in a coffee shop...'
      )
    })

    it('should render helper text about minimum characters', () => {
      render(<Home />)

      expect(screen.getByText('Enter at least 3 characters to search')).toBeInTheDocument()
    })

    it('should not show loading indicator initially', () => {
      render(<Home />)

      expect(screen.queryByText('Searching...')).not.toBeInTheDocument()
    })

    it('should not show error message initially', () => {
      render(<Home />)

      expect(screen.queryByText('Error')).not.toBeInTheDocument()
    })

    it('should not show results initially', () => {
      render(<Home />)

      expect(screen.queryByText(/Recommendations/)).not.toBeInTheDocument()
    })
  })

  describe('Search Input and Debouncing', () => {
    it('should update input value when user types', async () => {
      const user = userEvent.setup({ delay: null })
      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      await user.type(input, 'mystery')

      expect(input).toHaveValue('mystery')
    })

    it('should debounce API calls by 500ms', async () => {
      const user = userEvent.setup({ delay: null })
      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      
      // Type query
      await user.type(input, 'cozy mystery')

      // API should not be called immediately
      expect(mockApiClient.getRecommendations).not.toHaveBeenCalled()

      // Fast-forward time by 499ms (just before debounce)
      jest.advanceTimersByTime(499)
      expect(mockApiClient.getRecommendations).not.toHaveBeenCalled()

      // Fast-forward time by 1ms more (total 500ms)
      jest.advanceTimersByTime(1)
      
      // Now API should be called
      await waitFor(() => {
        expect(mockApiClient.getRecommendations).toHaveBeenCalledTimes(1)
      })
    })

    it('should reset debounce timer on each keystroke', async () => {
      const user = userEvent.setup({ delay: null })
      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      
      // Type first character
      await user.type(input, 'm')
      jest.advanceTimersByTime(300)

      // Type second character (resets timer)
      await user.type(input, 'y')
      jest.advanceTimersByTime(300)

      // Type third character (resets timer)
      await user.type(input, 's')
      
      // API should not be called yet
      expect(mockApiClient.getRecommendations).not.toHaveBeenCalled()

      // Fast-forward full 500ms from last keystroke
      jest.advanceTimersByTime(500)
      
      await waitFor(() => {
        expect(mockApiClient.getRecommendations).toHaveBeenCalledTimes(1)
      })
    })

    it('should not call API for queries shorter than 3 characters', async () => {
      const user = userEvent.setup({ delay: null })
      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      
      // Type 2 characters
      await user.type(input, 'ab')
      jest.advanceTimersByTime(500)

      // API should not be called
      await waitFor(() => {
        expect(mockApiClient.getRecommendations).not.toHaveBeenCalled()
      })
    })

    it('should not call API for empty query', async () => {
      const user = userEvent.setup({ delay: null })
      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      
      // Type and then clear
      await user.type(input, 'test')
      await user.clear(input)
      jest.advanceTimersByTime(500)

      // API should not be called
      await waitFor(() => {
        expect(mockApiClient.getRecommendations).not.toHaveBeenCalled()
      })
    })

    it('should not call API for whitespace-only query', async () => {
      const user = userEvent.setup({ delay: null })
      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      
      // Type only spaces
      await user.type(input, '   ')
      jest.advanceTimersByTime(500)

      // API should not be called
      await waitFor(() => {
        expect(mockApiClient.getRecommendations).not.toHaveBeenCalled()
      })
    })
  })

  describe('Loading State', () => {
    it('should show loading indicator when fetching recommendations', async () => {
      const user = userEvent.setup({ delay: null })
      
      // Mock API to return a promise that doesn't resolve immediately
      let resolvePromise: (value: any) => void
      const promise = new Promise((resolve) => {
        resolvePromise = resolve
      })
      mockApiClient.getRecommendations.mockReturnValue(promise as any)

      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      await user.type(input, 'mystery book')
      jest.advanceTimersByTime(500)

      // Wait for loading state to appear
      await waitFor(() => {
        expect(screen.getByText('Searching...')).toBeInTheDocument()
      })

      // Resolve the promise
      resolvePromise!({ results: [], query_time_ms: 100 })
    })

    it('should hide loading indicator after successful fetch', async () => {
      const user = userEvent.setup({ delay: null })
      
      mockApiClient.getRecommendations.mockResolvedValue({
        results: [],
        query_time_ms: 100,
      })

      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      await user.type(input, 'mystery book')
      jest.advanceTimersByTime(500)

      // Wait for loading to complete
      await waitFor(() => {
        expect(screen.queryByText('Searching...')).not.toBeInTheDocument()
      })
    })

    it('should hide loading indicator after error', async () => {
      const user = userEvent.setup({ delay: null })
      
      mockApiClient.getRecommendations.mockRejectedValue(
        new Error('Network error')
      )

      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      await user.type(input, 'mystery book')
      jest.advanceTimersByTime(500)

      // Wait for loading to complete
      await waitFor(() => {
        expect(screen.queryByText('Searching...')).not.toBeInTheDocument()
      })
    })
  })

  describe('Recommendation Results Rendering', () => {
    const mockResults: MediaRecommendation[] = [
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
      {
        id: '223e4567-e89b-12d3-a456-426614174001',
        title: 'Sci-Fi Adventure',
        description: 'An exciting space adventure',
        media_type: 'tv_show',
        metadata: {
          director: 'John Smith',
          genre: 'Science Fiction',
          year: 2022,
          rating: 9.0,
          seasons: 3,
        },
        similarity_score: 0.87,
      },
    ]

    it('should display recommendations after successful fetch', async () => {
      const user = userEvent.setup({ delay: null })
      
      mockApiClient.getRecommendations.mockResolvedValue({
        results: mockResults,
        query_time_ms: 123.45,
      })

      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      await user.type(input, 'mystery')
      jest.advanceTimersByTime(500)

      // Wait for results to appear
      await waitFor(() => {
        expect(screen.getByText('Recommendations (2)')).toBeInTheDocument()
      })
    })

    it('should render recommendation cards with title', async () => {
      const user = userEvent.setup({ delay: null })
      
      mockApiClient.getRecommendations.mockResolvedValue({
        results: mockResults,
        query_time_ms: 123.45,
      })

      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      await user.type(input, 'mystery')
      jest.advanceTimersByTime(500)

      await waitFor(() => {
        expect(screen.getByText('The Coffee Shop Mystery')).toBeInTheDocument()
        expect(screen.getByText('Sci-Fi Adventure')).toBeInTheDocument()
      })
    })

    it('should render recommendation cards with description', async () => {
      const user = userEvent.setup({ delay: null })
      
      mockApiClient.getRecommendations.mockResolvedValue({
        results: mockResults,
        query_time_ms: 123.45,
      })

      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      await user.type(input, 'mystery')
      jest.advanceTimersByTime(500)

      await waitFor(() => {
        expect(
          screen.getByText('A cozy mystery set in a small town coffee shop')
        ).toBeInTheDocument()
        expect(screen.getByText('An exciting space adventure')).toBeInTheDocument()
      })
    })

    it('should render similarity score as percentage', async () => {
      const user = userEvent.setup({ delay: null })
      
      mockApiClient.getRecommendations.mockResolvedValue({
        results: mockResults,
        query_time_ms: 123.45,
      })

      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      await user.type(input, 'mystery')
      jest.advanceTimersByTime(500)

      await waitFor(() => {
        expect(screen.getByText('95.0% match')).toBeInTheDocument()
        expect(screen.getByText('87.0% match')).toBeInTheDocument()
      })
    })

    it('should render media type badge for books', async () => {
      const user = userEvent.setup({ delay: null })
      
      mockApiClient.getRecommendations.mockResolvedValue({
        results: mockResults,
        query_time_ms: 123.45,
      })

      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      await user.type(input, 'mystery')
      jest.advanceTimersByTime(500)

      await waitFor(() => {
        expect(screen.getByText('📚 Book')).toBeInTheDocument()
      })
    })

    it('should render media type badge for TV shows', async () => {
      const user = userEvent.setup({ delay: null })
      
      mockApiClient.getRecommendations.mockResolvedValue({
        results: mockResults,
        query_time_ms: 123.45,
      })

      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      await user.type(input, 'mystery')
      jest.advanceTimersByTime(500)

      await waitFor(() => {
        expect(screen.getByText('📺 TV Show')).toBeInTheDocument()
      })
    })

    it('should render metadata fields when present', async () => {
      const user = userEvent.setup({ delay: null })
      
      mockApiClient.getRecommendations.mockResolvedValue({
        results: mockResults,
        query_time_ms: 123.45,
      })

      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      await user.type(input, 'mystery')
      jest.advanceTimersByTime(500)

      await waitFor(() => {
        // Book metadata
        expect(screen.getByText('by Jane Doe')).toBeInTheDocument()
        expect(screen.getByText('Mystery')).toBeInTheDocument()
        expect(screen.getByText('2023')).toBeInTheDocument()
        expect(screen.getByText('⭐ 8.5/10')).toBeInTheDocument()

        // TV show metadata
        expect(screen.getByText('dir. John Smith')).toBeInTheDocument()
        expect(screen.getByText('Science Fiction')).toBeInTheDocument()
        expect(screen.getByText('2022')).toBeInTheDocument()
        expect(screen.getByText('⭐ 9.0/10')).toBeInTheDocument()
      })
    })

    it('should not render metadata fields when absent', async () => {
      const user = userEvent.setup({ delay: null })
      
      const minimalResult: MediaRecommendation = {
        id: '323e4567-e89b-12d3-a456-426614174002',
        title: 'Minimal Book',
        description: 'A book with minimal metadata',
        media_type: 'book',
        metadata: {},
        similarity_score: 0.75,
      }

      mockApiClient.getRecommendations.mockResolvedValue({
        results: [minimalResult],
        query_time_ms: 100,
      })

      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      await user.type(input, 'minimal')
      jest.advanceTimersByTime(500)

      await waitFor(() => {
        expect(screen.getByText('Minimal Book')).toBeInTheDocument()
        // Should not render metadata that doesn't exist
        expect(screen.queryByText(/by /)).not.toBeInTheDocument()
        expect(screen.queryByText(/dir\./)).not.toBeInTheDocument()
        expect(screen.queryByText(/⭐/)).not.toBeInTheDocument()
      })
    })
  })

  describe('Error Handling', () => {
    it('should display error message when API call fails', async () => {
      const user = userEvent.setup({ delay: null })
      
      mockApiClient.getRecommendations.mockRejectedValue(
        new Error('Network connection failed')
      )

      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      await user.type(input, 'mystery')
      jest.advanceTimersByTime(500)

      await waitFor(() => {
        expect(screen.getByText('Error')).toBeInTheDocument()
        expect(screen.getByText('Network connection failed')).toBeInTheDocument()
      })
    })

    it('should display generic error for non-Error exceptions', async () => {
      const user = userEvent.setup({ delay: null })
      
      mockApiClient.getRecommendations.mockRejectedValue('Unknown error')

      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      await user.type(input, 'mystery')
      jest.advanceTimersByTime(500)

      await waitFor(() => {
        expect(screen.getByText('Error')).toBeInTheDocument()
        expect(screen.getByText('An unexpected error occurred')).toBeInTheDocument()
      })
    })

    it('should clear results when error occurs', async () => {
      const user = userEvent.setup({ delay: null })
      
      // First successful call
      mockApiClient.getRecommendations.mockResolvedValueOnce({
        results: [
          {
            id: '123',
            title: 'Test Book',
            description: 'Test description',
            media_type: 'book',
            metadata: {},
            similarity_score: 0.9,
          },
        ],
        query_time_ms: 100,
      })

      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      await user.type(input, 'test')
      jest.advanceTimersByTime(500)

      await waitFor(() => {
        expect(screen.getByText('Test Book')).toBeInTheDocument()
      })

      // Second call fails
      mockApiClient.getRecommendations.mockRejectedValueOnce(
        new Error('Server error')
      )

      await user.clear(input)
      await user.type(input, 'error')
      jest.advanceTimersByTime(500)

      await waitFor(() => {
        expect(screen.queryByText('Test Book')).not.toBeInTheDocument()
        expect(screen.getByText('Server error')).toBeInTheDocument()
      })
    })

    it('should not show error when loading', async () => {
      const user = userEvent.setup({ delay: null })
      
      let resolvePromise: (value: any) => void
      const promise = new Promise((resolve) => {
        resolvePromise = resolve
      })
      mockApiClient.getRecommendations.mockReturnValue(promise as any)

      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      await user.type(input, 'mystery')
      jest.advanceTimersByTime(500)

      await waitFor(() => {
        expect(screen.getByText('Searching...')).toBeInTheDocument()
      })

      // Error should not be visible while loading
      expect(screen.queryByText('Error')).not.toBeInTheDocument()

      // Resolve with error
      resolvePromise!({ results: [], query_time_ms: 100 })
    })

    it('should clear error when new search succeeds', async () => {
      const user = userEvent.setup({ delay: null })
      
      // First call fails
      mockApiClient.getRecommendations.mockRejectedValueOnce(
        new Error('Network error')
      )

      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      await user.type(input, 'error')
      jest.advanceTimersByTime(500)

      await waitFor(() => {
        expect(screen.getByText('Network error')).toBeInTheDocument()
      })

      // Second call succeeds
      mockApiClient.getRecommendations.mockResolvedValueOnce({
        results: [],
        query_time_ms: 100,
      })

      await user.clear(input)
      await user.type(input, 'success')
      jest.advanceTimersByTime(500)

      await waitFor(() => {
        expect(screen.queryByText('Network error')).not.toBeInTheDocument()
      })
    })
  })

  describe('Empty State', () => {
    it('should show empty state when no results found', async () => {
      const user = userEvent.setup({ delay: null })
      
      mockApiClient.getRecommendations.mockResolvedValue({
        results: [],
        query_time_ms: 100,
      })

      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      await user.type(input, 'nonexistent query')
      jest.advanceTimersByTime(500)

      await waitFor(() => {
        expect(screen.getByText('No recommendations found')).toBeInTheDocument()
        expect(screen.getByText('Try a different search query')).toBeInTheDocument()
      })
    })

    it('should not show empty state for queries shorter than 3 characters', async () => {
      const user = userEvent.setup({ delay: null })
      
      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      await user.type(input, 'ab')
      jest.advanceTimersByTime(500)

      await waitFor(() => {
        expect(screen.queryByText('No recommendations found')).not.toBeInTheDocument()
      })
    })

    it('should not show empty state when loading', async () => {
      const user = userEvent.setup({ delay: null })
      
      let resolvePromise: (value: any) => void
      const promise = new Promise((resolve) => {
        resolvePromise = resolve
      })
      mockApiClient.getRecommendations.mockReturnValue(promise as any)

      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      await user.type(input, 'mystery')
      jest.advanceTimersByTime(500)

      await waitFor(() => {
        expect(screen.getByText('Searching...')).toBeInTheDocument()
      })

      expect(screen.queryByText('No recommendations found')).not.toBeInTheDocument()

      resolvePromise!({ results: [], query_time_ms: 100 })
    })

    it('should not show empty state when error occurs', async () => {
      const user = userEvent.setup({ delay: null })
      
      mockApiClient.getRecommendations.mockRejectedValue(
        new Error('Network error')
      )

      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      await user.type(input, 'mystery')
      jest.advanceTimersByTime(500)

      await waitFor(() => {
        expect(screen.getByText('Error')).toBeInTheDocument()
      })

      expect(screen.queryByText('No recommendations found')).not.toBeInTheDocument()
    })
  })

  describe('API Integration', () => {
    it('should call API with correct query parameter', async () => {
      const user = userEvent.setup({ delay: null })
      
      mockApiClient.getRecommendations.mockResolvedValue({
        results: [],
        query_time_ms: 100,
      })

      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      await user.type(input, 'cozy mystery')
      jest.advanceTimersByTime(500)

      await waitFor(() => {
        expect(mockApiClient.getRecommendations).toHaveBeenCalledWith({
          query: 'cozy mystery',
          top_k: 5,
        })
      })
    })

    it('should call API with top_k parameter', async () => {
      const user = userEvent.setup({ delay: null })
      
      mockApiClient.getRecommendations.mockResolvedValue({
        results: [],
        query_time_ms: 100,
      })

      render(<Home />)

      const input = screen.getByRole('textbox', { name: /search query/i })
      await user.type(input, 'mystery')
      jest.advanceTimersByTime(500)

      await waitFor(() => {
        expect(mockApiClient.getRecommendations).toHaveBeenCalledWith(
          expect.objectContaining({
            top_k: 5,
          })
        )
      })
    })
  })
})
