"""
Generator persona dan insiden sintetis untuk pengujian internal.
Versi tanpa OpenAI — semua teks dihasilkan dari template lokal yang diperluas.
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import string
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

ZONA_INDONESIA = timezone(timedelta(hours=7))
# ============================================================
# GENERATOR NAMA INDONESIA (tanpa library eksternal)
# ============================================================

_NAMA_DEPAN_PRIA = [
    "Adi", "Agus", "Ahmad", "Amir", "Andika", "Andre", "Anton", "Arif", "Arman", "Bagas",
    "Budi", "Dani", "Denny", "Dian", "Didik", "Dimas", "Dwi", "Eko", "Fajar", "Fandi",
    "Fauzi", "Febri", "Ferdi", "Ganda", "Gilang", "Hadi", "Hendra", "Heru", "Iwan", "Joko",
    "Kevin", "Lutfi", "Mario", "Muhamad", "Nanda", "Nugroho", "Pandu", "Ragil", "Reza", "Ridho",
    "Rio", "Rizal", "Rizky", "Roni", "Ryan", "Sapto", "Sigit", "Slamet", "Surya", "Teguh",
    "Toni", "Tri", "Udin", "Wahyu", "Wawan", "Widi", "Yogi", "Yudha", "Yusuf", "Zaki",
    "Alif", "Bayu", "Candra", "Danu", "Erik", "Fuad", "Gunawan", "Hafiz", "Imam", "Jefri",
    "Krisna", "Lukman", "Mahendra", "Nanang", "Oki", "Panji", "Rafi", "Sandy", "Taufik", "Ucup",
    "Vino", "Wisnu", "Yanto", "Zainal", "Abdi", "Bramasto", "Cahyo", "Darma", "Erwin", "Firman",
    "Galih", "Hamid", "Indra", "Julio", "Karim", "Luthfi", "Mamat", "Niko", "Oky", "Prima",
]
_NAMA_DEPAN_WANITA = [
    "Aini", "Alya", "Amanda", "Andini", "Anggi", "Anisa", "Annisa", "Ayu", "Bella", "Cinta",
    "Desi", "Dewi", "Diana", "Dina", "Eka", "Elisa", "Ella", "Erni", "Fani", "Fatimah",
    "Febri", "Fitri", "Gita", "Hana", "Hesti", "Indah", "Ines", "Intan", "Julia", "Kartika",
    "Laila", "Leni", "Linda", "Lisa", "Lita", "Maya", "Mega", "Melati", "Mia", "Nadia",
    "Nanda", "Nani", "Nita", "Novi", "Nurul", "Putri", "Ratna", "Reni", "Rina", "Rini",
    "Santi", "Sarah", "Sari", "Sela", "Sinta", "Siti", "Sri", "Tari", "Tiara", "Tina",
    "Tri", "Ulfa", "Vika", "Wahyu", "Winda", "Wulan", "Yeni", "Yuliana", "Yuni", "Zahra",
    "Adinda", "Berliana", "Cantika", "Damayanti", "Elok", "Farah", "Gracia", "Hilda", "Irma", "Jasmine",
    "Kinasih", "Lestari", "Mutia", "Nabilah", "Olivia", "Permata", "Qonita", "Rara", "Safira", "Titi",
    "Ulfah", "Viona", "Wati", "Xena", "Yolanda", "Zainab", "Afifia", "Bening", "Cahaya", "Dara",
]
_NAMA_BELAKANG = [
    "Santoso", "Wijaya", "Kusuma", "Rahayu", "Pratama", "Setiawan", "Putra", "Utama", "Sanjaya", "Hadiyanto",
    "Nugroho", "Purnomo", "Kurniawan", "Wahyudi", "Susanto", "Hidayat", "Hartono", "Prasetyo", "Gunawan", "Saputra",
    "Wibowo", "Hakim", "Siregar", "Simbolon", "Nasution", "Sitompul", "Manurung", "Lubis", "Hasibuan", "Siahaan",
    "Suryadi", "Permana", "Wahyono", "Budiman", "Firmansyah", "Irawan", "Sulistyo", "Handoko", "Mulyono", "Supriyanto",
    "Adiputra", "Basuki", "Cahyono", "Darwanto", "Endarto", "Fathoni", "Ginanjar", "Halim", "Iskandar", "Jatmiko",
    "Kristanto", "Laksono", "Mahardika", "Nuraini", "Oktavian", "Prabowo", "Qomarudin", "Ramadhan", "Sudarmo", "Taufiqurrahman",
    "Utomo", "Valentino", "Widodo", "Yasin", "Zulkarnain", "Abdillah", "Budianto", "Cahyadi", "Darmawan", "Effendi",
    "Fadillah", "Gunarso", "Haryanto", "Ikhsan", "Juwono", "Kartono", "Listiyono", "Muhaimin", "Natsir", "Oryza",
    "Pujiyanto", "Rohman", "Supriadi", "Trisno", "Umar", "Valentina", "Widyanto", "Yuliono", "Zaenuri", "Ardiansyah",
    "Baskoro", "Ciptadi", "Darsono", "Erwanto", "Firdaus", "Gumilang", "Hamdani", "Irfandi", "Junaedi", "Koswara",
]


class GeneratorNamaIndonesia:
    """Generator nama Indonesia tanpa dependensi eksternal."""

    def __init__(self, rng: random.Random):
        self.rng = rng

    def nama_pria(self) -> str:
        depan = self.rng.choice(_NAMA_DEPAN_PRIA)
        belakang = self.rng.choice(_NAMA_BELAKANG)
        if self.rng.random() < 0.3:
            depan2 = self.rng.choice(_NAMA_DEPAN_PRIA)
            return f"{depan} {depan2} {belakang}"
        return f"{depan} {belakang}"

    def nama_wanita(self) -> str:
        depan = self.rng.choice(_NAMA_DEPAN_WANITA)
        belakang = self.rng.choice(_NAMA_BELAKANG)
        if self.rng.random() < 0.3:
            depan2 = self.rng.choice(_NAMA_DEPAN_WANITA)
            return f"{depan} {depan2} {belakang}"
        return f"{depan} {belakang}"


ENDPOINT_AVATAR = "https://100k-faces.vercel.app/api/random-image"
SUMBER_AVATAR = "100k-faces"

# ============================================================
# TEMPLATE TEKS YANG DIPERBANYAK
# ============================================================

TEMPLATE_BIO = [
    "Aktif di komunitas {minat}. Sering mobile antara {kota} dan sekitarnya.",
    "Suka ngobrol soal {minat}, kerja fleksibel, dan sering nongkrong di {kota}.",
    "Tertarik pada {minat}, update isu lokal, dan sering dokumentasi kegiatan harian.",
    "Ngurus operasional kecil-kecilan, hobi {minat}, dan punya circle terbatas di {kota}.",
    "Akun personal untuk catatan kegiatan, minat {minat}, dan koneksi komunitas lokal.",
    "Tinggal di {kota}, sibuk dengan {minat} dan hal-hal sekitar lingkungan.",
    "Freelancer yang juga aktif di komunitas {minat}. Base di {kota} tapi sering keliling.",
    "Suka share insight soal {minat}. Keseharian di {kota} dan sekitarnya.",
    "Remote worker. Hobi utama {minat}, sesekali dokumentasi jalan-jalan.",
    "Warga lokal {kota} yang aktif di forum dan diskusi seputar {minat}.",
    "Cuma orang biasa yang seneng {minat} dan update soal {kota}.",
    "Pengguna aktif sejak lama. Biasa bahas {minat} dan isu-isu ringan harian.",
    "Nongkrong online di {kota}. Topik favorit: {minat} dan hal sehari-hari.",
    "Punya usaha kecil, aktif komunitas {minat}, dan suka jalan-jalan di {kota}.",
    "Sering nulis catatan soal {minat}. Mayoritas aktivitas dari {kota}.",
    "Anggota beberapa grup {minat}. Sesekali update lokasi dan kegiatan dari {kota}.",
    "Bukan siapa-siapa, cuma hobi {minat} dan ngikutin perkembangan lokal di {kota}.",
    "Part-time content creator, full-time penggemar {minat}. Domisili {kota}.",
    "Suka eksplorasi tempat baru di sekitar {kota} sambil update soal {minat}.",
    "Bergabung karena {minat}, menetap karena komunitasnya. Lokasi: {kota}.",
    "Keseharian di {kota}, topik utama {minat}, sesekali bahas hal di luar itu.",
    "Diam-diam aktif di komunitas {minat}. Jarang posting tapi sering baca.",
    "Hidup nomaden di antara {kota} dan sekitarnya. Senang diskusi soal {minat}.",
    "Penasaran dengan banyak hal, tapi fokus utama tetap di {minat}.",
    "Akun untuk keperluan pribadi. Topik: {minat}, lokasi utama: {kota}.",
    "Update harian dari {kota}. Isi konten mostly soal {minat} dan kegiatan lokal.",
    "Santai tapi konsisten nulis soal {minat}. Berasa di rumah di {kota}.",
    "Gabung komunitas {minat} dari awal. Sekarang tinggal di {kota}.",
    "Sering cek update {minat} sambil menikmati suasana {kota} tiap hari.",
    "Senang bikin konten ringan soal {minat} dan kehidupan di {kota}.",
    "Wiraswasta yang aktif di forum {minat}. Sesekali nulis dari {kota}.",
    "Ngikutin perkembangan {minat} dari jauh, tapi base tetap di {kota}.",
    "Koleksi foto, diskusi {minat}, dan ngobrol soal dinamika lokal {kota}.",
    "Masih belajar banyak soal {minat}. Sementara itu tinggal nyaman di {kota}.",
    "Orang lapangan yang suka nulis. Minat utama {minat}, lokasi {kota}.",
    "Aktif tapi low profile. Topik: {minat}. Domisili: sekitar {kota}.",
    "Sehari-hari urus {minat} dan sesekali share cerita dari sudut {kota}.",
    "Masih aktif di komunitas {minat} walau udah lama gabung. Based di {kota}.",
    "Bukan influencer, cuma orang yang suka bahas {minat} di {kota}.",
    "Catatan harian dari {kota} — mostly soal {minat} dan hal-hal sekitar.",
]

TEMPLATE_POSTING = [
    "Lagi fokus urus agenda minggu ini. {tagline}",
    "Baru kelar ketemu teman lama di {kota}. {tagline}",
    "Kalau malam begini enak buat beresin kerjaan sambil pantau update {minat}.",
    "Hari ini ramai juga di sekitar {kota}.",
    "Masih cari referensi soal {minat}. Ada yang punya rekomendasi?",
    "Nanti malam kumpul singkat, semoga semua lancar.",
    "Kadang insight paling bagus datang pas lagi perjalanan pulang.",
    "Weekend begini biasanya santai, tapi timeline malah ramai.",
    "Lagi ngulik soal {minat}, ternyata seru juga kalau ditelisik.",
    "Balik ke {kota} setelah beberapa hari keluar. Capek tapi produktif.",
    "Diskusi panjang soal {minat} tadi, banyak yang belum kepikiran sebelumnya.",
    "Pagi yang sibuk, tapi sempet juga update soal {minat}.",
    "Coba hal baru minggu ini. Berhubungan sama {minat}, hasilnya lumayan.",
    "Salam dari {kota}. Hari ini cukup padat tapi masih bisa online.",
    "Lagi baca-baca soal {minat}. Banyak banget yang belum tau sebelumnya.",
    "Update dari lapangan. Situasi sekitar {kota} hari ini agak berbeda dari biasanya.",
    "Meeting selesai. Sekarang me-time sambil ngulik {minat}.",
    "Entah kenapa diskusi soal {minat} makin ramai belakangan ini.",
    "Tadi keliling area {kota}, suasananya agak berbeda dari biasanya.",
    "Masih standby. Sambil nunggu, update dulu soal {minat}.",
    "Hari ini banyak notif masuk soal {minat}. Ramai juga komunitasnya.",
    "Selesai urusan lapangan. Saatnya update dan baca-baca lagi.",
    "Nggak banyak yang berubah di {kota}, tapi diskusi {minat} makin seru.",
    "Lagi istirahat sebentar. Sambil scroll timeline soal {minat}.",
    "Ada yang tau update terbaru soal {minat}? Share dong kalau ada.",
    "Habis keliling {kota} tadi. Capek tapi puas bisa lihat langsung situasinya.",
    "Pindah titik sebentar. Masih sekitar {kota}.",
    "Lagi di perjalanan. Nggak bisa jauh dari update soal {minat}.",
    "Baru sadar udah lama nggak nulis soal {minat}. Yuk mulai lagi.",
    "Catch-up sama teman komunitas {minat} tadi. Ternyata banyak update.",
    "Malam yang cukup tenang di {kota}. Cocok buat mikir-mikir soal {minat}.",
    "Coba cari sudut pandang lain soal {minat}. Kadang perspektif baru itu perlu.",
    "Urusan selesai lebih cepat dari dugaan. Sisa waktu buat update.",
    "Lagi nunggu giliran. Sambil baca thread panjang soal {minat}.",
    "Habis hujan deras di {kota}. Suasana jadi lebih adem, enak buat mikir.",
    "Simpan dulu di draft, nanti dirapiin lagi sebelum dipost.",
    "Udah lama nggak keliling area ini. Lumayan buat refreshing.",
    "Sore yang santai di {kota}. Timeline ramai tapi tetap enjoy.",
    "Baru upload beberapa foto dari kegiatan tadi. Semoga bermanfaat.",
    "Nyoba tulis lebih panjang soal {minat}. Ternyata susah juga rangkumnya.",
    "Tadi sempet ngobrol panjang soal {minat} sama beberapa orang. Seru.",
    "Udah malam, tapi masih ada yang aktif di forum {minat}.",
    "Lagi compile catatan dari minggu kemarin. Banyak yang ketinggalan.",
    "Zona nyaman adalah diskusi {minat} sambil ngopi di sudut {kota}.",
    "Baru tau ada update besar soal {minat}. Perlu dikaji lebih dalam.",
    "Short trip ke area sekitar {kota}. Sedikit keluar dari rutinitas.",
    "Agak telat buka notif hari ini. Banyak yang missed soal {minat}.",
    "Reminder buat diri sendiri: istirahat itu penting. Tapi update dulu.",
    "Tadi rapat singkat, sekarang back to ngulik {minat}.",
    "Lagi di rest area. Perjalanan masih panjang, tapi koneksi bagus.",
    "Nggak banyak yang bisa diceritain, tapi hari ini cukup berasa.",
    "Timeline makin ramai soal {minat} minggu ini. Ada apa?",
    "Cuaca {kota} hari ini nggak menentu. Tapi urusan tetap jalan.",
    "Lagi evaluasi aktivitas bulan ini. Banyak yang bisa diperbaiki.",
    "Forum {minat} hari ini penuh diskusi menarik. Sayang nggak sempat semua.",
    "Slow day. Cocok buat baca-baca arsip soal {minat}.",
    "Habis cek kondisi lapangan. Laporan menyusul kalau sempat.",
    "Nggak tau kenapa tapi hari ini produktif banget. Semoga besok juga.",
    "Selesai urusan {kota}. Perjalanan pulang sambil dengerin podcast.",
    "Ada yang baru join komunitas {minat}? Salam kenal kalau ada.",
]

TEMPLATE_PENCARIAN = [
    "Menampilkan hasil profil terkait aktivitas komunitas lokal.",
    "Akun ini beberapa kali muncul dalam percakapan publik dan forum komunitas.",
    "Jejak akun memperlihatkan aktivitas lintas platform dengan intensitas menengah.",
    "Hasil pencarian menemukan kemiripan username dan lokasi kegiatan.",
    "Profil terkait terdeteksi pada beberapa forum diskusi dengan topik sejenis.",
    "Akun menunjukkan pola aktivitas yang konsisten di beberapa platform.",
    "Ditemukan referensi nama atau username serupa di kanal komunitas lokal.",
    "Jejak digital menunjukkan kehadiran di forum dan grup berbasis lokasi.",
    "Profil ini memiliki keterkaitan dengan beberapa akun lain di jaringan lokal.",
    "Aktivitas akun terdeteksi pada rentang waktu yang berdekatan di beberapa platform.",
    "Hasil menampilkan koneksi antara profil ini dan komunitas regional tertentu.",
    "Terdeteksi kesamaan pola posting dengan sejumlah profil di klaster yang sama.",
    "Username serupa ditemukan di beberapa layanan berbeda dengan konteks yang mirip.",
    "Akun terhubung dengan topik diskusi yang berulang di forum lokal.",
    "Data pencarian menunjukkan profil aktif dengan interaksi komunitas yang teratur.",
    "Profil ini pernah muncul dalam thread diskusi publik mengenai isu lokal.",
    "Jejak lokasi terdeteksi dari metadata posting dan check-in publik.",
    "Akun memiliki riwayat interaksi dengan profil-profil di jaringan regional.",
    "Pencarian menemukan referensi tidak langsung melalui mention dan reply.",
    "Profil menampilkan aktivitas yang konsisten pada jam-jam tertentu.",
    "Terdeteksi overlap antara jaringan pertemanan dan topik konten yang diposting.",
    "Data forum menunjukkan bahwa profil ini aktif di beberapa thread komunitas.",
    "Hasil agregasi menunjukkan profil ini memiliki jejak digital di beberapa platform.",
    "Akun terhubung secara tidak langsung dengan beberapa profil yang dimonitor.",
    "Pencarian menemukan histori aktivitas di platform yang saling tumpang tindih.",
    "Profil ini muncul dalam hasil crawling dengan tag lokasi yang relevan.",
    "Jejak digital konsisten dengan pola pengguna yang aktif di komunitas lokal.",
    "Terdeteksi kemiripan pola waktu aktivitas antara profil ini dan beberapa akun lain.",
    "Hasil menunjukkan akun pernah terlibat dalam diskusi kelompok di platform tertutup.",
    "Profil memiliki koneksi langsung dan tidak langsung di jaringan yang dipantau.",
]

# ============================================================
# KONFIGURASI UTAMA
# ============================================================

KLASTER_KOTA = [
    {"kota": "Bekasi", "provinsi": "Jawa Barat", "lat": -6.2349, "lon": 106.9896, "radius_km": 8.0},
    {"kota": "Karawang", "provinsi": "Jawa Barat", "lat": -6.3054, "lon": 107.2961, "radius_km": 9.0},
    {"kota": "Cikarang", "provinsi": "Jawa Barat", "lat": -6.2615, "lon": 107.1522, "radius_km": 7.5},
    {"kota": "Jakarta", "provinsi": "DKI Jakarta", "lat": -6.2088, "lon": 106.8456, "radius_km": 12.0},
    {"kota": "Depok", "provinsi": "Jawa Barat", "lat": -6.4025, "lon": 106.7942, "radius_km": 7.0},
    {"kota": "Bogor", "provinsi": "Jawa Barat", "lat": -6.5950, "lon": 106.8166, "radius_km": 8.5},
    {"kota": "Tangerang", "provinsi": "Banten", "lat": -6.1781, "lon": 106.6297, "radius_km": 8.0},
    {"kota": "Bandung", "provinsi": "Jawa Barat", "lat": -6.9175, "lon": 107.6191, "radius_km": 10.0},
    {"kota": "Cibinong", "provinsi": "Jawa Barat", "lat": -6.4818, "lon": 106.8561, "radius_km": 5.5},
    {"kota": "Cikampek", "provinsi": "Jawa Barat", "lat": -6.4116, "lon": 107.4607, "radius_km": 5.0},
]

BOBOT_KLASTER = [0.15, 0.12, 0.13, 0.18, 0.09, 0.09, 0.08, 0.07, 0.05, 0.04]

TIPE_TITIK_PERTEMUAN = [
    "coworking_space", "cafe", "rest_area", "warehouse_hub",
    "rental_house", "industrial_parking", "warung_kopi",
    "mushola_pinggir_jalan", "mini_market", "pos_ronda",
]

PLATFORM_SOSIAL = ["twitter", "instagram", "facebook", "tiktok", "telegram", "forum", "youtube", "whatsapp_channel"]

SET_BAHASA = [
    ["id", "en"], ["id"], ["id", "jv"], ["id", "su"], ["id", "en", "jv"],
    ["id", "btk"], ["id", "min"], ["id", "bug"],
]

GRUP_MINAT = [
    "otomotif", "fotografi", "kuliner", "logistik", "teknologi",
    "gaming", "komunitas_lokal", "musik", "olahraga", "politik",
    "aktivisme", "bisnis_online", "pertanian", "kesehatan", "pendidikan",
    "keuangan", "pariwisata", "fashion", "properti", "transportasi",
    "lingkungan", "hukum", "seni", "keagamaan", "hiburan",
]

PREFIKS_TELEPON = [
    "811", "812", "813", "821", "822", "823", "851", "852", "853",
    "855", "856", "857", "858", "877", "878", "881", "882", "895",
    "896", "897", "898", "899",
]

TUJUAN_PENDANAAN = [
    "iuran logistik", "dukungan operasional", "pengadaan alat komunikasi",
    "dana perjalanan", "paket konsumsi", "sewa tempat", "keperluan teknis",
    "pengadaan perlengkapan lapangan", "transportasi anggota", "dana darurat operasi",
]

# ============================================================
# KONFIGURASI KASUS
# ============================================================

KONFIGURASI_KASUS = {
    "kebakaran_gudang": {
        "id_kasus": "kasus-kebakaran-gudang",
        "judul": "Kebakaran Gudang Logistik - Indikasi Sabotase Terkoordinasi",
        "kota": "Bekasi",
        "provinsi": "Jawa Barat",
        "waktu_insiden": datetime(2026, 4, 11, 2, 30, tzinfo=ZONA_INDONESIA),
        "tipe_pertemuan": "warehouse_hub",
    },
    "pendanaan_mencurigakan": {
        "id_kasus": "kasus-pendanaan-mencurigakan",
        "judul": "Pola Pendanaan Tersebar - Indikasi Koordinasi Finansial",
        "kota": "Jakarta",
        "provinsi": "DKI Jakarta",
        "waktu_insiden": datetime(2026, 4, 7, 20, 0, tzinfo=ZONA_INDONESIA),
        "tipe_pertemuan": "coworking_space",
    },
    "propaganda": {
        "id_kasus": "kasus-propaganda-burst",
        "judul": "Amplifikasi Narasi Terkoordinasi - Indikasi Propaganda",
        "kota": "Cikarang",
        "provinsi": "Jawa Barat",
        "waktu_insiden": datetime(2026, 4, 12, 19, 15, tzinfo=ZONA_INDONESIA),
        "tipe_pertemuan": "cafe",
    },
}


# ============================================================
# DATACLASS BUNDLE
# ============================================================

@dataclass
class BundleData:
    profil: list
    akun: list
    kontak: list
    preferensi: list
    foto: list
    postingan: list
    pertemanan: list
    jaringan: list
    lokasi: list
    kasus: list
    transaksi: list
    peringatan_dana: list
    kampanye: list
    klaster_pesan: list
    crawling: list
    entitas: list
    peringatan: list
    skor_risiko: list
    laporan: list


# ============================================================
# UTILITAS
# ============================================================

def sekarang_iso() -> str:
    return datetime.now(ZONA_INDONESIA).replace(microsecond=0).isoformat()


def dt_ke_iso(nilai: datetime) -> str:
    return nilai.astimezone(ZONA_INDONESIA).replace(microsecond=0).isoformat()


def slugify(nilai: str) -> str:
    nilai = nilai.lower().strip()
    nilai = re.sub(r"[^a-z0-9]+", "-", nilai)
    return nilai.strip("-")


def id_acak(prefiks: str) -> str:
    return f"{prefiks}-{uuid.uuid4().hex[:10]}"


def dibulatkan(nilai: float) -> float:
    return round(nilai, 6)


def titik_acak(rng: random.Random, lat: float, lon: float, radius_km: float) -> tuple[float, float]:
    jarak = radius_km * math.sqrt(rng.random())
    arah = rng.random() * math.pi * 2
    offset_lat = (jarak / 111.0) * math.cos(arah)
    offset_lon = (jarak / (111.0 * math.cos(math.radians(lat)))) * math.sin(arah)
    return dibulatkan(lat + offset_lat), dibulatkan(lon + offset_lon)


def waktu_acak_antara(rng: random.Random, mulai: datetime, akhir: datetime) -> datetime:
    total = int((akhir - mulai).total_seconds())
    if total <= 0:
        return mulai
    return mulai + timedelta(seconds=rng.randint(0, total))


def pastikan_direktori(dir_output: Path) -> None:
    dir_output.mkdir(parents=True, exist_ok=True)
    (dir_output / "gambar").mkdir(parents=True, exist_ok=True)


def simpan_json(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def muat_json(path: Path, default):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def buat_nomor_telepon(rng: random.Random) -> tuple[str, str]:
    prefiks = rng.choice(PREFIKS_TELEPON)
    panjang = 8 if rng.random() < 0.7 else 9
    pelanggan = "".join(rng.choices(string.digits, k=panjang))
    lokal = f"0{prefiks}{pelanggan}"
    e164 = f"+62{lokal[1:]}"
    return lokal, e164


def buat_email(rng: random.Random, nama_lengkap: str) -> str:
    domain = ["example.com", "mail.test", "demo.id"]
    token = [t for t in re.split(r"[^a-zA-Z0-9]+", nama_lengkap.lower()) if t]
    dasar = "".join(token[:2])[:16] or "pengguna"
    akhiran = rng.randint(100, 9999)
    return f"{dasar}{akhiran}@{rng.choice(domain)}"


def buat_username(rng: random.Random, nama_lengkap: str) -> str:
    token = [t for t in re.split(r"[^a-zA-Z0-9]+", nama_lengkap.lower()) if t]
    dasar = "".join(token[:2])[:14] or "user"
    if rng.random() < 0.4:
        dasar = f"{token[0]}_{token[-1]}"[:18]
    akhiran = str(rng.randint(10, 9999)) if rng.random() < 0.65 else ""
    return f"{dasar}{akhiran}"


def url_avatar(id_profil: str) -> str:
    return f"{ENDPOINT_AVATAR}?seed={id_profil}"


def unduh_avatar(url: str, path_lokal: Path) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = resp.read()
        with open(path_lokal, "wb") as f:
            f.write(data)
        return True
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


def pilih_template_bio(rng: random.Random, minat: str, kota: str) -> str:
    template = rng.choice(TEMPLATE_BIO)
    return template.format(minat=minat, kota=kota)


def pilih_template_posting(rng: random.Random, minat: str, kota: str, tagline: str) -> str:
    template = rng.choice(TEMPLATE_POSTING)
    return template.format(minat=minat, kota=kota, tagline=tagline)


# ============================================================
# KELAS GENERATOR UTAMA
# ============================================================

class GeneratorDataSintetis:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)
        self.gen_nama = GeneratorNamaIndonesia(self.rng)

    def bangun_bundle_profil(self, jumlah: int, dir_output: str, dengan_gambar: bool = False) -> BundleData:
        path_output = Path(dir_output)
        pastikan_direktori(path_output)

        daftar_profil = []
        daftar_akun = []
        daftar_kontak = []
        daftar_preferensi = []
        daftar_foto = []
        daftar_postingan = []
        daftar_pertemanan = []
        daftar_jaringan = []
        daftar_lokasi = []

        titik_pertemuan = self._bangun_titik_pertemuan()
        keanggotaan_klaster = self._tetapkan_klaster_sosial(jumlah)
        klaster_per_profil = {idx: [] for idx in range(jumlah)}
        for klaster in keanggotaan_klaster["klaster"]:
            for idx in klaster["indeks_anggota"]:
                klaster_per_profil[idx].append(klaster["id_klaster"])
        for jembatan in keanggotaan_klaster["jembatan"]:
            klaster_per_profil[jembatan["indeks"]].extend(jembatan["id_klaster"])

        akun_per_profil: dict[str, list] = {}
        foto_per_profil: dict[str, list] = {}
        posting_per_profil: dict[str, list] = {}

        sekarang = datetime.now(ZONA_INDONESIA)

        for idx in range(jumlah):
            klaster = self.rng.choices(KLASTER_KOTA, weights=BOBOT_KLASTER, k=1)[0]
            lat, lon = titik_acak(self.rng, klaster["lat"], klaster["lon"], klaster["radius_km"])
            jenis_kelamin = self.rng.choice(["male", "female"])
            nama_lengkap = self.gen_nama.nama_pria() if jenis_kelamin == "male" else self.gen_nama.nama_wanita()
            tahun_lahir_mulai = self.rng.randint(1982, 2003)
            rentang_lahir = f"{tahun_lahir_mulai}-{tahun_lahir_mulai + self.rng.randint(0, 2)}"
            minat_profil = self.rng.sample(GRUP_MINAT, k=self.rng.randint(2, 5))

            nama_tampil = self._buat_nama_tampil(nama_lengkap)
            bio = pilih_template_bio(self.rng, self.rng.choice(minat_profil), klaster["kota"])

            id_profil = id_acak("prof")
            telepon_lokal, telepon_e164 = buat_nomor_telepon(self.rng)
            email = buat_email(self.rng, nama_lengkap)
            url_ava = url_avatar(id_profil)
            avatar_lokal = None

            if dengan_gambar:
                path_lokal = path_output / "gambar" / f"{id_profil}.jpg"
                if unduh_avatar(url_ava, path_lokal):
                    avatar_lokal = f"gambar/{id_profil}.jpg"

            dibuat_pada = sekarang - timedelta(days=self.rng.randint(150, 1800))

            profil = {
                "id_profil": id_profil,
                "nama_lengkap": nama_lengkap,
                "nama_tampil": nama_tampil,
                "jenis_kelamin": jenis_kelamin,
                "rentang_tahun_lahir": rentang_lahir,
                "bio": bio,
                "url_avatar": url_ava,
                "avatar_lokal": avatar_lokal,
                "sumber_avatar": SUMBER_AVATAR,
                "kode_negara": "ID",
                "kota": klaster["kota"],
                "provinsi": klaster["provinsi"],
                "latitude": lat,
                "longitude": lon,
                "bahasa": self.rng.choice(SET_BAHASA),
                "dibuat_pada": dt_ke_iso(dibuat_pada),
                "digenerate_pada": sekarang_iso(),
                "id_klaster": sorted(set(klaster_per_profil[idx])),
                "tag_risiko": [],
                "tautan_kasus": [],
            }
            daftar_profil.append(profil)

            kontak = {
                "id_kontak": id_acak("ktk"),
                "id_profil": id_profil,
                "email": email,
                "telepon_lokal": telepon_lokal,
                "telepon_e164": telepon_e164,
                "kota": klaster["kota"],
                "provinsi": klaster["provinsi"],
                "adalah_utama": True,
            }
            daftar_kontak.append(kontak)

            entri_preferensi = {
                "id_preferensi": id_acak("pref"),
                "id_profil": id_profil,
                "minat": minat_profil,
                "jendela_aktivitas": self.rng.choice(["pagi", "siang", "malam", "campuran"]),
                "penggunaan_perangkat": self.rng.choice(["android", "android+desktop", "ios", "android+tablet"]),
                "tingkat_mobilitas": self.rng.choice(["rendah", "menengah", "tinggi"]),
            }
            daftar_preferensi.append(entri_preferensi)

            lokasi_profil = self._bangun_lokasi_profil(profil, klaster, titik_pertemuan)
            daftar_lokasi.extend(lokasi_profil)

            akun_profil = self._bangun_akun(profil, minat_profil)
            daftar_akun.extend(akun_profil)
            akun_per_profil[id_profil] = akun_profil

            foto_profil = self._bangun_foto(profil, klaster)
            daftar_foto.extend(foto_profil)
            foto_per_profil[id_profil] = foto_profil

            if idx % 500 == 0 and idx > 0:
                print(f"  [PROGRES] {idx}/{jumlah} profil dibuat...")

        print(f"  [SELESAI] {jumlah} profil dibuat. Membangun graf sosial...")
        daftar_pertemanan, daftar_jaringan = self._bangun_graf_sosial(daftar_profil, keanggotaan_klaster)

        print(f"  [PROGRES] Membangun postingan dasar...")
        daftar_postingan = self._bangun_postingan_dasar(daftar_profil, akun_per_profil, daftar_preferensi)

        for posting in daftar_postingan:
            posting_per_profil.setdefault(posting["id_profil"], []).append(posting)

        print(f"  [PROGRES] Membangun profil terekstrak...")
        for profil in daftar_profil:
            pid = profil["id_profil"]
            kontak_profil = next(k for k in daftar_kontak if k["id_profil"] == pid)
            pref_profil = next(p for p in daftar_preferensi if p["id_profil"] == pid)
            profil["profil_terekstrak"] = self._bangun_profil_terekstrak(
                profil=profil,
                kontak=kontak_profil,
                preferensi=pref_profil,
                akun=akun_per_profil.get(pid, []),
                pertemanan=daftar_pertemanan,
                foto=foto_per_profil.get(pid, []),
                postingan=posting_per_profil.get(pid, []),
                lokasi=daftar_lokasi,
            )

        return BundleData(
            profil=daftar_profil,
            akun=daftar_akun,
            kontak=daftar_kontak,
            preferensi=daftar_preferensi,
            foto=daftar_foto,
            postingan=daftar_postingan,
            pertemanan=daftar_pertemanan,
            jaringan=daftar_jaringan,
            lokasi=daftar_lokasi,
            kasus=[],
            transaksi=[],
            peringatan_dana=[],
            kampanye=[],
            klaster_pesan=[],
            crawling=[],
            entitas=[],
            peringatan=[],
            skor_risiko=[],
            laporan=[],
        )

    def augmentasi_bundle_dengan_kasus(self, bundle: BundleData, nama_kasus: list[str] | None = None) -> BundleData:
        diminta = nama_kasus or list(KONFIGURASI_KASUS.keys())
        diminta = [nama for nama in diminta if nama in KONFIGURASI_KASUS]
        if not diminta:
            return bundle

        self._reset_output_kasus(bundle)

        profil_per_id = {profil["id_profil"]: profil for profil in bundle.profil}
        akun_per_profil: dict[str, list] = {}
        for akun in bundle.akun:
            akun_per_profil.setdefault(akun["id_profil"], []).append(akun)

        klaster_sosial = self._kelompokkan_profil_per_klaster(bundle.profil)
        pool_aktor_kasus = self._pilih_aktor_kasus(bundle.profil, klaster_sosial)
        titik_pertemuan = self._bangun_titik_pertemuan()

        for nama_kasus in diminta:
            config_kasus = KONFIGURASI_KASUS[nama_kasus]
            print(f"  [KASUS] Membangun kasus: {nama_kasus}...")

            if nama_kasus == "kebakaran_gudang":
                hasil = self._bangun_kasus_kebakaran_gudang(
                    bundle=bundle,
                    config_kasus=config_kasus,
                    akun_per_profil=akun_per_profil,
                    pool_aktor=pool_aktor_kasus,
                    titik_pertemuan=titik_pertemuan,
                )
            elif nama_kasus == "pendanaan_mencurigakan":
                hasil = self._bangun_kasus_pendanaan(
                    config_kasus=config_kasus,
                    akun_per_profil=akun_per_profil,
                    pool_aktor=pool_aktor_kasus,
                    titik_pertemuan=titik_pertemuan,
                )
            else:
                hasil = self._bangun_kasus_propaganda(
                    config_kasus=config_kasus,
                    akun_per_profil=akun_per_profil,
                    pool_aktor=pool_aktor_kasus,
                    titik_pertemuan=titik_pertemuan,
                )

            bundle.kasus.append(hasil["kasus"])
            bundle.postingan.extend(hasil["postingan"])
            bundle.lokasi.extend(hasil["lokasi"])
            bundle.jaringan.extend(hasil["jaringan"])
            bundle.crawling.extend(hasil["crawling"])
            bundle.entitas.extend(hasil["entitas"])
            bundle.peringatan.extend(hasil["peringatan"])
            bundle.skor_risiko.append(hasil["skor_risiko"])
            bundle.laporan.append(hasil["laporan"])
            bundle.transaksi.extend(hasil.get("transaksi", []))
            bundle.peringatan_dana.extend(hasil.get("peringatan_dana", []))
            bundle.kampanye.extend(hasil.get("kampanye", []))
            bundle.klaster_pesan.extend(hasil.get("klaster_pesan", []))

            for tautan in hasil["tautan_kasus"]:
                profil = profil_per_id[tautan["id_profil"]]
                profil["tautan_kasus"].append(tautan)
                if tautan["sinyal"] not in profil["tag_risiko"]:
                    profil["tag_risiko"].append(tautan["sinyal"])

        self._perbarui_ekstraksi_profil(bundle)
        return bundle

    def tulis_bundle(self, bundle: BundleData, dir_output: str) -> None:
        path_output = Path(dir_output)
        pastikan_direktori(path_output)
        peta_file = {
            "profil.json": bundle.profil,
            "akun.json": bundle.akun,
            "kontak.json": bundle.kontak,
            "preferensi.json": bundle.preferensi,
            "foto.json": bundle.foto,
            "postingan.json": bundle.postingan,
            "pertemanan.json": bundle.pertemanan,
            "jaringan.json": bundle.jaringan,
            "lokasi.json": bundle.lokasi,
            "kasus.json": bundle.kasus,
            "transaksi.json": bundle.transaksi,
            "peringatan_dana.json": bundle.peringatan_dana,
            "kampanye.json": bundle.kampanye,
            "klaster_pesan.json": bundle.klaster_pesan,
            "crawling.json": bundle.crawling,
            "entitas.json": bundle.entitas,
            "peringatan.json": bundle.peringatan,
            "skor_risiko.json": bundle.skor_risiko,
            "laporan.json": bundle.laporan,
        }
        for nama_file, data in peta_file.items():
            simpan_json(path_output / nama_file, data)
            print(f"  [SIMPAN] {nama_file} — {len(data) if isinstance(data, list) else 1} entri")

    def muat_bundle(self, dir_output: str) -> BundleData:
        path_output = Path(dir_output)
        return BundleData(
            profil=muat_json(path_output / "profil.json", []),
            akun=muat_json(path_output / "akun.json", []),
            kontak=muat_json(path_output / "kontak.json", []),
            preferensi=muat_json(path_output / "preferensi.json", []),
            foto=muat_json(path_output / "foto.json", []),
            postingan=muat_json(path_output / "postingan.json", []),
            pertemanan=muat_json(path_output / "pertemanan.json", []),
            jaringan=muat_json(path_output / "jaringan.json", []),
            lokasi=muat_json(path_output / "lokasi.json", []),
            kasus=muat_json(path_output / "kasus.json", []),
            transaksi=muat_json(path_output / "transaksi.json", []),
            peringatan_dana=muat_json(path_output / "peringatan_dana.json", []),
            kampanye=muat_json(path_output / "kampanye.json", []),
            klaster_pesan=muat_json(path_output / "klaster_pesan.json", []),
            crawling=muat_json(path_output / "crawling.json", []),
            entitas=muat_json(path_output / "entitas.json", []),
            peringatan=muat_json(path_output / "peringatan.json", []),
            skor_risiko=muat_json(path_output / "skor_risiko.json", []),
            laporan=muat_json(path_output / "laporan.json", []),
        )

    # ============================================================
    # METODE PRIVAT — BUILDER
    # ============================================================

    def _buat_nama_tampil(self, nama_lengkap: str) -> str:
        token = nama_lengkap.split()
        if self.rng.random() < 0.5:
            return token[0]
        elif self.rng.random() < 0.3:
            return " ".join(token[:2])
        return nama_lengkap

    def _bangun_titik_pertemuan(self) -> list[dict]:
        titik = []
        for klaster in KLASTER_KOTA:
            for tipe in TIPE_TITIK_PERTEMUAN:
                lat, lon = titik_acak(self.rng, klaster["lat"], klaster["lon"], min(klaster["radius_km"], 3.0))
                id_titik = f"pertemuan-{slugify(klaster['kota'])}-{tipe}"
                titik.append({
                    "id_titik_pertemuan": id_titik,
                    "kota": klaster["kota"],
                    "provinsi": klaster["provinsi"],
                    "tipe": tipe,
                    "label": f"{klaster['kota']} {tipe.replace('_', ' ')}",
                    "latitude": lat,
                    "longitude": lon,
                })
        return titik

    def _tetapkan_klaster_sosial(self, jumlah: int) -> dict:
        indeks = list(range(jumlah))
        self.rng.shuffle(indeks)
        jumlah_klaster = 3 if jumlah < 150 else (5 if jumlah < 500 else 8)
        kursor = 0
        klaster = []
        for i_klaster in range(jumlah_klaster):
            ukuran = min(max(6, jumlah // 20), 15)
            if kursor + ukuran > len(indeks):
                ukuran = max(4, len(indeks) - kursor)
            if ukuran <= 0:
                break
            anggota = indeks[kursor : kursor + ukuran]
            kursor += ukuran
            klaster.append({"id_klaster": f"klaster-{i_klaster + 1}", "indeks_anggota": anggota})
        jembatan = []
        if len(klaster) >= 2 and kursor < len(indeks):
            jumlah_jembatan = min(3, len(indeks) - kursor)
            for i_jembatan in range(jumlah_jembatan):
                indeks_j = indeks[kursor + i_jembatan]
                terhubung = self.rng.sample([k["id_klaster"] for k in klaster], k=2)
                jembatan.append({"indeks": indeks_j, "id_klaster": terhubung})
        return {"klaster": klaster, "jembatan": jembatan}

    def _bangun_lokasi_profil(self, profil: dict, klaster: dict, titik_pertemuan: list[dict]) -> list[dict]:
        entri = [{
            "id_lokasi": id_acak("lok"),
            "id_profil": profil["id_profil"],
            "tipe_lokasi": "basis_rumah",
            "label": f"Area tinggal {klaster['kota']}",
            "kota": klaster["kota"],
            "provinsi": klaster["provinsi"],
            "latitude": profil["latitude"],
            "longitude": profil["longitude"],
            "diamati_pada": profil["dibuat_pada"],
            "kepercayaan": 0.88,
        }]
        titik_cocok = [t for t in titik_pertemuan if t["kota"] == klaster["kota"]]
        self.rng.shuffle(titik_cocok)
        for titik in titik_cocok[: self.rng.randint(1, 3)]:
            entri.append({
                "id_lokasi": id_acak("lok"),
                "id_profil": profil["id_profil"],
                "tipe_lokasi": "spot_sering",
                "id_titik_pertemuan": titik["id_titik_pertemuan"],
                "label": titik["label"],
                "kota": titik["kota"],
                "provinsi": titik["provinsi"],
                "latitude": titik["latitude"],
                "longitude": titik["longitude"],
                "diamati_pada": profil["digenerate_pada"],
                "kepercayaan": round(self.rng.uniform(0.55, 0.83), 2),
            })
        return entri

    def _bangun_akun(self, profil: dict, minat: list[str]) -> list[dict]:
        sekarang = datetime.now(ZONA_INDONESIA)
        jumlah_akun = self.rng.randint(2, 5)
        platform_dipilih = self.rng.sample(PLATFORM_SOSIAL, k=min(jumlah_akun, len(PLATFORM_SOSIAL)))
        akun = []
        for platform in platform_dipilih:
            username = buat_username(self.rng, profil["nama_lengkap"])
            dibuat = sekarang - timedelta(days=self.rng.randint(7, 1800))
            akun.append({
                "id_akun": id_acak("akun"),
                "id_profil": profil["id_profil"],
                "platform": platform,
                "username": username,
                "url_profil": f"https://social.local/{platform}/{username}",
                "dibuat_pada": dt_ke_iso(dibuat),
                "jumlah_pengikut": self.rng.randint(20, 12000),
                "jumlah_mengikuti": self.rng.randint(15, 3000),
                "jumlah_posting": self.rng.randint(5, 600),
                "status_terverifikasi": self.rng.random() < 0.03,
                "terakhir_aktif_pada": dt_ke_iso(sekarang - timedelta(hours=self.rng.randint(1, 360))),
                "petunjuk_minat": self.rng.choice(minat),
            })
        return akun

    def _bangun_foto(self, profil: dict, klaster: dict) -> list[dict]:
        foto = []
        for _ in range(self.rng.randint(1, 5)):
            lat, lon = titik_acak(self.rng, profil["latitude"], profil["longitude"], 2.0)
            foto.append({
                "id_foto": id_acak("foto"),
                "id_profil": profil["id_profil"],
                "keterangan": self.rng.choice([
                    f"Sudut lain dari {klaster['kota']}.",
                    "Dokumentasi kegiatan harian.",
                    "Lagi keliling sebentar sambil cek suasana.",
                    "Arsip foto kegiatan.",
                    f"Momen sore di sekitar {klaster['kota']}.",
                    "Kegiatan komunitas kemarin.",
                    "Ngumpul bareng teman-teman.",
                    "Spot baru yang baru ditemukan.",
                ]),
                "diambil_pada": dt_ke_iso(datetime.now(ZONA_INDONESIA) - timedelta(days=self.rng.randint(1, 800))),
                "kota": klaster["kota"],
                "provinsi": klaster["provinsi"],
                "latitude": lat,
                "longitude": lon,
                "tipe_konten": self.rng.choice(["jalanan", "selfie", "kelompok", "makanan", "acara", "panorama"]),
            })
        return foto

    def _bangun_graf_sosial(self, profil: list[dict], keanggotaan_klaster: dict) -> tuple[list, list]:
        pertemanan = []
        jaringan = []
        profil_per_indeks = {idx: profil for idx, profil in enumerate(profil)}
        pasangan_ada = set()

        for klaster in keanggotaan_klaster["klaster"]:
            anggota = [profil_per_indeks[idx] for idx in klaster["indeks_anggota"]]
            for i, kiri in enumerate(anggota):
                for kanan in anggota[i + 1:]:
                    if self.rng.random() > 0.45:
                        continue
                    pasangan = tuple(sorted((kiri["id_profil"], kanan["id_profil"])))
                    if pasangan in pasangan_ada:
                        continue
                    pasangan_ada.add(pasangan)
                    sejak = dt_ke_iso(datetime.now(ZONA_INDONESIA) - timedelta(days=self.rng.randint(90, 1500)))
                    pertemanan.append({
                        "id_pertemanan": id_acak("pert"),
                        "profil_a": pasangan[0],
                        "profil_b": pasangan[1],
                        "kekuatan": round(self.rng.uniform(0.52, 0.94), 2),
                        "id_klaster": klaster["id_klaster"],
                        "sejak": sejak,
                    })
                    jaringan.append({
                        "id_edge": id_acak("edge"),
                        "id_profil_sumber": pasangan[0],
                        "id_profil_tujuan": pasangan[1],
                        "tipe_edge": "koneksi_sosial",
                        "bobot": round(self.rng.uniform(0.5, 0.95), 2),
                        "id_klaster": klaster["id_klaster"],
                    })

        for jembatan in keanggotaan_klaster["jembatan"]:
            profil_jembatan = profil_per_indeks[jembatan["indeks"]]
            for id_klaster in jembatan["id_klaster"]:
                klaster = next(k for k in keanggotaan_klaster["klaster"] if k["id_klaster"] == id_klaster)
                anggota = [profil_per_indeks[idx] for idx in klaster["indeks_anggota"]]
                for target in self.rng.sample(anggota, k=min(5, len(anggota))):
                    pasangan = tuple(sorted((profil_jembatan["id_profil"], target["id_profil"])))
                    if pasangan in pasangan_ada:
                        continue
                    pasangan_ada.add(pasangan)
                    pertemanan.append({
                        "id_pertemanan": id_acak("pert"),
                        "profil_a": pasangan[0],
                        "profil_b": pasangan[1],
                        "kekuatan": round(self.rng.uniform(0.61, 0.97), 2),
                        "id_klaster": id_klaster,
                        "sejak": dt_ke_iso(datetime.now(ZONA_INDONESIA) - timedelta(days=self.rng.randint(60, 900))),
                        "adalah_jembatan": True,
                    })
                    jaringan.append({
                        "id_edge": id_acak("edge"),
                        "id_profil_sumber": profil_jembatan["id_profil"],
                        "id_profil_tujuan": target["id_profil"],
                        "tipe_edge": "koneksi_jembatan",
                        "bobot": round(self.rng.uniform(0.62, 0.98), 2),
                        "id_klaster": id_klaster,
                    })

        profil_non_klaster = [p for p in profil if not p["id_klaster"]]
        for _ in range(max(3, len(profil) // 30)):
            if len(profil_non_klaster) < 2:
                break
            kiri, kanan = self.rng.sample(profil_non_klaster, 2)
            if kiri["kota"] != kanan["kota"] and self.rng.random() < 0.7:
                continue
            pasangan = tuple(sorted((kiri["id_profil"], kanan["id_profil"])))
            if pasangan in pasangan_ada:
                continue
            pasangan_ada.add(pasangan)
            pertemanan.append({
                "id_pertemanan": id_acak("pert"),
                "profil_a": pasangan[0],
                "profil_b": pasangan[1],
                "kekuatan": round(self.rng.uniform(0.22, 0.55), 2),
                "id_klaster": None,
                "sejak": dt_ke_iso(datetime.now(ZONA_INDONESIA) - timedelta(days=self.rng.randint(30, 600))),
            })
            jaringan.append({
                "id_edge": id_acak("edge"),
                "id_profil_sumber": pasangan[0],
                "id_profil_tujuan": pasangan[1],
                "tipe_edge": "koneksi_ringan",
                "bobot": round(self.rng.uniform(0.2, 0.45), 2),
            })

        return pertemanan, jaringan

    def _bangun_postingan_dasar(
        self,
        profil: list[dict],
        akun_per_profil: dict[str, list],
        preferensi: list[dict],
    ) -> list[dict]:
        pref_map = {item["id_profil"]: item for item in preferensi}
        postingan = []
        sekarang = datetime.now(ZONA_INDONESIA)
        daftar_tagline = [
            "#catatan", "#harian", "#komunitas", "#update", "#lokal",
            "#berbagi", "#santai", "#ngobrol", "#info", "#share",
        ]
        for profil_item in profil:
            akun = akun_per_profil.get(profil_item["id_profil"], [])
            if not akun:
                continue
            pref = pref_map[profil_item["id_profil"]]
            jumlah = self.rng.randint(6, 18)
            for _ in range(jumlah):
                akun_dipilih = self.rng.choice(akun)
                dibuat = waktu_acak_antara(self.rng, sekarang - timedelta(days=365), sekarang - timedelta(hours=4))
                minat = self.rng.choice(pref["minat"])
                konten = pilih_template_posting(
                    self.rng,
                    minat,
                    profil_item["kota"],
                    self.rng.choice(daftar_tagline),
                )
                postingan.append({
                    "id_posting": id_acak("post"),
                    "id_profil": profil_item["id_profil"],
                    "id_akun": akun_dipilih["id_akun"],
                    "platform": akun_dipilih["platform"],
                    "konten": konten,
                    "timestamp": dt_ke_iso(dibuat),
                    "kota": profil_item["kota"],
                    "provinsi": profil_item["provinsi"],
                    "latitude": profil_item["latitude"],
                    "longitude": profil_item["longitude"],
                    "tipe_konten": self.rng.choice(["teks", "gambar", "komentar", "repost", "video_pendek"]),
                    "engagement": {
                        "suka": self.rng.randint(0, 350),
                        "komentar": self.rng.randint(0, 100),
                        "bagikan": self.rng.randint(0, 60),
                    },
                    "hashtag": self.rng.sample(
                        ["#lokal", "#malam", "#jalan", "#update", "#komunitas", "#fokus", "#santai", "#info"],
                        k=self.rng.randint(1, 4),
                    ),
                    "kata_kunci": self.rng.sample(pref["minat"], k=min(2, len(pref["minat"]))),
                    "referensi_mention": [],
                    "balas_ke_id_posting": None,
                    "repost_dari_id_posting": None,
                    "tipe_sumber": "organik",
                    "referensi_skenario": [],
                })
        return postingan

    def _bangun_profil_terekstrak(
        self,
        profil: dict,
        kontak: dict,
        preferensi: dict,
        akun: list[dict],
        pertemanan: list[dict],
        foto: list[dict],
        postingan: list[dict],
        lokasi: list[dict],
    ) -> dict:
        lokasi_terkait = [item for item in lokasi if item["id_profil"] == profil["id_profil"]][:5]
        pertemanan_terkait = [
            item for item in pertemanan
            if profil["id_profil"] in (item["profil_a"], item["profil_b"])
        ][:10]
        hasil_pencarian = []
        for idx in range(self.rng.randint(2, 5)):
            hasil_pencarian.append({
                "peringkat": idx + 1,
                "sumber": self.rng.choice(["pencarian", "forum", "sosial_media"]),
                "judul": f"Hasil untuk {profil['nama_tampil']}",
                "cuplikan": self.rng.choice(TEMPLATE_PENCARIAN),
            })
        return {
            "informasi_pribadi": {
                "nama_lengkap": profil["nama_lengkap"],
                "nama_tampil": profil["nama_tampil"],
                "jenis_kelamin": profil["jenis_kelamin"],
                "rentang_tahun_lahir": profil["rentang_tahun_lahir"],
                "kode_negara": profil["kode_negara"],
            },
            "lokasi": lokasi_terkait,
            "akun": [
                {
                    "platform": a["platform"],
                    "username": a["username"],
                    "dibuat_pada": a["dibuat_pada"],
                    "terakhir_aktif_pada": a["terakhir_aktif_pada"],
                }
                for a in akun
            ],
            "statistik": {
                "jumlah_akun": len(akun),
                "jumlah_teman": len(pertemanan_terkait),
                "jumlah_foto": len(foto),
                "jumlah_posting": len(postingan),
            },
            "pertemanan": pertemanan_terkait,
            "foto": foto[:8],
            "postingan": postingan[:12],
            "hasil_pencarian_web": hasil_pencarian,
            "preferensi": preferensi,
            "info_kontak": kontak,
            "sinopsis": (
                f"{profil['nama_tampil']} berbasis di {profil['kota']} "
                f"dengan minat utama {', '.join(preferensi['minat'][:2])}."
            ),
            "tautan_kasus": profil.get("tautan_kasus", []),
        }

    # ============================================================
    # METODE PRIVAT — KASUS
    # ============================================================

    def _kelompokkan_profil_per_klaster(self, profil: list[dict]) -> dict[str, list[str]]:
        dikelompokkan: dict[str, list[str]] = {}
        for p in profil:
            for id_klaster in p["id_klaster"]:
                dikelompokkan.setdefault(id_klaster, []).append(p["id_profil"])
        return dikelompokkan

    def _pilih_aktor_kasus(self, profil: list[dict], klaster_sosial: dict[str, list[str]]) -> dict[str, list[str]]:
        semua_id = [p["id_profil"] for p in profil]
        id_klaster = sorted(klaster_sosial)
        pool = {
            "overlap": self.rng.sample(semua_id, k=min(8, len(semua_id))),
            "terisolasi_noise": [p["id_profil"] for p in profil if not p["id_klaster"]][: max(10, len(profil) // 12)],
        }
        for i, nama_pool in enumerate(["klaster_a", "klaster_b", "klaster_c"]):
            if i < len(id_klaster):
                pool[nama_pool] = klaster_sosial[id_klaster[i]][:]
            else:
                pool[nama_pool] = self.rng.sample(semua_id, k=min(10, len(semua_id)))
        return pool

    def _pilih_titik_pertemuan(self, titik_pertemuan: list[dict], kota: str, tipe: str) -> dict:
        cocok = [t for t in titik_pertemuan if t["kota"] == kota and t["tipe"] == tipe]
        if not cocok:
            cocok = [t for t in titik_pertemuan if t["kota"] == kota]
        return self.rng.choice(cocok)

    def _tambah_checkin_kasus(
        self,
        id_profil: list[str],
        titik_pertemuan: dict,
        waktu_insiden: datetime,
        id_kasus: str,
    ) -> tuple[list, list]:
        entri_lokasi = []
        entri_jaringan = []
        for pid in id_profil:
            diamati = waktu_insiden - timedelta(hours=self.rng.randint(4, 60), minutes=self.rng.randint(0, 55))
            entri_lokasi.append({
                "id_lokasi": id_acak("lok"),
                "id_profil": pid,
                "tipe_lokasi": "checkin_kasus",
                "id_titik_pertemuan": titik_pertemuan["id_titik_pertemuan"],
                "label": titik_pertemuan["label"],
                "kota": titik_pertemuan["kota"],
                "provinsi": titik_pertemuan["provinsi"],
                "latitude": titik_pertemuan["latitude"],
                "longitude": titik_pertemuan["longitude"],
                "diamati_pada": dt_ke_iso(diamati),
                "kepercayaan": round(self.rng.uniform(0.64, 0.94), 2),
                "id_kasus": id_kasus,
            })
        for i, kiri in enumerate(id_profil):
            for kanan in id_profil[i + 1:]:
                if self.rng.random() > 0.35:
                    continue
                entri_jaringan.append({
                    "id_edge": id_acak("edge"),
                    "id_profil_sumber": kiri,
                    "id_profil_tujuan": kanan,
                    "tipe_edge": "titik_pertemuan_bersama",
                    "bobot": round(self.rng.uniform(0.55, 0.9), 2),
                    "id_titik_pertemuan": titik_pertemuan["id_titik_pertemuan"],
                    "id_kasus": id_kasus,
                })
        return entri_lokasi, entri_jaringan

    def _bangun_kasus_kebakaran_gudang(
        self, bundle: BundleData, config_kasus: dict,
        akun_per_profil: dict, pool_aktor: dict, titik_pertemuan: list[dict]
    ) -> dict:
        id_kasus = config_kasus["id_kasus"]
        waktu_insiden = config_kasus["waktu_insiden"]
        anggota_klaster = pool_aktor["klaster_a"][:]
        kandidat_jembatan = [p["id_profil"] for p in bundle.profil if len(p["id_klaster"]) > 1]
        self.rng.shuffle(anggota_klaster)
        aktor = list(dict.fromkeys(anggota_klaster[:10] + kandidat_jembatan[:3] + pool_aktor["overlap"][:3]))
        titik = self._pilih_titik_pertemuan(titik_pertemuan, config_kasus["kota"], config_kasus["tipe_pertemuan"])

        konten_posting_kasus = [
            ("pra", "Akan ada kejutan besar di kawasan industri itu. #pengingat", -2 * 24 * 60),
            ("pra", "Situasi logistik area industri berubah cepat malam ini.", -36 * 60),
            ("saat", "Baru aja denger ledakan sebelum api gede naik. #bekasi #malam", 10),
            ("saat", "Ini bukan kebakaran biasa, tadi ada bunyi keras duluan.", 18),
            ("saat", "Asap hitamnya tebal banget, kayak ada bahan lain ikut kebakar.", 25),
            ("saat", "Orang-orang panik, jalur keluar udah macet semua.", 40),
            ("pasca", "Info awal katanya korsleting, tapi saksi pada beda cerita.", 60),
            ("pasca", "Motor sempat keluar dari area sebelum api membesar.", 90),
            ("pasca", "Timeline rame, banyak yang bilang ada bau bahan kimia.", 120),
            ("pasca", "Beberapa saksi menyebut hal yang sama soal ledakan awal.", 150),
            ("pasca", "Petugas masih olah TKP, belum ada keterangan resmi.", 200),
            ("pasca", "Gudang berisi bahan-bahan yang belum jelas statusnya.", 240),
        ]

        postingan = []
        for idx, (tipe_posting, konten, delta_menit) in enumerate(konten_posting_kasus[:len(aktor)]):
            if idx >= len(aktor):
                break
            pid = aktor[idx]
            akun = self.rng.choice(akun_per_profil[pid])
            timestamp = waktu_insiden + timedelta(minutes=delta_menit)
            postingan.append({
                "id_posting": id_acak("post"),
                "id_profil": pid,
                "id_akun": akun["id_akun"],
                "platform": akun["platform"],
                "konten": konten,
                "timestamp": dt_ke_iso(timestamp),
                "kota": config_kasus["kota"],
                "provinsi": config_kasus["provinsi"],
                "latitude": titik["latitude"],
                "longitude": titik["longitude"],
                "tipe_konten": self.rng.choice(["teks", "gambar", "video", "komentar"]),
                "engagement": {
                    "suka": self.rng.randint(4, 600),
                    "komentar": self.rng.randint(0, 180),
                    "bagikan": self.rng.randint(0, 150),
                },
                "hashtag": ["#gudang", "#kebakaran", "#industri", "#bekasi"],
                "kata_kunci": ["ledakan", "bau_kimia", "motor_mencurigakan"],
                "referensi_mention": [],
                "balas_ke_id_posting": None,
                "repost_dari_id_posting": None,
                "tipe_sumber": "sinyal_kasus",
                "referensi_skenario": [id_kasus],
            })

        lokasi, jaringan_pertemuan = self._tambah_checkin_kasus(aktor[:9], titik, waktu_insiden, id_kasus)
        entitas = [
            {"id_kasus": id_kasus, "tipe_entitas": "lokasi", "nilai": "kawasan industri Bekasi", "jumlah": 132},
            {"id_kasus": id_kasus, "tipe_entitas": "kata_kunci", "nilai": "ledakan", "jumlah": 188},
            {"id_kasus": id_kasus, "tipe_entitas": "kata_kunci", "nilai": "bau kimia", "jumlah": 87},
            {"id_kasus": id_kasus, "tipe_entitas": "kata_kunci", "nilai": "motor mencurigakan", "jumlah": 53},
            {"id_kasus": id_kasus, "tipe_entitas": "jangkar_waktu", "nilai": "02:30 WIB", "jumlah": 241},
        ]
        peringatan = [
            {"id_peringatan": id_acak("alert"), "id_kasus": id_kasus, "tingkat_keparahan": "tinggi", "tipe_sinyal": "posting_pra_kejadian", "deskripsi": "Post 2 hari sebelum kejadian menyebut kejutan besar di kawasan industri.", "kepercayaan": 0.82},
            {"id_peringatan": id_acak("alert"), "id_kasus": id_kasus, "tingkat_keparahan": "menengah", "tipe_sinyal": "narasi_copy_paste", "deskripsi": "Sekelompok akun menyebarkan wording mirip soal ledakan dan bau kimia dalam rentang waktu sempit.", "kepercayaan": 0.79},
            {"id_peringatan": id_acak("alert"), "id_kasus": id_kasus, "tingkat_keparahan": "menengah", "tipe_sinyal": "co_lokasi", "deskripsi": "Beberapa profil terlihat check-in di titik logistik yang sama sebelum insiden.", "kepercayaan": 0.74},
        ]
        skor_risiko = {
            "id_kasus": id_kasus,
            "label_risiko": "tinggi",
            "skor_risiko": 78,
            "probabilitas_kecelakaan": 0.58,
            "probabilitas_sabotase_terorganisir": 0.42,
            "pendorong": ["ledakan_awal", "akun_sinkron", "posting_pra_kejadian", "sinyal_co_lokasi"],
            "penafian": "Penilaian ini indikatif dan bukan atribusi final.",
        }
        laporan = {
            "id_laporan": id_acak("laporan"),
            "id_kasus": id_kasus,
            "judul": config_kasus["judul"],
            "ringkasan": "Data crawling menunjukkan indikasi ledakan awal, narasi seragam, dan sinyal kehadiran bersama sebelum kejadian.",
            "temuan": [
                "Sekitar 30% mention menyebut ledakan sebelum api besar.",
                "Sebagian akun menyebarkan narasi seragam dalam waktu hampir bersamaan.",
                "Terdapat posting pra-insiden dan sinyal shared meeting point.",
            ],
            "analisis": "Belum cukup dasar untuk atribusi final, namun pola konsisten dengan sabotase terorganisir atau koordinasi narasi pasca-insiden.",
            "rekomendasi": [
                "Monitor akun dan bridge account yang overlap dengan kasus lain.",
                "Bandingkan check-in lokasi dengan data posting dan edge jaringan.",
                "Uji kembali wording copy-paste dan kedekatan timestamp.",
            ],
            "digenerate_pada": sekarang_iso(),
            "penafian": "Laporan ini bersifat indikatif untuk kebutuhan analisis internal.",
        }
        tautan_kasus = [
            {"id_kasus": id_kasus, "id_profil": pid, "peran": "aktor_teramati" if i < 8 else "akun_sinyal", "sinyal": "sinyal_kebakaran_gudang"}
            for i, pid in enumerate(aktor[:12])
        ]
        kasus = {
            "id_kasus": id_kasus,
            "tipe_kasus": "kebakaran_gudang",
            "judul": config_kasus["judul"],
            "kota": config_kasus["kota"],
            "provinsi": config_kasus["provinsi"],
            "waktu_insiden": dt_ke_iso(waktu_insiden),
            "id_titik_pertemuan": titik["id_titik_pertemuan"],
            "jumlah_aktor": len(aktor[:12]),
            "status": "monitoring",
        }
        return {
            "kasus": kasus,
            "postingan": postingan,
            "lokasi": lokasi,
            "jaringan": jaringan_pertemuan,
            "crawling": self._bangun_crawling_kebakaran_gudang(id_kasus, config_kasus, aktor),
            "entitas": entitas,
            "peringatan": peringatan,
            "skor_risiko": skor_risiko,
            "laporan": laporan,
            "tautan_kasus": tautan_kasus,
        }

    def _bangun_crawling_kebakaran_gudang(self, id_kasus: str, config_kasus: dict, aktor: list[str]) -> list[dict]:
        waktu_insiden = config_kasus["waktu_insiden"]
        pool_konten = [
            ("sosial_media", "twitter", "Baru aja denger ledakan sebelum kebakaran."),
            ("sosial_media", "instagram", "Video api gede, orang-orang panik di lokasi."),
            ("sosial_media", "tiktok", "Asap hitam tebal kelihatan dari arah gudang."),
            ("forum", "forum", "Ini bukan kebakaran biasa, ada bau bahan kimia."),
            ("forum", "forum", "Katanya sempat ada ancaman sebelumnya."),
            ("berita", "portal", "Gudang terbakar, dugaan awal korsleting listrik."),
            ("berita", "portal", "Saksi menyebut ada ledakan sebelum api membesar."),
            ("sensor", "cuaca", "Cuaca normal, tidak ada petir di area sekitar."),
            ("cctv", "cctv", "Terlihat motor keluar beberapa menit sebelum api besar."),
            ("sosial_media", "facebook", "Warga sekitar sebut ada bau aneh sebelum api."),
            ("forum", "forum", "Thread panjang soal dugaan sabotase, masih spekulasi."),
            ("berita", "portal", "Pemadam kebakaran butuh waktu lama padamkan api."),
        ]
        crawling = []
        for idx in range(600):
            tipe_sumber, platform, konten_dasar = self.rng.choice(pool_konten)
            varian = konten_dasar
            if idx % 11 == 0:
                varian = "Info masih simpang siur, bisa jadi cuma korsleting biasa."
            elif idx % 13 == 0:
                varian = "Posting ini copy-paste dari akun lain, konteks belum jelas."
            elif idx % 17 == 0:
                varian = "Ada laporan tidak resmi soal aktivitas mencurigakan sebelum insiden."
            crawling.append({
                "id_titik_data": id_acak("crawl"),
                "id_kasus": id_kasus,
                "tipe_sumber": tipe_sumber,
                "platform": platform,
                "referensi_profil": self.rng.choice(aktor) if self.rng.random() < 0.48 else None,
                "konten": varian,
                "timestamp": dt_ke_iso(waktu_insiden + timedelta(minutes=self.rng.randint(-180, 700))),
                "kota": config_kasus["kota"],
                "provinsi": config_kasus["provinsi"],
                "latitude": dibulatkan(-6.24 + self.rng.uniform(-0.05, 0.05)),
                "longitude": dibulatkan(107.0 + self.rng.uniform(-0.07, 0.07)),
                "tag_sinyal": self.rng.sample(["ledakan", "api", "bau_kimia", "motor", "noise", "korsleting"], k=2),
                "reliabilitas": round(self.rng.uniform(0.18, 0.91), 2),
            })
        return crawling

    def _bangun_kasus_pendanaan(
        self, config_kasus: dict, akun_per_profil: dict,
        pool_aktor: dict, titik_pertemuan: list[dict]
    ) -> dict:
        id_kasus = config_kasus["id_kasus"]
        waktu_insiden = config_kasus["waktu_insiden"]
        aktor = list(dict.fromkeys(pool_aktor["klaster_b"][:9] + pool_aktor["overlap"][:4]))
        titik = self._pilih_titik_pertemuan(titik_pertemuan, config_kasus["kota"], config_kasus["tipe_pertemuan"])

        transaksi = []
        jaringan = []
        postingan = []
        for idx in range(max(12, len(aktor) - 1)):
            sumber, tujuan = self.rng.sample(aktor, 2)
            jumlah = self.rng.randint(300000, 3500000)
            ts = waktu_insiden - timedelta(days=self.rng.randint(1, 21), hours=self.rng.randint(0, 12))
            transaksi.append({
                "id_transaksi": id_acak("txn"),
                "id_kasus": id_kasus,
                "id_profil_sumber": sumber,
                "id_profil_tujuan": tujuan,
                "jumlah_idr": jumlah,
                "timestamp": dt_ke_iso(ts),
                "kanal": self.rng.choice(["transfer_bank", "dompet_digital", "tunai"]),
                "referensi": f"REF-{self.rng.randint(100000, 999999)}",
                "petunjuk_tujuan": self.rng.choice(TUJUAN_PENDANAAN),
                "id_perangkat_bersama": f"DEV-{self.rng.randint(1000, 9999)}" if idx < 5 else None,
                "ip_bersama": f"10.42.{self.rng.randint(1, 200)}.{self.rng.randint(2, 220)}" if idx < 6 else None,
            })
            jaringan.append({
                "id_edge": id_acak("edge"),
                "id_profil_sumber": sumber,
                "id_profil_tujuan": tujuan,
                "tipe_edge": "transfer_finansial",
                "bobot": round(min(jumlah / 3500000, 0.99), 2),
                "id_kasus": id_kasus,
            })

        for pid in aktor[:8]:
            akun = self.rng.choice(akun_per_profil[pid])
            postingan.append({
                "id_posting": id_acak("post"),
                "id_profil": pid,
                "id_akun": akun["id_akun"],
                "platform": akun["platform"],
                "konten": self.rng.choice([
                    "Siapkan dana operasional kecil-kecilan dulu, nanti disesuaikan.",
                    "Drop dulu yang urgent. Rincian menyusul di jalur aman.",
                    "Kebutuhan minggu ini jangan sampai telat, sisanya nanti dibahas.",
                    "Transfer sudah konfirm, tunggu kabar selanjutnya.",
                    "Dana awal sudah siap. Koordinasi lanjut seperti biasa.",
                ]),
                "timestamp": dt_ke_iso(waktu_insiden - timedelta(days=self.rng.randint(2, 14))),
                "kota": config_kasus["kota"],
                "provinsi": config_kasus["provinsi"],
                "latitude": titik["latitude"],
                "longitude": titik["longitude"],
                "tipe_konten": "teks",
                "engagement": {"suka": self.rng.randint(0, 50), "komentar": self.rng.randint(0, 20), "bagikan": self.rng.randint(0, 8)},
                "hashtag": ["#support", "#koordinasi"],
                "kata_kunci": ["transfer", "operasional", "drop"],
                "referensi_mention": [],
                "balas_ke_id_posting": None,
                "repost_dari_id_posting": None,
                "tipe_sumber": "sinyal_kasus",
                "referensi_skenario": [id_kasus],
            })

        crawling = []
        for _ in range(250):
            crawling.append({
                "id_titik_data": id_acak("crawl"),
                "id_kasus": id_kasus,
                "tipe_sumber": self.rng.choice(["forum", "obrolan", "catatan_transaksi", "sosial_media"]),
                "platform": self.rng.choice(["telegram", "forum", "twitter", "log_bank"]),
                "referensi_profil": self.rng.choice(aktor) if self.rng.random() < 0.55 else None,
                "konten": self.rng.choice([
                    "Transfer kecil berulang muncul pada rentang waktu berdekatan.",
                    "Akun forum membahas iuran logistik tanpa rincian jelas.",
                    "Komentar komunitas menyebut pengumpulan dana mendadak.",
                    "Ada catatan tentang rekening perantara dan pertemuan singkat.",
                    "Sebagian sinyal bisa saja sekadar iuran komunitas biasa.",
                    "Pola transfer memperlihatkan distribusi ke beberapa penerima berbeda.",
                    "Tidak ada keterangan resmi, informasi masih berdasarkan laporan awal.",
                ]),
                "timestamp": dt_ke_iso(waktu_insiden - timedelta(days=self.rng.randint(1, 25), hours=self.rng.randint(0, 23))),
                "kota": config_kasus["kota"],
                "provinsi": config_kasus["provinsi"],
                "latitude": titik["latitude"],
                "longitude": titik["longitude"],
                "tag_sinyal": self.rng.sample(["transfer", "iuran", "pertemuan", "dompet", "noise"], k=2),
                "reliabilitas": round(self.rng.uniform(0.22, 0.89), 2),
            })

        lokasi, jaringan_pertemuan = self._tambah_checkin_kasus(aktor[:7], titik, waktu_insiden, id_kasus)
        entitas = [
            {"id_kasus": id_kasus, "tipe_entitas": "kata_kunci", "nilai": "transfer kecil berulang", "jumlah": 78},
            {"id_kasus": id_kasus, "tipe_entitas": "lokasi", "nilai": titik["label"], "jumlah": 34},
            {"id_kasus": id_kasus, "tipe_entitas": "kata_kunci", "nilai": "perangkat_bersama", "jumlah": 12},
        ]
        peringatan = [{
            "id_peringatan": id_acak("alert"),
            "id_kasus": id_kasus,
            "tingkat_keparahan": "menengah",
            "tipe_sinyal": "pola_finansial",
            "deskripsi": "Pola transfer menunjukkan distribusi dana kecil berulang ke cluster terbatas.",
            "kepercayaan": 0.76,
        }]
        skor_risiko = {
            "id_kasus": id_kasus,
            "label_risiko": "menengah",
            "skor_risiko": 67,
            "probabilitas_dukungan_rutin": 0.54,
            "probabilitas_pendanaan_terkoordinasi": 0.46,
            "pendorong": ["transfer_berulang", "perangkat_bersama", "co_lokasi"],
            "penafian": "Penilaian ini indikatif dan bukan atribusi final.",
        }
        laporan = {
            "id_laporan": id_acak("laporan"),
            "id_kasus": id_kasus,
            "judul": config_kasus["judul"],
            "ringkasan": "Data memperlihatkan transaksi kecil berulang, kedekatan lokasi antar aktor, dan penggunaan perangkat/IP yang tumpang tindih.",
            "temuan": [
                "Transfer tersebar muncul menjelang aktivitas lapangan tertentu.",
                "Beberapa profil yang sama juga terlihat pada klaster propaganda atau kasus kebakaran gudang.",
                "Titik pertemuan bersama memperkuat sinyal korelasi lintas kasus.",
            ],
            "analisis": "Pola dapat dibaca sebagai koordinasi finansial, namun masih butuh validasi lintas sumber.",
            "rekomendasi": [
                "Uji graf transfer versus graf sosial.",
                "Periksa overlap perangkat/IP dan titik temu lokasi bersama.",
                "Prioritaskan bridge account yang muncul lintas kasus.",
            ],
            "digenerate_pada": sekarang_iso(),
            "penafian": "Laporan ini bersifat indikatif untuk kebutuhan analisis internal.",
        }
        tautan_kasus = [{"id_kasus": id_kasus, "id_profil": pid, "peran": "aktor_pendanaan", "sinyal": "sinyal_pendanaan"} for pid in aktor]
        kasus = {
            "id_kasus": id_kasus,
            "tipe_kasus": "pendanaan_mencurigakan",
            "judul": config_kasus["judul"],
            "kota": config_kasus["kota"],
            "provinsi": config_kasus["provinsi"],
            "waktu_insiden": dt_ke_iso(waktu_insiden),
            "id_titik_pertemuan": titik["id_titik_pertemuan"],
            "jumlah_aktor": len(aktor),
            "status": "analisis",
        }
        return {
            "kasus": kasus,
            "postingan": postingan,
            "lokasi": lokasi,
            "jaringan": jaringan + jaringan_pertemuan,
            "crawling": crawling,
            "entitas": entitas,
            "peringatan": peringatan,
            "skor_risiko": skor_risiko,
            "laporan": laporan,
            "transaksi": transaksi,
            "peringatan_dana": [
                {"id_peringatan_dana": id_acak("palert"), "id_kasus": id_kasus, "tingkat_keparahan": "menengah", "deskripsi": "Sejumlah transfer kecil berulang mengarah ke penerima yang sama dalam jendela waktu sempit.", "kepercayaan": 0.77},
                {"id_peringatan_dana": id_acak("palert"), "id_kasus": id_kasus, "tingkat_keparahan": "menengah", "deskripsi": "Sebagian transaksi berbagi perangkat atau IP yang sama.", "kepercayaan": 0.71},
            ],
            "tautan_kasus": tautan_kasus,
        }

    def _bangun_kasus_propaganda(
        self, config_kasus: dict, akun_per_profil: dict,
        pool_aktor: dict, titik_pertemuan: list[dict]
    ) -> dict:
        id_kasus = config_kasus["id_kasus"]
        waktu_insiden = config_kasus["waktu_insiden"]
        aktor = list(dict.fromkeys(pool_aktor["klaster_c"][:12] + pool_aktor["overlap"][:3]))
        titik = self._pilih_titik_pertemuan(titik_pertemuan, config_kasus["kota"], config_kasus["tipe_pertemuan"])
        pusat = aktor[0]
        varian_narasi = [
            "disrupsi supply chain bikin pihak tertentu kelabakan malam ini",
            "gangguan rantai pasok bikin situasi cepat berubah malam ini",
            "jalur distribusi lagi terganggu, efeknya bakal terasa cepat",
            "supply chain yang terguncang bisa bikin respons mereka terlambat",
            "kondisi logistik memburuk, beberapa pihak mulai kelimpungan",
            "situasi rantai pasokan yang tidak stabil bikin banyak yang was-was",
        ]

        postingan = []
        klaster_pesan = []
        kampanye = [{
            "id_kampanye": id_acak("kamp"),
            "id_kasus": id_kasus,
            "id_profil_pusat": pusat,
            "tujuan": "amplifikasi narasi terkait gangguan distribusi",
            "mulai_pada": dt_ke_iso(waktu_insiden - timedelta(hours=8)),
        }]
        id_posting_dasar = None
        for idx, pid in enumerate(aktor[:14]):
            akun = self.rng.choice(akun_per_profil[pid])
            id_posting = id_acak("post")
            if idx == 0:
                id_posting_dasar = id_posting
            postingan.append({
                "id_posting": id_posting,
                "id_profil": pid,
                "id_akun": akun["id_akun"],
                "platform": akun["platform"],
                "konten": varian_narasi[0] if idx == 0 else self.rng.choice(varian_narasi),
                "timestamp": dt_ke_iso(waktu_insiden - timedelta(minutes=self.rng.randint(2, 80))),
                "kota": config_kasus["kota"],
                "provinsi": config_kasus["provinsi"],
                "latitude": titik["latitude"],
                "longitude": titik["longitude"],
                "tipe_konten": "teks",
                "engagement": {"suka": self.rng.randint(5, 280), "komentar": self.rng.randint(0, 55), "bagikan": self.rng.randint(0, 110)},
                "hashtag": ["#supplychain", "#update", "#situasi", "#logistik"],
                "kata_kunci": ["disrupsi", "rantai_pasok", "sinkron"],
                "referensi_mention": [pusat] if idx > 0 and self.rng.random() < 0.45 else [],
                "balas_ke_id_posting": None,
                "repost_dari_id_posting": id_posting_dasar if idx > 0 and self.rng.random() < 0.55 else None,
                "tipe_sumber": "terkoordinasi" if idx > 0 else "benih_organik",
                "referensi_skenario": [id_kasus],
            })
        for i_klaster, frasa in enumerate(varian_narasi[:4]):
            klaster_pesan.append({
                "id_klaster_pesan": id_acak("kpst"),
                "id_kasus": id_kasus,
                "frasa_kanonik": frasa,
                "id_profil": aktor[i_klaster * 3 : i_klaster * 3 + 4],
                "jumlah_posting": self.rng.randint(4, 12),
                "kemiripan_copy": round(self.rng.uniform(0.74, 0.96), 2),
            })

        lokasi, jaringan_pertemuan = self._tambah_checkin_kasus(aktor[:6], titik, waktu_insiden, id_kasus)
        jaringan = list(jaringan_pertemuan)
        for pid in aktor[1:12]:
            jaringan.append({
                "id_edge": id_acak("edge"),
                "id_profil_sumber": pusat,
                "id_profil_tujuan": pid,
                "tipe_edge": "amplifikasi_pesan",
                "bobot": round(self.rng.uniform(0.61, 0.96), 2),
                "id_kasus": id_kasus,
            })

        crawling = []
        for _ in range(300):
            crawling.append({
                "id_titik_data": id_acak("crawl"),
                "id_kasus": id_kasus,
                "tipe_sumber": self.rng.choice(["sosial_media", "forum", "komentar_berita", "catatan_komunitas"]),
                "platform": self.rng.choice(["twitter", "instagram", "forum", "tiktok"]),
                "referensi_profil": self.rng.choice(aktor) if self.rng.random() < 0.65 else None,
                "konten": self.rng.choice([
                    "Sekelompok akun baru membagikan narasi yang sangat mirip.",
                    "Posting serempak muncul dalam rentang menit yang sempit.",
                    "Ada akun yang hanya aktif untuk satu topik lalu diam lagi.",
                    "Sebagian posting bisa dianggap opini biasa, tidak semua terkoordinasi.",
                    "Komentar forum menyebut pola copy-paste dan akun yang baru dibuat.",
                    "Pola wording nyaris identik di beberapa akun berbeda.",
                    "Akun lama tiba-tiba aktif lagi dengan topik yang sama.",
                    "Ada jeda waktu sangat pendek antara satu posting dan pengulangan berikutnya.",
                ]),
                "timestamp": dt_ke_iso(waktu_insiden - timedelta(hours=self.rng.randint(0, 28), minutes=self.rng.randint(0, 59))),
                "kota": config_kasus["kota"],
                "provinsi": config_kasus["provinsi"],
                "latitude": titik["latitude"],
                "longitude": titik["longitude"],
                "tag_sinyal": self.rng.sample(["copy_paste", "akun_baru", "narasi", "sinkron", "noise"], k=2),
                "reliabilitas": round(self.rng.uniform(0.21, 0.86), 2),
            })

        entitas = [
            {"id_kasus": id_kasus, "tipe_entitas": "kata_kunci", "nilai": "disrupsi supply chain", "jumlah": 49},
            {"id_kasus": id_kasus, "tipe_entitas": "kata_kunci", "nilai": "copy-paste wording", "jumlah": 26},
            {"id_kasus": id_kasus, "tipe_entitas": "klaster_akun", "nilai": "14 akun sinkron", "jumlah": 1},
        ]
        peringatan = [
            {"id_peringatan": id_acak("alert"), "id_kasus": id_kasus, "tingkat_keparahan": "tinggi", "tipe_sinyal": "posting_tersinkronisasi", "deskripsi": "Terdapat klaster akun dengan pola posting hampir serentak dan wording serupa.", "kepercayaan": 0.84},
            {"id_peringatan": id_acak("alert"), "id_kasus": id_kasus, "tingkat_keparahan": "menengah", "tipe_sinyal": "overlap_jembatan", "deskripsi": "Sebagian akun juga muncul dalam sinyal pendanaan atau kebakaran gudang.", "kepercayaan": 0.72},
        ]
        skor_risiko = {
            "id_kasus": id_kasus,
            "label_risiko": "tinggi",
            "skor_risiko": 74,
            "probabilitas_diskursus_organik": 0.49,
            "probabilitas_propagasi_terkoordinasi": 0.51,
            "pendorong": ["copy_paste", "sinkronisasi_waktu", "overlap_jembatan"],
            "penafian": "Penilaian ini indikatif dan bukan atribusi final.",
        }
        laporan = {
            "id_laporan": id_acak("laporan"),
            "id_kasus": id_kasus,
            "judul": config_kasus["judul"],
            "ringkasan": "Narasi beredar melalui akun pusat dan akun amplifikasi dengan jeda waktu pendek, termasuk akun yang juga muncul di kasus lain.",
            "temuan": [
                "Pola posting serempak menguat pada window kurang dari satu jam.",
                "Klaster pesan menunjukkan kemiripan frasa yang tinggi.",
                "Bridge account memperluas korelasi lintas kasus.",
            ],
            "analisis": "Sinyal konsisten dengan koordinasi narasi, namun masih bersifat indikatif.",
            "rekomendasi": [
                "Kelompokkan akun berdasarkan copy similarity dan waktu posting.",
                "Bandingkan overlap dengan edge transfer serta meeting point.",
                "Pisahkan akun baru dari akun lama untuk menguji pola bootstrap.",
            ],
            "digenerate_pada": sekarang_iso(),
            "penafian": "Laporan ini bersifat indikatif untuk kebutuhan analisis internal.",
        }
        tautan_kasus = [
            {"id_kasus": id_kasus, "id_profil": pid, "peran": "amplifier" if pid != pusat else "akun_benih", "sinyal": "sinyal_propaganda"}
            for pid in aktor[:14]
        ]
        kasus = {
            "id_kasus": id_kasus,
            "tipe_kasus": "propaganda",
            "judul": config_kasus["judul"],
            "kota": config_kasus["kota"],
            "provinsi": config_kasus["provinsi"],
            "waktu_insiden": dt_ke_iso(waktu_insiden),
            "id_titik_pertemuan": titik["id_titik_pertemuan"],
            "jumlah_aktor": len(aktor[:14]),
            "status": "monitoring",
        }
        return {
            "kasus": kasus,
            "postingan": postingan,
            "lokasi": lokasi,
            "jaringan": jaringan,
            "crawling": crawling,
            "entitas": entitas,
            "peringatan": peringatan,
            "skor_risiko": skor_risiko,
            "laporan": laporan,
            "kampanye": kampanye,
            "klaster_pesan": klaster_pesan,
            "tautan_kasus": tautan_kasus,
        }

    def _reset_output_kasus(self, bundle: BundleData) -> None:
        bundle.kasus = []
        bundle.transaksi = []
        bundle.peringatan_dana = []
        bundle.kampanye = []
        bundle.klaster_pesan = []
        bundle.crawling = []
        bundle.entitas = []
        bundle.peringatan = []
        bundle.skor_risiko = []
        bundle.laporan = []
        bundle.postingan = [item for item in bundle.postingan if not item.get("referensi_skenario")]
        bundle.lokasi = [item for item in bundle.lokasi if not item.get("id_kasus")]
        bundle.jaringan = [item for item in bundle.jaringan if not item.get("id_kasus")]
        for profil in bundle.profil:
            profil["tautan_kasus"] = []
            profil["tag_risiko"] = []

    def _perbarui_ekstraksi_profil(self, bundle: BundleData) -> None:
        kontak_per_profil = {item["id_profil"]: item for item in bundle.kontak}
        pref_per_profil = {item["id_profil"]: item for item in bundle.preferensi}
        akun_per_profil: dict[str, list] = {}
        foto_per_profil: dict[str, list] = {}
        posting_per_profil: dict[str, list] = {}
        for item in bundle.akun:
            akun_per_profil.setdefault(item["id_profil"], []).append(item)
        for item in bundle.foto:
            foto_per_profil.setdefault(item["id_profil"], []).append(item)
        for item in bundle.postingan:
            posting_per_profil.setdefault(item["id_profil"], []).append(item)

        for profil in bundle.profil:
            pid = profil["id_profil"]
            profil["profil_terekstrak"] = self._bangun_profil_terekstrak(
                profil=profil,
                kontak=kontak_per_profil[pid],
                preferensi=pref_per_profil[pid],
                akun=akun_per_profil.get(pid, []),
                pertemanan=bundle.pertemanan,
                foto=foto_per_profil.get(pid, []),
                postingan=sorted(posting_per_profil.get(pid, []), key=lambda x: x["timestamp"], reverse=True),
                lokasi=bundle.lokasi,
            )


# ============================================================
# FUNGSI UTAMA PUBLIK
# ============================================================

def bangun_dataset_profil(jumlah: int, dir_output: str, seed: int = 42, dengan_gambar: bool = False) -> BundleData:
    """Buat dataset profil sintetis sebanyak `jumlah` entri."""
    generator = GeneratorDataSintetis(seed=seed)
    return generator.bangun_bundle_profil(jumlah=jumlah, dir_output=dir_output, dengan_gambar=dengan_gambar)


def bangun_dataset_kasus(dir_output: str, seed: int = 42, nama_kasus: list[str] | None = None) -> BundleData:
    """Augmentasi bundle yang sudah ada dengan data kasus."""
    generator = GeneratorDataSintetis(seed=seed)
    bundle = generator.muat_bundle(dir_output)
    if not bundle.profil:
        raise ValueError("profil.json tidak ditemukan atau kosong. Jalankan bangun_dataset_profil() dulu.")
    return generator.augmentasi_bundle_dengan_kasus(bundle=bundle, nama_kasus=nama_kasus)


def bangun_dataset_lengkap(
    jumlah: int,
    dir_output: str,
    seed: int = 42,
    dengan_gambar: bool = False,
    nama_kasus: list[str] | None = None,
) -> BundleData:
    """Buat dataset lengkap: profil + kasus dalam satu langkah."""
    generator = GeneratorDataSintetis(seed=seed)
    print(f"[MULAI] Membangun {jumlah} profil sintetis...")
    bundle = generator.bangun_bundle_profil(jumlah=jumlah, dir_output=dir_output, dengan_gambar=dengan_gambar)
    print(f"[KASUS] Menambahkan 3 kasus...")
    bundle = generator.augmentasi_bundle_dengan_kasus(bundle=bundle, nama_kasus=nama_kasus)
    print(f"[SIMPAN] Menyimpan ke {dir_output}...")
    generator.tulis_bundle(bundle, dir_output)
    print(f"[SELESAI] Dataset lengkap tersedia di: {dir_output}")
    return bundle


# ============================================================
# CONTOH PENGGUNAAN
# ============================================================

if __name__ == "__main__":
    import sys

    jumlah = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    output = sys.argv[2] if len(sys.argv) > 2 else "./dataset"

    print(f"Membangun dataset dengan {jumlah} profil → {output}")
    bundle = bangun_dataset_lengkap(jumlah=jumlah, dir_output=output, seed=42)
    print(f"\nRingkasan:")
    print(f"  Profil      : {len(bundle.profil)}")
    print(f"  Akun        : {len(bundle.akun)}")
    print(f"  Postingan   : {len(bundle.postingan)}")
    print(f"  Pertemanan  : {len(bundle.pertemanan)}")
    print(f"  Jaringan    : {len(bundle.jaringan)}")
    print(f"  Lokasi      : {len(bundle.lokasi)}")
    print(f"  Kasus       : {len(bundle.kasus)}")
    print(f"  Transaksi   : {len(bundle.transaksi)}")
    print(f"  Crawling    : {len(bundle.crawling)}")
    print(f"  Laporan     : {len(bundle.laporan)}")