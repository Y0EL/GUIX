import { useState } from 'react'
import {
  CheckCircle, XCircle, ArrowUpCircle, Link2, UserPlus,
  Tag, MinusCircle, MousePointerClick, User, Clock, Network,
  ShieldAlert,
} from 'lucide-react'
import type { AlertWithTriage, Kasus, TriageStatus, SkorRisiko, Entitas } from '../types'
import LiveIntelFeed from './LiveIntelFeed'

type Props = {
  alert: AlertWithTriage | null
  kasus: Kasus[]
  skorRisiko: SkorRisiko[]
  entitas: Entitas[]
  onTriage: (id: string, status: TriageStatus) => void
  onNote: (id: string, note: string) => void
  onTag: (id: string, tag: string) => void
}

const SEVERITY_COLOR: Record<string, string> = {
  tinggi: '#DC2626',
  menengah: '#DD6B20',
  rendah: '#4CAF50',
}

const CONF_COLOR = (v: number) => {
  if (v >= 0.8) return '#DC2626'
  if (v >= 0.6) return '#DD6B20'
  return '#4CAF50'
}

export default function AlertDetailPanel({ alert, kasus, skorRisiko, entitas, onTriage, onNote, onTag }: Props) {
  const [noteVal, setNoteVal] = useState('')
  const [tagInput, setTagInput] = useState('')
  const [eskalasiConfirm, setEskalasiConfirm] = useState(false)

  if (!alert) {
    return (
      <div className="ac-col-center">
        <div className="ac-detail-empty">
          <MousePointerClick size={32} strokeWidth={1.5} />
          <p>Pilih alert dari daftar untuk mulai triage</p>
        </div>
      </div>
    )
  }

  const linkedKasus = kasus.find(k => k.id_kasus === alert.id_kasus)
  const linkedSkor = skorRisiko.find(s => s.id_kasus === alert.id_kasus)
  const linkedEntitas = entitas.filter(e => e.id_kasus === alert.id_kasus)
  const conf = alert.kepercayaan ?? 0

  const handleNote = () => {
    if (noteVal.trim()) {
      onNote(alert.id_peringatan, noteVal.trim())
      setNoteVal('')
    }
  }

  const handleTag = () => {
    if (tagInput.trim()) {
      onTag(alert.id_peringatan, tagInput.trim())
      setTagInput('')
    }
  }

  const isDone = ['valid', 'false_positive', 'diabaikan', 'eskalasi'].includes(alert.triage)

  // derive probabilitas keys
  const probEntries = linkedSkor
    ? Object.entries(linkedSkor).filter(([k]) => k.startsWith('probabilitas_')) as [string, number][]
    : []

  return (
    <div className="ac-col-center">
      {/* Scrollable detail */}
      <div className="ac-detail-inner">

        {/* Title row */}
        <div className="ac-detail-title-row">
          <div className={`ac-severity-badge ${alert.tingkat_keparahan}`}>
            <span
              style={{
                display: 'inline-block', width: 7, height: 7,
                borderRadius: '50%',
                background: SEVERITY_COLOR[alert.tingkat_keparahan],
              }}
            />
            {alert.tingkat_keparahan.toUpperCase()}
          </div>
          <div className="ac-detail-id">
            {alert.tipe_sinyal.replace(/_/g, ' ')}
            <small>{alert.id_peringatan}</small>
          </div>
        </div>

        {/* Description */}
        <div className="ac-detail-desc">
          {alert.deskripsi}
        </div>

        {/* Meta grid */}
        <div className="ac-detail-meta-grid">
          <div className="ac-meta-cell">
            <span className="lbl">Tipe Sinyal</span>
            <span className="val">{alert.tipe_sinyal.replace(/_/g, ' ')}</span>
          </div>
          <div className="ac-meta-cell">
            <span className="lbl">Status Triage</span>
            <span className="val" style={{ textTransform: 'capitalize' }}>
              {alert.triage.replace(/_/g, ' ')}
            </span>
          </div>
          {alert.assignee && (
            <div className="ac-meta-cell">
              <span className="lbl">Ditugaskan ke</span>
              <span className="val">{alert.assignee}</span>
            </div>
          )}
          {alert.tags && alert.tags.length > 0 && (
            <div className="ac-meta-cell" style={{ gridColumn: 'span 2' }}>
              <span className="lbl">Tags</span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginTop: 3 }}>
                {alert.tags.map(t => (
                  <span key={t} className="tag" style={{ fontSize: 10 }}>{t}</span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Confidence bar */}
        <div className="ac-conf-row">
          <span>Confidence</span>
          <div className="ac-conf-track">
            <div
              className="ac-conf-fill-lg"
              style={{ width: `${conf * 100}%`, background: CONF_COLOR(conf) }}
            />
          </div>
          <span className="ac-conf-pct">{Math.round(conf * 100)}%</span>
        </div>

        {/* Linked case */}
        {linkedKasus ? (
          <div className="ac-linked-kasus">
            <div className="lbl">
              <Link2 size={9} style={{ display: 'inline', marginRight: 4 }} />
              Linked Case
            </div>
            <div className="val">{linkedKasus.judul}</div>
            <div className="sub">
              {linkedKasus.tipe_kasus} · {linkedKasus.kota}, {linkedKasus.provinsi} · Status: {linkedKasus.status}
            </div>
          </div>
        ) : (
          <div className="ac-linked-kasus" style={{ opacity: .45 }}>
            <div className="lbl">Linked Case</div>
            <div className="val" style={{ fontSize: 11 }}>{alert.id_kasus}</div>
          </div>
        )}

        {/* Risk Assessment */}
        {linkedSkor && (
          <div className="ac-risk-block">
            <div className="ac-risk-header">
              <ShieldAlert size={11} />
              Risk Assessment — {linkedSkor.label_risiko.toUpperCase()}
            </div>

            {/* Skor bar */}
            <div className="ac-risk-score-row">
              <span className="ac-risk-score-label">Skor Risiko</span>
              <div className="ac-risk-bar-track">
                <div
                  className="ac-risk-bar-fill"
                  style={{
                    width: `${linkedSkor.skor_risiko}%`,
                    background: linkedSkor.skor_risiko >= 70 ? '#DC2626' : linkedSkor.skor_risiko >= 50 ? '#DD6B20' : '#4CAF50',
                  }}
                />
              </div>
              <span className={`ac-risk-score-num ${linkedSkor.skor_risiko >= 70 ? 'tinggi' : linkedSkor.skor_risiko >= 50 ? 'menengah' : 'rendah'}`}>
                {linkedSkor.skor_risiko}
              </span>
            </div>

            {/* Probabilitas */}
            {probEntries.length > 0 && (
              <div className="ac-risk-prob-grid">
                {probEntries.map(([k, v]) => (
                  <div key={k} className="ac-risk-prob-cell">
                    <span className="lbl">{k.replace('probabilitas_', '').replace(/_/g, ' ')}</span>
                    <span className="val">{Math.round((v as number) * 100)}%</span>
                  </div>
                ))}
              </div>
            )}

            {/* Pendorong chips */}
            {linkedSkor.pendorong.length > 0 && (
              <div className="ac-pendorong-row">
                {linkedSkor.pendorong.map(p => (
                  <span key={p} className="ac-pendorong-chip">{p.replace(/_/g, ' ')}</span>
                ))}
              </div>
            )}

            {/* Entitas terkait */}
            {linkedEntitas.length > 0 && (
              <div className="ac-entitas-row">
                {linkedEntitas.slice(0, 5).map((e, i) => (
                  <span key={i} className={`ac-entitas-chip ${e.tipe_entitas}`} title={`${e.tipe_entitas} · ${e.jumlah}x`}>
                    {e.nilai}
                  </span>
                ))}
              </div>
            )}

            <div className="ac-risk-penafian">{linkedSkor.penafian}</div>
          </div>
        )}

        {/* Note */}
        {alert.note && (
          <div style={{ marginBottom: 14, padding: '8px 12px', background: 'rgba(99,102,241,.07)', border: '1px solid rgba(99,102,241,.18)', borderRadius: 7 }}>
            <div style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.1em', color: 'rgba(165,180,252,.5)', marginBottom: 4 }}>Catatan</div>
            <div style={{ fontSize: 12, color: 'rgba(243,234,234,.7)', lineHeight: 1.5 }}>{alert.note}</div>
          </div>
        )}

        {/* Add note */}
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.1em', color: 'rgba(243,234,234,.22)', marginBottom: 5 }}>
            Tambah Catatan
          </div>
          <textarea
            className="ac-note-area"
            rows={2}
            placeholder="Tulis catatan cepat..."
            value={noteVal}
            onChange={e => setNoteVal(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleNote() } }}
          />
          {noteVal.trim() && (
            <button className="ac-action-btn assign" style={{ marginTop: 5, fontSize: 10 }} onClick={handleNote}>
              Simpan Catatan
            </button>
          )}
        </div>

        {/* Add tag */}
        <div style={{ marginBottom: 6 }}>
          <div style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.1em', color: 'rgba(243,234,234,.22)', marginBottom: 5 }}>
            Tag
          </div>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <input
              type="text"
              placeholder="urgent, finansial, propaganda..."
              value={tagInput}
              onChange={e => setTagInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); handleTag() } }}
              style={{
                flex: 1, background: 'rgba(6,2,2,.7)', border: '1px solid rgba(179,24,24,.18)',
                borderRadius: 5, color: 'var(--aksen)', fontFamily: 'var(--font)',
                fontSize: 11, padding: '5px 9px', outline: 'none',
              }}
            />
            {tagInput.trim() && (
              <button className="ac-action-btn assign" style={{ padding: '5px 10px', fontSize: 10 }} onClick={handleTag}>
                <Tag size={10} /> Tambah
              </button>
            )}
          </div>
        </div>

      </div>

      {/* Action buttons */}
      <div className="ac-actions">
        <div className="ac-actions-row">
          <button
            className="ac-action-btn ack"
            disabled={alert.triage !== 'baru'}
            onClick={() => onTriage(alert.id_peringatan, 'dilihat')}
          >
            <CheckCircle size={12} />
            Acknowledge
          </button>
          <button
            className="ac-action-btn valid"
            disabled={isDone}
            onClick={() => onTriage(alert.id_peringatan, 'valid')}
          >
            <CheckCircle size={12} />
            Valid
          </button>
          <button
            className="ac-action-btn fp"
            disabled={isDone}
            onClick={() => onTriage(alert.id_peringatan, 'false_positive')}
          >
            <XCircle size={12} />
            False Positive
          </button>
        </div>
        <div className="ac-actions-row">
          {eskalasiConfirm ? (
            <>
              <span className="ac-eskalasi-confirm-label">
                <ArrowUpCircle size={11} /> Buat Incident?
              </span>
              <button
                className="ac-action-btn eskalasi"
                onClick={() => { onTriage(alert.id_peringatan, 'eskalasi'); setEskalasiConfirm(false) }}
              >
                <CheckCircle size={12} /> Konfirmasi
              </button>
              <button
                className="ac-action-btn ignore"
                onClick={() => setEskalasiConfirm(false)}
              >
                <XCircle size={12} /> Batal
              </button>
            </>
          ) : (
            <>
              <button
                className="ac-action-btn eskalasi"
                disabled={isDone && alert.triage !== 'dilihat' && alert.triage !== 'valid'}
                onClick={() => setEskalasiConfirm(true)}
              >
                <ArrowUpCircle size={12} />
                Escalate → Incident
              </button>
              <button
                className="ac-action-btn assign"
                disabled={isDone}
                onClick={() => onTriage(alert.id_peringatan, 'dilihat')}
                title="Assign ke operator (simulasi)"
              >
                <UserPlus size={12} />
                Assign
              </button>
              <button
                className="ac-action-btn ignore"
                disabled={alert.triage === 'diabaikan'}
                onClick={() => onTriage(alert.id_peringatan, 'diabaikan')}
              >
                <MinusCircle size={12} />
                Ignore
              </button>
            </>
          )}
        </div>
      </div>

      {/* Drill-down links */}
      <div className="ac-drilldown-row">
        <span className="ac-drill-link" title="Belum diimplementasi">
          <User size={10} /> Entity Profile
        </span>
        <span className="ac-drill-link" title="Belum diimplementasi">
          <Clock size={10} /> Timeline
        </span>
        <span className="ac-drill-link" title="Belum diimplementasi">
          <Network size={10} /> Graph
        </span>
      </div>

      {/* Live Intel Feed — streams data dari semua dataset untuk kasus ini */}
      {(() => {
        const k = kasus.find(k => k.id_kasus === alert.id_kasus)
        if (!k) return null
        return (
          <div style={{ padding: '10px 16px 14px' }}>
            <LiveIntelFeed
              idKasus={alert.id_kasus}
              kasusKota={k.kota}
              kasusProvinsi={k.provinsi}
            />
          </div>
        )
      })()}
    </div>
  )
}
