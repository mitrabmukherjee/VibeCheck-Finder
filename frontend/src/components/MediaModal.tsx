'use client'

import { useEffect, useRef, useState } from 'react'
import { MediaRecommendation } from '@/types'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface CastMember {
  name: string
  character: string
  photo: string | null
}

interface Provider {
  name: string
  logo: string | null
}

interface Providers {
  flatrate: Provider[]
  rent:     Provider[]
  buy:      Provider[]
  link:     string | null
}

interface TMDBDetails {
  tmdb_id:   number | null
  cast:      CastMember[]
  providers: Providers
  trailer:   string | null
}

interface Props {
  media:   MediaRecommendation
  dark:    boolean
  onClose: () => void
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// ---------------------------------------------------------------------------
// Helper: avatar placeholder when TMDB has no photo
// ---------------------------------------------------------------------------
function AvatarPlaceholder({ name, dark }: { name: string; dark: boolean }) {
  const initials = name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()
  return (
    <div className={`w-16 h-16 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0 ${
      dark ? 'bg-gray-600 text-gray-300' : 'bg-gray-200 text-gray-600'
    }`}>
      {initials}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Score badge (reused from page.tsx logic)
// ---------------------------------------------------------------------------
function rescaleScore(raw: number): number {
  const c = Math.max(0, Math.min(1, raw))
  if (c >= 0.4) return Math.round(70 + Math.min((c - 0.4) / 0.3, 1) * 30)
  if (c >= 0.3) return Math.round(60 + ((c - 0.3) / 0.1) * 10)
  return Math.round((c / 0.3) * 60)
}

// ---------------------------------------------------------------------------
// Main modal component
// ---------------------------------------------------------------------------
export default function MediaModal({ media, dark, onClose }: Props) {
  const [details, setDetails]   = useState<TMDBDetails | null>(null)
  const [loading, setLoading]   = useState(true)
  const [fetchErr, setFetchErr] = useState(false)
  const backdropRef             = useRef<HTMLDivElement>(null)

  // Fetch TMDB details on mount
  useEffect(() => {
    let cancelled = false
    const run = async () => {
      setLoading(true)
      setFetchErr(false)
      try {
        const res = await fetch(`${API_BASE}/media/${media.id}/details`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data: TMDBDetails = await res.json()
        if (!cancelled) setDetails(data)
      } catch {
        if (!cancelled) setFetchErr(true)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    run()
    return () => { cancelled = true }
  }, [media.id])

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  // Prevent body scroll while modal is open
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  const score = rescaleScore(media.similarity_score)
  const scoreCls =
    score >= 80 ? 'bg-green-500 text-white' :
    score >= 65 ? 'bg-yellow-500 text-white' :
                  'bg-gray-500 text-white'

  const d = dark

  return (
    /* Backdrop */
    <div
      ref={backdropRef}
      onClick={e => { if (e.target === backdropRef.current) onClose() }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeInUp"
      style={{ animationDuration: '0.2s' }}
    >
      {/* Panel */}
      <div className={`relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl shadow-2xl ${
        d ? 'bg-gray-900 text-white' : 'bg-white text-gray-900'
      }`}>

        {/* Watch Trailer — fixed to bottom-right of card */}
        {!loading && !fetchErr && details?.trailer && (
          <a
            href={details.trailer}
            target="_blank"
            rel="noopener noreferrer"
            className="absolute bottom-5 right-5 z-10 inline-flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 text-white text-sm font-semibold rounded-xl shadow-lg transition-colors"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
            </svg>
            Watch Trailer
          </a>
        )}

        {/* Close button */}
        <button
          onClick={onClose}
          className={`absolute top-4 right-4 z-10 w-8 h-8 rounded-full flex items-center justify-center transition-colors ${
            d ? 'bg-gray-700 hover:bg-gray-600 text-gray-300' : 'bg-gray-100 hover:bg-gray-200 text-gray-600'
          }`}
          aria-label="Close"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <div className="p-6 sm:p-8">
          {/* Header */}
          <div className="flex items-start gap-4 mb-6 pr-8">
            <div className="w-14 h-14 bg-red-500 rounded-xl flex items-center justify-center flex-shrink-0">
              <span className="text-2xl">{media.media_type === 'tv_show' ? '📺' : '🎬'}</span>
            </div>
            <div className="flex-1 min-w-0">
              <h2 className={`text-2xl font-bold leading-tight mb-1 ${d ? 'text-white' : 'text-gray-900'}`}>
                {media.title}
              </h2>
              <div className="flex flex-wrap items-center gap-2 text-sm">
                {media.metadata.year && (
                  <span className={d ? 'text-gray-400' : 'text-gray-500'}>{media.metadata.year}</span>
                )}
                {media.metadata.year && media.metadata.genre && (
                  <span className={d ? 'text-gray-600' : 'text-gray-300'}>·</span>
                )}
                {media.metadata.genre && (
                  <span className={`px-2 py-0.5 rounded-md text-xs font-medium ${
                    d ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600'
                  }`}>{media.metadata.genre}</span>
                )}
                {media.metadata.rating && (
                  <span className={`flex items-center gap-1 ${d ? 'text-gray-400' : 'text-gray-500'}`}>
                    <svg className="w-3.5 h-3.5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                    {media.metadata.rating.toFixed(1)}
                  </span>
                )}
                <span className={`text-xs font-bold px-2.5 py-1 rounded-md ${scoreCls}`}>
                  {score}% Match
                </span>
              </div>
            </div>
          </div>

          {/* Description */}
          <div className="mb-6">
            <h3 className={`text-xs font-semibold uppercase tracking-widest mb-2 ${d ? 'text-gray-500' : 'text-gray-400'}`}>
              Synopsis
            </h3>
            <p className={`text-sm leading-relaxed ${d ? 'text-gray-300' : 'text-gray-600'}`}>
              {media.description}
            </p>
          </div>

          {/* TMDB enriched content */}
          {loading && (
            <div className="space-y-6">
              {/* Cast skeleton */}
              <div>
                <div className={`h-3 w-16 rounded mb-3 animate-pulse ${d ? 'bg-gray-700' : 'bg-gray-200'}`} />
                <div className="flex gap-4 overflow-hidden">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="flex flex-col items-center gap-2 flex-shrink-0">
                      <div className={`w-16 h-16 rounded-full animate-pulse ${d ? 'bg-gray-700' : 'bg-gray-200'}`} />
                      <div className={`h-2.5 w-14 rounded animate-pulse ${d ? 'bg-gray-700' : 'bg-gray-200'}`} />
                      <div className={`h-2 w-12 rounded animate-pulse ${d ? 'bg-gray-700' : 'bg-gray-200'}`} />
                    </div>
                  ))}
                </div>
              </div>
              {/* Providers skeleton */}
              <div>
                <div className={`h-3 w-24 rounded mb-3 animate-pulse ${d ? 'bg-gray-700' : 'bg-gray-200'}`} />
                <div className="flex gap-3">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <div key={i} className={`w-12 h-12 rounded-xl animate-pulse ${d ? 'bg-gray-700' : 'bg-gray-200'}`} />
                  ))}
                </div>
              </div>
            </div>
          )}

          {fetchErr && !loading && (
            <p className={`text-sm ${d ? 'text-gray-500' : 'text-gray-400'}`}>
              Could not load additional details right now.
            </p>
          )}

          {!loading && !fetchErr && details && (
            <div className="space-y-6">

              {/* Cast */}
              {details.cast.length > 0 && (
                <div>
                  <h3 className={`text-xs font-semibold uppercase tracking-widest mb-3 ${d ? 'text-gray-500' : 'text-gray-400'}`}>
                    Cast
                  </h3>
                  <div className="flex gap-4 overflow-x-auto pb-2 scrollbar-hide">
                    {details.cast.map((member, i) => (
                      <div key={i} className="flex flex-col items-center gap-1.5 flex-shrink-0 w-16">
                        {member.photo ? (
                          <img
                            src={member.photo}
                            alt={member.name}
                            className="w-16 h-16 rounded-full object-cover"
                            loading="lazy"
                          />
                        ) : (
                          <AvatarPlaceholder name={member.name} dark={d} />
                        )}
                        <span className={`text-xs text-center font-medium leading-tight line-clamp-2 ${
                          d ? 'text-gray-300' : 'text-gray-700'
                        }`}>{member.name}</span>
                        {member.character && (
                          <span className={`text-xs text-center leading-tight line-clamp-1 ${
                            d ? 'text-gray-500' : 'text-gray-400'
                          }`}>{member.character}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Streaming providers */}
              {details.providers.flatrate.length > 0 && (
                <div>
                  <h3 className={`text-xs font-semibold uppercase tracking-widest mb-3 ${d ? 'text-gray-500' : 'text-gray-400'}`}>
                    Stream On
                  </h3>
                  <div className="flex flex-wrap gap-3">
                    {details.providers.flatrate.map((p, i) => (
                      <div key={i} className="flex items-center gap-2" title={p.name}>
                        {p.logo ? (
                          <img
                            src={p.logo}
                            alt={p.name}
                            className="w-10 h-10 rounded-xl object-cover"
                            loading="lazy"
                          />
                        ) : (
                          <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-xs font-bold ${
                            d ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600'
                          }`}>
                            {p.name.slice(0, 2).toUpperCase()}
                          </div>
                        )}
                        <span className={`text-xs font-medium ${d ? 'text-gray-300' : 'text-gray-600'}`}>
                          {p.name}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Rent / Buy if no flatrate */}
              {details.providers.flatrate.length === 0 &&
               (details.providers.rent.length > 0 || details.providers.buy.length > 0) && (
                <div>
                  <h3 className={`text-xs font-semibold uppercase tracking-widest mb-3 ${d ? 'text-gray-500' : 'text-gray-400'}`}>
                    Rent / Buy
                  </h3>
                  <div className="flex flex-wrap gap-3">
                    {[...details.providers.rent, ...details.providers.buy].map((p, i) => (
                      <div key={i} className="flex items-center gap-2" title={p.name}>
                        {p.logo ? (
                          <img src={p.logo} alt={p.name} className="w-10 h-10 rounded-xl object-cover" loading="lazy" />
                        ) : (
                          <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-xs font-bold ${
                            d ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600'
                          }`}>
                            {p.name.slice(0, 2).toUpperCase()}
                          </div>
                        )}
                        <span className={`text-xs font-medium ${d ? 'text-gray-300' : 'text-gray-600'}`}>{p.name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* No providers found */}
              {details.providers.flatrate.length === 0 &&
               details.providers.rent.length === 0 &&
               details.providers.buy.length === 0 && (
                <p className={`text-sm ${d ? 'text-gray-500' : 'text-gray-400'}`}>
                  No streaming info available for your region.
                </p>
              )}

              {/* JustWatch link */}
              {details.providers.link && (
                <a
                  href={details.providers.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`inline-flex items-center gap-1.5 text-xs font-medium underline underline-offset-2 ${
                    d ? 'text-gray-400 hover:text-gray-200' : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  More options on JustWatch ↗
                </a>
              )}

              {/* Spacer so content doesn't hide behind the pinned trailer button */}
              {details.trailer && <div className="h-12" />}

            </div>
          )}
        </div>
      </div>
    </div>
  )
}
