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
import os, re, sys, json, time, asyncio, base64, tempfile, threading, warnings
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
from flask import Flask, request, jsonify, render_template_string, Response, stream_with_context
from flask_cors import CORS

sys.path.insert(0, str(Path(__file__).parent))
from atlas_data import AtlasData

# ============================================================
# CONFIG
# ============================================================
# Ollama: pakai cloud jika OLLAMA_API_KEY ada, fallback ke lokal
_OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "").strip()
_OLLAMA_CLOUD   = bool(_OLLAMA_API_KEY and not _OLLAMA_API_KEY.startswith("PASTE"))

OLLAMA_MODEL  = "gpt-oss:120b" if _OLLAMA_CLOUD else "qwen3.5:latest"
TTS_VOICE     = "id-ID-ArdiNeural"          # fallback edge-tts
WEB_PORT      = 7860
SENTENCE_MIN  = 15   # min karakter sebelum TTS per kalimat
MODEL_DIR     = Path(__file__).parent / "models"

# Piper model Indonesia
PIPER_MODEL   = MODEL_DIR / "id_ID-news_tts-medium.onnx"
PIPER_CONFIG  = MODEL_DIR / "id_ID-news_tts-medium.onnx.json"
PIPER_URL     = ("https://huggingface.co/rhasspy/piper-voices/resolve/main"
                 "/id/id_ID/news_tts/medium")

# ============================================================
# GLOBAL (lazy load)
# ============================================================
_whisper_model  = None
_atlas_data     = None
_lock_w         = threading.Lock()

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


def _get_ollama_client() -> ollama.Client:
    """Return Ollama client — cloud jika API key ada, lokal jika tidak."""
    if _OLLAMA_CLOUD:
        return ollama.Client(
            host="https://ollama.com",
            headers={"Authorization": f"Bearer {_OLLAMA_API_KEY}" "97271e761ac14287ac1d0c89d1179431.uGompoKunsmkPzZWotxFQHmK97271e761ac14287ac1d0c89d1179431.uGompoKunsmkPzZWotxFQHmK"},
        )
    return ollama.Client(host="http://localhost:11434")


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        with _lock_w:
            if _whisper_model is None:
                print("  [LOAD] Memuat faster-whisper small...", flush=True)
                _whisper_model = WhisperModel(
                    "small",
                    device="cpu",
                    compute_type="int8",
                    download_root=MODEL_DIR,
                )
                print("  [OK]   Whisper siap", flush=True)
    return _whisper_model


def _get_data():
    global _atlas_data
    if _atlas_data is None:
        _atlas_data = AtlasData(verbose=True)
    return _atlas_data


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


def tentukan_intent(teks: str):
    t = teks.lower().strip()
    for trigger in TRIGGER_NAV:
        if trigger in t:
            sisa = t[t.find(trigger) + len(trigger):].strip()
            for kw, path in PETA_HALAMAN.items():
                if kw in sisa or kw in t:
                    return "navigasi", {"path": path, "nama": NAMA_HALAMAN.get(path, path)}
            return "navigasi_tidak_jelas", {}
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


def _proses_non_chat(teks: str, history: list) -> dict:
    """Proses intent non-chat, return {jawaban, suara, intent, navigasi_url}."""
    data = _get_data()
    intent, extras = tentukan_intent(teks)
    nav_url = None
    teks_panjang = ""
    teks_suara   = ""

    if intent == "navigasi":
        path, nama = extras["path"], extras["nama"]
        nav_url = UIX_BASE_URL + path
        teks_panjang = f"Membuka halaman **{nama}**.\n→ {nav_url}"
        teks_suara   = f"Membuka halaman {nama}."

    elif intent == "navigasi_tidak_jelas":
        teks_panjang = teks_suara = "Halaman tidak dikenali. Sebutkan nama halaman yang lebih spesifik."

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
        teks_panjang = f"```\n{detail}\n```"
        baris = [b for b in detail.split("\n") if b.strip()]
        teks_suara = " ".join(baris[:5])

    elif intent == "cari_profil":
        hasil = data.cari_profil(extras.get("query", ""), top_k=3)
        if not hasil:
            teks_panjang = teks_suara = f"Tidak ada profil dengan nama {extras.get('query','')}."
        else:
            baris = [f"### Profil ({len(hasil)})\n"]; sb = [f"Ditemukan {len(hasil)} profil."]
            for p in hasil:
                ks = ", ".join(p.get("tautan_kasus", [])) or "tidak terkait kasus"
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
                baris.append(f"- ⚠️ **{p.get('tingkat_keparahan','?')}** Kasus {kid}: {p.get('deskripsi','-')}")
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
    }


# ============================================================
# TTS — Piper lokal (cepat) + edge-tts fallback
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

    # ── Coba Piper dulu (lokal, cepat) ──
    if _piper_ok is True:
        try:
            return _tts_piper(teks)
        except Exception as e:
            print(f"  [PIPER ERR] {e}", flush=True)

    # ── Fallback edge-tts ──
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
app = Flask(__name__)
CORS(app)
_sesi: dict[str, list] = {}


