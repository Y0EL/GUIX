/**
 * LinkAnalysis — H6 network graph D3 force-directed
 * Hanya menampilkan subgraph kasus yang dipilih:
 * profil terkait langsung + 1-hop teman + postingan mereka
 * Klik node → highlight + side panel (bukan fullscreen popup)
 */
import { useEffect, useState, useRef, useCallback, useMemo } from 'react'
import {
  AlertTriangle, ZoomIn, ZoomOut, Maximize2, RefreshCw,
  ChevronLeft, X, MapPin, ExternalLink, Activity,
} from 'lucide-react'
import * as d3 from 'd3'
import { useNavigate, useLocation } from 'react-router-dom'
import { muatJson } from '../utils'
import { useArrowNav } from '../hooks/useArrowNav'
import { useLinkGraph, type Noda } from '../hooks/useLinkGraph'
import type { Profil, Pertemanan, Postingan, Kasus } from '../types'
import EntityProfileModal from '../components/EntityProfileModal'
import PlatformIcon from '../components/PlatformIcon'

// ──────────────────────────────────────────────────────────
// Warna
// ──────────────────────────────────────────────────────────
const WARNA_EDGE: Record<string, string> = {
  pertemanan: 'rgba(99,179,237,.45)',
  postingan:  'rgba(246,173,85,.4)',
  balasan:    'rgba(154,230,180,.35)',
}
const WARNA_NODE: Record<string, string> = {
  postingan: '#F6AD55',
  balasan:   '#68D391',
}
const WARNA_PLATFORM: Record<string, string> = {
  twitter:   '#1DA1F2',
  instagram: '#E1306C',
  facebook:  '#1877F2',
  youtube:   '#FF0000',
  telegram:  '#26A5E4',
  tiktok:    '#69C9D0',
}

// ──────────────────────────────────────────────────────────
// NodeElement — SVG node dengan highlight & isDirect
// ──────────────────────────────────────────────────────────
function NodeElement({
  node, onClick, onDragStart, highlighted, isDirect, dimmed,
}: {
  node: Noda
  onClick: (n: Noda, e: React.MouseEvent) => void
  onDragStart: (nodeId: string, screenX: number, screenY: number) => void
  highlighted?: boolean
  isDirect?: boolean
  dimmed?: boolean
}) {
  const [imgError, setImgError] = useState(false)

  if (node.tipe === 'profil') {
    const r = highlighted ? 18 : 16
    const clipId = `clip-${node.id}`
    return (
      <g
        transform={`translate(${node.x ?? 0},${node.y ?? 0})`}
        className="la-node la-node-profil"
        onClick={e => onClick(node, e)}
        onMouseDown={e => { e.stopPropagation(); onDragStart(node.id, e.clientX, e.clientY) }}
        style={{ cursor: 'grab', opacity: dimmed ? 0.22 : 1 }}
      >
        {/* Ring merah untuk node terkait kasus */}
        {isDirect && (
          <circle r={r + 6} fill="none" stroke="rgba(220,38,38,.45)" strokeWidth={1.5} />
        )}
        {/* Ring putih saat highlight */}
        {highlighted && (
          <circle r={r + 4} fill="none" stroke="rgba(255,255,255,.65)" strokeWidth={2} className="la-hl-ring" />
        )}
        <circle
          r={r + 2}
          fill="rgba(0,0,0,.55)"
          stroke={isDirect ? 'rgba(220,38,38,.35)' : 'rgba(255,255,255,.1)'}
          strokeWidth={1}
        />
        <defs>
          <clipPath id={clipId}><circle r={r} /></clipPath>
        </defs>
        {!imgError && node.avatar ? (
          <image
            href={node.avatar}
            x={-r} y={-r} width={r * 2} height={r * 2}
            clipPath={`url(#${clipId})`}
            preserveAspectRatio="xMidYMid slice"
            onError={() => setImgError(true)}
          />
        ) : (
          <circle r={r} fill={isDirect ? '#3B1010' : '#374151'} />
        )}
        <circle
          r={r}
          fill="none"
          stroke={isDirect ? 'rgba(220,38,38,.25)' : 'rgba(255,255,255,.15)'}
          strokeWidth={.8}
        />
        {/* Label singkat di bawah node */}
        {(isDirect || highlighted) && (
          <text
            y={r + 13}
            textAnchor="middle"
            fontSize={9}
            fill={isDirect ? 'rgba(255,180,180,.8)' : 'rgba(243,234,234,.65)'}
            style={{ userSelect: 'none', pointerEvents: 'none' }}
          >
            {node.label.split(' ')[0]}
          </text>
        )}
      </g>
    )
  }

  // Postingan / balasan
  const r = node.tipe === 'postingan' ? 5 : 4
  const warna = WARNA_PLATFORM[node.platform ?? ''] ?? WARNA_NODE[node.tipe]
  return (
    <g
      transform={`translate(${node.x ?? 0},${node.y ?? 0})`}
      className="la-node la-node-post"
      onClick={e => onClick(node, e)}
      onMouseDown={e => { e.stopPropagation(); onDragStart(node.id, e.clientX, e.clientY) }}
      style={{ cursor: 'grab', opacity: dimmed ? 0.1 : (highlighted ? 1 : 0.65) }}
    >
      {highlighted && (
        <circle r={r + 4} fill="none" stroke="rgba(255,255,255,.45)" strokeWidth={1.2} />
      )}
      <circle r={r + 1} fill="rgba(0,0,0,.4)" />
      <circle r={r} fill={warna} />
    </g>
  )
}

