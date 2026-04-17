"""
atlas_web.py — Atlas LIVE v2  (faster-whisper + SSE streaming)

Pipeline baru:
  1. Browser VAD → stop rekam → POST /api/listen  → JSON {teks}   (fast ASR)
  2. Browser buka EventSource /api/stream?teks=...
       ├─ event:text  → typewriter karakter-per-karakter
       ├─ event:audio → base64 MP3 per kalimat → AudioContext queue (gapless)
       ├─ event:nav   → buka URL UIX
       └─ event:done  → tutup SSE → auto-listen loop

Jalankan: python atlas/atlas_web.py
Buka    : http://localhost:7860
"""

# ============================================================
# BOOTSTRAP — otomatis pakai venv
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
import os, re, sys, json, time, asyncio, base64, tempfile, threading, warnings, random
import webbrowser
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=False)

_tts_pool = ThreadPoolExecutor(max_workers=3)   # TTS jalan paralel

warnings.filterwarnings("ignore")

from faster_whisper import WhisperModel
import ollama
import edge_tts
from flask import Flask, request, jsonify, render_template, Response, stream_with_context, send_from_directory
from flask_cors import CORS

sys.path.insert(0, str(Path(__file__).parent))
from atlas_data import AtlasData

# ============================================================
# CONFIG
# ============================================================
# Ollama: default lokal. Cloud hanya aktif jika diminta eksplisit.
_OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "").strip()
_OLLAMA_MODE = os.environ.get("ATLAS_OLLAMA_MODE", "local").strip().lower()
_OLLAMA_CLOUD = (
  _OLLAMA_MODE == "cloud"
  and bool(_OLLAMA_API_KEY)
  and not _OLLAMA_API_KEY.startswith("PASTE")
)

OLLAMA_MODEL  = os.environ.get(
  "ATLAS_OLLAMA_MODEL",
  "gpt-oss:120b" if _OLLAMA_CLOUD else "qwen3.5:latest",
).strip() or ("gpt-oss:120b" if _OLLAMA_CLOUD else "qwen3.5:latest")
TTS_VOICE     = os.environ.get("ATLAS_TTS_VOICE", "id-ID-ArdiNeural").strip() or "id-ID-ArdiNeural"
TTS_MODE      = os.environ.get("ATLAS_TTS_MODE", "edge").strip().lower() or "edge"
WHISPER_MODEL = os.environ.get("ATLAS_WHISPER_MODEL", "turbo").strip() or "turbo"
WHISPER_DEVICE = os.environ.get("ATLAS_WHISPER_DEVICE", "cpu").strip() or "cpu"
WHISPER_COMPUTE_TYPE = os.environ.get("ATLAS_WHISPER_COMPUTE_TYPE", "int8").strip() or "int8"
WHISPER_PRELOAD = os.environ.get("ATLAS_WHISPER_PRELOAD", "1").strip().lower() in {"1", "true", "yes", "on"}
WHISPER_CPU_SAFE = os.environ.get("ATLAS_WHISPER_CPU_SAFE", "1").strip().lower() in {"1", "true", "yes", "on"}
WHISPER_BEAM_SIZE = int(os.environ.get("ATLAS_WHISPER_BEAM_SIZE", "1") or "1")
WHISPER_BEST_OF = int(os.environ.get("ATLAS_WHISPER_BEST_OF", "1") or "1")
WHISPER_VAD_MIN_SILENCE_MS = int(os.environ.get("ATLAS_WHISPER_VAD_MIN_SILENCE_MS", "220") or "220")
WEB_PORT      = 7860
SENTENCE_MIN  = 8    # min karakter sebelum TTS per kalimat
MODEL_DIR     = Path(__file__).parent / "models"
SESSION_MEMORY_DIR = Path(__file__).parent.parent / "runtime_state"
SESSION_MEMORY_FILE = SESSION_MEMORY_DIR / "atlas_session_memory.json"

# Piper model Indonesia
PIPER_MODEL   = MODEL_DIR / "id_ID-news_tts-medium.onnx"
PIPER_CONFIG  = MODEL_DIR / "id_ID-news_tts-medium.onnx.json"
PIPER_URL     = ("https://huggingface.co/rhasspy/piper-voices/resolve/main"
                 "/id/id_ID/news_tts/medium")

# ============================================================
# GLOBAL (lazy load)
# ============================================================
_whisper_model  = None
_whisper_model_name = "belum dimuat"
_whisper_effective_target = "belum ditentukan"
_whisper_loading = False
_whisper_error = ""
_atlas_data     = None
_lock_w         = threading.Lock()
_sesi_konteks: dict[str, dict] = {}
_lock_sesi_konteks = threading.Lock()

# Filler phrases — pre-generate audio saat startup supaya instan
_FILLER_PHRASES = [
    "Hmm, biarkan saya berpikir sejenak ya...",
    "Baik, saya sedang menganalisis pertanyaan kamu, sebentar ya...",
    "Oke, satu momen, saya sedang memeriksa data yang relevan...",
    "Saya sedang memproses informasinya, mohon tunggu sebentar ya...",
    "Hmm, pertanyaan yang menarik, biarkan saya cek dulu ya...",
    "Baik baik, saya pikirkan dulu, sebentar ya...",
]
_filler_audio: list[str] = []   # list of base64-encoded audio, diisi saat startup

_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U00002700-\U000027BF"
    "]+",
    flags=re.UNICODE,
)


def _hapus_emoji(teks: str) -> str:
    if not teks:
        return ""
    return _EMOJI_RE.sub("", teks)


def _get_ollama_client() -> ollama.Client:
    """Return Ollama client — cloud jika API key ada, lokal jika tidak."""
    if _OLLAMA_CLOUD:
        return ollama.Client(
            host="https://ollama.com",
      headers={"Authorization": f"Bearer {_OLLAMA_API_KEY}"},
        )
    return ollama.Client(host="http://localhost:11434")


