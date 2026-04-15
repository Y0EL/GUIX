import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { Lokasi, Kasus } from '../types'

type Props = {
  lokasi: Lokasi[]
  kasus: Kasus[]           // untuk label provinsi aktif
  activeProvinsi: string[] // provinsi yang relevan berdasarkan alert aktif
}

/* Warna per tipe_lokasi */
const WARNA_TIPE: Record<string, string> = {
  titik_observasi:  '#E04B4B',
  pertemuan_rutin:  '#FBBF24',
  mobilitas_kerja:  '#60A5FA',
  domisili:         '#A78BFA',
  titik_transit:    '#34D399',
}
function warnaTipe(tipe: string): string {
  return WARNA_TIPE[tipe] ?? '#94a3b8'
}

export default function InsightMiniMap({ lokasi, kasus: _kasus, activeProvinsi }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef       = useRef<L.Map | null>(null)
  const layerRef     = useRef<L.LayerGroup | null>(null)

  /* ── Init map sekali ── */
  useEffect(() => {
    const el = containerRef.current
    if (!el || mapRef.current) return

    const map = L.map(el, {
      center:          [-2.5, 118],
      zoom:            4,
      zoomControl:     false,
      attributionControl: false,
      dragging:        true,
      scrollWheelZoom: false,
      doubleClickZoom: false,
    })

    /* Dark tile layer */
    L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
      { subdomains: 'abcd', maxZoom: 18 },
    ).addTo(map)

    layerRef.current = L.layerGroup().addTo(map)
    mapRef.current   = map

    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  /* ── Update markers saat data/filter berubah ── */
  useEffect(() => {
    const layer = layerRef.current
    const map   = mapRef.current
    if (!layer || !map) return

    layer.clearLayers()

    /* Filter lokasi: tampilkan semua jika activeProvinsi kosong, atau yang cocok */
    const filtered = activeProvinsi.length > 0
      ? lokasi.filter(l => activeProvinsi.includes(l.provinsi))
      : lokasi

    if (filtered.length === 0) return

    const bounds: [number, number][] = []

    for (const lok of filtered) {
      const warna = warnaTipe(lok.tipe_lokasi)
      const radius = 3 + lok.kepercayaan * 4   // 3–7 px berdasar confidence

      const circle = L.circleMarker([lok.latitude, lok.longitude], {
        radius,
        color:       warna,
        fillColor:   warna,
        fillOpacity: 0.7 * lok.kepercayaan,
        weight:      1,
        opacity:     0.9,
      })

      circle.bindTooltip(
        `<div style="font:11px 'IBM Plex Sans',sans-serif;line-height:1.5;color:#f3eaea;background:#1a0505;border:1px solid rgba(179,24,24,.3);border-radius:5px;padding:5px 8px;">
          <b>${lok.label}</b><br/>
          ${lok.kota}, ${lok.provinsi}<br/>
          <span style="color:#aaa;font-size:10px;">${lok.tipe_lokasi.replace(/_/g,' ')} · conf ${Math.round(lok.kepercayaan*100)}%</span>
        </div>`,
        { direction: 'top', offset: [0, -4], opacity: 1, className: 'minimap-tooltip' },
      )

      circle.addTo(layer)
      bounds.push([lok.latitude, lok.longitude])
    }

    /* Fit bounds ke titik aktif, dengan padding */
    if (bounds.length > 0) {
      try {
        map.fitBounds(L.latLngBounds(bounds), { padding: [18, 18], maxZoom: 9, animate: true })
      } catch {
        /* ignore jika bounds terlalu kecil */
      }
    }
  }, [lokasi, activeProvinsi])

  /* Legend tipe */
  const tipeAktif = Array.from(
    new Set(
      (activeProvinsi.length > 0
        ? lokasi.filter(l => activeProvinsi.includes(l.provinsi))
        : lokasi
      ).map(l => l.tipe_lokasi)
    )
  ).slice(0, 4)

  return (
    <div className="insight-minimap-wrap">
      <div ref={containerRef} className="insight-minimap-canvas" />

      {/* Provinsi aktif pills */}
      {activeProvinsi.length > 0 && (
        <div className="insight-minimap-pills">
          {activeProvinsi.map(p => (
            <span key={p} className="insight-minimap-pill">{p}</span>
          ))}
        </div>
      )}

      {/* Legend tipe */}
      {tipeAktif.length > 0 && (
        <div className="insight-minimap-legend">
          {tipeAktif.map(t => (
            <div key={t} className="insight-minimap-legend-item">
              <span
                className="insight-minimap-legend-dot"
                style={{ background: warnaTipe(t) }}
              />
              <span>{t.replace(/_/g, ' ')}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
