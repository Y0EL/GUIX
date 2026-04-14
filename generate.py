"""
Liputan9 — Synthetic News Dataset Generator
=============================================
GPT-4o-mini untuk teks, DALL-E 3 untuk gambar
Fully async + parallel → 500 artikel dalam hitungan menit

Speed: ~20 artikel/menit (GPT) | ~5 gambar/menit (DALL-E)
"""

import argparse
import asyncio
import json
import os
import random
import sys
import time
import uuid
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from openai import AsyncOpenAI
except ImportError:
    print("Install dulu: pip install openai")
    sys.exit(1)

try:
    from faker import Faker
except ImportError:
    print("Install dulu: pip install faker")
    sys.exit(1)

try:
    from tqdm.asyncio import tqdm as atqdm
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    print("Tip: pip install tqdm  ← buat progress bar")
    HAS_TQDM = False
    atqdm = None

# ──────────────────────────────────────────
# PORTAL CONFIG
# ──────────────────────────────────────────

PORTAL_NAME    = "Liputan9"
PORTAL_TAGLINE = "Berita Terdepan, Terpercaya"
PORTAL_DOMAIN  = "liputan9.co.id"
BRAND_COLOR    = "#F97316"   # orange-500
BRAND_DARK     = "#EA580C"   # orange-600
BRAND_LIGHT    = "#FFF7ED"   # orange-50

# ──────────────────────────────────────────
# CONCURRENCY LIMITS
# ──────────────────────────────────────────

GPT_CONCURRENCY   = 20   # max concurrent GPT requests
DALLE_CONCURRENCY = 3    # DALL-E rate limit lebih ketat (5 img/min on standard)
DALLE_DELAY       = 13   # detik antar batch DALL-E

# ──────────────────────────────────────────
# DATA
# ──────────────────────────────────────────

PROVINSI_INDONESIA = [
    "Aceh", "Sumatera Utara", "Sumatera Barat", "Riau", "Kepulauan Riau",
    "Jambi", "Sumatera Selatan", "Bengkulu", "Lampung", "Bangka Belitung",
    "DKI Jakarta", "Jawa Barat", "Banten", "Jawa Tengah", "DI Yogyakarta",
    "Jawa Timur", "Bali", "Nusa Tenggara Barat", "Nusa Tenggara Timur",
    "Kalimantan Barat", "Kalimantan Tengah", "Kalimantan Selatan",
    "Kalimantan Timur", "Kalimantan Utara", "Sulawesi Utara", "Gorontalo",
    "Sulawesi Tengah", "Sulawesi Barat", "Sulawesi Selatan", "Sulawesi Tenggara",
    "Maluku", "Maluku Utara", "Papua", "Papua Barat",
]

KATEGORI_BERITA = [
    ("Nasional", [
        "kebijakan baru pemerintah pusat mengenai {topik} menuai pro dan kontra",
        "Presiden umumkan program nasional baru di bidang {topik}",
        "DPR sahkan RUU {topik} setelah sidang panjang",
        "menteri {topik} dicopot dari jabatan oleh presiden",
        "anggaran {topik} dipangkas besar-besaran dalam APBN perubahan",
    ]),
    ("Hukum & Kriminal", [
        "penembakan di {lokasi} oleh kelompok bersenjata tidak dikenal",
        "pejabat {lokasi} ditangkap KPK terkait suap proyek infrastruktur",
        "kasus pembunuhan di {lokasi} masuk persidangan, tersangka baru terungkap",
        "sindikat narkotika jaringan internasional digerebek di {lokasi}",
        "hakim pengadilan {lokasi} dilaporkan menerima suap",
        "terdakwa korupsi anggaran {lokasi} divonis bebas, publik geram",
        "sindikat perdagangan manusia digerebek di {lokasi}",
        "perampokan bersenjata di bank {lokasi} oleh kawanan bertopeng",
    ]),
    ("Keamanan", [
        "ledakan misterius di dekat kantor pemerintah {lokasi}",
        "ancaman bom diterima pejabat daerah {lokasi}",
        "serangan terhadap pos keamanan di wilayah perbatasan {lokasi}",
        "konflik lahan berujung bentrokan berdarah di {lokasi}",
        "kelompok bersenjata serang warga sipil di pedalaman {lokasi}",
        "demo besar di {lokasi} ricuh, polisi kerahkan water cannon",
    ]),
    ("Daerah", [
        "banjir bandang di {lokasi} memaksa ribuan warga mengungsi",
        "longsor di {lokasi} menimbun pemukiman warga",
        "kecelakaan maut di jalan tol {lokasi} menewaskan {n} orang",
        "kebakaran pasar tradisional di {lokasi} hanguskan ratusan kios",
        "warga {lokasi} protes pembangunan pabrik, blokir jalan utama",
        "jembatan di {lokasi} ambruk saat dilintasi kendaraan berat",
    ]),
    ("Ekonomi", [
        "harga {komoditas} melonjak di pasar {lokasi}, warga mengeluh",
        "PHK massal di pabrik {lokasi}, ribuan buruh kehilangan pekerjaan",
        "investasi asing masuk ke {lokasi}, ribuan lapangan kerja terbuka",
        "UMKM di {lokasi} kolaps akibat persaingan produk impor",
        "nilai tukar rupiah melemah pengaruhi harga {komoditas}",
    ]),
    ("Sosial", [
        "viral video penganiayaan di {lokasi}, pelaku masih berkeliaran",
        "guru di {lokasi} dianiaya orang tua murid di dalam kelas",
        "konflik suku di {lokasi} meledak, satu desa hangus terbakar",
        "pasien meninggal di IGD {lokasi} diduga akibat malapraktik",
        "anak hilang di {lokasi} ditemukan dalam kondisi mengenaskan",
        "kasus bullying parah di sekolah {lokasi} viral di media sosial",
    ]),
    ("Olahraga", [
        "timnas Indonesia kalahkan {lawan} dengan skor telak di laga persahabatan",
        "atlet {cabor} Indonesia raih medali emas di kejuaraan dunia",
        "klub sepak bola {lokasi} degradasi setelah kekalahan beruntun",
        "pemain bintang {cabor} asal Indonesia ditawar klub Eropa",
        "skandal pengaturan skor guncang liga {cabor} Indonesia",
    ]),
    ("Teknologi", [
        "startup teknologi asal {lokasi} berhasil raih pendanaan seri A",
        "penipuan online berbasis AI marak di {lokasi}, korban ratusan orang",
        "pemerintah {lokasi} luncurkan aplikasi layanan publik berbasis AI",
        "kebocoran data warga {lokasi} dari sistem pemerintah daerah",
        "perusahaan teknologi besar tutup kantor di {lokasi}, karyawan dirumahkan",
    ]),
]