def _get_whisper():
    global _whisper_model, _whisper_model_name, _whisper_effective_target, _whisper_loading, _whisper_error
    if _whisper_model is None:
        with _lock_w:
            if _whisper_model is None:
                _whisper_loading = True
                _whisper_error = ""
                model_target = WHISPER_MODEL
                if WHISPER_CPU_SAFE and WHISPER_DEVICE == "cpu" and WHISPER_MODEL == "turbo":
                    model_target = "small"
                    print("  [INFO] Turbo di CPU terdeteksi, mode aman aktif: pakai small untuk respons stabil.", flush=True)

                _whisper_effective_target = model_target
                kandidat = [model_target, "small"]
                if WHISPER_MODEL == "small":
                    kandidat = ["small"]
                kandidat = list(dict.fromkeys(kandidat))

                error_terakhir: Exception | None = None
                for nama_model in kandidat:
                    try:
                        print(f"  [LOAD] Memuat faster-whisper {nama_model}...", flush=True)
                        _whisper_model = WhisperModel(
                            nama_model,
                            device=WHISPER_DEVICE,
                            compute_type=WHISPER_COMPUTE_TYPE,
                            download_root=MODEL_DIR,
                        )
                        _whisper_model_name = nama_model
                        print(f"  [OK]   Whisper siap ({nama_model})", flush=True)
                        break
                    except Exception as e:
                        error_terakhir = e
                        _whisper_error = str(e)[:200]
                        print(f"  [WARN] Gagal memuat model {nama_model}: {str(e)[:120]}", flush=True)

                if _whisper_model is None:
                    _whisper_loading = False
                    raise RuntimeError(f"Semua model Whisper gagal dimuat: {error_terakhir}")
                _whisper_loading = False
    return _whisper_model


def _preload_whisper_async():
    def _runner():
        try:
            _get_whisper()
        except Exception as e:
            print(f"  [WARN] Preload Whisper gagal: {str(e)[:160]}", flush=True)

    t = threading.Thread(target=_runner, daemon=True)
    t.start()


def _get_data():
    global _atlas_data
    if _atlas_data is None:
        _atlas_data = AtlasData(verbose=True)
    return _atlas_data


