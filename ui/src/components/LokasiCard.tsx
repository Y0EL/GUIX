import { MapPin, Map } from 'lucide-react'
import type { Lokasi } from '../types'
import { highlightMatch } from '../hooks/useSearch'

type Props = {
  lokasi: Lokasi
  query: string
  onPetaClick?: (l: Lokasi) => void
}

export default function LokasiCard({ lokasi: l, query, onPetaClick }: Props) {

  function hl(text: string) {
    return <span dangerouslySetInnerHTML={{ __html: highlightMatch(text, query) }} />
  }

  return (
    <div
      className="sd-card sd-lokasi-card"
      onClick={() => onPetaClick?.(l)}
    >
      <div className="sd-card-type-icon lokasi">
        <MapPin size={14} />
      </div>
      <div className="sd-lokasi-info">
        <div className="sd-lokasi-label">{hl(l.label)}</div>
        <div className="sd-lokasi-meta">
          <span>{l.kota}, {l.provinsi}</span>
          <span className="sd-sep">·</span>
          <span className="sd-lokasi-tipe">{l.tipe_lokasi.replace(/_/g, ' ')}</span>
          <span className="sd-sep">·</span>
          <span className="sd-lokasi-koordinat">{l.latitude.toFixed(4)}, {l.longitude.toFixed(4)}</span>
        </div>
      </div>
      <div className="sd-card-action">
        <button className="sd-drill-btn primary" onClick={e => { e.stopPropagation(); onPetaClick?.(l) }}>
          <Map size={11} />
          Lihat Peta
        </button>
      </div>
    </div>
  )
}
