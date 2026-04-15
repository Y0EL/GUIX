import { useEffect, useRef, useImperativeHandle, forwardRef } from 'react'
import L from 'leaflet'
import type { Lokasi, Kasus, Peringatan, SkorRisiko } from '../types'

export type MapCanvasHandle = {
  flyTo: (lat: number, lng: number, zoom?: number) => void
  resetView: () => void
}

type Props = {
  lokasi: Lokasi[]
  kasus: Kasus[]
  peringatan: Peringatan[]
  skorRisiko: SkorRisiko[]
  filterSeverity: string[]
  filterTipeLokasi: string[]
  labelEnabled: boolean
  onSelectLokasi: (l: Lokasi) => void
}

const SEV_COLOR: Record<string, string> = {
  tinggi:   '#E5282A',
  menengah: '#F5A623',
  rendah:   '#4CAF50',
}

/** Tentukan severity sebuah lokasi berdasarkan profil → kasus → skor_risiko */
function severitasLokasi(
  lok: Lokasi,
  kasus: Kasus[],
  peringatan: Peringatan[],
  skorRisiko: SkorRisiko[],
): string {
  // Cari kasus yang berada di kota/provinsi sama
  const kasusWilayah = kasus.filter(k => k.provinsi === lok.provinsi)
  if (kasusWilayah.length === 0) return 'rendah'

  // Alert tertinggi dari kasus di wilayah ini
  const sev_order: Record<string, number> = { tinggi: 3, menengah: 2, rendah: 1 }
  let maxSev = 'rendah'
  for (const k of kasusWilayah) {
    const alerts = peringatan.filter(p => p.id_kasus === k.id_kasus)
    for (const a of alerts) {
      if (sev_order[a.tingkat_keparahan] > sev_order[maxSev]) {
        maxSev = a.tingkat_keparahan
      }
    }
    // Fallback: pakai label_risiko dari skor
    const sr = skorRisiko.find(s => s.id_kasus === k.id_kasus)
    if (sr && sev_order[sr.label_risiko] > sev_order[maxSev]) {
      maxSev = sr.label_risiko
    }
  }
  return maxSev
}

/** Hitung jumlah alert terkait lokasi (via provinsi) */
function hitungAlert(lok: Lokasi, kasus: Kasus[], peringatan: Peringatan[]): number {
  const kasusIds = kasus
    .filter(k => k.provinsi === lok.provinsi)
    .map(k => k.id_kasus)
  return peringatan.filter(p => kasusIds.includes(p.id_kasus)).length
}

const MapCanvas = forwardRef<MapCanvasHandle, Props>(function MapCanvas(
  { lokasi, kasus, peringatan, skorRisiko, filterSeverity, filterTipeLokasi, labelEnabled, onSelectLokasi },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const layerRef = useRef<L.LayerGroup | null>(null)

  // Expose flyTo & resetView ke parent
  useImperativeHandle(ref, () => ({
    flyTo(lat, lng, zoom = 11) {
      mapRef.current?.flyTo([lat, lng], zoom, { duration: 1.2 })
    },
    resetView() {
      mapRef.current?.flyTo([-2.5, 118.0], 5, { duration: 1.2 })
    },
  }))

  /* ── Init peta sekali ── */
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    if (mapRef.current) { mapRef.current.remove(); mapRef.current = null }

    const map = L.map(el, {
      center: [-2.5, 118.0],
      zoom: 5,
      minZoom: 3,
      maxZoom: 16,
      zoomControl: false,
      attributionControl: false,
    })

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
    }).addTo(map)

    L.control.zoom({ position: 'bottomright' }).addTo(map)

    layerRef.current = L.layerGroup().addTo(map)
    mapRef.current = map

    return () => { map.remove(); mapRef.current = null }
  }, [])

  /* ── Re-render marker saat filter/data berubah ── */
  useEffect(() => {
    const layer = layerRef.current
    if (!layer) return
    layer.clearLayers()

    const filtered = lokasi.filter(lok => {
      const sev = severitasLokasi(lok, kasus, peringatan, skorRisiko)
      const okSev = filterSeverity.length === 0 || filterSeverity.includes(sev)
      const okTipe = filterTipeLokasi.length === 0 || filterTipeLokasi.includes(lok.tipe_lokasi)
      return okSev && okTipe
    })

    for (const lok of filtered) {
      const sev = severitasLokasi(lok, kasus, peringatan, skorRisiko)
      const color = SEV_COLOR[sev] ?? '#888'
      const alertCount = hitungAlert(lok, kasus, peringatan)

      // Ring luar (pulse visual)
      L.circleMarker([lok.latitude, lok.longitude], {
        radius: 14 + alertCount * 2,
        color,
        weight: 1,
        fillColor: color,
        fillOpacity: 0.08,
        interactive: false,
      }).addTo(layer)

      // Ring tengah
      L.circleMarker([lok.latitude, lok.longitude], {
        radius: 8,
        color,
        weight: 1.5,
        fillColor: color,
        fillOpacity: 0.2,
        interactive: false,
      }).addTo(layer)

      // Titik pusat — interaktif
      const marker = L.circleMarker([lok.latitude, lok.longitude], {
        radius: 5,
        color,
        weight: 2,
        fillColor: color,
        fillOpacity: 0.95,
      }).addTo(layer)

      // Label kota — permanent hanya untuk lokasi dengan alert (menghindari overlap)
      // Untuk lokasi tanpa alert, tooltip muncul saat hover
      if (labelEnabled && alertCount > 0) {
        L.tooltip({
          permanent: true,
          direction: 'top',
          offset: [0, -12],
          className: 'mi-map-label',
        })
          .setContent(lok.kota)
          .setLatLng([lok.latitude, lok.longitude])
          .addTo(layer)
      } else if (labelEnabled) {
        marker.bindTooltip(lok.kota, {
          direction: 'top',
          offset: [0, -8],
          className: 'mi-map-label',
        })
      }

      // Badge alert count
      if (alertCount > 0) {
        const icon = L.divIcon({
          html: `<div class="mi-alert-badge">${alertCount}</div>`,
          className: '',
          iconSize: [18, 18],
          iconAnchor: [-4, 12],
        })
        L.marker([lok.latitude, lok.longitude], { icon, interactive: false }).addTo(layer)
      }

      marker.on('click', () => onSelectLokasi(lok))
      marker.on('mouseover', () => marker.setStyle({ radius: 8 }))
      marker.on('mouseout', () => marker.setStyle({ radius: 5 }))
    }
  }, [lokasi, kasus, peringatan, skorRisiko, filterSeverity, filterTipeLokasi, labelEnabled, onSelectLokasi])

  return <div ref={containerRef} className="mi-canvas" />
})

export default MapCanvas
