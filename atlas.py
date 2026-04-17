"""
atlas.py — Atlas Voice Assistant untuk UIX Intelligence System

Perintah suara: wake word "hey atlas" → perintah → eksekusi
Bisa membuka halaman UIX, membaca kasus/profil/berita, dan chat Ollama.

Jalankan: python atlas.py
Pastikan Ollama sudah jalan: ollama serve
"""

# ============================================================
# IMPORTS
# ============================================================
import os
import re
import sys
import time
import asyncio
import tempfile
import threading
import webbrowser
from pathlib import Path

import numpy as np
import sounddevice as sd

# -- init pygame duluan sebelum whisper supaya tidak ada konflik --
try:
    import pygame
    pygame.mixer.init()
    _PYGAME_OK = True
except Exception:
    _PYGAME_OK = False

import whisper  # type: ignore
import edge_tts  # type: ignore
import webrtcvad  # type: ignore
import ollama  # type: ignore

from atlas_data import AtlasData

# ============================================================
# CONFIG
# ============================================================
WAKE_KEYWORDS   = {"atlas", "hey atlas", "hei atlas", "ey atlas", "hai atlas"}
SAMPLE_RATE     = 16000
CHANNELS        = 1
CHUNK_DURATION  = 0.03                          # 30ms per frame VAD
CHUNK_SIZE      = int(SAMPLE_RATE * CHUNK_DURATION)
WINDOW_DURASI   = 3.0                           # detik window wake word
TTS_VOICE       = "id-ID-GadisNeural"
OLLAMA_MODEL    = "qwen3:latest"    # sesuaikan dengan ollama list
UIX_BASE_URL    = "http://localhost:5173"
SILENCE_LIMIT   = 1.8                           # detik silence untuk stop rekam
MAX_RECORD_SEC  = 12                            # maksimum durasi rekam perintah
OLLAMA_TIMEOUT  = 45                            # detik timeout Ollama
VAD_MODE        = 2                             # 0-3, makin tinggi makin agresif

# ============================================================
# PETA NAVIGASI — kata kunci → path UIX
# ============================================================
PETA_HALAMAN: dict[str, str] = {
    "beranda":        "/",
    "overview":       "/",
    "ikhtisar":       "/",
    "home":           "/",
    "peringatan":     "/alert-center",
    "alert":          "/alert-center",
    "pusat peringatan": "/alert-center",
    "insiden":        "/incident-queue",
    "antrean":        "/incident-queue",
    "antrean insiden": "/incident-queue",
    "peta":           "/map-intelligence",
    "map":            "/map-intelligence",
    "intelijen peta": "/map-intelligence",
    "pencarian":      "/search",
    "cari":           "/search",
    "search":         "/search",
    "link analysis":  "/link-analysis",
    "jaringan":       "/link-analysis",
    "analisis tautan": "/link-analysis",
    "timeline":       "/timeline",
    "kronologi":      "/timeline",
    "narasi":         "/narrative",
    "tren":           "/narrative",
    "narrative":      "/narrative",
    "kanvas":         "/canvas",
    "investigasi":    "/canvas",
    "canvas":         "/canvas",
    "konten":         "/content",
    "bukti":          "/content",
    "content":        "/content",
    "kasus workspace": "/case-workspace",
    "workspace":      "/case-workspace",
    "briefing":       "/briefing",
    "laporan halaman": "/briefing",
    "fusion":         "/fusion",
    "fusion board":   "/fusion",
    "admin":          "/admin",
    "sistem":         "/admin",
    "audit":          "/admin",
}

TRIGGER_NAVIGASI = [
    "buka", "pergi ke", "tampilkan", "navigasi ke",
    "ke halaman", "pindah ke", "lihat halaman", "buka halaman",
]

NAMA_HALAMAN: dict[str, str] = {
    "/":               "Ikhtisar",
    "/alert-center":   "Pusat Peringatan",
    "/incident-queue": "Antrean Insiden",
    "/map-intelligence": "Intelijen Peta",
    "/search":         "Pencarian dan Penemuan",
    "/link-analysis":  "Analisis Jaringan",
    "/timeline":       "Timeline Kejadian",
    "/narrative":      "Narasi dan Tren",
    "/canvas":         "Kanvas Investigasi",
    "/content":        "Konten dan Bukti",
    "/case-workspace": "Kasus Workspace",
    "/briefing":       "Briefing dan Laporan",
    "/fusion":         "Fusion Board",
    "/admin":          "Admin dan Audit Sistem",
}

