'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { apiClient } from '@/lib/api'
import { MediaRecommendation } from '@/types'

export default function Home() {
  const [query, setQuery] = useState<string>('')
  const [debouncedQuery, setDebouncedQuery] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(false)
  const [results, setResults] = useState<MediaRecommendation[]>([])
  const [allResults, setAllResults] = useState<MediaRecommendation[]>([])
  const [displayCount, setDisplayCount] = useState<number>(12)
  const [error, setError] = useState<string | null>(null)
  const [darkMode, setDarkMode] = useState<boolean>(false)
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
        setAllResults([])
        setDisplayCount(12)
        setError(null)
        return
      }

      setLoading(true)
      setError(null)

      try {
        const response = await apiClient.getRecommendations({
          query: debouncedQuery,
          top_k: 50, // Fetch more results for pagination
        })
        setAllResults(response.results as MediaRecommendation[])
        setResults((response.results as MediaRecommendation[]).slice(0, 12))
        setError(null)
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message)
        } else {
          setError('An unexpected error occurred')
        }
        setResults([])
        setAllResults([])
      } finally {
        setLoading(false)
      }
    }

    fetchRecommendations()
  }, [debouncedQuery])

  const handleQueryChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value)
    setDisplayCount(12) // Reset display count on new query
  }, [])

  const handleLoadMore = useCallback(() => {
    const newCount = displayCount + 12
    setDisplayCount(newCount)
    setResults(allResults.slice(0, newCount))
  }, [displayCount, allResults])

  const toggleDarkMode = useCallback(() => {
    setDarkMode(!darkMode)
  }, [darkMode])

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [darkMode])

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
    <div className={`min-h-screen transition-colors duration-200 ${darkMode ? 'bg-gray-900' : 'bg-white'}`}>
      {/* Header */}
      <header className={`border-b transition-colors duration-200 ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-center h-16">
            <div className="flex items-center gap-2">
              <span className="text-2xl">🎬</span>
              <h1 className="text-xl font-bold">
                <span className={darkMode ? 'text-white' : 'text-gray-900'}>VIBECHECK</span>
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
              <div className={darkMode ? 'text-white' : 'text-gray-900'}>Find your next</div>
              <div className="text-red-600">cinematic obsession.</div>
            </h2>
            <p className={`text-lg sm:text-xl max-w-2xl mx-auto mb-12 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Experience the future of streaming. Our AI understands context, emotion, and nuance to find exactly what you&apos;re in the mood for.
            </p>
          </div>
        )}

        {/* Search Box - Always Rendered */}
        <div className={`${query ? 'py-8' : ''} max-w-3xl mx-auto mb-8`}>
          <div className="relative">
            <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
              <svg className={`w-5 h-5 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={handleQueryChange}
              placeholder="Search with AI: 'A gritty crime drama set in New York'..."
              className={`w-full pl-12 pr-12 py-4 border-2 rounded-2xl focus:outline-none focus:border-red-500 transition-all ${!query ? 'text-lg' : ''} ${
                darkMode 
                  ? 'text-white bg-gray-800 border-gray-700 placeholder-gray-500 focus:bg-gray-800' 
                  : 'text-gray-900 bg-gray-50 border-gray-200 focus:bg-white'
              }`}
            />
            <div className="absolute inset-y-0 right-4 flex items-center">
              {!query ? (
                <kbd className={`hidden sm:inline-flex items-center gap-1 px-2 py-1 text-xs font-medium border rounded ${
                  darkMode 
                    ? 'text-gray-400 bg-gray-800 border-gray-700' 
                    : 'text-gray-500 bg-white border-gray-200'
                }`}>
                  <span>⌘</span>K
                </kbd>
              ) : (
                <button
                  onClick={() => setQuery('')}
                  className={`transition-colors ${darkMode ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600'}`}
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
          </div>
          {!query && (
            <p className={`text-sm mt-3 text-center ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
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
                <h3 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>Explore Genres</h3>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
                {genres.map((genre) => (
                  <button
                    key={genre.name}
                    onClick={() => setQuery(genre.name.toLowerCase())}
                    className={`group relative aspect-[3/4] rounded-2xl overflow-hidden transition-all duration-300 hover:scale-105 ${
                      darkMode 
                        ? 'bg-gradient-to-br from-gray-800 to-gray-900 hover:shadow-xl' 
                        : 'bg-gradient-to-br from-gray-100 to-gray-200 hover:shadow-xl'
                    }`}
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
                <div className={`text-4xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>500+</div>
                <div className={darkMode ? 'text-gray-400' : 'text-gray-600'}>Movies & Shows Indexed</div>
              </div>
              <div className="text-center">
                <div className={`text-4xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>800ms</div>
                <div className={darkMode ? 'text-gray-400' : 'text-gray-600'}>Average Search Speed</div>
              </div>
              <div className="text-center">
                <div className={`text-4xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>AI</div>
                <div className={darkMode ? 'text-gray-400' : 'text-gray-600'}>Powered Semantic Search</div>
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
                <div className={`w-12 h-12 border-4 rounded-full animate-spin mb-4 ${
                  darkMode ? 'border-gray-700 border-t-red-600' : 'border-gray-200 border-t-red-600'
                }`}></div>
                <p className={darkMode ? 'text-gray-400' : 'text-gray-600'}>Searching...</p>
              </div>
            )}

            {/* Error */}
            {error && !loading && (
              <div className={`max-w-2xl mx-auto rounded-xl p-6 ${
                darkMode ? 'bg-red-900/20 border border-red-800' : 'bg-red-50 border border-red-200'
              }`}>
                <p className={`font-medium ${darkMode ? 'text-red-400' : 'text-red-800'}`}>Error: {error}</p>
              </div>
            )}

            {/* Results */}
            {!loading && !error && results.length > 0 && (
              <div>
                {/* Results Header */}
                <div className={`mb-6 pb-4 border-b transition-colors duration-200 ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                  <p className={`text-sm font-semibold uppercase tracking-wide ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                    FOUND <span className={darkMode ? 'text-white' : 'text-gray-900'}>{allResults.length} MATCHES</span>
                  </p>
                </div>

                {/* Results List */}
                <div className="space-y-6">
                  {results.map((result) => (
                    <div
                      key={result.id}
                      className={`rounded-xl p-6 hover:shadow-md transition-all duration-200 ${
                        darkMode 
                          ? 'bg-gray-800 hover:bg-gray-750' 
                          : 'bg-white hover:shadow-md'
                      }`}
                    >
                      <div className="flex items-start gap-4">
                        {/* Media Type Icon */}
                        <div className="flex-shrink-0">
                          <div className="w-14 h-14 bg-red-500 rounded-xl flex items-center justify-center">
                            <span className="text-2xl text-white">{result.media_type === 'tv_show' ? '📺' : '🎬'}</span>
                          </div>
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          {/* Title and Match Score */}
                          <div className="flex items-start justify-between gap-4 mb-2">
                            <h3 className={`text-xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                              {result.title}
                            </h3>
                            <div className="flex-shrink-0">
                              <div className="bg-green-500 text-white text-xs font-bold px-3 py-1.5 rounded-md">
                                {rescaleScore(result.similarity_score).toFixed(0)}% Match
                              </div>
                            </div>
                          </div>

                          {/* Metadata Row */}
                          <div className="flex flex-wrap items-center gap-3 mb-3 text-sm">
                            {result.metadata.year && (
                              <span className={`flex items-center gap-1.5 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
                                </svg>
                                {result.metadata.year}
                              </span>
                            )}
                            {result.metadata.rating && (
                              <span className={`flex items-center gap-1.5 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                                <svg className="w-4 h-4 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                                </svg>
                                {result.metadata.rating.toFixed(1)}
                              </span>
                            )}
                            {result.metadata.genre && (
                              <span className={`px-2.5 py-0.5 rounded-md text-xs font-medium uppercase ${
                                darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-700'
                              }`}>
                                {result.metadata.genre}
                              </span>
                            )}
                            <span className={`flex items-center gap-1.5 ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M2 6a2 2 0 012-2h6a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6zM14.553 7.106A1 1 0 0014 8v4a1 1 0 00.553.894l2 1A1 1 0 0018 13V7a1 1 0 00-1.447-.894l-2 1z" />
                              </svg>
                              {result.media_type === 'tv_show' ? 'TV Show' : 'Movie'}
                            </span>
                          </div>

                          {/* Description */}
                          <p className={`leading-relaxed text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                            {result.description}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Load More Button */}
                {results.length < allResults.length && (
                  <div className="flex justify-center mt-8">
                    <button 
                      onClick={handleLoadMore}
                      className={`px-6 py-3 border-2 font-medium rounded-xl transition-all duration-200 ${
                        darkMode 
                          ? 'bg-gray-800 border-gray-700 text-gray-300 hover:border-red-500 hover:text-red-400' 
                          : 'bg-white border-gray-200 text-gray-700 hover:border-red-500 hover:text-red-600'
                      }`}
                    >
                      Load more results
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* No Results */}
            {!loading && !error && query.trim().length >= 3 && results.length === 0 && (
              <div className="text-center py-20">
                <div className="text-6xl mb-4">🔍</div>
                <p className={`text-xl font-semibold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>No results found</p>
                <p className={darkMode ? 'text-gray-400' : 'text-gray-600'}>Try adjusting your search or explore our genres</p>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Dark Mode Toggle (bottom right) */}
      <button
        onClick={toggleDarkMode}
        className={`fixed bottom-6 right-6 w-12 h-12 border-2 rounded-full flex items-center justify-center transition-all duration-200 shadow-lg ${
          darkMode 
            ? 'bg-gray-800 border-gray-700 hover:border-gray-600' 
            : 'bg-white border-gray-200 hover:border-gray-300'
        }`}
        aria-label="Toggle dark mode"
      >
        {darkMode ? (
          <svg className="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
          </svg>
        ) : (
          <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
          </svg>
        )}
      </button>
    </div>
  )
}