def _muat_memori_sesi():
    global _sesi_konteks
    with _lock_sesi_konteks:
        try:
            SESSION_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
            if not SESSION_MEMORY_FILE.exists():
                _sesi_konteks = {}
                return
            data = json.loads(SESSION_MEMORY_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                _sesi_konteks = {str(k): v for k, v in data.items() if isinstance(v, dict)}
            else:
                _sesi_konteks = {}
        except Exception as e:
            print(f"  [WARN] Gagal memuat memori sesi: {str(e)[:140]}", flush=True)
            _sesi_konteks = {}


def _simpan_memori_sesi():
    with _lock_sesi_konteks:
        try:
            SESSION_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
            temp_file = SESSION_MEMORY_FILE.with_suffix(".tmp")
            temp_file.write_text(
                json.dumps(_sesi_konteks, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temp_file.replace(SESSION_MEMORY_FILE)
        except Exception as e:
            print(f"  [WARN] Gagal menyimpan memori sesi: {str(e)[:140]}", flush=True)


def _ambil_sesi_konteks(session_id: str) -> dict:
    with _lock_sesi_konteks:
        konteks = _sesi_konteks.setdefault(session_id, {})
        return dict(konteks)


def _update_sesi_konteks(session_id: str, **kwargs):
    with _lock_sesi_konteks:
        konteks = _sesi_konteks.setdefault(session_id, {})
        for k, v in kwargs.items():
            if v is not None:
                konteks[k] = v
        konteks["updated_at"] = datetime.utcnow().isoformat() + "Z"
    _simpan_memori_sesi()


def _reset_sesi_konteks(session_id: str):
    with _lock_sesi_konteks:
        if session_id in _sesi_konteks:
            _sesi_konteks.pop(session_id, None)
    _simpan_memori_sesi()


_muat_memori_sesi()


# ============================================================
# INTENT ENGINE
# ============================================================
UIX_BASE_URL = "http://localhost:5173"

PETA_HALAMAN = {
    "beranda": "/", "overview": "/", "ikhtisar": "/", "home": "/",
    "peringatan": "/alert-center", "alert": "/alert-center", "pusat peringatan": "/alert-center",
    "insiden": "/incident-queue", "antrean": "/incident-queue",
    "peta": "/map-intelligence", "map": "/map-intelligence",
    "pencarian": "/search", "cari": "/search", "search": "/search",
    "link analysis": "/link-analysis", "jaringan": "/link-analysis",
    "timeline": "/timeline", "kronologi": "/timeline",
    "narasi": "/narrative", "tren": "/narrative", "narrative": "/narrative",
    "kanvas": "/canvas", "investigasi": "/canvas", "canvas": "/canvas",
    "konten": "/content", "bukti": "/content", "content": "/content",
    "workspace": "/case-workspace", "kasus workspace": "/case-workspace",
    "briefing": "/briefing",
    "fusion": "/fusion", "fusion board": "/fusion",
    "admin": "/admin", "sistem": "/admin", "audit": "/admin",
}
NAMA_HALAMAN = {
    "/": "Ikhtisar", "/alert-center": "Pusat Peringatan",
    "/incident-queue": "Antrean Insiden", "/map-intelligence": "Intelijen Peta",
    "/search": "Pencarian dan Penemuan", "/link-analysis": "Analisis Jaringan",
    "/timeline": "Timeline Kejadian", "/narrative": "Narasi dan Tren",
    "/canvas": "Kanvas Investigasi", "/content": "Konten dan Bukti",
    "/case-workspace": "Kasus Workspace", "/briefing": "Briefing dan Laporan",
    "/fusion": "Fusion Board", "/admin": "Admin dan Audit Sistem",
}
TRIGGER_NAV = ["buka", "pergi ke", "tampilkan", "navigasi ke", "ke halaman",
               "pindah ke", "lihat halaman", "buka halaman"]


def _infer_halaman_otomatis(teks: str, sesi_konteks: dict | None = None) -> tuple[str, str]:
    t = teks.lower().strip()
    sesi_konteks = sesi_konteks or {}

    if re.search(r"(kasus|detail|kebakaran|pendanaan|propaganda|gudang|mencurigakan)", t):
        path = "/case-workspace"
        return path, NAMA_HALAMAN.get(path, path)
    if re.search(r"(jaringan|link analysis|analisis tautan|network|relasi|koneksi)", t):
        path = "/link-analysis"
        return path, NAMA_HALAMAN.get(path, path)
    if re.search(r"(timeline|kronologi|alur kejadian)", t):
        path = "/timeline"
        return path, NAMA_HALAMAN.get(path, path)
    if re.search(r"(peringatan|alert|darurat)", t):
        path = "/alert-center"
        return path, NAMA_HALAMAN.get(path, path)
    if re.search(r"(berita|kabar|headline)", t):
        path = "/search"
        return path, NAMA_HALAMAN.get(path, path)

    path_terakhir = sesi_konteks.get("last_nav_path", "")
    if path_terakhir in NAMA_HALAMAN:
        return path_terakhir, NAMA_HALAMAN[path_terakhir]

    path = "/"
    return path, NAMA_HALAMAN.get(path, path)


def tentukan_intent(teks: str, sesi_konteks: dict | None = None):
    t = teks.lower().strip()
    sesi_konteks = sesi_konteks or {}

    if re.search(r"(ada apa hari ini|hari ini ada apa|update hari ini|lagi apa hari ini)", t):
        return "navigasi_hari_ini", {}

    if re.search(r"(halaman apa aja|halaman apa saja|daftar halaman|menu apa saja|menu apa aja|bisa buka halaman apa|halaman yang bisa dibuka)", t):
        return "daftar_halaman", {}

    if re.search(r"(lihat|cek|tinjau|pantau|analisis).{0,24}(jaringan|link analysis|analisis tautan|network)", t):
        return "navigasi", {"path": "/link-analysis", "nama": NAMA_HALAMAN.get("/link-analysis", "Analisis Jaringan")}

    if re.search(r"(lebih detail|detailnya|lebih rinci|lanjut|lanjutkan|buka yang tadi|yang tadi|yang barusan|coba lebih detail)", t):
        path_terakhir = sesi_konteks.get("last_nav_path", "")
        nama_terakhir = sesi_konteks.get("last_nav_name", "")
        if path_terakhir:
            return "navigasi_lanjutan", {"path": path_terakhir, "nama": nama_terakhir or NAMA_HALAMAN.get(path_terakhir, path_terakhir)}

    for trigger in TRIGGER_NAV:
        if trigger in t:
            sisa = t[t.find(trigger) + len(trigger):].strip()
            for kw, path in PETA_HALAMAN.items():
                if kw in sisa or kw in t:
                    return "navigasi", {"path": path, "nama": NAMA_HALAMAN.get(path, path)}
            path_auto, nama_auto = _infer_halaman_otomatis(t, sesi_konteks)
            return "navigasi", {
                "path": path_auto,
                "nama": nama_auto,
                "auto": True,
            }
    if re.search(r"(daftar kasus|ada kasus apa|kasus apa saja|list kasus|semua kasus)", t):
        return "daftar_kasus", {}
    m = re.search(r"(kasus|ceritakan|info|detail).{0,20}(kebakaran|pendanaan|propaganda|gudang|mencurigakan|kasus-\S+)", t)
    if m:
        return "detail_kasus", {"query": m.group(2).strip()}
    m = re.search(r"(siapa|cari profil|profil|info tentang|cek profil)\s+(.+)", t)
    if m:
        q = m.group(2).strip()
        if q not in {"itu", "ini", "dia", "mereka", "kasus", "berita"}:
            return "cari_profil", {"query": q}
    if re.search(r"(berita terbaru|berita hari ini|baca berita|berita apa)", t):
        return "berita_terbaru", {}
    m = re.search(r"(cari berita|berita tentang|berita soal)\s+(.+)", t)
    if m:
        return "cari_berita", {"query": m.group(2).strip()}
    if re.search(r"(peringatan aktif|alert aktif|ada peringatan)", t):
        return "peringatan", {}
    if re.search(r"(status sistem|ringkasan|kondisi sistem|overview)", t):
        return "status", {}
    if re.search(r"(klaster|propaganda|narasi koordinasi|pesan terkoordinasi)", t):
        return "klaster", {}
    return "chat", {}


def _proses_non_chat(teks: str, history: list, sesi_konteks: dict | None = None) -> dict:
    """Proses intent non-chat, return {jawaban, suara, intent, navigasi_url}."""
    data = _get_data()
    intent, extras = tentukan_intent(teks, sesi_konteks)
    nav_url = None
    nav_path = None
    nav_nama = None
    teks_panjang = ""
    teks_suara   = ""

    def _jelaskan_halaman_dengan_ai(nama: str, path: str, ucapan_user: str, mode: str = "normal") -> str:
        try:
            client = _get_ollama_client()
            konteks = data.ringkasan_untuk_llm()
            if mode == "hari_ini":
                prompt_system = (
                    "Kamu adalah Atlas. Buat penjelasan informatif untuk briefing cepat hari ini. "
                    "Jelaskan: apa yang ada di halaman ini, kenapa halaman ini relevan untuk kondisi hari ini, "
                    "dan apa aktivitas konkret yang bisa user lakukan di sana sekarang. "
                    "Bahasa harus natural, langsung ke poin, tanpa emoji, tanpa markdown, tanpa gaya tutorial menggurui. "
                    "Maksimal 4 kalimat."
                )
            elif mode == "lanjutan":
                prompt_system = (
                    "Kamu adalah Atlas. User meminta lanjutan detail dari halaman yang tadi dibuka. "
                    "Jelaskan lebih rinci: indikator utama yang harus dicek sekarang, urutan langkah investigasi, "
                    "dan keputusan cepat yang bisa langsung diambil. "
                    "Bahasa natural, tanpa emoji, tanpa markdown, maksimal 4 kalimat."
                )
            else:
                prompt_system = (
                    "Kamu adalah Atlas. Jelaskan secara informatif apa yang akan dilihat user setelah membuka halaman UIX ini, "
                    "kenapa halaman ini relevan untuk pertanyaan user, dan apa yang bisa langsung dilakukan user di dalamnya. "
                    "Gunakan konteks data UIX hanya jika relevan. "
                    "Jangan gunakan emoji, jangan markdown, dan jangan kalimat meta seperti 'fitur tersedia'. "
                    "Maksimal 4 kalimat, ringkas, jelas, dan terdengar seperti asisten manusia."
                )
            prompt_user = (
                f"Ucapan user: {ucapan_user}\n"
                f"Halaman tujuan: {nama} ({path})\n\n"
                f"Konteks data UIX:\n{konteks}"
            )
            resp = client.chat(
                model=OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": prompt_system},
                    {"role": "user", "content": prompt_user},
                ],
                think=False,
                options={"temperature": 0.5, "num_predict": 140},
            )
            hasil = _hapus_emoji((resp.message.content or "").strip())
            if hasil:
                return hasil
        except Exception:
            pass
        return (
            f"Halaman {nama} akan dibuka sekarang. Setelah terbuka, saya bisa bantu jelaskan informasi penting "
            "yang muncul sesuai kebutuhanmu."
        )

    def _klarifikasi_halaman_dengan_ai(ucapan_user: str) -> str:
        try:
            client = _get_ollama_client()
            opsi = [nama for _, nama in NAMA_HALAMAN.items()]
            daftar_opsi = ", ".join(opsi)
            prompt_system = (
                "Kamu adalah Atlas. User meminta buka halaman tapi tujuannya belum jelas. "
                "Buat satu pertanyaan klarifikasi yang natural, lalu beri 3 saran halaman paling mungkin dipilih user. "
                "Tanpa emoji, tanpa markdown, singkat dan tegas."
            )
            prompt_user = (
                f"Ucapan user: {ucapan_user}\n"
                f"Daftar halaman yang tersedia: {daftar_opsi}"
            )
            resp = client.chat(
                model=OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": prompt_system},
                    {"role": "user", "content": prompt_user},
                ],
                think=False,
                options={"temperature": 0.45, "num_predict": 120},
            )
            hasil = _hapus_emoji((resp.message.content or "").strip())
            if hasil:
                return hasil
        except Exception:
            pass

        nama_opsi = [nama for _, nama in list(NAMA_HALAMAN.items())[:3]]
        return (
            "Maksud halaman yang mana? "
            f"Kalau mau, kamu bisa pilih: {nama_opsi[0]}, {nama_opsi[1]}, atau {nama_opsi[2]}."
        )

    def _ringkas_detail_kasus_natural(detail: str) -> tuple[str, str]:
        if not detail or "tidak ditemukan di dataset" in detail:
            return detail, detail

        info: dict[str, str] = {}
        temuan: list[str] = []
        rekomendasi = ""
        peringatan_utama = ""

        for baris in [baris.strip() for baris in detail.split("\n") if baris.strip()]:
            if baris.startswith("Temuan "):
                _, isi = baris.split(":", 1)
                temuan.append(isi.strip())
                continue
            if baris.startswith("Rekomendasi:"):
                rekomendasi = baris.split(":", 1)[1].strip()
                continue
            if baris.startswith("Peringatan utama:"):
                peringatan_utama = baris.split(":", 1)[1].strip()
                continue
            if ":" in baris:
                key, value = baris.split(":", 1)
                info[key.strip()] = value.strip()

        judul = info.get("Kasus", "Kasus tidak dikenal")
        tipe_status = info.get("Tipe", "-")
        lokasi = info.get("Lokasi", "-")
        waktu = info.get("Waktu insiden", "-")
        aktor = info.get("Jumlah aktor terlibat", "?")
        risiko = info.get("Skor risiko", "")
        ringkasan = info.get("Ringkasan laporan", "")
        total_peringatan = info.get("Total peringatan", "")
        transaksi = info.get("Transaksi terkait", "")

        kalimat_1 = f"Kasus {judul} saat ini tercatat di {lokasi} dengan waktu insiden {waktu} dan melibatkan sekitar {aktor} aktor."
        kalimat_2 = f"Status operasionalnya {tipe_status}."
        if risiko:
            kalimat_2 += f" Penilaian risikonya {risiko}"
        if ringkasan:
            kalimat_3 = f"Ringkasnya, {ringkasan[0].lower() + ringkasan[1:] if len(ringkasan) > 1 else ringkasan}"
        else:
            kalimat_3 = ""

        bagian = [kalimat_1, kalimat_2]
        if kalimat_3:
            bagian.append(kalimat_3)
        if temuan:
            bagian.append("Temuan penting:")
            bagian.extend([f"- {item}" for item in temuan[:3]])
        if rekomendasi:
            bagian.append(f"Rekomendasi utama saat ini: {rekomendasi}")
        if total_peringatan:
            bagian.append(f"Peringatan aktif: {total_peringatan}")
        if peringatan_utama:
            bagian.append(f"Peringatan yang paling menonjol: {peringatan_utama}")
        if transaksi:
            bagian.append(f"Tambahan konteks finansial: {transaksi}")

        teks = "\n\n".join(
            [
                " ".join(bagian[:3]).strip(),
                "\n".join(bagian[3:]).strip() if len(bagian) > 3 else "",
            ]
        ).strip()

        suara_parts = [
            f"Kasus {judul} terjadi di {lokasi} pada {waktu}.",
            f"Statusnya {tipe_status}.",
        ]
        if risiko:
            suara_parts.append(risiko)
        if ringkasan:
            suara_parts.append(ringkasan)
        if rekomendasi:
            suara_parts.append(f"Rekomendasi utamanya {rekomendasi}")
        return teks, " ".join(suara_parts[:5]).strip()

    if intent == "navigasi":
        path, nama = extras["path"], extras["nama"]
        auto_mode = bool(extras.get("auto"))
        nav_path = path
        nav_nama = nama
        nav_url = UIX_BASE_URL + path
        deskripsi = _jelaskan_halaman_dengan_ai(nama, path, teks)
        if auto_mode:
            teks_panjang = f"Saya langsung buka halaman {nama}.\n{deskripsi}\nURL: {nav_url}".strip()
            teks_suara   = f"Saya langsung buka halaman {nama}. {deskripsi}".strip()
        else:
            teks_panjang = f"Membuka halaman {nama}.\n{deskripsi}\nURL: {nav_url}".strip()
            teks_suara   = f"Membuka halaman {nama}. {deskripsi}".strip()

    elif intent == "navigasi_hari_ini":
        kandidat = [
            "/alert-center", "/incident-queue", "/timeline", "/narrative", "/fusion", "/"
        ]
        path = random.choice(kandidat)
        nama = NAMA_HALAMAN.get(path, path)
        nav_path = path
        nav_nama = nama
        nav_url = UIX_BASE_URL + path
        deskripsi = _jelaskan_halaman_dengan_ai(nama, path, teks, mode="hari_ini")
        teks_panjang = (
            f"Untuk update hari ini, saya buka dulu halaman {nama}.\n"
            f"{deskripsi}\n"
            f"URL: {nav_url}"
        ).strip()
        teks_suara = f"Untuk update hari ini, saya buka halaman {nama}. {deskripsi}".strip()

    elif intent == "navigasi_lanjutan":
        path = extras.get("path", "")
        nama = extras.get("nama") or NAMA_HALAMAN.get(path, path)
        nav_path = path
        nav_nama = nama
        nav_url = UIX_BASE_URL + path if path else None
        deskripsi = _jelaskan_halaman_dengan_ai(nama, path, teks, mode="lanjutan")
        teks_panjang = (
            f"Oke, kita lanjut detail di halaman {nama}.\n"
            f"{deskripsi}\n"
            f"URL: {nav_url}"
        ).strip()
        teks_suara = f"Oke, kita lanjut detail di halaman {nama}. {deskripsi}".strip()

    elif intent == "daftar_halaman":
        urut = list(NAMA_HALAMAN.items())
        daftar = [f"{i}. {nama} ({path})" for i, (path, nama) in enumerate(urut, 1)]
        contoh = ", ".join([nama for _, nama in urut[:6]])
        teks_panjang = (
            "Halaman UIX yang bisa saya buka saat ini:\n\n"
            + "\n".join(daftar)
            + "\n\n"
            + "Kamu tinggal bilang misalnya: buka Intelijen Peta, buka Timeline Kejadian, atau buka Pusat Peringatan."
        )
        teks_suara = f"Saya bisa buka {contoh}, dan halaman UIX lainnya. Sebutkan saja nama halamannya."

    elif intent == "navigasi_tidak_jelas":
        klarifikasi = _klarifikasi_halaman_dengan_ai(teks)
        teks_panjang = teks_suara = klarifikasi

    elif intent == "daftar_kasus":
        ks = data.daftar_kasus()
        if not ks:
            teks_panjang = teks_suara = "Tidak ada kasus di dataset."
        else:
            baris = [f"### Daftar Kasus ({len(ks)})\n"]
            sb = [f"Ada {len(ks)} kasus."]
            for k in ks:
                idk = k['id_kasus'].replace('kasus-','').replace('-',' ').title()
                baris.append(f"- **{idk}** — {k['judul']} _{k.get('status','?')}_")
                sb.append(f"{idk}: {k['judul']}.")
            teks_panjang = "\n".join(baris)
            teks_suara   = " ".join(sb[:4])

    elif intent == "detail_kasus":
        detail = data.baca_detail_kasus(extras.get("query", ""))
        teks_panjang, teks_suara = _ringkas_detail_kasus_natural(detail)

    elif intent == "cari_profil":
        hasil = data.cari_profil(extras.get("query", ""), top_k=3)
        if not hasil:
            teks_panjang = teks_suara = f"Tidak ada profil dengan nama {extras.get('query','')}."
        else:
            baris = [f"### Profil ({len(hasil)})\n"]; sb = [f"Ditemukan {len(hasil)} profil."]
            for p in hasil:
                tautan_raw = p.get("tautan_kasus", []) or []
                tautan_str = []
                for item in tautan_raw:
                    if isinstance(item, str):
                        tautan_str.append(item)
                    elif isinstance(item, dict):
                        tautan_str.append(
                            str(item.get("id_kasus") or item.get("kasus") or item.get("id") or "")
                        )
                tautan_str = [x for x in tautan_str if x]
                ks = ", ".join(tautan_str) or "tidak terkait kasus"
                baris.append(f"- **{p['nama_lengkap']}** — {p.get('kota','?')}, {p.get('provinsi','?')} | {ks}")
                sb.append(f"{p['nama_lengkap']} dari {p.get('kota','?')}.")
            teks_panjang = "\n".join(baris)
            teks_suara   = " ".join(sb[:3])

    elif intent == "berita_terbaru":
        berita = data.baca_berita_terbaru(5)
        if not berita:
            teks_panjang = teks_suara = "Tidak ada berita tersedia."
        else:
            baris = [f"### Berita Terbaru\n"]; sb = [f"{len(berita)} berita terbaru."]
            for i, b in enumerate(berita, 1):
                tgl = b.get("published_at","")[:10]
                baris.append(f"{i}. **{b['judul']}** _{b.get('kategori','?')} · {tgl}_")
                sb.append(f"Berita {i}: {b['judul']}.")
            teks_panjang = "\n".join(baris)
            teks_suara   = " ".join(sb[:4])

    elif intent == "cari_berita":
        q = extras.get("query","")
        hasil = data.cari_berita(q, top_k=3)
        if not hasil:
            teks_panjang = teks_suara = f"Tidak ada berita terkait {q}."
        else:
            baris = [f"### Berita terkait \"{q}\"\n"]; sb = [f"{len(hasil)} berita terkait {q}."]
            for b in hasil:
                baris.append(f"- **{b['judul']}** — _{b.get('kategori','?')}_")
                sb.append(f"{b['judul']}.")
            teks_panjang = "\n".join(baris)
            teks_suara   = " ".join(sb[:3])

    elif intent == "peringatan":
        pr = data.baca_peringatan_aktif(5)
        if not pr:
            teks_panjang = teks_suara = "Tidak ada peringatan aktif."
        else:
            baris = [f"### Peringatan Aktif ({len(pr)})\n"]; sb = [f"{len(pr)} peringatan aktif."]
            for p in pr:
                kid = p.get("id_kasus","?").replace("kasus-","").replace("-"," ").title()
                baris.append(f"- **{p.get('tingkat_keparahan','?')}** Kasus {kid}: {p.get('deskripsi','-')}")
                sb.append(f"Keparahan {p.get('tingkat_keparahan','?')}: {p.get('deskripsi','-')}")
            teks_panjang = "\n".join(baris)
            teks_suara   = " ".join(sb[:3])

    elif intent == "status":
        rs = data.ringkas_sistem()
        teks_panjang = f"### Status Sistem\n\n```\n{rs}\n```"
        baris = [b for b in rs.split("\n") if b.strip()]
        teks_suara = " ".join(baris[:4])

    elif intent == "klaster":
        kl = data.baca_klaster_kritis(3)
        if not kl:
            teks_panjang = teks_suara = "Tidak ada klaster pesan."
        else:
            baris = [f"### Klaster Pesan ({len(kl)})\n"]; sb = [f"{len(kl)} klaster terdeteksi."]
            for kp in kl:
                baris.append(f"- **{kp['frasa_kanonik'][:80]}** — {kp['kemiripan_copy']:.0%}, {kp.get('jumlah_posting','?')} posting")
                sb.append(f"Frasa: {kp['frasa_kanonik'][:50]}.")
            teks_panjang = "\n".join(baris)
            teks_suara   = " ".join(sb[:3])

    return {
        "jawaban": teks_panjang,
        "suara":   teks_suara,
        "intent":  intent,
        "navigasi_url": nav_url,
        "navigasi_path": nav_path,
        "navigasi_nama": nav_nama,
    }


# ============================================================
# TTS — edge-tts default, Piper opsional
# ============================================================
_piper_voice  = None
_piper_lock   = threading.Lock()
_piper_ok     = False   # False = belum coba, None = gagal, True = siap


def _setup_piper() -> bool:
    """Download model Piper Indonesia jika belum ada, lalu load."""
    global _piper_voice, _piper_ok
    if _piper_ok:
        return True
    with _piper_lock:
        if _piper_ok:
            return True
        try:
            import urllib.request
            MODEL_DIR.mkdir(parents=True, exist_ok=True)

            def _download(url, dest):
                import requests
                r = requests.get(url, stream=True, timeout=60,
                                 headers={"User-Agent": "Mozilla/5.0"})
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        f.write(chunk)

            if not PIPER_MODEL.exists():
                print(f"  [TTS] Mengunduh Piper {PIPER_MODEL.name} (~63 MB)...", flush=True)
                _download(f"{PIPER_URL}/{PIPER_MODEL.name}", str(PIPER_MODEL))
            if not PIPER_CONFIG.exists():
                _download(f"{PIPER_URL}/{PIPER_CONFIG.name}", str(PIPER_CONFIG))

            from piper import PiperVoice
            _piper_voice = PiperVoice.load(str(PIPER_MODEL), config_path=str(PIPER_CONFIG))
            _piper_ok = True
            print("  [OK]  Piper TTS siap (lokal, ~30ms/kalimat)", flush=True)
            return True
        except Exception as e:
            print(f"  [WARN] Piper gagal: {e} — pakai edge-tts", flush=True)
            _piper_ok = None
            return False


def _tts_piper(teks: str) -> bytes | None:
    """Generate WAV via Piper, return raw WAV bytes."""
    import io, wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)   # 16-bit PCM
        wf.setframerate(_piper_voice.config.sample_rate)
        _piper_voice.synthesize(teks, wf)
    return buf.getvalue()