@app.route("/")
def halaman_utama():
    return render_template_string(HTML)


@app.route("/api/status")
def api_status():
    try:
        c = _get_ollama_client()
        c.chat(model=OLLAMA_MODEL, messages=[{"role":"user","content":"ping"}], options={"num_predict":1})
        ollama_ok = True
    except Exception:
        ollama_ok = False
    return jsonify({"ollama": ollama_ok, "model": OLLAMA_MODEL,
                    "whisper": _whisper_model is not None})


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

    try:
        model = _get_whisper()
        segments, info = model.transcribe(
            tmp_path,
            language="id",
            beam_size=1,          # greedy — lebih cepat
            vad_filter=True,      # filter non-suara otomatis
            vad_parameters={"min_silence_duration_ms": 300},
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

    print(f"  [ASR] '{teks}'", flush=True)
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
    intent, _ = tentukan_intent(teks)

    def sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    def generate():
        # ── Non-chat intent ──────────────────────────────
        if intent != "chat":
            hasil = _proses_non_chat(teks, history)
            jawaban = hasil["jawaban"]
            suara   = hasil["suara"]
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

            yield sse("done", {})
            return

        # ── Chat: stream Ollama, TTS per kalimat ─────────
        data    = _get_data()
        ctx     = data.ringkasan_untuk_llm()
        sys_msg = (
            "Kamu adalah Atlas, asisten AI untuk sistem intelijen UIX. "
            "Jawab dalam Bahasa Indonesia. Singkat dan padat — maksimal 3-4 kalimat. "
            "Boleh markdown untuk teks.\n\n" + ctx
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
                token = chunk.message.content
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
            err = f"Maaf, Ollama error: {str(e)[:80]}"
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
    """Fallback teks → JSON (untuk kompatibilitas)."""
    d    = request.get_json(silent=True) or {}
    teks = (d.get("teks") or "").strip()
    sid  = d.get("session_id", "default")
    if not teks:
        return jsonify({"error": "teks kosong"}), 400
    history = _sesi.setdefault(sid, [])
    hasil   = _proses_non_chat(teks, history)
    intent, _ = tentukan_intent(teks)
    if intent == "chat":
        # fallback sync ollama
        data = _get_data()
        sys_msg = ("Kamu adalah Atlas, asisten UIX. Jawab Bahasa Indonesia, singkat.\n\n"
                   + data.ringkasan_untuk_llm())
        messages = [{"role":"system","content":sys_msg}]
        for h in history[-8:]:
            messages.append(h)
        messages.append({"role":"user","content":teks})
        try:
            resp = _get_ollama_client().chat(
                model=OLLAMA_MODEL, messages=messages,
                think=False, options={"temperature":0.6,"num_predict":300}
            )
            jawaban = resp.message.content.strip()
        except Exception as e:
            jawaban = f"Ollama error: {e}"
        hasil["jawaban"] = jawaban
        hasil["suara"]   = jawaban
    history.append({"role":"user","content":teks})
    history.append({"role":"assistant","content":hasil["jawaban"]})
    if len(history) > 40:
        _sesi[sid] = history[-40:]
    return jsonify({
        "jawaban": hasil["jawaban"],
        "intent": hasil["intent"],
        "navigasi_url": hasil["navigasi_url"],
    })


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
    """Kirim semua filler audio ke browser saat halaman load."""
    return jsonify({"audios": _filler_audio})


@app.route("/api/clear", methods=["POST"])
def api_clear():
    d   = request.get_json(silent=True) or {}
    sid = d.get("session_id", "default")
    _sesi[sid] = []
    return jsonify({"ok": True})


# ============================================================
# HTML — Live Voice UI v2
# ============================================================
HTML = r"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Atlas Live — UIX Intelligence</title>
<style>
:root {
  --merah:   #B31818;
  --merah2:  #D62828;
  --merah-hl:#F5E8E8;
  --latar:   #F7F3F2;
  --permukaan:#FFF8F7;
  --border:  #E8DEDD;
  --teks:    #1A1A1A;
  --redup:   #7A6060;
  --hijau:   #2E7D32;
  --font: -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  --r: 12px;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;font-family:var(--font);background:var(--latar);color:var(--teks);overflow:hidden}

.app{display:flex;height:100vh}

/* SIDEBAR */
.sidebar{
  width:230px;min-width:230px;
  background:var(--permukaan);border-right:1px solid var(--border);
  display:flex;flex-direction:column;
}
.sb-head{padding:16px 14px 12px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px}
.logo{width:34px;height:34px;border-radius:9px;background:var(--merah);color:#fff;
  font-weight:800;font-size:16px;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.sb-title{font-weight:700;font-size:14px}
.sb-sub{font-size:11px;color:var(--redup)}
.sb-section{padding:12px 14px 4px;font-size:10px;text-transform:uppercase;letter-spacing:.7px;font-weight:700;color:var(--redup)}
.chip-nav{
  margin:3px 8px;padding:7px 10px;border-radius:8px;
  border:1px solid var(--border);background:transparent;
  font-size:12.5px;color:var(--redup);cursor:pointer;text-align:left;
  display:flex;align-items:center;gap:7px;transition:all .12s;
}
.chip-nav:hover{background:var(--merah-hl);color:var(--merah);border-color:var(--merah)}
.sb-spacer{flex:1}
.sb-footer{padding:12px 14px;border-top:1px solid var(--border);font-size:11px;color:var(--redup)}
.dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:4px;vertical-align:middle}
.dot.on{background:var(--hijau)}.dot.off{background:#C62828}

/* MAIN */
.main{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}

/* TOPBAR */
.topbar{
  height:50px;padding:0 20px;flex-shrink:0;
  border-bottom:1px solid var(--border);background:var(--permukaan);
  display:flex;align-items:center;justify-content:space-between;
}
.topbar-title{font-size:14px;font-weight:700;display:flex;align-items:center;gap:8px}
.mode-badge{font-size:10px;padding:2px 8px;border-radius:20px;font-weight:700;
  background:var(--merah-hl);color:var(--merah);letter-spacing:.3px}
.topbar-right{display:flex;gap:6px;align-items:center}
.btn-sm{padding:5px 10px;border-radius:8px;border:1px solid var(--border);
  background:var(--permukaan);font-size:12px;cursor:pointer;color:var(--redup);transition:all .12s}
.btn-sm:hover{border-color:var(--merah);color:var(--merah);background:var(--merah-hl)}

/* LIVE ZONE */
.live-zone{
  flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;
  gap:18px;padding:20px;overflow:hidden;position:relative;
}

/* ORB */
.orb-wrap{position:relative;display:flex;align-items:center;justify-content:center}
.orb{
  width:112px;height:112px;border-radius:50%;
  background:radial-gradient(circle at 35% 35%, #E04B4B, var(--merah));
  display:flex;align-items:center;justify-content:center;
  cursor:pointer;user-select:none;
  box-shadow:0 4px 24px rgba(179,24,24,.25);
  transition:transform .15s,box-shadow .15s;
  position:relative;z-index:2;
}
.orb:hover{transform:scale(1.05);box-shadow:0 8px 32px rgba(179,24,24,.35)}
.orb svg{pointer-events:none}
.ring{position:absolute;border-radius:50%;border:2px solid rgba(179,24,24,.3);animation:none}
.orb-wrap.listening .ring:nth-child(1){width:136px;height:136px;animation:ripple 1.4s ease-out infinite}
.orb-wrap.listening .ring:nth-child(2){width:162px;height:162px;animation:ripple 1.4s ease-out .35s infinite}
.orb-wrap.listening .ring:nth-child(3){width:188px;height:188px;animation:ripple 1.4s ease-out .7s infinite}
.orb-wrap.speaking  .ring:nth-child(1){width:136px;height:136px;animation:pulse-spk .9s ease-in-out infinite}
.orb-wrap.speaking  .ring:nth-child(2){width:162px;height:162px;animation:pulse-spk .9s ease-in-out .2s infinite}
.orb-wrap.speaking  .ring:nth-child(3){width:188px;height:188px;animation:pulse-spk .9s ease-in-out .4s infinite}
@keyframes ripple  {0%{transform:scale(1);opacity:.5}100%{transform:scale(1.15);opacity:0}}
@keyframes pulse-spk{0%,100%{transform:scale(1);opacity:.5}50%{transform:scale(1.08);opacity:.2}}

.state-label{
  font-size:13.5px;font-weight:600;color:var(--redup);
  letter-spacing:.3px;min-height:20px;text-align:center;transition:opacity .2s;
}
.state-label.merah{color:var(--merah)}

/* WAVEFORM */
#waveform{width:260px;height:40px;border-radius:8px;opacity:0;transition:opacity .3s}
.orb-wrap.listening ~ #waveform{opacity:1}

/* TRANSCRIPT AREA */
.transcript-area{
  width:100%;max-width:580px;
  background:var(--permukaan);border:1px solid var(--border);border-radius:var(--r);
  padding:14px 16px;font-size:14px;line-height:1.65;
  min-height:60px;max-height:200px;overflow-y:auto;
}
.transcript-area.kosong{opacity:.4}
.tr-you-lbl{color:var(--redup);font-size:11.5px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;margin-bottom:5px}
.tr-you-teks{color:var(--teks)}
.tr-atlas-wrap{margin-top:10px;padding-top:10px;border-top:1px solid var(--border)}
.tr-atlas-lbl{color:var(--merah);font-size:11.5px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;margin-bottom:5px;
  display:flex;align-items:center;gap:6px}
.tr-atlas-teks{color:var(--teks);white-space:pre-wrap}

/* Blink cursor saat typewriter */
.blink::after{content:"▋";animation:blink .7s step-end infinite;color:var(--merah);font-size:.9em}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0}}

/* markdown lite */
.tr-atlas-teks h3{color:var(--merah);font-size:13px;margin:6px 0 3px}
.tr-atlas-teks strong{color:var(--teks)}
.tr-atlas-teks ul{padding-left:16px}
.tr-atlas-teks pre{background:var(--latar);padding:8px;border-radius:6px;font-size:12px;overflow-x:auto;margin:6px 0}
.tr-atlas-teks code{background:var(--latar);padding:1px 5px;border-radius:4px;font-size:12px}

/* INPUT BAR */
.input-bar{padding:10px 16px 12px;flex-shrink:0;border-top:1px solid var(--border);background:var(--permukaan)}
.input-inner{
  max-width:580px;margin:0 auto;
  display:flex;align-items:flex-end;gap:8px;
  background:var(--latar);border:1.5px solid var(--border);border-radius:12px;
  padding:7px 8px;transition:border-color .15s;
}
.input-inner:focus-within{border-color:var(--merah)}
#inp{flex:1;border:none;outline:none;background:transparent;
  font-family:var(--font);font-size:13px;color:var(--teks);
  resize:none;max-height:100px;min-height:20px;line-height:1.5;padding:2px 4px}
#inp::placeholder{color:var(--redup)}
.btn-send{width:32px;height:32px;border-radius:8px;border:none;
  background:var(--merah);color:#fff;cursor:pointer;font-size:14px;flex-shrink:0;
  display:flex;align-items:center;justify-content:center;transition:background .12s}
.btn-send:hover{background:var(--merah2)}
.btn-send:disabled{background:var(--border);cursor:default}
.input-hint{max-width:580px;margin:5px auto 0;font-size:11px;color:var(--redup);text-align:center}

/* NAV TOAST */
.nav-toast{
  position:fixed;bottom:80px;left:50%;transform:translateX(-50%);
  background:var(--merah);color:#fff;padding:9px 18px;border-radius:20px;
  font-size:13px;font-weight:600;box-shadow:0 4px 16px rgba(179,24,24,.3);
  opacity:0;pointer-events:none;transition:opacity .25s;z-index:100;
}
.nav-toast.show{opacity:1;pointer-events:auto}

::-webkit-scrollbar{width:4px}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:99px}
@media(max-width:600px){.sidebar{display:none}}
</style>
</head>
<body>
<div class="app">

