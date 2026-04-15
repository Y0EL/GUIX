import { Clock, Users, Bell, FolderSearch } from 'lucide-react'
import type { IncidentWithMeta, IncidentStatus } from '../types'
import { hitungSLA } from '../utils'
import RiskGauge from './RiskGauge'

type SortBy = 'risiko' | 'waktu' | 'alert'

type Props = {
  incidents: IncidentWithMeta[]
  selected: string | null
  filterStatus: IncidentStatus[]
  filterTipe: string[]
  filterKota: string[]
  sortBy: SortBy
  onSelect: (id: string) => void
  onFilterStatus: (s: IncidentStatus) => void
  onFilterTipe: (t: string) => void
  onSort: (by: SortBy) => void
}

const STATUS_LIST: IncidentStatus[] = ['baru', 'monitoring', 'analisis', 'eskalasi', 'selesai']

const TIPE_LABEL: Record<string, string> = {
  kebakaran_gudang: 'Kebakaran',
  pendanaan_mencurigakan: 'Pendanaan',
  propaganda: 'Propaganda',
}

export default function IncidentListPanel({
  incidents, selected,
  filterStatus, filterTipe, filterKota,
  sortBy,
  onSelect, onFilterStatus, onFilterTipe, onSort,
}: Props) {
  const uniqueTipe = Array.from(new Set(incidents.map(i => i.tipe_kasus)))
  const uniqueKota = Array.from(new Set(incidents.map(i => i.kota)))

  const filtered = incidents
    .filter(i => filterStatus.length === 0 || filterStatus.includes(i.runtimeStatus))
    .filter(i => filterTipe.length === 0 || filterTipe.includes(i.tipe_kasus))
    .filter(i => filterKota.length === 0 || filterKota.includes(i.kota))
    .slice()
    .sort((a, b) => {
      if (sortBy === 'risiko') return (b.skor?.skor_risiko ?? 0) - (a.skor?.skor_risiko ?? 0)
      if (sortBy === 'waktu') return new Date(a.waktu_insiden).getTime() - new Date(b.waktu_insiden).getTime()
      return b.alertCount - a.alertCount
    })

  return (
    <div className="iq-col-left">
      {/* Status filter */}
      <div className="iq-filter-section">
        <div className="iq-filter-label">Status</div>
        <div className="iq-filter-chips">
          {STATUS_LIST.map(s => (
            <button
              key={s}
              className={`ac-chip ${filterStatus.includes(s) ? 'aktif' : ''}`}
              onClick={() => onFilterStatus(s)}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Tipe filter */}
      {uniqueTipe.length > 1 && (
        <div className="iq-filter-section">
          <div className="iq-filter-label">Tipe</div>
          <div className="iq-filter-chips">
            {uniqueTipe.map(t => (
              <button
                key={t}
                className={`ac-chip ${filterTipe.includes(t) ? 'aktif' : ''}`}
                onClick={() => onFilterTipe(t)}
              >
                {TIPE_LABEL[t] ?? t}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Kota filter */}
      {uniqueKota.length > 1 && (
        <div className="iq-filter-section">
          <div className="iq-filter-label">Wilayah</div>
          <div className="iq-filter-chips">
            {uniqueKota.map(k => (
              <button
                key={k}
                className={`ac-chip ${filterKota.includes(k) ? 'aktif' : ''}`}
                onClick={() => onFilterStatus(k as IncidentStatus)}
              >
                {k}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Sort */}
      <div className="iq-sort-bar">
        <span>Urutkan</span>
        {(['risiko', 'waktu', 'alert'] as SortBy[]).map(s => (
          <button
            key={s}
            className={`iq-sort-btn ${sortBy === s ? 'aktif' : ''}`}
            onClick={() => onSort(s)}
          >
            {s === 'risiko' ? 'Risiko' : s === 'waktu' ? 'Waktu' : 'Alert'}
          </button>
        ))}
        <span style={{ marginLeft: 'auto', fontSize: 9, color: 'rgba(243,234,234,.18)' }}>
          {filtered.length}/{incidents.length}
        </span>
      </div>

      {/* Card list */}
      <div className="iq-incident-list">
        {filtered.map((inc, idx) => {
          const sla = hitungSLA(inc.waktu_insiden)
          const score = inc.skor?.skor_risiko ?? 0
          const statusCls = `status-${inc.runtimeStatus}`

          return (
            <div
              key={inc.id_kasus}
              className={`iq-card ${selected === inc.id_kasus ? 'aktif' : ''} ${statusCls}`}
              onClick={() => onSelect(inc.id_kasus)}
            >
              <div className="iq-card-header">
                <span className="iq-priority-num">
                  {String(idx + 1).padStart(2, '0')}
                </span>
                <RiskGauge score={score} size="sm" />
                <div className="iq-card-body">
                  <div className="iq-card-title">{inc.judul}</div>
                  <div className="iq-card-meta">
                    <span className="iq-tipe-badge">
                      {TIPE_LABEL[inc.tipe_kasus] ?? inc.tipe_kasus}
                    </span>
                    <span>{inc.kota}</span>
                  </div>
                </div>
              </div>

              <div className="iq-card-footer">
                <span className={`iq-sla-tag ${sla.kelas}`}>
                  <Clock size={9} />
                  {sla.label}
                </span>
                <span className="iq-meta-icon">
                  <Users size={9} />
                  {inc.jumlah_aktor}
                </span>
                <span className="iq-alert-badge">
                  <Bell size={8} style={{ display: 'inline', marginRight: 3 }} />
                  {inc.alertCount} alert
                </span>
                <span className={`iq-status-badge ${inc.runtimeStatus}`}>
                  {inc.runtimeStatus}
                </span>
              </div>
            </div>
          )
        })}

        {filtered.length === 0 && (
          <div style={{
            padding: '32px 16px', textAlign: 'center',
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
          }}>
            <FolderSearch size={24} style={{ color: 'rgba(179,24,24,.2)' }} />
            <span style={{ fontSize: 12, color: 'rgba(243,234,234,.2)' }}>
              Tidak ada insiden yang cocok
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