async def _tts_edge(teks: str) -> bytes | None:
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp = f.name
    try:
        await edge_tts.Communicate(teks, TTS_VOICE).save(tmp)
        with open(tmp, "rb") as f:
            return f.read()
    except Exception as e:
        print(f"  [TTS ERR] {e}", flush=True)
        return None
    finally:
        try: os.unlink(tmp)
        except: pass


def buat_audio(teks: str) -> bytes | None:
    teks = re.sub(r"[*#→•\[\]_`<>]", "", teks)
    teks = re.sub(r"\n+", ". ", teks).strip()
    if not teks:
        return None

    # ── Piper hanya dipakai jika diminta eksplisit ──
    if TTS_MODE == "piper" and _piper_ok is True:
        try:
            return _tts_piper(teks)
        except Exception as e:
            print(f"  [PIPER ERR] {e}", flush=True)

    # ── Default edge-tts suara Ardi ──
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_tts_edge(teks))
    finally:
        loop.close()


# ============================================================
# FILLER — pre-generate sekali di startup
# ============================================================
def _pregenerate_filler():
    import random
    print("  [TTS] Pre-generate filler phrases...", flush=True)
    for phrase in _FILLER_PHRASES:
        audio = buat_audio(phrase)
        if audio:
            _filler_audio.append(base64.b64encode(audio).decode())
    print(f"  [OK]  {len(_filler_audio)} filler audio siap", flush=True)