TOPIK_NASIONAL = ["pendidikan", "kesehatan", "infrastruktur", "pangan", "energi", "pertahanan", "hukum"]
KOMODITAS = ["beras", "minyak goreng", "cabai", "kedelai", "gula", "daging sapi", "BBM"]
LAWAN_TIMNAS = ["Vietnam", "Thailand", "Malaysia", "Filipina", "Myanmar", "Kamboja"]
CABOR = ["bulu tangkis", "sepak bola", "tinju", "angkat besi", "renang", "atletik"]

REPORTER_NAMES = [
    "Ahmad Faruqi", "Siti Rahayu", "Budi Santoso", "Dewi Lestari",
    "Rizky Pratama", "Nur Hidayah", "Andi Kurniawan", "Fitri Wahyuni",
    "Doni Setiawan", "Rahmawati Putri", "Hendra Gunawan", "Yuni Astuti",
    "Bagas Prasetyo", "Mira Kusuma", "Fauzi Ramadhan", "Indah Permata",
    "Teguh Wibowo", "Lestari Ningrum", "Arif Budiman", "Sari Dewanti",
]

# ──────────────────────────────────────────
# GPT ASYNC GENERATOR
# ──────────────────────────────────────────

SYSTEM_PROMPT = """Kamu adalah jurnalis senior Indonesia dengan pengalaman 15 tahun di media nasional.
Tulis artikel berita dalam bahasa Indonesia yang sangat realistis, persis seperti portal berita Liputan6, Kompas, atau Detik.

Aturan:
- Gaya jurnalistik piramida terbalik (fakta terpenting di awal)
- 3-5 paragraf, total 250-400 kata
- Sertakan kutipan narasumber yang realistis (nama, jabatan, institusi)
- Detail spesifik: waktu, tanggal, lokasi, angka
- Jangan pernah sebut artikel ini fiktif atau sintetis
- Akhiri dengan perkembangan terkini atau rencana tindak lanjut

Output JSON ONLY (tanpa markdown):
{"judul":"...","subjudul":"...","isi":"...","kutipan_utama":"...","narasumber":"...","jabatan_narasumber":"..."}"""

async def generate_article_async(client: AsyncOpenAI, semaphore: asyncio.Semaphore,
                                  topik: str, lokasi: str, provinsi: str, tanggal_str: str):
    async with semaphore:
        prompt = f"""Tulis artikel berita tentang: {topik}
Lokasi: {lokasi}, {provinsi}
Tanggal: {tanggal_str}

Buat sangat realistis seperti berita asli Indonesia."""

        for attempt in range(3):
            try:
                resp = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.85,
                    max_tokens=800,
                    response_format={"type": "json_object"},
                )
                return json.loads(resp.choices[0].message.content)
            except Exception as e:
                if attempt == 2:
                    print(f"\n  [GPT error] {e}")
                    return None
                await asyncio.sleep(2 ** attempt)

# ──────────────────────────────────────────
# DALL-E ASYNC GENERATOR
# ──────────────────────────────────────────

VISUAL_MAP = {
    "Nasional":        "Indonesian government officials at a press conference in Jakarta, formal setting, photojournalism",
    "Hukum & Kriminal":"Indonesian police officers at a crime scene, forensic team, police tape, documentary photo",
    "Keamanan":        "Indonesian security forces in formation, official military briefing, news photography",
    "Daerah":          "Emergency response team in Indonesia, rescue workers, local area, documentary photo",
    "Ekonomi":         "Indonesian market scene, traders and buyers, economic activity, photojournalism",
    "Sosial":          "Indonesian community gathering, social event, people in urban setting, news photo",
    "Olahraga":        "Indonesian athletes competing, sports arena, crowd cheering, sports photography",
    "Teknologi":       "Technology conference in Jakarta, startup event, people with devices, modern setting",
}

async def generate_image_async(client: AsyncOpenAI, semaphore: asyncio.Semaphore,
                                 kategori: str, lokasi: str, article_id: str, out_dir: Path):
    async with semaphore:
        prompt = VISUAL_MAP.get(kategori,
            f"News photo from Indonesia, {lokasi}, documentary journalism style, realistic")

        for attempt in range(2):
            try:
                resp = await client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    size="1792x1024",
                    quality="standard",
                    n=1,
                )
                url = resp.data[0].url
                img_filename = f"{article_id}.jpg"
                img_path = out_dir / "images" / img_filename

                # Download (sync dalam thread pool)
                loop = asyncio.get_event_loop()
                ok = await loop.run_in_executor(None, _download_img, url, str(img_path))
                if ok:
                    return img_filename
            except Exception as e:
                if attempt == 1:
                    return None
                await asyncio.sleep(DALLE_DELAY)
        return None

def _download_img(url: str, path: str) -> bool:
    try:
        urllib.request.urlretrieve(url, path)
        return True
    except:
        return False

# ──────────────────────────────────────────
# HELPER
# ──────────────────────────────────────────

BULAN = {1:"Januari",2:"Februari",3:"Maret",4:"April",5:"Mei",6:"Juni",
         7:"Juli",8:"Agustus",9:"September",10:"Oktober",11:"November",12:"Desember"}
BULAN_SHORT = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"Mei",6:"Jun",
               7:"Jul",8:"Agu",9:"Sep",10:"Okt",11:"Nov",12:"Des"}

def random_topik(faker):
    kat_name, templates = random.choice(KATEGORI_BERITA)
    template = random.choice(templates)
    lokasi = faker.city()
    provinsi = random.choice(PROVINSI_INDONESIA)
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    pub = now - timedelta(days=random.randint(0, 90), minutes=random.randint(0, 1440))
    pub_local = pub + timedelta(hours=7)
    tanggal_str = f"{pub_local.day} {BULAN_SHORT[pub_local.month]} {pub_local.year}"

    topik = template.format(
        lokasi=lokasi,
        provinsi=provinsi,
        n=random.randint(2, 15),
        topik=random.choice(TOPIK_NASIONAL),
        komoditas=random.choice(KOMODITAS),
        lawan=random.choice(LAWAN_TIMNAS),
        cabor=random.choice(CABOR),
    )
    return kat_name, topik, lokasi, provinsi, pub, pub_local, tanggal_str

# ──────────────────────────────────────────
# HTML TEMPLATES — LIPUTAN9
# ──────────────────────────────────────────

NAVBAR_LINKS = [
    ("Nasional", "nasional"),
    ("Hukum & Kriminal", "hukum"),
    ("Keamanan", "keamanan"),
    ("Daerah", "daerah"),
    ("Ekonomi", "ekonomi"),
    ("Sosial", "sosial"),
    ("Olahraga", "olahraga"),
    ("Teknologi", "teknologi"),
]

