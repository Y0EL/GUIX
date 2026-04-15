export type Kasus = {
  id_kasus: string
  tipe_kasus: string
  judul: string
  kota: string
  provinsi: string
  waktu_insiden: string
  jumlah_aktor: number
  status: string
}

export type Lokasi = {
  id_lokasi: string
  id_profil: string
  tipe_lokasi: string
  label: string
  kota: string
  provinsi: string
  latitude: number
  longitude: number
  diamati_pada: string
  kepercayaan: number
}

export type Peringatan = {
  id_peringatan: string
  id_kasus: string
  tingkat_keparahan: 'tinggi' | 'menengah' | 'rendah'
  tipe_sinyal: string
  deskripsi: string
  kepercayaan: number
  pesan?: string
  waktu?: string
}

export type Berita = {
  id: string
  judul: string
  subjudul?: string
  kategori: string
  lokasi: string
  provinsi?: string
  portal?: string
  published_at: string
  tags?: string[]
  image_local?: string
}

export type KlasterPesan = {
  id_klaster_pesan: string
  id_kasus: string
  frasa_kanonik: string
  id_profil: string[]
  jumlah_posting: number
  kemiripan_copy: number
}

export type Hotspot = {
  id: string
  kota: string
  provinsi: string
  lat: number
  lng: number
  jumlah: number
  kepercayaan: number
  profil: number
  terakhir: string
}

export type MetrikData = {
  kritis: number
  tinggi: number
  sedang: number
  subjek: number
  wilayah: number
}

export type StatusSistem = {
  id: string
  label: string
  status: 'ok' | 'warning' | 'error'
  detail: string
}

export type TriageStatus =
  | 'baru'
  | 'dilihat'
  | 'valid'
  | 'false_positive'
  | 'eskalasi'
  | 'diabaikan'

export type GroupMode = 'flat' | 'kasus' | 'tipe' | 'wilayah'

export type Entitas = {
  id_kasus: string
  tipe_entitas: 'lokasi' | 'kata_kunci' | 'jangkar_waktu'
  nilai: string
  jumlah: number
}

export type AlertWithTriage = Peringatan & {
  triage: TriageStatus
  assignee?: string
  note?: string
  tags?: string[]
}

/* ── Halaman 3 — Incident Queue ── */

export type IncidentStatus =
  | 'baru'
  | 'monitoring'
  | 'analisis'
  | 'eskalasi'
  | 'selesai'

export type SkorRisiko = {
  id_kasus: string
  label_risiko: 'tinggi' | 'menengah' | 'rendah'
  skor_risiko: number
  pendorong: string[]
  penafian: string
  probabilitas?: Record<string, number>   // probabilitas_* keys berbeda tiap kasus
  [key: string]: unknown
}

export type IncidentWithMeta = Kasus & {
  skor: SkorRisiko | null
  alertCount: number
  linkedAlerts: Peringatan[]
  runtimeStatus: IncidentStatus
  assignedAnalyst: string | null
  flaggedForBriefing: boolean
}

export type Postingan = {
  id_posting: string
  id_profil: string
  platform: string
  konten: string
  timestamp: string
  kota: string
  provinsi: string
  tipe_konten: string
  engagement: { suka: number; komentar: number; bagikan: number }
  hashtag: string[]
  kata_kunci: string[]
  balas_ke_id_posting?: string | null
}

export type Laporan = {
  id_laporan: string
  id_kasus: string
  judul: string
  ringkasan: string
  temuan: string[]
  analisis: string
  rekomendasi: string[]
  digenerate_pada: string
  penafian: string
}

export type ProfilAkun = {
  platform: string
  username: string
  dibuat_pada: string
  terakhir_aktif_pada: string
}

export type Profil = {
  id_profil: string
  nama_lengkap: string
  nama_tampil: string
  jenis_kelamin: string
  rentang_tahun_lahir: string
  bio: string
  url_avatar: string
  avatar_lokal: string | null
  kode_negara: string
  kota: string
  provinsi: string
  latitude: number
  longitude: number
  bahasa: string[]
  dibuat_pada: string
  tag_risiko: string[]
  tautan_kasus: Array<{ id_kasus: string; id_profil: string; peran: string; sinyal: string }>
  id_klaster: string[]
  profil_terekstrak: {
    akun: ProfilAkun[]
    statistik: {
      jumlah_akun: number
      jumlah_teman: number
      jumlah_foto: number
      jumlah_posting: number
    }
  }
}

export type Pertemanan = {
  id_pertemanan: string
  profil_a: string
  profil_b: string
  kekuatan: number
  id_klaster: string
  sejak: string
  adalah_jembatan?: boolean
}

export type SearchResult = {
  tipe: 'profil' | 'kasus' | 'lokasi' | 'postingan'
  id: string
  matchScore: number
  matchedFields: string[]
  data: Profil | Kasus | Lokasi | Postingan
}

export type Transaksi = {
  id_transaksi: string
  id_kasus: string
  id_profil_sumber: string
  id_profil_tujuan: string
  jumlah_idr: number
  timestamp: string
  kanal: string
  referensi: string
  petunjuk_tujuan: string
  id_perangkat_bersama: string
  ip_bersama: string
}

/* ── Halaman 4 — Map Intelligence ── */

export type Wilayah = {
  id_wilayah: string
  nama: string
  provinsi: string
  total_kasus: number
  alert_aktif: number
  skor_risiko_rata: number
  severity_tertinggi: 'tinggi' | 'menengah' | 'rendah'
  koordinat_pusat: [number, number]
}