def _get_filler() -> str | None:
    """Ambil filler audio secara acak (base64 string)."""
    import random
    return random.choice(_filler_audio) if _filler_audio else None


# ============================================================
# SENTENCE SPLITTER
# ============================================================
_SENT_RE = re.compile(r'^(.{' + str(SENTENCE_MIN) + r',}?[.!?\n])\s*(.*)', re.DOTALL)

def _pop_sentence(buf: str):
    """Pop kalimat pertama yang lengkap. Return (kalimat, sisa) atau (None, buf)."""
    m = _SENT_RE.match(buf)
    if m:
        return m.group(1).strip(), m.group(2)
    return None, buf


# ============================================================
# FLASK
# ============================================================
app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True
CORS(app)
_sesi: dict[str, list] = {}


@app.route("/")
def halaman_utama():
  return render_template("index.html")


@app.route("/globe.json")
def aset_globe():
  return send_from_directory(str(Path(__file__).parent), "globe.json", mimetype="application/json")


@app.route("/api/status")
def api_status():
    try:
        c = _get_ollama_client()
        c.chat(model=OLLAMA_MODEL, messages=[{"role":"user","content":"ping"}], options={"num_predict":1})
        ollama_ok = True
    except Exception:
        ollama_ok = False
    return jsonify({"ollama": ollama_ok, "model": OLLAMA_MODEL,
                    "whisper": _whisper_model is not None,
                    "whisper_loading": _whisper_loading,
                    "whisper_error": _whisper_error,
                    "whisper_model": _whisper_model_name,
                    "whisper_target": WHISPER_MODEL,
                    "whisper_effective_target": _whisper_effective_target,
                    "whisper_cpu_safe": WHISPER_CPU_SAFE,
                    "whisper_device": WHISPER_DEVICE,
                    "whisper_compute_type": WHISPER_COMPUTE_TYPE})