CSS_VARS = f"""
  --brand:     {BRAND_COLOR};
  --brand-dk:  {BRAND_DARK};
  --brand-lt:  {BRAND_LIGHT};
  --text:      #1a1a1a;
  --text-muted:#6b7280;
  --border:    #e5e7eb;
  --bg:        #f9fafb;
  --card:      #ffffff;
"""

BASE_CSS = f"""
<style>
:root {{{CSS_VARS}}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);font-size:15px}}
a{{color:inherit;text-decoration:none}}

/* ── Topbar ── */
.topbar{{background:#1a1a1a;padding:6px 0;font-size:11px;color:#9ca3af;font-family:monospace}}
.topbar-inner{{max-width:1280px;margin:0 auto;padding:0 20px;display:flex;justify-content:space-between;align-items:center}}
.topbar a{{color:#9ca3af;margin-left:16px}}
.topbar a:hover{{color:#fff}}

/* ── Navbar ── */
.navbar{{background:#fff;border-bottom:3px solid var(--brand);position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
.navbar-inner{{max-width:1280px;margin:0 auto;padding:0 20px;display:flex;align-items:stretch;gap:0}}
.nav-logo{{display:flex;align-items:center;padding:12px 24px 12px 0;border-right:1px solid var(--border);margin-right:8px}}
.nav-logo .wordmark{{font-size:1.75em;font-weight:900;letter-spacing:-1px;line-height:1;color:var(--brand)}}
.nav-logo .wordmark span{{color:#1a1a1a}}
.nav-logo .tagline{{font-size:9px;color:var(--text-muted);letter-spacing:.5px;margin-top:2px;text-transform:uppercase}}
.nav-links{{display:flex;align-items:stretch;flex:1;overflow-x:auto;scrollbar-width:none}}
.nav-links::-webkit-scrollbar{{display:none}}
.nav-links a{{display:flex;align-items:center;padding:0 14px;font-size:12.5px;font-weight:600;color:#374151;white-space:nowrap;border-bottom:3px solid transparent;margin-bottom:-3px;transition:.15s}}
.nav-links a:hover,.nav-links a.active{{color:var(--brand);border-bottom-color:var(--brand)}}
.nav-search{{display:flex;align-items:center;padding:8px 0 8px 16px;border-left:1px solid var(--border);margin-left:auto}}
.nav-search input{{border:1px solid var(--border);border-radius:20px;padding:5px 12px 5px 32px;font-size:12px;background:var(--bg);width:180px;outline:none}}
.nav-search input:focus{{border-color:var(--brand);background:#fff}}
.search-icon{{position:relative;}}
.search-icon::before{{content:'🔍';font-size:12px;position:absolute;left:10px;top:50%;transform:translateY(-50%);pointer-events:none;z-index:1}}

/* ── Breaking Ticker ── */
.ticker{{background:var(--brand);color:#fff;padding:5px 0;overflow:hidden;font-size:12px;font-weight:600}}
.ticker-inner{{max-width:1280px;margin:0 auto;padding:0 20px;display:flex;align-items:center;gap:12px}}
.ticker-label{{background:#fff;color:var(--brand);padding:2px 10px;border-radius:2px;font-size:11px;font-weight:800;white-space:nowrap;flex-shrink:0}}
.ticker-wrap{{overflow:hidden;flex:1}}
.ticker-track{{display:flex;gap:40px;white-space:nowrap;animation:ticker 40s linear infinite}}
.ticker-track span{{white-space:nowrap}}
@keyframes ticker{{0%{{transform:translateX(0)}}100%{{transform:translateX(-50%)}}}}

/* ── Layout ── */
.container{{max-width:1280px;margin:24px auto;padding:0 20px;display:grid;grid-template-columns:1fr 340px;gap:28px}}
.container.full{{grid-template-columns:1fr}}

/* ── Cards ── */
.card{{background:var(--card);border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08);transition:.2s}}
.card:hover{{box-shadow:0 4px 16px rgba(0,0,0,.12);transform:translateY(-1px)}}
.card a:hover .card-title{{color:var(--brand)}}

/* ── Hero Card ── */
.hero-card{{position:relative;border-radius:8px;overflow:hidden;margin-bottom:24px;cursor:pointer}}
.hero-card img{{width:100%;height:420px;object-fit:cover;display:block}}
.hero-overlay{{position:absolute;bottom:0;left:0;right:0;background:linear-gradient(transparent,rgba(0,0,0,.85));padding:32px 24px 24px}}
.hero-cat{{display:inline-block;background:var(--brand);color:#fff;font-size:11px;font-weight:700;padding:3px 10px;border-radius:2px;margin-bottom:10px;text-transform:uppercase;letter-spacing:.5px}}
.hero-title{{font-size:1.6em;font-weight:800;color:#fff;line-height:1.25;margin-bottom:8px}}
.hero-meta{{font-size:12px;color:rgba(255,255,255,.7);display:flex;gap:12px}}

/* ── Grid Cards ── */
.grid-3{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:24px}}
.grid-2{{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin-bottom:24px}}
.card-img{{width:100%;height:170px;object-fit:cover}}
.card-body{{padding:14px}}
.card-cat{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--brand);margin-bottom:6px}}
.card-title{{font-size:.9em;font-weight:700;line-height:1.4;color:var(--text);margin-bottom:8px;transition:.15s}}
.card-meta{{font-size:11px;color:var(--text-muted);display:flex;gap:8px;flex-wrap:wrap}}

/* ── List Cards (sidebar style) ── */
.list-card{{display:flex;gap:12px;padding:14px 0;border-bottom:1px solid var(--border)}}
.list-card:last-child{{border-bottom:none}}
.list-card img{{width:88px;height:66px;object-fit:cover;border-radius:4px;flex-shrink:0}}
.list-card-body{{flex:1;min-width:0}}
.list-card-cat{{font-size:10px;font-weight:700;color:var(--brand);text-transform:uppercase;margin-bottom:4px}}
.list-card-title{{font-size:.82em;font-weight:700;line-height:1.4;color:var(--text);transition:.15s}}
.list-card:hover .list-card-title{{color:var(--brand)}}
.list-card-meta{{font-size:10.5px;color:var(--text-muted);margin-top:4px}}

/* ── Sidebar ── */
.sidebar-widget{{background:var(--card);border-radius:8px;padding:20px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.widget-title{{font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.8px;color:var(--text);border-left:3px solid var(--brand);padding-left:10px;margin-bottom:16px}}
.sidebar-rank-item{{display:flex;gap:12px;padding:10px 0;border-bottom:1px solid var(--border);align-items:flex-start}}
.sidebar-rank-item:last-child{{border-bottom:none}}
.rank-num{{font-size:1.4em;font-weight:900;color:var(--border);line-height:1;width:24px;flex-shrink:0}}
.sidebar-rank-item:nth-child(1) .rank-num{{color:var(--brand)}}
.sidebar-rank-item:nth-child(2) .rank-num{{color:#f59e0b}}
.sidebar-rank-item:nth-child(3) .rank-num{{color:#6b7280}}
.rank-title{{font-size:.82em;font-weight:600;line-height:1.4;color:var(--text);transition:.15s}}
.sidebar-rank-item:hover .rank-title{{color:var(--brand)}}
.rank-meta{{font-size:10.5px;color:var(--text-muted);margin-top:3px}}

/* ── Section Header ── */
.section-hdr{{display:flex;align-items:center;gap:12px;margin-bottom:16px;border-bottom:2px solid var(--border);padding-bottom:10px}}
.section-hdr h2{{font-size:14px;font-weight:800;text-transform:uppercase;letter-spacing:.6px}}
.section-hdr .line{{flex:1;height:2px;background:linear-gradient(90deg,var(--brand),transparent)}}
.section-hdr a{{font-size:11px;color:var(--brand);font-weight:600}}

/* ── Article Page ── */
.art-container{{max-width:860px;margin:28px auto;padding:0 20px}}
.art-breadcrumb{{font-size:11px;color:var(--text-muted);margin-bottom:16px;display:flex;gap:6px;align-items:center}}
.art-breadcrumb a{{color:var(--brand)}}
.art-cat-badge{{display:inline-block;background:var(--brand);color:#fff;font-size:11px;font-weight:700;padding:3px 12px;border-radius:2px;text-transform:uppercase;letter-spacing:.5px;margin-bottom:12px}}
.art-title{{font-size:2em;font-weight:900;line-height:1.2;color:var(--text);margin-bottom:12px;font-family:'Georgia',serif}}
.art-subjudul{{font-size:1.1em;color:#4b5563;line-height:1.6;margin-bottom:16px;font-style:italic;border-left:3px solid var(--brand);padding-left:14px}}
.art-meta{{font-size:12px;color:var(--text-muted);display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap;padding-bottom:16px;border-bottom:1px solid var(--border)}}
.art-meta .author{{color:var(--brand);font-weight:700}}
.art-hero{{width:100%;border-radius:8px;margin-bottom:8px;max-height:500px;object-fit:cover;display:block}}
.art-caption{{font-size:11.5px;color:var(--text-muted);margin-bottom:28px;font-style:italic}}
.art-body{{font-size:1em;line-height:1.85;color:#374151;font-family:'Georgia',serif}}
.art-body p{{margin-bottom:18px}}
.art-body blockquote{{border-left:4px solid var(--brand);padding:12px 18px;margin:24px 0;background:var(--brand-lt);border-radius:0 6px 6px 0;font-style:italic;color:#374151}}
.art-body blockquote strong{{color:var(--brand);font-style:normal;display:block;margin-top:8px;font-size:.9em}}

/* ── Share Bar ── */
.share-bar{{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:16px 20px;margin-top:28px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}}
.share-bar span{{font-size:12px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px}}
.share-btn{{padding:7px 18px;border-radius:4px;font-size:12px;font-weight:700;border:none;cursor:pointer;color:#fff;transition:.15s}}
.share-btn:hover{{opacity:.85}}
.share-btn.fb{{background:#1877f2}}
.share-btn.tw{{background:#000}}
.share-btn.wa{{background:#25d366}}
.share-btn.tg{{background:#0088cc}}

/* ── Tag Cloud ── */
.tag-cloud{{margin-top:20px;display:flex;flex-wrap:wrap;gap:8px}}
.tag{{background:var(--bg);border:1px solid var(--border);padding:4px 12px;border-radius:20px;font-size:11.5px;color:var(--text-muted);cursor:pointer;transition:.15s}}
.tag:hover{{background:var(--brand-lt);border-color:var(--brand);color:var(--brand)}}

/* ── Related ── */
.related-section{{margin-top:32px}}
.related-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-top:14px}}

/* ── Category Page ── */
.cat-header{{background:var(--card);border-radius:8px;padding:20px 24px;margin-bottom:24px;border-left:5px solid var(--brand)}}
.cat-header h1{{font-size:1.5em;font-weight:900;color:var(--text)}}
.cat-header p{{font-size:13px;color:var(--text-muted);margin-top:4px}}
.article-list{{display:flex;flex-direction:column;gap:16px}}
.list-item{{background:var(--card);border-radius:8px;overflow:hidden;display:flex;box-shadow:0 1px 3px rgba(0,0,0,.08);transition:.2s;cursor:pointer}}
.list-item:hover{{box-shadow:0 4px 16px rgba(0,0,0,.12)}}
.list-item img{{width:200px;height:140px;object-fit:cover;flex-shrink:0}}
.list-item-body{{padding:16px 20px;flex:1}}
.list-item-cat{{font-size:10px;font-weight:700;color:var(--brand);text-transform:uppercase;margin-bottom:6px}}
.list-item-title{{font-size:1.05em;font-weight:700;line-height:1.35;color:var(--text);margin-bottom:8px;transition:.15s}}
.list-item:hover .list-item-title{{color:var(--brand)}}
.list-item-summary{{font-size:13px;color:#6b7280;line-height:1.55;margin-bottom:10px}}
.list-item-meta{{font-size:11px;color:var(--text-muted);display:flex;gap:12px}}
.no-img-placeholder{{width:200px;height:140px;background:#f3f4f6;display:flex;align-items:center;justify-content:center;color:#9ca3af;font-size:12px;flex-shrink:0}}

/* ── Footer ── */
.footer{{background:#111;color:#9ca3af;padding:40px 0 20px;margin-top:48px}}
.footer-inner{{max-width:1280px;margin:0 auto;padding:0 20px}}
.footer-top{{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:32px;margin-bottom:32px}}
.footer-brand .wordmark{{font-size:1.6em;font-weight:900;color:var(--brand);letter-spacing:-1px}}
.footer-brand .wordmark span{{color:#fff}}
.footer-brand p{{font-size:12px;margin-top:8px;line-height:1.6}}
.footer-col h4{{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#fff;margin-bottom:14px}}
.footer-col a{{display:block;font-size:12px;color:#9ca3af;margin-bottom:8px;transition:.15s}}
.footer-col a:hover{{color:var(--brand)}}
.footer-bottom{{border-top:1px solid #2d2d2d;padding-top:16px;display:flex;justify-content:space-between;font-size:11px;flex-wrap:wrap;gap:8px}}

/* ── Responsive ── */
@media(max-width:900px){{
  .container{{grid-template-columns:1fr}}
  .sidebar{{display:none}}
  .grid-3{{grid-template-columns:repeat(2,1fr)}}
  .footer-top{{grid-template-columns:1fr 1fr}}
  .list-item img{{width:120px;height:100px}}
  .art-title{{font-size:1.5em}}
  .hero-card img{{height:260px}}
  .related-grid{{grid-template-columns:1fr}}
}}
@media(max-width:600px){{
  .grid-3,.grid-2{{grid-template-columns:1fr}}
  .list-item{{flex-direction:column}}
  .list-item img,.no-img-placeholder{{width:100%;height:180px}}
  .nav-links a{{padding:0 10px;font-size:11px}}
}}
</style>
"""

