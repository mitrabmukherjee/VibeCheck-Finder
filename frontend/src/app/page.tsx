'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { apiClient } from '@/lib/api'
import { MediaRecommendation } from '@/types'
import MediaModal from '@/components/MediaModal'
import LandingHero from '@/components/LandingHero'

// ─── Constants ────────────────────────────────────────────────────────────────

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

const GENRE_GRADIENTS: Record<string, string> = {
  action:      'from-red-900    to-red-950',
  scifi:       'from-blue-900   to-blue-950',
  thriller:    'from-purple-900 to-purple-950',
  drama:       'from-amber-900  to-amber-950',
  comedy:      'from-yellow-800 to-yellow-950',
  documentary: 'from-green-900  to-green-950',
  romance:     'from-pink-900   to-pink-950',
  animation:   'from-cyan-900   to-cyan-950',
  horror:      'from-zinc-900   to-black',
  crime:       'from-slate-900  to-slate-950',
}

const DECADES = [
  { label: 'Any',     min: null, max: null  },
  { label: '2020s',   min: 2020, max: 2029  },
  { label: '2010s',   min: 2010, max: 2019  },
  { label: '2000s',   min: 2000, max: 2009  },
  { label: '90s',     min: 1990, max: 1999  },
  { label: 'Classic', min: null, max: 1989  },
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

function rescaleScore(raw: number): number {
  const c = Math.max(0, Math.min(1, raw))
  if (c >= 0.4) return Math.round(70 + Math.min((c - 0.4) / 0.3, 1) * 30)
  if (c >= 0.3) return Math.round(60 + ((c - 0.3) / 0.1) * 10)
  return Math.round((c / 0.3) * 60)
}

// ─── SkeletonCard ─────────────────────────────────────────────────────────────

function SkeletonCard({ dark }: { dark: boolean }) {
  const base = dark ? 'bg-gray-700' : 'bg-gray-200'
  return (
    <div className={`rounded-xl overflow-hidden ${dark ? 'bg-gray-800' : 'bg-white border border-gray-100'}`}>
      <div className={`aspect-video w-full animate-pulse ${base}`} />
      <div className="p-3 space-y-2 md:hidden">
        <div className={`h-4 w-2/3 rounded animate-pulse ${base}`} />
        <div className={`h-3 w-full rounded animate-pulse ${base}`} />
      </div>
    </div>
  )
}

// ─── MediaCard ────────────────────────────────────────────────────────────────

interface Images { poster: string | null; backdrop: string | null }

function MediaCard({
  result, dark, onClick, images,
}: {
  result: MediaRecommendation
  dark: boolean
  onClick: () => void
  images: Images | undefined
}) {
  const pct      = rescaleScore(result.similarity_score)
  const scoreCls = pct >= 80 ? 'bg-green-500' : pct >= 65 ? 'bg-yellow-500' : 'bg-gray-500'
  const bg       = images?.backdrop || images?.poster
  const genreKey = (result.metadata.genre || '').toLowerCase().replace(/[\s\-/]+/g, '')
  const grad     = GENRE_GRADIENTS[genreKey] ?? 'from-gray-800 to-gray-950'

  return (
    <div
      onClick={onClick}
      className="cursor-pointer group rounded-xl overflow-hidden ring-2 ring-transparent
                 hover:ring-red-500 transition-all duration-200 hover:scale-[1.02]"
    >
      {/* ── Image section ── */}
      <div className="relative aspect-video">

        {/* Background */}
        {bg ? (
          <img
            src={bg}
            alt={result.title}
            className="absolute inset-0 w-full h-full object-cover
                       group-hover:scale-105 transition-transform duration-500"
            loading="lazy"
          />
        ) : images === undefined ? (
          <div className={`absolute inset-0 animate-pulse ${dark ? 'bg-gray-800' : 'bg-gray-200'}`} />
        ) : (
          <div className={`absolute inset-0 bg-gradient-to-br ${grad}
                           flex flex-col items-center justify-center gap-2`}>
            <div className="w-14 h-14 rounded-full bg-white/10 flex items-center justify-center">
              <span className="text-2xl font-bold text-white/70">{result.title[0]}</span>
            </div>
            <span className="text-white/40 text-xs">
              {result.metadata.genre || (result.media_type === 'tv_show' ? 'TV' : 'Film')}
            </span>
          </div>
        )}

        {bg && <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/10 to-transparent" />}

        {/* Score badge */}
        <div className="absolute top-2.5 right-2.5 z-10">
          <span className={`text-xs font-bold px-2 py-1 rounded-md text-white ${scoreCls}`}>{pct}%</span>
        </div>

        {/* Default bottom info — slides away on hover (desktop only) */}
        <div className="absolute bottom-0 left-0 right-0 p-3
                        translate-y-0 group-hover:translate-y-full transition-transform duration-300">
          <h3 className="text-white font-bold text-sm line-clamp-1">{result.title}</h3>
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            {result.metadata.year   && <span className="text-gray-300 text-xs">{result.metadata.year}</span>}
            {result.metadata.rating && <span className="text-yellow-400 text-xs">⭐ {result.metadata.rating.toFixed(1)}</span>}
            {result.metadata.genre  && (
              <span className="text-gray-400 text-xs bg-black/30 px-1.5 py-0.5 rounded">
                {result.metadata.genre}
              </span>
            )}
          </div>
        </div>

        {/* Hover overlay with description (desktop) */}
        <div className="absolute inset-0 bg-black/80 opacity-0 group-hover:opacity-100
                        transition-opacity duration-300 hidden md:flex flex-col justify-end p-4">
          <h3 className="text-white font-bold text-sm mb-1.5 line-clamp-1">{result.title}</h3>
          <p className="text-gray-300 text-xs leading-relaxed line-clamp-4 mb-2">
            {result.description}
          </p>
          <div className="flex items-center gap-2">
            {result.metadata.year   && <span className="text-gray-400 text-xs">{result.metadata.year}</span>}
            {result.metadata.rating && <span className="text-yellow-400 text-xs">⭐ {result.metadata.rating.toFixed(1)}</span>}
          </div>
          <p className="text-red-400 text-xs font-semibold mt-2.5 flex items-center gap-1">
            Tap for full details
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </p>
        </div>
      </div>

      {/* ── Mobile info (always visible, no hover needed) ── */}
      <div className={`md:hidden p-3 border-t ${dark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-100'}`}>
        <h3 className={`text-sm font-bold mb-1 ${dark ? 'text-white' : 'text-gray-900'}`}>
          {result.title}
        </h3>
        <div className="flex items-center gap-2 mb-1.5 flex-wrap">
          {result.metadata.year   && <span className={`text-xs ${dark ? 'text-gray-400' : 'text-gray-500'}`}>{result.metadata.year}</span>}
          {result.metadata.rating && <span className="text-yellow-500 text-xs">⭐ {result.metadata.rating.toFixed(1)}</span>}
          {result.metadata.genre  && (
            <span className={`text-xs px-1.5 py-0.5 rounded ${dark ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600'}`}>
              {result.metadata.genre}
            </span>
          )}
        </div>
        <p className={`text-xs leading-relaxed line-clamp-2 ${dark ? 'text-gray-400' : 'text-gray-600'}`}>
          {result.description}
        </p>
      </div>
    </div>
  )
}

// ─── Filter pill button ───────────────────────────────────────────────────────

function FilterPill({
  label, active, dark, onClick,
}: {
  label: string; active: boolean; dark: boolean; onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1 rounded-full text-xs font-medium border transition-all whitespace-nowrap ${
        active
          ? 'bg-red-600 border-red-600 text-white'
          : dark
            ? 'bg-gray-800 border-gray-700 text-gray-300 hover:border-red-500 hover:text-red-400'
            : 'bg-white border-gray-200 text-gray-600 hover:border-red-400 hover:text-red-600'
      }`}
    >
      {label}
    </button>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function Home() {
  const [query, setQuery]               = useState('')
  const [debouncedQuery, setDebounced]  = useState('')
  const [loading, setLoading]           = useState(false)
  const [results, setResults]           = useState<MediaRecommendation[]>([])
  const [allResults, setAllResults]     = useState<MediaRecommendation[]>([])
  const [displayCount, setDisplayCount] = useState(12)
  const [error, setError]               = useState<string | null>(null)
  const [dark, setDark]                 = useState(false)
  const [selectedMedia, setSelectedMedia] = useState<MediaRecommendation | null>(null)
  const [inputFocused, setInputFocused] = useState(false)

  // filters
  const [filterType,   setFilterType]   = useState<'' | 'movie' | 'tv_show'>('')
  const [filterRating, setFilterRating] = useState<'' | '7' | '8' | '9'>('')
  const [filterDecade, setFilterDecade] = useState<string>('')

  // poster images map: id → { poster, backdrop }
  const [posterMap, setPosterMap] = useState<Record<string, Images>>({})

  const inputRef         = useRef<HTMLInputElement>(null)
  const searchWrapperRef = useRef<HTMLDivElement>(null)
  const scrollSaveRef    = useRef<number>(0)

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  // ── Dark mode ──────────────────────────────────────────────────────────────
  useEffect(() => {
    const saved = localStorage.getItem('vibecheck-dark')
    if (saved !== null) setDark(saved === 'true')
    else setDark(window.matchMedia('(prefers-color-scheme: dark)').matches)
  }, [])

  useEffect(() => {
    localStorage.setItem('vibecheck-dark', String(dark))
    document.documentElement.classList.toggle('dark', dark)
  }, [dark])

  // ── Read query from URL on mount ───────────────────────────────────────────
  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get('q')
    if (q) { setQuery(q); setDebounced(q) }
  }, [])

  // ── Write query to URL ─────────────────────────────────────────────────────
  useEffect(() => {
    const url = query.trim()
      ? `?q=${encodeURIComponent(query.trim())}`
      : window.location.pathname
    window.history.replaceState({}, '', url)
  }, [query])

  // ── Scroll position: save on modal open, restore on close ─────────────────
  useEffect(() => {
    if (selectedMedia) {
      scrollSaveRef.current = window.scrollY
    } else if (scrollSaveRef.current > 0) {
      requestAnimationFrame(() => window.scrollTo(0, scrollSaveRef.current))
    }
  }, [selectedMedia])

  // ── Click outside search wrapper → close suggestions ──────────────────────
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (searchWrapperRef.current && !searchWrapperRef.current.contains(e.target as Node)) {
        setInputFocused(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // ── ⌘K / Escape ───────────────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        inputRef.current?.focus()
        setInputFocused(true)
      }
      if (e.key === 'Escape') { setInputFocused(false); inputRef.current?.blur() }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  // ── Debounce (300 ms) ──────────────────────────────────────────────────────
  useEffect(() => {
    const t = setTimeout(() => setDebounced(query), 300)
    return () => clearTimeout(t)
  }, [query])

  // ── Search ─────────────────────────────────────────────────────────────────
  useEffect(() => {
    const run = async () => {
      if (!debouncedQuery.trim() || debouncedQuery.trim().length < 3) {
        setResults([]); setAllResults([]); setDisplayCount(12); setError(null)
        return
      }
      setLoading(true); setError(null)
      try {
        const apiFilters: Record<string, unknown> = {}
        if (filterType)   apiFilters.media_type = filterType
        if (filterRating) apiFilters.min_rating  = parseFloat(filterRating)
        const decade = DECADES.find(d => d.label === filterDecade)
        if (decade?.min)  apiFilters.min_year = decade.min
        if (decade?.max)  apiFilters.max_year = decade.max

        const res = await apiClient.getRecommendations({
          query: debouncedQuery,
          top_k: 50,
          ...(Object.keys(apiFilters).length > 0 && { filters: apiFilters }),
        })
        const all = res.results as MediaRecommendation[]
        setAllResults(all)
        setResults(all.slice(0, 12))
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unexpected error occurred')
        setResults([]); setAllResults([])
      } finally {
        setLoading(false)
      }
    }
    run()
  }, [debouncedQuery, filterType, filterRating, filterDecade])

  // ── Batch poster fetch when results change ─────────────────────────────────
  useEffect(() => {
    if (!results.length) { setPosterMap({}); return }
    const ids = results.map(r => r.id)
    fetch(`${apiUrl}/media/posters`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ ids }),
    })
      .then(r => r.json())
      .then(data => setPosterMap(prev => ({ ...prev, ...data })))
      .catch(console.error)
  }, [results, apiUrl])

  // ── Handlers ───────────────────────────────────────────────────────────────
  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value)
    setDisplayCount(12)
  }, [])

  const clearQuery = useCallback(() => {
    setQuery('')
    setDisplayCount(12)
    setFilterType('')
    setFilterRating('')
    setFilterDecade('')
  }, [])

  const handleLoadMore = useCallback(() => {
    const n = displayCount + 12
    setDisplayCount(n)
    setResults(allResults.slice(0, n))
  }, [displayCount, allResults])

  const toggleDark = useCallback(() => setDark(d => !d), [])
  const retry      = useCallback(() => setDebounced(q => q + ' '), [])

  const activeFilterCount = [filterType, filterRating, filterDecade].filter(Boolean).length

  // For modal navigation
  const selectedIndex = selectedMedia
    ? results.findIndex(r => r.id === selectedMedia.id)
    : -1

  const handleModalNavigate = useCallback((media: MediaRecommendation) => {
    setSelectedMedia(media)
  }, [])

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className={`min-h-screen transition-colors duration-300 ${dark ? 'bg-gray-900' : 'bg-gray-50'}`}>

      {/* ── Sticky header ── */}
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

        {/* ── Search bar ── */}
        <div className={`${query ? 'pt-8 pb-2' : 'pt-6 pb-2'} max-w-3xl mx-auto`}>
          <div ref={searchWrapperRef} className="relative">
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
              className={`w-full pl-12 pr-16 py-4 border-2 text-base focus:outline-none transition-all ${
                dark
                  ? 'text-white bg-gray-800 border-gray-700 placeholder-gray-500 focus:border-red-500'
                  : 'text-gray-900 bg-white border-gray-200 placeholder-gray-400 focus:border-red-500'
              } ${inputFocused && !query ? 'rounded-t-2xl rounded-b-none border-b-0' : 'rounded-2xl'}`}
            />

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

            {/* Suggestions dropdown */}
            {inputFocused && !query && (
              <div className={`absolute left-0 right-0 top-full z-50 border-2 border-t-0 rounded-b-2xl overflow-hidden shadow-xl ${
                dark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
              }`}>
                <p className={`px-4 pt-3 pb-1 text-xs font-semibold uppercase tracking-widest ${dark ? 'text-gray-500' : 'text-gray-400'}`}>
                  Try asking
                </p>
                {EXAMPLE_QUERIES.map((q, i) => (
                  <button
                    key={q}
                    onMouseDown={e => {
                      e.preventDefault()
                      setQuery(q); setDisplayCount(12); setInputFocused(false)
                    }}
                    className={`w-full flex items-center gap-3 px-4 py-3 text-sm text-left transition-colors ${
                      dark
                        ? 'text-gray-300 hover:bg-gray-700 hover:text-white'
                        : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                    } ${i < EXAMPLE_QUERIES.length - 1
                        ? (dark ? 'border-b border-gray-700/50' : 'border-b border-gray-100')
                        : ''}`}
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

        {/* ── Filter bar (shown when actively searching) ── */}
        {query && (
          <div className={`max-w-3xl mx-auto mb-6 pt-3 pb-1`}>
            <div className="flex items-center gap-2 flex-wrap">
              {/* Type */}
              <FilterPill label="All"     active={filterType === ''}         dark={dark} onClick={() => setFilterType('')} />
              <FilterPill label="Movies"  active={filterType === 'movie'}    dark={dark} onClick={() => setFilterType(t => t === 'movie'    ? '' : 'movie')} />
              <FilterPill label="TV"      active={filterType === 'tv_show'}  dark={dark} onClick={() => setFilterType(t => t === 'tv_show'  ? '' : 'tv_show')} />

              <span className={`w-px h-4 ${dark ? 'bg-gray-700' : 'bg-gray-300'}`} />

              {/* Rating */}
              {(['7', '8', '9'] as const).map(r => (
                <FilterPill key={r} label={`★ ${r}+`} active={filterRating === r} dark={dark}
                  onClick={() => setFilterRating(cur => cur === r ? '' : r)} />
              ))}

              <span className={`w-px h-4 ${dark ? 'bg-gray-700' : 'bg-gray-300'}`} />

              {/* Decade */}
              {DECADES.slice(1).map(d => (
                <FilterPill key={d.label} label={d.label} active={filterDecade === d.label} dark={dark}
                  onClick={() => setFilterDecade(cur => cur === d.label ? '' : d.label)} />
              ))}

              {/* Clear all filters */}
              {activeFilterCount > 0 && (
                <button
                  onClick={() => { setFilterType(''); setFilterRating(''); setFilterDecade('') }}
                  className={`ml-auto text-xs font-medium underline underline-offset-2 ${dark ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600'}`}
                >
                  Clear filters
                </button>
              )}
            </div>
          </div>
        )}

        {/* ── Landing (hero + trending rows + genre + stats) ── */}
        {!query && (
          <div className="pt-2">
            <LandingHero
              dark={dark}
              onSearch={title => { setQuery(title); setDisplayCount(12) }}
            />

            {/* Genre cards */}
            <div className="mt-12 mb-12">
              <p className={`text-xs font-semibold uppercase tracking-widest mb-6 text-center ${dark ? 'text-gray-500' : 'text-gray-400'}`}>
                Browse by genre
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
                {GENRES.map(g => (
                  <button
                    key={g.name}
                    onClick={() => setQuery(g.name.toLowerCase())}
                    className={`group relative aspect-[3/4] rounded-2xl overflow-hidden transition-all duration-300 hover:scale-105 hover:shadow-xl ${
                      dark ? 'bg-gradient-to-br from-gray-800 to-gray-900' : 'bg-gradient-to-br from-gray-100 to-gray-200'
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

            {/* Why VibeCheck — benefit-focused stats */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 max-w-4xl mx-auto pb-16">
              {[
                { icon: '🧠', title: 'Understands your vibe',     desc: 'Describe a mood or emotion — not just a title or genre' },
                { icon: '🎯', title: 'Semantic AI matching',       desc: 'Finds what you mean, even when you can\'t name it' },
                { icon: '🌍', title: 'Cast & streaming info',      desc: 'Know who\'s in it and where to watch before you commit' },
              ].map(s => (
                <div key={s.title} className="text-center">
                  <div className="text-3xl mb-2">{s.icon}</div>
                  <div className={`font-bold mb-1 ${dark ? 'text-white' : 'text-gray-900'}`}>{s.title}</div>
                  <div className={`text-sm ${dark ? 'text-gray-400' : 'text-gray-500'}`}>{s.desc}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Results area ── */}
        {query && (
          <div className="pb-12">

            {/* Skeleton grid */}
            {loading && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {Array.from({ length: 6 }).map((_, i) => (
                  <SkeletonCard key={i} dark={dark} />
                ))}
              </div>
            )}

            {/* Error */}
            {error && !loading && (
              <div className={`max-w-2xl mx-auto rounded-xl p-6 ${
                dark ? 'bg-red-900/20 border border-red-800' : 'bg-red-50 border border-red-200'
              }`}>
                <p className={`font-medium mb-3 ${dark ? 'text-red-400' : 'text-red-700'}`}>{error}</p>
                <button onClick={retry} className="text-sm font-medium text-red-600 hover:text-red-500 underline underline-offset-2">
                  Try again
                </button>
              </div>
            )}

            {/* Results */}
            {!loading && !error && results.length > 0 && (
              <div>
                {/* Header showing query + count */}
                <div className={`mb-5 pb-4 border-b flex items-center gap-2 flex-wrap ${dark ? 'border-gray-700' : 'border-gray-200'}`}>
                  <p className={`text-sm font-semibold uppercase tracking-wide ${dark ? 'text-gray-500' : 'text-gray-500'}`}>
                    <span className={dark ? 'text-white' : 'text-gray-900'}>{allResults.length}</span>
                    {' results for '}
                    <span className={`font-bold ${dark ? 'text-red-400' : 'text-red-600'}`}>
                      &ldquo;{debouncedQuery.trim()}&rdquo;
                    </span>
                  </p>
                  {activeFilterCount > 0 && (
                    <span className={`text-xs px-2 py-0.5 rounded-full ${dark ? 'bg-red-900/40 text-red-400' : 'bg-red-50 text-red-600'}`}>
                      {activeFilterCount} filter{activeFilterCount > 1 ? 's' : ''} active
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {results.map((result, i) => (
                    <div key={result.id} style={{ animationDelay: `${i * 35}ms` }} className="animate-fadeInUp">
                      <MediaCard
                        result={result}
                        dark={dark}
                        images={posterMap[result.id]}
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

            {/* No results */}
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

      {/* ── Media detail modal ── */}
      {selectedMedia && (
        <MediaModal
          media={selectedMedia}
          dark={dark}
          onClose={() => setSelectedMedia(null)}
          results={results}
          currentIndex={selectedIndex}
          onNavigate={handleModalNavigate}
        />
      )}
    </div>
  )
}
