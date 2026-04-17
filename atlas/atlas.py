"""
atlas.py — Atlas Voice Assistant untuk UIX Intelligence System

Perintah suara: wake word "hey atlas" → perintah → eksekusi
Bisa membuka halaman UIX, membaca kasus/profil/berita, dan chat Ollama.

Jalankan: python atlas.py
Pastikan Ollama sudah jalan: ollama serve
"""

# ============================================================
# BOOTSTRAP — Pastikan selalu jalan di venv UIX
# ============================================================
import sys, os as _os, subprocess as _sub
_VENV_PY = _os.path.normpath(
    _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                  "..", ".venv", "Scripts", "python.exe")
)
if _os.path.exists(_VENV_PY) and \
   _os.path.normcase(_os.path.abspath(sys.executable)) != _os.path.normcase(_VENV_PY):
    sys.exit(_sub.call([_VENV_PY] + sys.argv))

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
import warnings
import webbrowser
from pathlib import Path

# Suppress torchcodec/FFmpeg warning dari pyannote (bukan masalah — kita pakai numpy array)
warnings.filterwarnings("ignore", category=UserWarning, module=r"pyannote\.audio\.core\.io")
warnings.filterwarnings("ignore", message=".*torchcodec.*")

import numpy as np
import sounddevice as sd

# -- init pygame duluan sebelum whisper supaya tidak ada konflik --
try:
    import pygame
    pygame.mixer.init()
    _PYGAME_OK = True
except Exception:
    _PYGAME_OK = False

import torch          # type: ignore
import whisper         # type: ignore
import edge_tts        # type: ignore
try:
    import webrtcvad       # type: ignore
    _VAD_OK = True
except ImportError:
    _VAD_OK = False
import ollama          # type: ignore

try:
    from pyannote.audio import Model as PyannoteModel, Inference as PyannoteInference  # type: ignore
    _PYANNOTE_OK = True
except Exception:
    _PYANNOTE_OK = False

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
TTS_VOICE       = "id-ID-ArdiNeural"
OLLAMA_MODEL    = "qwen3.5:latest"              # sesuaikan dengan ollama list
UIX_BASE_URL    = "http://localhost:5173"
SILENCE_LIMIT   = 1.8                           # detik silence untuk stop rekam
MAX_RECORD_SEC  = 12                            # maksimum durasi rekam perintah
OLLAMA_TIMEOUT  = 45                            # detik timeout Ollama
VAD_MODE        = 2                             # 0-3, makin tinggi makin agresif
# Sliding window wake word
SLIDE_CHUNK_SEC  = 3   # durasi setiap potongan rekaman
SLIDE_WINDOW_SEC = 3.0   # total buffer yang dievaluasi Whisper (harus ≥ 1 detik)
SLIDE_STEP_SEC   = 1.5   # seberapa sering evaluasi — 50% overlap
# Speaker verification (pyannote)
# Isi HF_TOKEN dengan token HuggingFace kamu.
# Cara dapat token: https://huggingface.co/settings/tokens
# Pastikan sudah accept terms di: https://huggingface.co/pyannote/embedding
HF_TOKEN         = ""      # isi token HuggingFace di sini
SPEAKER_THRESHOLD = 0.75                                        # 0-1, makin tinggi makin ketat
ENROLL_DURASI    = 10.0                                         # detik perekaman enrollment
EMBEDDING_DIR   = Path(__file__).parent / "embeddings"          # folder berisi {nama}.npy
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
# SPEAKER VERIFIER (pyannote)
# ============================================================