@app.route("/api/listen", methods=["POST"])
def api_listen():
    """
    ASR saja — terima audio WebM, return JSON {teks}.
    Cepat karena faster-whisper small + vad_filter.
    """
    if "audio" not in request.files:
        return jsonify({"error": "tidak ada audio"}), 400

    f   = request.files["audio"]
    suffix = ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name
        f.save(tmp_path)

    # Validasi ukuran minimal
    if os.path.getsize(tmp_path) < 2000:
        os.unlink(tmp_path)
        return jsonify({"error": "rekaman terlalu pendek"}), 422

    mulai_asr = time.perf_counter()
    try:
        model = _get_whisper()
        segments, info = model.transcribe(
            tmp_path,
            language="id",
            beam_size=WHISPER_BEAM_SIZE,
            best_of=WHISPER_BEST_OF,
            temperature=0.0,
            condition_on_previous_text=False,
            word_timestamps=False,
            vad_filter=True,      # filter non-suara otomatis
            vad_parameters={"min_silence_duration_ms": WHISPER_VAD_MIN_SILENCE_MS},
            log_prob_threshold=-1.0,
            no_speech_threshold=0.5,
        )
        # Filter halusinasi: buang segmen dengan no_speech_prob tinggi
        bagian = []
        for s in segments:
            if s.no_speech_prob < 0.5:
                bagian.append(s.text)
        teks = " ".join(bagian).strip()
    except Exception as e:
        return jsonify({"error": f"ASR gagal: {str(e)[:100]}"}), 500
    finally:
        try: os.unlink(tmp_path)
        except: pass

    if not teks:
        return jsonify({"error": "tidak ada suara terdeteksi"}), 422

    # Buang frasa halusinasi umum Whisper
    _HALUSINASI = {"selamat menikmati", "terima kasih telah menonton",
                   "subscribe", "like dan subscribe", "sampai jumpa",
                   "musik", "terima kasih sudah menonton"}
    if teks.lower().strip(".! ") in _HALUSINASI:
        return jsonify({"error": "tidak ada suara terdeteksi"}), 422

    durasi_asr_ms = int((time.perf_counter() - mulai_asr) * 1000)
    print(f"  [ASR] '{teks}' ({durasi_asr_ms} ms)", flush=True)
    return jsonify({"teks": teks})


