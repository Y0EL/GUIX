import { X, MapPin, AlertTriangle, ShieldAlert, User } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { Lokasi, Kasus, Peringatan } from '../types'
import { formatTanggal } from '../utils'

type Tab = 'info' | 'kasus' | 'alert' | 'entitas'

type Props = {
  lokasi: Lokasi
  kasus: Kasus[]
  peringatan: Peringatan[]
  activeTab: Tab
  onTab: (t: Tab) => void
  onClose: () => void
}

const SEV_COLOR: Record<string, string> = {
  tinggi:   '#E5282A',
  menengah: '#F5A623',
  rendah:   '#4CAF50',
}

const SEV_LABEL: Record<string, string> = {
  tinggi:   'KRITIS',
  menengah: 'TINGGI',
  rendah:   'RENDAH',
}

export default function LocationDetailPanel({
  lokasi,
  kasus,
  peringatan,
  activeTab,
  onTab,
  onClose,
}: Props) {
  const nav = useNavigate()

  // Kasus yang berada di provinsi sama
  const kasusWilayah = kasus.filter(k => k.provinsi === lokasi.provinsi)
  const kasusIds = kasusWilayah.map(k => k.id_kasus)
  const alertWilayah = peringatan.filter(p => kasusIds.includes(p.id_kasus))

  // Severity tertinggi dari alert
  const sev_order: Record<string, number> = { tinggi: 3, menengah: 2, rendah: 1 }
  let sevMax = 'rendah'
  for (const a of alertWilayah) {
    if (sev_order[a.tingkat_keparahan] > sev_order[sevMax]) sevMax = a.tingkat_keparahan
  }

  const TABS: { key: Tab; label: string }[] = [
    { key: 'info',    label: 'Info Lokasi' },
    { key: 'kasus',   label: `Kasus (${kasusWilayah.length})` },
    { key: 'alert',   label: `Alert (${alertWilayah.length})` },
    { key: 'entitas', label: 'Entitas' },
  ]

  return (
    <div className="mi-detail-panel">
      {/* Header */}
      <div className="mi-detail-header">
        <div className="mi-detail-header-info">
          <div className="mi-detail-label">{lokasi.label}</div>
          <div className="mi-detail-sub">
            <MapPin size={9} />
            {lokasi.kota}, {lokasi.provinsi}
          </div>
        </div>
        {alertWilayah.length > 0 && (
          <div
            className="mi-detail-sev-badge"
            style={{
              background: SEV_COLOR[sevMax] + '22',
              border: `1px solid ${SEV_COLOR[sevMax]}55`,
              color: SEV_COLOR[sevMax],
            }}
          >
            <ShieldAlert size={10} />
            {SEV_LABEL[sevMax]}
          </div>
        )}
        <button className="mi-detail-close" onClick={onClose}>
          <X size={14} />
        </button>
      </div>

      {/* Tab bar */}
      <div className="mi-tab-bar">
        {TABS.map(t => (
          <button
            key={t.key}
            className={`mi-tab-btn ${activeTab === t.key ? 'aktif' : ''}`}
            onClick={() => onTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="mi-tab-content">

        {activeTab === 'info' && (
          <div className="mi-info-grid">
            <div className="mi-info-row">
              <span className="lbl">Tipe Lokasi</span>
              <span className="val">{lokasi.tipe_lokasi.replace(/_/g, ' ')}</span>
            </div>
            <div className="mi-info-row">
              <span className="lbl">Kepercayaan</span>
              <span className="val">{Math.round(lokasi.kepercayaan * 100)}%</span>
            </div>
            <div className="mi-info-row">
              <span className="lbl">Diamati Pada</span>
              <span className="val">{formatTanggal(lokasi.diamati_pada)}</span>
            </div>
            <div className="mi-info-row">
              <span className="lbl">Koordinat</span>
              <span className="val" style={{ fontFamily: 'var(--font-j)', fontSize: 11 }}>
                {lokasi.latitude.toFixed(5)}, {lokasi.longitude.toFixed(5)}
              </span>
            </div>
            <div className="mi-info-row">
              <span className="lbl">ID Profil</span>
              <span className="val" style={{ fontSize: 10, opacity: .6 }}>{lokasi.id_profil}</span>
            </div>
            <div className="mi-info-row">
              <span className="lbl">ID Lokasi</span>
              <span className="val" style={{ fontSize: 10, opacity: .6 }}>{lokasi.id_lokasi}</span>
            </div>
          </div>
        )}

        {activeTab === 'kasus' && (
          <div className="mi-list-content">
            {kasusWilayah.length === 0 ? (
              <div className="mi-empty">Tidak ada kasus di wilayah ini</div>
            ) : kasusWilayah.map(k => (
              <div key={k.id_kasus} className="mi-kasus-row">
                <div className="mi-kasus-judul">{k.judul}</div>
                <div className="mi-kasus-meta">
                  <span>{k.tipe_kasus.replace(/_/g, ' ')}</span>
                  <span>·</span>
                  <span>{k.kota}</span>
                  <span>·</span>
                  <span
                    style={{
                      padding: '1px 6px', borderRadius: 3, fontSize: 9, fontWeight: 700,
                      background: k.status === 'monitoring' ? 'rgba(220,38,38,.15)' : 'rgba(99,102,241,.15)',
                      color: k.status === 'monitoring' ? '#ff8a8a' : '#a5b4fc',
                    }}
                  >
                    {k.status}
                  </span>
                </div>
                <div className="mi-kasus-meta" style={{ marginTop: 2 }}>
                  <span>{k.jumlah_aktor} aktor</span>
                  <span>·</span>
                  <span>{formatTanggal(k.waktu_insiden)}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'alert' && (
          <div className="mi-list-content">
            {alertWilayah.length === 0 ? (
              <div className="mi-empty">Tidak ada alert di wilayah ini</div>
            ) : alertWilayah.map(a => (
              <div key={a.id_peringatan} className="mi-alert-row">
                <div className="mi-alert-header">
                  <span
                    className="mi-alert-sev"
                    style={{ background: SEV_COLOR[a.tingkat_keparahan] + '22', color: SEV_COLOR[a.tingkat_keparahan] }}
                  >
                    {a.tingkat_keparahan.toUpperCase()}
                  </span>
                  <span className="mi-alert-tipe">{a.tipe_sinyal.replace(/_/g, ' ')}</span>
                  <span className="mi-alert-conf">{Math.round(a.kepercayaan * 100)}%</span>
                </div>
                <div className="mi-alert-desc">{a.deskripsi}</div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'entitas' && (
          <div className="mi-empty" style={{ flexDirection: 'column', gap: 8 }}>
            <User size={24} style={{ color: 'rgba(179,24,24,.3)' }} />
            <div>Profil entitas tersedia setelah H6 Entity Profile selesai</div>
            <div style={{ fontSize: 10, opacity: .5 }}>ID Profil: {lokasi.id_profil}</div>
          </div>
        )}

      </div>

      {/* Action bar */}
      <div className="mi-action-bar">
        <button
          className="mi-action-btn primary"
          onClick={() => nav('/incident-queue', { state: { filterWilayah: lokasi.kota } })}
        >
          <AlertTriangle size={12} />
          Buka di Incident Queue
        </button>
        <button className="mi-action-btn disabled" disabled title="Tersedia setelah H6">
          <User size={12} />
          Entity Profile
        </button>
      </div>
    </div>
  )
}
