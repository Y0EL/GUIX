import { Clock, SortAsc } from 'lucide-react'
import type { FilterTipe, SortMode } from '../hooks/useSearch'

const TABS: { key: FilterTipe; label: string }[] = [
  { key: 'all',       label: 'Semua' },
  { key: 'profil',    label: 'Profil' },
  { key: 'kasus',     label: 'Kasus' },
  { key: 'lokasi',    label: 'Lokasi' },
  { key: 'postingan', label: 'Postingan' },
]

type Props = {
  activeFilter: FilterTipe
  sortMode: SortMode
  counts: Record<FilterTipe, number>
  hasQuery: boolean
  onFilter: (f: FilterTipe) => void
  onSort: (s: SortMode) => void
}

export default function SearchFilterBar({
  activeFilter, sortMode, counts, hasQuery, onFilter, onSort,
}: Props) {
  return (
    <div className="sd-filterbar">
      <div className="sd-filter-tabs">
        {TABS.map(t => {
          const count = counts[t.key]
          const aktif = activeFilter === t.key
          return (
            <button
              key={t.key}
              className={`sd-filter-tab ${aktif ? 'aktif' : ''}`}
              onClick={() => onFilter(t.key)}
            >
              {t.label}
              {hasQuery && count > 0 && (
                <span className={`sd-filter-count ${aktif ? 'aktif' : ''}`}>
                  {count}
                </span>
              )}
            </button>
          )
        })}
      </div>

      <div className="sd-sort-group">
        <button
          className={`sd-sort-btn ${sortMode === 'relevansi' ? 'aktif' : ''}`}
          onClick={() => onSort('relevansi')}
        >
          <SortAsc size={12} />
          Relevansi
        </button>
        <button
          className={`sd-sort-btn ${sortMode === 'terbaru' ? 'aktif' : ''}`}
          onClick={() => onSort('terbaru')}
        >
          <Clock size={12} />
          Terbaru
        </button>
      </div>
    </div>
  )
}
