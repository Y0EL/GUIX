import { useEffect, useRef } from 'react'
import L from 'leaflet'
import type { Hotspot, Kasus } from '../types'
import { RADIUS_KOTA, buatPoligon, formatTanggal } from '../utils'

/* ── 12 warna kontras untuk choropleth gelap ── */
const PALET: string[] = [
  '#60A5FA', '#34D399', '#A78BFA', '#FBBF24',
  '#F472B6', '#86EFAC', '#67E8F9', '#FB923C',
  '#818CF8', '#2DD4BF', '#E879F9', '#FDE047',
]

/* Indeks warna per provinsi — persisten */
const indProv = new Map<string, number>()
let ctrProv = 0

function warnaProvinsi(state: string): string {
  if (!indProv.has(state)) indProv.set(state, ctrProv++ % PALET.length)
  return PALET[indProv.get(state)!]
}

export type ViewPayload = {
  hotspot: Hotspot[]
  kotaSet: Set<string>
}

type Props = {
  hotspot: Hotspot[]
  kasus: Kasus[]
  onViewChange: (p: ViewPayload) => void
}

export default function PetaOverview({ hotspot, kasus, onViewChange }: Props) {
  const containerRef  = useRef<HTMLDivElement>(null)
  const mapRef        = useRef<L.Map | null>(null)
  const cbRef         = useRef(onViewChange)
  const hotspotRef    = useRef(hotspot)
  cbRef.current      = onViewChange
  hotspotRef.current = hotspot

  /* ── Init map (sekali) ── */
  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    if (mapRef.current) {
      mapRef.current.remove()
      mapRef.current = null
    }

    const map = L.map(el, {
      center: [-2.5, 118.0],
      zoom: 5,
      minZoom: 3,
      maxZoom: 14,
      zoomControl: false,
      attributionControl: false,
    })

    /* Tile gelap */
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      subdomains: 'abcd',
      maxZoom: 14,
    }).addTo(map)

    /* Choropleth provinsi dari GeoJSON offline */
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    fetch('/maps/indonesia.geojson')
      .then(r => { if (!r.ok) throw new Error('GeoJSON not ok'); return r.json() })
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .then((geo: any) => {
        const m = mapRef.current
        if (!m) return
        // Pre-assign warna setiap provinsi
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        geo.features.forEach((f: any) => {
          const nama: string = f.properties?.state ?? ''
          if (nama) warnaProvinsi(nama)
        })
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        L.geoJSON(geo as any, {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          style: (feature: any) => {
            const nama: string = feature?.properties?.state ?? ''
            const warna = warnaProvinsi(nama)
            return {
              fillColor: warna,
              fillOpacity: 0.10,
              color: warna,
              weight: 0.8,
              opacity: 0.30,
            }
          },
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          onEachFeature: (feature: any, layer: L.Layer) => {
            const nama: string = feature?.properties?.state ?? ''
            const warna = warnaProvinsi(nama)
            const path  = layer as L.Path
            path.on('mouseover', () => {
              path.setStyle({ fillOpacity: 0.28, weight: 1.8, opacity: 0.65 })
              path.bindTooltip(nama, {
                permanent: false,
                direction: 'center',
                className: 'leaflet-tooltip-uix',
              }).openTooltip()
            })
            path.on('mouseout', () => {
              path.setStyle({ fillColor: warna, fillOpacity: 0.10, weight: 0.8, opacity: 0.30 })
              path.closeTooltip()
            })
          },
        }).addTo(m)
      })
      .catch(() => { /* gagal dimuat, lanjut tile saja */ })

    /* Viewport change → kirim ke parent */
    function updateView() {
      const bounds = map.getBounds()
      const vis = hotspotRef.current.filter(h =>
        bounds.contains([h.lat, h.lng] as [number, number]),
      )
      cbRef.current({ hotspot: vis, kotaSet: new Set(vis.map(h => h.kota)) })
    }

    map.on('moveend zoomend', updateView)
    const initTimer = setTimeout(updateView, 400)

    mapRef.current = map

    return () => {
      clearTimeout(initTimer)
      map.remove()
      if (mapRef.current === map) mapRef.current = null
    }
  }, [])

  /* ── Hotspot overlay ── */
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    const lapisan = L.layerGroup().addTo(map)

    hotspot.forEach(h => {
      const kasusKotaList = kasus.filter(k => k.kota.toLowerCase() === h.kota.toLowerCase())
      const adaKritis     = kasusKotaList.some(k => k.status === 'monitoring')
      const adaAktif      = kasusKotaList.length > 0

      const warnaBorder   = adaKritis ? '#EF4444' : adaAktif ? '#F97316' : 'rgba(255,255,255,0.32)'
      const fillOpacity   = adaKritis ? 0.28 : adaAktif ? 0.15 : 0.04
      const strokeWeight  = adaKritis ? 2.5  : adaAktif ? 2.0  : 0.9
      const strokeOpacity = adaKritis ? 1.0  : adaAktif ? 0.85 : 0.45
      const dashArray     = adaAktif ? undefined : '6 4'

      const radiusKm  = RADIUS_KOTA[h.kota] ?? 8
      const titikPoly = buatPoligon(h.lat, h.lng, radiusKm, h.kota)

      const polygon = L.polygon(titikPoly, {
        color    : warnaBorder,
        fillColor: warnaBorder,
        fillOpacity,
        weight  : strokeWeight,
        opacity : strokeOpacity,
        dashArray,
      }).addTo(lapisan)

      L.circleMarker([h.lat, h.lng], {
        radius     : adaKritis ? 7 : adaAktif ? 5 : 3,
        color      : warnaBorder,
        fillColor  : warnaBorder,
        fillOpacity: 1,
        weight     : 0,
      }).addTo(lapisan)

      /* Popup — string concat supaya aman dari linter template literal */
      const kasusKota = kasusKotaList.slice(0, 4)
      const kasusHtml = kasusKota.length > 0
        ? kasusKota.map(k =>
            '<div class="pu-kasus-item">' +
            '<span class="pu-badge">' + k.tipe_kasus + '</span>' +
            '<span class="pu-judul">' + k.judul + '</span>' +
            '<span class="pu-meta">' + k.status + ' &middot; ' + k.jumlah_aktor + ' aktor &middot; ' +
              new Date(k.waktu_insiden).toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' }) +
            '</span></div>',
          ).join('')
        : '<div class="pu-kosong">Tidak ada kasus terdaftar</div>'

      const popupHtml =
        '<div class="popup-uix">' +
          '<div class="pu-header">' +
            '<span class="pu-dot" style="background:' + warnaBorder + '"></span>' +
            '<strong>' + h.kota + '</strong>' +
            '<span class="pu-prov">' + h.provinsi + '</span>' +
          '</div>' +
          '<div class="pu-stats">' +
            '<div class="pu-stat"><span class="pu-val">' + h.profil + '</span><span class="pu-lbl">profil</span></div>' +
            '<div class="pu-stat"><span class="pu-val">' + h.jumlah + '</span><span class="pu-lbl">titik data</span></div>' +
            '<div class="pu-stat"><span class="pu-val">' + Math.round(h.kepercayaan) + '%</span><span class="pu-lbl">kepercayaan</span></div>' +
          '</div>' +
          '<div class="pu-kasus-header">Kasus Terkait</div>' +
          '<div class="pu-kasus-list">' + kasusHtml + '</div>' +
          '<div class="pu-footer">Terakhir dipantau: ' + formatTanggal(h.terakhir) + '</div>' +
        '</div>'

      polygon.bindPopup(
        L.popup({ className: 'popup-uix-wrapper', maxWidth: 320, minWidth: 280, autoPan: true })
          .setContent(popupHtml),
      )
    })

    /* Kirim update viewport setelah hotspot dirender */
    const bounds = map.getBounds()
    const vis = hotspot.filter(h => bounds.contains([h.lat, h.lng] as [number, number]))
    cbRef.current({ hotspot: vis, kotaSet: new Set(vis.map(h => h.kota)) })

    return () => { lapisan.remove() }
  }, [hotspot, kasus])

  /* Sync hotspotRef ke prop terbaru */
  useEffect(() => { hotspotRef.current = hotspot }, [hotspot])

  return <div ref={containerRef} className="cesium-container" />
}
