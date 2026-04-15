import { useEffect, useMemo, useRef, useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import 'leaflet/dist/leaflet.css'

import MapTopBar from '../components/MapTopBar'
import MapFilterPanel from '../components/MapFilterPanel'
import MapCanvas, { type MapCanvasHandle } from '../components/MapCanvas'
import LocationDetailPanel from '../components/LocationDetailPanel'

import type { Lokasi, Kasus, Peringatan, SkorRisiko, Wilayah } from '../types'
import { muatJson } from '../utils'
import { useArrowNav } from '../hooks/useArrowNav'

type Tab = 'info' | 'kasus' | 'alert' | 'entitas'

export default function MapIntelligence() {
  useArrowNav()

  const [lokasi, setLokasi] = useState<Lokasi[]>([])
  const [kasus, setKasus] = useState<Kasus[]>([])
  const [peringatan, setPeringatan] = useState<Peringatan[]>([])
  const [skorRisiko, setSkorRisiko] = useState<SkorRisiko[]>([])
  const [wilayah, setWilayah] = useState<Wilayah[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  /* Filter state */
  const [filterSeverity, setFilterSeverity] = useState<string[]>([])
  const [filterTipeLokasi, setFilterTipeLokasi] = useState<string[]>([])

  /* Peta state */
  const [labelEnabled, setLabelEnabled] = useState(false)
  const [clusterEnabled, setClusterEnabled] = useState(false)
  const [selectedWilayah, setSelectedWilayah] = useState<string | null>(null)

  /* Detail panel state */
  const [selectedLokasi, setSelectedLokasi] = useState<Lokasi | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('info')

  const mapRef = useRef<MapCanvasHandle>(null)

  /* Load data */
  useEffect(() => {
    async function muat() {
      try {
        const [lData, kData, pData, srData, wData] = await Promise.all([
          muatJson<Lokasi[]>('/data/lokasi.json'),
          muatJson<Kasus[]>('/data/kasus.json'),
          muatJson<Peringatan[]>('/data/peringatan.json'),
          muatJson<SkorRisiko[]>('/data/skor_risiko.json'),
          muatJson<Wilayah[]>('/data/wilayah.json'),
        ])
        setLokasi(lData)
        setKasus(kData)
        setPeringatan(pData)
        setSkorRisiko(srData)
        setWilayah(wData)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Gagal memuat data')
      } finally {
        setLoading(false)
      }
    }
    muat()
  }, [])

  /* Daftar tipe lokasi unik dari data */
  const tipeLokasi = useMemo(
    () => Array.from(new Set(lokasi.map(l => l.tipe_lokasi))).sort(),
    [lokasi],
  )

  function handleToggleSeverity(s: string) {
    setFilterSeverity(prev =>
      prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s],
    )
  }

  function handleToggleTipe(t: string) {
    setFilterTipeLokasi(prev =>
      prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t],
    )
  }

  function handleSelectWilayah(id: string) {
    const w = wilayah.find(x => x.id_wilayah === id)
    if (!w) return
    setSelectedWilayah(id)
    mapRef.current?.flyTo(w.koordinat_pusat[0], w.koordinat_pusat[1], 11)
  }

  function handleSelectLokasi(l: Lokasi) {
    setSelectedLokasi(l)
    setActiveTab('info')
  }

  if (loading) {
    return (
      <div className="halaman-mi" style={{ display: 'grid', placeContent: 'center' }}>
        <div className="overlay-tengah" style={{ position: 'relative', background: 'none' }}>
          <div className="spinner" />
          <h1>Memuat Map Intelligence...</h1>
          <p>Mengambil data lokasi dan kasus</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="halaman-mi" style={{ display: 'grid', placeContent: 'center' }}>
        <div className="overlay-tengah overlay-error" style={{ position: 'relative', background: 'none' }}>
          <AlertTriangle size={36} />
          <h1>Gagal Memuat Data</h1>
          <p>{error}</p>
        </div>
      </div>
    )
  }

  /* Jumlah marker yang akan ditampilkan setelah filter */
  const totalTitik = lokasi.filter(lok => {
    const okTipe = filterTipeLokasi.length === 0 || filterTipeLokasi.includes(lok.tipe_lokasi)
    return okTipe
  }).length

  return (
    <div className="halaman-mi">
      <MapTopBar
        wilayah={wilayah}
        totalTitik={totalTitik}
        labelEnabled={labelEnabled}
        clusterEnabled={clusterEnabled}
        onToggleLabel={() => setLabelEnabled(p => !p)}
        onToggleCluster={() => setClusterEnabled(p => !p)}
        onResetView={() => mapRef.current?.resetView()}
      />

      <div className="mi-body">
        {/* Sidebar kiri */}
        <MapFilterPanel
          filterSeverity={filterSeverity}
          filterTipeLokasi={filterTipeLokasi}
          tipeLokasi={tipeLokasi}
          wilayah={wilayah}
          selectedWilayah={selectedWilayah}
          onToggleSeverity={handleToggleSeverity}
          onToggleTipe={handleToggleTipe}
          onSelectWilayah={handleSelectWilayah}
        />

        {/* Area peta + panel detail */}
        <div className="mi-map-area">
          <MapCanvas
            ref={mapRef}
            lokasi={lokasi}
            kasus={kasus}
            peringatan={peringatan}
            skorRisiko={skorRisiko}
            filterSeverity={filterSeverity}
            filterTipeLokasi={filterTipeLokasi}
            labelEnabled={labelEnabled}
            onSelectLokasi={handleSelectLokasi}
          />

          {/* Location Detail Panel — slide up saat ada lokasi terpilih */}
          {selectedLokasi && (
            <LocationDetailPanel
              lokasi={selectedLokasi}
              kasus={kasus}
              peringatan={peringatan}
              activeTab={activeTab}
              onTab={setActiveTab}
              onClose={() => setSelectedLokasi(null)}
            />
          )}
        </div>
      </div>

      {/* Footer nav hint */}
      <div className="mi-footer">
        <span>← Incident Queue</span>
        <span className="mi-footer-current">Map Intelligence</span>
        <span>→</span>
      </div>
    </div>
  )
}
