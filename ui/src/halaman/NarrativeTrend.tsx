/**
 * NarrativeTrend — H10 Narasi & Tren
 *
 * Visual-first. 4 section:
 * 1. Bar chart volume postingan per hari (SVG inline)
 * 2. Word cloud kata kunci + hashtag (SVG bubble, ukuran = frekuensi)
 * 3. Klaster pesan terkoordinasi (card besar, progress bar kemiripan)
 * 4. Feed berita terkait (thumbnail dominan, panel kanan)
 *
 * Terima nav state { filterKasus?, filterProfil? } dari H3/H9.
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { AlertTriangle, ChevronRight, ExternalLink, GitBranch, RefreshCw, Users } from 'lucide-react'
import { muatJson } from '../utils'
import { useArrowNav } from '../hooks/useArrowNav'
import type { Kasus, KlasterPesan, Postingan, Profil, Berita } from '../types'
import EntityProfileModal from '../components/EntityProfileModal'

// ─── Warna kategori berita ───────────────────────────────────────────────────
const WARNA_KATEGORI: Record<string, string> = {
  'Hukum & Kriminal': '#C62828',
  'Hukum':            '#C62828',
  'Keamanan':         '#B31818',
  'Nasional':         '#1565C0',
  'Daerah':           '#2E7D32',
  'Ekonomi':          '#D96C06',
  'Sosial':           '#7B1FA2',
  'Teknologi':        '#0277BD',
  'Olahraga':         '#1B5E20',
}

function warnaBadge(kategori: string) {
  return WARNA_KATEGORI[kategori] ?? '#555'
}

function fmtTgl(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString('id-ID', { day: 'numeric', month: 'short' })
}
function fmtTglPanjang(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' })
}

// ─── Bar Chart SVG ───────────────────────────────────────────────────────────
type BarDatum = { tanggal: string; jumlah: number }

function BarChart({ data }: { data: BarDatum[] }) {
  const [hovered, setHovered] = useState<number | null>(null)
  if (data.length === 0) return (
    <div className="nt-empty-hint"><RefreshCw size={18} style={{ opacity: .15 }} /> Tidak ada data postingan</div>
  )

  const W = 800, H = 160, PAD_L = 28, PAD_B = 36, PAD_T = 12, PAD_R = 12
  const maxVal = Math.max(...data.map(d => d.jumlah), 1)
  const barW = Math.max(4, Math.min(36, (W - PAD_L - PAD_R) / data.length - 3))
  const gap  = (W - PAD_L - PAD_R - barW * data.length) / Math.max(data.length - 1, 1)
  const scaleY = (v: number) => PAD_T + (H - PAD_T - PAD_B) * (1 - v / maxVal)

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="nt-barchart-svg" preserveAspectRatio="none">
      {/* Grid lines */}
      {[0.25, 0.5, 0.75, 1].map(f => {
        const y = scaleY(maxVal * f)
        return (
          <line key={f} x1={PAD_L} y1={y} x2={W - PAD_R} y2={y}
            stroke="rgba(255,255,255,.06)" strokeWidth={1} />
        )
      })}

      {/* Bars */}
      {data.map((d, i) => {
        const x = PAD_L + i * (barW + gap)
        const barH = (H - PAD_T - PAD_B) * (d.jumlah / maxVal)
        const y = H - PAD_B - barH
        const aktif = hovered === i
        return (
          <g key={d.tanggal} onMouseEnter={() => setHovered(i)} onMouseLeave={() => setHovered(null)}>
            <rect x={x} y={y} width={barW} height={barH}
              fill={aktif ? '#E5282A' : '#B31818'}
              rx={2} style={{ transition: 'fill .12s' }}
            />
            {/* Tooltip */}
            {aktif && (
              <g>
                <rect x={Math.min(x - 8, W - 90)} y={y - 34} width={84} height={28} rx={4}
                  fill="#1a1a1a" stroke="rgba(229,40,42,.5)" strokeWidth={1} />
                <text x={Math.min(x - 8, W - 90) + 42} y={y - 22} textAnchor="middle"
                  fill="#E5282A" fontSize={9} fontWeight="700">{d.jumlah} posting</text>
                <text x={Math.min(x - 8, W - 90) + 42} y={y - 12} textAnchor="middle"
                  fill="rgba(243,234,234,.5)" fontSize={8}>{d.tanggal}</text>
              </g>
            )}
            {/* X label — setiap 4 atau 5 */}
            {(i % Math.max(1, Math.floor(data.length / 10)) === 0) && (
              <text x={x + barW / 2} y={H - PAD_B + 12} textAnchor="middle"
                fill="rgba(243,234,234,.3)" fontSize={8}>{fmtTgl(d.tanggal)}</text>
            )}
          </g>
        )
      })}

      {/* Y-axis label */}
      <text x={PAD_L - 4} y={scaleY(maxVal) + 4} textAnchor="end"
        fill="rgba(243,234,234,.2)" fontSize={8}>{maxVal}</text>
    </svg>
  )
}