<!-- SIDEBAR -->
<aside class="sidebar">
  <div class="sb-head">
    <div class="logo">A</div>
    <div><div class="sb-title">Atlas</div><div class="sb-sub">UIX Intelligence</div></div>
  </div>
  <div class="sb-section">Navigasi Cepat</div>
  <button class="chip-nav" onclick="kirimTeks('Buka halaman ikhtisar')">🏠 Ikhtisar</button>
  <button class="chip-nav" onclick="kirimTeks('Buka halaman peringatan')">⚠️ Peringatan</button>
  <button class="chip-nav" onclick="kirimTeks('Buka halaman peta')">🗺️ Peta</button>
  <button class="chip-nav" onclick="kirimTeks('Buka link analysis')">🕸️ Link Analysis</button>
  <button class="chip-nav" onclick="kirimTeks('Buka timeline')">📅 Timeline</button>
  <div class="sb-section">Tanya Atlas</div>
  <button class="chip-nav" onclick="kirimTeks('Daftar semua kasus')">📋 Daftar kasus</button>
  <button class="chip-nav" onclick="kirimTeks('Berita terbaru')">📰 Berita terbaru</button>
  <button class="chip-nav" onclick="kirimTeks('Peringatan aktif')">🔔 Alert aktif</button>
  <button class="chip-nav" onclick="kirimTeks('Status sistem')">📊 Status sistem</button>
  <div class="sb-spacer"></div>
  <div class="sb-footer">
    <div id="st-ollama"><span class="dot off" id="dot-o"></span>Memeriksa...</div>
    <div id="st-model" style="margin-top:4px;font-size:10px"></div>
  </div>