def navbar_html(active_cat="", depth=""):
    links = ""
    for label, slug in NAVBAR_LINKS:
        is_active = "active" if slug == active_cat else ""
        links += f'<a href="{depth}kategori/{slug}.html" class="{is_active}">{label}</a>\n'

    return f"""
<div class="topbar">
  <div class="topbar-inner">
    <span>📅 {datetime.now().strftime("%A, %d %B %Y")}</span>
    <div><a href="#">Tentang Kami</a><a href="#">Redaksi</a><a href="#">Kontak</a><a href="#">Iklan</a></div>
  </div>
</div>
<nav class="navbar">
  <div class="navbar-inner">
    <a href="{depth}index.html" class="nav-logo">
      <div>
        <div class="wordmark">Liputan<span>9</span></div>
        <div class="tagline">{PORTAL_TAGLINE}</div>
      </div>
    </a>
    <div class="nav-links">
      {links}
    </div>
    <div class="nav-search search-icon">
      <input type="text" placeholder="Cari berita..." id="searchInput" oninput="doSearch(this.value)">
    </div>
  </div>
</nav>
"""

def ticker_html(articles):
    items = random.sample(articles, min(8, len(articles)))
    track = "  ".join(f"<span>🔴 {a['judul']}</span>" for a in items)
    return f"""
<div class="ticker">
  <div class="ticker-inner">
    <div class="ticker-label">BREAKING</div>
    <div class="ticker-wrap">
      <div class="ticker-track">{track}&nbsp;&nbsp;&nbsp;{track}</div>
    </div>
  </div>
</div>
"""

