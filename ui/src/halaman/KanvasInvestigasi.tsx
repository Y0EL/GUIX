/**
 * KanvasInvestigasi — H9 Kanvas Investigasi (Maltego-like)
 *
 * Arsitektur baru:
 * - WorkspaceManager: hierarki Folder → Kanvas di localStorage
 * - Entity palette: drag/klik tipe entitas → SearchModal parameter-based
 * - SearchModal: isi parameter filter → Cari & Pasang → node muncul di canvas
 * - Pivot engine: ekspansi koneksi dari node yang dipilih
 *
 * localStorage key: uix-workspace (multi-folder, multi-canvas)
 */
import {
  createContext, useCallback, useContext, useEffect, useMemo, useRef, useState,
  type ReactNode, type ComponentType,
} from 'react'
import {
  ReactFlow, Background, BackgroundVariant, Controls, MiniMap,
  addEdge, useNodesState, useEdgesState, Handle, Position,
  type Node, type Edge, type NodeTypes, type Connection,
  type NodeProps, type ReactFlowInstance, type XYPosition,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import {
  X, ChevronRight, Users, Activity, MapPin, Bell, Trash2, Save,
  Plus, RefreshCw, Search, Folder, FolderOpen, FileText,
  Clock, MousePointer2,
} from 'lucide-react'
import Fuse, { type FuseOptionKey } from 'fuse.js'
import { muatJson } from '../utils'
import { useArrowNav } from '../hooks/useArrowNav'
import { useNavigate } from 'react-router-dom'
import type { Profil, Kasus, Transaksi, Lokasi, Peringatan, Postingan } from '../types'
import PanelPetaLokasi from '../components/PanelPetaLokasi'
import InsightMiniMap from '../components/InsightMiniMap'

// ─── Tipe inline (tidak ada di types.ts) ─────────────────────────────────────
type Akun = {
  id_akun: string; id_profil: string; platform: string; username: string
  dibuat_pada: string; jumlah_pengikut: number; jumlah_mengikuti: number
  jumlah_posting: number; status_terverifikasi: boolean
  terakhir_aktif_pada: string; petunjuk_minat: string
}
type Kontak = {
  id_kontak: string; id_profil: string; email: string
  telepon_lokal: string; telepon_e164: string
  kota: string; provinsi: string; adalah_utama: boolean
}

// ─── NodeTipe (8 tipe) ────────────────────────────────────────────────────────
export type NodeTipe = 'profil' | 'akun' | 'kontak' | 'transaksi' | 'lokasi' | 'postingan' | 'kasus' | 'peringatan'

// @xyflow/react v12: data harus extends Record<string,unknown>
export interface KiNodeData extends Record<string, unknown> {
  tipe: NodeTipe
  data: Record<string, unknown>
}
export type KiNode = Node<KiNodeData>
export type KiEdge = Edge<Record<string, unknown>>

// ─── Workspace / Folder types ─────────────────────────────────────────────────
interface KanvasEntry {
  id: string; nama: string; dibuat_pada: string
  nodes: KiNode[]; edges: KiEdge[]
  viewport?: { x: number; y: number; zoom: number }
}
interface FolderItem {
  id: string; nama: string; dibuat_pada: string; kanvas: KanvasEntry[]
  pos?: { x: number; y: number }
}
interface WorkspaceStore { version: number; folders: FolderItem[] }

// ─── Search param field definitions ──────────────────────────────────────────
interface FieldDef {
  id: string; label: string; tipe: 'text' | 'select' | 'number'
  opsi?: string[]; placeholder?: string
}

// ─── Konstanta ────────────────────────────────────────────────────────────────
const TIPE_WARNA: Record<NodeTipe, string> = {
  profil: '#D62828', akun: '#3B82F6', kontak: '#14B8A6',
  transaksi: '#4CAF50', lokasi: '#17A2B8', postingan: '#F59E0B',
  kasus: '#F5A623', peringatan: '#9B59B6',
}
const TIPE_LABEL: Record<NodeTipe, string> = {
  profil: 'PROFIL', akun: 'AKUN', kontak: 'KONTAK',
  transaksi: 'TRANSAKSI', lokasi: 'LOKASI', postingan: 'POSTINGAN',
  kasus: 'KASUS', peringatan: 'PERINGATAN',
}
const TIPE_DESC: Record<NodeTipe, string> = {
  profil: 'Identitas subjek', akun: 'Akun media sosial', kontak: 'Data kontak',
  transaksi: 'Transfer finansial', lokasi: 'Titik lokasi', postingan: 'Konten diposting',
  kasus: 'Insiden / kasus', peringatan: 'Sinyal ancaman',
}
const ENTITY_TYPES: NodeTipe[] = ['profil', 'akun', 'kontak', 'transaksi', 'lokasi', 'postingan', 'kasus', 'peringatan']
const PLATFORMS = ['semua', 'twitter', 'instagram', 'facebook', 'tiktok', 'telegram', 'youtube', 'forum', 'whatsapp_channel']
const MINAT_LIST = ['semua','aktivisme','bisnis_online','fashion','fotografi','gaming','hiburan','hukum','keagamaan','kesehatan','keuangan','komunitas_lokal','kuliner','lingkungan','logistik','musik','olahraga','otomotif','pariwisata','pendidikan','pertanian','politik','properti','seni','teknologi','transportasi']

const PARAM_DEFS: Record<NodeTipe, FieldDef[]> = {
  profil: [
    { id: 'nama',            label: 'Nama',                tipe: 'text',   placeholder: 'Cari nama…' },
    { id: 'jenis_kelamin',   label: 'Jenis Kelamin',       tipe: 'select', opsi: ['semua','male','female'] },
    { id: 'kota',            label: 'Kota',                tipe: 'text',   placeholder: 'Contoh: Depok' },
    { id: 'provinsi',        label: 'Provinsi',            tipe: 'text',   placeholder: 'Contoh: Jawa Barat' },
    { id: 'tag_risiko',      label: 'Sinyal Risiko',       tipe: 'select', opsi: ['semua','sinyal_kebakaran_gudang','sinyal_propaganda','sinyal_pendanaan'] },
    { id: 'platform',        label: 'Platform (Akun)',     tipe: 'select', opsi: PLATFORMS },
    { id: 'petunjuk_minat',  label: 'Minat (Akun)',        tipe: 'select', opsi: MINAT_LIST },
  ],
  akun: [
    { id: 'platform',       label: 'Platform',     tipe: 'select', opsi: PLATFORMS },
    { id: 'petunjuk_minat', label: 'Minat',         tipe: 'select', opsi: MINAT_LIST },
    { id: 'username',       label: 'Username',      tipe: 'text',   placeholder: 'Cari username…' },
    { id: 'pengikut_min',   label: 'Pengikut min.', tipe: 'number', placeholder: '0' },
    { id: 'terverifikasi',  label: 'Terverifikasi', tipe: 'select', opsi: ['semua','ya','tidak'] },
  ],
  kontak: [
    { id: 'kota',     label: 'Kota',           tipe: 'text', placeholder: 'Contoh: Depok' },
    { id: 'provinsi', label: 'Provinsi',        tipe: 'text', placeholder: 'Contoh: Jawa Barat' },
    { id: 'email',    label: 'Email (partial)', tipe: 'text', placeholder: 'Contoh: @mail.test' },
    { id: 'telepon',  label: 'Telepon (prefix)',tipe: 'text', placeholder: 'Contoh: 0878' },
  ],
  transaksi: [
    { id: 'kanal',           label: 'Kanal',           tipe: 'select', opsi: ['semua','dompet_digital','transfer_bank','tunai'] },
    { id: 'jumlah_min',      label: 'Jumlah min (Rp)', tipe: 'number', placeholder: '0' },
    { id: 'jumlah_max',      label: 'Jumlah max (Rp)', tipe: 'number', placeholder: '∞' },
    { id: 'petunjuk_tujuan', label: 'Petunjuk Tujuan', tipe: 'text',   placeholder: 'Contoh: perjalanan' },
  ],
  lokasi: [
    { id: 'tipe_lokasi', label: 'Tipe Lokasi', tipe: 'select', opsi: ['semua','basis_rumah','spot_sering','checkin_kasus'] },
    { id: 'kota',        label: 'Kota',        tipe: 'text', placeholder: 'Contoh: Bekasi' },
    { id: 'provinsi',    label: 'Provinsi',    tipe: 'text', placeholder: '' },
  ],
  postingan: [
    { id: 'platform',    label: 'Platform',    tipe: 'select', opsi: PLATFORMS },
    { id: 'tipe_konten', label: 'Tipe Konten', tipe: 'select', opsi: ['semua','komentar','repost','teks','video_pendek','gambar','video'] },
    { id: 'kota',        label: 'Kota',        tipe: 'text', placeholder: '' },
    { id: 'hashtag',     label: 'Hashtag',     tipe: 'text', placeholder: 'Contoh: #fokus' },
  ],
  kasus: [
    { id: 'tipe_kasus', label: 'Tipe',   tipe: 'select', opsi: ['semua','kebakaran_gudang','pendanaan_mencurigakan','propaganda'] },
    { id: 'kota',       label: 'Kota',   tipe: 'text', placeholder: '' },
    { id: 'status',     label: 'Status', tipe: 'select', opsi: ['semua','monitoring','analisis'] },
  ],
  peringatan: [
    { id: 'tingkat_keparahan', label: 'Tingkat',    tipe: 'select', opsi: ['semua','tinggi','menengah','rendah'] },
    { id: 'tipe_sinyal',       label: 'Tipe Sinyal', tipe: 'select', opsi: ['semua','posting_pra_kejadian','narasi_copy_paste','co_lokasi','pola_finansial','posting_tersinkronisasi','overlap_jembatan'] },
  ],
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
function genId() { return Math.random().toString(36).slice(2,10) + Date.now().toString(36).slice(-4) }
function fmtRupiah(n: number) { return 'Rp ' + n.toLocaleString('id-ID') }
function initialsOf(nama: string) { return nama.split(' ').slice(0,2).map(w=>w[0]).join('').toUpperCase() }
function fmtTgl(s: string) { return new Date(s).toLocaleDateString('id-ID',{day:'numeric',month:'short',year:'numeric'}) }

// ─── Full Data Store ──────────────────────────────────────────────────────────
type FullDataStore = {
  profil: Profil[]; akun: Akun[]; kontak: Kontak[]; transaksi: Transaksi[]
  lokasi: Lokasi[]; postingan: Postingan[]; kasus: Kasus[]; peringatan: Peringatan[]
  jaringan: Array<{ id_edge: string; id_profil_sumber: string; id_profil_tujuan: string; tipe_edge: string; bobot: number }>
}

// ─── Fuzzy Search (Fuse.js — mirip vector similarity untuk JSON) ─────────────
//
// Strategi hybrid:
//   • Field enum/select  → exact match (platform, tipe_kasus, kanal, dll.)
//   • Field teks bebas   → Fuse.js fuzzy search (threshold 0.4 ≈ 60% mirip)
//   • Field angka        → range filter biasa
//
// Cara kerja: tiap tipe punya FUSE_KEYS (bobot field teks), dataset di-filter
// dulu pakai exact-match enum, lalu hasilnya di-fuzzy-search pakai query teks.
// Score Fuse: 0=sempurna, 1=tidak cocok → threshold 0.4 masih lolos.

const FUSE_THRESHOLD = 0.4  // toleransi ketidakcocokan (~mirip 60%)

const FUSE_KEYS: Partial<Record<NodeTipe, FuseOptionKey<unknown>[]>> = {
  profil: [
    { name: 'nama_lengkap', weight: 0.5 },
    { name: 'nama_tampil',  weight: 0.4 },
    { name: 'kota',         weight: 0.3 },
    { name: 'provinsi',     weight: 0.2 },
    { name: 'bio',          weight: 0.1 },
  ],
  akun: [
    { name: 'username',    weight: 0.6 },
    { name: 'nama_tampil', weight: 0.3 },
  ],
  kontak: [
    { name: 'nama_lengkap', weight: 0.5 },
    { name: 'kota',         weight: 0.3 },
    { name: 'provinsi',     weight: 0.2 },
    { name: 'email',        weight: 0.2 },
    { name: 'telepon_lokal',weight: 0.1 },
  ],
  transaksi: [
    { name: 'petunjuk_tujuan', weight: 0.6 },
    { name: 'referensi',       weight: 0.2 },
  ],
  lokasi: [
    { name: 'label',    weight: 0.5 },
    { name: 'kota',     weight: 0.4 },
    { name: 'provinsi', weight: 0.2 },
  ],
  postingan: [
    { name: 'teks',    weight: 0.5 },
    { name: 'kota',    weight: 0.2 },
    { name: 'hashtag', weight: 0.3 },
  ],
  kasus: [
    { name: 'judul',    weight: 0.6 },
    { name: 'kota',     weight: 0.3 },
    { name: 'provinsi', weight: 0.1 },
  ],
  peringatan: [
    { name: 'deskripsi', weight: 0.5 },
    { name: 'pesan',     weight: 0.3 },
    { name: 'tipe_sinyal', weight: 0.2 },
  ],
}

function fuzzyFilter<T>(items: T[], keys: FuseOptionKey<T>[], query: string): T[] {
  if (!query.trim()) return items
  const fuse = new Fuse(items, { keys, threshold: FUSE_THRESHOLD, includeScore: false, ignoreLocation: true, minMatchCharLength: 2 })
  return fuse.search(query).map(r => r.item)
}

function cariBerdasarParam(tipe: NodeTipe, params: Record<string,string>, store: FullDataStore): unknown[] {
  const hasParam = (k: string) => params[k] && params[k] !== 'semua' && params[k] !== ''

  switch (tipe) {
    case 'profil': {
      // Exact: enum akun (platform, minat) → dapat kandidat id_profil
      let candidateIds: Set<string> | null = null
      if (hasParam('platform')) {
        const ids = new Set(store.akun.filter(a => a.platform === params.platform).map(a => a.id_profil))
        candidateIds = ids
      }
      if (hasParam('petunjuk_minat')) {
        const ids = new Set(store.akun.filter(a => a.petunjuk_minat === params.petunjuk_minat).map(a => a.id_profil))
        candidateIds = candidateIds ? new Set([...candidateIds].filter(id => ids.has(id))) : ids
      }
      // Exact: enum fields
      let pool = store.profil.filter(p => {
        if (candidateIds && !candidateIds.has(p.id_profil)) return false
        if (hasParam('jenis_kelamin') && p.jenis_kelamin !== params.jenis_kelamin) return false
        if (hasParam('tag_risiko') && !p.tag_risiko.includes(params.tag_risiko)) return false
        return true
      })
      // Fuzzy: gabung query teks (nama + kota + provinsi jadi satu query)
      const tekstual = [params.nama, params.kota, params.provinsi].filter(Boolean).join(' ')
      if (tekstual.trim()) pool = fuzzyFilter(pool, FUSE_KEYS.profil!, tekstual)
      return pool.slice(0, 20)
    }
    case 'akun': {
      let pool = store.akun.filter(a => {
        if (hasParam('platform') && a.platform !== params.platform) return false
        if (hasParam('petunjuk_minat') && a.petunjuk_minat !== params.petunjuk_minat) return false
        if (hasParam('pengikut_min') && !isNaN(+params.pengikut_min) && a.jumlah_pengikut < +params.pengikut_min) return false
        if (hasParam('terverifikasi') && a.status_terverifikasi !== (params.terverifikasi === 'ya')) return false
        return true
      })
      if (hasParam('username')) pool = fuzzyFilter(pool, FUSE_KEYS.akun!, params.username)
      return pool.slice(0, 20)
    }
    case 'kontak': {
      const tekstual = [params.nama, params.kota, params.provinsi].filter(Boolean).join(' ')
      let pool = store.kontak as unknown[]
      if (tekstual.trim()) pool = fuzzyFilter(store.kontak, FUSE_KEYS.kontak!, tekstual)
      else pool = store.kontak
      if (hasParam('email')) pool = fuzzyFilter(pool as typeof store.kontak, [{ name: 'email', weight: 1 }], params.email)
      if (hasParam('telepon')) pool = fuzzyFilter(pool as typeof store.kontak, [{ name: 'telepon_lokal', weight: 1 }], params.telepon)
      return (pool as typeof store.kontak).slice(0, 20)
    }
    case 'transaksi': {
      let pool = store.transaksi.filter(t => {
        if (hasParam('kanal') && t.kanal !== params.kanal) return false
        if (hasParam('jumlah_min') && !isNaN(+params.jumlah_min) && t.jumlah_idr < +params.jumlah_min) return false
        if (hasParam('jumlah_max') && !isNaN(+params.jumlah_max) && t.jumlah_idr > +params.jumlah_max) return false
        return true
      })
      if (hasParam('petunjuk_tujuan')) pool = fuzzyFilter(pool, FUSE_KEYS.transaksi!, params.petunjuk_tujuan)
      return pool.slice(0, 20)
    }
    case 'lokasi': {
      let pool = store.lokasi.filter(l => {
        if (hasParam('tipe_lokasi') && l.tipe_lokasi !== params.tipe_lokasi) return false
        return true
      })
      const tekstual = [params.kota, params.provinsi, params.label].filter(Boolean).join(' ')
      if (tekstual.trim()) pool = fuzzyFilter(pool, FUSE_KEYS.lokasi!, tekstual)
      return pool.slice(0, 20)
    }
    case 'postingan': {
      let pool = store.postingan.filter(p => {
        if (hasParam('platform') && p.platform !== params.platform) return false
        if (hasParam('tipe_konten') && p.tipe_konten !== params.tipe_konten) return false
        return true
      })
      const tekstual = [params.kota, params.teks, params.hashtag].filter(Boolean).join(' ')
      if (tekstual.trim()) pool = fuzzyFilter(pool, FUSE_KEYS.postingan!, tekstual)
      return pool.slice(0, 20)
    }
    case 'kasus': {
      let pool = store.kasus.filter(k => {
        if (hasParam('tipe_kasus') && k.tipe_kasus !== params.tipe_kasus) return false
        if (hasParam('status') && k.status !== params.status) return false
        return true
      })
      const tekstual = [params.judul, params.kota].filter(Boolean).join(' ')
      if (tekstual.trim()) pool = fuzzyFilter(pool, FUSE_KEYS.kasus!, tekstual)
      return pool.slice(0, 20)
    }
    case 'peringatan': {
      let pool = store.peringatan.filter(p => {
        if (hasParam('tingkat_keparahan') && p.tingkat_keparahan !== params.tingkat_keparahan) return false
        if (hasParam('tipe_sinyal') && p.tipe_sinyal !== params.tipe_sinyal) return false
        return true
      })
      const tekstual = [params.deskripsi, params.pesan].filter(Boolean).join(' ')
      if (tekstual.trim()) pool = fuzzyFilter(pool, FUSE_KEYS.peringatan!, tekstual)
      return pool.slice(0, 20)
    }
    default: return []
  }
}

const ID_FIELD: Record<NodeTipe, string> = {
  profil: 'id_profil', akun: 'id_akun', kontak: 'id_kontak',
  transaksi: 'id_transaksi', lokasi: 'id_lokasi', postingan: 'id_posting',
  kasus: 'id_kasus', peringatan: 'id_peringatan',
}

function hasilKeNodes(tipe: NodeTipe, items: unknown[], dropPos: XYPosition, existingIds: Set<string>): KiNode[] {
  const out: KiNode[] = []
  let placed = 0
  const total = items.length
  items.forEach(item => {
    const rec = item as Record<string, unknown>
    const idVal = rec[ID_FIELD[tipe]] as string
    const nodeId = `${tipe}-${idVal}`
    if (existingIds.has(nodeId)) return
    const angle = total === 1 ? 0 : (placed / total) * Math.PI * 2
    const radius = total === 1 ? 0 : Math.min(130 + total * 8, 250)
    out.push({
      id: nodeId, type: tipe,
      position: { x: dropPos.x + Math.cos(angle) * radius, y: dropPos.y + Math.sin(angle) * radius },
      data: { tipe, data: rec },
    } as KiNode)
    placed++
  })
  return out
}

// ─── Context (removeKiNode untuk node components) ─────────────────────────────
const KanvasCtx = createContext<{ removeKiNode: (id: string) => void }>({ removeKiNode: () => {} })
function useKanvasCtx() { return useContext(KanvasCtx) }

// ─── Node Components ──────────────────────────────────────────────────────────
function BaseNodeShell({ tipe, selected, onRemove, children }: {
  tipe: NodeTipe; selected: boolean; onRemove: () => void; children: ReactNode
}) {
  const warna = TIPE_WARNA[tipe]
  return (
    <div className={`ki-node ki-node-${tipe}${selected ? ' ki-node-sel' : ''}`} style={{ borderColor: warna + (selected ? '' : '55') }}>
      <Handle type="target" position={Position.Left} className="ki-handle" />
      <Handle type="source" position={Position.Right} className="ki-handle" />
      <div className="ki-node-header" style={{ background: warna + '1a', borderBottomColor: warna + '33' }}>
        <span className="ki-node-tipe" style={{ color: warna }}>{TIPE_LABEL[tipe]}</span>
        <button className="ki-node-close" onClick={e => { e.stopPropagation(); onRemove() }} title="Hapus"><X size={9} /></button>
      </div>
      <div className="ki-node-body">{children}</div>
    </div>
  )
}

function EntityNode({ data, selected, id }: NodeProps<KiNode>) {
  const { removeKiNode } = useKanvasCtx()
  const tipe = data.tipe
  const d = data.data
  return (
    <BaseNodeShell tipe={tipe} selected={!!selected} onRemove={() => removeKiNode(id)}>
      {tipe === 'profil' && (() => {
        const p = d as unknown as Profil
        return (<>
          <div className="ki-profil-avatar"><span>{initialsOf(p.nama_lengkap)}</span></div>
          <div className="ki-node-nama">{p.nama_tampil}</div>
          <div className="ki-node-sub">{p.kota}, {p.provinsi}</div>
          {p.tag_risiko.length > 0 && <div className="ki-node-tags">{p.tag_risiko.slice(0,2).map(t=><span key={t} className="ki-tag" style={{borderColor:'#D6282833',color:'#D62828'}}>{t.replace('sinyal_','')}</span>)}</div>}
        </>)
      })()}
      {tipe === 'akun' && (() => {
        const a = d as unknown as Akun
        return (<>
          <div className="ki-node-nama" style={{fontSize:11}}>{a.username}</div>
          <div className="ki-node-sub">{a.platform} · {a.jumlah_pengikut.toLocaleString('id-ID')}</div>
          <div className="ki-node-sub" style={{fontSize:9,opacity:.5}}>{a.petunjuk_minat}</div>
        </>)
      })()}
      {tipe === 'kontak' && (() => {
        const k = d as unknown as Kontak
        return (<>
          <div className="ki-node-nama" style={{fontSize:10}}>{k.email}</div>
          <div className="ki-node-sub">{k.kota}, {k.provinsi}</div>
          <div className="ki-node-sub" style={{fontSize:9,opacity:.5}}>{k.telepon_lokal}</div>
        </>)
      })()}
      {tipe === 'transaksi' && (() => {
        const t = d as unknown as Transaksi
        return (<>
          <div className="ki-node-nama" style={{fontSize:11}}>{fmtRupiah(t.jumlah_idr)}</div>
          <div className="ki-node-sub">{t.kanal.replace(/_/g,' ')}</div>
          <div className="ki-node-sub" style={{fontSize:9,opacity:.4,fontFamily:'monospace'}}>{t.referensi}</div>
        </>)
      })()}
      {tipe === 'lokasi' && (() => {
        const l = d as unknown as Lokasi
        return (<>
          <div className="ki-node-nama" style={{fontSize:11}}>{l.label || l.tipe_lokasi}</div>
          <div className="ki-node-sub">{l.kota}, {l.provinsi}</div>
          <div className="ki-node-sub" style={{fontSize:9,opacity:.35,fontFamily:'monospace'}}>{l.latitude.toFixed(3)}, {l.longitude.toFixed(3)}</div>
        </>)
      })()}
      {tipe === 'postingan' && (() => {
        const p = d as unknown as Postingan
        return (<>
          <div className="ki-node-nama" style={{fontSize:10}}>{p.konten.length>55?p.konten.slice(0,55)+'…':p.konten}</div>
          <div className="ki-node-sub">{p.platform} · {p.tipe_konten}</div>
          <div className="ki-node-sub" style={{fontSize:9,opacity:.4}}>{p.kota}</div>
        </>)
      })()}
      {tipe === 'kasus' && (() => {
        const k = d as unknown as Kasus
        const sw = k.status==='eskalasi'?'#E5282A':k.status==='analisis'?'#F5A623':'#4CAF50'
        return (<>
          <div className="ki-node-nama" style={{fontSize:10}}>{k.judul.length>42?k.judul.slice(0,42)+'…':k.judul}</div>
          <div className="ki-node-sub">{k.tipe_kasus.replace(/_/g,' ')}</div>
          <div className="ki-node-tags"><span className="ki-tag" style={{borderColor:sw+'44',color:sw}}>{k.status}</span></div>
        </>)
      })()}
      {tipe === 'peringatan' && (() => {
        const p = d as unknown as Peringatan
        const sw = p.tingkat_keparahan==='tinggi'?'#E5282A':p.tingkat_keparahan==='menengah'?'#F5A623':'#4CAF50'
        return (<>
          <div className="ki-node-nama" style={{fontSize:10}}>{p.deskripsi.length>50?p.deskripsi.slice(0,50)+'…':p.deskripsi}</div>
          <div className="ki-node-sub">{p.tipe_sinyal.replace(/_/g,' ')}</div>
          <div className="ki-node-tags"><span className="ki-tag" style={{borderColor:sw+'44',color:sw}}>{p.tingkat_keparahan}</span></div>
        </>)
      })()}
    </BaseNodeShell>
  )
}

const NODE_TYPES: NodeTypes = Object.fromEntries(
  ENTITY_TYPES.map(t => [t, EntityNode as ComponentType<NodeProps>])
)

// ─── Pivot engine ─────────────────────────────────────────────────────────────
function toRec(v: unknown): Record<string,unknown> { return v as Record<string,unknown> }

function pivotProfilToJaringan(sourceId: string, store: FullDataStore, existingIds: Set<string>, pos: XYPosition): { nodes: KiNode[]; edges: KiEdge[] } {
  const teman = store.jaringan.filter(j=>j.id_profil_sumber===sourceId||j.id_profil_tujuan===sourceId)
  const newNodes: KiNode[] = []; const newEdges: KiEdge[] = []; let idx = 0
  teman.forEach(j => {
    const lawanId = j.id_profil_sumber===sourceId ? j.id_profil_tujuan : j.id_profil_sumber
    const nodeId = `profil-${lawanId}`
    if (!existingIds.has(nodeId)) {
      const profil = store.profil.find(p=>p.id_profil===lawanId)
      if (!profil) return
      const angle = (idx / Math.max(teman.length,1)) * Math.PI * 2
      newNodes.push({ id: nodeId, type: 'profil', position: { x: pos.x+Math.cos(angle)*220, y: pos.y+Math.sin(angle)*220 }, data: { tipe: 'profil' as const, data: toRec(profil) } })
      existingIds.add(nodeId); idx++
    }
    newEdges.push({ id: `e-${j.id_edge}`, source: `profil-${sourceId}`, target: nodeId, data: { tipe: j.tipe_edge, bobot: j.bobot }, style: { stroke: TIPE_WARNA.profil+'80', strokeWidth: Math.max(1, j.bobot*3) }, animated: j.bobot>0.7 })
  })
  return { nodes: newNodes, edges: newEdges }
}

function pivotProfilToTransaksi(sourceId: string, store: FullDataStore, existingIds: Set<string>, pos: XYPosition): { nodes: KiNode[]; edges: KiEdge[] } {
  const txs = store.transaksi.filter(t=>t.id_profil_sumber===sourceId||t.id_profil_tujuan===sourceId)
  const newNodes: KiNode[] = []; const newEdges: KiEdge[] = []
  txs.forEach((t, idx) => {
    const arah = t.id_profil_sumber===sourceId ? 'kirim' : 'terima'
    const nodeId = `transaksi-${t.id_transaksi}`
    if (existingIds.has(nodeId)) return
    const angle = (idx / Math.max(txs.length,1)) * Math.PI - Math.PI/2
    newNodes.push({ id: nodeId, type: 'transaksi', position: { x: pos.x+Math.cos(angle)*200+120, y: pos.y+Math.sin(angle)*200 }, data: { tipe: 'transaksi' as const, data: { ...toRec(t), arah } } })
    newEdges.push({ id: `e-tx-${t.id_transaksi}-${sourceId}`, source: arah==='kirim'?`profil-${sourceId}`:nodeId, target: arah==='kirim'?nodeId:`profil-${sourceId}`, data: { tipe: 'transaksi' }, style: { stroke: TIPE_WARNA.transaksi+'90', strokeWidth: 1.5 }, animated: true })
    existingIds.add(nodeId)
  })
  return { nodes: newNodes, edges: newEdges }
}

function pivotProfilToLokasi(sourceId: string, store: FullDataStore, existingIds: Set<string>, pos: XYPosition): { nodes: KiNode[]; edges: KiEdge[] } {
  const loks = store.lokasi.filter(l=>l.id_profil===sourceId)
  const newNodes: KiNode[] = []; const newEdges: KiEdge[] = []
  loks.forEach((l, idx) => {
    const nodeId = `lokasi-${l.id_lokasi}`
    if (existingIds.has(nodeId)) return
    const angle = (idx / Math.max(loks.length,1)) * Math.PI + Math.PI/2
    newNodes.push({ id: nodeId, type: 'lokasi', position: { x: pos.x+Math.cos(angle)*200, y: pos.y+Math.sin(angle)*200+120 }, data: { tipe: 'lokasi' as const, data: toRec(l) } })
    newEdges.push({ id: `e-lok-${l.id_lokasi}-${sourceId}`, source: `profil-${sourceId}`, target: nodeId, data: { tipe: 'lokasi' }, style: { stroke: TIPE_WARNA.lokasi+'80', strokeWidth: 1 } })
    existingIds.add(nodeId)
  })
  return { nodes: newNodes, edges: newEdges }
}

function pivotKasusToProfil(kasusId: string, store: FullDataStore, existingIds: Set<string>, pos: XYPosition): { nodes: KiNode[]; edges: KiEdge[] } {
  const profils = store.profil.filter(p=>p.tautan_kasus.some(tk=>tk.id_kasus===kasusId))
  const newNodes: KiNode[] = []; const newEdges: KiEdge[] = []
  profils.forEach((p, idx) => {
    const nodeId = `profil-${p.id_profil}`
    if (!existingIds.has(nodeId)) {
      const angle = (idx / Math.max(profils.length,1)) * Math.PI * 2
      newNodes.push({ id: nodeId, type: 'profil', position: { x: pos.x+Math.cos(angle)*220, y: pos.y+Math.sin(angle)*220 }, data: { tipe: 'profil' as const, data: toRec(p) } })
      existingIds.add(nodeId)
    }
    newEdges.push({ id: `e-kasus-${kasusId}-${p.id_profil}`, source: `kasus-${kasusId}`, target: nodeId, data: { tipe: 'tautan_kasus' }, style: { stroke: TIPE_WARNA.kasus+'80', strokeWidth: 1.5 } })
  })
  return { nodes: newNodes, edges: newEdges }
}

function pivotKasusToPeringatan(kasusId: string, store: FullDataStore, existingIds: Set<string>, pos: XYPosition): { nodes: KiNode[]; edges: KiEdge[] } {
  const perings = store.peringatan.filter(p=>p.id_kasus===kasusId)
  const newNodes: KiNode[] = []; const newEdges: KiEdge[] = []
  perings.forEach((p, idx) => {
    const nodeId = `peringatan-${p.id_peringatan}`
    if (existingIds.has(nodeId)) return
    const angle = (idx / Math.max(perings.length,1)) * Math.PI
    newNodes.push({ id: nodeId, type: 'peringatan', position: { x: pos.x+Math.cos(angle)*200, y: pos.y+Math.sin(angle)*200-120 }, data: { tipe: 'peringatan' as const, data: toRec(p) } })
    newEdges.push({ id: `e-per-${p.id_peringatan}-${kasusId}`, source: `kasus-${kasusId}`, target: nodeId, data: { tipe: 'peringatan' }, style: { stroke: TIPE_WARNA.peringatan+'80', strokeWidth: 1 } })
    existingIds.add(nodeId)
  })
  return { nodes: newNodes, edges: newEdges }
}

// ─── Auto-connect: buat edge otomatis antar node berdasarkan relasi data ────
function buatAutoEdges(allNodes: KiNode[], store: FullDataStore, existingEids: Set<string>): KiEdge[] {
  const idSet = new Set(allNodes.map(n => n.id))
  const result: KiEdge[] = []
  const seen = new Set<string>()
  function add(e: KiEdge) {
    if (seen.has(e.id) || existingEids.has(e.id)) return
    if (!idSet.has(e.source) || !idSet.has(e.target)) return
    seen.add(e.id); result.push(e)
  }
  // profil ↔ profil via jaringan
  store.jaringan.forEach(j => {
    add({ id: `e-${j.id_edge}`, source: `profil-${j.id_profil_sumber}`, target: `profil-${j.id_profil_tujuan}`,
      data: { tipe: j.tipe_edge }, style: { stroke: TIPE_WARNA.profil+'80', strokeWidth: Math.max(1.2, j.bobot*3) }, animated: j.bobot>0.7 })
  })
  // profil → transaksi
  store.transaksi.forEach(t => {
    const tx = `transaksi-${t.id_transaksi}`
    add({ id: `e-tx-src-${t.id_transaksi}`, source: `profil-${t.id_profil_sumber}`, target: tx, data:{tipe:'transaksi'}, style:{stroke:TIPE_WARNA.transaksi+'90',strokeWidth:1.5}, animated:true })
    add({ id: `e-tx-tgt-${t.id_transaksi}`, source: tx, target: `profil-${t.id_profil_tujuan}`, data:{tipe:'transaksi'}, style:{stroke:TIPE_WARNA.transaksi+'90',strokeWidth:1.5}, animated:true })
  })
  // profil → lokasi
  store.lokasi.forEach(l => {
    add({ id: `e-lok-${l.id_lokasi}-${l.id_profil}`, source: `profil-${l.id_profil}`, target: `lokasi-${l.id_lokasi}`, data:{tipe:'lokasi'}, style:{stroke:TIPE_WARNA.lokasi+'80',strokeWidth:1} })
  })
  // profil → akun
  store.akun.forEach(a => {
    add({ id: `e-akun-${a.id_akun}`, source: `profil-${a.id_profil}`, target: `akun-${a.id_akun}`, data:{tipe:'akun'}, style:{stroke:TIPE_WARNA.akun+'80',strokeWidth:1} })
  })
  // profil → kontak
  store.kontak.forEach(k => {
    add({ id: `e-kontak-${k.id_kontak}`, source: `profil-${k.id_profil}`, target: `kontak-${k.id_kontak}`, data:{tipe:'kontak'}, style:{stroke:TIPE_WARNA.kontak+'80',strokeWidth:1} })
  })
  // profil → postingan
  store.postingan.forEach(p => {
    add({ id: `e-post-${p.id_posting}`, source: `profil-${p.id_profil}`, target: `postingan-${p.id_posting}`, data:{tipe:'postingan'}, style:{stroke:TIPE_WARNA.postingan+'80',strokeWidth:1} })
  })
  // kasus → profil via tautan_kasus
  store.profil.forEach(p => {
    p.tautan_kasus.forEach(tk => {
      add({ id: `e-kasus-${tk.id_kasus}-${p.id_profil}`, source: `kasus-${tk.id_kasus}`, target: `profil-${p.id_profil}`, data:{tipe:'tautan_kasus'}, style:{stroke:TIPE_WARNA.kasus+'80',strokeWidth:1.5} })
    })
  })
  // kasus → peringatan
  store.peringatan.forEach(p => {
    add({ id: `e-per-${p.id_peringatan}-${p.id_kasus}`, source: `kasus-${p.id_kasus}`, target: `peringatan-${p.id_peringatan}`, data:{tipe:'peringatan'}, style:{stroke:TIPE_WARNA.peringatan+'80',strokeWidth:1} })
  })
  return result
}

// ─── Workspace utilities ──────────────────────────────────────────────────────
const WS_KEY = 'uix-workspace'
const DEFAULT_WS: WorkspaceStore = { version: 1, folders: [] }
function muatWorkspace(): WorkspaceStore {
  try { const raw = localStorage.getItem(WS_KEY); if (!raw) return DEFAULT_WS; const p = JSON.parse(raw) as WorkspaceStore; return p.folders ? p : DEFAULT_WS } catch { return DEFAULT_WS }
}
function simpanWorkspace(ws: WorkspaceStore) { localStorage.setItem(WS_KEY, JSON.stringify(ws)) }

// ─── WorkspaceManager Component ───────────────────────────────────────────────
interface WMCtxValue { bukaPopup: (id: string) => void }
const WMCtx = createContext<WMCtxValue>({ bukaPopup: () => {} })

interface WMNodeData extends Record<string, unknown> { folder: FolderItem }
type WMFolderNode = Node<WMNodeData>

function FolderNodeUI({ data, selected }: NodeProps) {
  const folder = (data as unknown as WMNodeData).folder
  return (
    <div className={`wm-node${selected ? ' wm-node-selected' : ''}`}>
      <Folder size={40} className="wm-node-icon-svg" />
      <div className="wm-node-nama">{folder.nama}</div>
      <div className="wm-node-meta">{folder.kanvas.length} kanvas</div>
    </div>
  )
}
const WM_NODE_TYPES: NodeTypes = { folderNode: FolderNodeUI as ComponentType<NodeProps> }

interface WMProps {
  workspace: WorkspaceStore
  setWorkspace: React.Dispatch<React.SetStateAction<WorkspaceStore>>
  onBukaKanvas: (fi: number, ki: number) => void
}
function WorkspaceManager({ workspace, setWorkspace, onBukaKanvas }: WMProps) {
  const [popupId, setPopupId] = useState<string | null>(null)
  const [modal, setModal] = useState<{ tipe: 'folder' } | { tipe: 'kanvas'; folderId: string } | null>(null)
  const [nama, setNama] = useState('')

  const toRFNodes = useCallback((folders: FolderItem[]): WMFolderNode[] =>
    folders.map((f, i) => ({
      id: f.id,
      type: 'folderNode',
      position: f.pos ?? { x: (i % 6) * 200, y: Math.floor(i / 6) * 180 },
      data: { folder: f },
      selected: false,
    }))
  , [])

  const [nodes, setNodes, onNodesChange] = useNodesState<WMFolderNode>(toRFNodes(workspace.folders))

  useEffect(() => {
    setNodes(toRFNodes(workspace.folders))
  }, [workspace.folders, setNodes, toRFNodes])

  const onNodeDragStop = useCallback((_ev: React.MouseEvent, node: WMFolderNode) => {
    const updated: WorkspaceStore = {
      ...workspace,
      folders: workspace.folders.map(f =>
        f.id !== node.id ? f : { ...f, pos: { x: Math.round(node.position.x), y: Math.round(node.position.y) } }
      ),
    }
    setWorkspace(updated)
    simpanWorkspace(updated)
  }, [workspace, setWorkspace])

  function buatFolder() {
    if (!nama.trim()) return
    const n = workspace.folders.length
    const updated: WorkspaceStore = {
      ...workspace,
      folders: [...workspace.folders, {
        id: `fldr-${genId()}`, nama: nama.trim(), dibuat_pada: new Date().toISOString(),
        kanvas: [],
        pos: { x: 80 + (n % 6) * 200, y: 80 + Math.floor(n / 6) * 180 },
      }],
    }
    setWorkspace(updated); simpanWorkspace(updated); setModal(null); setNama('')
  }
  function buatKanvas(folderId: string) {
    if (!nama.trim()) return
    const updated: WorkspaceStore = {
      ...workspace,
      folders: workspace.folders.map(f =>
        f.id !== folderId ? f
          : { ...f, kanvas: [...f.kanvas, { id: `cvs-${genId()}`, nama: nama.trim(), dibuat_pada: new Date().toISOString(), nodes: [], edges: [] }] }
      ),
    }
    setWorkspace(updated); simpanWorkspace(updated); setModal(null); setNama('')
  }
  function hapusFolder(folderId: string) {
    const f = workspace.folders.find(f => f.id === folderId)
    if (!f || !window.confirm(`Hapus folder "${f.nama}"?`)) return
    const updated: WorkspaceStore = { ...workspace, folders: workspace.folders.filter(f => f.id !== folderId) }
    setWorkspace(updated); simpanWorkspace(updated)
    if (popupId === folderId) setPopupId(null)
  }
  function hapusKanvas(folderId: string, kanvasId: string) {
    const f = workspace.folders.find(f => f.id === folderId)
    const cvs = f?.kanvas.find(k => k.id === kanvasId)
    if (!cvs || !window.confirm(`Hapus kanvas "${cvs.nama}"?`)) return
    const updated: WorkspaceStore = {
      ...workspace,
      folders: workspace.folders.map(f =>
        f.id !== folderId ? f : { ...f, kanvas: f.kanvas.filter(k => k.id !== kanvasId) }
      ),
    }
    setWorkspace(updated); simpanWorkspace(updated)
  }
  function bukaKanvasById(folderId: string, kanvasId: string) {
    const fi = workspace.folders.findIndex(f => f.id === folderId)
    const ki = workspace.folders[fi]?.kanvas.findIndex(k => k.id === kanvasId) ?? -1
    if (fi >= 0 && ki >= 0) onBukaKanvas(fi, ki)
  }

  const popupFolder = workspace.folders.find(f => f.id === popupId) ?? null

  return (
    <WMCtx.Provider value={useMemo(() => ({ bukaPopup: id => setPopupId(p => p === id ? null : id) }), [])}>
      <div className="wm-root">
        <div className="wm-canvas-toolbar">
          <div className="wm-canvas-titlebar">
            <span className="wm-canvas-title">Investigasi</span>
            <span className="wm-canvas-hint">Seret folder ke mana saja · scroll untuk zoom · klik untuk buka</span>
          </div>
          <button className="wm-btn-primer" onClick={() => { setNama(''); setModal({ tipe: 'folder' }) }}>
            <Plus size={14} /> Folder Baru
          </button>
        </div>
        <div className="wm-rf-wrap">
          <ReactFlow<WMFolderNode, never>
            nodes={nodes}
            edges={[]}
            onNodesChange={onNodesChange}
            onNodeDragStop={onNodeDragStop}
            nodeTypes={WM_NODE_TYPES}
            onNodeClick={(_ev, node) => setPopupId(p => p === node.id ? null : node.id)}
            fitView={workspace.folders.length > 0}
            fitViewOptions={{ padding: 0.5 }}
            minZoom={0.1}
            maxZoom={4}
            panOnDrag
            zoomOnScroll
            deleteKeyCode={null}
            selectionOnDrag={false}
            proOptions={{ hideAttribution: true }}
          >
            <Background variant={BackgroundVariant.Dots} gap={28} size={1.2} color="rgba(255,255,255,.06)" />
            <Controls showInteractive={false} />
            {workspace.folders.length === 0 && (
              <div className="wm-canvas-empty">
                <FolderOpen size={56} style={{ opacity: .07 }} />
                <p>Belum ada folder investigasi.</p>
                <p style={{ fontSize: 11, opacity: .3 }}>Klik "Folder Baru" — lalu seret folder ke mana saja.</p>
              </div>
            )}
          </ReactFlow>
          {popupFolder && (
            <div className="wm-popup">
              <div className="wm-popup-hdr">
                <Folder size={13} style={{ color: '#F5A623' }} />
                <span className="wm-popup-nama">{popupFolder.nama}</span>
                <button className="wm-icon-btn" onClick={() => hapusFolder(popupFolder.id)} title="Hapus folder"><Trash2 size={10} /></button>
                <button className="wm-icon-btn" onClick={() => setPopupId(null)}><X size={12} /></button>
              </div>
              <div className="wm-popup-list">
                {popupFolder.kanvas.length === 0 && <div className="wm-popup-empty">Belum ada kanvas.</div>}
                {popupFolder.kanvas.map(cvs => (
                  <div key={cvs.id} className="wm-popup-item">
                    <FileText size={11} style={{ color: '#888', flexShrink: 0 }} />
                    <span className="wm-kanvas-nama">{cvs.nama}</span>
                    <span className="wm-kanvas-meta">{cvs.nodes.length} node</span>
                    <button className="wm-btn-buka" onClick={() => bukaKanvasById(popupFolder.id, cvs.id)}>Buka</button>
                    <button className="wm-icon-btn" onClick={() => hapusKanvas(popupFolder.id, cvs.id)}><X size={9} /></button>
                  </div>
                ))}
              </div>
              <button className="wm-btn-tambah-kanvas" onClick={() => { setNama(''); setModal({ tipe: 'kanvas', folderId: popupFolder.id }) }}>
                <Plus size={11} /> Buat Kanvas Baru
              </button>
            </div>
          )}
        </div>
        {modal && (
          <div className="wm-overlay" onClick={() => setModal(null)}>
            <div className="wm-modal" onClick={e => e.stopPropagation()}>
              <div className="wm-modal-title">{modal.tipe === 'folder' ? 'Buat Folder Baru' : 'Buat Kanvas Baru'}</div>
              <input className="wm-modal-input" autoFocus
                placeholder={modal.tipe === 'folder' ? 'Nama folder investigasi…' : 'Nama kanvas / sandbox…'}
                value={nama} onChange={e => setNama(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') modal.tipe === 'folder' ? buatFolder() : buatKanvas((modal as { folderId: string }).folderId) }}
              />
              <div className="wm-modal-actions">
                <button className="wm-btn-sekunder" onClick={() => setModal(null)}>Batal</button>
                <button className="wm-btn-primer" onClick={() => modal.tipe === 'folder' ? buatFolder() : buatKanvas((modal as { folderId: string }).folderId)}>Buat</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </WMCtx.Provider>
  )
}



// ─── Search Modal ─────────────────────────────────────────────────────────────
interface SMProps {
  tipe: NodeTipe; dropPos: XYPosition; store: FullDataStore
  existingIds: Set<string>; onDeploy: (n: KiNode[]) => void; onTutup: () => void
}
function SearchModal({ tipe, dropPos, store, existingIds, onDeploy, onTutup }: SMProps) {
  const [params, setParams] = useState<Record<string,string>>({})
  const [count, setCount] = useState<number | null>(null)
  const setP = (id: string, v: string) => { setParams(prev=>({...prev,[id]:v})); setCount(null) }
  function cariDanDeploy() {
    const hasil = cariBerdasarParam(tipe, params, store)
    setCount(hasil.length)
    if (hasil.length === 0) return
    const nodesBaru = hasilKeNodes(tipe, hasil, dropPos, existingIds)
    if (nodesBaru.length > 0) onDeploy(nodesBaru)
  }
  const warna = TIPE_WARNA[tipe]
  return (
    <div className="sm-overlay" onClick={onTutup}>
      <div className="sm-box" onClick={e=>e.stopPropagation()}>
        <div className="sm-header" style={{borderBottomColor:warna+'44'}}>
          <span className="sm-badge" style={{background:warna+'20',color:warna}}>{TIPE_LABEL[tipe]}</span>
          <h3 className="sm-title">Cari & Pasang {TIPE_LABEL[tipe]}</h3>
          <button className="sm-close" onClick={onTutup}><X size={13}/></button>
        </div>
        <p className="sm-desc">Isi parameter filter di bawah. Kosongkan field untuk tidak membatasi hasil.</p>
        <div className="sm-form">
          {PARAM_DEFS[tipe].map(f => (
            <div key={f.id} className="sm-field">
              <label className="sm-label">{f.label}</label>
              {f.tipe === 'select'
                ? <select className="sm-select" value={params[f.id]??''} onChange={e=>setP(f.id,e.target.value)}>
                    {f.opsi!.map(o=><option key={o} value={o==='semua'?'':o}>{o==='semua'?'— semua —':o}</option>)}
                  </select>
                : <input type={f.tipe==='number'?'number':'text'} className="sm-input"
                    placeholder={f.placeholder??''} value={params[f.id]??''} onChange={e=>setP(f.id,e.target.value)}
                    onKeyDown={e=>{if(e.key==='Enter') cariDanDeploy()}}
                  />
              }
            </div>
          ))}
        </div>
        <div className="sm-footer">
          {count !== null && (
            <span className={`sm-count${count===0?' sm-count-empty':''}`}>
              {count===0 ? 'Tidak ada hasil.' : `${count} hasil ditemukan — siap dipasang ke kanvas`}
            </span>
          )}
          <button className="sm-btn-cari" style={{background:warna}} onClick={cariDanDeploy}>
            <Search size={12}/> Cari & Pasang
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Komponen Utama ───────────────────────────────────────────────────────────
export default function KanvasInvestigasi() {
  useArrowNav()
  const navigate = useNavigate()
  const rfWrapper = useRef<HTMLDivElement>(null)
  const [rfInstance, setRfInstance] = useState<ReactFlowInstance<KiNode, KiEdge> | null>(null)

  // ── Workspace state ──
  const [workspace, setWorkspace] = useState<WorkspaceStore>(() => muatWorkspace())
  const [activeFolderIdx, setActiveFolderIdx] = useState<number | null>(null)
  const [activeKanvasIdx, setActiveKanvasIdx] = useState<number | null>(null)
  const mode = (activeFolderIdx !== null && activeKanvasIdx !== null) ? 'canvas' : 'workspace'

  // ── Data store ──
  const [store, setStore] = useState<FullDataStore>({
    profil:[], akun:[], kontak:[], transaksi:[], lokasi:[], postingan:[], kasus:[], peringatan:[], jaringan:[],
  })

  // ── React Flow ──
  const [nodes, setNodes, onNodesChange] = useNodesState<KiNode>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<KiEdge>([])

  // ── UI state ──
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [savedMsg, setSavedMsg] = useState(false)
  const [searchModal, setSearchModal] = useState<{ tipe: NodeTipe; dropPos: XYPosition } | null>(null)
  const [panelTab, setPanelTab] = useState<'detail' | 'timeline' | 'peta'>('detail')
  const [petaLokasiPanel, setPetaLokasiPanel] = useState<Lokasi | null>(null)
  const [kanvasMode, setKanvasMode] = useState<'pan' | 'select'>('pan')

  // ── Context ──
  const removeKiNode = useCallback((id: string) => {
    setNodes(nds => nds.filter(n => n.id !== id))
    setEdges(eds => eds.filter(e => e.source !== id && e.target !== id))
    setSelectedNodeId(prev => prev === id ? null : prev)
  }, [setNodes, setEdges])

  // ── Muat data ──
  useEffect(() => {
    async function muat() {
      const [profil, akun, kontak, transaksi, lokasi, postingan, kasus, peringatan, jaringan] = await Promise.all([
        muatJson<Profil[]>('/data/profil.json').catch(()=>[]),
        muatJson<Akun[]>('/data/akun.json').catch(()=>[]),
        muatJson<Kontak[]>('/data/kontak.json').catch(()=>[]),
        muatJson<Transaksi[]>('/data/transaksi.json').catch(()=>[]),
        muatJson<Lokasi[]>('/data/lokasi.json').catch(()=>[]),
        muatJson<Postingan[]>('/data/postingan.json').catch(()=>[]),
        muatJson<Kasus[]>('/data/kasus.json').catch(()=>[]),
        muatJson<Peringatan[]>('/data/peringatan.json').catch(()=>[]),
        muatJson<FullDataStore['jaringan']>('/data/jaringan.json').catch(()=>[]),
      ])
      setStore({ profil, akun, kontak, transaksi, lokasi, postingan, kasus, peringatan, jaringan })
    }
    muat()
  }, [])

  // ── Buka kanvas dari workspace ──
  function bukaKanvas(fi: number, ki: number) {
    const cvs = workspace.folders[fi].kanvas[ki]
    setNodes(cvs.nodes)
    setEdges(cvs.edges)
    setSelectedNodeId(null)
    setActiveFolderIdx(fi)
    setActiveKanvasIdx(ki)
  }

  // ── Kembali ke workspace (auto-save) ──
  function kembaliKeWorkspace() {
    _simpanKanvas()
    setActiveFolderIdx(null)
    setActiveKanvasIdx(null)
    setSelectedNodeId(null)
  }

  // ── Simpan kanvas ke workspace store ──
  function _simpanKanvas() {
    if (activeFolderIdx === null || activeKanvasIdx === null) return
    const viewport = rfInstance?.getViewport() ?? { x: 0, y: 0, zoom: 1 }
    const updated: WorkspaceStore = {
      ...workspace,
      folders: workspace.folders.map((f,fi) => fi !== activeFolderIdx ? f : {
        ...f,
        kanvas: f.kanvas.map((k,ki) => ki !== activeKanvasIdx ? k : { ...k, nodes, edges, viewport }),
      }),
    }
    setWorkspace(updated)
    simpanWorkspace(updated)
    setSavedMsg(true)
    setTimeout(() => setSavedMsg(false), 1800)
  }

  // ── Hapus semua node di kanvas ──
  function hapusSemuaNode() {
    if (!window.confirm('Hapus semua node dan edge di kanvas ini?')) return
    setNodes([]); setEdges([]); setSelectedNodeId(null)
  }

  // ── Connect edge manual ──
  const onConnect = useCallback(
    (params: Connection) => setEdges(eds => addEdge({ ...params, style:{stroke:'#555',strokeWidth:1.2}, data:{tipe:'manual'} }, eds)),
    [setEdges],
  )

  // ── Drag palette → canvas ──
  function onDragStartPalette(e: React.DragEvent, tipe: NodeTipe) {
    e.dataTransfer.setData('ki-entity-tipe', tipe)
    e.dataTransfer.effectAllowed = 'copy'
  }

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    if (!rfWrapper.current || !rfInstance) return
    const incoming = e.dataTransfer.getData('ki-entity-tipe') as NodeTipe
    if (!ENTITY_TYPES.includes(incoming)) return
    const rect = rfWrapper.current.getBoundingClientRect()
    const dropPos = rfInstance.screenToFlowPosition({ x: e.clientX - rect.left, y: e.clientY - rect.top })
    setSearchModal({ tipe: incoming, dropPos })
  }, [rfInstance])

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault(); e.dataTransfer.dropEffect = 'copy'
  }, [])

  // ── Klik palette item → search modal di tengah ──
  function bukaCariDariPalette(tipe: NodeTipe) {
    const centerPos: XYPosition = rfInstance
      ? rfInstance.screenToFlowPosition({ x: window.innerWidth / 2, y: window.innerHeight / 2 })
      : { x: 300, y: 300 }
    setSearchModal({ tipe, dropPos: centerPos })
  }

  // ── Deploy hasil pencarian ──
  function deployNodes(newNodes: KiNode[]) {
    setNodes(nds => {
      const merged = [...nds, ...newNodes]
      const existingEids = new Set(edges.map(e => e.id))
      const autoEdges = buatAutoEdges(merged, store, existingEids)
      if (autoEdges.length > 0) {
        setEdges(eds => { const ex = new Set(eds.map(e=>e.id)); return [...eds, ...autoEdges.filter(e=>!ex.has(e.id))] })
      }
      return merged
    })
    setSearchModal(null)
  }

  // ── Node click ──
  const onNodeClick = useCallback((_: React.MouseEvent, node: KiNode) => setSelectedNodeId(node.id), [])
  const onPaneClick = useCallback(() => setSelectedNodeId(null), [])

  // ── Expand (pivot) ──
  function expand(tipeExpand: string) {
    if (!selectedNodeId) return
    const selNode = nodes.find(n => n.id === selectedNodeId)
    if (!selNode) return
    const pos = selNode.position
    const existingIds = new Set(nodes.map(n => n.id))
    let hasil: { nodes: KiNode[]; edges: KiEdge[] } = { nodes: [], edges: [] }
    const nodeTipe = selNode.data.tipe
    if (nodeTipe === 'profil') {
      const profId = (selNode.data.data as unknown as Profil).id_profil
      if (tipeExpand === 'jaringan')  hasil = pivotProfilToJaringan(profId, store, existingIds, pos)
      if (tipeExpand === 'transaksi') hasil = pivotProfilToTransaksi(profId, store, existingIds, pos)
      if (tipeExpand === 'lokasi')    hasil = pivotProfilToLokasi(profId, store, existingIds, pos)
    } else if (nodeTipe === 'kasus') {
      const kasusId = (selNode.data.data as unknown as Kasus).id_kasus
      if (tipeExpand === 'profil')    hasil = pivotKasusToProfil(kasusId, store, existingIds, pos)
      if (tipeExpand === 'peringatan') hasil = pivotKasusToPeringatan(kasusId, store, existingIds, pos)
    }
    if (hasil.nodes.length === 0 && hasil.edges.length === 0) return
    setNodes(nds => [...nds, ...hasil.nodes])
    setEdges(eds => {
      const eids = new Set(eds.map(e => e.id))
      return [...eds, ...hasil.edges.filter(e => !eids.has(e.id))]
    })
  }

  // ── Edge count per node ──
  const nodeEdgeCount = useMemo(() => {
    const m = new Map<string, number>()
    edges.forEach(e => { m.set(e.source,(m.get(e.source)??0)+1); m.set(e.target,(m.get(e.target)??0)+1) })
    return m
  }, [edges])

  // ── Co-lokasi: pasang profil yang pernah di tempat yang sama ──
  const coLokasiPairs = useMemo<Set<string>>(() => {
    // Dua profil dianggap co-lokasi hanya jika ada titik lokasi dalam jarak <250m
    function haversineM(lat1: number, lng1: number, lat2: number, lng2: number): number {
      const R = 6371000
      const dLat = (lat2 - lat1) * Math.PI / 180
      const dLng = (lng2 - lng1) * Math.PI / 180
      const a = Math.sin(dLat / 2) ** 2
        + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLng / 2) ** 2
      return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
    }
    const profLokasiMap = new Map<string, Array<{ lat: number; lng: number }>>()
    store.lokasi.forEach(l => {
      if (!profLokasiMap.has(l.id_profil)) profLokasiMap.set(l.id_profil, [])
      profLokasiMap.get(l.id_profil)!.push({ lat: l.latitude, lng: l.longitude })
    })
    const profilsOnCanvas = nodes
      .filter(n => n.data.tipe === 'profil')
      .map(n => ({ nodeId: n.id, profId: (n.data.data as unknown as Profil).id_profil }))
    const pairs = new Set<string>()
    for (let i = 0; i < profilsOnCanvas.length; i++) {
      for (let j = i + 1; j < profilsOnCanvas.length; j++) {
        const { nodeId: nA, profId: pA } = profilsOnCanvas[i]
        const { nodeId: nB, profId: pB } = profilsOnCanvas[j]
        const locsA = profLokasiMap.get(pA) ?? []
        const locsB = profLokasiMap.get(pB) ?? []
        const dekat = locsA.some(a => locsB.some(b => haversineM(a.lat, a.lng, b.lat, b.lng) < 250))
        if (dekat) { pairs.add(`${nA}:${nB}`); pairs.add(`${nB}:${nA}`) }
      }
    }
    return pairs
  }, [nodes, store.lokasi])

  // ── Display edges: merah untuk co-lokasi, tambah edge baru kalau belum ada ──
  const displayEdges = useMemo<KiEdge[]>(() => {
    const existingPairs = new Set<string>()
    const updated = edges.map(e => {
      existingPairs.add(`${e.source}:${e.target}`)
      existingPairs.add(`${e.target}:${e.source}`)
      if (coLokasiPairs.has(`${e.source}:${e.target}`)) {
        return { ...e, animated: true, style: { ...e.style, stroke: '#D62828', strokeWidth: 2.5 } }
      }
      return e
    })
    const newCoLok: KiEdge[] = []
    coLokasiPairs.forEach(pair => {
      if (existingPairs.has(pair)) return
      const [src, tgt] = pair.split(':')
      if (src < tgt) newCoLok.push({
        id: `e-colok-${src}-${tgt}`, source: src, target: tgt,
        animated: true, data: { tipe: 'co_lokasi' },
        style: { stroke: '#D62828', strokeWidth: 2 },
      })
    })
    return [...updated, ...newCoLok]
  }, [edges, coLokasiPairs])

  const selNode = selectedNodeId ? nodes.find(n => n.id === selectedNodeId) : null
  const selTipe = selNode?.data.tipe ?? null

  // ── Detail panel ──
  function renderDetail() {
    if (!selNode) return (
      <div className="ki-detail-empty">
        <RefreshCw size={22} style={{opacity:.15}}/>
        <span>Klik node untuk melihat detail & ekspansi</span>
      </div>
    )
    const dt = selNode.data.data
    const tipe = selNode.data.tipe
    const warna = TIPE_WARNA[tipe]
    const koneksi = nodeEdgeCount.get(selNode.id) ?? 0
    return (
      <div className="ki-detail-content">
        <div className="ki-detail-header" style={{borderBottomColor:warna+'33'}}>
          <span className="ki-detail-badge" style={{background:warna+'20',color:warna}}>{TIPE_LABEL[tipe]}</span>
          <span className="ki-detail-koneksi">{koneksi} koneksi</span>
        </div>
        <div className="ki-detail-fields">
          {tipe === 'profil' && (() => { const p = dt as unknown as Profil; return (<>
            <div className="ki-detail-row"><span>Nama</span><span>{p.nama_lengkap}</span></div>
            <div className="ki-detail-row"><span>Kota</span><span>{p.kota}, {p.provinsi}</span></div>
            <div className="ki-detail-row"><span>Lhr.</span><span>{p.rentang_tahun_lahir}</span></div>
            <div className="ki-detail-row"><span>Bahasa</span><span>{p.bahasa.join(', ')}</span></div>
            {p.bio&&<div className="ki-detail-bio">{p.bio}</div>}
            {p.tag_risiko.length>0&&<div className="ki-detail-row"><span>Risiko</span><div style={{display:'flex',gap:4,flexWrap:'wrap'}}>{p.tag_risiko.map(t=><span key={t} className="ki-tag" style={{borderColor:'#D6282833',color:'#D62828'}}>{t}</span>)}</div></div>}
            {p.tautan_kasus.length>0&&<div className="ki-detail-row"><span>Kasus</span><span>{p.tautan_kasus.length} terkait</span></div>}
          </>)})()}
          {tipe === 'akun' && (() => { const a = dt as unknown as Akun; return (<>
            <div className="ki-detail-row"><span>Username</span><span>{a.username}</span></div>
            <div className="ki-detail-row"><span>Platform</span><span>{a.platform}</span></div>
            <div className="ki-detail-row"><span>Pengikut</span><span>{a.jumlah_pengikut.toLocaleString('id-ID')}</span></div>
            <div className="ki-detail-row"><span>Minat</span><span>{a.petunjuk_minat}</span></div>
            <div className="ki-detail-row"><span>Dibuat</span><span>{fmtTgl(a.dibuat_pada)}</span></div>
            <div className="ki-detail-row"><span>Verifikasi</span><span>{a.status_terverifikasi?'Ya':'Tidak'}</span></div>
          </>)})()}
          {tipe === 'kontak' && (() => { const k = dt as unknown as Kontak; return (<>
            <div className="ki-detail-row"><span>Email</span><span style={{fontFamily:'monospace',fontSize:10}}>{k.email}</span></div>
            <div className="ki-detail-row"><span>Telepon</span><span>{k.telepon_lokal}</span></div>
            <div className="ki-detail-row"><span>Kota</span><span>{k.kota}, {k.provinsi}</span></div>
            <div className="ki-detail-row"><span>Utama</span><span>{k.adalah_utama?'Ya':'Tidak'}</span></div>
          </>)})()}
          {tipe === 'transaksi' && (() => { const t = dt as unknown as Transaksi; const sn=store.profil.find(p=>p.id_profil===t.id_profil_sumber)?.nama_tampil??t.id_profil_sumber.slice(0,14); const tn=store.profil.find(p=>p.id_profil===t.id_profil_tujuan)?.nama_tampil??t.id_profil_tujuan.slice(0,14); return (<>
            <div className="ki-detail-row"><span>Jumlah</span><span style={{color:'#4CAF50'}}>{fmtRupiah(t.jumlah_idr)}</span></div>
            <div className="ki-detail-row"><span>Kanal</span><span>{t.kanal.replace(/_/g,' ')}</span></div>
            <div className="ki-detail-row"><span>Dari</span><span>{sn}</span></div>
            <div className="ki-detail-row"><span>Ke</span><span>{tn}</span></div>
            <div className="ki-detail-row"><span>Tujuan</span><span>{t.petunjuk_tujuan}</span></div>
            <div className="ki-detail-row"><span>Ref</span><span style={{fontFamily:'monospace',fontSize:9}}>{t.referensi}</span></div>
          </>)})()}
          {tipe === 'lokasi' && (() => { const l = dt as unknown as Lokasi; return (<>
            <div className="ki-detail-row"><span>Label</span><span>{l.label}</span></div>
            <div className="ki-detail-row"><span>Tipe</span><span>{l.tipe_lokasi}</span></div>
            <div className="ki-detail-row"><span>Kota</span><span>{l.kota}, {l.provinsi}</span></div>
            <div className="ki-detail-row"><span>Koor.</span><span style={{fontFamily:'monospace',fontSize:9}}>{l.latitude.toFixed(5)}, {l.longitude.toFixed(5)}</span></div>
            <div className="ki-detail-row"><span>Kepercayaan</span><span>{Math.round(l.kepercayaan*100)}%</span></div>
            <button className="ki-maps-btn" onClick={() => setPetaLokasiPanel(l)}>
              <MapPin size={11}/> Lihat di Peta
            </button>
          </>)})()}
          {tipe === 'postingan' && (() => { const p = dt as unknown as Postingan; return (<>
            <div className="ki-detail-bio">{p.konten}</div>
            <div className="ki-detail-row"><span>Platform</span><span>{p.platform}</span></div>
            <div className="ki-detail-row"><span>Tipe</span><span>{p.tipe_konten}</span></div>
            <div className="ki-detail-row"><span>Kota</span><span>{p.kota}</span></div>
            <div className="ki-detail-row"><span>Waktu</span><span>{fmtTgl(p.timestamp)}</span></div>
            {p.hashtag.length>0&&<div className="ki-detail-row"><span>Hashtag</span><span style={{fontSize:10,opacity:.7}}>{p.hashtag.slice(0,4).join(' ')}</span></div>}
          </>)})()}
          {tipe === 'kasus' && (() => { const k = dt as unknown as Kasus; return (<>
            <div className="ki-detail-row"><span>Tipe</span><span>{k.tipe_kasus.replace(/_/g,' ')}</span></div>
            <div className="ki-detail-row"><span>Lokasi</span><span>{k.kota}, {k.provinsi}</span></div>
            <div className="ki-detail-row"><span>Status</span><span style={{textTransform:'capitalize'}}>{k.status}</span></div>
            <div className="ki-detail-row"><span>Aktor</span><span>{k.jumlah_aktor} orang</span></div>
            <div className="ki-detail-row"><span>Waktu</span><span>{fmtTgl(k.waktu_insiden)}</span></div>
          </>)})()}
          {tipe === 'peringatan' && (() => { const p = dt as unknown as Peringatan; const sw=p.tingkat_keparahan==='tinggi'?'#E5282A':p.tingkat_keparahan==='menengah'?'#F5A623':'#4CAF50'; return (<>
            <div className="ki-detail-row"><span>Sinyal</span><span>{p.tipe_sinyal.replace(/_/g,' ')}</span></div>
            <div className="ki-detail-row"><span>Tingkat</span><span style={{color:sw}}>{p.tingkat_keparahan}</span></div>
            <div className="ki-detail-row"><span>Kepercayaan</span><span>{Math.round(p.kepercayaan*100)}%</span></div>
            <div className="ki-detail-bio" style={{opacity:.6}}>{p.deskripsi}</div>
          </>)})()}
        </div>

        {/* Ekspansi */}
        <div className="ki-expand-section">
          <div className="ki-expand-label">EKSPANSI</div>
          {selTipe === 'profil' && (<>
            <button className="ki-expand-btn" onClick={()=>expand('jaringan')}><Users size={11}/> Koneksi Sosial</button>
            <button className="ki-expand-btn" onClick={()=>expand('transaksi')}><Activity size={11}/> Transaksi</button>
            <button className="ki-expand-btn" onClick={()=>expand('lokasi')}><MapPin size={11}/> Lokasi</button>
          </>)}
          {selTipe === 'kasus' && (<>
            <button className="ki-expand-btn" onClick={()=>expand('profil')}><Users size={11}/> Profil Terkait</button>
            <button className="ki-expand-btn" onClick={()=>expand('peringatan')}><Bell size={11}/> Peringatan</button>
          </>)}
          {selTipe && !['profil','kasus'].includes(selTipe) && (
            <p style={{fontSize:10,color:'rgba(243,234,234,.25)',padding:'4px 0'}}>Tidak ada ekspansi untuk tipe ini.</p>
          )}
        </div>

        {/* Navigasi */}
        <div className="ki-expand-section" style={{marginTop:4}}>
          <div className="ki-expand-label">BUKA DI</div>
          {selTipe === 'kasus' && (
            <button className="ki-expand-btn ki-expand-btn-nav" onClick={()=>navigate('/incident-queue',{state:{focusKasus:(dt as unknown as Kasus).id_kasus}})}>
              <ChevronRight size={11}/> Incident Queue
            </button>
          )}
          {selTipe === 'profil' && (
            <button className="ki-expand-btn ki-expand-btn-nav" onClick={()=>navigate('/link-analysis',{state:{filterProfil:(dt as unknown as Profil).id_profil}})}>
              <ChevronRight size={11}/> Link Analysis
            </button>
          )}
          <button className="ki-expand-btn ki-expand-btn-nav"
            onClick={()=>navigate('/timeline',{state: selTipe==='kasus'?{filterKasus:(dt as unknown as Kasus).id_kasus}:selTipe==='profil'?{filterProfil:(dt as unknown as Profil).id_profil}:{}})}>
            <ChevronRight size={11}/> Timeline
          </button>
          {(selTipe === 'kasus' || selTipe === 'profil') && (
            <button className="ki-expand-btn ki-expand-btn-nav"
              onClick={()=>navigate('/narrative',{state: selTipe==='kasus'?{filterKasus:(dt as unknown as Kasus).id_kasus}:{filterProfil:(dt as unknown as Profil).id_profil}})}>
              <ChevronRight size={11}/> Narasi & Tren
            </button>
          )}
        </div>
      </div>
    )
  }

  // ── Timeline panel ──
  function renderTimeline() {
    type Evt = { waktu: string; label: string; tipe: NodeTipe; nodeId: string }
    const events: Evt[] = []
    nodes.forEach(n => {
      const d = n.data.data
      if (n.data.tipe === 'postingan') {
        const p = d as unknown as Postingan
        events.push({ waktu: p.timestamp, label: `[${p.platform}] ${p.konten.slice(0,70)}…`, tipe: 'postingan', nodeId: n.id })
      } else if (n.data.tipe === 'transaksi') {
        const t = d as unknown as Transaksi
        events.push({ waktu: t.timestamp, label: `Transaksi ${fmtRupiah(t.jumlah_idr)} via ${t.kanal}`, tipe: 'transaksi', nodeId: n.id })
      } else if (n.data.tipe === 'kasus') {
        const k = d as unknown as Kasus
        events.push({ waktu: k.waktu_insiden, label: `Insiden: ${k.tipe_kasus.replace(/_/g,' ')} di ${k.kota}`, tipe: 'kasus', nodeId: n.id })
      } else if (n.data.tipe === 'peringatan') {
        const p = d as unknown as Peringatan
        if (p.waktu) events.push({ waktu: p.waktu, label: `Peringatan: ${p.tipe_sinyal.replace(/_/g,' ')}`, tipe: 'peringatan', nodeId: n.id })
      } else if (n.data.tipe === 'lokasi') {
        const l = d as unknown as Lokasi
        events.push({ waktu: l.diamati_pada, label: `Lokasi: ${l.label} (${l.kota})`, tipe: 'lokasi', nodeId: n.id })
      }
    })
    events.sort((a,b) => a.waktu.localeCompare(b.waktu))
    if (events.length === 0) return (
      <div className="ki-detail-empty"><Clock size={22} style={{opacity:.15}}/><span>Tidak ada event bertanggal di kanvas.</span></div>
    )
    return (
      <div className="ki-timeline-list">
        {events.map((ev, i) => (
          <div key={i} className={`ki-timeline-item${selectedNodeId===ev.nodeId?' aktif':''}`} onClick={() => setSelectedNodeId(ev.nodeId)}>
            <div className="ki-timeline-line"/>
            <div className="ki-timeline-dot" style={{background: TIPE_WARNA[ev.tipe]}}/>
            <div className="ki-timeline-content">
              <div className="ki-timeline-waktu">{fmtTgl(ev.waktu)}</div>
              <div className="ki-timeline-label">{ev.label}</div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  // ── Peta panel ──
  function renderPeta() {
    const lokasiNodes = nodes.filter(n => n.data.tipe === 'lokasi')
    if (lokasiNodes.length === 0) return (
      <div className="ki-detail-empty"><MapPin size={22} style={{opacity:.15}}/><span>Tidak ada node lokasi di kanvas.</span></div>
    )
    const lokasiData = lokasiNodes.map(n => n.data.data as unknown as Lokasi)
    return (
      <div className="ki-peta-wrap">
        <div className="ki-peta-map-container">
          <InsightMiniMap lokasi={lokasiData} kasus={[]} activeProvinsi={[]}/>
        </div>
        <div className="ki-peta-list">
          {lokasiNodes.map(n => {
            const l = n.data.data as unknown as Lokasi
            return (
              <div key={n.id} className={`ki-peta-item${selectedNodeId===n.id?' aktif':''}`} onClick={() => setSelectedNodeId(n.id)}>
                <MapPin size={12} style={{color: TIPE_WARNA.lokasi, flexShrink:0}}/>
                <div className="ki-peta-info">
                  <div className="ki-peta-nama">{l.label}</div>
                  <div className="ki-peta-kota">{l.kota}, {l.provinsi}</div>
                  <div className="ki-peta-koor">{l.latitude.toFixed(5)}, {l.longitude.toFixed(5)}</div>
                </div>
                <button className="ki-peta-btn" onClick={e=>{e.stopPropagation(); setPetaLokasiPanel(l)}}>
                  <MapPin size={9}/>
                </button>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  function hapusNodeTerpilih() {
    const dipilihIds = new Set(nodes.filter(n => n.selected).map(n => n.id))
    setNodes(nds => nds.filter(n => !dipilihIds.has(n.id)))
    setEdges(eds => eds.filter(e => !dipilihIds.has(e.source) && !dipilihIds.has(e.target)))
    setSelectedNodeId(null)
  }

  const namaFolder = activeFolderIdx !== null ? workspace.folders[activeFolderIdx]?.nama ?? '—' : '—'
  const namaKanvas = (activeFolderIdx !== null && activeKanvasIdx !== null) ? workspace.folders[activeFolderIdx]?.kanvas[activeKanvasIdx]?.nama ?? '—' : '—'
  const existingNodeIds = new Set(nodes.map(n => n.id))

  // ── Mode: Workspace (pilih folder/kanvas) ──
  if (mode === 'workspace') {
    return (
      <WorkspaceManager
        workspace={workspace}
        setWorkspace={setWorkspace}
        onBukaKanvas={bukaKanvas}
      />
    )
  }

  // ── Mode: Canvas ──
  return (
    <KanvasCtx.Provider value={{ removeKiNode }}>
      <div className="ki-root">
        {/* Topbar */}
        <div className="ki-topbar">
          <button className="ki-topbar-btn" onClick={kembaliKeWorkspace}>← Workspace</button>
          <div className="ki-topbar-divider"/>
          <span className="ki-topbar-breadcrumb">
            <span style={{opacity:.45}}>{namaFolder}</span>
            <span style={{opacity:.25}}> / </span>
            <span>{namaKanvas}</span>
          </span>
          <div className="ki-topbar-stats">
            <span>{nodes.length} node · {edges.length} edge</span>
          </div>
          <div style={{flex:1}}/>
          <button
            className={`ki-topbar-btn ki-topbar-btn-mode${kanvasMode === 'select' ? ' aktif' : ''}`}
            onClick={() => setKanvasMode(m => m === 'pan' ? 'select' : 'pan')}
            title={kanvasMode === 'pan' ? 'Aktifkan mode pilih (seret untuk seleksi banyak node)' : 'Kembali ke mode gerak'}
          >
            <MousePointer2 size={12}/> {kanvasMode === 'select' ? 'Mode Pilih' : 'Mode Gerak'}
          </button>
          {nodes.filter(n => n.selected).length > 1 && (
            <button className="ki-topbar-btn ki-topbar-btn-hapus-sel" onClick={hapusNodeTerpilih}>
              <Trash2 size={12}/> Hapus {nodes.filter(n => n.selected).length} node
            </button>
          )}
          <button className="ki-topbar-btn ki-topbar-btn-save" onClick={_simpanKanvas}>
            <Save size={12}/> {savedMsg ? 'Tersimpan!' : 'Simpan'}
          </button>
          <button className="ki-topbar-btn ki-topbar-btn-danger" onClick={hapusSemuaNode}>
            <Trash2 size={12}/> Reset
          </button>
        </div>

        <div className="ki-body">
          {/* Panel Kiri: Palette tipe entitas */}
          <div className="ki-panel-kiri">
            <div className="ki-panel-section-hdr">TIPE ENTITAS</div>
            <div className="ki-palette-list">
              {ENTITY_TYPES.map(tipe => {
                const warna = TIPE_WARNA[tipe]
                return (
                  <div key={tipe} className="ki-palette-item"
                    draggable onDragStart={e => onDragStartPalette(e, tipe)}
                    onClick={() => bukaCariDariPalette(tipe)}
                    title={`Drag ke kanvas atau klik untuk cari ${TIPE_LABEL[tipe]}`}
                  >
                    <span className="ki-palette-dot" style={{background:warna}}/>
                    <div className="ki-palette-info">
                      <span className="ki-palette-nama" style={{color:warna}}>{TIPE_LABEL[tipe]}</span>
                      <span className="ki-palette-desc">{TIPE_DESC[tipe]}</span>
                    </div>
                    <span className="ki-palette-drag">⠿</span>
                  </div>
                )
              })}
            </div>
            <div className="ki-panel-hint">Drag ke kanvas atau klik untuk cari berdasarkan parameter</div>
          </div>

          {/* Canvas */}
          <div className="ki-canvas-wrap" ref={rfWrapper} onDrop={onDrop} onDragOver={onDragOver}>
            <ReactFlow<KiNode, KiEdge>
              nodes={nodes} edges={displayEdges}
              onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
              onConnect={onConnect} nodeTypes={NODE_TYPES}
              onInit={setRfInstance} onNodeClick={onNodeClick} onPaneClick={onPaneClick}
              fitView minZoom={0.12} maxZoom={2.5}
              panOnDrag={kanvasMode === 'pan' ? true : [2]}
              selectionOnDrag={kanvasMode === 'select'}
              selectionKeyCode="partial"
              multiSelectionKeyCode="Control"
            >
              <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="rgba(243,234,234,.05)"/>
              <Controls/>
              <MiniMap nodeColor={n => TIPE_WARNA[(n.data as KiNodeData).tipe]+'99'} style={{background:'#0d0d0d',border:'1px solid #222'}}/>
            </ReactFlow>
            {nodes.length === 0 && (
              <div className="ki-canvas-hint">
                <RefreshCw size={28} style={{opacity:.1,marginBottom:8}}/>
                <span>Kanvas kosong.</span>
                <span>Drag tipe entitas dari panel kiri, atau klik tipe entitas untuk mencari berdasarkan parameter.</span>
              </div>
            )}
          </div>

          {/* Panel Kanan: tabs */}
          <div className="ki-panel-kanan">
            <div className="ki-panel-tabs">
              <button className={`ki-panel-tab${panelTab==='detail'?' aktif':''}`} onClick={()=>setPanelTab('detail')}>DETAIL</button>
              <button className={`ki-panel-tab${panelTab==='timeline'?' aktif':''}`} onClick={()=>setPanelTab('timeline')}><Clock size={10}/> TIMELINE</button>
              <button className={`ki-panel-tab${panelTab==='peta'?' aktif':''}`} onClick={()=>setPanelTab('peta')}><MapPin size={10}/> PETA</button>
            </div>
            {panelTab==='detail' && renderDetail()}
            {panelTab==='timeline' && renderTimeline()}
            {panelTab==='peta' && renderPeta()}
          </div>
        </div>

        {/* Panel Peta Lokasi (slide-in overlay) */}
        {petaLokasiPanel && (
          <PanelPetaLokasi lokasi={petaLokasiPanel} onClose={() => setPetaLokasiPanel(null)}/>
        )}

        {/* Search Modal */}
        {searchModal && (
          <SearchModal
            tipe={searchModal.tipe} dropPos={searchModal.dropPos}
            store={store} existingIds={existingNodeIds}
            onDeploy={deployNodes} onTutup={() => setSearchModal(null)}
          />
        )}
      </div>
    </KanvasCtx.Provider>
  )
}