</aside>

<!-- MAIN -->
<main class="main">
  <div class="topbar">
    <div class="topbar-title">
      Atlas Live
      <span class="mode-badge" id="mode-badge">SIAP</span>
    </div>
    <div class="topbar-right">
      <button class="btn-sm" onclick="clearChat()">🗑 Hapus</button>
      <button class="btn-sm" onclick="window.open('http://localhost:5173','_blank')">↗ UIX</button>
    </div>
  </div>

  <div class="live-zone">
    <!-- ORB -->
    <div class="orb-wrap" id="orb-wrap" onclick="toggleLive()">
      <div class="ring"></div><div class="ring"></div><div class="ring"></div>
      <div class="orb" id="orb">
        <svg id="ico-mic" width="42" height="42" viewBox="0 0 24 24" fill="none"
          stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
          <line x1="12" y1="19" x2="12" y2="23"/>
          <line x1="8" y1="23" x2="16" y2="23"/>
        </svg>
        <svg id="ico-stop" width="38" height="38" viewBox="0 0 24 24" fill="white" style="display:none">
          <rect x="4" y="4" width="16" height="16" rx="3"/>
        </svg>
        <svg id="ico-spk" width="42" height="42" viewBox="0 0 24 24" fill="none"
          stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="display:none">
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
          <path d="M15.54 8.46a5 5 0 0 1 0 7.07M19.07 4.93a10 10 0 0 1 0 14.14"/>
        </svg>
        <svg id="ico-proc" width="38" height="38" viewBox="0 0 24 24" fill="none"
          stroke="white" stroke-width="2" stroke-linecap="round" style="display:none">
          <circle cx="12" cy="12" r="9" stroke-dasharray="28 56" stroke-dashoffset="0">
            <animateTransform attributeName="transform" type="rotate"
              from="0 12 12" to="360 12 12" dur=".8s" repeatCount="indefinite"/>
          </circle>
        </svg>
      </div>
    </div>

    <canvas id="waveform" width="260" height="40"></canvas>
    <div class="state-label" id="state-label">Ketuk orb untuk mulai bicara</div>

    <!-- TRANSCRIPT -->
    <div class="transcript-area kosong" id="transcript-area">
      <div id="tr-placeholder" style="color:var(--redup);font-size:13px;text-align:center">
        Mulai bicara — Atlas akan menjawab langsung
      </div>
      <div id="tr-content" style="display:none">
        <div class="tr-you-lbl">Kamu</div>
        <div class="tr-you-teks" id="tr-kamu"></div>
        <div class="tr-atlas-wrap" id="tr-atlas-wrap" style="display:none">
          <div class="tr-atlas-lbl">
            Atlas
            <span id="tr-loading" style="display:none;opacity:.6;font-size:11px;font-weight:400">memproses...</span>
          </div>
          <div class="tr-atlas-teks" id="tr-atlas"></div>
        </div>
      </div>
    </div>
  </div>

  <!-- INPUT BAR -->
  <div class="input-bar">
    <div class="input-inner">
      <textarea id="inp" placeholder="Atau ketik perintah di sini..." rows="1"
        onkeydown="onKey(event)" oninput="resize(this)"></textarea>
      <button class="btn-send" id="btn-send" onclick="kirimInput()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <line x1="22" y1="2" x2="11" y2="13"/>
          <polygon points="22 2 15 22 11 13 2 9 22 2"/>
        </svg>
      </button>
    </div>
    <div class="input-hint">Ketuk orb untuk bicara · Enter untuk kirim teks</div>
  </div>
