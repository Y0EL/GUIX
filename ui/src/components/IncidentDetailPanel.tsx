import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FolderSearch, CheckCircle, ArrowUpCircle, BookOpen,
  UserPlus, Users, Bell, MapPin, Bookmark, BookmarkCheck, Clock,
} from 'lucide-react'
import type { IncidentWithMeta, IncidentStatus } from '../types'
import LiveIntelFeed from './LiveIntelFeed'
import { extractProbabilities, hitungSLA, formatTanggal } from '../utils'
import RiskGauge from './RiskGauge'

type Tab = 'overview' | 'alerts' | 'risk' | 'actions'

type Props = {
  incident: IncidentWithMeta | null
  onStatusUpdate: (id: string, status: IncidentStatus) => void
  onAssign: (id: string, analyst: string) => void
  onToggleBriefing: (id: string) => void
  onResolve: (id: string) => void
  onEscalate: (id: string) => void
}

const PIPELINE: IncidentStatus[] = ['baru', 'monitoring', 'analisis', 'eskalasi', 'selesai']
const PIPELINE_LABEL: Record<IncidentStatus, string> = {
  baru: 'Baru', monitoring: 'Monitor', analisis: 'Analisis',
  eskalasi: 'Eskalasi', selesai: 'Selesai',
}

const SEV_COLOR: Record<string, string> = {
  tinggi: '#DC2626', menengah: '#DD6B20', rendah: '#4CAF50',
}

function probColor(v: number): string {
  if (v >= 0.6) return '#DC2626'
  if (v >= 0.4) return '#DD6B20'
  return '#4CAF50'
}

