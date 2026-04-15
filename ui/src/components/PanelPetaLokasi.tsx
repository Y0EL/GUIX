/**
 * PanelPetaLokasi — Slide-in panel peta untuk hasil pencarian lokasi.
 * Mode 2D: Leaflet dark tile + marker + polygon area ~400m.
 * Mode 2.5D: MapLibre GL JS + OpenFreeMap Positron + building extrusion 3D.
 * Reverse geocode via Nominatim (OSM) — gratis, tanpa API key.
 */
import { useEffect, useRef, useState, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { X, Map, Globe, MapPin, Navigation } from 'lucide-react'
import L from 'leaflet'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { Lokasi } from '../types'

// Fix leaflet default icon path (Vite build issue)
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl:       'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl:     'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

type Mode = '2d' | '2.5d'

type Props = {
  lokasi: Lokasi | null
  onClose: () => void
}

type InfoJalan = {
  status: 'loading' | 'found' | 'notfound' | 'error'
  namaJalan?: string
  kelurahan?: string
  kecamatan?: string
  kotaDetail?: string
  kodePos?: string
}

async function reverseGeocode(lat: number, lon: number): Promise<InfoJalan> {
  try {
    const url = `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&accept-language=id`
    const res = await fetch(url, {
      headers: { 'Accept-Language': 'id', 'User-Agent': 'UIX-Intel/1.0' },
    })
    if (!res.ok) throw new Error('Nominatim gagal')
    const data = await res.json()
    const addr = data.address ?? {}
    return {
      status: 'found',
      namaJalan: addr.road ?? addr.pedestrian ?? addr.path ?? addr.residential ?? undefined,
      kelurahan: addr.village ?? addr.suburb ?? addr.neighbourhood ?? undefined,
      kecamatan: addr.city_district ?? addr.subdistrict ?? addr.county ?? undefined,
      kotaDetail: addr.city ?? addr.town ?? addr.municipality ?? undefined,
      kodePos: addr.postcode ?? undefined,
    }
  } catch {
    return { status: 'error' }
  }
}

export default function PanelPetaLokasi({ lokasi, onClose }: Props) {
  const [mode, setMode] = useState<Mode>('2d')
  const [infoJalan, setInfoJalan] = useState<InfoJalan>({ status: 'loading' })

  const mapRef2d   = useRef<L.Map | null>(null)
  const containerRef   = useRef<HTMLDivElement>(null)
  const mapLibreRef    = useRef<HTMLDivElement>(null)
  const mapLibreMap    = useRef<maplibregl.Map | null>(null)

  // Reverse geocode saat lokasi berubah
  useEffect(() => {
    if (!lokasi) return
    setInfoJalan({ status: 'loading' })
    reverseGeocode(lokasi.latitude, lokasi.longitude).then(setInfoJalan)
  }, [lokasi?.id_lokasi])

  // Init/update Leaflet 2D
  useEffect(() => {
    if (!containerRef.current || !lokasi || mode !== '2d') return

    const lat = lokasi.latitude
    const lng = lokasi.longitude

    if (!mapRef2d.current) {
      const map = L.map(containerRef.current, {
        center: [lat, lng],
        zoom: 15,
        zoomControl: false,
        attributionControl: false,
      })

      // Tile gelap (CartoDB Dark)
      L.tileLayer(
        'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
        { subdomains: 'abcd', maxZoom: 19 }
      ).addTo(map)

      L.control.attribution({ position: 'bottomright', prefix: false })
        .addAttribution('© <a href="https://carto.com">CARTO</a> © <a href="https://osm.org">OSM</a>')
        .addTo(map)

      // Marker merah custom
      const iconMerah = L.divIcon({
        className: '',
        html: `<div style="
          width:14px;height:14px;border-radius:50%;
          background:#D62828;border:2.5px solid #fff;
          box-shadow:0 0 8px rgba(214,40,40,.7)
        "></div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      })
      L.marker([lat, lng], { icon: iconMerah }).addTo(map)

      // Polygon ~400m radius
      const pts: [number, number][] = []
      const R = 400
      for (let i = 0; i < 36; i++) {
        const a = (i * 10 * Math.PI) / 180
        const dlat = (R * Math.cos(a)) / 111320
        const dlng = (R * Math.sin(a)) / (111320 * Math.cos((lat * Math.PI) / 180))
        pts.push([lat + dlat, lng + dlng])
      }
      L.polygon(pts, {
        color: '#D62828', fillColor: '#D62828',
        fillOpacity: 0.08, weight: 1.5, dashArray: '4 4',
      }).addTo(map)

      mapRef2d.current = map
    } else {
      mapRef2d.current.flyTo([lat, lng], 15, { duration: 0.8 })
    }
  }, [lokasi?.id_lokasi, mode])

  // Destroy Leaflet saat mode switch
  useEffect(() => {
    if (mode === '2.5d' && mapRef2d.current) {
      mapRef2d.current.remove()
      mapRef2d.current = null
    }
    if (mode === '2d' && mapLibreMap.current) {
      mapLibreMap.current.remove()
      mapLibreMap.current = null
    }
  }, [mode])

  // Init MapLibre 2.5D
  useEffect(() => {
    if (mode !== '2.5d' || !mapLibreRef.current || !lokasi) return

    const lat = lokasi.latitude
    const lng = lokasi.longitude

    if (mapLibreMap.current) {
      mapLibreMap.current.flyTo({ center: [lng, lat], zoom: 16, pitch: 60, bearing: -20, duration: 1000 })
      return
    }

    // OpenFreeMap Positron style — gratis, tanpa API key, mendukung extrusion
    const map = new maplibregl.Map({
      container: mapLibreRef.current,
      style: 'https://tiles.openfreemap.org/styles/positron',
      center: [lng, lat],
      zoom: 15.5,
      pitch: 60,
      bearing: -20,
      attributionControl: false,
    })

    map.on('load', () => {
      // Marker merah
      const el = document.createElement('div')
      el.style.cssText = `
        width:16px;height:16px;border-radius:50%;
        background:#D62828;border:3px solid #fff;
        box-shadow:0 0 12px rgba(214,40,40,.8);
      `
      new maplibregl.Marker({ element: el }).setLngLat([lng, lat]).addTo(map)

      // Circle polygon
      const circleCoords: [number, number][] = []
      const R = 400
      for (let i = 0; i <= 64; i++) {
        const a = (i * 360 / 64 * Math.PI) / 180
        const dlat = (R * Math.cos(a)) / 111320
        const dlng = (R * Math.sin(a)) / (111320 * Math.cos((lat * Math.PI) / 180))
        circleCoords.push([lng + dlng, lat + dlat])
      }

      map.addSource('area-circle', {
        type: 'geojson',
        data: { type: 'Feature', geometry: { type: 'Polygon', coordinates: [circleCoords] }, properties: {} },
      })
      map.addLayer({
        id: 'area-fill',
        type: 'fill',
        source: 'area-circle',
        paint: { 'fill-color': '#D62828', 'fill-opacity': 0.12 },
      })
      map.addLayer({
        id: 'area-outline',
        type: 'line',
        source: 'area-circle',
        paint: { 'line-color': '#D62828', 'line-width': 1.5, 'line-dasharray': [3, 3] },
      })

      // 3D Building extrusion — pakai layer dari style jika ada, atau tambahkan
      if (!map.getLayer('building-extrusion')) {
        const firstSymbol = map.getStyle().layers?.find(l => l.type === 'symbol')?.id
        map.addLayer({
          id: 'building-extrusion',
          type: 'fill-extrusion',
          source: 'openmaptiles',
          'source-layer': 'building',
          paint: {
            'fill-extrusion-color': '#1a1a2e',
            'fill-extrusion-height': ['coalesce', ['get', 'render_height'], 10],
            'fill-extrusion-base':   ['coalesce', ['get', 'render_min_height'], 0],
            'fill-extrusion-opacity': 0.85,
          },
        }, firstSymbol)
      }
    })

    mapLibreMap.current = map
  }, [mode, lokasi?.id_lokasi])

  const handleClose = useCallback(() => {
    if (mapRef2d.current)  { mapRef2d.current.remove();  mapRef2d.current  = null }
    if (mapLibreMap.current) { mapLibreMap.current.remove(); mapLibreMap.current = null }
    onClose()
  }, [onClose])

  if (!lokasi) return null

  const koordinatStr = `${lokasi.latitude.toFixed(6)}, ${lokasi.longitude.toFixed(6)}`

  return createPortal(
    <>
      {/* Backdrop */}
      <div className="ppl-backdrop" onClick={handleClose} />

      {/* Panel */}
      <div className="ppl-panel">
        {/* Header */}
        <div className="ppl-header">
          <div className="ppl-header-left">
            <MapPin size={14} className="ppl-header-icon" />
            <div>
              <div className="ppl-header-label">{lokasi.label}</div>
              <div className="ppl-header-meta">
                {lokasi.kota}, {lokasi.provinsi}
                <span className="ppl-sep">·</span>
                <span className="ppl-tipe">{lokasi.tipe_lokasi.replace(/_/g, ' ')}</span>
              </div>
            </div>
          </div>
          <button className="ppl-close-btn" onClick={handleClose}><X size={15} /></button>
        </div>

        {/* Mode toggle */}
        <div className="ppl-mode-bar">
          <button
            className={`ppl-mode-btn ${mode === '2d' ? 'aktif' : ''}`}
            onClick={() => setMode('2d')}
          >
            <Map size={12} /> 2D
          </button>
          <button
            className={`ppl-mode-btn ${mode === '2.5d' ? 'aktif' : ''}`}
            onClick={() => setMode('2.5d')}
          >
            <Globe size={12} /> 2.5D
          </button>

          <div className="ppl-koordinat">
            <Navigation size={10} />
            {koordinatStr}
          </div>
        </div>

        {/* Peta 2D Leaflet */}
        {mode === '2d' && (
          <div className="ppl-map-container" ref={containerRef} />
        )}

        {/* Peta 2.5D MapLibre — building extrusion */}
        {mode === '2.5d' && (
          <div className="ppl-map-container" ref={mapLibreRef} />
        )}

        {/* Info jalan */}
        <div className="ppl-info-jalan">
          <div className="ppl-info-title">Informasi Lokasi</div>
          {infoJalan.status === 'loading' && (
            <div className="ppl-info-row ppl-loading-text">Memuat nama jalan…</div>
          )}
          {infoJalan.status === 'error' && (
            <div className="ppl-info-row ppl-muted">Gagal memuat informasi jalan</div>
          )}
          {infoJalan.status === 'found' && (
            <>
              <div className="ppl-info-row">
                <span className="ppl-info-key">Jalan</span>
                <span className="ppl-info-val">{infoJalan.namaJalan ?? <em className="ppl-muted">Belum diketahui</em>}</span>
              </div>
              {infoJalan.kelurahan && (
                <div className="ppl-info-row">
                  <span className="ppl-info-key">Kelurahan</span>
                  <span className="ppl-info-val">{infoJalan.kelurahan}</span>
                </div>
              )}
              {infoJalan.kecamatan && (
                <div className="ppl-info-row">
                  <span className="ppl-info-key">Kecamatan</span>
                  <span className="ppl-info-val">{infoJalan.kecamatan}</span>
                </div>
              )}
              <div className="ppl-info-row">
                <span className="ppl-info-key">Kota</span>
                <span className="ppl-info-val">{infoJalan.kotaDetail ?? lokasi.kota}</span>
              </div>
              {infoJalan.kodePos && (
                <div className="ppl-info-row">
                  <span className="ppl-info-key">Kode Pos</span>
                  <span className="ppl-info-val">{infoJalan.kodePos}</span>
                </div>
              )}
            </>
          )}
          <div className="ppl-info-row">
            <span className="ppl-info-key">Kepercayaan</span>
            <span className="ppl-info-val ppl-kepercayaan">
              {Math.round((lokasi.kepercayaan ?? 0) * 100)}%
            </span>
          </div>
          <div className="ppl-info-row">
            <span className="ppl-info-key">Diamati</span>
            <span className="ppl-info-val ppl-muted">
              {new Date(lokasi.diamati_pada).toLocaleDateString('id-ID', { day: 'numeric', month: 'long', year: 'numeric' })}
            </span>
          </div>
        </div>
      </div>
    </>,
    document.body
  )
}
