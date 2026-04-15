import { useCallback, useEffect, useMemo, useState } from 'react'
import { AlertTriangle, Radio, Activity, Wifi, Bell } from 'lucide-react'
import { Link } from 'react-router-dom'
import 'leaflet/dist/leaflet.css'

import BarMetrik from '../components/BarMetrik'
import JamDisplay from '../components/JamDisplay'
import PetaOverview, { type ViewPayload } from '../components/PetaOverview'
import PanelKasus from '../components/PanelKasus'
import PanelBerita from '../components/PanelBerita'
import PanelAlert from '../components/PanelAlert'

import type { Kasus, Lokasi, Peringatan, Berita } from '../types'
import { muatJson, agregasiHotspot } from '../utils'
import { useArrowNav } from '../hooks/useArrowNav'

export default function Overview() {
  useArrowNav()

  const [kasus, setKasus] = useState<Kasus[]>([])
  const [lokasi, setLokasi] = useState<Lokasi[]>([])
  const [peringatan, setPeringatan] = useState<Peringatan[]>([])
  const [berita, setBerita] = useState<Berita[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  /* Viewport — hotspot dan kota yang saat ini terlihat di layar */
  const [hotspotVP, setHotspotVP] = useState<typeof hotspot>([])  
  const [kotaSetVP, setKotaSetVP] = useState<Set<string>>(new Set())

  /* Muat semua data */
  useEffect(() => {
    async function muat() {
      try {
        const [kData, lData, pData, bRaw] = await Promise.all([
          muatJson<Kasus[]>('/data/kasus.json'),
          muatJson<Lokasi[]>('/data/lokasi.json'),
          muatJson<Peringatan[]>('/data/peringatan.json'),
          fetch('/data/news.dataset.jsonl').then((r) => {
            if (!r.ok) throw new Error('Gagal memuat berita')
            return r.text()
          }),
        ])
        setKasus(kData)
        setLokasi(lData)
        setPeringatan(pData)
        setBerita(
          bRaw
            .split('\n')
            .map((b) => b.trim())
            .filter(Boolean)
            .map((b) => JSON.parse(b) as Berita),
        )
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Gagal memuat data')
      } finally {
        setLoading(false)
      }
    }
    muat()
  }, [])

  /* Agregasi hotspot dari lokasi */
  const hotspot = useMemo(() => agregasiHotspot(lokasi), [lokasi])

  /* Viewport change handler dari PetaOverview */
  const handleViewChange = useCallback((p: ViewPayload) => {
    setHotspotVP(p.hotspot)
    setKotaSetVP(p.kotaSet)
  }, [])

  /* Sinkron hotspotVP saat hotspot berubah & kotaSetVP belum diisi */
  useEffect(() => {
    if (kotaSetVP.size === 0 && hotspot.length > 0) {
      setHotspotVP(hotspot)
      setKotaSetVP(new Set(hotspot.map(h => h.kota)))
    }
  }, [hotspot, kotaSetVP.size])

  /* Metrik dinamis berdasarkan viewport */
  const metrikDasar = useMemo(() => {
    const isPenuh = kotaSetVP.size === 0 || kotaSetVP.size >= hotspot.length
    const kasusVP = isPenuh
      ? kasus
      : kasus.filter(k => kotaSetVP.has(k.kota))
    const kasusIdVP = new Set(kasusVP.map(k => k.id_kasus))
    const totalSubjek = isPenuh
      ? new Set(lokasi.map(l => l.id_profil)).size
      : hotspotVP.reduce((s, h) => s + h.profil, 0)
    return {
      kritis: peringatan.filter(p =>
        p.tingkat_keparahan === 'tinggi' && kasusIdVP.has(p.id_kasus)
      ).length,
      tinggi : kasusVP.filter(k => k.status === 'monitoring').length,
      sedang : kasusVP.filter(k => k.status === 'analisis').length,
      subjek : totalSubjek,
      wilayah: kotaSetVP.size > 0 ? kotaSetVP.size : new Set(kasus.map(k => k.kota)).size,
    }
  }, [hotspotVP, kotaSetVP, kasus, peringatan, lokasi, hotspot.length])

  /* Status sistem simulated */
  const statusSistem = useMemo(() => ({
    feed: 'aktif',
    pipeline: kasus.length > 0 ? 'sehat' : 'idle',
    sumber: peringatan.length + berita.length,
  }), [kasus.length, peringatan.length, berita.length])

  return (
    <main className="halaman-radar">

      {/* Peta — selalu dirender agar ref kontainer siap */}
      <PetaOverview hotspot={hotspot} kasus={kasus} onViewChange={handleViewChange} />

      {/* Overlay loading */}
      {loading && (
        <div className="overlay-tengah">
          <div className="spinner" />
          <h1>Menginisialisasi...</h1>
          <p>Memuat data intelijen...</p>
        </div>
      )}

      {/* Overlay error */}
      {error && (
        <div className="overlay-tengah overlay-error">
          <AlertTriangle size={36} />
          <h1>Gagal Memuat Data</h1>
          <p>{error}</p>
        </div>
      )}

      {/* UI — hanya tampil setelah data siap */}
      {!loading && !error && (
        <>
          <BarMetrik metrik={metrikDasar} />

          <JamDisplay />

          <PanelAlert peringatan={peringatan} />

          <PanelKasus kasus={kasus} />

          <PanelBerita berita={berita} />

          <footer className="bar-status">
            <span>
              <Radio size={8} className="pulse-dot" />
              &nbsp;{hotspot.length} zona aktif
            </span>
            <span>{kasus.length} kasus terpantau</span>
            <span>
              <Wifi size={8} style={{ color: '#2E7D32' }} />
              &nbsp;Feed {statusSistem.feed}
            </span>
            <span>
              <Activity size={8} style={{ color: '#2E7D32' }} />
              &nbsp;Pipeline {statusSistem.pipeline}
            </span>
            <span>{statusSistem.sumber} sumber intelijen</span>
            <Link to="/alert-center" className="nav-ac-link">
              <Bell size={9} />
              Alert Center
            </Link>
            <span style={{ fontSize: 9, color: 'rgba(243,234,234,.12)', letterSpacing: '.06em' }}>
              ← → navigasi halaman
            </span>
          </footer>
        </>
      )}

    </main>
  )
}
