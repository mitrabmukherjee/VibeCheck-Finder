'use client'

import { useState, useEffect, useRef } from 'react'

interface TmdbItem {
  tmdb_id: number
  title: string
  overview: string
  backdrop: string | null
  poster: string | null
  rating: number
  year: string
  media_type: 'movie' | 'tv'
}

interface LandingData {
  hero: TmdbItem[]
  trending_movies: TmdbItem[]
  trending_tv: TmdbItem[]
  upcoming: TmdbItem[]
}

interface Props {
  dark: boolean
  onSearch: (title: string) => void
}

// ---------------------------------------------------------------------------
// Poster card used inside each horizontal row
// ---------------------------------------------------------------------------
function PosterCard({ item, dark, onSearch }: { item: TmdbItem; dark: boolean; onSearch: (t: string) => void }) {
  return (
    <button
      onClick={() => onSearch(item.title)}
      className="flex-shrink-0 w-28 sm:w-32 md:w-36 group relative rounded-xl overflow-hidden
                 ring-2 ring-transparent hover:ring-red-500 transition-all duration-200 hover:scale-105"
    >
      <div className={`aspect-[2/3] ${dark ? 'bg-gray-800' : 'bg-gray-200'}`}>
        {item.poster ? (
          <img
            src={item.poster}
            alt={item.title}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <span className="text-4xl">{item.media_type === 'tv' ? '📺' : '🎬'}</span>
          </div>
        )}
      </div>
      {/* Hover overlay */}
      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/65 transition-all duration-200
                      flex flex-col justify-end p-2">
        <p className="text-white text-xs font-semibold opacity-0 group-hover:opacity-100
                      transition-opacity duration-150 leading-snug line-clamp-2">
          {item.title}
        </p>
        {item.rating > 0 && (
          <p className="text-yellow-400 text-xs opacity-0 group-hover:opacity-100 transition-opacity duration-150 mt-0.5">
            ⭐ {item.rating.toFixed(1)}
          </p>
        )}
      </div>
    </button>
  )
}

