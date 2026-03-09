'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { apiClient } from '@/lib/api'
import { MediaRecommendation } from '@/types'

export default function Home() {
  const [query, setQuery] = useState<string>('')
  const [debouncedQuery, setDebouncedQuery] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(false)
  const [results, setResults] = useState<MediaRecommendation[]>([])
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query)
    }, 500)
    return () => clearTimeout(timer)
  }, [query])

  useEffect(() => {
    const fetchRecommendations = async () => {
      if (!debouncedQuery.trim() || debouncedQuery.trim().length < 3) {
        setResults([])
        setError(null)
        return
      }

      setLoading(true)
      setError(null)

      try {
        const response = await apiClient.getRecommendations({
          query: debouncedQuery,
          top_k: 12,
        })
        setResults(response.results as MediaRecommendation[])
        setError(null)
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message)
        } else {
          setError('An unexpected error occurred')
        }
        setResults([])
      } finally {
        setLoading(false)
      }
    }

    fetchRecommendations()
  }, [debouncedQuery])

  const handleQueryChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value)
  }, [])

  const rescaleScore = (rawScore: number): number => {
    // Sentence-BERT cosine similarity scores range from -1 to 1
    // In practice, scores above 0.3 indicate semantic relevance
    // We'll map 0.3-0.7 to 60-100% for better UX
    
    // Clamp score to valid range
    const clampedScore = Math.max(0, Math.min(1, rawScore))
    
    // Map 0.4-0.7 to 70-100% (most common range for good matches)
    if (clampedScore >= 0.4) {
      const normalized = Math.min((clampedScore - 0.4) / 0.3, 1)
      return 70 + normalized * 30
    }
    
    // Map 0.3-0.4 to 60-70% (decent matches)
    if (clampedScore >= 0.3) {
      return 60 + ((clampedScore - 0.3) / 0.1) * 10
    }
    
    // Map 0-0.3 to 0-60% (weak matches)
    return (clampedScore / 0.3) * 60
  }

  const genres = [
    { name: 'Action', image: '🎬' },
    { name: 'Sci-Fi', image: '🚀' },
    { name: 'Thriller', image: '🔪' },
    { name: 'Documentary', image: '📽️' },
    { name: 'Romance', image: '💕' },
    { name: 'Comedy', image: '😂' },
  ]


  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-center h-16">
            <div className="flex items-center gap-2">
              <span className="text-2xl">🎬</span>
              <h1 className="text-xl font-bold">
                <span className="text-gray-900">VIBECHECK</span>
                <span className="text-red-600">FINDER</span>
              </h1>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Hero Section */}
        {!query && (
          <div className="text-center py-16 sm:py-24">
            <h2 className="text-5xl sm:text-6xl lg:text-7xl font-bold mb-6">
              <div className="text-gray-900">Find your next</div>
              <div className="text-red-600">cinematic obsession.</div>
            </h2>
            <p className="text-gray-600 text-lg sm:text-xl max-w-2xl mx-auto mb-12">
              Experience the future of streaming. Our AI understands context, emotion, and nuance to find exactly what you're in the mood for.
            </p>
          </div>
        )}

        {/* Search Box - Always Rendered */}
        <div className={`${query ? 'py-8' : ''} max-w-3xl mx-auto mb-8`}>
          <div className="relative">
            <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
              <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={handleQueryChange}
              placeholder="Search with AI: 'A gritty crime drama set in New York'..."
              className={`w-full pl-12 pr-12 py-4 text-gray-900 bg-gray-50 border-2 border-gray-200 rounded-2xl focus:outline-none focus:border-red-500 focus:bg-white transition-all ${!query ? 'text-lg' : ''}`}
            />
            <div className="absolute inset-y-0 right-4 flex items-center">
              {!query ? (
                <kbd className="hidden sm:inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-gray-500 bg-white border border-gray-200 rounded">
                  <span>⌘</span>K
                </kbd>
              ) : (
                <button
                  onClick={() => setQuery('')}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
          </div>
          {!query && (
            <p className="text-gray-500 text-sm mt-3 text-center">
              Try searching for themes, moods, or specific plot points.
            </p>
          )}
        </div>

        {/* Hero Content - Genre Cards and Stats */}
        {!query && (
          <div className="text-center">

            {/* Genre Cards */}
            <div className="mb-16">
              <div className="mb-6">
                <h3 className="text-2xl font-bold text-gray-900">Explore Genres</h3>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
                {genres.map((genre) => (
                  <button
                    key={genre.name}
                    onClick={() => setQuery(genre.name.toLowerCase())}
                    className="group relative aspect-[3/4] rounded-2xl overflow-hidden bg-gradient-to-br from-gray-100 to-gray-200 hover:shadow-xl transition-all duration-300 hover:scale-105"
                  >
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent"></div>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span className="text-5xl mb-2 group-hover:scale-110 transition-transform">{genre.image}</span>
                      <span className="text-white font-bold text-lg">{genre.name}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 max-w-4xl mx-auto pb-16">
              <div className="text-center">
                <div className="text-4xl font-bold text-gray-900 mb-2">500+</div>
                <div className="text-gray-600">Movies & Shows Indexed</div>
              </div>
              <div className="text-center">
                <div className="text-4xl font-bold text-gray-900 mb-2">95%</div>
                <div className="text-gray-600">Search Accuracy</div>
              </div>
              <div className="text-center">
                <div className="text-4xl font-bold text-gray-900 mb-2">AI</div>
                <div className="text-gray-600">Powered Semantic Search</div>
              </div>
            </div>
          </div>
        )}

        {/* Search Results */}
        {query && (
          <div className="pb-8">

            {/* Loading */}
            {loading && (
              <div className="flex flex-col items-center justify-center py-20">
                <div className="w-12 h-12 border-4 border-gray-200 border-t-red-600 rounded-full animate-spin mb-4"></div>
                <p className="text-gray-600">Searching...</p>
              </div>
            )}

            {/* Error */}
            {error && !loading && (
              <div className="max-w-2xl mx-auto bg-red-50 border border-red-200 rounded-xl p-6">
                <p className="text-red-800 font-medium">Error: {error}</p>
              </div>
            )}

            {/* Results */}
            {!loading && !error && results.length > 0 && (
              <div>
                <div className="mb-6">
                  <h2 className="text-2xl font-bold text-gray-900">
                    Found {results.length} matches
                  </h2>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
                  {results.map((result) => (
                    <div
                      key={result.id}
                      className="group cursor-pointer"
                    >
                      <div className="relative aspect-[2/3] rounded-xl overflow-hidden bg-gradient-to-br from-gray-100 to-gray-200 mb-3 hover:shadow-xl transition-all duration-300 hover:scale-105">
                        {result.metadata.thumbnail_url ? (
                          <img
                            src={result.metadata.thumbnail_url}
                            alt={result.title}
                            className="w-full h-full object-cover"
                            onError={(e) => {
                              // Fallback to gradient if image fails to load
                              e.currentTarget.style.display = 'none'
                            }}
                          />
                        ) : null}
                        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent"></div>
                        
                        {/* Match Score */}
                        <div className="absolute top-2 right-2">
                          <div className="bg-green-500 text-white text-xs font-bold px-2 py-1 rounded-full">
                            {rescaleScore(result.similarity_score).toFixed(0)}%
                          </div>
                        </div>

                        {/* Content Info */}
                        <div className="absolute bottom-0 left-0 right-0 p-3">
                          <div className="flex items-center gap-2 mb-1">
                            {result.metadata.year && (
                              <span className="text-white text-xs">{result.metadata.year}</span>
                            )}
                            {result.metadata.rating && (
                              <span className="text-yellow-400 text-xs flex items-center gap-1">
                                ⭐ {result.metadata.rating.toFixed(1)}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Media Type Icon */}
                        <div className="absolute top-2 left-2">
                          <span className="text-2xl">{result.media_type === 'tv_show' ? '📺' : '🎬'}</span>
                        </div>
                      </div>
                      
                      <h3 className="font-semibold text-gray-900 text-sm mb-1 line-clamp-2 group-hover:text-red-600 transition-colors">
                        {result.title}
                      </h3>
                      {result.metadata.genre && (
                        <p className="text-gray-500 text-xs">{result.metadata.genre}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* No Results */}
            {!loading && !error && query.trim().length >= 3 && results.length === 0 && (
              <div className="text-center py-20">
                <div className="text-6xl mb-4">🔍</div>
                <p className="text-gray-900 text-xl font-semibold mb-2">No results found</p>
                <p className="text-gray-600">Try adjusting your search or explore our genres</p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