def footer_html():
    year = datetime.now().year
    cats_html = "".join(f'<a href="kategori/{slug}.html">{label}</a>' for label, slug in NAVBAR_LINKS)
    return f"""
<footer class="footer">
  <div class="footer-inner">
    <div class="footer-top">
      <div class="footer-brand">
        <div class="wordmark">Liputan<span>9</span></div>
        <p>Portal berita terdepan Indonesia. Menghadirkan informasi akurat, cepat, dan berimbang dari seluruh penjuru nusantara.</p>
      </div>
      <div class="footer-col">
        <h4>Kategori</h4>
        {cats_html}
      </div>
      <div class="footer-col">
        <h4>Layanan</h4>
        <a href="#">Newsletter</a>
        <a href="#">Podcast</a>
        <a href="#">Aplikasi Mobile</a>
        <a href="#">RSS Feed</a>
        <a href="#">Notifikasi</a>
      </div>
      <div class="footer-col">
        <h4>Perusahaan</h4>
        <a href="#">Tentang Kami</a>
        <a href="#">Redaksi</a>
        <a href="#">Karir</a>
        <a href="#">Iklan</a>
        <a href="#">Kebijakan Privasi</a>
      </div>
    </div>
    <div class="footer-bottom">
      <span>&copy; {year} {PORTAL_NAME}. Hak cipta dilindungi undang-undang.</span>
      <span>Syarat & Ketentuan &nbsp;|&nbsp; Kebijakan Privasi &nbsp;|&nbsp; Disclaimer</span>
    </div>
  </div>
</footer>
"""

SEARCH_JS = """
<script>
function doSearch(q) {
  if (!q || q.length < 2) return;
  // Simple client-side redirect to category search
  const term = encodeURIComponent(q.trim());
  window.location.href = 'search.html?q=' + term;
}
document.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && document.getElementById('searchInput')) {
    doSearch(document.getElementById('searchInput').value);
  }
});
</script>
"""

# ──────────────────────────────────────────
# PAGE WRITERS
# ──────────────────────────────────────────

def img_src(article, depth=""):
    if article.get("image_local"):
        return f"{depth}images/{article['image_local']}"
    # SVG placeholder (no external deps)
    return f"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='260'%3E%3Crect fill='%23f3f4f6' width='400' height='260'/%3E%3Ctext fill='%239ca3af' font-size='14' x='50%25' y='50%25' text-anchor='middle' dominant-baseline='middle'%3EFoto tidak tersedia%3C/text%3E%3C/svg%3E"


def write_index(articles, out_dir):
    out = Path(out_dir)
    sorted_a = sorted(articles, key=lambda x: x["published_at"], reverse=True)
    headline = sorted_a[0]
    second_row = sorted_a[1:4]
    main_list = sorted_a[4:14]
    sidebar_pop = sorted_a[:8]
    sidebar_daerah = [a for a in sorted_a if a["kategori"] == "Daerah"][:6]

    # Hero
    hero = f"""
<a href="berita/{headline['id']}.html">
<div class="hero-card">
  <img src="{img_src(headline)}" alt="{headline['judul']}" loading="lazy">
  <div class="hero-overlay">
    <div class="hero-cat">{headline['kategori']}</div>
    <div class="hero-title">{headline['judul']}</div>
    <div class="hero-meta">
      <span>✍ {headline['reporter']}</span>
      <span>🕐 {headline['tanggal_display']}</span>
      <span>📍 {headline['lokasi']}</span>
    </div>
  </div>
</div>
</a>
"""

    # 3-grid row
    grid3 = '<div class="grid-3">'
    for a in second_row:
        grid3 += f"""
<a href="berita/{a['id']}.html">
<div class="card">
  <img class="card-img" src="{img_src(a)}" alt="{a['judul']}" loading="lazy">
  <div class="card-body">
    <div class="card-cat">{a['kategori']}</div>
    <div class="card-title">{a['judul']}</div>
    <div class="card-meta"><span>{a['reporter']}</span><span>{a['tanggal_display']}</span></div>
  </div>
</div>
</a>"""
    grid3 += "</div>"

    # Section header
    sec_hdr = '<div class="section-hdr"><h2>Berita Terkini</h2><div class="line"></div><a href="kategori/nasional.html">Lihat Semua →</a></div>'

    # List items
    list_html = ""
    for a in main_list:
        if a.get("image_local"):
            img = f'<img src="{img_src(a)}" alt="{a["judul"]}" loading="lazy">'
        else:
            img = '<div class="no-img-placeholder">📷</div>'
        list_html += f"""
<a href="berita/{a['id']}.html">
<div class="list-item">
  {img}
  <div class="list-item-body">
    <div class="list-item-cat">{a['kategori']}</div>
    <div class="list-item-title">{a['judul']}</div>
    <div class="list-item-summary">{a.get('subjudul','')[:120]}...</div>
    <div class="list-item-meta"><span>✍ {a['reporter']}</span><span>🕐 {a['tanggal_display']}</span><span>📍 {a['lokasi']}, {a['provinsi']}</span></div>
  </div>
</div>
</a>"""

    # Sidebar
    sidebar_html = '<div class="sidebar">'
    sidebar_html += '<div class="sidebar-widget"><div class="widget-title">Terpopuler</div>'
    for i, a in enumerate(sidebar_pop[:6], 1):
        sidebar_html += f"""
<div class="sidebar-rank-item">
  <div class="rank-num">{i}</div>
  <div>
    <a href="berita/{a['id']}.html"><div class="rank-title">{a['judul']}</div></a>
    <div class="rank-meta">{a['kategori']} · {a['provinsi']}</div>
  </div>
</div>"""
    sidebar_html += "</div>"

    sidebar_html += '<div class="sidebar-widget"><div class="widget-title">Berita Daerah</div>'
    for a in (sidebar_daerah or sorted_a[8:14]):
        sidebar_html += f"""
<div class="list-card">
  <img src="{img_src(a)}" alt="{a['judul']}" loading="lazy">
  <div class="list-card-body">
    <div class="list-card-cat">{a['provinsi']}</div>
    <a href="berita/{a['id']}.html"><div class="list-card-title">{a['judul']}</div></a>
    <div class="list-card-meta">{a['tanggal_display']}</div>
  </div>
</div>"""
    sidebar_html += "</div></div>"

    html = f"""<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{PORTAL_NAME} — {PORTAL_TAGLINE}</title>
<meta name="description" content="Portal berita Indonesia terpercaya. Berita terkini nasional, daerah, hukum, ekonomi, dan olahraga.">
{BASE_CSS}
</head>
<body>
{navbar_html()}
{ticker_html(articles)}
<div class="container">
<div class="main-content">
{hero}
{grid3}
{sec_hdr}
<div class="article-list">{list_html}</div>
</div>
{sidebar_html}
</div>
{footer_html()}
{SEARCH_JS}
</body></html>"""

    with open(out / "index.html", "w", encoding="utf-8") as f:
        f.write(html)