// ---------------------------------------------------------------------------
// Horizontal scroll row
// ---------------------------------------------------------------------------
function TrendingRow({ title, items, dark, onSearch }: {
  title: string
  items: TmdbItem[]
  dark: boolean
  onSearch: (t: string) => void
}) {
  const rowRef = useRef<HTMLDivElement>(null)

  const scroll = (dir: 'left' | 'right') => {
    if (!rowRef.current) return
    rowRef.current.scrollBy({ left: dir === 'right' ? 320 : -320, behavior: 'smooth' })
  }

  if (!items.length) return null

  return (
    <div className="mb-10">
      <div className="flex items-center justify-between mb-3">
        <h3 className={`text-base font-bold ${dark ? 'text-white' : 'text-gray-900'}`}>{title}</h3>
        <span className={`text-xs sm:hidden ${dark ? 'text-gray-600' : 'text-gray-400'}`}>swipe →</span>
      </div>
      <div className="relative group/row">
        {/* Left arrow */}
        <button
          onClick={() => scroll('left')}
          className={`absolute left-0 top-1/2 -translate-y-1/2 z-10 w-8 h-12 flex items-center justify-center
                      rounded-r-lg opacity-0 group-hover/row:opacity-100 transition-opacity
                      ${dark ? 'bg-gray-900/90 text-white' : 'bg-white/90 text-gray-800'} shadow-lg`}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        <div ref={rowRef} className="flex gap-2.5 overflow-x-auto scrollbar-hide pb-1 px-0.5">
          {items.map(item => (
            <PosterCard key={item.tmdb_id} item={item} dark={dark} onSearch={onSearch} />
          ))}
        </div>

        {/* Right arrow */}
        <button
          onClick={() => scroll('right')}
          className={`absolute right-0 top-1/2 -translate-y-1/2 z-10 w-8 h-12 flex items-center justify-center
                      rounded-l-lg opacity-0 group-hover/row:opacity-100 transition-opacity
                      ${dark ? 'bg-gray-900/90 text-white' : 'bg-white/90 text-gray-800'} shadow-lg`}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Skeleton rows shown while fetching
// ---------------------------------------------------------------------------
function SkeletonRows({ dark }: { dark: boolean }) {
  const base = dark ? 'bg-gray-800' : 'bg-gray-200'
  return (
    <div className="space-y-10">
      {['Trending Movies', 'Trending TV Shows', 'Coming Soon'].map(label => (
        <div key={label}>
          <div className={`h-4 w-36 rounded mb-3 animate-pulse ${base}`} />
          <div className="flex gap-2.5">
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={i}
                className={`flex-shrink-0 w-28 sm:w-32 md:w-36 aspect-[2/3] rounded-xl animate-pulse ${base}`}
                style={{ animationDelay: `${i * 60}ms` }}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main export
// ---------------------------------------------------------------------------
export default function LandingHero({ dark, onSearch }: Props) {
  const [data, setData]           = useState<LandingData | null>(null)
  const [heroIdx, setHeroIdx]     = useState(0)
  const [imgLoaded, setImgLoaded] = useState(false)

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => {
    fetch(`${apiUrl}/landing`)
      .then(r => r.json())
      .then((d: LandingData) => { setData(d); setImgLoaded(false) })
      .catch(console.error)
  }, [apiUrl])

  // Auto-rotate hero every 7 s
  useEffect(() => {
    if (!data?.hero?.length) return
    const id = setInterval(() => {
      setHeroIdx(i => (i + 1) % data.hero.length)
      setImgLoaded(false)
    }, 7000)
    return () => clearInterval(id)
  }, [data?.hero?.length])

  const hero = data?.hero?.[heroIdx] ?? null

  return (
    <div>
      {/* ── Hero ── */}
      <div className="relative w-full h-[58vh] sm:h-[68vh] overflow-hidden rounded-2xl mb-10">

        {/* Background image */}
        {hero?.backdrop ? (
          <img
            key={hero.backdrop}
            src={hero.backdrop}
            alt={hero.title}
            onLoad={() => setImgLoaded(true)}
            className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-700 ${
              imgLoaded ? 'opacity-100' : 'opacity-0'
            }`}
          />
        ) : (
          <div className={`absolute inset-0 animate-pulse ${dark ? 'bg-gray-800' : 'bg-gray-300'}`} />
        )}

        {/* Gradient overlays */}
        <div className="absolute inset-0 bg-gradient-to-r from-black/85 via-black/40 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/20" />

        {/* Content */}
        <div className="absolute inset-0 flex flex-col justify-end p-6 sm:p-10 pb-10 sm:pb-14">
          {hero ? (
            <div className="max-w-lg">
              <div className="flex items-center gap-2 mb-2 flex-wrap">
                <span className="text-xs font-bold uppercase tracking-widest text-red-400 bg-red-500/10 px-2 py-0.5 rounded">
                  {hero.media_type === 'tv' ? 'TV Show' : 'Movie'}
                </span>
                {hero.year && (
                  <span className="text-gray-300 text-xs">{hero.year}</span>
                )}
                {hero.rating > 0 && (
                  <span className="text-yellow-400 text-xs font-medium">⭐ {hero.rating.toFixed(1)}</span>
                )}
              </div>

              <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-3 leading-tight
                             [text-shadow:0_2px_12px_rgba(0,0,0,0.6)]">
                {hero.title}
              </h2>

              {hero.overview && (
                <p className="text-gray-200 text-sm sm:text-base leading-relaxed mb-5 max-w-md
                               line-clamp-2 [text-shadow:0_1px_6px_rgba(0,0,0,0.8)]">
                  {hero.overview}
                </p>
              )}

              <button
                onClick={() => onSearch(hero.title)}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-white text-gray-900
                           font-semibold text-sm rounded-xl hover:bg-gray-100 active:scale-95
                           transition-all duration-150 shadow-lg"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                Search this vibe
              </button>
            </div>
          ) : (
            /* Skeleton content */
            <div className="max-w-lg space-y-3 animate-pulse">
              <div className="h-3 w-16 bg-gray-600 rounded" />
              <div className="h-9 w-72 bg-gray-600 rounded" />
              <div className="h-4 w-96 bg-gray-700 rounded" />
              <div className="h-4 w-64 bg-gray-700 rounded" />
              <div className="h-9 w-36 bg-gray-600 rounded-xl" />
            </div>
          )}
        </div>

        {/* Navigation dots */}
        {data?.hero && data.hero.length > 1 && (
          <div className="absolute bottom-4 right-6 flex items-center gap-1.5">
            {data.hero.map((_, i) => (
              <button
                key={i}
                onClick={() => { setHeroIdx(i); setImgLoaded(false) }}
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  i === heroIdx
                    ? 'w-6 bg-white'
                    : 'w-1.5 bg-white/40 hover:bg-white/70'
                }`}
                aria-label={`Hero slide ${i + 1}`}
              />
            ))}
          </div>
        )}
      </div>

      {/* ── Trending rows ── */}
      {data ? (
        <>
          <TrendingRow
            title="🔥 Trending Movies"
            items={data.trending_movies}
            dark={dark}
            onSearch={onSearch}
          />
          <TrendingRow
            title="📺 Trending TV Shows"
            items={data.trending_tv}
            dark={dark}
            onSearch={onSearch}
          />
          <TrendingRow
            title="🎟️ Coming Soon"
            items={data.upcoming}
            dark={dark}
            onSearch={onSearch}
          />
        </>
      ) : (
        <SkeletonRows dark={dark} />
      )}
    </div>
  )
}