@app.route("/api/stream")
def api_stream():
    """
    SSE endpoint — stream teks + audio per kalimat.
    Events: text | audio | nav | done
    """
    teks = request.args.get("teks", "").strip()
    sid  = request.args.get("session_id", "default")
    if not teks:
        return jsonify({"error": "teks kosong"}), 400

    history = _sesi.setdefault(sid, [])
    sesi_konteks = _ambil_sesi_konteks(sid)
    intent, _ = tentukan_intent(teks, sesi_konteks)

    def sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    def generate():
        # ── Non-chat intent ──────────────────────────────
        if intent != "chat":
            hasil = _proses_non_chat(teks, history, sesi_konteks=sesi_konteks)
            jawaban = _hapus_emoji(hasil["jawaban"])
            suara   = _hapus_emoji(hasil["suara"])
            nav_url = hasil["navigasi_url"]

            # Teks langsung (typewriter di sisi browser)
            yield sse("text", {"c": jawaban, "full": True})

            if nav_url:
                yield sse("nav", {"url": nav_url})

            if suara:
                audio = buat_audio(suara)
                if audio:
                    yield sse("audio", {"d": base64.b64encode(audio).decode()})

            history.append({"role": "user",      "content": teks})
            history.append({"role": "assistant", "content": jawaban})
            if len(history) > 40:
                _sesi[sid] = history[-40:]

            _update_sesi_konteks(
                sid,
                last_intent=hasil.get("intent"),
                last_user_text=teks,
                last_reply_text=jawaban,
                last_nav_url=hasil.get("navigasi_url"),
                last_nav_path=hasil.get("navigasi_path"),
                last_nav_name=hasil.get("navigasi_nama"),
            )

            yield sse("done", {})
            return

        # ── Chat: stream Ollama, TTS per kalimat ─────────
        data    = _get_data()
        ctx     = data.ringkasan_untuk_llm()
        sys_msg = (
            "Kamu adalah Atlas, AI voice assistant yang ngobrol natural dengan user. "
            "Jawab dalam Bahasa Indonesia yang santai, jelas, dan langsung menanggapi maksud user. "
            "Untuk ucapan umum, obrolan bebas, pertanyaan acak, atau kalimat informal, jawab secara percakapan seperti asisten yang benar-benar paham konteks pembicaraan. "
            "Jangan menjawab dengan gaya meta atau birokratis seperti 'instruksi diterima', 'sistem akan memproses', atau 'fitur tersedia', kecuali user memang meminta eksekusi sistem. "
            "Kalau user meminta opini, penjelasan, saran, atau respons lanjutan, jawab isi pertanyaannya secara langsung. "
            "Saat pertanyaan relevan dengan data UIX, gunakan konteks database di bawah sebagai rujukan utama. "
            "Saat pertanyaan tidak butuh data UIX, jangan dipaksa diarahkan ke database. "
            "Jangan mengarang fakta spesifik dari database jika tidak ada di konteks. "
            "Usahakan singkat, enak didengar, maksimal 4 kalimat.\n\n"
            "Konteks UIX berikut hanya referensi jika relevan:\n"
            f"{ctx}"
        )
        messages = [{"role": "system", "content": sys_msg}]
        for h in history[-8:]:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": teks})

        client    = _get_ollama_client()
        buf       = ""
        full_text = []
        pending   = []   # list of Future[bytes|None] — TTS jobs, harus yield IN ORDER

        def _submit_tts(txt: str):
            """Bersihkan dan kirim ke thread pool."""
            clean = re.sub(r'[*#`\[\]_→•<>]', '', txt).strip()
            if clean:
                pending.append(_tts_pool.submit(buat_audio, clean))

        def _drain_ready():
            """Yield audio dari future yang sudah selesai, urut dari depan."""
            while pending and pending[0].done():
                audio = pending.pop(0).result()
                if audio:
                    yield sse("audio", {"d": base64.b64encode(audio).decode()})

        try:
            stream = client.chat(
                model=OLLAMA_MODEL,
                messages=messages,
                stream=True,
                think=False,
                options={"temperature": 0.6, "num_predict": 300},
            )
            for chunk in stream:
                token = _hapus_emoji(chunk.message.content or "")
                if not token:
                    continue
                buf += token
                full_text.append(token)

                # Kirim token ke browser (typewriter) — langsung, tidak nunggu TTS
                yield sse("text", {"c": token})

                # Cek kalimat lengkap → submit TTS ke thread (non-blocking)
                sentence, buf = _pop_sentence(buf)
                if sentence:
                    _submit_tts(sentence)

                # Cek apakah ada TTS yang sudah selesai → yield audio
                yield from _drain_ready()

        except Exception as e:
            err = _hapus_emoji(f"Maaf, Ollama error: {str(e)[:80]}")
            yield sse("text", {"c": err})
            _submit_tts(err)

        # Flush sisa buffer
        if buf.strip():
            _submit_tts(buf)

        # Drain semua TTS yang masih pending (tunggu dalam urutan)
        for fut in pending:
            audio = fut.result()
            if audio:
                yield sse("audio", {"d": base64.b64encode(audio).decode()})

        # Simpan history
        joined = "".join(full_text)
        history.append({"role": "user",      "content": teks})
        history.append({"role": "assistant", "content": joined})
        if len(history) > 40:
            _sesi[sid] = history[-40:]

        _update_sesi_konteks(
            sid,
            last_intent="chat",
            last_user_text=teks,
            last_reply_text=joined,
        )

        print(f"  [ATLAS] {joined[:80]}", flush=True)
        yield sse("done", {})

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":       "keep-alive",
        },
    )