</main>
</div>
<div class="nav-toast" id="nav-toast"></div>

<script>
// ═══════════════════════════════════════════════
// STATE MACHINE  idle|listening|processing|speaking
// ═══════════════════════════════════════════════
let state    = "idle";
let autoLive = false;

// ─── Recording ───────────────────────────────
let mediaStream   = null;
let mediaRecorder = null;
let audioChunks   = [];

// ─── VAD ─────────────────────────────────────
let audioCtx    = null;
let analyser    = null;
let vadInterval = null;
let silenceMs   = 0;
const SILENCE_THRESHOLD = 0.012;
const SILENCE_STOP_MS   = 1300;
const MIN_RECORD_MS     = 600;
let recordStart = 0;

// ─── Waveform ────────────────────────────────
const cvs  = document.getElementById("waveform");
const ctx2 = cvs.getContext("2d");
let waveAnim = null;
let waveLevel = 0;

// ─── Audio queue (gapless AudioContext) ──────
let playCtx      = null;
let nextStartAt  = 0;    // scheduled time for next chunk
let chunksQueued = 0;
let chunksPlayed = 0;
let streamDone   = false;
let currentSrc   = null;

// ─── SSE ─────────────────────────────────────
let sseSource = null;

// ─── Typewriter ──────────────────────────────
let twQueue  = "";
let twTimer  = null;
let twFull   = false;   // true = paste full text instantly

// ─── Session ─────────────────────────────────
const SESSION_ID = "live_" + Math.random().toString(36).slice(2, 9);

// ─── Filler audio (pre-loaded dari server) ───
let _fillerBuffers = [];   // Array of AudioBuffer, siap play kapanpun

async function loadFillers() {
  try {
    const r = await fetch("/api/fillers");
    const d = await r.json();
    const ctx = getPlayCtx();
    for (const b64 of d.audios) {
      const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
      try {
        const buf = await ctx.decodeAudioData(bytes.buffer);
        _fillerBuffers.push(buf);
      } catch(e) {}
    }
    console.log(`[Atlas] ${_fillerBuffers.length} filler audio siap`);
  } catch(e) {}
}

function playFiller() {
  if (!_fillerBuffers.length) return;
  const ctx = getPlayCtx();
  const buf = _fillerBuffers[Math.floor(Math.random() * _fillerBuffers.length)];
  const src = ctx.createBufferSource();
  src.buffer = buf;
  src.connect(ctx.destination);
  const startAt = Math.max(ctx.currentTime, nextStartAt);
  src.start(startAt);
  nextStartAt = startAt + buf.duration;   // response audio antri di belakang
  chunksQueued++;
  src.onended = () => { chunksPlayed++; checkStreamAudioDone(); };
  currentSrc = src;
  setState("speaking");
}