def write_category_pages(articles, out_dir):
    out = Path(out_dir)
    (out / "kategori").mkdir(exist_ok=True)

    cat_slug_map = {label: slug for label, slug in NAVBAR_LINKS}

    # Group by kategori
    from collections import defaultdict
    cat_articles = defaultdict(list)
    for a in articles:
        cat_articles[a["kategori"]].append(a)

    for label, slug in NAVBAR_LINKS:
        cat_a = sorted(cat_articles.get(label, []), key=lambda x: x["published_at"], reverse=True)
        # Fallback: all articles if category is empty
        if not cat_a:
            cat_a = sorted(articles, key=lambda x: x["published_at"], reverse=True)[:20]

        # Hero
        hero_a = cat_a[0]
        hero = f"""
<a href="../berita/{hero_a['id']}.html">
<div class="hero-card">
  <img src="{img_src(hero_a, depth='../')}" alt="{hero_a['judul']}" loading="lazy">
  <div class="hero-overlay">
    <div class="hero-cat">{label}</div>
    <div class="hero-title">{hero_a['judul']}</div>
    <div class="hero-meta">
      <span>✍ {hero_a['reporter']}</span>
      <span>🕐 {hero_a['tanggal_display']}</span>
    </div>
  </div>
</div>
</a>
"""

        list_html = ""
        for a in cat_a[1:]:
            if a.get("image_local"):
                img = f'<img src="{img_src(a, depth="../")}" alt="{a["judul"]}" loading="lazy">'
            else:
                img = '<div class="no-img-placeholder">📷</div>'
            list_html += f"""
<a href="../berita/{a['id']}.html">
<div class="list-item">
  {img}
  <div class="list-item-body">
    <div class="list-item-cat">{a['kategori']}</div>
    <div class="list-item-title">{a['judul']}</div>
    <div class="list-item-summary">{a.get('subjudul','')[:120]}...</div>
    <div class="list-item-meta"><span>✍ {a['reporter']}</span><span>🕐 {a['tanggal_display']}</span><span>📍 {a['lokasi']}</span></div>
  </div>
</div>
</a>"""

        sidebar = '<div class="sidebar">'
        sidebar += '<div class="sidebar-widget"><div class="widget-title">Artikel Terbaru</div>'
        for a in sorted(articles, key=lambda x: x["published_at"], reverse=True)[:8]:
            sidebar += f"""
<div class="list-card">
  <img src="{img_src(a, depth='../')}" alt="{a['judul']}" loading="lazy">
  <div class="list-card-body">
    <div class="list-card-cat">{a['kategori']}</div>
    <a href="../berita/{a['id']}.html"><div class="list-card-title">{a['judul']}</div></a>
    <div class="list-card-meta">{a['tanggal_display']}</div>
  </div>
</div>"""
        sidebar += "</div></div>"

        nav = navbar_html(active_cat=slug, depth="../")
        # patch nav search path
        nav = nav.replace("href=\"../search.html", "href=\"../search.html")

        html = f"""<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{label} — {PORTAL_NAME}</title>
{BASE_CSS}
</head>
<body>
{nav}
<div class="container" style="margin-top:24px">
<div class="main-content">
<div class="cat-header">
  <h1>📂 {label}</h1>
  <p>Berita terbaru seputar {label.lower()} dari seluruh Indonesia</p>
</div>
{hero}
<div class="section-hdr"><h2>Semua Berita {label}</h2><div class="line"></div></div>
<div class="article-list">{list_html}</div>
</div>
{sidebar}
</div>
{footer_html()}
{SEARCH_JS}
</body></html>"""

        with open(out / "kategori" / f"{slug}.html", "w", encoding="utf-8") as f:
            f.write(html)