// ─── Word Cloud SVG ──────────────────────────────────────────────────────────
type WordDatum = { kata: string; freq: number }

function WordCloud({ words, onKlik }: { words: WordDatum[]; onKlik: (kata: string) => void }) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [posisi, setPosisi] = useState<Array<{ x: number; y: number; fs: number; kata: string; freq: number }>>([])
  const [hovered, setHovered] = useState<string | null>(null)

  useEffect(() => {
    if (words.length === 0) return
    const W = 640, H = 220
    const maxFreq = Math.max(...words.map(w => w.freq))
    const minFreq = Math.min(...words.map(w => w.freq))

    // Simple spiral placement (deterministik berdasarkan index)
    const placed: Array<{ x: number; y: number; w: number; h: number }> = []

    function overlaps(nx: number, ny: number, nw: number, nh: number) {
      const pad = 6
      return placed.some(p =>
        nx < p.x + p.w + pad && nx + nw + pad > p.x &&
        ny < p.y + p.h + pad && ny + nh + pad > p.y
      )
    }

    const result: typeof posisi = []
    words.forEach((w, i) => {
      const range = maxFreq === minFreq ? 1 : maxFreq - minFreq
      const t = (w.freq - minFreq) / range
      const fs = 10 + Math.round(t * 26)
      const ww = w.kata.length * fs * 0.62 + 8
      const wh = fs + 10

      // Spiral outward from center
      let placed_ok = false
      for (let r = 0; r <= 300; r += 4) {
        const angle = i * 2.4 + r * 0.18
        const cx = W / 2 + r * Math.cos(angle) - ww / 2
        const cy = H / 2 + r * Math.sin(angle) * 0.55 - wh / 2
        if (cx < 4 || cy < 4 || cx + ww > W - 4 || cy + wh > H - 4) continue
        if (!overlaps(cx, cy, ww, wh)) {
          placed.push({ x: cx, y: cy, w: ww, h: wh })
          result.push({ x: cx + ww / 2, y: cy + wh / 2 + fs * 0.35, fs, kata: w.kata, freq: w.freq })
          placed_ok = true
          break
        }
      }
      if (!placed_ok && result.length < 5) {
        // fallback: put somewhere
        const fx = (i % 8) * 78 + 10
        const fy = Math.floor(i / 8) * 42 + 20
        result.push({ x: fx + ww / 2, y: fy + wh / 2 + fs * 0.35, fs, kata: w.kata, freq: w.freq })
      }
    })
    setPosisi(result)
  }, [words])

  if (words.length === 0) return (
    <div className="nt-empty-hint"><RefreshCw size={18} style={{ opacity: .15 }} /> Tidak ada kata kunci</div>
  )

  const maxFreq = Math.max(...words.map(w => w.freq))

  return (
    <svg ref={svgRef} viewBox="0 0 640 220" className="nt-wordcloud-svg" preserveAspectRatio="xMidYMid meet">
      {posisi.map(p => {
        const t = p.freq / maxFreq
        const alpha = 0.35 + t * 0.65
        const color = t > 0.7 ? '#E5282A' : t > 0.4 ? '#B31818' : `rgba(213,40,40,${alpha})`
        const isHov = hovered === p.kata
        return (
          <text
            key={p.kata}
            x={p.x} y={p.y}
            textAnchor="middle"
            fontSize={p.fs}
            fontWeight={t > 0.6 ? '700' : t > 0.3 ? '600' : '500'}
            fill={isHov ? '#FF6B6B' : color}
            style={{ cursor: 'pointer', transition: 'fill .12s', userSelect: 'none' }}
            onMouseEnter={() => setHovered(p.kata)}
            onMouseLeave={() => setHovered(null)}
            onClick={() => onKlik(p.kata)}
          >
            {p.kata}
          </text>
        )
      })}
    </svg>
  )
}

