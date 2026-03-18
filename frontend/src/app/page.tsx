'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { apiClient } from '@/lib/api'
import { MediaRecommendation } from '@/types'
import MediaModal from '@/components/MediaModal'
import LandingHero from '@/components/LandingHero'

const EXAMPLE_QUERIES = [
  "a dark psychological thriller where you can't trust anyone",
  'sci-fi about AI taking over humanity',
  'comedy tv show about awkward office life',
  'documentary about a real crime',
  'something that makes you question everything',
  'action movie with a female lead who seeks revenge',
]

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
// Wallpaper grid card for each search result
// ---------------------------------------------------------------------------
function MediaCard({
  result, dark, onClick,
}: {
  result: MediaRecommendation
  dark: boolean
  onClick: () => void
}) {
  const [images, setImages] = useState<{ poster: string | null; backdrop: string | null } | null>(null)
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => {
    let cancelled = false
    fetch(`${apiUrl}/media/${result.id}/poster`)
      .then(r => r.json())
      .then(d => { if (!cancelled) setImages(d) })
      .catch(() => { if (!cancelled) setImages({ poster: null, backdrop: null }) })
    return () => { cancelled = true }
  }, [result.id, apiUrl])

  const pct = rescaleScore(result.similarity_score)
  const scoreCls = pct >= 80 ? 'bg-green-500' : pct >= 65 ? 'bg-yellow-500' : 'bg-gray-500'
  const bg = images?.backdrop || images?.poster

  return (
    <div
      onClick={onClick}
      className="group relative aspect-video rounded-xl overflow-hidden cursor-pointer
                 ring-2 ring-transparent hover:ring-red-500 transition-all duration-200 hover:scale-[1.02]"
    >
      {/* Background image or gradient placeholder */}
      {bg ? (
        <img
          src={bg}
          alt={result.title}
          className="absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
          loading="lazy"
        />
      ) : (
        <div className={`absolute inset-0 flex items-center justify-center
          ${images === null
            ? (dark ? 'bg-gray-800 animate-pulse' : 'bg-gray-200 animate-pulse')
            : 'bg-gradient-to-br from-gray-800 via-gray-900 to-black'
          }`}
        >
          {images !== null && (
            <span className="text-6xl opacity-30">
              {result.media_type === 'tv_show' ? '📺' : '🎬'}
            </span>
          )}
        </div>
      )}

      {/* Permanent bottom gradient */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/10 to-transparent" />

      {/* Score badge — top right */}
      <div className="absolute top-3 right-3">
        <span className={`text-xs font-bold px-2.5 py-1 rounded-md text-white ${scoreCls}`}>
          {pct}%
        </span>
      </div>

      {/* Default bottom info */}
      <div className="absolute bottom-0 left-0 right-0 p-4
                      translate-y-0 group-hover:translate-y-full transition-transform duration-300">
        <h3 className="text-white font-bold text-sm leading-snug line-clamp-2 mb-1">
          {result.title}
        </h3>
        <div className="flex items-center gap-2 flex-wrap">
          {result.metadata.year && (
            <span className="text-gray-300 text-xs">{result.metadata.year}</span>
          )}
          {result.metadata.rating && (
            <span className="text-yellow-400 text-xs">⭐ {result.metadata.rating.toFixed(1)}</span>
          )}
          {result.metadata.genre && (
            <span className="text-gray-400 text-xs bg-black/40 px-1.5 py-0.5 rounded">
              {result.metadata.genre}
            </span>
          )}
          <span className="text-gray-500 text-xs">
            {result.media_type === 'tv_show' ? 'TV Show' : 'Movie'}
          </span>
        </div>
      </div>

      {/* Hover overlay with description */}
      <div className="absolute inset-0 bg-black/80 opacity-0 group-hover:opacity-100
                      transition-opacity duration-300 flex flex-col justify-end p-4">
        <h3 className="text-white font-bold text-sm mb-1.5 line-clamp-1">{result.title}</h3>
        <p className="text-gray-300 text-xs leading-relaxed line-clamp-4 mb-3">
          {result.description}
        </p>
        <div className="flex items-center gap-2 flex-wrap">
          {result.metadata.year && (
            <span className="text-gray-400 text-xs">{result.metadata.year}</span>
          )}
          {result.metadata.rating && (
            <span className="text-yellow-400 text-xs">⭐ {result.metadata.rating.toFixed(1)}</span>
          )}
          {result.metadata.genre && (
            <span className="text-xs bg-white/10 text-gray-300 px-2 py-0.5 rounded">
              {result.metadata.genre}
            </span>
          )}
        </div>
        <p className="text-red-400 text-xs font-semibold mt-3 flex items-center gap-1">
          Tap for full details
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </p>
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
  const [selectedMedia, setSelectedMedia]   = useState<MediaRecommendation | null>(null)
  const [inputFocused, setInputFocused]     = useState(false)
  const inputRef        = useRef<HTMLInputElement>(null)
  const searchWrapperRef = useRef<HTMLDivElement>(null)

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

  // Close suggestions when clicking outside the search wrapper
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (searchWrapperRef.current && !searchWrapperRef.current.contains(e.target as Node)) {
        setInputFocused(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // ⌘K / Ctrl+K → focus search, Escape → close suggestions + blur
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        inputRef.current?.focus()
        setInputFocused(true)
      }
      if (e.key === 'Escape') {
        setInputFocused(false)
        inputRef.current?.blur()
      }
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

        {/* ---- Search bar — always at the top ---- */}
        <div className={`${query ? 'pt-8 pb-4' : 'pt-6 pb-4'} max-w-3xl mx-auto mb-6`}>
          <div ref={searchWrapperRef} className="relative">
            {/* Left icon: spinner while loading, magnifier otherwise */}
            <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none z-10">
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
              onFocus={() => setInputFocused(true)}
              placeholder="Describe a vibe, mood, or title…"
              className={`w-full pl-12 pr-16 py-4 border-2 rounded-2xl focus:outline-none transition-all text-base ${
                dark
                  ? 'text-white bg-gray-800 border-gray-700 placeholder-gray-500 focus:border-red-500'
                  : 'text-gray-900 bg-white border-gray-200 placeholder-gray-400 focus:border-red-500'
              } ${inputFocused && !query ? 'rounded-b-none border-b-0' : ''}`}
            />

            {/* Right: ⌘K hint or clear button */}
            <div className="absolute inset-y-0 right-4 flex items-center gap-2 z-10">
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

            {/* ---- Suggestions dropdown ---- */}
            {inputFocused && !query && (
              <div className={`absolute left-0 right-0 top-full z-50 border-2 border-t-0 rounded-b-2xl overflow-hidden shadow-xl ${
                dark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
              }`}>
                <p className={`px-4 pt-3 pb-1 text-xs font-semibold uppercase tracking-widest ${
                  dark ? 'text-gray-500' : 'text-gray-400'
                }`}>
                  Try asking
                </p>
                {EXAMPLE_QUERIES.map((q, i) => (
                  <button
                    key={q}
                    onMouseDown={(e) => {
                      e.preventDefault()
                      setQuery(q)
                      setDisplayCount(12)
                      setExpandedIds(new Set())
                      setInputFocused(false)
                    }}
                    className={`w-full flex items-center gap-3 px-4 py-3 text-sm text-left transition-colors ${
                      dark
                        ? 'text-gray-300 hover:bg-gray-700 hover:text-white'
                        : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                    } ${i < EXAMPLE_QUERIES.length - 1 ? (dark ? 'border-b border-gray-700/50' : 'border-b border-gray-100') : ''}`}
                  >
                    <svg className={`w-4 h-4 flex-shrink-0 ${dark ? 'text-gray-600' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    {q}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ---- Hero backdrop (hidden once user starts typing) ---- */}
        {!query && (
          <div>
            <LandingHero dark={dark} onSearch={(title) => { setQuery(title); setDisplayCount(12); setExpandedIds(new Set()) }} />
          </div>
        )}

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

            {/* Result grid */}
            {!loading && !error && results.length > 0 && (
              <div>
                <div className={`mb-6 pb-4 border-b ${dark ? 'border-gray-700' : 'border-gray-200'}`}>
                  <p className={`text-sm font-semibold uppercase tracking-wide ${dark ? 'text-gray-500' : 'text-gray-500'}`}>
                    FOUND <span className={dark ? 'text-white' : 'text-gray-900'}>{allResults.length} MATCHES</span>
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {results.map((result, i) => (
                    <div
                      key={result.id}
                      style={{ animationDelay: `${i * 40}ms` }}
                      className="animate-fadeInUp"
                    >
                      <MediaCard
                        result={result}
                        dark={dark}
                        onClick={() => setSelectedMedia(result)}
                      />
                    </div>
                  ))}
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
