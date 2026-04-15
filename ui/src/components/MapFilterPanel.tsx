import { MapPin } from 'lucide-react'
import type { Wilayah } from '../types'

type Props = {
  filterSeverity: string[]
  filterTipeLokasi: string[]
  tipeLokasi: string[]
  wilayah: Wilayah[]
  selectedWilayah: string | null
  onToggleSeverity: (s: string) => void
  onToggleTipe: (t: string) => void
  onSelectWilayah: (id: string) => void
}

const SEVERITIES = [
  { key: 'tinggi',   label: 'Kritis',  color: '#E5282A' },
  { key: 'menengah', label: 'Tinggi',  color: '#F5A623' },
  { key: 'rendah',   label: 'Rendah',  color: '#4CAF50' },
]

const SEV_COLOR: Record<string, string> = {
  tinggi: '#E5282A',
  menengah: '#F5A623',
  rendah: '#4CAF50',
}

export default function MapFilterPanel({
  filterSeverity,
  filterTipeLokasi,
  tipeLokasi,
  wilayah,
  selectedWilayah,
  onToggleSeverity,
  onToggleTipe,
  onSelectWilayah,
}: Props) {
  return (
    <div className="mi-filter-panel">

      {/* Section: Severity */}
      <div className="mi-section">
        <div className="mi-section-title">Severity</div>
        {SEVERITIES.map(s => {
          const aktif = filterSeverity.length === 0 || filterSeverity.includes(s.key)
          return (
            <label key={s.key} className={`mi-sev-row ${filterSeverity.includes(s.key) ? 'selected' : ''}`}>
              <input
                type="checkbox"
                className="mi-checkbox"
                checked={aktif}
                onChange={() => onToggleSeverity(s.key)}
              />
              <span className="mi-sev-dot" style={{ background: s.color }} />
              <span className="mi-sev-label">{s.label}</span>
              <span className="mi-sev-count">
                {wilayah.filter(w => w.severity_tertinggi === s.key).length}
              </span>
            </label>
          )
        })}
      </div>

      {/* Section: Tipe Lokasi */}
      {tipeLokasi.length > 0 && (
        <div className="mi-section">
          <div className="mi-section-title">Tipe Lokasi</div>
          <div className="mi-tipe-pills">
            {tipeLokasi.map(t => (
              <button
                key={t}
                className={`mi-tipe-pill ${filterTipeLokasi.includes(t) ? 'aktif' : ''}`}
                onClick={() => onToggleTipe(t)}
              >
                {t.replace(/_/g, ' ')}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Section: Wilayah ranking */}
      <div className="mi-section mi-section-grow">
        <div className="mi-section-title">Wilayah</div>
        <div className="mi-region-list">
          {wilayah.map(w => (
            <div
              key={w.id_wilayah}
              className={`mi-region-row ${selectedWilayah === w.id_wilayah ? 'aktif' : ''}`}
              style={{ borderLeftColor: SEV_COLOR[w.severity_tertinggi] ?? 'transparent' }}
              onClick={() => onSelectWilayah(w.id_wilayah)}
            >
              <div className="mi-region-info">
                <div className="mi-region-nama">{w.nama}</div>
                <div className="mi-region-prov">{w.provinsi}</div>
              </div>
              <div className="mi-region-meta">
                {w.total_kasus > 0 && (
                  <span className="mi-region-badge kasus">{w.total_kasus} kasus</span>
                )}
                {w.alert_aktif > 0 && (
                  <span className="mi-region-badge alert">{w.alert_aktif} alert</span>
                )}
                {w.skor_risiko_rata > 0 && (
                  <span className="mi-region-skor" style={{ color: SEV_COLOR[w.severity_tertinggi] }}>
                    {w.skor_risiko_rata}
                  </span>
                )}
                <MapPin size={9} className="mi-region-icon" />
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  )
}