// ═══════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════
document.addEventListener("DOMContentLoaded", () => {
  setState("idle");
  cekStatus();
  loadFillers();   // pre-load filler ke AudioContext buffer
});

async function cekStatus() {
  try {
    const r = await fetch("/api/status");
    const d = await r.json();
    const ok = d.ollama;
    document.getElementById("dot-o").className = "dot " + (ok ? "on" : "off");
    document.getElementById("st-ollama").innerHTML =
      `<span class="dot ${ok?"on":"off"}"></span>${ok?"Ollama aktif":"Ollama offline"}`;
    document.getElementById("st-model").textContent = d.model || "";
  } catch(e) {}
}

// ═══════════════════════════════════════════════
// STATE SETTER
// ═══════════════════════════════════════════════
function setState(s) {
  state = s;
  const wrap  = document.getElementById("orb-wrap");
  const lbl   = document.getElementById("state-label");
  const badge = document.getElementById("mode-badge");
  const mic   = document.getElementById("ico-mic");
  const stop  = document.getElementById("ico-stop");
  const spk   = document.getElementById("ico-spk");
  const proc  = document.getElementById("ico-proc");

  wrap.className = "orb-wrap" + (s==="listening"?" listening":s==="speaking"?" speaking":"");
  mic.style.display = stop.style.display = spk.style.display = proc.style.display = "none";

  switch(s) {
    case "idle":
      mic.style.display = "";
      lbl.textContent   = autoLive ? "Mode live aktif — siap mendengarkan" : "Ketuk orb untuk mulai bicara";
      lbl.className     = "state-label";
      badge.textContent = autoLive ? "LIVE" : "SIAP";
      stopWaveform();
      break;
    case "listening":
      stop.style.display = "";
      lbl.textContent    = "Mendengarkan...";
      lbl.className      = "state-label merah";
      badge.textContent  = "LISTEN";
      startWaveform();
      break;
    case "processing":
      proc.style.display = "";
      lbl.textContent    = "Memproses...";
      lbl.className      = "state-label";
      badge.textContent  = "PROSES";
      stopWaveform();
      break;
    case "speaking":
      spk.style.display = "";
      lbl.textContent   = "Atlas berbicara...";
      lbl.className     = "state-label merah";
      badge.textContent = "BICARA";
      break;
  }
}

// ═══════════════════════════════════════════════
// TOGGLE ORB
// ═══════════════════════════════════════════════
function toggleLive() {
  if (state === "listening") {
    stopListening(true);
  } else if (state === "speaking") {
    interruptSpeaking();
  } else if (state === "idle" || state === "processing") {
    autoLive = true;
    startListening();
  }
}

// ═══════════════════════════════════════════════
// LISTENING
// ═══════════════════════════════════════════════
async function startListening() {
  if (state === "listening") return;
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
  } catch(e) {
    alert("Tidak bisa akses mikrofon: " + e.message); return;
  }

  audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
  const src = audioCtx.createMediaStreamSource(mediaStream);
  analyser  = audioCtx.createAnalyser();
  analyser.fftSize = 1024;
  src.connect(analyser);

  audioChunks = [];
  const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
    ? "audio/webm;codecs=opus" : "audio/webm";
  mediaRecorder = new MediaRecorder(mediaStream, { mimeType: mime });
  mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
  mediaRecorder.onstop = onRecordStop;
  mediaRecorder.start(100);
  recordStart = Date.now();
  setState("listening");
  silenceMs = 0;

  const buf = new Float32Array(analyser.fftSize);
  vadInterval = setInterval(() => {
    analyser.getFloatTimeDomainData(buf);
    const rms = Math.sqrt(buf.reduce((s,v) => s+v*v, 0) / buf.length);
    updateWaveformLevel(rms);
    const elapsed = Date.now() - recordStart;
    if (rms < SILENCE_THRESHOLD && elapsed > MIN_RECORD_MS) {
      silenceMs += 100;
      if (silenceMs >= SILENCE_STOP_MS) stopListening(false);
    } else {
      silenceMs = 0;
    }
  }, 100);
}

function stopListening(manual=false) {
  if (vadInterval) { clearInterval(vadInterval); vadInterval = null; }
  if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop();
  if (mediaStream) { mediaStream.getTracks().forEach(t => t.stop()); mediaStream = null; }
  if (audioCtx) { try { audioCtx.close(); } catch(e){} audioCtx = null; }
  if (manual) { setState("idle"); autoLive = false; }
  else {
    playFiller();        // ← langsung play saat VAD stop, sebelum ASR selesai
    setState("processing");
  }
}

