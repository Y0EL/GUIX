# Atlas Voice Assistant — Dokumentasi Interaksi

**Atlas** adalah asisten suara berbasis AI untuk sistem intelijen UIX.  
Berjalan lokal dengan Ollama + Whisper + edge-tts. Bisa membuka halaman UIX di browser, membaca dataset internal, dan menjawab pertanyaan bebas.

---

## Cara Menjalankan

### Prasyarat

```bash
# 1. Install dependencies Python
pip install edge-tts openai-whisper sounddevice numpy scipy webrtcvad pygame ollama requests

# 2. Install ffmpeg (wajib untuk Whisper)
winget install ffmpeg           # Windows
# atau download dari https://ffmpeg.org/download.html → tambah ke PATH

# 3. Jika webrtcvad error di Windows:
pip install webrtcvad-wheels     # versi pre-compiled

# 4. Pastikan Ollama server aktif di terminal terpisah:
ollama serve
# Cek model tersedia:
ollama list                      # harus ada: qwen3.5:latest
```

### Jalankan Atlas

```bash
# Terminal 1 (biarkan terbuka):
ollama serve

# Terminal 2:
cd C:\Users\Engineer02\Desktop\UIX
python atlas.py
```

### Output Startup yang Diharapkan

```
====================================================
  Memulai Atlas Voice Assistant — UIX
====================================================

  [1/3] Memuat dataset UIX...
  [OK] kasus.json — 3 record
  [OK] peringatan.json — 15 record
  [OK] profil.json — 30 record
  ...
  [OK] news/dataset.jsonl — 20 berita

  [2/3] Memeriksa koneksi Ollama...
  [OK] Ollama terhubung, model qwen3.5:latest siap

  [3/3] Inisialisasi komponen suara (Whisper + TTS)...
  Memuat model Whisper tiny (wake word)...
  [OK] Model tiny siap
  Memuat model Whisper base (transkripsi perintah)...
  [OK] Model base siap

  Semua komponen siap. Atlas aktif!

====================================================
  🤖  ATLAS — UIX Intelligence Voice Assistant
  Model LLM : qwen3.5:latest
  TTS Voice : id-ID-GadisNeural
  UIX URL   : http://localhost:5173
  Wake word : 'Hey Atlas'
====================================================
  ⏳ Mendengarkan wake word... (window 3 detik)
====================================================
  [cek] ''
  [cek] 'hey atlas'
  🔔  Wake word terdeteksi!
```

---

## Cara Memanggil Atlas

Ucapkan **"Hey Atlas"** — tunggu sampai Atlas menjawab **"Ya?"**,  
lalu ucapkan perintahmu dengan jelas.

Atlas akan berhenti merekam otomatis sekitar 1–2 detik setelah kamu diam.

---

## Daftar Perintah Suara

### Navigasi Halaman UIX

| Ucapan | Halaman yang Dibuka |
|--------|---------------------|
| "Buka beranda" / "Buka overview" | `/` — Ikhtisar Global |
| "Buka peringatan" / "Buka alert" | `/alert-center` — Pusat Peringatan |
| "Buka insiden" / "Buka antrean" | `/incident-queue` — Antrean Insiden |
| "Buka peta" / "Buka map" | `/map-intelligence` — Intelijen Peta |
| "Buka pencarian" / "Buka search" | `/search` — Pencarian & Penemuan |
| "Buka jaringan" / "Buka link analysis" | `/link-analysis` — Analisis Jaringan |
| "Buka timeline" / "Buka kronologi" | `/timeline` — Timeline Kejadian |
| "Buka narasi" / "Buka tren" | `/narrative` — Narasi & Tren |
| "Buka kanvas" / "Buka investigasi" | `/canvas` — Kanvas Investigasi |
| "Buka konten" / "Buka bukti" | `/content` — Konten & Bukti |
| "Buka briefing" / "Buka laporan halaman" | `/briefing` — Briefing & Laporan |
| "Buka fusion" / "Buka fusion board" | `/fusion` — Fusion Board |
| "Buka admin" / "Buka sistem" | `/admin` — Admin & Audit |

**Pola trigger navigasi yang dikenali:**  
"buka X" · "pergi ke X" · "tampilkan X" · "navigasi ke X" · "pindah ke X" · "ke halaman X"

---

### Membaca Data Kasus

