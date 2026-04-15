import type { Hotspot, Lokasi } from './types'

export function muatJson<T>(url: string): Promise<T> {
  return fetch(url).then((r) => {
    if (!r.ok) throw new Error(`Gagal memuat ${url}`)
    return r.json() as Promise<T>
  })
}

export function waktuJam() {
  return new Date().toLocaleTimeString('id-ID', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export function tanggalHariIni() {
  return new Date().toLocaleDateString('id-ID', {
    weekday: 'long',
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  })
}

export function formatTanggal(iso: string) {
  return new Date(iso).toLocaleString('id-ID', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function warnaHeat(rasio: number): string {
  if (rasio >= 0.75) return '#E53E3E'
  if (rasio >= 0.5) return '#DD6B20'
  if (rasio >= 0.3) return '#D69E2E'
  return '#38A169'
}

/* ── Warna per pulau/region ── */
const WARNA_REGION: Record<string, string> = {
  // Jawa
  Jakarta: '#3B82F6', Bekasi: '#3B82F6', Depok: '#3B82F6',
  Tangerang: '#3B82F6', Bogor: '#3B82F6', Bandung: '#3B82F6',
  Semarang: '#3B82F6', Surabaya: '#3B82F6', Yogyakarta: '#3B82F6', Malang: '#3B82F6',
  // Sumatra
  Medan: '#10B981', Palembang: '#10B981', Pekanbaru: '#10B981',
  Batam: '#10B981', Padang: '#10B981',
  // Kalimantan
  Balikpapan: '#8B5CF6', Samarinda: '#8B5CF6', Banjarmasin: '#8B5CF6',
  // Sulawesi
  Makassar: '#F59E0B', Manado: '#F59E0B', Palu: '#F59E0B',
  // Bali & Nusa Tenggara
  Denpasar: '#EC4899', Mataram: '#EC4899',
  // Papua & Maluku
  Jayapura: '#84CC16', Sorong: '#84CC16',
}

export function warnaRegion(kota: string): string {
  return WARNA_REGION[kota] ?? '#6B7280'
}

/* Radius kota (km) — sesuai definisi klaster di synthetic_dataset.py */
export const RADIUS_KOTA: Record<string, number> = {
  Jakarta: 12, Bekasi: 8, Depok: 7, Tangerang: 8, Bogor: 8.5,
  Bandung: 10, Semarang: 9, Surabaya: 11, Yogyakarta: 7, Malang: 8,
  Medan: 10, Palembang: 9, Pekanbaru: 8.5, Batam: 7.5, Padang: 7,
  Balikpapan: 8, Samarinda: 7.5, Banjarmasin: 7,
  Makassar: 10, Manado: 7, Palu: 6.5,
  Denpasar: 7.5, Mataram: 6.5,
  Jayapura: 7, Sorong: 6,
}

/* Poligon tidak beraturan — bentuk deterministik seeded dari nama kota */
export function buatPoligon(
  lat: number,
  lng: number,
  radiusKm: number,
  seed: string,
): [number, number][] {
  let s = 0
  for (let i = 0; i < seed.length; i++) s = (s * 31 + seed.charCodeAt(i)) & 0xffffffff
  function rand() {
    s = (s * 1664525 + 1013904223) & 0xffffffff
    return (s >>> 0) / 0xffffffff
  }
  const sisi = 10
  const latRad = (lat * Math.PI) / 180
  const titik: [number, number][] = []
  for (let i = 0; i < sisi; i++) {
    const sudut = (i / sisi) * 2 * Math.PI - Math.PI / 2
    const r = radiusKm * (0.5 + 0.85 * rand())
    const dlat = (r / 111.32) * Math.cos(sudut)
    const dlng = (r / (111.32 * Math.cos(latRad))) * Math.sin(sudut)
    titik.push([lat + dlat, lng + dlng])
  }
  return titik
}

/* ── Halaman 3 helpers ── */

import type { SkorRisiko } from './types'

export function extractProbabilities(
  skor: SkorRisiko,
): { label: string; value: number }[] {
  return Object.entries(skor)
    .filter(([k, v]) => k.startsWith('probabilitas_') && typeof v === 'number')
    .map(([k, v]) => ({
      label: k.replace('probabilitas_', '').replace(/_/g, ' '),
      value: v as number,
    }))
}

type SLAKelas = 'segar' | 'aging' | 'overdue'

export function hitungSLA(waktuInsiden: string): { label: string; kelas: SLAKelas } {
  const insiden = new Date(waktuInsiden).getTime()
  const sekarang = Date.now()
  const selisihMs = sekarang - insiden
  const jamTotal = selisihMs / (1000 * 60 * 60)

  let label: string
  if (jamTotal < 1) {
    const menit = Math.floor(selisihMs / (1000 * 60))
    label = `${menit}m`
  } else if (jamTotal < 24) {
    label = `${Math.floor(jamTotal)}j`
  } else {
    const hari = Math.floor(jamTotal / 24)
    const sisaJam = Math.floor(jamTotal % 24)
    label = sisaJam > 0 ? `${hari}h ${sisaJam}j` : `${hari}h`
  }

  const kelas: SLAKelas = jamTotal < 24 ? 'segar' : jamTotal <= 72 ? 'aging' : 'overdue'
  return { label, kelas }
}

/* Agregasi lokasi → hotspot per kota */
export function agregasiHotspot(lokasi: Lokasi[]): Hotspot[] {
  const map = new Map<
    string,
    {
      kota: string
      provinsi: string
      total: number
      kepTotal: number
      latSum: number
      lonSum: number
      profil: Set<string>
      terakhir: string
    }
  >()

  for (const item of lokasi) {
    const key = `${item.kota}|${item.provinsi}`
    const ada = map.get(key)
    if (!ada) {
      map.set(key, {
        kota: item.kota,
        provinsi: item.provinsi,
        total: 1,
        kepTotal: item.kepercayaan,
        latSum: item.latitude,
        lonSum: item.longitude,
        profil: new Set([item.id_profil]),
        terakhir: item.diamati_pada,
      })
    } else {
      ada.total++
      ada.kepTotal += item.kepercayaan
      ada.latSum += item.latitude
      ada.lonSum += item.longitude
      ada.profil.add(item.id_profil)
      if (+new Date(item.diamati_pada) > +new Date(ada.terakhir)) ada.terakhir = item.diamati_pada
    }
  }

  return Array.from(map.entries()).map(([id, v]) => ({
    id,
    kota: v.kota,
    provinsi: v.provinsi,
    lat: v.latSum / v.total,
    lng: v.lonSum / v.total,
    jumlah: v.total,
    kepercayaan: v.kepTotal / v.total,
    profil: v.profil.size,
    terakhir: v.terakhir,
  }))
}
