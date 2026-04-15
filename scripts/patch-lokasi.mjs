/**
 * Patch lokasi.json — tambah lokasi dari 25 kota Indonesia
 * Jalankan: node scripts/patch-lokasi.mjs
 */
import { readFileSync, writeFileSync } from 'fs'
import { createHash } from 'crypto'

const KLASTER_KOTA = [
  // Jawa
  { kota: 'Jakarta',    provinsi: 'DKI Jakarta',         lat: -6.2088,  lon: 106.8456, radius_km: 12.0 },
  { kota: 'Bekasi',     provinsi: 'Jawa Barat',          lat: -6.2349,  lon: 106.9896, radius_km: 8.0  },
  { kota: 'Depok',      provinsi: 'Jawa Barat',          lat: -6.4025,  lon: 106.7942, radius_km: 7.0  },
  { kota: 'Tangerang',  provinsi: 'Banten',              lat: -6.1781,  lon: 106.6297, radius_km: 8.0  },
  { kota: 'Bogor',      provinsi: 'Jawa Barat',          lat: -6.5950,  lon: 106.8166, radius_km: 8.5  },
  { kota: 'Bandung',    provinsi: 'Jawa Barat',          lat: -6.9175,  lon: 107.6191, radius_km: 10.0 },
  { kota: 'Semarang',   provinsi: 'Jawa Tengah',         lat: -6.9932,  lon: 110.4203, radius_km: 9.0  },
  { kota: 'Surabaya',   provinsi: 'Jawa Timur',          lat: -7.2575,  lon: 112.7521, radius_km: 11.0 },
  { kota: 'Yogyakarta', provinsi: 'DI Yogyakarta',       lat: -7.7956,  lon: 110.3695, radius_km: 7.0  },
  { kota: 'Malang',     provinsi: 'Jawa Timur',          lat: -7.9666,  lon: 112.6326, radius_km: 8.0  },
  // Sumatera
  { kota: 'Medan',      provinsi: 'Sumatera Utara',      lat:  3.5952,  lon:  98.6722, radius_km: 10.0 },
  { kota: 'Palembang',  provinsi: 'Sumatera Selatan',    lat: -2.9761,  lon: 104.7754, radius_km: 9.0  },
  { kota: 'Pekanbaru',  provinsi: 'Riau',                lat:  0.5071,  lon: 101.4478, radius_km: 8.5  },
  { kota: 'Batam',      provinsi: 'Kepulauan Riau',      lat:  1.0457,  lon: 104.0305, radius_km: 7.5  },
  { kota: 'Padang',     provinsi: 'Sumatera Barat',      lat: -0.9471,  lon: 100.4172, radius_km: 7.0  },
  // Kalimantan
  { kota: 'Balikpapan', provinsi: 'Kalimantan Timur',    lat: -1.2379,  lon: 116.8529, radius_km: 8.0  },
  { kota: 'Samarinda',  provinsi: 'Kalimantan Timur',    lat: -0.5022,  lon: 117.1536, radius_km: 7.5  },
  { kota: 'Banjarmasin',provinsi: 'Kalimantan Selatan',  lat: -3.3186,  lon: 114.5944, radius_km: 7.0  },
  // Sulawesi
  { kota: 'Makassar',   provinsi: 'Sulawesi Selatan',    lat: -5.1477,  lon: 119.4327, radius_km: 10.0 },
  { kota: 'Manado',     provinsi: 'Sulawesi Utara',      lat:  1.4748,  lon: 124.8421, radius_km: 7.0  },
  { kota: 'Palu',       provinsi: 'Sulawesi Tengah',     lat: -0.8997,  lon: 119.8707, radius_km: 6.5  },
  // Bali & NTB
  { kota: 'Denpasar',   provinsi: 'Bali',                lat: -8.6705,  lon: 115.2126, radius_km: 7.5  },
  { kota: 'Mataram',    provinsi: 'NTB',                 lat: -8.5833,  lon: 116.1167, radius_km: 6.5  },
  // Papua
  { kota: 'Jayapura',   provinsi: 'Papua',               lat: -2.5337,  lon: 140.7180, radius_km: 7.0  },
  { kota: 'Sorong',     provinsi: 'Papua Barat',         lat: -0.8641,  lon: 131.2503, radius_km: 6.0  },
]

const TIPE_LOKASI = ['basis_rumah', 'titik_observasi', 'pertemuan_rutin', 'mobilitas_kerja', 'titik_transit']
const LABEL_TMPL  = {
  basis_rumah:     'Area tinggal',
  titik_observasi: 'Titik pengamatan',
  pertemuan_rutin: 'Lokasi pertemuan',
  mobilitas_kerja: 'Area kerja',
  titik_transit:   'Titik transit',
}

// Seed-based PRNG — deterministik
function lcg(seed) {
  let s = seed >>> 0
  return () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 0xffffffff }
}
const rand = lcg(0xdeadbeef)

// Buat id deterministik
function mkId(prefix, i) {
  return `${prefix}-${createHash('sha1').update(String(i + 0xabcd)).digest('hex').slice(0, 10)}`
}

// Gaussian-ish dari uniform
function randGauss(r) { return (r() + r() + r() - 1.5) / 1.5 }

// Tanggal acak dalam 12 bulan terakhir
function randDate(r) {
  const now = new Date('2026-04-15T00:00:00+07:00')
  const past = new Date(now - r() * 365 * 24 * 3600 * 1000)
  return past.toISOString().replace('Z', '+07:00').slice(0, 19) + '+07:00'
}

// Baca profil existing untuk id_profil yang valid
const lokasiLama = JSON.parse(readFileSync('ui/public/data/lokasi.json', 'utf8'))
const idProfilAda = [...new Set(lokasiLama.map(l => l.id_profil))]

// Bobot kota — kota besar dapat lebih banyak titik
const BOBOT = [14,9,7,8,6, 6,5,8,4,4, 6,5,4,4,4, 4,4,4, 5,4,3, 4,3, 3,2]
const totalBobot = BOBOT.reduce((a, b) => a + b, 0)

// Generate jumlah titik per kota proposional, total ~400
const TARGET = 400
const jumlahPerKota = BOBOT.map(b => Math.max(3, Math.round((b / totalBobot) * TARGET)))

const hasil = []
let idx = 0

KLASTER_KOTA.forEach((k, ki) => {
  const n = jumlahPerKota[ki]
  for (let i = 0; i < n; i++) {
    const r1 = randGauss(rand)
    const r2 = randGauss(rand)
    const lat = k.lat + (r1 * k.radius_km / 111.32)
    const lon = k.lon + (r2 * k.radius_km / (111.32 * Math.cos(k.lat * Math.PI / 180)))
    const tipe = TIPE_LOKASI[Math.floor(rand() * TIPE_LOKASI.length)]
    const idProfil = idProfilAda[Math.floor(rand() * idProfilAda.length)]

    hasil.push({
      id_lokasi:   mkId('lok', idx++),
      id_profil:   idProfil,
      tipe_lokasi: tipe,
      label:       `${LABEL_TMPL[tipe]} ${k.kota}`,
      kota:        k.kota,
      provinsi:    k.provinsi,
      latitude:    parseFloat(lat.toFixed(6)),
      longitude:   parseFloat(lon.toFixed(6)),
      diamati_pada: randDate(rand),
      kepercayaan: parseFloat((0.55 + rand() * 0.43).toFixed(2)),
    })
  }
})

writeFileSync('ui/public/data/lokasi.json', JSON.stringify(hasil, null, 2))
console.log(`Selesai: ${hasil.length} lokasi dari ${KLASTER_KOTA.length} kota`)