class SpeakerVerifier:
    """
    Verifikasi multi-speaker berbasis embedding pyannote.
    Setiap orang didaftarkan via mode interaktif `--enroll`.
    Embedding disimpan di atlas/embeddings/{nama}.npy
    """

    def __init__(self, hf_token: str) -> None:
        if not _PYANNOTE_OK:
            raise RuntimeError("pyannote.audio tidak terpasang. Jalankan: pip install pyannote.audio")
        print("  Memuat model pyannote speaker embedding...", flush=True)
        model = PyannoteModel.from_pretrained("pyannote/embedding", token=hf_token)
        self._inferensi = PyannoteInference(model, window="whole")
        print("  [OK] Model speaker embedding siap", flush=True)

        # Muat semua embedding yang sudah terdaftar
        EMBEDDING_DIR.mkdir(parents=True, exist_ok=True)
        self._embeddings: dict[str, np.ndarray] = {}
        self._muat_semua()

    def _muat_semua(self) -> None:
        """Muat ulang semua file .npy dari EMBEDDING_DIR ke memori."""
        self._embeddings.clear()
        for f in sorted(EMBEDDING_DIR.glob("*.npy")):
            nama = f.stem
            self._embeddings[nama] = np.load(str(f))
            print(f"  [OK] Embedding '{nama}' dimuat", flush=True)
        if not self._embeddings:
            print("  [WARN] Belum ada speaker terdaftar. Jalankan: python atlas/atlas.py --enroll", flush=True)
        else:
            print(f"  [OK] Total {len(self._embeddings)} speaker terdaftar: {', '.join(self._embeddings)}", flush=True)

    def daftar_terdaftar(self) -> list[str]:
        """Return daftar nama speaker terdaftar."""
        return list(self._embeddings.keys())

    def ekstrak(self, audio: np.ndarray) -> np.ndarray:
        """Ekstrak embedding dari audio numpy float32 1D."""
        waveform = torch.tensor(audio).unsqueeze(0)  # (1, T)
        embedding = self._inferensi({"waveform": waveform, "sample_rate": SAMPLE_RATE})
        return np.array(embedding).flatten()

    def enroll(self, nama: str, audio: np.ndarray) -> None:
        """Simpan embedding untuk nama speaker tertentu."""
        nama_bersih = re.sub(r"[^a-zA-Z0-9_-]", "_", nama.strip().lower())
        emb = self.ekstrak(audio)
        path = EMBEDDING_DIR / f"{nama_bersih}.npy"
        np.save(str(path), emb)
        self._embeddings[nama_bersih] = emb
        print(f"  [OK] Embedding '{nama_bersih}' disimpan ke {path}", flush=True)

    def hapus(self, nama: str) -> bool:
        """Hapus embedding speaker. Return True jika berhasil."""
        nama_bersih = nama.strip().lower()
        path = EMBEDDING_DIR / f"{nama_bersih}.npy"
        if path.exists():
            path.unlink()
            self._embeddings.pop(nama_bersih, None)
            return True
        return False

    def verifikasi(self, audio: np.ndarray) -> tuple[bool, float, str | None]:
        """
        Cek apakah audio berasal dari salah satu speaker terdaftar.
        Return: (cocok, skor_tertinggi, nama_speaker | None)
        Jika belum ada yang terdaftar, selalu return (True, 1.0, None).
        """
        if not self._embeddings:
            return True, 1.0, None
        emb = self.ekstrak(audio)
        skor_terbaik = -1.0
        nama_terbaik = None
        for nama, ref in self._embeddings.items():
            skor = float(np.dot(emb, ref) / (np.linalg.norm(emb) * np.linalg.norm(ref) + 1e-9))
            if skor > skor_terbaik:
                skor_terbaik = skor
                nama_terbaik = nama
        cocok = skor_terbaik >= SPEAKER_THRESHOLD
        return cocok, skor_terbaik, nama_terbaik if cocok else None


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

    def __init__(self, speaker_verifier: "SpeakerVerifier | None" = None) -> None:
        print("  Memuat model Whisper large (wake word + transkripsi)...", flush=True)
        self.turbo = whisper.load_model("large")
        print("  [OK] Model large siap (large-v3)")

        self.vad = webrtcvad.Vad(VAD_MODE) if _VAD_OK else None
        if not _VAD_OK:
            print("  [WARN] webrtcvad tidak tersedia — VAD dinonaktifkan, stop rekam pakai durasi maksimum", flush=True)
        self.speaker = speaker_verifier

    def rekam_detik(self, durasi: float) -> np.ndarray:
        """Rekam audio float32 selama `durasi` detik, return array 1D."""
        jumlah_frame = int(SAMPLE_RATE * durasi)
        audio = sd.rec(jumlah_frame, samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32")
        sd.wait()
        return audio.flatten()

    def dengarkan_sliding(self) -> None:
        """
        Sliding window wake word detection.
        Rekam chunk 0.5 detik terus-menerus, simpan buffer 3 detik terakhir.
        Evaluasi Whisper setiap 1.5 detik (50% overlap) → wake word di
        batas dua window fixed tidak lagi terlewat.
        Blokir sampai wake word terdeteksi, lalu return.
        """
        from collections import deque

        chunk_samples = int(SAMPLE_RATE * SLIDE_CHUNK_SEC)
        n_window = round(SLIDE_WINDOW_SEC / SLIDE_CHUNK_SEC)  # 6 chunks = 3 det
        n_step   = round(SLIDE_STEP_SEC   / SLIDE_CHUNK_SEC)  # 3 chunks = 1.5 det

        buffer: deque[np.ndarray] = deque(maxlen=n_window)
        sejak_evaluasi = 0

        while True:
            chunk = sd.rec(chunk_samples, samplerate=SAMPLE_RATE,
                           channels=CHANNELS, dtype="float32")
            sd.wait()
            buffer.append(chunk.flatten())
            sejak_evaluasi += 1

            # Evaluasi setiap n_step chunk baru DAN buffer sudah penuh
            if sejak_evaluasi >= n_step and len(buffer) == n_window:
                sejak_evaluasi = 0
                audio = np.concatenate(list(buffer))
                if self.cek_wake_word(audio):
                    return  # wake word terdeteksi → kembali ke mulai()

    def cek_wake_word(self, audio: np.ndarray) -> bool:
        """Cek speaker dulu (jika aktif), lalu transcribe untuk wake word."""
        # Lapis 1: verifikasi speaker sebelum Whisper (hemat compute)
        if self.speaker is not None:
            try:
                cocok, skor, nama_spk = self.speaker.verifikasi(audio)
                print(f"  [speaker] skor={skor:.3f} {nama_spk or ''} — {'✓ pemilik' if cocok else '✗ bukan pemilik, dilewati'}", flush=True)
                if not cocok:
                    return False
            except Exception as e:
                print(f"  [speaker ERROR] {e} — lanjut tanpa verifikasi", flush=True)

        # Lapis 2: transkripsi Whisper
        try:
            hasil = self.turbo.transcribe(
                audio,
                language="id",
                fp16=False,
                condition_on_previous_text=False,
            )
            teks = hasil.get("text", "").strip().lower()
            print(f"  [mic] '{teks}'", flush=True)
            return any(kw in teks for kw in WAKE_KEYWORDS)
        except Exception as e:
            print(f"  [cek ERROR] {e}", flush=True)
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
                if self.vad is not None:
                    is_speech = self.vad.is_speech(chunk_int16.tobytes(), SAMPLE_RATE)
                else:
                    # Tanpa VAD: anggap semua ada suara, stop hanya saat max durasi
                    is_speech = True
            except Exception:
                is_speech = True

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
            hasil = self.turbo.transcribe(
                full_audio,
                language="id",
                fp16=False,
                condition_on_previous_text=False,
            )
            teks = hasil.get("text", "").strip()
            print(f"  [ASR] Hasil: '{teks}'")
            return teks
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
            "Langsung ke inti jawaban tanpa basa-basi panjang. /no_think\n\n"
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
                think=False,
                options={"temperature": 0.6, "num_predict": 256},
            )
            jawaban = resp.message.content.strip()
        except Exception as e:
            jawaban = f"Maaf, ada masalah saat menghubungi Ollama: {str(e)[:80]}"

        self.history.append({"role": "assistant", "content": jawaban})
        return jawaban


