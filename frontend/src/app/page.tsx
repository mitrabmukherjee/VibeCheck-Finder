'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { apiClient } from '@/lib/api'
import { MediaRecommendation } from '@/types'
import MediaModal from '@/components/MediaModal'
import LandingHero from '@/components/LandingHero'

const GENRES = [
  { name: 'Action',      emoji: '🎬' },
  { name: 'Sci-Fi',      emoji: '🚀' },
  { name: 'Thriller',    emoji: '🔪' },
  { name: 'Documentary', emoji: '📽️' },
  { name: 'Romance',     emoji: '💕' },
  { name: 'Comedy',      emoji: '😂' },
]

// ---------------------------------------------------------------------------
// Skeleton card shown while loading
// ---------------------------------------------------------------------------
function SkeletonCard({ dark }: { dark: boolean }) {
  const bg = dark ? 'bg-gray-700' : 'bg-gray-200'
  const card = dark ? 'bg-gray-800' : 'bg-white border border-gray-100'
  return (
    <div className={`rounded-xl p-6 ${card}`}>
      <div className="flex items-start gap-4">
        <div className={`w-14 h-14 rounded-xl flex-shrink-0 ${bg} animate-pulse`} />
        <div className="flex-1 min-w-0 space-y-3">
          <div className="flex items-start justify-between gap-4">
            <div className={`h-5 rounded-lg w-2/3 ${bg} animate-pulse`} />
            <div className={`h-5 rounded-md w-20 flex-shrink-0 ${bg} animate-pulse`} />
          </div>
          <div className="flex gap-3">
            <div className={`h-3.5 rounded w-12 ${bg} animate-pulse`} />
            <div className={`h-3.5 rounded w-10 ${bg} animate-pulse`} />
            <div className={`h-3.5 rounded w-16 ${bg} animate-pulse`} />
          </div>
          <div className="space-y-2">
            <div className={`h-3 rounded w-full ${bg} animate-pulse`} />
            <div className={`h-3 rounded w-5/6 ${bg} animate-pulse`} />
            <div className={`h-3 rounded w-4/6 ${bg} animate-pulse`} />
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Match score badge — colour shifts green → yellow → grey by score
// ---------------------------------------------------------------------------
function ScoreBadge({ score }: { score: number }) {
  const pct = rescaleScore(score)
  const cls =
    pct >= 80 ? 'bg-green-500 text-white' :
    pct >= 65 ? 'bg-yellow-500 text-white' :
                'bg-gray-500 text-white'
  return (
    <span className={`text-xs font-bold px-3 py-1.5 rounded-md flex-shrink-0 ${cls}`}>
      {pct}% Match
    </span>
  )
}

function rescaleScore(raw: number): number {
  const c = Math.max(0, Math.min(1, raw))
  if (c >= 0.4) return Math.round(70 + Math.min((c - 0.4) / 0.3, 1) * 30)
  if (c >= 0.3) return Math.round(60 + ((c - 0.3) / 0.1) * 10)
  return Math.round((c / 0.3) * 60)
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function Home() {
  const [query, setQuery]               = useState('')
  const [debouncedQuery, setDebounced]  = useState('')
  const [loading, setLoading]           = useState(false)
  const [results, setResults]           = useState<MediaRecommendation[]>([])
  const [allResults, setAllResults]     = useState<MediaRecommendation[]>([])
  const [displayCount, setDisplayCount] = useState(12)
  const [error, setError]               = useState<string | null>(null)
  const [dark, setDark]                 = useState(false)
  const [expandedIds, setExpandedIds]   = useState<Set<string>>(new Set())
  const [selectedMedia, setSelectedMedia] = useState<MediaRecommendation | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Restore dark mode from localStorage / system preference
  useEffect(() => {
    const saved = localStorage.getItem('vibecheck-dark')
    if (saved !== null) {
      setDark(saved === 'true')
    } else {
      setDark(window.matchMedia('(prefers-color-scheme: dark)').matches)
    }
  }, [])

  // Persist dark mode + apply to <html>
  useEffect(() => {
    localStorage.setItem('vibecheck-dark', String(dark))
    document.documentElement.classList.toggle('dark', dark)
  }, [dark])

  // ⌘K / Ctrl+K → focus search, Escape → blur
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        inputRef.current?.focus()
      }
      if (e.key === 'Escape') inputRef.current?.blur()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  // Debounce query → debouncedQuery
  useEffect(() => {
    const t = setTimeout(() => setDebounced(query), 500)
    return () => clearTimeout(t)
  }, [query])

  // Fetch recommendations when debouncedQuery changes
  useEffect(() => {
    const run = async () => {
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
        const res = await apiClient.getRecommendations({ query: debouncedQuery, top_k: 50 })
        const all = res.results as MediaRecommendation[]
        setAllResults(all)
        setResults(all.slice(0, 12))
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unexpected error occurred')
        setResults([])
        setAllResults([])
      } finally {
        setLoading(false)
      }
    }
    run()
  }, [debouncedQuery])

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value)
    setDisplayCount(12)
    setExpandedIds(new Set())
  }, [])

  const clearQuery = useCallback(() => {
    setQuery('')
    setExpandedIds(new Set())
  }, [])

  const handleLoadMore = useCallback(() => {
    const n = displayCount + 12
    setDisplayCount(n)
    setResults(allResults.slice(0, n))
  }, [displayCount, allResults])

  const toggleDark = useCallback(() => setDark(d => !d), [])

  const toggleExpand = useCallback((id: string) => {
    setExpandedIds(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }, [])

  // Retry: re-trigger by nudging the debounced value
  const retry = useCallback(() => setDebounced(q => q + ' '), [])

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  return (
    <div className={`min-h-screen transition-colors duration-300 ${dark ? 'bg-gray-900' : 'bg-gray-50'}`}>

      {/* ---- Sticky header ---- */}
      <header className={`sticky top-0 z-50 border-b backdrop-blur-sm transition-colors duration-300 ${
        dark ? 'bg-gray-900/90 border-gray-700' : 'bg-white/90 border-gray-200'
      }`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🎬</span>
            <h1 className="text-xl font-bold tracking-tight">
              <span className={dark ? 'text-white' : 'text-gray-900'}>VIBECHECK</span>
              <span className="text-red-600">FINDER</span>
            </h1>
          </div>

          {/* Dark mode toggle in header */}
          <button
            onClick={toggleDark}
            className={`w-9 h-9 rounded-full flex items-center justify-center transition-all border ${
              dark
                ? 'bg-gray-800 border-gray-700 hover:border-gray-500 text-yellow-400'
                : 'bg-white border-gray-200 hover:border-gray-300 text-gray-600'
            }`}
            aria-label="Toggle dark mode"
          >
            {dark ? (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
            )}
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

        {/* ---- Hero backdrop (hidden once user starts typing) ---- */}
        {!query && (
          <div className="pt-6">
            <LandingHero dark={dark} onSearch={(title) => { setQuery(title); setDisplayCount(12); setExpandedIds(new Set()) }} />
          </div>
        )}

        {/* ---- Search bar ---- */}
        <div className={`${query ? 'py-8' : 'py-6'} max-w-3xl mx-auto mb-8`}>
          <div className="relative">
            {/* Left icon: spinner while loading, magnifier otherwise */}
            <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
              {loading ? (
                <div className={`w-5 h-5 border-2 rounded-full animate-spin ${
                  dark ? 'border-gray-600 border-t-red-500' : 'border-gray-300 border-t-red-500'
                }`} />
              ) : (
                <svg className={`w-5 h-5 ${dark ? 'text-gray-500' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              )}
            </div>

            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={handleChange}
              placeholder="Try: 'a dark psychological thriller where you can't trust anyone'..."
              className={`w-full pl-12 pr-16 py-4 border-2 rounded-2xl focus:outline-none transition-all ${!query ? 'text-lg' : ''} ${
                dark
                  ? 'text-white bg-gray-800 border-gray-700 placeholder-gray-500 focus:border-red-500'
                  : 'text-gray-900 bg-white border-gray-200 placeholder-gray-400 focus:border-red-500'
              }`}
            />

            {/* Right: ⌘K hint or clear button */}
            <div className="absolute inset-y-0 right-4 flex items-center gap-2">
              {query ? (
                <button
                  onClick={clearQuery}
                  className={`rounded-full p-1 transition-colors ${
                    dark ? 'text-gray-500 hover:text-gray-300 hover:bg-gray-700' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
                  }`}
                  aria-label="Clear search"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              ) : (
                <kbd className={`hidden sm:inline-flex items-center gap-1 px-2 py-1 text-xs font-medium border rounded ${
                  dark ? 'text-gray-400 bg-gray-700 border-gray-600' : 'text-gray-500 bg-gray-50 border-gray-200'
                }`}>
                  <span>⌘</span>K
                </kbd>
              )}
            </div>
          </div>
        </div>

        {/* ---- Landing content: genre cards + stats ---- */}
        {!query && (
          <div>
            {/* Genre cards */}
            <div className="mb-16">
              <p className={`text-xs font-semibold uppercase tracking-widest mb-6 text-center ${dark ? 'text-gray-500' : 'text-gray-400'}`}>
                Browse by genre
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
                {GENRES.map(g => (
                  <button
                    key={g.name}
                    onClick={() => setQuery(g.name.toLowerCase())}
                    className={`group relative aspect-[3/4] rounded-2xl overflow-hidden transition-all duration-300 hover:scale-105 hover:shadow-xl ${
                      dark
                        ? 'bg-gradient-to-br from-gray-800 to-gray-900'
                        : 'bg-gradient-to-br from-gray-100 to-gray-200'
                    }`}
                  >
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span className="text-5xl mb-2 group-hover:scale-110 transition-transform duration-200">{g.emoji}</span>
                      <span className="text-white font-bold text-lg">{g.name}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 max-w-4xl mx-auto pb-16">
              {[
                { value: '5,000+',  label: 'Movies & Shows Indexed' },
                { value: '<200ms',  label: 'Average Search Speed'   },
                { value: 'AI',      label: 'Powered Semantic Search' },
              ].map(s => (
                <div key={s.label} className="text-center">
                  <div className={`text-4xl font-bold mb-2 ${dark ? 'text-white' : 'text-gray-900'}`}>{s.value}</div>
                  <div className={dark ? 'text-gray-400' : 'text-gray-500'}>{s.label}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ---- Results area ---- */}
        {query && (
          <div className="pb-12">

            {/* Skeleton loading */}
            {loading && (
              <div className="space-y-4">
                <div className={`h-5 w-32 rounded animate-pulse mb-6 ${dark ? 'bg-gray-700' : 'bg-gray-200'}`} />
                {Array.from({ length: 6 }).map((_, i) => (
                  <SkeletonCard key={i} dark={dark} />
                ))}
              </div>
            )}

            {/* Error state with retry */}
            {error && !loading && (
              <div className={`max-w-2xl mx-auto rounded-xl p-6 ${
                dark ? 'bg-red-900/20 border border-red-800' : 'bg-red-50 border border-red-200'
              }`}>
                <p className={`font-medium mb-3 ${dark ? 'text-red-400' : 'text-red-700'}`}>{error}</p>
                <button
                  onClick={retry}
                  className="text-sm font-medium text-red-600 hover:text-red-500 underline underline-offset-2"
                >
                  Try again
                </button>
              </div>
            )}

            {/* Result cards */}
            {!loading && !error && results.length > 0 && (
              <div>
                <div className={`mb-6 pb-4 border-b ${dark ? 'border-gray-700' : 'border-gray-200'}`}>
                  <p className={`text-sm font-semibold uppercase tracking-wide ${dark ? 'text-gray-500' : 'text-gray-500'}`}>
                    FOUND <span className={dark ? 'text-white' : 'text-gray-900'}>{allResults.length} MATCHES</span>
                  </p>
                </div>

                <div className="space-y-4">
                  {results.map((result, i) => {
                    const expanded = expandedIds.has(result.id)
                    const longDesc = result.description.length > 220
                    return (
                      <div
                        key={result.id}
                        style={{ animationDelay: `${i * 40}ms` }}
                        onClick={() => setSelectedMedia(result)}
                        className={`rounded-xl p-6 transition-all duration-200 animate-fadeInUp cursor-pointer ${
                          dark
                            ? 'bg-gray-800 hover:bg-gray-700'
                            : 'bg-white border border-gray-100 hover:border-gray-200 hover:shadow-md'
                        }`}
                      >
                        <div className="flex items-start gap-4">
                          {/* Icon */}
                          <div className="flex-shrink-0">
                            <div className="w-14 h-14 bg-red-500 rounded-xl flex items-center justify-center">
                              <span className="text-2xl">{result.media_type === 'tv_show' ? '📺' : '🎬'}</span>
                            </div>
                          </div>

                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            {/* Title + score */}
                            <div className="flex items-start justify-between gap-4 mb-2">
                              <h3 className={`text-lg font-bold leading-snug ${dark ? 'text-white' : 'text-gray-900'}`}>
                                {result.title}
                              </h3>
                              <ScoreBadge score={result.similarity_score} />
                            </div>

                            {/* Metadata pills */}
                            <div className="flex flex-wrap items-center gap-3 mb-3 text-sm">
                              {result.metadata.year && (
                                <span className={`flex items-center gap-1.5 ${dark ? 'text-gray-400' : 'text-gray-500'}`}>
                                  <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
                                  </svg>
                                  {result.metadata.year}
                                </span>
                              )}
                              {result.metadata.rating && (
                                <span className={`flex items-center gap-1.5 ${dark ? 'text-gray-400' : 'text-gray-500'}`}>
                                  <svg className="w-3.5 h-3.5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                                  </svg>
                                  {result.metadata.rating.toFixed(1)}
                                </span>
                              )}
                              {result.metadata.genre && (
                                <span className={`px-2.5 py-0.5 rounded-md text-xs font-medium ${
                                  dark ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600'
                                }`}>
                                  {result.metadata.genre}
                                </span>
                              )}
                              <span className={`text-xs ${dark ? 'text-gray-500' : 'text-gray-400'}`}>
                                {result.media_type === 'tv_show' ? 'TV Show' : 'Movie'}
                              </span>
                            </div>

                            {/* Description with read more */}
                            <p className={`text-sm leading-relaxed ${dark ? 'text-gray-400' : 'text-gray-600'}`}>
                              {expanded || !longDesc
                                ? result.description
                                : result.description.slice(0, 220) + '…'}
                            </p>
                            {longDesc && (
                              <button
                                onClick={e => { e.stopPropagation(); toggleExpand(result.id) }}
                                className={`text-xs mt-1.5 font-medium ${
                                  dark ? 'text-red-400 hover:text-red-300' : 'text-red-600 hover:text-red-500'
                                }`}
                              >
                                {expanded ? 'Show less' : 'Read more'}
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>

                {/* Load more */}
                {results.length < allResults.length && (
                  <div className="flex justify-center mt-8">
                    <button
                      onClick={handleLoadMore}
                      className={`px-6 py-3 border-2 font-medium rounded-xl transition-all ${
                        dark
                          ? 'bg-gray-800 border-gray-700 text-gray-300 hover:border-red-500 hover:text-red-400'
                          : 'bg-white border-gray-200 text-gray-700 hover:border-red-500 hover:text-red-600'
                      }`}
                    >
                      Load {Math.min(12, allResults.length - results.length)} more results
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* No results — show genre shortcuts */}
            {!loading && !error && debouncedQuery.trim().length >= 3 && results.length === 0 && (
              <div className="text-center py-20">
                <div className="text-6xl mb-4">🔍</div>
                <p className={`text-xl font-semibold mb-2 ${dark ? 'text-white' : 'text-gray-900'}`}>
                  No results found
                </p>
                <p className={`mb-6 ${dark ? 'text-gray-400' : 'text-gray-500'}`}>
                  Try rephrasing or browse a genre below
                </p>
                <div className="flex flex-wrap justify-center gap-2">
                  {GENRES.map(g => (
                    <button
                      key={g.name}
                      onClick={() => setQuery(g.name.toLowerCase())}
                      className={`px-4 py-2 rounded-full text-sm border transition-all hover:scale-105 ${
                        dark
                          ? 'bg-gray-800 border-gray-700 text-gray-300 hover:border-red-500 hover:text-red-400'
                          : 'bg-white border-gray-200 text-gray-600 hover:border-red-400 hover:text-red-600'
                      }`}
                    >
                      {g.emoji} {g.name}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Media detail modal */}
      {selectedMedia && (
        <MediaModal
          media={selectedMedia}
          dark={dark}
          onClose={() => setSelectedMedia(null)}
        />
      )}
    </div>
  )
}