// ─── Klaster Card ────────────────────────────────────────────────────────────
type SeverityTier = 'kritis' | 'tinggi' | 'sedang'
function hitungSeverity(kemiripan: number, jumlah: number): SeverityTier {
  if (kemiripan >= 0.85 || (kemiripan >= 0.75 && jumlah >= 50)) return 'kritis'
  if (kemiripan >= 0.75 || jumlah >= 40) return 'tinggi'
  return 'sedang'
}
const WARNA_SEVERITY: Record<SeverityTier, { bg: string; border: string; text: string; label: string }> = {
  kritis: { bg: 'rgba(198,40,40,.15)', border: 'rgba(198,40,40,.5)',  text: '#FF4444', label: 'KRITIS'  },
  tinggi: { bg: 'rgba(217,108,6,.12)', border: 'rgba(217,108,6,.4)',  text: '#F5A623', label: 'TINGGI'  },
  sedang: { bg: 'rgba(255,255,255,.02)', border: 'rgba(255,255,255,.07)', text: '#666', label: 'SEDANG' },
}

function inisial(nama: string) {
  return nama.split(' ').slice(0, 2).map(s => s[0]).join('').toUpperCase()
}

function AvatarProfil({ profil: p, onClick }: { profil: Profil; onClick: () => void }) {
  const [imgOk, setImgOk] = useState(true)
  return (
    <button className="nt-klaster-avatar-btn" onClick={onClick} title={p.nama_tampil}>
      {imgOk ? (
        <img
          src={p.url_avatar}
          alt=""
          className="nt-klaster-avatar"
          onError={() => setImgOk(false)}
        />
      ) : (
        <div className="nt-klaster-avatar nt-klaster-avatar-inisial">
          {inisial(p.nama_tampil)}
        </div>
      )}
    </button>
  )
}

function KlasterCard({
  klaster, profilMap, onBukaProfil, onBukaKasus, onBukaKanvas,
}: {
  klaster: KlasterPesan
  profilMap: Map<string, Profil>
  onBukaProfil: (p: Profil) => void
  onBukaKasus: (id: string) => void
  onBukaKanvas: (idKasus: string) => void
}) {
  const pct      = Math.round(klaster.kemiripan_copy * 100)
  const severity = hitungSeverity(klaster.kemiripan_copy, klaster.jumlah_posting)
  const sev      = WARNA_SEVERITY[severity]
  const warnaBar = severity === 'kritis' ? '#E5282A' : severity === 'tinggi' ? '#D96C06' : '#555'

  return (
    <div className="nt-klaster-card" style={{ background: sev.bg, borderColor: sev.border }}>

      {/* Baris 1: severity pill + kasus label */}
      <div className="nt-klaster-meta-row">
        <span className="nt-severity-badge" style={{ color: sev.text, borderColor: sev.border }}>
          {severity === 'kritis' && <AlertTriangle size={9} />}{sev.label}
        </span>
        <span className="nt-klaster-kasus-label">
          {klaster.id_kasus.replace('kasus-', '')}
        </span>
        <span className="nt-klaster-stat-inline">{klaster.jumlah_posting} posting</span>
        <span className="nt-klaster-stat-inline">{klaster.id_profil.length} akun</span>
        <span className="nt-klaster-stat-inline nt-klaster-pct" style={{ color: warnaBar }}>
          {pct}% kemiripan
        </span>
      </div>

      {/* Baris 2: frasa kanonik */}
      <div className="nt-klaster-frasa">
        "{klaster.frasa_kanonik}"
      </div>

      {/* Baris 3: progress bar */}
      <div className="nt-klaster-progress-track" style={{ marginTop: 8 }}>
        <div className="nt-klaster-progress-fill" style={{ width: `${pct}%`, background: warnaBar }} />
      </div>

      {/* Baris 4: avatar + actions dalam satu baris */}
      <div className="nt-klaster-footer">
        <div className="nt-klaster-profil-row">
          {klaster.id_profil.map(id => {
            const p = profilMap.get(id)
            if (!p) return (
              <div key={id} className="nt-klaster-avatar nt-klaster-avatar-inisial" title={id}>?</div>
            )
            return <AvatarProfil key={id} profil={p} onClick={() => onBukaProfil(p)} />
          })}
        </div>
        <div className="nt-klaster-actions">
          <button className="nt-action-btn nt-action-kanvas" onClick={() => onBukaKanvas(klaster.id_kasus)}>
            <GitBranch size={11} /> Jaringan
          </button>
          <button className="nt-action-btn nt-action-kasus" onClick={() => onBukaKasus(klaster.id_kasus)}>
            <Users size={11} /> Kasus
          </button>
        </div>
      </div>

    </div>
  )
}

