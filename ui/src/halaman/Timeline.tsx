/**
 * Timeline — H8 Kronologi Kejadian
 * 6 tipe event dalam satu sumbu waktu berurutan.
 * Menerima context navigate state { filterKasus, filterProfil } dari H3/H6/H7.
 */
import { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { createPortal } from 'react-dom'
import {
  AlertTriangle, Bell, MessageSquare, Activity, FileText,
  X, MapPin, ChevronLeft, ExternalLink, Filter, Navigation,
  ChevronDown, ChevronUp, ArrowUpRight, ArrowDownLeft,
} from 'lucide-react'
import { muatJson } from '../utils'
import { useArrowNav } from '../hooks/useArrowNav'
import type { Kasus, Peringatan, Postingan, Transaksi, Laporan, Profil, Lokasi } from '../types'
import EntityProfileModal from '../components/EntityProfileModal'
import PlatformIcon from '../components/PlatformIcon'

// ─── Types ──────────────────────────────────────────────────────────
type EventTipe = 'kasus' | 'alert' | 'postingan' | 'transaksi' | 'laporan' | 'lokasi'
type EventSeverity = 'kritis' | 'tinggi' | 'sedang' | 'rendah' | 'info'

interface TimelineEvent {
  id: string
  timestamp: string
  tipe: EventTipe
  severity: EventSeverity
  judul: string
  deskripsi: string
  id_kasus?: string
  id_profil?: string
  id_lokasi?: string
  arah?: 'kirim' | 'terima'
  id_profil_lawan?: string
  label_transaksi?: string
  metadata: Record<string, unknown>
}

// ─── Config ─────────────────────────────────────────────────────────
const TIPE_CFG: Record<EventTipe, { label: string; warna: string }> = {
  alert:     { label: 'ALERT',     warna: '#E5282A' },
  kasus:     { label: 'KASUS',     warna: '#F5A623' },
  postingan: { label: 'POSTINGAN', warna: '#378ADD' },
  transaksi: { label: 'TRANSAKSI', warna: '#4CAF50' },
  laporan:   { label: 'LAPORAN',   warna: '#9B59B6' },
  lokasi:    { label: 'LOKASI',    warna: '#17A2B8' },
}

const SEV_ORDER: EventSeverity[] = ['kritis', 'tinggi', 'sedang', 'rendah', 'info']

const SEV_CFG: Record<EventSeverity, { label: string; bg: string; dot: number }> = {
  kritis: { label: 'KRITIS', bg: '#E5282A',             dot: 12 },
  tinggi: { label: 'TINGGI', bg: '#F5A623',             dot: 10 },
  sedang: { label: 'SEDANG', bg: 'rgba(250,204,21,.85)', dot: 8  },
  rendah: { label: 'RENDAH', bg: '#4CAF50',             dot: 6  },
  info:   { label: '',       bg: 'transparent',          dot: 6  },
}

const CLUSTER_MS = 5 * 60 * 1000 // 5 menit

function TipeIcon({ tipe, size = 11 }: { tipe: EventTipe; size?: number }) {
  if (tipe === 'alert')     return <Bell size={size} />
  if (tipe === 'kasus')     return <AlertTriangle size={size} />
  if (tipe === 'postingan') return <MessageSquare size={size} />
  if (tipe === 'transaksi') return <Activity size={size} />
  if (tipe === 'lokasi')    return <Navigation size={size} />
  return <FileText size={size} />
}

// ─── Helpers ────────────────────────────────────────────────────────
function fmtTime(iso: string) {
  return new Date(iso).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })
}
function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('id-ID', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  })
}
function fmtTs(iso: string) {
  return new Date(iso).toLocaleString('id-ID', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}
function fmtRupiah(n: number) {
  return 'Rp ' + n.toLocaleString('id-ID')
}
function dayKey(iso: string) {
  return iso.slice(0, 10)
}

function worstSeverity(events: TimelineEvent[]): EventSeverity {
  return SEV_ORDER.find(s => events.some(e => e.severity === s)) ?? 'info'
}
function topTipe(events: TimelineEvent[]): EventTipe {
  const counts = new Map<EventTipe, number>()
  events.forEach(e => counts.set(e.tipe, (counts.get(e.tipe) ?? 0) + 1))
  return [...counts.entries()].sort((a, b) => b[1] - a[1])[0][0]
}

// Gap threshold auto-calc (adaptif)
function calcGapThreshold(events: TimelineEvent[]): number {
  if (events.length < 2) return 12 * 3_600_000
  const ts = events.map(e => new Date(e.timestamp).getTime()).sort((a, b) => a - b)
  const gaps = ts.slice(1).map((t, i) => t - ts[i]).filter(g => g > 0)
  if (!gaps.length) return 12 * 3_600_000
  const avg = gaps.reduce((a, b) => a + b, 0) / gaps.length
  return Math.max(avg * 3, 6 * 3_600_000) // min 6 jam
}

// ─── Normalisasi ─────────────────────────────────────────────────────
function normalizeToEvents(
  kasus: Kasus[],
  peringatan: Peringatan[],
  postingan: Postingan[],
  transaksi: Transaksi[],
  laporan: Laporan[],
  lokasi: Lokasi[],
  filterProfilIds: string[],
  showLokasi: boolean,
): TimelineEvent[] {
  const ev: TimelineEvent[] = []

  kasus.forEach(k => ev.push({
    id: `kas-${k.id_kasus}`,
    timestamp: k.waktu_insiden,
    tipe: 'kasus',
    severity: 'sedang',
    judul: k.judul,
    deskripsi: `${k.tipe_kasus} · ${k.kota}`,
    id_kasus: k.id_kasus,
    metadata: k as unknown as Record<string, unknown>,
  }))

  peringatan.forEach(p => {
    if (!p.waktu) return
    const sev: EventSeverity =
      p.tingkat_keparahan === 'tinggi' ? 'kritis' :
      p.tingkat_keparahan === 'menengah' ? 'tinggi' : 'sedang'
    ev.push({
      id: `per-${p.id_peringatan}`,
      timestamp: p.waktu,
      tipe: 'alert',
      severity: sev,
      judul: p.deskripsi,
      deskripsi: p.tipe_sinyal,
      id_kasus: p.id_kasus,
      metadata: p as unknown as Record<string, unknown>,
    })
  })

  postingan.forEach(ps => ev.push({
    id: `pos-${ps.id_posting}`,
    timestamp: ps.timestamp,
    tipe: 'postingan',
    severity: 'info',
    judul: ps.konten.length > 70 ? ps.konten.slice(0, 70) + '…' : ps.konten,
    deskripsi: `${ps.platform} · ${ps.kota}`,
    id_profil: ps.id_profil,
    metadata: ps as unknown as Record<string, unknown>,
  }))

  // Transaksi dua sisi: sumber DAN tujuan ketika filter profil aktif
  if (filterProfilIds.length > 0) {
    transaksi.forEach(t => {
      const isSumber = filterProfilIds.includes(t.id_profil_sumber)
      const isTujuan = filterProfilIds.includes(t.id_profil_tujuan)
      if (isSumber) {
        ev.push({
          id: `tx-${t.id_transaksi}-kirim`,
          timestamp: t.timestamp, tipe: 'transaksi', severity: 'sedang',
          judul: `${fmtRupiah(t.jumlah_idr)} via ${t.kanal}`,
          deskripsi: t.petunjuk_tujuan,
          id_kasus: t.id_kasus, id_profil: t.id_profil_sumber,
          id_profil_lawan: t.id_profil_tujuan,
          arah: 'kirim', label_transaksi: 'Mengirim ke __LAWAN__',
          metadata: t as unknown as Record<string, unknown>,
        })
      }
      if (isTujuan && !isSumber) {
        ev.push({
          id: `tx-${t.id_transaksi}-terima`,
          timestamp: t.timestamp, tipe: 'transaksi', severity: 'sedang',
          judul: `${fmtRupiah(t.jumlah_idr)} via ${t.kanal}`,
          deskripsi: t.petunjuk_tujuan,
          id_kasus: t.id_kasus, id_profil: t.id_profil_tujuan,
          id_profil_lawan: t.id_profil_sumber,
          arah: 'terima', label_transaksi: 'Menerima dari __LAWAN__',
          metadata: t as unknown as Record<string, unknown>,
        })
      }
    })
  } else {
    transaksi.forEach(t => ev.push({
      id: `tx-${t.id_transaksi}`,
      timestamp: t.timestamp, tipe: 'transaksi', severity: 'sedang',
      judul: `${fmtRupiah(t.jumlah_idr)} via ${t.kanal}`,
      deskripsi: t.petunjuk_tujuan,
      id_kasus: t.id_kasus, id_profil: t.id_profil_sumber,
      id_profil_lawan: t.id_profil_tujuan,
      metadata: t as unknown as Record<string, unknown>,
    }))
  }

  laporan.forEach(l => ev.push({
    id: `lap-${l.id_laporan}`,
    timestamp: l.digenerate_pada,
    tipe: 'laporan', severity: 'info',
    judul: l.judul,
    deskripsi: l.ringkasan.length > 80 ? l.ringkasan.slice(0, 80) + '…' : l.ringkasan,
    id_kasus: l.id_kasus,
    metadata: l as unknown as Record<string, unknown>,
  }))

  if (showLokasi) {
    lokasi.forEach(loc => {
      if (!loc.diamati_pada) return
      ev.push({
        id: `lok-${loc.id_lokasi}`,
        timestamp: loc.diamati_pada, tipe: 'lokasi', severity: 'info',
        judul: loc.label || `${loc.tipe_lokasi} · ${loc.kota}`,
        deskripsi: `${loc.kota}, ${loc.provinsi}`,
        id_profil: loc.id_profil, id_lokasi: loc.id_lokasi,
        metadata: loc as unknown as Record<string, unknown>,
      })
    })
  }

  return ev.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
}

// ─── EventCluster ───────────────────────────────────────────────────
function EventCluster({
  events, onExpand, profilMap,
}: {
  events: TimelineEvent[]
  onExpand: () => void
  profilMap: Map<string, Profil>
}) {
  const ws  = worstSeverity(events)
  const tp  = topTipe(events)
  const bg  = SEV_CFG[ws].bg !== 'transparent' ? SEV_CFG[ws].bg : TIPE_CFG[tp].warna

  return (
    <div className="tl-cluster" onClick={onExpand}>
      <div className="tl-cluster-dot" style={{ background: bg }}>
        <span style={{ color: '#fff', fontSize: 9, fontWeight: 700 }}>{events.length}</span>
      </div>
      <div className="tl-cluster-body">
        <div className="tl-cluster-title">
          <TipeIcon tipe={tp} size={10} />
          <span style={{ color: bg, fontWeight: 600 }}>{events.length} event</span>
          <span className="tl-cluster-sep">·</span>
          <span style={{ color: bg }}>{ws}</span>
          <span className="tl-cluster-time">{fmtTime(events[0].timestamp)} – {fmtTime(events[events.length - 1].timestamp)}</span>
        </div>
        <div className="tl-cluster-names">
          {events.slice(0, 3).map(e => {
            const nama = e.id_profil ? profilMap.get(e.id_profil)?.nama_tampil : undefined
            return nama ? <span key={e.id} className="tl-cluster-tag">{nama}</span> : null
          })}
        </div>
      </div>
      <ChevronDown size={11} style={{ color: 'rgba(243,234,234,.3)', marginLeft: 'auto', flexShrink: 0 }} />
    </div>
  )
}

// ─── EventNode ──────────────────────────────────────────────────────
function EventNode({
  event, selected, onClick, kasusMap, profilMap, isLatestKritis,
}: {
  event: TimelineEvent
  selected: boolean
  onClick: () => void
  kasusMap: Map<string, Kasus>
  profilMap: Map<string, Profil>
  isLatestKritis: boolean
}) {
  const cfg   = TIPE_CFG[event.tipe]
  const sev   = SEV_CFG[event.severity]
  const pulse = isLatestKritis && event.severity === 'kritis'
  const subLabel =
    event.id_profil ? profilMap.get(event.id_profil)?.nama_lengkap :
    event.id_kasus  ? kasusMap.get(event.id_kasus)?.judul :
    undefined
  const arahIcon = event.arah === 'kirim'
    ? <ArrowUpRight size={9} style={{ color: '#F5A623' }} />
    : event.arah === 'terima'
      ? <ArrowDownLeft size={9} style={{ color: '#4CAF50' }} />
      : null

  return (
    <div
      className={`tl-event-node${selected ? ' aktif' : ''}`}
      style={{ borderLeftColor: cfg.warna }}
      onClick={onClick}
    >
      {/* Dot severity */}
      <div className="tl-event-dot-wrap">
        <div
          className={`tl-event-dot${pulse ? ' pulse' : ''}`}
          style={{
            width: sev.dot, height: sev.dot,
            background: cfg.warna,
            opacity: event.severity === 'info' ? 0.45 : event.severity === 'rendah' ? 0.6 : event.severity === 'sedang' ? 0.82 : 1,
            boxShadow: event.severity === 'kritis' ? `0 0 0 2px ${cfg.warna}44` : 'none',
          }}
        />
      </div>
      <div className="tl-event-body">
        <div className="tl-event-meta">
          <span className="tl-event-icon" style={{ color: cfg.warna }}>
            <TipeIcon tipe={event.tipe} />
          </span>
          <span className="tl-event-tipe" style={{ color: cfg.warna }}>{cfg.label}</span>
          {arahIcon}
          <span className="tl-event-time">
            {fmtTime(event.timestamp)}
            <span className="tl-event-date">
              {' '}{new Date(event.timestamp).toLocaleDateString('id-ID', { day: 'numeric', month: 'short' })}
            </span>
          </span>
          {sev.label && (
            <span className="tl-severity-badge" style={{ background: sev.bg }}>{sev.label}</span>
          )}
        </div>
        <div className="tl-event-judul">{event.judul}</div>
        {subLabel && <div className="tl-event-sub">{subLabel}</div>}
      </div>
    </div>
  )
}

// ─── EventDetailCard ────────────────────────────────────────────────
function EventDetailCard({
  event, kasusMap, profilMap, onClose, onOpenProfil,
}: {
  event: TimelineEvent
  kasusMap: Map<string, Kasus>
  profilMap: Map<string, Profil>
  onClose: () => void
  onOpenProfil: (id: string) => void
}) {
  const navigate = useNavigate()
  const cfg = TIPE_CFG[event.tipe]
  const kasusItem  = event.id_kasus  ? kasusMap.get(event.id_kasus)  : undefined
  const profilItem = event.id_profil ? profilMap.get(event.id_profil) : undefined

  const alertData = event.tipe === 'alert'     ? event.metadata as unknown as Peringatan : null
  const postData  = event.tipe === 'postingan' ? event.metadata as unknown as Postingan  : null
  const txData    = event.tipe === 'transaksi' ? event.metadata as unknown as Transaksi  : null
  const lapData   = event.tipe === 'laporan'   ? event.metadata as unknown as Laporan    : null
  const kasusData = event.tipe === 'kasus'     ? event.metadata as unknown as Kasus      : null
  const lokData   = event.tipe === 'lokasi'    ? event.metadata as unknown as Lokasi     : null

  const lawanNama = event.id_profil_lawan ? profilMap.get(event.id_profil_lawan)?.nama_lengkap : undefined
  const labelTx = event.label_transaksi
    ? event.label_transaksi.replace('__LAWAN__', lawanNama ?? (event.id_profil_lawan ? event.id_profil_lawan.slice(0, 12) + '…' : '?'))
    : undefined

  return createPortal(
    <>
      <div className="tl-detail-backdrop" onClick={onClose} />
      <div className="tl-detail-card">
        {/* Header */}
        <div className="tl-detail-header" style={{ borderBottomColor: `${cfg.warna}30` }}>
          <div className="tl-detail-title-row">
            <span className="tl-detail-icon" style={{ color: cfg.warna }}>
              <TipeIcon tipe={event.tipe} size={13} />
            </span>
            <span className="tl-detail-judul">{event.judul}</span>
            <button className="tl-detail-close" onClick={onClose}><X size={12} /></button>
          </div>
          <div className="tl-detail-ts">{fmtTs(event.timestamp)}</div>
          {SEV_CFG[event.severity].label && (
            <span className="tl-severity-badge" style={{ background: SEV_CFG[event.severity].bg, marginTop: 5, display: 'inline-block' }}>
              {SEV_CFG[event.severity].label}
            </span>
          )}
        </div>

        {/* Body */}
        <div className="tl-detail-body">

          {/* ALERT */}
          {alertData && (
          <>
            <div className="tl-detail-section">
              <div className="tl-detail-row">
                <span className="tl-detail-lbl">Sinyal</span>
                <span>{alertData.tipe_sinyal}</span>
              </div>
              <div className="tl-detail-row">
                <span className="tl-detail-lbl">Deskripsi</span>
                <span>{alertData.deskripsi}</span>
              </div>
              {alertData.pesan && (
                <div className="tl-detail-row">
                  <span className="tl-detail-lbl">Pesan</span>
                  <span>{alertData.pesan}</span>
                </div>
              )}
            </div>
            <div className="tl-detail-section">
              <div className="tl-detail-lbl" style={{ marginBottom: 5 }}>Kepercayaan</div>
              <div className="tl-conf-bar-wrap">
                <div className="tl-conf-bar" style={{ width: `${alertData.kepercayaan * 100}%`, background: cfg.warna }} />
              </div>
              <div style={{ fontSize: 10, color: 'rgba(243,234,234,.35)', marginTop: 3 }}>
                {Math.round(alertData.kepercayaan * 100)}%
              </div>
            </div>
          </>
        )}

        {/* KASUS */}
        {kasusData && (
          <div className="tl-detail-section">
            <div className="tl-detail-row"><span className="tl-detail-lbl">Tipe</span><span>{kasusData.tipe_kasus}</span></div>
            <div className="tl-detail-row">
              <span className="tl-detail-lbl">Lokasi</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <MapPin size={9} /> {kasusData.kota}, {kasusData.provinsi}
              </span>
            </div>
            <div className="tl-detail-row"><span className="tl-detail-lbl">Status</span><span style={{ textTransform: 'capitalize' }}>{kasusData.status}</span></div>
            <div className="tl-detail-row"><span className="tl-detail-lbl">Aktor</span><span>{kasusData.jumlah_aktor}</span></div>
          </div>
        )}

        {/* POSTINGAN */}
        {postData && (
          <>
            <div className="tl-detail-section">
              <div className="tl-detail-platform">
                <PlatformIcon platform={postData.platform} size={13} showLabel />
                <span className="tl-detail-kota"><MapPin size={9} />{postData.kota}</span>
              </div>
              <div className="tl-detail-konten">{postData.konten}</div>
            </div>
            {postData.hashtag.length > 0 && (
              <div className="tl-detail-section tl-hashtags">
                {postData.hashtag.slice(0, 6).map(h => (
                  <span key={h} className="tl-hashtag">{h}</span>
                ))}
              </div>
            )}
            <div className="tl-detail-section tl-detail-eng">
              <span>❤ {postData.engagement.suka}</span>
              <span>💬 {postData.engagement.komentar}</span>
              <span>🔁 {postData.engagement.bagikan}</span>
            </div>
          </>
        )}

          {/* TRANSAKSI */}
          {txData && (
            <div className="tl-detail-section">
              <div className="tl-detail-nominal">{fmtRupiah(txData.jumlah_idr)}</div>
              {labelTx && (
                <div className="tl-detail-row">
                  <span className="tl-detail-lbl">Arah</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    {event.arah === 'kirim'
                      ? <ArrowUpRight size={11} style={{ color: '#F5A623' }} />
                      : <ArrowDownLeft size={11} style={{ color: '#4CAF50' }} />}
                    {labelTx}
                  </span>
                </div>
              )}
              <div className="tl-detail-row"><span className="tl-detail-lbl">Kanal</span><span>{txData.kanal}</span></div>
              <div className="tl-detail-row">
                <span className="tl-detail-lbl">Sumber</span>
                <span>{profilMap.get(txData.id_profil_sumber)?.nama_lengkap ?? txData.id_profil_sumber.slice(0, 14) + '…'}</span>
              </div>
              <div className="tl-detail-row">
                <span className="tl-detail-lbl">Tujuan</span>
                <span>{profilMap.get(txData.id_profil_tujuan)?.nama_lengkap ?? txData.id_profil_tujuan.slice(0, 14) + '…'}</span>
              </div>
              {txData.petunjuk_tujuan && (
                <div className="tl-detail-row"><span className="tl-detail-lbl">Petunjuk</span><span>{txData.petunjuk_tujuan}</span></div>
              )}
              {txData.referensi && (
                <div className="tl-detail-row">
                  <span className="tl-detail-lbl">Ref</span>
                  <span style={{ fontFamily: 'monospace', fontSize: 10 }}>{txData.referensi}</span>
                </div>
              )}
            </div>
          )}

          {/* LAPORAN */}
          {lapData && (
            <>
              <div className="tl-detail-section">
                <div className="tl-detail-lbl" style={{ marginBottom: 5 }}>Ringkasan</div>
                <div style={{ fontSize: 11.5, color: 'rgba(243,234,234,.65)', lineHeight: 1.5 }}>
                  {lapData.ringkasan}
                </div>
              </div>
              {lapData.temuan.length > 0 && (
                <div className="tl-detail-section">
                  <div className="tl-detail-lbl" style={{ marginBottom: 5 }}>Temuan</div>
                  <ul className="tl-detail-list">
                    {lapData.temuan.slice(0, 3).map((t, i) => <li key={i}>{t}</li>)}
                    {lapData.temuan.length > 3 && (
                      <li style={{ opacity: .35 }}>+{lapData.temuan.length - 3} temuan lainnya</li>
                    )}
                  </ul>
                </div>
              )}
              {lapData.rekomendasi.length > 0 && (
                <div className="tl-detail-section">
                  <div className="tl-detail-lbl" style={{ marginBottom: 5 }}>Rekomendasi</div>
                  <ul className="tl-detail-list">
                    {lapData.rekomendasi.slice(0, 2).map((r, i) => <li key={i}>{r}</li>)}
                  </ul>
                </div>
              )}
            </>
          )}

          {/* LOKASI */}
          {lokData && (
            <div className="tl-detail-section">
              <div className="tl-detail-row"><span className="tl-detail-lbl">Label</span><span>{lokData.label}</span></div>
              <div className="tl-detail-row"><span className="tl-detail-lbl">Tipe</span><span style={{ textTransform: 'capitalize' }}>{lokData.tipe_lokasi}</span></div>
              <div className="tl-detail-row">
                <span className="tl-detail-lbl">Koordinat</span>
                <span style={{ fontFamily: 'monospace', fontSize: 10 }}>{lokData.latitude.toFixed(5)}, {lokData.longitude.toFixed(5)}</span>
              </div>
              <div className="tl-detail-row"><span className="tl-detail-lbl">Kota</span><span>{lokData.kota}, {lokData.provinsi}</span></div>
              <div className="tl-detail-row"><span className="tl-detail-lbl">Kepercayaan</span><span>{Math.round(lokData.kepercayaan * 100)}%</span></div>
            </div>
          )}

          {/* Kasus terkait (bukan event kasus) */}
          {kasusItem && event.tipe !== 'kasus' && (
            <div className="tl-detail-section tl-detail-kasus-ref">
              <span className="tl-detail-lbl" style={{ flexShrink: 0 }}>Kasus</span>
              <span>{kasusItem.judul}</span>
            </div>
          )}
        </div>

        {/* Action bar */}
        <div className="tl-detail-actions">
          <button
            className={`tl-action-btn${!event.id_kasus ? ' disabled' : ''}`}
            disabled={!event.id_kasus}
            onClick={() => navigate('/incident-queue', { state: { focusKasus: event.id_kasus } })}
            title={event.id_kasus ? 'Buka di Incident Queue' : 'Tidak ada kasus terkait'}
          >
            Insiden
          </button>
          <button
            className={`tl-action-btn${!event.id_profil && !profilItem ? ' disabled' : ''}`}
            disabled={!event.id_profil && !profilItem}
            onClick={() => {
              const id = event.id_profil ?? profilItem?.id_profil
              if (id) onOpenProfil(id)
            }}
            title="Lihat profil entitas"
          >
            <ExternalLink size={10} /> Profil
          </button>
          <button
            className="tl-action-btn"
            onClick={() => navigate('/map-intelligence', { state: { focusLokasi: event.id_lokasi } })}
            title="Lihat di Map Intelligence"
          >
            <MapPin size={10} /> Peta
          </button>
          <button className="tl-action-btn" disabled title="Tersedia di H10 — Konten Bukti" style={{ opacity: .25 }}>
            Konten
          </button>
          <button className="tl-action-btn" disabled title="Tersedia di H15 — Briefing & Pelaporan" style={{ opacity: .25 }}>
            Briefing
          </button>
        </div>
      </div>
    </>,
    document.body
  )
}

// ─── Komponen Utama ──────────────────────────────────────────────────
export default function Timeline() {
  useArrowNav()
  const location = useLocation()
  const navigate  = useNavigate()
  const trackRef  = useRef<HTMLDivElement>(null)

  // ── Data ──
  const [kasusList,  setKasusList]  = useState<Kasus[]>([])
  const [lokasiList, setLokasiList] = useState<Lokasi[]>([])
  const [profilList, setProfilList] = useState<Profil[]>([])
  const [rawEvents,  setRawEvents]  = useState<TimelineEvent[]>([])
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState<string | null>(null)
  // Cache raw JSON so re-normalization doesn't re-fetch
  const rawDataRef = useRef<{ kd: Kasus[], pd: Peringatan[], psd: Postingan[], txd: Transaksi[], ld: Laporan[], lokd: Lokasi[] } | null>(null)

  // ── Filter ──
  const [filterTipe,  setFilterTipe]  = useState<Set<EventTipe>>(new Set<EventTipe>(['kasus', 'alert', 'postingan', 'transaksi', 'laporan']))
  const [showLokasi,  setShowLokasi]  = useState(false)
  const [filterKasus, setFilterKasus] = useState<Set<string>>(new Set())
  const [filterProfil,setFilterProfil]= useState<Set<string>>(new Set())
  const [preset,      setPreset]      = useState<'24j'|'7h'|'30h'|'semua'>('semua')
  const [gapMode,     setGapMode]     = useState<'auto'|'manual'>('auto')
  const [gapJam,      setGapJam]      = useState(12)

  // ── View ──
  const [selectedEvent,      setSelectedEvent]      = useState<TimelineEvent | null>(null)
  const [fullscreenProfilId, setFullscreenProfilId] = useState<string | null>(null)
  const [expandedClusters,   setExpandedClusters]   = useState<Set<string>>(new Set())
  const [zoomLevel,          setZoomLevel]          = useState<1|2|3|4>(1)

  // ── Load data ──
  useEffect(() => {
    async function muat() {
      try {
        const [kd, pd, psd, txd, ld, profilData, lokd] = await Promise.all([
          muatJson<Kasus[]>('/data/kasus.json').catch(()     => [] as Kasus[]),
          muatJson<Peringatan[]>('/data/peringatan.json').catch(() => [] as Peringatan[]),
          muatJson<Postingan[]>('/data/postingan.json').catch(()  => [] as Postingan[]),
          muatJson<Transaksi[]>('/data/transaksi.json').catch(()  => [] as Transaksi[]),
          muatJson<Laporan[]>('/data/laporan.json').catch(()      => [] as Laporan[]),
          muatJson<Profil[]>('/data/profil.json').catch(()        => [] as Profil[]),
          muatJson<Lokasi[]>('/data/lokasi.json').catch(()        => [] as Lokasi[]),
        ])
        rawDataRef.current = { kd, pd, psd, txd, ld, lokd }
        setKasusList(kd)
        setProfilList(profilData)
        setLokasiList(lokd)
        setRawEvents(normalizeToEvents(kd, pd, psd, txd, ld, lokd, [], false))
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Gagal memuat data')
      } finally {
        setLoading(false)
      }
    }
    muat()
  }, [])

  // Regenerate events (cached) saat filterProfil/showLokasi berubah
  useEffect(() => {
    if (!rawDataRef.current) return
    const { kd, pd, psd, txd, ld, lokd } = rawDataRef.current
    setRawEvents(normalizeToEvents(kd, pd, psd, txd, ld, lokd, Array.from(filterProfil), showLokasi))
  }, [filterProfil, showLokasi])

  // ── Terima context dari halaman lain ──
  useEffect(() => {
    const state = location.state as { filterKasus?: string; filterProfil?: string } | null
    if (!state) return
    if (state.filterKasus)  setFilterKasus(new Set([state.filterKasus]))
    if (state.filterProfil) setFilterProfil(new Set([state.filterProfil]))
  }, []) // eslint-disable-line

  // ── Ctrl+scroll = zoom ──
  useEffect(() => {
    function handler(e: WheelEvent) {
      if (!e.ctrlKey) return
      e.preventDefault()
      setZoomLevel(prev => {
        if (e.deltaY < 0) return Math.min(prev + 1, 4) as 1|2|3|4
        return Math.max(prev - 1, 1) as 1|2|3|4
      })
    }
    window.addEventListener('wheel', handler, { passive: false })
    return () => window.removeEventListener('wheel', handler)
  }, [])

  // ── Maps ──
  const kasusMap  = useMemo(() => new Map(kasusList.map(k  => [k.id_kasus, k])),  [kasusList])
  const profilMap = useMemo(() => new Map(profilList.map(p => [p.id_profil, p])), [profilList])

  // ── Filter events ──
  const presetMs =
    preset === '24j' ? 24 * 3_600_000 :
    preset === '7h'  ? 7  * 86_400_000 :
    preset === '30h' ? 30 * 86_400_000 : null

  const filteredEvents = useMemo(() => {
    const now = Date.now()
    const activeTipe = new Set(filterTipe)
    if (showLokasi) activeTipe.add('lokasi')
    return rawEvents.filter(ev => {
      if (!activeTipe.has(ev.tipe)) return false
      if (filterKasus.size > 0 && (!ev.id_kasus || !filterKasus.has(ev.id_kasus))) return false
      if (filterProfil.size > 0 && (!ev.id_profil || !filterProfil.has(ev.id_profil))) return false
      if (presetMs && now - new Date(ev.timestamp).getTime() > presetMs) return false
      return true
    })
  }, [rawEvents, filterTipe, filterKasus, filterProfil, presetMs, showLokasi])

  // ── Gap threshold ──
  const gapMs = useMemo(() => {
    if (gapMode === 'manual') return gapJam * 3_600_000
    return calcGapThreshold(filteredEvents)
  }, [filteredEvents, gapMode, gapJam])

  // ── Latest kritis id (untuk pulse) ──
  const latestKritisId = useMemo(() => {
    const kritis = filteredEvents.filter(e => e.severity === 'kritis')
    return kritis.length > 0 ? kritis[kritis.length - 1].id : null
  }, [filteredEvents])

  // ── Build render items ──
  type RenderItem =
    | { kind: 'header';  key: string; label: string }
    | { kind: 'event';   event: TimelineEvent }
    | { kind: 'cluster'; key: string; events: TimelineEvent[] }
    | { kind: 'gap';     key: string; hours: number }

  const renderItems = useMemo((): RenderItem[] => {
    const items: RenderItem[] = []
    let lastDay = ''
    let lastTs  = 0
    let i = 0
    while (i < filteredEvents.length) {
      const ev = filteredEvents[i]
      const ts = new Date(ev.timestamp).getTime()
      if (lastTs > 0 && ts - lastTs > gapMs) {
        items.push({ kind: 'gap', key: `gap-${ts}`, hours: Math.round((ts - lastTs) / 3_600_000) })
      }
      const day = dayKey(ev.timestamp)
      if (day !== lastDay) {
        items.push({ kind: 'header', key: `hdr-${day}`, label: fmtDate(ev.timestamp) })
        lastDay = day
      }
      // Cluster detection
      const clusterEnd = ts + CLUSTER_MS
      const cluster: TimelineEvent[] = [ev]
      let j = i + 1
      while (j < filteredEvents.length) {
        const nextTs = new Date(filteredEvents[j].timestamp).getTime()
        if (nextTs > clusterEnd) break
        cluster.push(filteredEvents[j])
        j++
      }
      const clusterKey = `cluster-${ts}`
      if (cluster.length >= 3 && !expandedClusters.has(clusterKey)) {
        items.push({ kind: 'cluster', key: clusterKey, events: cluster })
        lastTs = new Date(cluster[cluster.length - 1].timestamp).getTime()
        i = j
      } else {
        items.push({ kind: 'event', event: ev })
        lastTs = ts
        i++
      }
    }
    return items
  }, [filteredEvents, gapMs, expandedClusters])

  // ── Density bar ──
  const densityData = useMemo(() => {
    const counts = new Map<string, number>()
    filteredEvents.forEach(ev => {
      const d = dayKey(ev.timestamp)
      counts.set(d, (counts.get(d) ?? 0) + 1)
    })
    const entries = Array.from(counts.entries()).sort()
    const max = Math.max(...entries.map(([, v]) => v), 1)
    return entries.map(([day, count]) => ({ day, count, pct: count / max }))
  }, [filteredEvents])

  // Scroll ke hari saat density bar diklik
  const scrollToDay = useCallback((day: string) => {
    if (!trackRef.current) return
    const hdrs = trackRef.current.querySelectorAll<HTMLElement>('[data-day]')
    for (const el of hdrs) {
      if (el.dataset.day === day) { el.scrollIntoView({ behavior: 'smooth', block: 'start' }); break }
    }
  }, [])

  // ── Summary ──
  const tipeAktif   = useMemo(() => new Set(filteredEvents.map(e => e.tipe)).size, [filteredEvents])
  const rentangHari = useMemo(() => {
    if (filteredEvents.length < 2) return 0
    const t0 = new Date(filteredEvents[0].timestamp).getTime()
    const t1 = new Date(filteredEvents[filteredEvents.length - 1].timestamp).getTime()
    return Math.ceil((t1 - t0) / 86_400_000)
  }, [filteredEvents])

  // ── Helpers filter ──
  const toggleTipe   = (t: EventTipe) => setFilterTipe(prev => { const n = new Set(prev); n.has(t) ? n.delete(t) : n.add(t); return n })
  const toggleKasus  = (id: string)   => setFilterKasus(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n })
  const toggleProfil = (id: string)   => setFilterProfil(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n })

  const zoomLabel = ['Overview (1 hari)', 'Sedang (6 jam)', 'Detail (1 jam)', 'Mikro (15 mnt)'][zoomLevel - 1]

  // ── Loading / Error ──
  if (loading) return (
    <div className="halaman-tl loading-state">
      <div className="la-spinner" />
      <p className="la-loading-text">Memuat kronologi…</p>
    </div>
  )
  if (error) return (
    <div className="halaman-tl loading-state">
      <AlertTriangle size={32} style={{ color: '#E53E3E' }} />
      <p className="la-loading-text">{error}</p>
    </div>
  )

  return (
    <div className="halaman-tl">

      {/* ── Topbar ── */}
      <div className="tl-topbar">
        <div className="tl-topbar-left">
          <span className="tl-topbar-title">Timeline</span>
          <span className="tl-summary-pill">
            {filteredEvents.length} event
            {tipeAktif > 0 && ` · ${tipeAktif} tipe`}
            {rentangHari > 0 && ` · ${rentangHari} hari`}
          </span>
        </div>

        {/* Mode pills */}
        <div className="tl-mode-btns">
          <button
            className={`tl-mode-btn ${filterKasus.size === 0 && filterProfil.size === 0 ? 'aktif' : ''}`}
            onClick={() => { setFilterKasus(new Set()); setFilterProfil(new Set()) }}
          >
            Semua
          </button>
          <button
            className={`tl-mode-btn ${filterKasus.size > 0 ? 'aktif' : ''}`}
            title="Filter per kasus dipilih di panel kiri"
          >
            Per Kasus{filterKasus.size > 0 ? ` (${filterKasus.size})` : ''}
          </button>
          <button
            className={`tl-mode-btn ${filterProfil.size > 0 ? 'aktif' : ''}`}
            title="Filter per profil dipilih di panel kiri"
          >
            Per Profil{filterProfil.size > 0 ? ` (${filterProfil.size})` : ''}
          </button>
        </div>

        {/* Zoom control */}
        <div className="tl-zoom-ctrl">
          <button
            className="tl-zoom-btn"
            disabled={zoomLevel <= 1}
            onClick={() => setZoomLevel(prev => Math.max(prev - 1, 1) as 1|2|3|4)}
          >–</button>
          <span className="tl-zoom-label" title="Ctrl+Scroll untuk zoom">{zoomLabel}</span>
          <button
            className="tl-zoom-btn"
            disabled={zoomLevel >= 4}
            onClick={() => setZoomLevel(prev => Math.min(prev + 1, 4) as 1|2|3|4)}
          >+</button>
        </div>
      </div>

      {/* ── Body ── */}
      <div className="tl-body">

        {/* Filter panel */}
        <div className="tl-filter-panel">

          {/* Tipe event */}
          <div className="tl-filter-section">
            <div className="tl-filter-label"><Filter size={9} /> Tipe Event</div>
            {(['alert', 'kasus', 'postingan', 'transaksi', 'laporan'] as EventTipe[]).map(t => (
              <label key={t} className="tl-filter-check">
                <input type="checkbox" checked={filterTipe.has(t)} onChange={() => toggleTipe(t)} />
                <span className="tl-check-dot" style={{ background: TIPE_CFG[t].warna }} />
                <span style={{ color: filterTipe.has(t) ? TIPE_CFG[t].warna : 'rgba(243,234,234,.35)' }}>
                  {TIPE_CFG[t].label}
                </span>
                <span className="tl-check-count">{rawEvents.filter(e => e.tipe === t).length}</span>
              </label>
            ))}
            {/* Lokasi — default OFF */}
            <label className="tl-filter-check">
              <input type="checkbox" checked={showLokasi} onChange={() => setShowLokasi(v => !v)} />
              <span className="tl-check-dot" style={{ background: TIPE_CFG.lokasi.warna, opacity: showLokasi ? 1 : 0.35 }} />
              <span style={{ color: showLokasi ? TIPE_CFG.lokasi.warna : 'rgba(243,234,234,.25)' }}>
                LOKASI <span style={{ fontSize: 8, opacity: .5 }}>opsional</span>
              </span>
              <span className="tl-check-count">{lokasiList.length}</span>
            </label>
          </div>

          {/* Filter kasus */}
          <div className="tl-filter-section">
            <div className="tl-filter-label">Kasus</div>
            {kasusList.map(k => (
              <label key={k.id_kasus} className="tl-filter-check">
                <input type="checkbox" checked={filterKasus.has(k.id_kasus)} onChange={() => toggleKasus(k.id_kasus)} />
                <span className="tl-check-dot" style={{ background: filterKasus.has(k.id_kasus) ? '#F5A623' : 'rgba(243,234,234,.15)' }} />
                <span className={filterKasus.has(k.id_kasus) ? 'tl-check-aktif' : ''}>
                  {k.judul.length > 22 ? k.judul.slice(0, 22) + '…' : k.judul}
                </span>
              </label>
            ))}
            {filterKasus.size > 0 && (
              <button className="tl-clear-btn" onClick={() => setFilterKasus(new Set())}>× Hapus filter kasus</button>
            )}
          </div>

          {/* Filter profil */}
          <div className="tl-filter-section">
            <div className="tl-filter-label">Profil</div>
            <div className="tl-profil-select">
              {profilList.slice(0, 20).map(p => (
                <button
                  key={p.id_profil}
                  className={`tl-profil-chip${filterProfil.has(p.id_profil) ? ' aktif' : ''}`}
                  onClick={() => toggleProfil(p.id_profil)}
                >
                  <span className="tl-check-dot" style={{ background: filterProfil.has(p.id_profil) ? '#378ADD' : 'rgba(243,234,234,.1)' }} />
                  {p.nama_tampil || p.nama_lengkap.split(' ')[0]}
                </button>
              ))}
            </div>
            {filterProfil.size > 0 && (
              <button className="tl-clear-btn" onClick={() => setFilterProfil(new Set())}>× Hapus filter profil</button>
            )}
          </div>

          {/* Preset waktu */}
          <div className="tl-filter-section">
            <div className="tl-filter-label">Rentang Waktu</div>
            <div className="tl-preset-btns">
              {(['24j', '7h', '30h', 'semua'] as const).map(p => (
                <button key={p} className={`tl-preset-btn${preset === p ? ' aktif' : ''}`} onClick={() => setPreset(p)}>
                  {p === '24j' ? '24J' : p === '7h' ? '7H' : p === '30h' ? '30H' : 'Semua'}
                </button>
              ))}
            </div>
          </div>

          {/* Gap control */}
          <div className="tl-filter-section">
            <div className="tl-filter-label">Gap Kontrol</div>
            <div style={{ display: 'flex', gap: 4, marginBottom: 4 }}>
              <button className={`tl-preset-btn${gapMode === 'auto' ? ' aktif' : ''}`} onClick={() => setGapMode('auto')}>Auto</button>
              <button className={`tl-preset-btn${gapMode === 'manual' ? ' aktif' : ''}`} onClick={() => setGapMode('manual')}>Manual</button>
            </div>
            {gapMode === 'manual' && (
              <div className="tl-gap-slider-wrap">
                <input type="range" min={1} max={48} value={gapJam} onChange={e => setGapJam(Number(e.target.value))} className="tl-gap-slider" />
                <span className="tl-gap-val">{gapJam} jam</span>
              </div>
            )}
            {gapMode === 'auto' && (
              <span style={{ fontSize: 9, color: 'rgba(243,234,234,.2)' }}>Threshold: ~{Math.round(gapMs / 3_600_000)} jam</span>
            )}
          </div>

          {/* Density mini */}
          {densityData.length > 0 && (
            <div className="tl-filter-section">
              <div className="tl-filter-label">Distribusi per Hari</div>
              <div className="tl-density-mini">
                {densityData.map(d => (
                  <div
                    key={d.day}
                    className="tl-density-mini-bar"
                    style={{ height: `${Math.max(d.pct * 100, 8)}%`, cursor: 'pointer' }}
                    title={`${d.day}: ${d.count} event`}
                    onClick={() => scrollToDay(d.day)}
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Canvas */}
        <div className="tl-canvas">

          {/* Density bar sticky */}
          {densityData.length > 1 && (
            <div className="tl-density-bar">
              {densityData.map(d => (
                <div
                  key={d.day}
                  className="tl-density-seg"
                  style={{ flex: 1, height: `${Math.max(d.pct * 100, 8)}%`, cursor: 'pointer' }}
                  title={`${d.day}: ${d.count} event — klik untuk navigasi`}
                  onClick={() => scrollToDay(d.day)}
                />
              ))}
            </div>
          )}

          {/* Event track */}
          <div className="tl-event-track" ref={trackRef}>
            {filteredEvents.length === 0 && (
              <div className="tl-empty">
                <Activity size={28} style={{ opacity: .18 }} />
                <span>Tidak ada event sesuai filter yang dipilih.</span>
                {(filterKasus.size > 0 || filterProfil.size > 0 || preset !== 'semua') && (
                  <button
                    className="tl-clear-btn"
                    style={{ marginTop: 4 }}
                    onClick={() => { setFilterKasus(new Set()); setFilterProfil(new Set()); setPreset('semua') }}
                  >
                    Hapus semua filter
                  </button>
                )}
              </div>
            )}

            {renderItems.map(item => {
              if (item.kind === 'header') {
                return (
                  <div key={item.key} className="tl-group-header" data-day={item.key.replace('hdr-', '')}>
                    {item.label}
                  </div>
                )
              }
              if (item.kind === 'gap') {
                return (
                  <div key={item.key} className="tl-gap-indicator">
                    Tidak ada aktivitas · {item.hours} jam
                  </div>
                )
              }
              if (item.kind === 'cluster') {
                return expandedClusters.has(item.key) ? (
                  <div key={item.key}>
                    <div className="tl-cluster-expanded-hdr" onClick={() => setExpandedClusters(prev => { const n = new Set(prev); n.delete(item.key); return n })}>
                      <ChevronUp size={10} /> Tutup cluster ({item.events.length} event)
                    </div>
                    {item.events.map(ev => (
                      <EventNode
                        key={ev.id}
                        event={ev}
                        selected={selectedEvent?.id === ev.id}
                        onClick={() => setSelectedEvent(selectedEvent?.id === ev.id ? null : ev)}
                        kasusMap={kasusMap}
                        profilMap={profilMap}
                        isLatestKritis={ev.id === latestKritisId}
                      />
                    ))}
                  </div>
                ) : (
                  <EventCluster
                    key={item.key}
                    events={item.events}
                    onExpand={() => setExpandedClusters(prev => new Set([...prev, item.key]))}
                    profilMap={profilMap}
                  />
                )
              }
              return (
                <EventNode
                  key={item.event.id}
                  event={item.event}
                  selected={selectedEvent?.id === item.event.id}
                  onClick={() => setSelectedEvent(selectedEvent?.id === item.event.id ? null : item.event)}
                  kasusMap={kasusMap}
                  profilMap={profilMap}
                  isLatestKritis={item.event.id === latestKritisId}
                />
              )
            })}
          </div>
        </div>
      </div>

      {/* ── Footer ── */}
      <div className="tl-footer">
        <button className="la-footer-nav" onClick={() => navigate('/link-analysis')}>
          <ChevronLeft size={12} /> Link Analysis
        </button>
        <span className="la-footer-current">Timeline</span>
        <span style={{ opacity: .2 }}>H8</span>
      </div>

      {/* ── EventDetailCard overlay ── */}
      {selectedEvent && (
        <EventDetailCard
          event={selectedEvent}
          kasusMap={kasusMap}
          profilMap={profilMap}
          onClose={() => setSelectedEvent(null)}
          onOpenProfil={setFullscreenProfilId}
        />
      )}

      {/* ── EntityProfileModal ── */}
      {fullscreenProfilId && (() => {
        const p = profilList.find(pr => pr.id_profil === fullscreenProfilId)
        if (!p) return null
        return <EntityProfileModal profil={p} onClose={() => setFullscreenProfilId(null)} />
      })()}
    </div>
  )
}