// ──────────────────────────────────────────────────────────
// NodeInfoPanel — side panel info (bukan fullscreen)
// ──────────────────────────────────────────────────────────
function NodeInfoPanel({
  node, profil, postingan, kasusProfilIds, kasus, selectedKasusId,
  onClose, onOpenFullscreen,
}: {
  node: Noda
  profil: Profil[]
  postingan: Postingan[]
  kasusProfilIds: Set<string>
  kasus: Kasus[]
  selectedKasusId: string | null
  onClose: () => void
  onOpenFullscreen: (id: string) => void
}) {
  const [imgErr, setImgErr] = useState(false)

  // Cari profil untuk node
  const profilId = node.tipe === 'profil' ? node.id : node.profil_id
  const p = profil.find(pr => pr.id_profil === profilId)

  // Untuk node postingan, cari datanya
  const post = (node.tipe === 'postingan' || node.tipe === 'balasan')
    ? postingan.find(ps => ps.id_posting === node.id)
    : null

  const isDirect = profilId ? kasusProfilIds.has(profilId) : false
  const peranInKasus = p?.tautan_kasus.find(t => t.id_kasus === selectedKasusId)
  const akun = p?.profil_terekstrak?.akun ?? []
  const kasusCount = p?.tautan_kasus.length ?? 0

  return (
    <div className="la-node-panel">
      <button className="la-panel-close" onClick={onClose} title="Tutup panel">
        <X size={12} />
      </button>

      {/* Jika ini node postingan, tampilkan info postingan dulu */}
      {post && (
        <div className="la-panel-post-card">
          <div className="la-panel-post-platform">
            <PlatformIcon platform={post.platform} size={12} showLabel />
            <span className="la-panel-post-tipe">{post.tipe_konten}</span>
          </div>
          <div className="la-panel-post-konten">{post.konten}</div>
          <div className="la-panel-post-eng">
            <span>❤ {post.engagement.suka}</span>
            <span>💬 {post.engagement.komentar}</span>
            <span>🔁 {post.engagement.bagikan}</span>
          </div>
          {p && (
            <div className="la-panel-post-owner">
              <span style={{ color: 'rgba(243,234,234,.3)', fontSize: 9 }}>oleh</span>
              {p.nama_lengkap}
            </div>
          )}
        </div>
      )}

      {/* Info profil */}
      {p ? (
        <>
          <div className="la-panel-header">
            <div className="la-panel-avatar-wrap">
              {!imgErr && p.url_avatar ? (
                <img
                  src={p.url_avatar} alt={p.nama_lengkap}
                  className="la-panel-avatar"
                  onError={() => setImgErr(true)}
                />
              ) : (
                <div className="la-panel-avatar-fallback" />
              )}
              {isDirect && <div className="la-panel-avatar-dot" />}
            </div>
            <div className="la-panel-header-info">
              <div className="la-panel-nama">{p.nama_lengkap}</div>
              <div className="la-panel-sub">
                <MapPin size={9} />
                {p.kota}
                {isDirect && (
                  <span className="la-panel-badge-direct">Terkait Kasus</span>
                )}
              </div>
            </div>
          </div>

          {/* Peran di kasus aktif */}
          {peranInKasus && (
            <div className="la-panel-peran">
              <span className="la-panel-peran-label">Peran</span>
              <span className="la-panel-peran-val">{peranInKasus.peran}</span>
              {peranInKasus.sinyal && (
                <span className="la-panel-sinyal">{peranInKasus.sinyal}</span>
              )}
            </div>
          )}

          {/* Risk tags */}
          {p.tag_risiko.length > 0 && (
            <div className="la-panel-tags">
              {p.tag_risiko.map(t => (
                <span key={t} className="la-panel-tag">
                  {t.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          )}

          {/* Platform accounts */}
          {akun.length > 0 && (
            <div className="la-panel-platforms">
              {akun.slice(0, 4).map((a, i) => (
                <div key={i} className="la-panel-platform-item">
                  <PlatformIcon platform={a.platform} size={11} />
                  <span>@{a.username}</span>
                </div>
              ))}
              {akun.length > 4 && (
                <div className="la-panel-platform-item">+{akun.length - 4}</div>
              )}
            </div>
          )}

          {/* Mini stats */}
          <div className="la-panel-stats">
            <div className="la-panel-stat">
              <span className="la-panel-stat-val">
                {p.profil_terekstrak?.statistik?.jumlah_posting ?? 0}
              </span>
              <span className="la-panel-stat-lbl">Postingan</span>
            </div>
            <div className="la-panel-stat">
              <span className="la-panel-stat-val">{kasusCount}</span>
              <span className="la-panel-stat-lbl">Kasus</span>
            </div>
            <div className="la-panel-stat">
              <span className="la-panel-stat-val">{p.tag_risiko.length}</span>
              <span className="la-panel-stat-lbl">Risiko</span>
            </div>
          </div>

          {/* Kasus lain yang terhubung */}
          {kasusCount > 0 && (
            <div className="la-panel-kasus-list">
              {p.tautan_kasus.slice(0, 3).map(tk => {
                const k = kasus.find(c => c.id_kasus === tk.id_kasus)
                return (
                  <div key={tk.id_kasus} className="la-panel-kasus-item">
                    <span className="la-panel-kasus-peran">{tk.peran}</span>
                    <span className="la-panel-kasus-judul">
                      {k?.judul?.slice(0, 30) ?? tk.id_kasus}
                      {(k?.judul?.length ?? 0) > 30 ? '…' : ''}
                    </span>
                  </div>
                )
              })}
            </div>
          )}

          {/* Open fullscreen */}
          <button
            className="la-panel-fullscreen-btn"
            onClick={() => onOpenFullscreen(p.id_profil)}
          >
            <ExternalLink size={11} /> Buka Profil Lengkap
          </button>
        </>
      ) : (
        <div className="la-panel-empty">
          <Activity size={18} style={{ opacity: .3 }} />
          <span>Profil tidak ditemukan di dataset</span>
        </div>
      )}
    </div>
  )
}

// ──────────────────────────────────────────────────────────
// Komponen utama
// ──────────────────────────────────────────────────────────
export default function LinkAnalysis() {
  useArrowNav()
  const navigate = useNavigate()
  const location = useLocation()
  // URL param — reaktif via useLocation, bukan window.location
  const urlParam = new URLSearchParams(location.search).get('profil')
  // Navigate state dari halaman lain (KanvasInvestigasi, Timeline, IncidentQueue, dll)
  const navState = location.state as { filterKasus?: string; filterProfil?: string } | null

  const [profil, setProfil]         = useState<Profil[]>([])
  const [pertemanan, setPertemanan] = useState<Pertemanan[]>([])
  const [postingan, setPostingan]   = useState<Postingan[]>([])
  const [kasus, setKasus]           = useState<Kasus[]>([])
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState<string | null>(null)

  // Filter toggles
  const [showPertemanan, setShowPertemanan] = useState(true)
  const [showPostingan, setShowPostingan]   = useState(true)
  const [showBalasan, setShowBalasan]       = useState(false)

  // Kasus yang dipilih untuk dianalisa
  const [selectedKasusId, setSelectedKasusId] = useState<string | null>(null)

  // Pan/zoom
  const [transform, setTransform] = useState({ x: 0, y: 0, k: 1 })
  const transformRef = useRef({ x: 0, y: 0, k: 1 })
  const svgRef  = useRef<SVGSVGElement>(null)
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null)

  // Node highlight & panel
  const [highlightedId, setHighlightedId]           = useState<string | null>(null)
  const [panelNode, setPanelNode]                   = useState<Noda | null>(null)
  const [fullscreenProfilId, setFullscreenProfilId] = useState<string | null>(null)

  // Drag state — purely ref (no re-render during drag)
  const dragRef = useRef<{ nodeId: string } | null>(null)

  // Load data
  useEffect(() => {
    async function muat() {
      try {
        const [pData, pertData, postData, kasusData] = await Promise.all([
          muatJson<Profil[]>('/data/profil.json'),
          muatJson<Pertemanan[]>('/data/pertemanan.json'),
          muatJson<Postingan[]>('/data/postingan.json'),
          muatJson<Kasus[]>('/data/kasus.json'),
        ])
        setProfil(pData)
        setPertemanan(pertData)
        setPostingan(postData)
        setKasus(kasusData)

        // Hanya auto-pilih kasus jika ada konteks eksplisit
        const konteksKasus  = navState?.filterKasus
        const konteksProfil = navState?.filterProfil ?? urlParam

        if (konteksKasus) {
          // Context langsung berupa kasus ID
          setSelectedKasusId(konteksKasus)
        } else if (konteksProfil) {
          // Context berupa profil — cari kasus terkaitnya
          const targetProfil = pData.find(p => p.id_profil === konteksProfil)
          if (targetProfil && targetProfil.tautan_kasus.length > 0) {
            setSelectedKasusId(targetProfil.tautan_kasus[0].id_kasus)
          } else {
            // Cek via 1-hop teman
            const temanIds = pertData
              .filter(pt => pt.profil_a === konteksProfil || pt.profil_b === konteksProfil)
              .map(pt => pt.profil_a === konteksProfil ? pt.profil_b : pt.profil_a)
            let kasusViaTeman: string | null = null
            for (const tid of temanIds) {
              const teman = pData.find(p => p.id_profil === tid)
              if (teman && teman.tautan_kasus.length > 0) {
                kasusViaTeman = teman.tautan_kasus[0].id_kasus
                break
              }
            }
            setSelectedKasusId(kasusViaTeman)
          }
        }
        // Tidak ada konteks → selectedKasusId tetap null → empty state
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Gagal memuat data')
      } finally {
        setLoading(false)
      }
    }
    muat()
  }, [urlParam, navState?.filterKasus, navState?.filterProfil]) // re-run jika param berubah

  // Profil yang terhubung langsung ke kasus
  const kasusProfilIds = useMemo(() => {
    if (!selectedKasusId) return new Set<string>()
    return new Set(
      profil
        .filter(p => p.tautan_kasus.some(t => t.id_kasus === selectedKasusId))
        .map(p => p.id_profil)
    )
  }, [selectedKasusId, profil])

  // Subgraph profil yang ditampilkan di graph
  const filteredProfil = useMemo(() => {
    // Tidak ada konteks = jangan tampilkan apapun
    if (!selectedKasusId && !urlParam && !navState?.filterProfil) return []

    if (urlParam || navState?.filterProfil) {
      const pid = urlParam ?? navState!.filterProfil!
      // Mode entity: hanya profil target + teman langsungnya
      const target = profil.find(p => p.id_profil === pid)
      if (!target) return []
      const temanLangsungIds = new Set(
        pertemanan
          .filter(pt => pt.profil_a === pid || pt.profil_b === pid)
          .map(pt => pt.profil_a === pid ? pt.profil_b : pt.profil_a)
      )
      return profil.filter(p => p.id_profil === pid || temanLangsungIds.has(p.id_profil))
    }
    // Mode kasus: direct + 1-hop teman
    if (!selectedKasusId) return []
    const hopIds = new Set<string>()
    pertemanan.forEach(pt => {
      if (kasusProfilIds.has(pt.profil_a)) hopIds.add(pt.profil_b)
      if (kasusProfilIds.has(pt.profil_b)) hopIds.add(pt.profil_a)
    })
    return profil.filter(p => kasusProfilIds.has(p.id_profil) || hopIds.has(p.id_profil))
  }, [urlParam, navState?.filterProfil, selectedKasusId, profil, pertemanan, kasusProfilIds])

  // Postingan: hanya dari profil subgraph, max 4 per profil
  const filteredPostingan = useMemo(() => {
    if (!selectedKasusId || !showPostingan) return []
    const ids = new Set(filteredProfil.map(p => p.id_profil))
    const cnt = new Map<string, number>()
    return postingan.filter(ps => {
      if (!ids.has(ps.id_profil)) return false
      const c = cnt.get(ps.id_profil) ?? 0
      if (c >= 4) return false
      cnt.set(ps.id_profil, c + 1)
      return true
    })
  }, [selectedKasusId, filteredProfil, postingan, showPostingan])

  // D3 force graph — RAF-based rendering
  const { nodesRef, edgesRef, renderVersion, simRef } = useLinkGraph({
  // eslint-disable-line
    profil: filteredProfil,
    pertemanan,
    postingan: filteredPostingan,
    showPertemanan,
    showPostingan,
    showBalasan,
  })

  // Auto-highlight profil dari URL param setelah data & sim ready
  useEffect(() => {
    if (!urlParam || nodesRef.current.length === 0) return
    const found = nodesRef.current.find(n => n.id === urlParam)
    if (found) {
      setHighlightedId(urlParam)
      setPanelNode(found)
    }
  // Hanya run sekali setelah renderVersion pertama (sim mulai) — bukan setiap tick
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlParam, renderVersion > 0])

  // D3 zoom setup
  useEffect(() => {
    if (!svgRef.current) return
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.15, 5])
      .filter(_event => {
        // Jangan zoom saat drag node sedang aktif
        if (dragRef.current) return false
        return true
      })
      .on('zoom', (e) => {
        const t = { x: e.transform.x, y: e.transform.y, k: e.transform.k }
        transformRef.current = t
        setTransform(t)
      })
    d3.select(svgRef.current).call(zoom)
    zoomRef.current = zoom
    return () => { d3.select(svgRef.current!).on('.zoom', null) }
  }, [loading])

  // Auto-fit saat kasus berubah
  useEffect(() => {
    const nodes = nodesRef.current
    if (nodes.length === 0 || !svgRef.current || !zoomRef.current) return
    const t = setTimeout(() => {
      const el = svgRef.current
      if (!el || !zoomRef.current) return
      const w = el.clientWidth, h = el.clientHeight
      const padding = 80
      const xs = nodes.map(n => n.x ?? 0)
      const ys = nodes.map(n => n.y ?? 0)
      const minX = Math.min(...xs), maxX = Math.max(...xs)
      const minY = Math.min(...ys), maxY = Math.max(...ys)
      const dx = maxX - minX || 1, dy = maxY - minY || 1
      const k = Math.min((w - padding * 2) / dx, (h - padding * 2) / dy, 2.5)
      const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2
      d3.select(el)
        .transition().duration(700)
        .call(zoomRef.current.transform,
          d3.zoomIdentity.translate(w / 2 - k * cx, h / 2 - k * cy).scale(k))
    }, 1800)
    return () => clearTimeout(t)
  }, [selectedKasusId]) // eslint-disable-line

  const handleZoom = useCallback((factor: number) => {
    if (!svgRef.current || !zoomRef.current) return
    d3.select(svgRef.current).transition().duration(250).call(zoomRef.current.scaleBy, factor)
  }, [])

  const handleFit = useCallback(() => {
    const nodes = nodesRef.current
    if (!svgRef.current || !zoomRef.current || nodes.length === 0) return
    const w = svgRef.current.clientWidth, h = svgRef.current.clientHeight
    const padding = 80
    const xs = nodes.map(n => n.x ?? 0), ys = nodes.map(n => n.y ?? 0)
    const minX = Math.min(...xs), maxX = Math.max(...xs)
    const minY = Math.min(...ys), maxY = Math.max(...ys)
    const dx = maxX - minX || 1, dy = maxY - minY || 1
    const k = Math.min((w - padding * 2) / dx, (h - padding * 2) / dy, 2.5)
    const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2
    d3.select(svgRef.current)
      .transition().duration(400)
      .call(zoomRef.current.transform,
        d3.zoomIdentity.translate(w / 2 - k * cx, h / 2 - k * cy).scale(k))
  }, [nodesRef])

  const handleReset = useCallback(() => {
    if (!svgRef.current || !zoomRef.current) return
    d3.select(svgRef.current).transition().duration(300).call(zoomRef.current.transform, d3.zoomIdentity)
  }, [])

  // ── DRAG: React mouse events, tidak bergantung D3 selectAll ──
  // Dipanggil dari NodeElement onMouseDown
  const handleNodeDragStart = useCallback((nodeId: string, _screenX: number, _screenY: number) => {
    const sim = simRef.current
    if (!sim) return
    sim.alphaTarget(0.3).restart()
    const node = nodesRef.current.find(n => n.id === nodeId)
    if (!node) return
    node.fx = node.x ?? 0
    node.fy = node.y ?? 0
    dragRef.current = { nodeId }

    const rect = svgRef.current?.getBoundingClientRect()
    if (!rect) return

    function onMove(e: MouseEvent) {
      const t = transformRef.current
      const svgW = rect!.width, svgH = rect!.height
      const offsetX = e.clientX - rect!.left
      const offsetY = e.clientY - rect!.top
      // graph coords = (screen - zoom.translate - center) / zoom.scale
      const gx = (offsetX - t.x - svgW / 2) / t.k
      const gy = (offsetY - t.y - svgH / 2) / t.k
      const n = nodesRef.current.find(nn => nn.id === nodeId)
      if (n) { n.fx = gx; n.fy = gy }
    }

    function onUp() {
      const sim2 = simRef.current
      if (sim2) sim2.alphaTarget(0)
      const n = nodesRef.current.find(nn => nn.id === nodeId)
      if (n) { n.fx = null; n.fy = null }
      dragRef.current = null
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }

    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }, [nodesRef, simRef])

  // Klik node → highlight + panel
  const handleNodeClick = useCallback((node: Noda, e: React.MouseEvent) => {
    e.stopPropagation()
    if (highlightedId === node.id) {
      setHighlightedId(null)
      setPanelNode(null)
    } else {
      setHighlightedId(node.id)
      setPanelNode(node)
    }
  }, [highlightedId])

  const handleCanvasClick = useCallback(() => {
    setHighlightedId(null)
    setPanelNode(null)
  }, [])

  const nodes = nodesRef.current
  const edges = edgesRef.current
  const jumlahProfil = nodes.filter(n => n.tipe === 'profil').length
  const selectedKasus = kasus.find(k => k.id_kasus === selectedKasusId)

  const svgCx = typeof window !== 'undefined' ? window.innerWidth / 2 : 720
  const svgCy = typeof window !== 'undefined' ? window.innerHeight / 2 : 400

  // ── Render states ──
  if (loading) {
    return (
      <div className="halaman-la loading-state">
        <div className="la-spinner" />
        <p className="la-loading-text">Memuat data jaringan…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="halaman-la loading-state">
        <AlertTriangle size={32} style={{ color: '#E53E3E' }} />
        <p className="la-loading-text">{error}</p>
      </div>
    )
  }

  return (
    <div className="halaman-la">
      {/* ── Topbar ── */}
      <div className="la-topbar">
        <div className="la-topbar-left">
          <span className="la-topbar-title">Link Analysis</span>
          {selectedKasusId && (
            <span className="la-topbar-meta">
              {jumlahProfil} profil · {edges.length} koneksi
            </span>
          )}
        </div>

        {/* Legend/Filters */}
        <div className="la-legend">
          <label className={`la-legend-item ${!showPertemanan ? 'off' : ''}`}>
            <input type="checkbox" checked={showPertemanan} onChange={e => setShowPertemanan(e.target.checked)} />
            <span className="la-legend-dot" style={{ background: 'rgba(99,179,237,.9)' }} />
            <span>Pertemanan</span>
          </label>
          <label className={`la-legend-item ${!showPostingan ? 'off' : ''}`}>
            <input type="checkbox" checked={showPostingan} onChange={e => setShowPostingan(e.target.checked)} />
            <span className="la-legend-dot" style={{ background: '#F6AD55' }} />
            <span>Postingan</span>
          </label>
          <label className={`la-legend-item ${!showBalasan ? 'off' : ''}`}>
            <input type="checkbox" checked={showBalasan} onChange={e => setShowBalasan(e.target.checked)} />
            <span className="la-legend-dot" style={{ background: '#68D391' }} />
            <span>Balasan</span>
          </label>
        </div>

        {/* Zoom controls */}
        <div className="la-controls">
          <button className="la-ctrl-btn" onClick={() => handleZoom(1.3)} title="Zoom in"><ZoomIn size={14} /></button>
          <button className="la-ctrl-btn" onClick={() => handleZoom(0.77)} title="Zoom out"><ZoomOut size={14} /></button>
          <button className="la-ctrl-btn" onClick={handleFit} title="Fit semua node"><Maximize2 size={14} /></button>
          <button className="la-ctrl-btn" onClick={handleReset} title="Reset zoom"><RefreshCw size={14} /></button>
        </div>

        {/* Tombol keluar */}
        <button
          className="la-close-btn"
          onClick={() => navigate('/search')}
          title="Kembali ke Search & Discovery"
        >
          <X size={15} />
        </button>
      </div>

      {/* ── Kasus selector ── */}
      <div className="la-kasus-selector">
        <span className="la-kasus-label">Analisis Kasus:</span>
        {kasus.map(k => (
          <button
            key={k.id_kasus}
            className={`la-kasus-pill ${selectedKasusId === k.id_kasus ? 'aktif' : ''}`}
            onClick={() => {
              setSelectedKasusId(k.id_kasus)
              setHighlightedId(null)
              setPanelNode(null)
            }}
          >
            <span className="la-kasus-pill-dot" />
            {k.judul}
          </button>
        ))}
      </div>

      {/* ── Body: canvas + side panel ── */}
      <div className="la-body">
        {/* Canvas SVG */}
        <svg
          ref={svgRef}
          className="la-canvas"
          onClick={handleCanvasClick}
        >
          {!selectedKasusId ? (
            /* Empty state di dalam SVG */
            <g>
              <text
                x="50%" y="45%"
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={13}
                fill="rgba(255,255,255,.12)"
              >
                Pilih kasus di atas untuk mulai analisis jaringan
              </text>
              <text
                x="50%" y="52%"
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={10}
                fill="rgba(255,255,255,.06)"
              >
                — atau buka dari Incident Queue, Search, atau Kanvas Investigasi —
              </text>
            </g>
          ) : (
            <g transform={`translate(${transform.x + svgCx},${transform.y + svgCy}) scale(${transform.k})`}>
              {/* Edges */}
              <g className="la-edges">
                {edges.map(e => {
                  const s = e.source as Noda
                  const t = e.target as Noda
                  if (!s.x || !t.x) return null
                  const dimEdge = highlightedId !== null &&
                    s.id !== highlightedId && t.id !== highlightedId &&
                    s.profil_id !== highlightedId && t.profil_id !== highlightedId
                  return (
                    <line
                      key={e.id}
                      x1={s.x} y1={s.y}
                      x2={t.x} y2={t.y}
                      stroke={WARNA_EDGE[e.tipe]}
                      strokeWidth={e.tipe === 'pertemanan' ? (e.kekuatan ?? .5) * 1.5 + .5 : .6}
                      strokeOpacity={dimEdge ? .08 : .7}
                    />
                  )
                })}
              </g>

              {/* Nodes */}
              <g className="la-nodes">
                {/* Post nodes dulu (di bawah) */}
                {nodes
                  .filter(n => n.tipe !== 'profil')
                  .map(n => (
                    <NodeElement
                      key={n.id}
                      node={n}
                      onClick={handleNodeClick}
                      onDragStart={handleNodeDragStart}
                      highlighted={highlightedId === n.id}
                      dimmed={highlightedId !== null && highlightedId !== n.id}
                    />
                  ))}
                {/* Profil nodes di atas */}
                {nodes
                  .filter(n => n.tipe === 'profil')
                  .map(n => (
                    <NodeElement
                      key={n.id}
                      node={n}
                      onClick={handleNodeClick}
                      onDragStart={handleNodeDragStart}
                      highlighted={highlightedId === n.id}
                      isDirect={kasusProfilIds.has(n.id)}
                      dimmed={highlightedId !== null && highlightedId !== n.id}
                    />
                  ))}
              </g>
            </g>
          )}
        </svg>

        {/* Side panel — muncul saat node dipilih */}
        {panelNode && (
          <NodeInfoPanel
            node={panelNode}
            profil={profil}
            postingan={postingan}
            kasusProfilIds={kasusProfilIds}
            kasus={kasus}
            selectedKasusId={selectedKasusId}
            onClose={() => { setPanelNode(null); setHighlightedId(null) }}
            onOpenFullscreen={setFullscreenProfilId}
          />
        )}
      </div>

      {/* ── Footer ── */}
      <div className="la-footer">
        <button className="la-footer-nav" onClick={() => window.history.back()}>
          <ChevronLeft size={12} /> Search & Discovery
        </button>
        <span className="la-footer-current">Link Analysis</span>
        {selectedKasus && (
          <span style={{ opacity: .35, fontSize: 9 }}>
            {kasusProfilIds.size} profil terkait langsung · {filteredProfil.length} total di subgraph
          </span>
        )}
        <span style={{ opacity: .2 }}>H6</span>
      </div>

      {/* Fullscreen profil modal — hanya dibuka dari panel "Buka Profil Lengkap" */}
      {fullscreenProfilId && (() => {
        const p = profil.find(pr => pr.id_profil === fullscreenProfilId)
        if (!p) return null
        return <EntityProfileModal profil={p} onClose={() => setFullscreenProfilId(null)} />
      })()}
    </div>
  )
}