@app.route("/api/chat", methods=["POST"])
def api_chat():
  """Interaksi teks dinonaktifkan. Gunakan trigger suara via klik globe."""
  return jsonify({"error": "mode teks dinonaktifkan, gunakan trigger suara lewat klik globe"}), 410


@app.route("/api/tts", methods=["POST"])
def api_tts():
    d    = request.get_json(silent=True) or {}
    teks = (d.get("teks") or "").strip()
    if not teks:
        return jsonify({"error": "teks kosong"}), 400
    audio = buat_audio(teks)
    if not audio:
        return jsonify({"error": "TTS gagal"}), 500
    return Response(audio, mimetype="audio/mpeg")


@app.route("/api/fillers")
def api_fillers():
  """Kirim satu filler audio acak per request."""
  audio = _get_filler()
  if not audio:
    return jsonify({"audio": None}), 204
  return jsonify({"audio": audio})


@app.route("/api/clear", methods=["POST"])
def api_clear():
    d   = request.get_json(silent=True) or {}
    sid = d.get("session_id", "default")
    _sesi[sid] = []
    _reset_sesi_konteks(sid)
    return jsonify({"ok": True})

# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    print()
    _mode = "☁️  CLOUD  (ollama.com)" if _OLLAMA_CLOUD else "💻 LOKAL  (localhost:11434)"
    print("=" * 54)
    print("  Atlas LIVE v2 — UIX Intelligence Voice Assistant")
    print(f"  URL  : http://localhost:{WEB_PORT}")
    print(f"  LLM  : {OLLAMA_MODEL}  [{_mode}]")
    print(f"  TTS  : {TTS_MODE} / {TTS_VOICE}")
    print("=" * 54)
    print()
    print("  Memuat dataset...", flush=True)
    _get_data()
    print()
    if TTS_MODE == "piper":
      print("  Memuat Piper TTS (download ~65 MB jika belum ada)...", flush=True)
      _setup_piper()
    else:
      print("  TTS mode edge aktif — memakai voice Ardi dari edge-tts", flush=True)
    _pregenerate_filler()
    print()
    print("  Menyiapkan Whisper (non-blocking saat startup)...", flush=True)
    if WHISPER_PRELOAD:
        _preload_whisper_async()
        print(f"  [OK]   Preload Whisper dimulai di background (target: {WHISPER_MODEL})", flush=True)
    else:
        print("  [OK]   Preload Whisper dimatikan (lazy load saat /api/listen)", flush=True)
    print()
    print(f"  Server siap → http://localhost:{WEB_PORT}")
    print()
    print("  [Ctrl+C] untuk menghentikan")
    print()

    threading.Timer(1.2, lambda: webbrowser.open(f"http://localhost:{WEB_PORT}")).start()
    app.run(host="0.0.0.0", port=WEB_PORT, debug=False, use_reloader=False, threaded=True)