# ============================================================
# ATLAS — KONTROLLER UTAMA
# ============================================================

class Atlas:
    """Orkestrator utama: wake word → intent → eksekusi → TTS."""

    def __init__(self, speaker_verifier: "SpeakerVerifier | None" = None) -> None:
        self.tts      = AtlasTTS()
        self.listener = AtlasListener(speaker_verifier=speaker_verifier)
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
        print(f"  Mode      : sliding window ({SLIDE_WINDOW_SEC}s buffer, {SLIDE_STEP_SEC}s step)")
        print(sep)
        print("  ⏳ Mendengarkan wake word secara kontinu...")
        print(sep)
        print()

        while True:
            try:
                # Sliding window — blokir sampai 'hey atlas' terdeteksi
                self.listener.dengarkan_sliding()

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

def _buat_speaker_verifier() -> "SpeakerVerifier | None":
    """Coba buat SpeakerVerifier jika HF_TOKEN diisi dan pyannote tersedia."""
    if not HF_TOKEN:
        return None
    if not _PYANNOTE_OK:
        print("  [WARN] pyannote.audio tidak tersedia. Speaker verification dinonaktifkan.")
        return None
    try:
        return SpeakerVerifier(HF_TOKEN)
    except Exception as e:
        print(f"  [WARN] Gagal memuat speaker verifier: {e}")
        return None