# ============================================================
# UTILITAS
# ============================================================

def strip_think(teks: str) -> str:
    """Hapus blok <think>...</think> dari output Qwen."""
    return re.sub(r"<think>.*?</think>", "", teks, flags=re.DOTALL).strip()


def format_untuk_suara(teks: str) -> str:
    """Bersihkan teks dari karakter non-suara agar nyaman didengar."""
    teks = re.sub(r"[*#→•\[\]_`]", "", teks)
    teks = re.sub(r"\n+", ". ", teks)
    teks = re.sub(r"\s{2,}", " ", teks)
    teks = re.sub(r"Rp\s?([\d,.]+)", r"Rupiah \1", teks)
    return teks.strip()


def potong_untuk_suara(teks: str, maks_kata: int = 80) -> str:
    """Potong teks jika terlalu panjang untuk disuarakan."""
    kata = teks.split()
    if len(kata) <= maks_kata:
        return teks
    return " ".join(kata[:maks_kata]) + "... dan seterusnya."


# ============================================================
# TTS
# ============================================================

class AtlasTTS:
    """Wrapper edge-tts + pygame untuk output suara Atlas."""

    def __init__(self, voice: str = TTS_VOICE) -> None:
        self.voice = voice
        self._tmpfile = os.path.join(tempfile.gettempdir(), "atlas_tts_out.mp3")

    def ucapkan(self, teks: str, potong: bool = True) -> None:
        """Ucapkan teks secara sinkron (blokir sampai selesai)."""
        if not teks.strip():
            return
        teks_bersih = format_untuk_suara(teks)
        if potong:
            teks_bersih = potong_untuk_suara(teks_bersih)
        print(f"\n  [ATLAS] {teks_bersih}\n")
        try:
            asyncio.run(self._generate(teks_bersih))
            self._play()
        except Exception as e:
            # TTS gagal (mungkin offline) — sudah di-print di atas
            print(f"  [TTS ERROR] {e}")

    async def _generate(self, teks: str) -> None:
        tts = edge_tts.Communicate(teks, self.voice)
        await tts.save(self._tmpfile)

    def _play(self) -> None:
        if not os.path.exists(self._tmpfile):
            return
        if _PYGAME_OK:
            try:
                pygame.mixer.music.load(self._tmpfile)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
            except Exception as e:
                print(f"  [PLAY ERROR] {e}")
        else:
            # Fallback Windows: buka dengan default player
            os.startfile(self._tmpfile)
            time.sleep(2)


# ============================================================
# LISTENER (Whisper + VAD)
# ============================================================