def write_article_page(article, articles, out_dir):
    out = Path(out_dir)
    (out / "berita").mkdir(exist_ok=True)

    pub = datetime.fromisoformat(article["published_at"].replace("Z", "+00:00"))
    pub_local = pub + timedelta(hours=7)
    tanggal_long = f"{pub_local.day} {BULAN[pub_local.month]} {pub_local.year}, {pub_local.strftime('%H:%M')} WIB"

    img_html = ""
    if article.get("image_local"):
        img_html = f'<img class="art-hero" src="../images/{article["image_local"]}" alt="{article["judul"]}" loading="lazy">\n<p class="art-caption">Foto: Dokumentasi {PORTAL_NAME} / {article["reporter"]}</p>'
    else:
        img_html = '<div style="width:100%;height:300px;background:#f3f4f6;border-radius:8px;margin-bottom:28px;display:flex;align-items:center;justify-content:center;color:#9ca3af;font-size:14px">Foto tidak tersedia</div>'

    # Body
    isi = article.get("isi", "")
    paragraphs = [p.strip() for p in isi.split("\n") if p.strip()]
    body = ""
    for i, p in enumerate(paragraphs):
        if i == 1 and article.get("kutipan_utama") and article.get("narasumber"):
            body += f'<blockquote>"{article["kutipan_utama"]}"<strong>— {article["narasumber"]}, {article.get("jabatan_narasumber","")}</strong></blockquote>\n'
        body += f"<p>{p}</p>\n"

    # Related
    related = [a for a in articles if a["id"] != article["id"] and a["kategori"] == article["kategori"]]
    if len(related) < 2:
        related = [a for a in articles if a["id"] != article["id"]]
    related = random.sample(related, min(4, len(related)))

    rel_html = ""
    for r in related:
        rel_html += f"""
<a href="{r['id']}.html">
<div class="card">
  <img class="card-img" src="{img_src(r, depth='../')}" alt="{r['judul']}" loading="lazy">
  <div class="card-body">
    <div class="card-cat">{r['kategori']}</div>
    <div class="card-title">{r['judul']}</div>
    <div class="card-meta"><span>{r['tanggal_display']}</span></div>
  </div>
</div>
</a>"""

    cat_slug = dict(NAVBAR_LINKS).get(article["kategori"], "nasional")

    html = f"""<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{article['judul']} — {PORTAL_NAME}</title>
<meta name="description" content="{article.get('subjudul','')[:160]}">
<meta property="og:title" content="{article['judul']}">
<meta property="og:description" content="{article.get('subjudul','')[:200]}">
{BASE_CSS}
</head>
<body>
{navbar_html(active_cat=cat_slug, depth="../")}
<div class="art-container">
  <div class="art-breadcrumb">
    <a href="../index.html">Beranda</a> › 
    <a href="../kategori/{cat_slug}.html">{article['kategori']}</a> › 
    {article['judul'][:50]}...
  </div>
  <div class="art-cat-badge">{article['kategori']}</div>
  <h1 class="art-title">{article['judul']}</h1>
  <p class="art-subjudul">{article.get('subjudul','')}</p>
  <div class="art-meta">
    <span class="author">✍ {article['reporter']}</span>
    <span>🕐 {tanggal_long}</span>
    <span>📍 {article['lokasi']}, {article['provinsi']}</span>
  </div>
  {img_html}
  <div class="art-body">{body}</div>
  <div class="share-bar">
    <span>Bagikan:</span>
    <button class="share-btn fb" onclick="window.open('https://facebook.com/sharer/sharer.php?u='+encodeURIComponent(location.href))">Facebook</button>
    <button class="share-btn tw" onclick="window.open('https://twitter.com/intent/tweet?url='+encodeURIComponent(location.href)+'&text='+encodeURIComponent(document.title))">X/Twitter</button>
    <button class="share-btn wa" onclick="window.open('https://wa.me/?text='+encodeURIComponent(document.title+' '+location.href))">WhatsApp</button>
    <button class="share-btn tg" onclick="window.open('https://t.me/share/url?url='+encodeURIComponent(location.href))">Telegram</button>
  </div>
  <div class="tag-cloud">
    <span class="tag">{article['kategori']}</span>
    <span class="tag">{article['provinsi']}</span>
    <span class="tag">{article['lokasi']}</span>
    <span class="tag">Indonesia</span>
  </div>
  <div class="related-section">
    <div class="section-hdr"><h2>Berita Terkait</h2><div class="line"></div></div>
    <div class="related-grid">{rel_html}</div>
  </div>
</div>
{footer_html()}
{SEARCH_JS}
</body></html>"""

    with open(out / "berita" / f"{article['id']}.html", "w", encoding="utf-8") as f:
        f.write(html)


def write_search_page(articles, out_dir):
    """Simple client-side search page"""
    articles_json = json.dumps([
        {"id": a["id"], "judul": a["judul"], "subjudul": a.get("subjudul",""),
         "kategori": a["kategori"], "lokasi": a["lokasi"], "tanggal": a["tanggal_display"]}
        for a in articles
    ], ensure_ascii=False)

    html = f"""<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pencarian — {PORTAL_NAME}</title>
{BASE_CSS}
</head>
<body>
{navbar_html()}
<div class="container full">
  <div class="cat-header">
    <h1>🔍 Hasil Pencarian</h1>
    <p id="search-info">Masukkan kata kunci di kolom pencarian</p>
  </div>
  <div id="results" class="article-list"></div>
</div>
{footer_html()}
<script>
const ARTICLES = {articles_json};

function getQuery() {{
  return new URLSearchParams(window.location.search).get('q') || '';
}}

function render(q) {{
  const el = document.getElementById('results');
  const info = document.getElementById('search-info');
  if (!q) {{ el.innerHTML = ''; return; }}
  const lq = q.toLowerCase();
  const hits = ARTICLES.filter(a => 
    a.judul.toLowerCase().includes(lq) || 
    a.subjudul.toLowerCase().includes(lq) ||
    a.kategori.toLowerCase().includes(lq) ||
    a.lokasi.toLowerCase().includes(lq)
  );
  info.textContent = `Ditemukan ${{hits.length}} hasil untuk "${{q}}"`;
  el.innerHTML = hits.map(a => `
    <a href="berita/${{a.id}}.html">
    <div class="list-item">
      <div class="no-img-placeholder">📰</div>
      <div class="list-item-body">
        <div class="list-item-cat">${{a.kategori}}</div>
        <div class="list-item-title">${{a.judul}}</div>
        <div class="list-item-summary">${{a.subjudul.slice(0,150)}}...</div>
        <div class="list-item-meta"><span>📍 ${{a.lokasi}}</span><span>🕐 ${{a.tanggal}}</span></div>
      </div>
    </div>
    </a>`).join('');
}}

const q = getQuery();
if (q) document.getElementById('searchInput').value = q;
render(q);

function doSearch(v) {{
  window.location.href = 'search.html?q=' + encodeURIComponent(v);
}}
</script>
</body></html>"""

    with open(Path(out_dir) / "search.html", "w", encoding="utf-8") as f:
        f.write(html)