// ─── Berita Card ─────────────────────────────────────────────────────────────
function BeritaCard({ berita }: { berita: Berita }) {
  const warna = warnaBadge(berita.kategori)
  return (
    <a
      href={`/news/berita/${berita.id}.html`}
      target="_blank"
      rel="noopener noreferrer"
      className="nt-berita-card"
    >
      <div className="nt-berita-img-wrap">
        {berita.image_local ? (
          <img
            src={`/news/images/${berita.image_local}`}
            alt={berita.judul}
            className="nt-berita-img"
            onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
          />
        ) : (
          <div className="nt-berita-img-placeholder" />
        )}
        <span className="nt-berita-kategori-badge" style={{ background: warna }}>
          {berita.kategori}
        </span>
      </div>
      <div className="nt-berita-body">
        <div className="nt-berita-judul">{berita.judul}</div>
        <div className="nt-berita-meta">
          {berita.portal && <span>{berita.portal}</span>}
          <span>{fmtTglPanjang(berita.published_at)}</span>
          {berita.lokasi && <span>{berita.lokasi}</span>}
        </div>
      </div>
      <ExternalLink size={10} className="nt-berita-link-icon" />
    </a>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function NarrativeTrend() {
  useArrowNav()
  const navigate = useNavigate()
  const location = useLocation()

  // ── Data state ──
  const [postingan, setPostingan]     = useState<Postingan[]>([])
  const [klaster, setKlaster]         = useState<KlasterPesan[]>([])
  const [kasus, setKasus]             = useState<Kasus[]>([])
  const [profil, setProfil]           = useState<Profil[]>([])
  const [berita, setBerita]           = useState<Berita[]>([])
  const [loading, setLoading]         = useState(true)

  // ── UI state ──
  const [filterKasus, setFilterKasus] = useState<string>('semua')
  const [filterKata,  setFilterKata]  = useState<string | null>(null)
  const [profilModal, setProfilModal] = useState<Profil | null>(null)

  // ── Terima nav state dari H3 / H9 ──
  useEffect(() => {
    const state = location.state as { filterKasus?: string; filterProfil?: string } | null
    if (state?.filterKasus) setFilterKasus(state.filterKasus)
  }, [location.state])

  // ── Load semua data ──
  useEffect(() => {
    async function muat() {
      try {
        const [pData, kpData, kasData, prData, bRaw] = await Promise.all([
          muatJson<Postingan[]>('/data/postingan.json'),
          muatJson<KlasterPesan[]>('/data/klaster_pesan.json'),
          muatJson<Kasus[]>('/data/kasus.json'),
          muatJson<Profil[]>('/data/profil.json'),
          fetch('/data/news.dataset.jsonl').then(r => r.ok ? r.text() : Promise.resolve('')),
        ])
        setPostingan(pData)
        setKlaster(kpData)
        setKasus(kasData)
        setProfil(prData)
        setBerita(
          bRaw.split('\n').map(l => l.trim()).filter(Boolean).map(l => JSON.parse(l) as Berita)
        )
      } catch (e) {
        console.error('NarrativeTrend: gagal muat data', e)
      } finally {
        setLoading(false)
      }
    }
    muat()
  }, [])

  // ── Derived: id_profil terkait kasus aktif ──
  const profilMap = useMemo(() => new Map(profil.map(p => [p.id_profil, p])), [profil])

  const profilIdKasus = useMemo(() => {
    if (filterKasus === 'semua') return null  // null = semua profil
    const profilTerkait = new Set<string>()
    profil.forEach(p => {
      if (p.tautan_kasus.some(t => t.id_kasus === filterKasus)) profilTerkait.add(p.id_profil)
    })
    return profilTerkait
  }, [profil, filterKasus])

  // ── Postingan terfilter ──
  const postinganFiltered = useMemo(() => {
    if (!profilIdKasus) return postingan
    return postingan.filter(p => profilIdKasus.has(p.id_profil))
  }, [postingan, profilIdKasus])

  // ── Bar chart data: group by tanggal ──
  const barData = useMemo<BarDatum[]>(() => {
    const map = new Map<string, number>()
    postinganFiltered.forEach(p => {
      const tgl = p.timestamp.slice(0, 10)
      map.set(tgl, (map.get(tgl) ?? 0) + 1)
    })
    return [...map.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([tanggal, jumlah]) => ({ tanggal, jumlah }))
  }, [postinganFiltered])

  // ── Word cloud: frekuensi kata_kunci + hashtag ──
  const wordData = useMemo<WordDatum[]>(() => {
    const freq = new Map<string, number>()
    postinganFiltered.forEach(p => {
      p.kata_kunci?.forEach(k => { const w = k.toLowerCase().trim(); if (w) freq.set(w, (freq.get(w) ?? 0) + 1) })
      p.hashtag?.forEach(h => { const w = h.replace(/^#/, '').toLowerCase().trim(); if (w) freq.set(w, (freq.get(w) ?? 0) + 1) })
    })
    return [...freq.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 40)
      .map(([kata, freq]) => ({ kata, freq }))
  }, [postinganFiltered])

  // ── Klaster terfilter ──
  const klasterFiltered = useMemo(() => {
    let list = filterKasus === 'semua' ? klaster : klaster.filter(k => k.id_kasus === filterKasus)
    if (filterKata) list = list.filter(k => k.frasa_kanonik.toLowerCase().includes(filterKata))
    return [...list].sort((a, b) => b.jumlah_posting - a.jumlah_posting)
  }, [klaster, filterKasus, filterKata])

  // ── Berita diurutkan by published_at desc ──
  const beritaSorted = useMemo(() => {
    const list = filterKasus === 'semua' ? berita : berita.filter(b => {
      const k = kasus.find(k => k.id_kasus === filterKasus)
      if (!k) return true
      return b.tags?.some(t => t.includes(k.tipe_kasus.toLowerCase().replace(/_/g, '-'))) ||
             b.provinsi === k.provinsi
    })
    return [...list].sort((a, b) => b.published_at.localeCompare(a.published_at))
  }, [berita, filterKasus, kasus])

  const handleKlikKata = (kata: string) => {
    setFilterKata(prev => prev === kata ? null : kata)
  }

  // ── Statistik ringkasan untuk strip intelijen ──
  const ringkasan = useMemo(() => {
    const klasterKritis  = klasterFiltered.filter(k => hitungSeverity(k.kemiripan_copy, k.jumlah_posting) === 'kritis').length
    const profilAktif    = new Set(klasterFiltered.flatMap(k => k.id_profil)).size
    const puncak         = barData.length > 0
      ? barData.reduce((a, b) => b.jumlah > a.jumlah ? b : a, barData[0])
      : null
    return { klasterKritis, profilAktif, puncak }
  }, [klasterFiltered, barData])

  if (loading) return (
    <div className="nt-root nt-loading">
      <RefreshCw size={32} style={{ opacity: .2, animation: 'spin 1s linear infinite' }} />
      <span>Memuat data narasi…</span>
    </div>
  )

  return (
    <div className="nt-root">
      {/* ── Topbar ── */}
      <div className="nt-topbar">
        <span className="nt-topbar-judul">Narasi & Tren</span>
        <div className="nt-topbar-divider" />
        <div className="nt-kasus-pills">
          <button
            className={`nt-kasus-pill${filterKasus === 'semua' ? ' aktif' : ''}`}
            onClick={() => setFilterKasus('semua')}
          >Semua Kasus</button>
          {kasus.map(k => (
            <button
              key={k.id_kasus}
              className={`nt-kasus-pill${filterKasus === k.id_kasus ? ' aktif' : ''}`}
              onClick={() => setFilterKasus(k.id_kasus)}
            >{k.judul}</button>
          ))}
        </div>
        {filterKata && (
          <div className="nt-filter-kata-badge">
            Filter: <strong>{filterKata}</strong>
            <button onClick={() => setFilterKata(null)}>×</button>
          </div>
        )}
        <div style={{ flex: 1 }} />
        <span className="nt-topbar-stats">{postinganFiltered.length} posting · {klasterFiltered.length} klaster</span>
      </div>

      {/* ── Strip Ringkasan Intelijen ── */}
      <div className="nt-intel-strip">
        <div className={`nt-intel-stat${ringkasan.klasterKritis > 0 ? ' nt-intel-stat-alert' : ''}`}>
          <AlertTriangle size={12} />
          <span><strong>{ringkasan.klasterKritis}</strong> klaster kritis</span>
        </div>
        <div className="nt-intel-divider" />
        <div className="nt-intel-stat">
          <Users size={12} />
          <span><strong>{ringkasan.profilAktif}</strong> akun berkoordinasi aktif</span>
        </div>
        <div className="nt-intel-divider" />
        <div className="nt-intel-stat">
          <span>Puncak aktivitas:</span>
          <strong>{ringkasan.puncak ? `${fmtTglPanjang(ringkasan.puncak.tanggal)} (${ringkasan.puncak.jumlah} posting)` : '–'}</strong>
        </div>
        <div className="nt-intel-divider" />
        <div className="nt-intel-hint">
          Klik kata di word cloud untuk filter klaster · Klik avatar profil untuk detail · Gunakan "Buka Jaringan" untuk pemetaan koneksi
        </div>
      </div>

      {/* ── Body ── */}
      <div className="nt-body">
        {/* Kolom Utama */}
        <div className="nt-main">

          {/* Section 1: Volume Postingan */}
          <div className="nt-section">
            <div className="nt-section-title">
              <span className="nt-section-dot" style={{ background: '#B31818' }} />
              Volume Postingan Harian
              <span className="nt-section-sub">{barData.length} hari aktif</span>
            </div>
            <div className="nt-barchart-wrap">
              <BarChart data={barData} />
            </div>
          </div>

          {/* Section 2: Word Cloud */}
          <div className="nt-section">
            <div className="nt-section-title">
              <span className="nt-section-dot" style={{ background: '#D62828' }} />
              Kata Kunci & Hashtag
              <span className="nt-section-sub">{wordData.length} kata unik · klik untuk filter klaster</span>
            </div>
            <div className="nt-wordcloud-wrap">
              <WordCloud words={wordData} onKlik={handleKlikKata} />
            </div>
          </div>

          {/* Section 3: Klaster Pesan */}
          <div className="nt-section">
            <div className="nt-section-title">
              <span className="nt-section-dot" style={{ background: '#FF6B6B' }} />
              Klaster Pesan Terkoordinasi
              <span className="nt-section-sub">{klasterFiltered.length} klaster ditemukan</span>
            </div>
            {klasterFiltered.length === 0 ? (
              <div className="nt-empty-hint">Tidak ada klaster untuk filter ini</div>
            ) : (
              <div className="nt-klaster-grid">
                {klasterFiltered.map(k => (
                  <KlasterCard
                    key={k.id_klaster_pesan}
                    klaster={k}
                    profilMap={profilMap}
                    onBukaProfil={p => setProfilModal(p)}
                    onBukaKasus={id => navigate('/incident-queue', { state: { focusKasus: id } })}
                    onBukaKanvas={id => navigate('/canvas', { state: { filterKasus: id } })}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Panel Kanan: Feed Berita */}
        <div className="nt-panel-kanan">
          <div className="nt-panel-kanan-judul">Berita Terkait</div>
          <div className="nt-berita-list">
            {beritaSorted.length === 0 ? (
              <div className="nt-empty-hint">Tidak ada berita</div>
            ) : (
              beritaSorted.map(b => <BeritaCard key={b.id} berita={b} />)
            )}
          </div>
        </div>
      </div>

      {/* Entity Profile Modal */}
      {profilModal && (
        <EntityProfileModal profil={profilModal} onClose={() => setProfilModal(null)} />
      )}
    </div>
  )
}