class AtlasListener:
    """Mendengarkan wake word dan menangkap perintah via Whisper + VAD."""

    def __init__(self) -> None:
        print("  Memuat model Whisper tiny (wake word)...", flush=True)
        self.tiny = whisper.load_model("tiny")
        print("  [OK] Model tiny siap")

        print("  Memuat model Whisper base (transkripsi perintah)...", flush=True)
        self.base = whisper.load_model("base")
        print("  [OK] Model base siap")

        self.vad = webrtcvad.Vad(VAD_MODE)

    def rekam_detik(self, durasi: float) -> np.ndarray:
        """Rekam audio float32 selama `durasi` detik, return array 1D."""
        jumlah_frame = int(SAMPLE_RATE * durasi)
        audio = sd.rec(jumlah_frame, samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32")
        sd.wait()
        return audio.flatten()

    def cek_wake_word(self, audio: np.ndarray) -> bool:
        """Transcribe audio pendek dan cek apakah ada wake word."""
        try:
            hasil = self.tiny.transcribe(
                audio, language="id", fp16=False, condition_on_previous_text=False
            )
            teks = hasil.get("text", "").strip().lower()
            if teks:
                print(f"  [cek] '{teks}'")
            return any(kw in teks for kw in WAKE_KEYWORDS)
        except Exception:
            return False

    def tangkap_perintah(self) -> str:
        """
        Rekam perintah menggunakan VAD.
        Berhenti otomatis saat SILENCE_LIMIT detik hening setelah ada suara.
        Return teks transkripsi.
        """
        print("  [MIC] Mendengarkan perintah (berhenti otomatis saat diam)...", flush=True)

        frames_float: list[np.ndarray] = []
        hitung_hening  = 0
        ada_suara      = False
        maks_frame     = int(MAX_RECORD_SEC / CHUNK_DURATION)
        frame_hening   = int(SILENCE_LIMIT / CHUNK_DURATION)

        for _ in range(maks_frame):
            # Rekam chunk 30ms sebagai int16 untuk VAD
            chunk_int16 = sd.rec(
                CHUNK_SIZE, samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="int16"
            )
            sd.wait()

            is_speech = False
            try:
                is_speech = self.vad.is_speech(chunk_int16.tobytes(), SAMPLE_RATE)
            except Exception:
                pass

            # Konversi ke float32 untuk Whisper
            chunk_float = chunk_int16.astype(np.float32) / 32768.0
            frames_float.append(chunk_float.flatten())

            if is_speech:
                ada_suara = True
                hitung_hening = 0
            elif ada_suara:
                hitung_hening += 1
                if hitung_hening >= frame_hening:
                    print("  [MIC] Diam terdeteksi, berhenti rekam.", flush=True)
                    break

        if not frames_float or not ada_suara:
            return ""

        full_audio = np.concatenate(frames_float)
        print("  [ASR] Mentranskripsikan...", flush=True)
        try:
            hasil = self.base.transcribe(
                full_audio, language="id", fp16=False,
                condition_on_previous_text=False
            )
            return hasil.get("text", "").strip()
        except Exception as e:
            print(f"  [ASR ERROR] {e}")
            return ""


# ============================================================
# BRAIN (Ollama)
# ============================================================

class AtlasBrain:
    """Antarmuka ke Ollama (qwen3.5) dengan context history."""

    def __init__(self, context_dataset: str = "") -> None:
        self.client          = ollama.Client(host="http://localhost:11434")
        self.history: list   = []
        self.context_dataset = context_dataset
        self.system_prompt   = (
            "Kamu adalah Atlas, asisten AI suara untuk sistem intelijen UIX. "
            "Berbicara dalam Bahasa Indonesia yang natural dan singkat. "
            "Jawaban maksimal 3 kalimat karena ini output suara, bukan teks. "
            "Jangan gunakan markdown, bullet point, atau simbol apapun. "
            "Langsung ke inti jawaban tanpa basa-basi panjang.\n\n"
            + context_dataset
        )

    def think(self, user_input: str) -> str:
        """Kirim ke Ollama, strip <think>, return teks bersih."""
        self.history.append({"role": "user", "content": user_input})
        messages = [
            {"role": "system", "content": self.system_prompt}
        ] + self.history[-8:]

        jawaban = ""
        try:
            resp = self.client.chat(
                model=OLLAMA_MODEL,
                messages=messages,
                options={"temperature": 0.6, "num_predict": 180},
            )
            jawaban = resp["message"]["content"]
            jawaban = strip_think(jawaban)
        except Exception as e:
            jawaban = f"Maaf, ada masalah saat menghubungi Ollama: {str(e)[:80]}"

        self.history.append({"role": "assistant", "content": jawaban})
        return jawaban


# ============================================================
# ATLAS — KONTROLLER UTAMA
# ============================================================

class Atlas:
    """Orkestrator utama: wake word → intent → eksekusi → TTS."""

    def __init__(self) -> None:
        self.tts      = AtlasTTS()
        self.listener = AtlasListener()
        self.data     = AtlasData(verbose=True)
        self.brain    = AtlasBrain(context_dataset=self.data.ringkasan_untuk_llm())

    # ------------------------------------------------------------------
    # INTENT CLASSIFICATION
    # ------------------------------------------------------------------

    def _tentukan_intent(self, teks: str) -> tuple[str, dict]:
        """
        Klasifikasikan teks perintah.
        Return: (tipe_intent, extras_dict)
        Tipe: 'navigasi' | 'daftar_kasus' | 'detail_kasus' | 'cari_profil' |
              'berita_terbaru' | 'cari_berita' | 'peringatan' | 'status' |
              'klaster' | 'chat'
        """
        t = teks.lower().strip()

        # --- NAVIGASI ---
        for trigger in TRIGGER_NAVIGASI:
            if trigger in t:
                sisa = t[t.find(trigger) + len(trigger):].strip()
                for kw, path in PETA_HALAMAN.items():
                    if kw in sisa or kw in t:
                        return "navigasi", {"path": path, "nama": NAMA_HALAMAN.get(path, path)}
                # trigger ada tapi halaman tidak dikenali
                return "navigasi_tidak_jelas", {}

        # --- DAFTAR KASUS ---
        if re.search(r"(daftar kasus|ada kasus apa|kasus apa saja|list kasus|semua kasus)", t):
            return "daftar_kasus", {}

        # --- DETAIL KASUS ---
        m = re.search(
            r"(kasus|ceritakan|bacakan|info|detail).{0,20}"
            r"(kebakaran|pendanaan|propaganda|gudang|mencurigakan|burst|kasus-\S+)",
            t,
        )
        if m:
            query_kasus = m.group(2).strip()
            return "detail_kasus", {"query": query_kasus}

        # --- CARI PROFIL ---
        m = re.search(r"(siapa|cari profil|profil|info tentang|cek profil)\s+(.+)", t)
        if m:
            query_nama = m.group(2).strip()
            # Abaikan jika yang dicari adalah kata umum
            if query_nama not in {"itu", "ini", "dia", "mereka", "kasus", "berita"}:
                return "cari_profil", {"query": query_nama}

        # --- BERITA TERBARU ---
        if re.search(r"(berita terbaru|berita hari ini|berita terkini|baca berita|berita apa)", t):
            return "berita_terbaru", {}

        # --- CARI BERITA ---
        m = re.search(r"(cari berita|berita tentang|berita soal|berita mengenai)\s+(.+)", t)
        if m:
            return "cari_berita", {"query": m.group(2).strip()}

        # --- PERINGATAN ---
        if re.search(r"(peringatan aktif|alert aktif|ada peringatan|peringatan apa)", t):
            return "peringatan", {}

        # --- STATUS SISTEM ---
        if re.search(r"(status sistem|ringkasan|kondisi sistem|laporan sistem|overview data)", t):
            return "status", {}

        # --- KLASTER PESAN ---
        if re.search(r"(klaster|kluster|propaganda|narasi koordinasi|pesan terkoordinasi)", t):
            return "klaster", {}

        # --- FALLBACK CHAT ---
        return "chat", {}

    # ------------------------------------------------------------------
    # HANDLER PER INTENT
    # ------------------------------------------------------------------

    def _handle_navigasi(self, path: str, nama: str) -> None:
        url = UIX_BASE_URL + path
        self.tts.ucapkan(f"Membuka halaman {nama}.")
        print(f"  [NAV] {url}")
        try:
            webbrowser.open(url)
        except Exception as e:
            self.tts.ucapkan(f"Gagal membuka browser: {e}")

    def _handle_daftar_kasus(self) -> None:
        self.tts.ucapkan("Sedang mengambil daftar kasus dari dataset.")
        kasus_list = self.data.daftar_kasus()
        if not kasus_list:
            self.tts.ucapkan("Tidak ada kasus ditemukan di dataset.")
            return
        bagian = [f"Ada {len(kasus_list)} kasus di sistem."]
        for k in kasus_list:
            bagian.append(
                f"Kasus {k['id_kasus'].replace('kasus-', '').replace('-', ' ')}: "
                f"{k['judul']}, status {k.get('status', '?')}."
            )
        self.tts.ucapkan(" ".join(bagian), potong=False)

    def _handle_detail_kasus(self, query: str) -> None:
        self.tts.ucapkan(f"Sedang membaca detail kasus {query}.")
        detail = self.data.baca_detail_kasus(query)
        print(f"\n[DATA KASUS]\n{detail}\n")
        # Untuk suara, ambil bagian paling penting
        baris = [b for b in detail.split("\n") if b.strip()]
        ringkas = " ".join(baris[:6])
        self.tts.ucapkan(format_untuk_suara(ringkas), potong=True)

    def _handle_cari_profil(self, query: str) -> None:
        self.tts.ucapkan(f"Sedang mencari profil dengan nama {query}.")
        hasil = self.data.cari_profil(query, top_k=3)
        if not hasil:
            self.tts.ucapkan(f"Tidak ada profil yang cocok dengan nama {query}.")
            return
        bagian = [f"Ditemukan {len(hasil)} profil."]
        for p in hasil:
            bagian.append(
                f"{p['nama_lengkap']} dari {p.get('kota', '?')}, "
                f"{p.get('provinsi', '?')}. "
                f"{'Terkait kasus: ' + ', '.join(p.get('tautan_kasus', [])) if p.get('tautan_kasus') else 'Tidak terkait kasus.'}"
            )
        self.tts.ucapkan(" ".join(bagian), potong=False)

    def _handle_berita_terbaru(self) -> None:
        self.tts.ucapkan("Sedang membaca berita terbaru.")
        berita = self.data.baca_berita_terbaru(5)
        if not berita:
            self.tts.ucapkan("Tidak ada berita tersedia di dataset.")
            return
        bagian = [f"Lima berita terbaru berikut ini."]
        for i, b in enumerate(berita, 1):
            tgl = b.get("published_at", "")[:10]
            bagian.append(
                f"Berita {i}: {b['judul']}. "
                f"Kategori {b.get('kategori', '?')}, tanggal {tgl}."
            )
        self.tts.ucapkan(" ".join(bagian), potong=False)

    def _handle_cari_berita(self, query: str) -> None:
        self.tts.ucapkan(f"Sedang mencari berita tentang {query}.")
        hasil = self.data.cari_berita(query, top_k=3)
        if not hasil:
            self.tts.ucapkan(f"Tidak ada berita yang cocok dengan kata kunci {query}.")
            return
        bagian = [f"Ditemukan {len(hasil)} berita terkait {query}."]
        for b in hasil:
            bagian.append(
                f"{b['judul']}. "
                f"Kategori {b.get('kategori', '?')}, "
                f"lokasi {b.get('lokasi', '?')}."
            )
        self.tts.ucapkan(" ".join(bagian), potong=False)

    def _handle_peringatan(self) -> None:
        self.tts.ucapkan("Sedang membaca peringatan aktif prioritas tertinggi.")
        peringatan = self.data.baca_peringatan_aktif(5)
        if not peringatan:
            self.tts.ucapkan("Tidak ada peringatan aktif di dataset.")
            return
        bagian = [f"Ada {len(peringatan)} peringatan prioritas teratas."]
        for p in peringatan:
            kasus_id = p.get("id_kasus", "?").replace("kasus-", "").replace("-", " ")
            bagian.append(
                f"Keparahan {p.get('tingkat_keparahan', '?')}, kasus {kasus_id}: "
                f"{p.get('deskripsi', '-')}"
            )
        self.tts.ucapkan(" ".join(bagian), potong=False)

    def _handle_status(self) -> None:
        self.tts.ucapkan("Sedang membaca ringkasan sistem.")
        ringkasan = self.data.ringkas_sistem()
        print(f"\n[STATUS SISTEM]\n{ringkasan}\n")
        self.tts.ucapkan(ringkasan, potong=False)

    def _handle_klaster(self) -> None:
        self.tts.ucapkan("Sedang membaca klaster pesan terkoordinasi.")
        klaster = self.data.baca_klaster_kritis(3)
        if not klaster:
            self.tts.ucapkan("Tidak ada data klaster pesan di dataset.")
            return
        bagian = [f"Ada {len(klaster)} klaster pesan koordinasi terdeteksi."]
        for kp in klaster:
            bagian.append(
                f"Klaster dengan frasa: {kp['frasa_kanonik'][:60]}. "
                f"Kemiripan copy: {kp['kemiripan_copy']:.0%}, "
                f"jumlah posting: {kp.get('jumlah_posting', '?')}."
            )
        self.tts.ucapkan(" ".join(bagian), potong=False)

    def _handle_chat(self, teks: str) -> None:
        self.tts.ucapkan("Oke, lagi berpikir sebentar.")
        print("  [THINK] Kirim ke Ollama...", flush=True)

        # Jalankan Ollama di thread terpisah dengan timeout
        result_container: list[str] = []

        def _worker():
            result_container.append(self.brain.think(teks))

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

        # Beri tahu pengguna tiap 10 detik jika masih loading
        elapsed = 0
        interval = 10
        while t.is_alive():
            t.join(timeout=interval)
            elapsed += interval
            if t.is_alive():
                if elapsed < OLLAMA_TIMEOUT:
                    self.tts.ucapkan(f"Masih memproses, sudah {elapsed} detik. Mohon tunggu.")
                else:
                    self.tts.ucapkan(
                        "Waktu tunggu Ollama habis. "
                        "Coba lagi atau periksa apakah Ollama sudah berjalan."
                    )
                    return

        jawaban = result_container[0] if result_container else "Maaf, tidak ada respons."
        print(f"  [OLLAMA] {jawaban[:120]}...")
        self.tts.ucapkan(jawaban)

    def _handle_navigasi_tidak_jelas(self) -> None:
        daftar = ", ".join(sorted(set(PETA_HALAMAN.keys()))[:8])
        self.tts.ucapkan(
            f"Halaman tidak dikenali. "
            f"Halaman yang tersedia antara lain: {daftar}, dan lainnya."
        )

    # ------------------------------------------------------------------
    # PROSES PERINTAH
    # ------------------------------------------------------------------

    def proses(self, teks: str) -> None:
        if not teks.strip():
            self.tts.ucapkan("Maaf, aku tidak menangkap perintahmu. Coba lagi?")
            return

        print(f"\n  [USER] {teks}")
        intent, extras = self._tentukan_intent(teks)
        print(f"  [INTENT] {intent} | extras: {extras}")

        handlers = {
            "navigasi":             lambda: self._handle_navigasi(extras["path"], extras["nama"]),
            "navigasi_tidak_jelas": lambda: self._handle_navigasi_tidak_jelas(),
            "daftar_kasus":         lambda: self._handle_daftar_kasus(),
            "detail_kasus":         lambda: self._handle_detail_kasus(extras.get("query", "")),
            "cari_profil":          lambda: self._handle_cari_profil(extras.get("query", "")),
            "berita_terbaru":       lambda: self._handle_berita_terbaru(),
            "cari_berita":          lambda: self._handle_cari_berita(extras.get("query", "")),
            "peringatan":           lambda: self._handle_peringatan(),
            "status":               lambda: self._handle_status(),
            "klaster":              lambda: self._handle_klaster(),
            "chat":                 lambda: self._handle_chat(teks),
        }

        handler = handlers.get(intent, lambda: self._handle_chat(teks))
        try:
            handler()
        except Exception as e:
            msg = f"Terjadi kesalahan saat menjalankan perintah: {str(e)[:100]}"
            print(f"  [ERR] {e}")
            self.tts.ucapkan(msg)

    # ------------------------------------------------------------------
    # LOOP UTAMA
    # ------------------------------------------------------------------

    def mulai(self) -> None:
        sep = "=" * 52
        print(sep)
        print("  🤖  ATLAS — UIX Intelligence Voice Assistant")
        print(f"  Model LLM : {OLLAMA_MODEL}")
        print(f"  TTS Voice : {TTS_VOICE}")
        print(f"  UIX URL   : {UIX_BASE_URL}")
        print(f"  Wake word : 'Hey Atlas'")
        print(sep)
        print("  ⏳ Mendengarkan wake word... (window 3 detik)")
        print(sep)

        while True:
            try:
                audio = self.listener.rekam_detik(WINDOW_DURASI)
                terdeteksi = self.listener.cek_wake_word(audio)

                if terdeteksi:
                    print("\n  🔔  Wake word terdeteksi!")
                    self.tts.ucapkan("Ya?")

                    print("  🎙️  Menunggu perintahmu...", flush=True)
                    teks_perintah = self.listener.tangkap_perintah()

                    if not teks_perintah.strip():
                        self.tts.ucapkan("Tidak ada suara terdeteksi. Panggil lagi bila perlu.")
                        print(sep)
                        print("  ⏳ Kembali mendengarkan...")
                        print(sep)
                        continue

                    self.proses(teks_perintah)
                    print()
                    print(sep)
                    print("  ⏳ Kembali mendengarkan...")
                    print(sep)

            except KeyboardInterrupt:
                print("\n\n  [ATLAS] Sampai jumpa! Atlas dimatikan.")
                self.tts.ucapkan("Sampai jumpa.")
                sys.exit(0)
            except Exception as e:
                print(f"  [LOOP ERROR] {e}")
                time.sleep(1)


# ============================================================
# ENTRY POINT
# ============================================================

def main() -> None:
    print()
    print("=" * 52)
    print("  Memulai Atlas Voice Assistant — UIX")
    print("=" * 52)
    print()
    print("  [1/3] Memuat dataset UIX...")
    # Dataset dimuat di dalam Atlas.__init__(), tapi kita print dulu header-nya
    print()

    # Cek Ollama aktif sebelum lanjut
    print("  [2/3] Memeriksa koneksi Ollama...")
    try:
        client_test = ollama.Client(host="http://localhost:11434")
        client_test.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": "ping"}],
            options={"num_predict": 3},
        )
        print(f"  [OK] Ollama terhubung, model {OLLAMA_MODEL} siap")
    except Exception as e:
        print(f"  [WARN] Ollama tidak merespons: {e}")
        print("  Atlas tetap berjalan tapi fitur chat tidak akan berfungsi.")
        print("  Jalankan: ollama serve (di terminal lain)")
    print()

    print("  [3/3] Inisialisasi komponen suara (Whisper + TTS)...")
    print()

    atlas = Atlas()

    print()
    print("  Semua komponen siap. Atlas aktif!")
    print()
    atlas.mulai()


if __name__ == "__main__":
    main()