// ═══════════════════════════════════════════════
// SEND AUDIO → ASR → STREAM
// ═══════════════════════════════════════════════
async function onRecordStop() {
  if (state === "idle") return;  // user stop manual

  const totalSize = audioChunks.reduce((s,c) => s+c.size, 0);
  if (totalSize < 2000) {
    setTranscript("[rekaman terlalu pendek]", null);
    autoLive ? setTimeout(startListening, 800) : setState("idle");
    return;
  }

  const blob = new Blob(audioChunks, { type: "audio/webm" });
  const form = new FormData();
  form.append("audio", blob, "rekam.webm");
  form.append("session_id", SESSION_ID);

  // ── ASR ──
  let teks = "";
  try {
    const r = await fetch("/api/listen", { method: "POST", body: form });
    const d = await r.json();
    if (!r.ok || d.error) {
      setTranscript(d.error || "ASR gagal", null);
      autoLive ? setTimeout(startListening, 1000) : setState("idle");
      return;
    }
    teks = d.teks;
  } catch(e) {
    setTranscript("Error: " + e.message, null);
    autoLive ? setTimeout(startListening, 1200) : setState("idle");
    return;
  }

  // Tampilkan transkripsi user langsung
  setTranscript(teks, null);
  showAtlasLoading(true);

  // ── Buka SSE stream ──
  openStream(teks);
}

// ═══════════════════════════════════════════════
// SSE STREAM
// ═══════════════════════════════════════════════
function openStream(teks) {
  closeStream();
  resetAudioQueue();
  streamDone = false;
  twFull = false;
  clearTypewriter();

  const url = `/api/stream?teks=${encodeURIComponent(teks)}&session_id=${encodeURIComponent(SESSION_ID)}`;
  sseSource = new EventSource(url);

  sseSource.addEventListener("text", e => {
    const d = JSON.parse(e.data);
    showAtlasLoading(false);
    showAtlasTr();
    if (d.full) {
      // Non-chat: paste langsung (typewriter dari awal)
      twFull = false;
      appendTypewriter(d.c);
    } else {
      appendTypewriter(d.c);
    }
  });

  sseSource.addEventListener("audio", e => {
    const d = JSON.parse(e.data);
    enqueueAudio(d.d);
  });

  sseSource.addEventListener("nav", e => {
    const d = JSON.parse(e.data);
    tampilNavToast(d.url);
    setTimeout(() => window.open(d.url, "_blank"), 700);
  });

  sseSource.addEventListener("done", () => {
    closeStream();
    streamDone = true;
    stopTypewriter();      // hilangkan cursor blink
    checkStreamAudioDone();
  });

  sseSource.onerror = () => {
    closeStream();
    streamDone = true;
    checkStreamAudioDone();
  };
}

function closeStream() {
  if (sseSource) { sseSource.close(); sseSource = null; }
}

// ═══════════════════════════════════════════════
// AUDIO QUEUE — gapless AudioContext scheduling
// ═══════════════════════════════════════════════
function getPlayCtx() {
  if (!playCtx || playCtx.state === "closed") {
    playCtx     = new AudioContext();
    nextStartAt = 0;
  }
  if (playCtx.state === "suspended") playCtx.resume();
  return playCtx;
}

async function enqueueAudio(b64) {
  chunksQueued++;
  const ctx = getPlayCtx();
  const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
  try {
    const audioBuf = await ctx.decodeAudioData(bytes.buffer);
    setState("speaking");

    const now     = ctx.currentTime;
    const startAt = Math.max(now + 0.05, nextStartAt);
    nextStartAt   = startAt + audioBuf.duration;

    const src = ctx.createBufferSource();
    src.buffer = audioBuf;
    src.connect(ctx.destination);
    src.start(startAt);
    currentSrc = src;

    src.onended = () => {
      chunksPlayed++;
      checkStreamAudioDone();
    };
  } catch(err) {
    console.warn("Audio decode err:", err);
    chunksPlayed++;
    checkStreamAudioDone();
  }
}

function resetAudioQueue() {
  if (currentSrc) { try { currentSrc.stop(); } catch(e){} currentSrc = null; }
  if (playCtx)    { try { playCtx.close();   } catch(e){} playCtx    = null; }
  chunksQueued = 0;
  chunksPlayed = 0;
  nextStartAt  = 0;
}

function interruptSpeaking() {
  closeStream();
  resetAudioQueue();
  streamDone = true;
  stopTypewriter();
  autoLive ? setTimeout(startListening, 400) : setState("idle");
}

function checkStreamAudioDone() {
  if (streamDone && chunksPlayed >= chunksQueued) {
    // Semua audio sudah selesai, stream juga done
    setTimeout(() => {
      if (autoLive) {
        setState("idle");
        setTimeout(startListening, 500);
      } else {
        setState("idle");
      }
    }, 300);
  }
}

// ═══════════════════════════════════════════════
// TYPEWRITER
// ═══════════════════════════════════════════════
function appendTypewriter(text) {
  twQueue += text;
  if (!twTimer) tickTypewriter();
}

function tickTypewriter() {
  const el = document.getElementById("tr-atlas");
  if (!el || !twQueue) {
    twTimer = null;
    return;
  }
  // Ambil beberapa karakter sekaligus (lebih smooth di teks panjang)
  const batch = twQueue.slice(0, 3);
  twQueue = twQueue.slice(3);
  el.textContent += batch;
  // Auto-scroll
  const area = document.getElementById("transcript-area");
  area.scrollTop = area.scrollHeight;
  twTimer = setTimeout(tickTypewriter, 14);
}