export default function IncidentDetailPanel({
  incident, onStatusUpdate, onAssign, onToggleBriefing, onResolve, onEscalate,
}: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('overview')
  const [assignInput, setAssignInput] = useState('')
  const navigate = useNavigate()

  if (!incident) {
    return (
      <div className="iq-col-right">
        <div className="iq-detail-empty">
          <FolderSearch size={36} strokeWidth={1.4} />
          <p>Pilih insiden dari antrian</p>
        </div>
      </div>
    )
  }

  const sla = hitungSLA(incident.waktu_insiden)
  const probs = incident.skor ? extractProbabilities(incident.skor) : []
  const curIdx = PIPELINE.indexOf(incident.runtimeStatus)

  const handleAssign = () => {
    if (assignInput.trim()) {
      onAssign(incident.id_kasus, assignInput.trim())
      setAssignInput('')
    }
  }

  const isDone = incident.runtimeStatus === 'selesai'

  /* ── TABS ── */

  const tabOverview = (
    <div>
      <div className="iq-overview-grid">
        <div className="iq-stat-block">
          <span className="lbl">Tipe</span>
          <span className="val">{incident.tipe_kasus.replace(/_/g, ' ')}</span>
        </div>
        <div className="iq-stat-block">
          <span className="lbl">Status</span>
          <span className="val" style={{ textTransform: 'capitalize' }}>{incident.runtimeStatus}</span>
        </div>
        <div className="iq-stat-block">
          <span className="lbl">Lokasi</span>
          <span className="val">{incident.kota}</span>
        </div>
        <div className="iq-stat-block">
          <span className="lbl">Insiden</span>
          <span className="val" style={{ fontSize: 11 }}>
            {formatTanggal(incident.waktu_insiden)}
          </span>
        </div>
        <div className="iq-stat-block">
          <span className="lbl">Aktor</span>
          <span className="val">
            <Users size={11} style={{ display: 'inline', marginRight: 4 }} />
            {incident.jumlah_aktor}
          </span>
        </div>
        <div className="iq-stat-block">
          <span className="lbl">Alert</span>
          <span className="val">
            <Bell size={11} style={{ display: 'inline', marginRight: 4 }} />
            {incident.alertCount}
          </span>
        </div>
      </div>

      {/* SLA block */}
      <div className="iq-stat-block" style={{ marginBottom: 14, flexDirection: 'row', alignItems: 'center', gap: 10 }}>
        <div style={{ flex: 1 }}>
          <span className="lbl">Usia Insiden (SLA)</span>
          <span className={`iq-sla-tag ${sla.kelas}`} style={{ marginTop: 3, fontSize: 16 }}>
            {sla.label}
          </span>
        </div>
        {incident.skor && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
            <span className="lbl" style={{ fontSize: 9 }}>Risk Score</span>
            <RiskGauge score={incident.skor.skor_risiko} size="sm" />
          </div>
        )}
      </div>

      {/* Assigned analyst */}
      <div className="iq-analyst-row">
        <span className="lbl">Analis</span>
        {incident.assignedAnalyst ? (
          <span className="val">
            <UserPlus size={11} style={{ display: 'inline', marginRight: 5 }} />
            {incident.assignedAnalyst}
          </span>
        ) : (
          <span className="val" style={{ color: 'rgba(243,234,234,.25)' }}>
            Belum ditugaskan
          </span>
        )}
      </div>

      {/* Mini timeline */}
      <div style={{ marginTop: 14 }}>
        <div style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.12em', color: 'rgba(243,234,234,.22)', marginBottom: 10 }}>
          Kronologi Singkat
        </div>
        <div className="iq-timeline">
          {[
            { label: 'Insiden terjadi', time: formatTanggal(incident.waktu_insiden), aktif: false },
            { label: 'Terdeteksi sistem — alert masuk', time: 'Otomatis', aktif: false },
            { label: `Status: ${incident.runtimeStatus}`, time: 'Saat ini', aktif: true },
            { label: 'Timeline lengkap tersedia', time: '→ /timeline', aktif: false },
          ].map((item, i, arr) => (
            <div key={i} className="iq-tl-item">
              <div className="iq-tl-dot-wrap">
                <div className={`iq-tl-dot ${item.aktif ? 'aktif' : ''}`} />
                {i < arr.length - 1 && <div className="iq-tl-line" />}
              </div>
              <div className="iq-tl-body">
                <div className="iq-tl-label">{item.label}</div>
                <div className="iq-tl-time">{item.time}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Live Intel Feed */}
      <div style={{ marginTop: 16 }}>
        <LiveIntelFeed
          idKasus={incident.id_kasus}
          kasusKota={incident.kota}
          kasusProvinsi={incident.provinsi}
        />
      </div>
    </div>
  )

  const tabAlerts = (
    <div>
      {incident.linkedAlerts.length === 0 ? (
        <div style={{ fontSize: 12, color: 'rgba(243,234,234,.25)', padding: '16px 0' }}>
          Tidak ada alert terhubung.
        </div>
      ) : (
        <>
          {incident.linkedAlerts.length === 1 && (
            <div style={{ fontSize: 10, color: 'rgba(243,234,234,.22)', marginBottom: 10, fontStyle: 'italic' }}>
              Hanya 1 sinyal terhubung ke insiden ini.
            </div>
          )}
          {incident.linkedAlerts.map(a => (
            <div key={a.id_peringatan} className="iq-alert-item">
              <div className="iq-alert-item-header">
                <span
                  style={{
                    width: 7, height: 7, borderRadius: '50%',
                    background: SEV_COLOR[a.tingkat_keparahan] ?? '#888',
                    display: 'inline-block', flexShrink: 0,
                  }}
                />
                <span style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.07em', color: 'rgba(243,234,234,.35)' }}>
                  {a.tingkat_keparahan}
                </span>
                <span style={{ fontSize: 10, color: 'rgba(243,234,234,.3)', flex: 1 }}>
                  {a.tipe_sinyal.replace(/_/g, ' ')}
                </span>
              </div>
              <div className="iq-alert-desc">{a.deskripsi}</div>
              <div className="iq-alert-conf-row">
                <div className="ac-conf-track" style={{ flex: 1 }}>
                  <div
                    className="ac-conf-fill-lg"
                    style={{
                      width: `${(a.kepercayaan ?? 0) * 100}%`,
                      background: SEV_COLOR[a.tingkat_keparahan],
                    }}
                  />
                </div>
                <span>{Math.round((a.kepercayaan ?? 0) * 100)}% kepercayaan</span>
                <span style={{ marginLeft: 'auto', opacity: .5, fontSize: 9 }}>{a.id_peringatan}</span>
              </div>
            </div>
          ))}
          <div style={{ marginTop: 10, fontSize: 10, color: 'rgba(243,234,234,.2)', borderTop: '1px solid rgba(179,24,24,.07)', paddingTop: 10 }}>
            Lihat detail triage di Alert Center (/alert-center)
          </div>
        </>
      )}
    </div>
  )

  const tabRisk = incident.skor ? (
    <div>
      <div className="iq-risk-header">
        <div style={{ flex: 1 }}>
          <RiskGauge score={incident.skor.skor_risiko} size="lg" />
        </div>
        <div className="iq-risk-score-col" style={{ flex: 2 }}>
          <span
            className="iq-risk-score-num"
            style={{ color: incident.skor.skor_risiko >= 70 ? '#ff8a8a' : incident.skor.skor_risiko >= 50 ? '#f0a060' : '#81c784' }}
          >
            {incident.skor.skor_risiko}
          </span>
          <span className={`iq-risk-label ${incident.skor.label_risiko}`}>
            {incident.skor.label_risiko}
          </span>
        </div>
      </div>

      {probs.length > 0 && (
        <div className="iq-prob-section">
          <div className="iq-prob-section-title">Probabilitas</div>
          {probs.map(p => (
            <div key={p.label} className="iq-prob-row">
              <span className="iq-prob-label">{p.label}</span>
              <div className="iq-prob-track">
                <div
                  className="iq-prob-fill"
                  style={{
                    width: `${p.value * 100}%`,
                    background: probColor(p.value),
                  }}
                />
              </div>
              <span className="iq-prob-pct">{Math.round(p.value * 100)}%</span>
            </div>
          ))}
        </div>
      )}

      <div style={{ marginBottom: 14 }}>
        <div className="iq-prob-section-title">Pendorong Risiko</div>
        <div className="iq-pendorong-list">
          {incident.skor.pendorong.map(d => (
            <span key={d} className="iq-pendorong-tag">{d.replace(/_/g, ' ')}</span>
          ))}
        </div>
      </div>

      <div className="iq-penafian">{incident.skor.penafian}</div>
    </div>
  ) : (
    <div style={{ fontSize: 12, color: 'rgba(243,234,234,.25)', padding: '16px 0' }}>
      Data risiko tidak tersedia untuk insiden ini.
    </div>
  )

  const tabActions = (
    <div>
      {/* Pipeline visualization */}
      <div className="iq-action-section">
        <div className="iq-action-section-label">Status Pipeline</div>
        <div className="iq-pipeline-bar">
          {PIPELINE.map((step, i) => {
            const stepCls = i < curIdx ? 'lewat' : i === curIdx ? 'aktif' : ''
            return (
              <div key={step} style={{ display: 'flex', alignItems: 'flex-start' }}>
                {i > 0 && <div className="iq-pipeline-connector" />}
                <div className={`iq-pipeline-step ${stepCls}`}>
                  <div className="iq-pipeline-dot">
                    {i < curIdx ? '✓' : i === curIdx ? '●' : '○'}
                  </div>
                  <div className="iq-pipeline-lbl">{PIPELINE_LABEL[step]}</div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Update status */}
      <div className="iq-action-section">
        <div className="iq-action-section-label">Update Status</div>
        <div className="iq-status-btns">
          {PIPELINE.filter(s => s !== incident.runtimeStatus).map(s => (
            <button
              key={s}
              className="iq-action-btn assign-quick"
              onClick={() => onStatusUpdate(incident.id_kasus, s)}
            >
              → {PIPELINE_LABEL[s]}
            </button>
          ))}
        </div>
      </div>

      {/* Assign */}
      <div className="iq-action-section">
        <div className="iq-action-section-label">Tugaskan Analis</div>
        <div className="iq-assign-row">
          <input
            className="iq-assign-input"
            type="text"
            placeholder="Nama analis..."
            value={assignInput}
            onChange={e => setAssignInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleAssign() }}
          />
          <button
            className="iq-action-btn assign-quick"
            disabled={!assignInput.trim()}
            onClick={handleAssign}
          >
            <UserPlus size={12} /> Tugaskan
          </button>
        </div>
        {incident.assignedAnalyst && (
          <div className="iq-current-analyst">
            <UserPlus size={11} />
            Saat ini: <strong>{incident.assignedAnalyst}</strong>
          </div>
        )}
      </div>

      {/* Briefing flag */}
      <div className="iq-action-section">
        <div className="iq-action-section-label">Tanda Briefing Komando</div>
        <button
          className={`iq-briefing-btn ${incident.flaggedForBriefing ? 'aktif' : ''}`}
          onClick={() => onToggleBriefing(incident.id_kasus)}
        >
          {incident.flaggedForBriefing
            ? <><BookmarkCheck size={14} /> Ditandai untuk Briefing Komando</>
            : <><Bookmark size={14} /> Tandai untuk Briefing Komando</>}
        </button>
      </div>

      {/* Navigasi lintas halaman */}
      <div className="iq-action-section">
        <div className="iq-action-section-label">Analisis Lanjutan</div>
        <button className="iq-action-btn assign-quick" onClick={() => navigate('/narrative', { state: { filterKasus: incident.id_kasus } })}>
          Narasi & Tren →
        </button>
        <button className="iq-action-btn assign-quick" onClick={() => navigate('/timeline', { state: { filterKasus: incident.id_kasus } })}>
          Timeline →
        </button>
      </div>
    </div>
  )

  const TABS: { key: Tab; label: string }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'alerts', label: `Alerts (${incident.alertCount})` },
    { key: 'risk', label: 'Risk' },
    { key: 'actions', label: 'Actions' },
  ]

  return (
    <div className="iq-col-right">
      {/* Header */}
      <div className="iq-detail-header">
        <div className="iq-detail-title">{incident.judul}</div>
        <div className="iq-detail-subtitle">
          <span className={`iq-risk-label ${incident.skor?.label_risiko ?? 'rendah'}`}>
            {incident.skor?.label_risiko ?? '—'}
          </span>
          <span style={{ fontSize: 10, color: 'rgba(243,234,234,.3)', display: 'flex', alignItems: 'center', gap: 4 }}>
            <MapPin size={9} /> {incident.kota}, {incident.provinsi}
          </span>
          <span className={`iq-status-badge ${incident.runtimeStatus}`}>
            {incident.runtimeStatus}
          </span>
          {incident.flaggedForBriefing && (
            <span style={{ fontSize: 9, color: '#f0a060', display: 'flex', alignItems: 'center', gap: 3 }}>
              <BookmarkCheck size={10} /> Briefing
            </span>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="iq-tab-bar">
        {TABS.map(t => (
          <button
            key={t.key}
            className={`iq-tab-btn ${activeTab === t.key ? 'aktif' : ''}`}
            onClick={() => setActiveTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="iq-tab-content">
        {activeTab === 'overview' && tabOverview}
        {activeTab === 'alerts' && tabAlerts}
        {activeTab === 'risk' && tabRisk}
        {activeTab === 'actions' && tabActions}
      </div>

      {/* Action bar — always visible */}
      <div className="iq-actions-bar">
        <div className="iq-actions-row">
          <button
            className="iq-action-btn"
            onClick={() => navigate('/timeline', { state: { filterKasus: incident.id_kasus } })}
            title="Buka kronologi lengkap kasus ini"
          >
            <Clock size={12} />
            Lihat Timeline
          </button>
          <button
            className={`iq-action-btn briefing ${incident.flaggedForBriefing ? 'aktif' : ''}`}
            onClick={() => onToggleBriefing(incident.id_kasus)}
          >
            <BookOpen size={12} />
            {incident.flaggedForBriefing ? 'Unflag Briefing' : 'Flag Briefing'}
          </button>
          <button
            className="iq-action-btn escalate"
            disabled={incident.runtimeStatus === 'eskalasi' || isDone}
            onClick={() => onEscalate(incident.id_kasus)}
          >
            <ArrowUpCircle size={12} />
            Eskalasi ke Komando
          </button>
          <button
            className="iq-action-btn resolve"
            disabled={isDone}
            onClick={() => onResolve(incident.id_kasus)}
          >
            <CheckCircle size={12} />
            {isDone ? 'Selesai' : 'Tandai Selesai'}
          </button>
        </div>
      </div>
    </div>
  )
}
