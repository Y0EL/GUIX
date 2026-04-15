import { SquareActivity, ExternalLink } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { Kasus } from '../types'
import { highlightMatch } from '../hooks/useSearch'
import { formatTanggal } from '../utils'

type Props = {
  kasus: Kasus
  query: string
}

const STATUS_STYLE: Record<string, { bg: string; color: string; label: string }> = {
  monitoring: { bg: 'rgba(229,40,42,.15)', color: '#ff8a8a', label: 'Monitoring' },
  analisis:   { bg: 'rgba(245,166,35,.15)', color: '#fbbf24', label: 'Analisis' },
  eskalasi:   { bg: 'rgba(229,40,42,.25)', color: '#E5282A', label: 'Eskalasi' },
  selesai:    { bg: 'rgba(74,222,128,.15)', color: '#4ade80', label: 'Selesai' },
}

export default function KasusCard({ kasus: k, query }: Props) {
  const nav = useNavigate()
  const status = STATUS_STYLE[k.status] ?? STATUS_STYLE.monitoring

  function hl(text: string) {
    return <span dangerouslySetInnerHTML={{ __html: highlightMatch(text, query) }} />
  }

  return (
    <div className="sd-card sd-kasus-card" onClick={() => nav('/incident-queue', { state: { focusKasus: k.id_kasus } })}>
      <div className="sd-card-type-icon kasus">
        <SquareActivity size={14} />
      </div>
      <div className="sd-kasus-info">
        <div className="sd-kasus-header">
          <span className="sd-kasus-id">{hl(k.id_kasus)}</span>
          <span
            className="sd-kasus-status"
            style={{ background: status.bg, color: status.color }}
          >
            {status.label}
          </span>
        </div>
        <div className="sd-kasus-judul">{hl(k.judul)}</div>
        <div className="sd-kasus-meta">
          <span>{k.tipe_kasus.replace(/_/g, ' ')}</span>
          <span className="sd-sep">·</span>
          <span>{k.kota}</span>
          <span className="sd-sep">·</span>
          <span>{formatTanggal(k.waktu_insiden)}</span>
          <span className="sd-sep">·</span>
          <span>{k.jumlah_aktor} aktor</span>
        </div>
      </div>
      <div className="sd-card-action">
        <button className="sd-drill-btn primary">
          <ExternalLink size={11} />
          Buka Antrian
        </button>
      </div>
    </div>
  )
}