def mode_enroll() -> None:
    """Mode enrollment interaktif: daftarkan satu atau lebih speaker."""
    if not HF_TOKEN:
        print("\n  [ERROR] HF_TOKEN belum diisi di atlas.py!")
        print("  Isi konstanta HF_TOKEN dengan token HuggingFace kamu.")
        sys.exit(1)
    if not _PYANNOTE_OK:
        print("\n  [ERROR] pyannote.audio tidak terpasang.")
        print("  Jalankan: pip install pyannote.audio")
        sys.exit(1)

    print()
    print("=" * 52)
    print("  ATLAS — Pendaftaran Speaker")
    print("=" * 52)
    verifier = SpeakerVerifier(HF_TOKEN)
    tts = AtlasTTS()

    while True:
        terdaftar = verifier.daftar_terdaftar()
        print()
        if terdaftar:
            print(f"  Speaker terdaftar ({len(terdaftar)}): {', '.join(terdaftar)}")
        else:
            print("  Belum ada speaker terdaftar.")
        print()
        print("  Pilihan:")
        print("  [1] Daftarkan speaker baru")
        print("  [2] Hapus speaker")
        print("  [3] Selesai")
        print()
        pilihan = input("  Pilih (1/2/3): ").strip()

        if pilihan == "1":
            nama = input("  Nama speaker: ").strip()
            if not nama:
                print("  Nama tidak boleh kosong.")
                continue
            nama_key = re.sub(r"[^a-zA-Z0-9_-]", "_", nama.lower())
            if nama_key in terdaftar:
                timpa = input(f"  '{nama_key}' sudah terdaftar. Timpa? (y/n): ").strip().lower()
                if timpa != "y":
                    continue

            tts.ucapkan(
                f"Siap merekam suara {nama} selama {int(ENROLL_DURASI)} detik. "
                "Bicara dengan normal. Mulai sekarang."
            )
            print(f"  Merekam {nama} selama {int(ENROLL_DURASI)} detik...")

            jumlah_frame = int(SAMPLE_RATE * ENROLL_DURASI)
            audio = sd.rec(jumlah_frame, samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32")
            sd.wait()
            audio = audio.flatten()

            print("  Merekam selesai. Mengekstrak embedding...")
            verifier.enroll(nama, audio)
            tts.ucapkan(f"Suara {nama} berhasil didaftarkan.")

        elif pilihan == "2":
            if not terdaftar:
                print("  Tidak ada speaker untuk dihapus.")
                continue
            nama = input(f"  Nama speaker yang dihapus ({', '.join(terdaftar)}): ").strip().lower()
            if verifier.hapus(nama):
                print(f"  [OK] '{nama}' dihapus.")
            else:
                print(f"  Speaker '{nama}' tidak ditemukan.")

        elif pilihan == "3":
            print()
            print(f"  Selesai. Speaker terdaftar: {', '.join(verifier.daftar_terdaftar()) or 'tidak ada'}")
            print("  Jalankan: python atlas/atlas.py")
            break
        else:
            print("  Pilihan tidak valid.")


def main() -> None:
    # Mode enrollment
    if len(sys.argv) > 1 and sys.argv[1] == "--enroll":
        mode_enroll()
        return

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

    # Speaker verification (opsional)
    speaker_verifier = _buat_speaker_verifier()
    if speaker_verifier is not None:
        terdaftar = speaker_verifier.daftar_terdaftar()
        if terdaftar:
            status_spk = f"aktif — {len(terdaftar)} speaker: {', '.join(terdaftar)}"
        else:
            status_spk = "aktif — BELUM ada speaker. Jalankan: python atlas/atlas.py --enroll"
    else:
        status_spk = "nonaktif (isi HF_TOKEN untuk mengaktifkan)"
    atlas = Atlas(speaker_verifier=speaker_verifier)

    print()
    print("  Semua komponen siap. Atlas aktif!")
    print(f"  Speaker verif : {status_spk}")
    print()
    atlas.mulai()


if __name__ == "__main__":
    main()
