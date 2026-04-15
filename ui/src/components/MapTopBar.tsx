import { ChevronLeft, MapPin, Layers, Tag, RotateCcw } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { Wilayah } from '../types'

type Props = {
  wilayah: Wilayah[]
  totalTitik: number
  labelEnabled: boolean
  clusterEnabled: boolean
  onToggleLabel: () => void
  onToggleCluster: () => void
  onResetView: () => void
}

export default function MapTopBar({
  wilayah,
  totalTitik,
  labelEnabled,
  clusterEnabled,
  onToggleLabel,
  onToggleCluster,
  onResetView,
}: Props) {
  const nav = useNavigate()

  const totalKasus = wilayah.reduce((s, w) => s + w.total_kasus, 0)
  const wilayahKritis = wilayah.filter(w => w.severity_tertinggi === 'tinggi').length

  return (
    <div className="mi-topbar">
      {/* Kiri: breadcrumb */}
      <div className="mi-breadcrumb">
        <button className="mi-back-btn" onClick={() => nav('/incident-queue')}>
          <ChevronLeft size={13} />
          Incident Queue
        </button>
        <span className="mi-breadcrumb-sep">/</span>
        <span className="mi-breadcrumb-current">Map Intelligence</span>
      </div>

      {/* Tengah: pill stats */}
      <div className="mi-stat-pills">
        <div className="mi-stat-pill">
          <span className="mi-stat-dot" style={{ background: 'rgba(243,234,234,.4)' }} />
          {totalTitik} Titik Aktif
        </div>
        <div className="mi-stat-pill">
          <span className="mi-stat-dot" style={{ background: '#818CF8' }} />
          {totalKasus} Kasus
        </div>
        {wilayahKritis > 0 && (
          <div className="mi-stat-pill kritis">
            <span className="mi-stat-dot" style={{ background: '#E5282A' }} />
            {wilayahKritis} Wilayah Kritis
          </div>
        )}
      </div>

      {/* Kanan: toggle buttons */}
      <div className="mi-toggle-group">
        <button
          className={`mi-toggle-btn ${clusterEnabled ? 'aktif' : ''}`}
          onClick={onToggleCluster}
          title="Toggle cluster"
        >
          <Layers size={13} />
        </button>
        <button
          className={`mi-toggle-btn ${labelEnabled ? 'aktif' : ''}`}
          onClick={onToggleLabel}
          title="Toggle label"
        >
          <Tag size={12} />
        </button>
        <button
          className="mi-toggle-btn"
          onClick={onResetView}
          title="Reset ke Indonesia"
        >
          <RotateCcw size={12} />
        </button>
        <button
          className="mi-toggle-btn"
          onClick={() => nav('/')}
          title="Kembali ke Overview"
        >
          <MapPin size={12} />
        </button>
      </div>
    </div>
  )
}
