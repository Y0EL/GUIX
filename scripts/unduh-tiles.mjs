#!/usr/bin/env node
/**
 * Unduh tiles peta CartoDB Dark Matter untuk wilayah Indonesia.
 * Simpan ke ui/public/tiles/{z}/{x}/{y}.png
 *
 * Jalankan dari root proyek:
 *   node scripts/unduh-tiles.mjs
 *
 * Tiles yang sudah ada dilewati — aman dijalankan ulang.
 */

import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const OUTPUT_DIR = path.join(__dirname, '..', 'ui', 'public', 'tiles')

const TILE_URL = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png'
const SUBDOMAINS = ['a', 'b', 'c', 'd']
const DELAY_MS = 1   // ms antar request — jangan terlalu agresif ke server

/* Bounding box Indonesia + sedikit padding */
const BBOX = { west: 93, east: 143, north: 8, south: -13 }
const ZOOM_MIN = 3
const ZOOM_MAX = 8   // ~900 tiles total, ~12-18 MB

/* ── Utilitas konversi koordinat → tile ── */
function lonToX(lon, z) {
  return Math.floor(((lon + 180) / 360) * Math.pow(2, z))
}

function latToY(lat, z) {
  const rad = (lat * Math.PI) / 180
  return Math.floor(
    ((1 - Math.log(Math.tan(rad) + 1 / Math.cos(rad)) / Math.PI) / 2) *
      Math.pow(2, z)
  )
}

function jeda(ms) {
  return new Promise((res) => setTimeout(res, ms))
}

/* ── Unduh satu tile ── */
async function unduhTile(z, x, y) {
  const dest = path.join(OUTPUT_DIR, String(z), String(x), `${y}.png`)
  if (fs.existsSync(dest)) return 'lewat'

  fs.mkdirSync(path.dirname(dest), { recursive: true })

  const sub = SUBDOMAINS[(x + y) % SUBDOMAINS.length]
  const url = TILE_URL
    .replace('{s}', sub)
    .replace('{z}', String(z))
    .replace('{x}', String(x))
    .replace('{y}', String(y))

  const res = await fetch(url, {
    headers: { 'User-Agent': 'UIX-Demo-App/1.0 (offline-tile-cache)' },
  })
  if (!res.ok) throw new Error(`HTTP ${res.status} — ${url}`)

  const buf = Buffer.from(await res.arrayBuffer())
  fs.writeFileSync(dest, buf)
  return 'ok'
}

/* ── Main ── */
async function main() {
  const daftar = []
  for (let z = ZOOM_MIN; z <= ZOOM_MAX; z++) {
    const xMin = lonToX(BBOX.west, z)
    const xMax = lonToX(BBOX.east, z)
    const yMin = latToY(BBOX.north, z)
    const yMax = latToY(BBOX.south, z)
    for (let x = xMin; x <= xMax; x++) {
      for (let y = yMin; y <= yMax; y++) {
        daftar.push({ z, x, y })
      }
    }
  }

  console.log(`UIX — Unduh Tiles Offline`)
  console.log(`Tujuan  : ${OUTPUT_DIR}`)
  console.log(`Zoom    : ${ZOOM_MIN}–${ZOOM_MAX}`)
  console.log(`Total   : ${daftar.length} tiles`)
  console.log(`Estimasi: ~${Math.round(daftar.length * DELAY_MS / 1000)}s\n`)

  let ok = 0, lewat = 0, gagal = 0

  for (const { z, x, y } of daftar) {
    try {
      const hasil = await unduhTile(z, x, y)
      if (hasil === 'lewat') {
        lewat++
      } else {
        ok++
        await jeda(DELAY_MS)
      }
      const total = ok + lewat + gagal
      process.stdout.write(
        `\r  [${total}/${daftar.length}] z=${z} x=${x} y=${y}   `
      )
    } catch (e) {
      gagal++
      console.error(`\n  Gagal z=${z} x=${x} y=${y}: ${e.message}`)
    }
  }

  console.log(`\n\nSelesai!`)
  console.log(`  Diunduh : ${ok}`)
  console.log(`  Dilewati: ${lewat} (sudah ada)`)
  if (gagal > 0) console.log(`  Gagal   : ${gagal} — jalankan ulang untuk retry`)
}

main().catch(console.error)
