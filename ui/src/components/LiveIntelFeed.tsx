/**
 * LiveIntelFeed — streams intel items dari semua dataset secara bertahap.
 * Self-contained: load data sendiri, filter by id_kasus / provinsi.
 * Reveal 1 item setiap 8-14 detik (random) setelah 3 item pertama muncul cepat.
 */
import { useEffect, useRef, useState } from 'react'
import {
  MapPin, DollarSign, MessageSquare, FileText,
  Navigation, Wifi, AlertTriangle,
} from 'lucide-react'
import type { Entitas, Laporan, Lokasi, Postingan, Transaksi } from '../types'
import { muatJson } from '../utils'

/* ── Intel item type ── */
type IntelTipe =
  | 'entitas'
  | 'transaksi'
  | 'postingan'
  | 'laporan'
  | 'lokasi'
  | 'sinyal'

type IntelItem = {
  id: string
  tipe: IntelTipe
  badge: string
  judul: string
  detail: string
  receivedAt: number   // ms timestamp
}

/* ── Styling per tipe ── */
const TIPE_META: Record<IntelTipe, {
  color: string
  bg: string
  icon: React.ReactNode
}> = {
  entitas:   { color: '#E04B4B', bg: 'rgba(179,24,24,.12)',    icon: <AlertTriangle size={10} /> },
  transaksi: { color: '#f0a060', bg: 'rgba(221,107,32,.12)',   icon: <DollarSign size={10} /> },
  postingan: { color: '#60A5FA', bg: 'rgba(96,165,250,.1)',    icon: <MessageSquare size={10} /> },
  laporan:   { color: '#A78BFA', bg: 'rgba(167,139,250,.1)',   icon: <FileText size={10} /> },
  lokasi:    { color: '#34D399', bg: 'rgba(52,211,153,.1)',    icon: <MapPin size={10} /> },
  sinyal:    { color: '#FBBF24', bg: 'rgba(251,191,36,.1)',    icon: <Wifi size={10} /> },
}

function relTime(ms: number): string {
  const secs = Math.floor((Date.now() - ms) / 1000)
  if (secs < 5)  return 'baru saja'
  if (secs < 60) return `${secs}d lalu`
  const mins = Math.floor(secs / 60)
  return `${mins}m lalu`
}

function fmtRupiah(n: number): string {
  if (n >= 1_000_000) return `Rp${(n / 1_000_000).toFixed(1)}jt`
  if (n >= 1_000)     return `Rp${Math.round(n / 1000)}rb`
  return `Rp${n}`
}

/* ── Build intel queue from all datasets for a given kasus ── */
function buildQueue(
  idKasus: string,
  kasusKota: string,
  kasusProvinsi: string,
  entitas: Entitas[],
  transaksi: Transaksi[],
  postingan: Postingan[],
  laporan: Laporan[],
  lokasi: Lokasi[],
): IntelItem[] {
  const items: IntelItem[] = []

  /* ENTITAS */
  entitas
    .filter(e => e.id_kasus === idKasus)
    .forEach(e => {
      items.push({
        id:         `ent-${e.nilai}`,
        tipe:       'entitas',
        badge:      e.tipe_entitas.replace('_', ' '),
        judul:      e.nilai,
        detail:     `${e.jumlah} mention terdeteksi`,
        receivedAt: 0,
      })
    })

  /* TRANSAKSI */
  transaksi
    .filter(t => t.id_kasus === idKasus)
    .forEach(t => {
      items.push({
        id:     t.id_transaksi,
        tipe:   'transaksi',
        badge:  t.kanal.replace('_', ' '),
        judul:  `Transfer ${fmtRupiah(t.jumlah_idr)}`,
        detail: `${t.petunjuk_tujuan} · ${t.referensi}`,
        receivedAt: 0,
      })
    })

  /* POSTINGAN — filter by kota dulu, fallback ke provinsi */
  const postByKota = postingan.filter(p => p.kota === kasusKota)
  const postPool   = postByKota.length >= 8
    ? postByKota
    : postingan.filter(p => p.provinsi === kasusProvinsi)

  /* Ambil sample representatif: 20 acak dari pool */
  const shuffled = [...postPool].sort(() => Math.random() - 0.5).slice(0, 20)
  shuffled.forEach(p => {
    const eng = p.engagement.suka + p.engagement.komentar + p.engagement.bagikan
    items.push({
      id:     p.id_posting,
      tipe:   'postingan',
      badge:  p.platform,
      judul:  p.konten.slice(0, 60) + (p.konten.length > 60 ? '…' : ''),
      detail: `${p.kota} · ${p.tipe_konten} · ❤ ${eng}`,
      receivedAt: 0,
    })
  })

  /* LAPORAN — temuan per baris */
  laporan
    .filter(l => l.id_kasus === idKasus)
    .forEach(l => {
      l.temuan.forEach((t, i) => {
        items.push({
          id:     `${l.id_laporan}-t${i}`,
          tipe:   'laporan',
          badge:  'temuan',
          judul:  t.slice(0, 80) + (t.length > 80 ? '…' : ''),
          detail: l.judul,
          receivedAt: 0,
        })
      })
      l.rekomendasi.forEach((r, i) => {
        items.push({
          id:     `${l.id_laporan}-r${i}`,
          tipe:   'laporan',
          badge:  'rekomendasi',
          judul:  r.slice(0, 80) + (r.length > 80 ? '…' : ''),
          detail: l.judul,
          receivedAt: 0,
        })
      })
    })

  /* LOKASI — filter by provinsi, acak 15 */
  lokasi
    .filter(l => l.provinsi === kasusProvinsi)
    .sort(() => Math.random() - 0.5)
    .slice(0, 15)
    .forEach(l => {
      items.push({
        id:     l.id_lokasi,
        tipe:   'lokasi',
        badge:  l.tipe_lokasi.replace(/_/g, ' '),
        judul:  l.label,
        detail: `${l.kota} · conf ${Math.round(l.kepercayaan * 100)}%`,
        receivedAt: 0,
      })
    })

  /* Shuffle semua agar beragam */
  return items.sort(() => Math.random() - 0.5)
}

