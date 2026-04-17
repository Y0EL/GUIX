"""
atlas_text.py — Mode Ketik untuk Test Atlas tanpa Mikrofon/TTS

Jalankan:
    python atlas/atlas_text.py

Ketik perintah langsung, Atlas merespons via teks di terminal.
Navigasi tetap buka browser. Ollama opsional (bisa skip).
Tekan Ctrl+C atau ketik 'keluar' untuk berhenti.
"""

import re
import sys
import webbrowser
import threading
from pathlib import Path

# Pastikan bisa import atlas_data dari folder yang sama
sys.path.insert(0, str(Path(__file__).parent))
from atlas_data import AtlasData

# ============================================================
# CONFIG
# ============================================================
OLLAMA_MODEL   = "qwen3.5:latest"
UIX_BASE_URL   = "http://localhost:5173"
OLLAMA_TIMEOUT = 45

# ============================================================
# PETA NAVIGASI (sama persis dengan atlas.py)
# ============================================================
PETA_HALAMAN: dict[str, str] = {
    "beranda":           "/",
    "overview":          "/",
    "ikhtisar":          "/",
    "home":              "/",
    "peringatan":        "/alert-center",
    "alert":             "/alert-center",
    "pusat peringatan":  "/alert-center",
    "insiden":           "/incident-queue",
    "antrean":           "/incident-queue",
    "antrean insiden":   "/incident-queue",
    "peta":              "/map-intelligence",
    "map":               "/map-intelligence",
    "intelijen peta":    "/map-intelligence",
    "pencarian":         "/search",
    "cari":              "/search",
    "search":            "/search",
    "link analysis":     "/link-analysis",
    "jaringan":          "/link-analysis",
    "analisis tautan":   "/link-analysis",
    "timeline":          "/timeline",
    "kronologi":         "/timeline",
    "narasi":            "/narrative",
    "tren":              "/narrative",
    "narrative":         "/narrative",
    "kanvas":            "/canvas",
    "investigasi":       "/canvas",
    "canvas":            "/canvas",
    "konten":            "/content",
    "bukti":             "/content",
    "content":           "/content",
    "kasus workspace":   "/case-workspace",
    "workspace":         "/case-workspace",
    "briefing":          "/briefing",
    "fusion":            "/fusion",
    "fusion board":      "/fusion",
    "admin":             "/admin",
    "sistem":            "/admin",
    "audit":             "/admin",
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
    return re.sub(r"<think>.*?</think>", "", teks, flags=re.DOTALL).strip()

def atlas_print(teks: str) -> None:
    """Cetak respons Atlas dengan format yang jelas."""
    print(f"\n  🤖  {teks}\n")

def status_print(teks: str) -> None:
    """Cetak status proses (bukan jawaban akhir)."""
    print(f"  ⏳  {teks}", flush=True)

# ============================================================
# BRAIN (Ollama) — opsional
# ============================================================

_ollama_ok = False
try:
    import ollama as _ollama_lib
    _client = _ollama_lib.Client(host="http://localhost:11434")
    _history: list = []

    def _system_prompt(ctx: str) -> str:
        return (
            "Kamu adalah Atlas, asisten AI untuk sistem intelijen UIX. "
            "Berbicara dalam Bahasa Indonesia yang natural dan singkat. "
            "Jawaban maksimal 3 kalimat. "
            "Jangan gunakan markdown atau simbol apapun. /no_think\n\n" + ctx
        )

    _ollama_ok = True
except ImportError:
    pass


def tanya_ollama(teks: str, ctx: str = "") -> str:
    if not _ollama_ok:
        return "Ollama tidak tersedia. Install dengan: pip install ollama"
    _history.append({"role": "user", "content": teks})
    messages = [{"role": "system", "content": _system_prompt(ctx)}] + _history[-8:]
    result_box: list[str] = []

    def _worker():
        try:
            resp = _client.chat(
                model=OLLAMA_MODEL,
                messages=messages,
                think=False,
                options={"temperature": 0.6, "num_predict": 256},
            )
            raw = resp.message.content
            result_box.append(raw.strip())
        except Exception as e:
            result_box.append(f"Error Ollama: {str(e)[:120]}")

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    elapsed = 0
    while t.is_alive():
        t.join(timeout=10)
        elapsed += 10
        if t.is_alive():
            if elapsed < OLLAMA_TIMEOUT:
                status_print(f"Masih berpikir... sudah {elapsed} detik")
            else:
                return "Waktu tunggu Ollama habis. Coba lagi atau periksa 'ollama serve'."
    jawaban = result_box[0] if result_box else "Tidak ada respons dari Ollama."
    _history.append({"role": "assistant", "content": jawaban})
    return jawaban

# ============================================================
# INTENT CLASSIFIER (sama logika dengan atlas.py)
# ============================================================

def tentukan_intent(teks: str) -> tuple[str, dict]:
    t = teks.lower().strip()

    # --- NAVIGASI ---
    for trigger in TRIGGER_NAVIGASI:
        if trigger in t:
            sisa = t[t.find(trigger) + len(trigger):].strip()
            for kw, path in PETA_HALAMAN.items():
                if kw in sisa or kw in t:
                    return "navigasi", {"path": path, "nama": NAMA_HALAMAN.get(path, path)}
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
        return "detail_kasus", {"query": m.group(2).strip()}

    # --- CARI PROFIL ---
    m = re.search(r"(siapa|cari profil|profil|info tentang|cek profil)\s+(.+)", t)
    if m:
        q = m.group(2).strip()
        if q not in {"itu", "ini", "dia", "mereka", "kasus", "berita"}:
            return "cari_profil", {"query": q}

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

    # --- KLASTER ---
    if re.search(r"(klaster|kluster|propaganda|narasi koordinasi|pesan terkoordinasi)", t):
        return "klaster", {}

    # --- BANTUAN ---
    if re.search(r"(help|bantuan|apa yang bisa|perintah apa|daftar perintah)", t):
        return "bantuan", {}

    return "chat", {}

# ============================================================
# HANDLERS
# ============================================================

def handle(teks: str, data: AtlasData) -> None:
    intent, extras = tentukan_intent(teks)
    print(f"  [intent: {intent}]")

    if intent == "navigasi":
        path  = extras["path"]
        nama  = extras["nama"]
        url   = UIX_BASE_URL + path
        atlas_print(f"Membuka halaman {nama}.")
        print(f"  [NAV] {url}")
        webbrowser.open(url)

    elif intent == "navigasi_tidak_jelas":
        daftar = ", ".join(list(PETA_HALAMAN.keys())[:10])
        atlas_print(f"Halaman tidak dikenali. Kata kunci yang tersedia: {daftar}, ...")

    elif intent == "daftar_kasus":
        kasus_list = data.daftar_kasus()
        baris = [f"Ada {len(kasus_list)} kasus di sistem:"]
        for k in kasus_list:
            baris.append(
                f"  • {k['id_kasus'].replace('kasus-','').replace('-',' ').title()}: "
                f"{k['judul']} — status {k.get('status','?')}"
            )
        atlas_print("\n".join(baris))

    elif intent == "detail_kasus":
        q = extras.get("query", "")
        status_print(f"Membaca detail kasus '{q}'...")
        detail = data.baca_detail_kasus(q)
        atlas_print(detail)

    elif intent == "cari_profil":
        q = extras.get("query", "")
        status_print(f"Mencari profil '{q}'...")
        hasil = data.cari_profil(q)
        if not hasil:
            atlas_print(f"Tidak ada profil yang cocok dengan '{q}'.")
        else:
            baris = [f"Ditemukan {len(hasil)} profil:"]
            for p in hasil:
                baris.append(
                    f"  • {p['nama_lengkap']} — {p.get('kota','?')}, {p.get('provinsi','?')}"
                    + (f" | kasus: {', '.join(p.get('tautan_kasus',[]))}" if p.get("tautan_kasus") else "")
                )
            atlas_print("\n".join(baris))

    elif intent == "berita_terbaru":
        status_print("Membaca berita terbaru...")
        berita = data.baca_berita_terbaru(5)
        baris = [f"Lima berita terbaru:"]
        for i, b in enumerate(berita, 1):
            tgl = b.get("published_at", "")[:10]
            baris.append(f"  {i}. [{b.get('kategori','?')}] {b['judul']} ({tgl})")
        atlas_print("\n".join(baris))

    elif intent == "cari_berita":
        q = extras.get("query", "")
        status_print(f"Mencari berita '{q}'...")
        hasil = data.cari_berita(q)
        if not hasil:
            atlas_print(f"Tidak ada berita terkait '{q}'.")
        else:
            baris = [f"Ditemukan {len(hasil)} berita untuk '{q}':"]
            for b in hasil:
                baris.append(f"  • [{b.get('kategori','?')}] {b['judul']} — {b.get('lokasi','?')}")
            atlas_print("\n".join(baris))

    elif intent == "peringatan":
        status_print("Membaca peringatan aktif...")
        peringatan = data.baca_peringatan_aktif(5)
        if not peringatan:
            atlas_print("Tidak ada peringatan aktif di dataset.")
        else:
            baris = [f"Top {len(peringatan)} peringatan aktif:"]
            for p in peringatan:
                kid = p.get("id_kasus","?").replace("kasus-","").replace("-"," ")
                baris.append(
                    f"  • [{p.get('tingkat_keparahan','?').upper()}] {kid}: "
                    f"{p.get('deskripsi','-')[:80]}"
                )
            atlas_print("\n".join(baris))

    elif intent == "status":
        status_print("Membaca ringkasan sistem...")
        atlas_print(data.ringkas_sistem())

    elif intent == "klaster":
        status_print("Membaca klaster pesan terkoordinasi...")
        klaster = data.baca_klaster_kritis(3)
        if not klaster:
            atlas_print("Tidak ada data klaster pesan.")
        else:
            baris = [f"Top {len(klaster)} klaster pesan terkoordinasi:"]
            for kp in klaster:
                baris.append(
                    f"  • \"{kp['frasa_kanonik'][:60]}\" "
                    f"— kemiripan {kp['kemiripan_copy']:.0%}, "
                    f"{kp.get('jumlah_posting','?')} posting"
                )
            atlas_print("\n".join(baris))

    elif intent == "bantuan":
        atlas_print(
            "Perintah yang tersedia:\n"
            "  Navigasi   : 'buka peta', 'buka timeline', 'buka kanvas', dst.\n"
            "  Kasus      : 'daftar kasus', 'kasus kebakaran', 'ceritakan kasus propaganda'\n"
            "  Profil     : 'siapa Ahmad', 'cari profil Winda'\n"
            "  Berita     : 'berita terbaru', 'cari berita banjir'\n"
            "  Peringatan : 'ada peringatan apa'\n"
            "  Status     : 'status sistem', 'ringkasan'\n"
            "  Klaster    : 'klaster pesan', 'narasi koordinasi'\n"
            "  Chat bebas : pertanyaan apapun → diteruskan ke Ollama"
        )

    elif intent == "chat":
        status_print("Mengirim ke Ollama, mohon tunggu...")
        jawaban = tanya_ollama(teks, data.ringkasan_untuk_llm())
        atlas_print(jawaban)

# ============================================================
# MAIN LOOP
# ============================================================

def main() -> None:
    sep = "=" * 54
    print()
    print(sep)
    print("  🤖  ATLAS — Mode Teks (tanpa mikrofon / TTS)")
    print(f"  UIX URL  : {UIX_BASE_URL}")
    print(f"  Ollama   : {'✅ tersambung' if _ollama_ok else '⚠️  tidak tersedia (install + serve)'}")
    print(sep)
    print()
    print("  Memuat dataset UIX...")
    data = AtlasData(verbose=True)
    print()
    print(sep)
    print("  Ketik perintahmu. 'bantuan' untuk daftar perintah. 'keluar' untuk berhenti.")
    print(sep)
    print()

    while True:
        try:
            teks = input("  Kamu: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n  Atlas: Sampai jumpa!")
            sys.exit(0)

        if not teks:
            continue
        if teks.lower() in {"keluar", "exit", "quit", "bye"}:
            print("\n  Atlas: Sampai jumpa!")
            sys.exit(0)

        handle(teks, data)

if __name__ == "__main__":
    main()