def write_jsonl(articles, out_dir):
    path = Path(out_dir) / "dataset.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for a in articles:
            record = {
                "id": a["id"],
                "judul": a["judul"],
                "subjudul": a.get("subjudul", ""),
                "isi": a.get("isi", ""),
                "kategori": a["kategori"],
                "provinsi": a["provinsi"],
                "lokasi": a["lokasi"],
                "reporter": a["reporter"],
                "portal": PORTAL_NAME,
                "published_at": a["published_at"],
                "tags": a.get("tags", []),
                "image_local": a.get("image_local"),
                # hidden metadata — tidak tampil di UI
                "is_synthetic": True,
                "synthetic_version": "2.0",
                "generated_by": "gpt-4o-mini + dall-e-3",
                "dataset_purpose": "AI training dataset",
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return str(path)


# ──────────────────────────────────────────
# ASYNC MAIN
# ──────────────────────────────────────────

async def main_async(args):
    client = AsyncOpenAI(api_key="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")
    faker = Faker("id_ID")
    random.seed(args.seed)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "images").mkdir(exist_ok=True)
    (out_dir / "berita").mkdir(exist_ok=True)
    (out_dir / "kategori").mkdir(exist_ok=True)

    print(f"\n{'='*50}")
    print(f"  🗞️  {PORTAL_NAME} — Synthetic News Generator v2")
    print(f"{'='*50}")
    print(f"  Target  : {args.count} artikel")
    print(f"  GPT     : {GPT_CONCURRENCY} concurrent requests")
    print(f"  DALL-E  : {'SKIP (--no-images)' if args.no_images else f'{DALLE_CONCURRENCY} concurrent'}")
    print(f"  Output  : {out_dir}")
    print(f"{'='*50}\n")

    # ── 1. Build tasks metadata ──
    tasks_meta = []
    for _ in range(args.count):
        kat_name, topik, lokasi, provinsi, pub, pub_local, tanggal_str = random_topik(faker)
        article_id = str(uuid.uuid4())[:8]
        reporter = random.choice(REPORTER_NAMES)
        tanggal_display = f"{pub_local.day} {BULAN_SHORT[pub_local.month]} {pub_local.year}, {pub_local.strftime('%H:%M')} WIB"

        tasks_meta.append({
            "id": article_id,
            "kat_name": kat_name,
            "topik": topik,
            "lokasi": lokasi,
            "provinsi": provinsi,
            "pub": pub,
            "pub_local": pub_local,
            "tanggal_str": tanggal_str,
            "tanggal_display": tanggal_display,
            "reporter": reporter,
        })

    # ── 2. Generate articles in parallel ──
    gpt_sem = asyncio.Semaphore(GPT_CONCURRENCY)

    print(f"[1/3] Generating {args.count} articles (GPT-4o-mini, {GPT_CONCURRENCY} parallel)...")
    t0 = time.time()

    async def gen_one(meta):
        data = await generate_article_async(
            client, gpt_sem,
            meta["topik"], meta["lokasi"], meta["provinsi"], meta["tanggal_str"]
        )
        return meta, data

    coros = [gen_one(m) for m in tasks_meta]

    articles = []
    if HAS_TQDM:
        results = []
        for coro in atqdm.as_completed(coros, total=len(coros), desc="  GPT"):
            results.append(await coro)
    else:
        results = await asyncio.gather(*coros)

    gpt_elapsed = time.time() - t0

    for meta, gpt_data in results:
        if not gpt_data:
            continue
        articles.append({
            "id": meta["id"],
            "judul": gpt_data.get("judul", meta["topik"]),
            "subjudul": gpt_data.get("subjudul", ""),
            "isi": gpt_data.get("isi", ""),
            "kutipan_utama": gpt_data.get("kutipan_utama", ""),
            "narasumber": gpt_data.get("narasumber", ""),
            "jabatan_narasumber": gpt_data.get("jabatan_narasumber", ""),
            "kategori": meta["kat_name"],
            "provinsi": meta["provinsi"],
            "lokasi": meta["lokasi"],
            "reporter": meta["reporter"],
            "portal": PORTAL_NAME,
            "published_at": meta["pub"].isoformat().replace("+00:00", "Z"),
            "tanggal_display": meta["tanggal_display"],
            "tags": [meta["kat_name"].lower(), meta["provinsi"].lower().replace(" ", "-")],
            "image_local": None,
        })

    print(f"  ✓ {len(articles)}/{args.count} artikel selesai dalam {gpt_elapsed:.1f}s "
          f"({len(articles)/gpt_elapsed*60:.0f} artikel/menit)\n")

    # ── 3. Generate images in parallel ──
    if not args.no_images and articles:
        dalle_sem = asyncio.Semaphore(DALLE_CONCURRENCY)

        print(f"[2/3] Generating images (DALL-E 3, {DALLE_CONCURRENCY} parallel, ~{DALLE_DELAY}s delay)...")
        t1 = time.time()

        img_coros = [
            generate_image_async(client, dalle_sem, a["kategori"], a["lokasi"], a["id"], out_dir)
            for a in articles
        ]

        if HAS_TQDM:
            img_results = []
            for coro in atqdm.as_completed(img_coros, total=len(img_coros), desc="  DALL-E"):
                img_results.append(await coro)
        else:
            img_results = await asyncio.gather(*img_coros)

        for article, img_filename in zip(articles, img_results):
            if img_filename:
                article["image_local"] = img_filename

        img_elapsed = time.time() - t1
        success_img = sum(1 for x in img_results if x)
        print(f"  ✓ {success_img}/{len(articles)} gambar selesai dalam {img_elapsed:.1f}s\n")

    # ── 4. Write HTML ──
    print(f"[3/3] Writing HTML pages...")
    t2 = time.time()

    for a in articles:
        write_article_page(a, articles, str(out_dir))

    write_index(articles, str(out_dir))
    write_category_pages(articles, str(out_dir))
    write_search_page(articles, str(out_dir))
    jsonl_path = write_jsonl(articles, str(out_dir))

    html_elapsed = time.time() - t2
    total_elapsed = time.time() - t0

    print(f"  ✓ HTML selesai dalam {html_elapsed:.1f}s\n")

    print(f"{'='*50}")
    print(f"  ✅ SELESAI!")
    print(f"  Artikel  : {len(articles)}")
    print(f"  Total    : {total_elapsed:.1f}s ({total_elapsed/60:.1f} menit)")
    print(f"  Portal   : {out_dir}/index.html")
    print(f"  Kategori : {out_dir}/kategori/[nasional|hukum|...].html")
    print(f"  Search   : {out_dir}/search.html")
    print(f"  Dataset  : {jsonl_path}")
    print(f"{'='*50}\n")


def main():
    ap = argparse.ArgumentParser(description="news — Parallel Synthetic News Generator")
    ap.add_argument("--count",        type=int,  default=20,        help="Jumlah artikel")
    ap.add_argument("--out-dir",      type=str,  default="news", help="Direktori output")
    ap.add_argument("--seed",         type=int,  default=42)
    ap.add_argument("--no-images",    action="store_true",           help="Skip DALL-E (hemat cost)")
    ap.add_argument("--gpt-workers",  type=int,  default=GPT_CONCURRENCY, help="Max concurrent GPT calls")
    ap.add_argument("--dalle-workers",type=int,  default=DALLE_CONCURRENCY, help="Max concurrent DALL-E calls")
    args = ap.parse_args()

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()