/* ── Props ── */
type Props = {
  idKasus: string
  kasusKota: string
  kasusProvinsi: string
  maxVisible?: number
}

const MAX_VISIBLE_DEFAULT = 6

export default function LiveIntelFeed({
  idKasus,
  kasusKota,
  kasusProvinsi,
  maxVisible = MAX_VISIBLE_DEFAULT,
}: Props) {
  const [visible, setVisible]   = useState<IntelItem[]>([])
  const [loading, setLoading]   = useState(true)
  const [count, setCount]       = useState(0)     // total item yang sudah muncul
  const queueRef   = useRef<IntelItem[]>([])
  const timerRef   = useRef<ReturnType<typeof setTimeout> | null>(null)

  /* Reset dan load ulang saat idKasus berubah */
  useEffect(() => {
    setLoading(true)
    setVisible([])
    setCount(0)
    if (timerRef.current) clearTimeout(timerRef.current)

    async function load() {
      try {
        const [entData, txnData, postData, lapData, lokData] = await Promise.all([
          muatJson<Entitas[]>('/data/entitas.json'),
          muatJson<Transaksi[]>('/data/transaksi.json'),
          muatJson<Postingan[]>('/data/postingan.json'),
          muatJson<Laporan[]>('/data/laporan.json'),
          muatJson<Lokasi[]>('/data/lokasi.json'),
        ])
        queueRef.current = buildQueue(
          idKasus, kasusKota, kasusProvinsi,
          entData, txnData, postData, lapData, lokData,
        )
      } catch {
        queueRef.current = []
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [idKasus, kasusKota, kasusProvinsi])

  /* Stream items setelah loading selesai */
  useEffect(() => {
    if (loading) return
    if (queueRef.current.length === 0) return

    function reveal() {
      const queue = queueRef.current
      if (queue.length === 0) return

      const item = { ...queue.shift()!, receivedAt: Date.now() }
      setVisible(prev => {
        const next = [item, ...prev]
        return next.slice(0, maxVisible)
      })
      setCount(prev => prev + 1)

      // Pertama 3 item: cepat (1.2s antar item). Setelahnya: 8-14 detik acak.
      const delay = count < 3
        ? 1200 + count * 600
        : 8000 + Math.random() * 6000

      timerRef.current = setTimeout(reveal, delay)
    }

    reveal()
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, idKasus])

  /* Relative time ticker */
  const [tick, setTick] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setTick(v => v + 1), 15_000)
    return () => clearInterval(t)
  }, [])

  /* Suppress unused warning */
  void tick

  if (loading) {
    return (
      <div className="lif-wrap">
        <div className="lif-header">
          <Wifi size={11} className="lif-header-icon" />
          INTEL STREAM
          <span className="lif-scanning">scanning…</span>
        </div>
        <div className="lif-loading">
          <div className="spinner" style={{ width: 14, height: 14 }} />
          <span>Menghubungkan sumber data</span>
        </div>
      </div>
    )
  }

  return (
    <div className="lif-wrap">
      <div className="lif-header">
        <Navigation size={11} className="lif-header-icon" />
        INTEL STREAM
        <span className="lif-count">{count} sinyal</span>
        <span className="lif-live-dot" />
      </div>

      <div className="lif-list">
        {visible.length === 0 && (
          <div className="lif-empty">Menunggu sinyal masuk…</div>
        )}

        {visible.map((item, idx) => {
          const meta = TIPE_META[item.tipe]
          return (
            <div
              key={item.id}
              className={`lif-item ${idx === 0 ? 'lif-item-new' : ''}`}
              style={{ '--lif-color': meta.color, '--lif-bg': meta.bg } as React.CSSProperties}
            >
              {/* Type badge + icon */}
              <span className="lif-badge">
                {meta.icon}
                {item.badge}
              </span>

              {/* Content */}
              <div className="lif-content">
                <div className="lif-title">{item.judul}</div>
                <div className="lif-detail">{item.detail}</div>
              </div>

              {/* Timestamp */}
              <span className="lif-time">{relTime(item.receivedAt)}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