function stopTypewriter() {
  if (twTimer) { clearTimeout(twTimer); twTimer = null; }
  // Flush sisa
  const el = document.getElementById("tr-atlas");
  if (el && twQueue) { el.textContent += twQueue; twQueue = ""; }
  el && el.classList.remove("blink");
}

function clearTypewriter() {
  if (twTimer) { clearTimeout(twTimer); twTimer = null; }
  twQueue = "";
  const el = document.getElementById("tr-atlas");
  if (el) { el.textContent = ""; el.classList.add("blink"); }
}

// ═══════════════════════════════════════════════
// TRANSCRIPT UI
// ═══════════════════════════════════════════════
function setTranscript(kamu, atlas) {
  const area = document.getElementById("transcript-area");
  const ph   = document.getElementById("tr-placeholder");
  const cont = document.getElementById("tr-content");
  const trK  = document.getElementById("tr-kamu");

  area.classList.remove("kosong");
  ph.style.display   = "none";
  cont.style.display = "";
  if (kamu !== null) trK.textContent = kamu;

  document.getElementById("tr-atlas-wrap").style.display = "none";
  clearTypewriter();
}

function showAtlasTr() {
  document.getElementById("tr-atlas-wrap").style.display = "";
  document.getElementById("tr-loading").style.display    = "none";
}

function showAtlasLoading(show) {
  const wrap  = document.getElementById("tr-atlas-wrap");
  const ldg   = document.getElementById("tr-loading");
  if (show) {
    wrap.style.display = "";
    ldg.style.display  = "";
    document.getElementById("tr-atlas").textContent = "";
  } else {
    ldg.style.display = "none";
  }
}

// ═══════════════════════════════════════════════
// TEXT INPUT
// ═══════════════════════════════════════════════
function onKey(e) {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); kirimInput(); }
}
function resize(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 100) + "px";
}
async function kirimInput() {
  const inp = document.getElementById("inp");
  const t   = inp.value.trim();
  if (!t) return;
  inp.value = ""; inp.style.height = "auto";
  kirimTeks(t);
}
function kirimTeks(t) {
  if (state === "listening") stopListening(true);
  interruptSpeaking();

  autoLive = true;
  setState("processing");
  setTranscript(t, null);
  showAtlasLoading(true);
  openStream(t);
}

// ═══════════════════════════════════════════════
// WAVEFORM
// ═══════════════════════════════════════════════
function updateWaveformLevel(rms) { waveLevel = Math.min(1, rms * 14); }

function startWaveform() {
  cvs.style.opacity = "1";
  if (waveAnim) return;
  let t = 0;
  function draw() {
    t += 0.08;
    ctx2.clearRect(0, 0, cvs.width, cvs.height);
    const bars = 38;
    const bw   = cvs.width / bars;
    ctx2.fillStyle = "#B31818";
    for (let i = 0; i < bars; i++) {
      const h = (Math.sin(t + i * 0.5) * 0.5 + 0.5) * waveLevel * cvs.height * 0.85 + 2;
      const x = i * bw + 1;
      const y = (cvs.height - h) / 2;
      ctx2.beginPath();
      ctx2.roundRect(x, y, bw-2, h, 2);
      ctx2.fill();
    }
    waveAnim = requestAnimationFrame(draw);
  }
  draw();
}

function stopWaveform() {
  cvs.style.opacity = "0";
  if (waveAnim) { cancelAnimationFrame(waveAnim); waveAnim = null; }
  ctx2.clearRect(0, 0, cvs.width, cvs.height);
  waveLevel = 0;
}

// ═══════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════
function tampilNavToast(url) {
  const t = document.getElementById("nav-toast");
  t.textContent = "↗ Membuka " + url;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 3000);
}

async function clearChat() {
  await fetch("/api/clear", {
    method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({ session_id: SESSION_ID })
  });
  document.getElementById("tr-placeholder").style.display = "";
  document.getElementById("tr-content").style.display     = "none";
  document.getElementById("transcript-area").classList.add("kosong");
}
</script>
</body>
</html>
"""

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
    print(f"  TTS  : {TTS_VOICE}")
    print("=" * 54)
    print()
    print("  Memuat dataset...", flush=True)
    _get_data()
    print()
    print("  Memuat Piper TTS (download ~65 MB jika belum ada)...", flush=True)
    _setup_piper()
    _pregenerate_filler()
    print()
    print("  Memuat Whisper (download ~250 MB jika belum ada)...", flush=True)
    _get_whisper()
    print()
    print(f"  Server siap → http://localhost:{WEB_PORT}")
    print()
    print("  [Ctrl+C] untuk menghentikan")
    print()

    threading.Timer(1.2, lambda: webbrowser.open(f"http://localhost:{WEB_PORT}")).start()
    app.run(host="0.0.0.0", port=WEB_PORT, debug=False, use_reloader=False, threaded=True)
