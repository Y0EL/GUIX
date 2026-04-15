import { ArrowLeft, SlidersHorizontal } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { FilterTipe } from '../hooks/useSearch'

type Props = {
  query: string
  counts: Record<FilterTipe, number>
}

export default function SearchTopBar({ query, counts }: Props) {
  const nav = useNavigate()
  const total = counts.all

  return (
    <div className="sd-topbar">
      <div className="sd-breadcrumb">
        <button className="sd-back-btn" onClick={() => nav('/map-intelligence')}>
          <ArrowLeft size={12} />
          Map Intelligence
        </button>
        <span className="sd-breadcrumb-sep">/</span>
        <span className="sd-breadcrumb-current">Search & Discovery</span>
      </div>

      <div className="sd-topbar-summary">
        {query.trim().length >= 2 && total > 0 && (
          <>
            <SlidersHorizontal size={12} style={{ color: '#555' }} />
            <span>{total} hasil</span>
            {counts.profil > 0 && <span className="sd-summary-chip">{counts.profil} profil</span>}
            {counts.kasus > 0 && <span className="sd-summary-chip">{counts.kasus} kasus</span>}
            {counts.lokasi > 0 && <span className="sd-summary-chip">{counts.lokasi} lokasi</span>}
            {counts.postingan > 0 && <span className="sd-summary-chip">{counts.postingan} postingan</span>}
          </>
        )}
        {query.trim().length >= 2 && total === 0 && (
          <span className="sd-summary-empty">Tidak ada hasil untuk "{query}"</span>
        )}
      </div>
    </div>
  )
}