| Ucapan | Respons Atlas |
|--------|---------------|
| "Daftar kasus" / "Ada kasus apa saja?" | Membaca semua kasus + status |
| "Kasus kebakaran" / "Ceritakan kasus gudang" | Detail lengkap kasus kebakaran gudang |
| "Kasus pendanaan" / "Info kasus pendanaan mencurigakan" | Detail kasus pendanaan |
| "Kasus propaganda" / "Bacakan kasus propaganda burst" | Detail kasus propaganda |

**Kasus yang tersedia di dataset:**
- `kasus-kebakaran-gudang` — Kebakaran Gudang Logistik, Bekasi, indikasi sabotase
- `kasus-pendanaan-mencurigakan` — Pola pendanaan tersebar, Jakarta
- `kasus-propaganda-burst` — Amplifikasi narasi terkoordinasi, Cikarang

---

### Membaca Profil

| Ucapan | Respons Atlas |
|--------|---------------|
| "Siapa Winda?" | Cari profil dengan nama mengandung "Winda" |
| "Cari profil Ahmad" | Cari semua profil bernama Ahmad |
| "Info tentang Jakarta" | Cari profil berdomisili Jakarta |
| "Profil prof-b90000841f" | Detail profil berdasarkan ID |

Atlas mengembalikan **top 3 profil** yang paling cocok dengan nama yang disebutkan.

---

### Membaca Berita

| Ucapan | Respons Atlas |
|--------|---------------|
| "Berita terbaru" / "Berita hari ini" | 5 berita terbaru berdasarkan tanggal |
| "Berita terkini" / "Baca berita" | Sama seperti di atas |
| "Cari berita banjir" | Cari berita dengan kata kunci "banjir" |
| "Berita tentang Jakarta" | Cari berita lokasi/tag Jakarta |
| "Berita soal perdagangan manusia" | Cari berita terkait topik tersebut |

**Kategori berita tersedia:** Daerah · Ekonomi · Hukum & Kriminal · Keamanan · Nasional · Olahraga · Sosial · Teknologi

---

### Peringatan & Status Sistem

| Ucapan | Respons Atlas |
|--------|---------------|
| "Ada peringatan apa?" / "Peringatan aktif" | 5 peringatan prioritas tertinggi |
| "Status sistem" / "Ringkasan" / "Kondisi sistem" | Ringkasan jumlah semua data |
| "Klaster pesan" / "Narasi koordinasi" | Klaster pesan terkoordinasi tertinggi |

---

### Chat Bebas (Fallback Ollama)

Semua perintah yang tidak cocok dengan kategori di atas akan diteruskan ke Ollama.

| Ucapan Contoh | Keterangan |
|----------------|------------|
| "Apa yang kamu tahu tentang sabotase gudang?" | Atlas bisa menjawab berbasis context dataset |
| "Bagaimana cara analisis jaringan sosial?" | Pengetahuan umum Ollama |
| "Jelaskan apa itu OSINT" | Pertanyaan umum |
| "Apa rekomendasi investigasi untuk kasus propaganda?" | Atlas menggunakan context internal |

---

## Dataset yang Bisa Diakses Atlas

| Dataset | Isi | Jumlah |
|---------|-----|--------|
| `kasus.json` | Kasus investigasi (id, judul, tipe, lokasi, status) | 3 kasus |
| `peringatan.json` | Peringatan aktif per kasus (tingkat, deskripsi, kepercayaan) | ~15 |
| `laporan.json` | Laporan analisis per kasus (ringkasan, temuan, rekomendasi) | ~3 |
| `skor_risiko.json` | Skor risiko 0-100 + probabilitas per kasus | ~3 |
| `profil.json` | Profil target (nama, lokasi, bio, platform, tag risiko) | ~30 |
| `akun.json` | Akun media sosial per profil (platform, username) | ~60 |
| `postingan.json` | Postingan media sosial per profil | banyak |
| `transaksi.json` | Transaksi finansial per kasus (jumlah, kanal, timestamp) | banyak |
| `klaster_pesan.json` | Klaster pesan terkoordinasi (frasa, kemiripan, profil terlibat) | banyak |
| `crawling.json` | Data crawling OSINT per kasus (konten, platform, reliabilitas) | banyak |
| `news/dataset.jsonl` | Berita (judul, isi, kategori, lokasi, tanggal) | 20 artikel |

---

## Perilaku Status Atlas

Atlas **tidak pernah diam** saat memproses. Berikut feedback yang selalu diberikan:

| Kondisi | Yang Atlas Katakan |
|---------|--------------------|
| Wake word terdeteksi | *"Ya?"* |
| Navigasi terdeteksi | *"Membuka halaman [nama]."* |
| Sebelum baca data | *"Sedang membaca/mencari data..."* |
| Sebelum tanya Ollama | *"Oke, lagi berpikir sebentar."* |
| Ollama lambat (tiap 10 detik) | *"Masih memproses, sudah 10 detik. Mohon tunggu."* |
| Timeout Ollama (45 detik) | *"Waktu tunggu habis. Coba lagi atau periksa Ollama."* |
| Tidak ada suara tertangkap | *"Tidak ada suara terdeteksi. Panggil lagi bila perlu."* |
| Halaman tidak dikenali | *"Halaman tidak dikenali. Halaman yang tersedia: ..."* |
| Error apapun | Selalu diucapkan + dicetak di terminal |
| Matikan (Ctrl+C) | *"Sampai jumpa."* |

---

## Test Mandiri

### Test Dataset Saja

```bash
python atlas_data.py
```

Output: ringkasan semua dataset, daftar kasus, detail kasus, berita, peringatan.

### Test Koneksi Ollama

```python
# test_ollama.py
import ollama
client = ollama.Client(host="http://localhost:11434")
resp = client.chat(
    model="qwen3.5:latest",
    messages=[{"role": "user", "content": "Halo, kamu siapa?"}],
    options={"num_predict": 50},
)
print(resp["message"]["content"])
```

### Test TTS

```python
# test_tts.py
import asyncio, edge_tts

async def test():
    tts = edge_tts.Communicate("Halo! Saya Atlas, asisten intelijen UIX.", "id-ID-GadisNeural")
    await tts.save("test_atlas_tts.mp3")
    print("File test_atlas_tts.mp3 dibuat.")

asyncio.run(test())
```

---

## Pengaturan (atlas.py bagian atas)

```python
OLLAMA_MODEL  = "qwen3.5:latest"   # sesuaikan dengan: ollama list
TTS_VOICE     = "id-ID-GadisNeural"  # atau: id-ID-ArdiNeural (suara pria)
UIX_BASE_URL  = "http://localhost:5173"
SILENCE_LIMIT = 1.8                # detik diam sebelum stop rekam
OLLAMA_TIMEOUT = 45               # detik maksimum tunggu Ollama
VAD_MODE      = 2                  # 0=lunak ... 3=ketat untuk deteksi suara
```

---

## Troubleshooting

| Error | Solusi |
|-------|--------|
| `ollama.ResponseError: model not found` | Jalankan `ollama pull qwen3.5:latest` atau cek nama model dengan `ollama list` |
| `Connection refused` ke Ollama | Jalankan `ollama serve` di terminal terpisah |
| `No module named 'webrtcvad'` | `pip install webrtcvad-wheels` (Windows) |
| `PortAudio not found` | `pip install pipwin && pipwin install pyaudio` |
| TTS tidak bersuara | Cek koneksi internet (edge-tts butuh internet), atau ganti `TTS_VOICE` |
| Whisper lambat | Model sudah `tiny` untuk wake word dan `base` untuk perintah — cukup optimal |
| Wake word sering miss | Ucapkan lebih jelas dan dekat mikrofon; coba "atlas" saja tanpa "hey" |
| Atlas tidak berhenti rekam | Kurangi `VAD_MODE` ke 1 atau naikkan `SILENCE_LIMIT` |

---

## Suara TTS yang Tersedia

```bash
python -c "import asyncio, edge_tts; voices = asyncio.run(edge_tts.list_voices()); [print(v['ShortName']) for v in voices if 'id-ID' in v['ShortName']]"
```

| Voice | Gender | Karakter |
|-------|--------|----------|
| `id-ID-GadisNeural` | Wanita | Natural, ramah *(default Atlas)* |
| `id-ID-ArdiNeural` | Pria | Natural, santai |

---

## Arsitektur Singkat

```
python atlas.py
    │
    ├── AtlasData (atlas_data.py)
    │     └── Muat /dataset/*.json + /news/dataset.jsonl ke memori
    │
    ├── AtlasTTS
    │     └── edge-tts → MP3 → pygame.mixer
    │
    ├── AtlasListener
    │     ├── Whisper tiny → cek wake word (window 3 detik)
    │     └── webrtcvad + Whisper base → tangkap & transkripsi perintah
    │
    ├── AtlasBrain
    │     └── ollama.Client → qwen3.5, history 8 pesan, strip <think>
    │
    └── Atlas (main loop)
          └── Wake word → "Ya?" → Rekam → Transkripsi → Intent → Handler → TTS
```

---

*Dibuat: 16 April 2026 | Proyek: UIX Intelligence Command Center*
