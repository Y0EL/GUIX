import { useState, type ReactNode } from 'react'
import { ChevronDown, ChevronRight, Clock, X, Search } from 'lucide-react'
import type { SearchResult } from '../types'
import type { FilterTipe } from '../hooks/useSearch'
import ProfilCard from './ProfilCard'
import KasusCard from './KasusCard'
import LokasiCard from './LokasiCard'
import PostinganCard from './PostinganCard'
import type { Profil, Kasus, Lokasi, Postingan } from '../types'

type Props = {
  results: SearchResult[]
  query: string
  activeFilter: FilterTipe
  recentSearches: string[]
  onRecentClick: (q: string) => void
  onRemoveRecent: (q: string) => void
  koneksiPerProfil?: Map<string, number>
  kasusMap?: Record<string, string>
  onLokasiClick?: (l: Lokasi) => void
  initialContent?: ReactNode
}

const SECTION_ORDER: Array<{ tipe: Exclude<FilterTipe, 'all'>; label: string }> = [
  { tipe: 'profil',    label: 'Profil' },
  { tipe: 'kasus',     label: 'Kasus' },
  { tipe: 'lokasi',    label: 'Lokasi' },
  { tipe: 'postingan', label: 'Postingan' },
]

export default function SearchResultsPanel({
  results, query, activeFilter, recentSearches, onRecentClick, onRemoveRecent,
  koneksiPerProfil, kasusMap, onLokasiClick, initialContent,
}: Props) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})

  function toggleCollapse(tipe: string) {
    setCollapsed(prev => ({ ...prev, [tipe]: !prev[tipe] }))
  }

  /* ── Initial state — belum ada query ── */
  if (query.trim().length < 2) {
    return (
      <div className="sd-results-panel">
        {initialContent}
        {recentSearches.length > 0 && (
          <div className="sd-initial-section">
            <div className="sd-section-title">Pencarian Terakhir</div>
            {recentSearches.map(q => (
              <div key={q} className="sd-recent-row">
                <Clock size={12} className="sd-recent-icon" />
                <span className="sd-recent-query" onClick={() => onRecentClick(q)}>{q}</span>
                <button className="sd-recent-remove" onClick={() => onRemoveRecent(q)}>
                  <X size={11} />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="sd-initial-hint">
          <Search size={32} style={{ color: '#333', marginBottom: 12 }} />
          <div className="sd-hint-title">Cari lintas dataset</div>
          <div className="sd-hint-rows">
            <div className="sd-hint-row"><span className="sd-hint-chip profil">Profil</span> nama, kota, bio, tag risiko</div>
            <div className="sd-hint-row"><span className="sd-hint-chip kasus">Kasus</span> id, judul, tipe, status</div>
            <div className="sd-hint-row"><span className="sd-hint-chip lokasi">Lokasi</span> label, kota, tipe lokasi</div>
            <div className="sd-hint-row"><span className="sd-hint-chip post">Postingan</span> konten, platform, hashtag</div>
          </div>
        </div>
      </div>
    )
  }

  /* ── Empty state ── */
  if (results.length === 0) {
    return (
      <div className="sd-results-panel">
        <div className="sd-empty-state">
          <Search size={36} style={{ color: '#333' }} />
          <div className="sd-empty-title">Tidak ada hasil untuk "{query}"</div>
          <div className="sd-empty-hint">
            Coba nama kota, id kasus, kata kunci lebih singkat, atau cek ejaan
          </div>
        </div>
      </div>
    )
  }

  /* ── Results ── */
  const sectionsToShow = activeFilter === 'all'
    ? SECTION_ORDER
    : SECTION_ORDER.filter(s => s.tipe === activeFilter)

  return (
    <div className="sd-results-panel">
      {sectionsToShow.map(({ tipe, label }) => {
        const items = results.filter(r => r.tipe === tipe)
        if (items.length === 0) return null
        const isCollapsed = collapsed[tipe]

        return (
          <div key={tipe} className="sd-section">
            <button className="sd-section-header" onClick={() => toggleCollapse(tipe)}>
              <span className="sd-section-label">{label}</span>
              <span className="sd-section-count">{items.length}</span>
              <span className="sd-section-toggle">
                {isCollapsed ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
              </span>
            </button>

            {!isCollapsed && (
              <div className={`sd-section-body ${tipe === 'profil' ? 'grid' : 'list'}`}>
                {items.map(r => {
                  if (r.tipe === 'profil')
                    return <ProfilCard key={r.id} profil={r.data as Profil} query={query} matchedFields={r.matchedFields} koneksiCount={koneksiPerProfil?.get((r.data as Profil).id_profil) ?? 0} kasusMap={kasusMap} />
                  if (r.tipe === 'kasus')
                    return <KasusCard key={r.id} kasus={r.data as Kasus} query={query} />
                  if (r.tipe === 'lokasi')
                    return <LokasiCard key={r.id} lokasi={r.data as Lokasi} query={query} onPetaClick={onLokasiClick} />
                  if (r.tipe === 'postingan')
                    return <PostinganCard key={r.id} postingan={r.data as Postingan} query={query} />
                  return null
                })}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
