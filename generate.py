"""
Bulk News Generator - Parallel Edition
Bisa generate 100 artikel jauh lebih cepat pakai ThreadPoolExecutor
GPT calls paralel, DALL-E tetap throttled biar ga kena rate limit
"""

import json
import os
import random
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path

from openai import OpenAI
from faker import Faker

# ── CONFIG ──────────────────────────────────
OPENAI_API_KEY = "sk"
OUT_DIR        = "out_news"
COUNT          = 1000
GPT_WORKERS    = 10    # parallel GPT calls (aman di 10, max ~20)
NO_IMAGES      = False  # Faslse = generate gambar (jauh lebih lambat & mahal)
SEED           = 42
# ────────────────────────────────────────────

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
    ("Kriminal", [
        "penembakan di {lokasi} oleh kelompok bersenjata tidak dikenal",
        "penikaman massal di pasar {lokasi} menyebabkan beberapa korban jiwa",
        "pembunuhan berencana di {lokasi} dengan motif yang belum diketahui",
        "pembakaran rumah warga di {lokasi} disertai ancaman",
        "penculikan aktivis di {lokasi}, keluarga minta pertolongan",
        "perampokan bersenjata di bank {lokasi} oleh kawanan bertopeng",
        "pelarian narapidana berbahaya dari lapas {lokasi}",
        "tawuran berdarah antar kelompok di {lokasi} memakan korban",
        "kasus narkotika jaringan internasional terbongkar di {lokasi}",
        "sindikat perdagangan manusia digerebek di {lokasi}",
    ]),
    ("Keamanan", [
        "ledakan misterius di dekat kantor pemerintah {lokasi}",
        "ancaman bom diterima pejabat daerah {lokasi}",
        "temuan senjata ilegal dalam penggerebekan di {lokasi}",
        "aksi intimidasi terhadap tokoh masyarakat di {lokasi}",
        "kerusuhan massa di depan kantor DPRD {lokasi}",
        "serangan terhadap pos keamanan di wilayah perbatasan {lokasi}",
        "konflik lahan berujung bentrokan berdarah di {lokasi}",
        "kelompok bersenjata serang warga sipil di pedalaman {lokasi}",
    ]),
    ("Kecelakaan & Bencana", [
        "kecelakaan maut di jalan tol {lokasi} menewaskan {n} orang",
        "kapal nelayan tenggelam di perairan {lokasi}, penumpang hilang",
        "longsor di {lokasi} menimbun pemukiman warga",
        "kebakaran pabrik di {lokasi} menyebabkan ledakan besar",
        "banjir bandang di {lokasi} memaksa ribuan warga mengungsi",
        "gempa susulan terasa di {lokasi} setelah gempa besar",
    ]),
    ("Hukum & Peradilan", [
        "terdakwa korupsi anggaran {lokasi} divonis bebas, publik geram",
        "kasus pembunuhan {lokasi} masuk persidangan, tersangka baru terungkap",
        "pejabat {lokasi} ditangkap KPK terkait suap proyek infrastruktur",
        "hakim pengadilan {lokasi} dilaporkan menerima suap",
        "kasus pelecehan oleh oknum aparat di {lokasi} naik ke penyidikan",
    ]),
    ("Sosial & Politik", [
        "demo besar di {lokasi} ricuh, polisi kerahkan water cannon",
        "konflik suku di {lokasi} meledak, satu desa hangus terbakar",
        "pemuda tewas dalam bentrokan pilkada di {lokasi}",
        "warga {lokasi} mengamuk, kantor kecamatan dirusak massa",
        "kelompok radikal dikabarkan aktif rekrut anggota di {lokasi}",
    ]),
    ("Umum", [
        "penemuan mayat misterius di sungai {lokasi} gegerkan warga",
        "anak hilang di {lokasi} ditemukan dalam kondisi mengenaskan",
        "pasien meninggal di IGD {lokasi} diduga akibat malapraktik",
        "guru di {lokasi} dianiaya orang tua murid di dalam kelas",
        "viral video penganiayaan di {lokasi}, pelaku masih berkeliaran",
    ]),
]

REPORTER_NAMES = [
    "Ahmad Faruqi", "Siti Rahayu", "Budi Santoso", "Dewi Lestari",
    "Rizky Pratama", "Nur Hidayah", "Andi Kurniawan", "Fitri Wahyuni",
    "Doni Setiawan", "Rahmawati Putri", "Hendra Gunawan", "Yuni Astuti",
    "Bagas Prasetyo", "Mira Kusuma", "Fauzi Ramadhan", "Indah Permata",
]

BULAN = {1:'Januari',2:'Februari',3:'Maret',4:'April',5:'Mei',6:'Juni',
         7:'Juli',8:'Agustus',9:'September',10:'Oktober',11:'November',12:'Desember'}

SYSTEM_PROMPT = """Kamu adalah jurnalis senior Indonesia dengan pengalaman 15 tahun di media nasional.
Tulis artikel berita dalam bahasa Indonesia yang sangat realistis, persis seperti portal berita ternama.

Aturan:
- Gaya jurnalistik piramida terbalik
- 3-5 paragraf, 250-400 kata
- Kutipan narasumber realistis (nama, jabatan, institusi)
- Detail spesifik: waktu, tanggal, lokasi, angka
- Jangan sebut artikel ini fiktif atau sintetis
- Akhiri dengan perkembangan terkini

Output JSON:
{"judul":"...","subjudul":"...","isi":"...","kutipan_utama":"...","narasumber":"...","jabatan_narasumber":"..."}"""


def build_job(faker, idx):
    """Buat satu job spec (sebelum di-send ke GPT)"""
    random.seed(idx)
    kat_name, templates = random.choice(KATEGORI_BERITA)
    template = random.choice(templates)
    provinsi = random.choice(PROVINSI_INDONESIA)
    lokasi = faker.city()
    
    now = datetime.now(timezone.utc)
    pub = now - timedelta(days=random.randint(0, 90), minutes=random.randint(0, 1440))
    pub_local = pub + timedelta(hours=7)
    tanggal_str = f"{pub_local.day} {BULAN[pub_local.month]} {pub_local.year}"
    tanggal_display = f"{tanggal_str}, {pub_local.strftime('%H:%M')} WIB"
    
    topik = template.format(lokasi=lokasi, provinsi=provinsi, n=random.randint(2, 15))
    
    return {
        "idx": idx,
        "topik": topik,
        "kat_name": kat_name,
        "provinsi": provinsi,
        "lokasi": lokasi,
        "pub_iso": pub.isoformat().replace("+00:00", "Z"),
        "tanggal_display": tanggal_display,
        "reporter": random.choice(REPORTER_NAMES),
    }


def process_job(client, job):
    """Generate satu artikel — dipanggil dari thread pool"""
    prompt = f"""Tulis artikel berita: {job['topik']}
Lokasi: {job['lokasi']}, {job['provinsi']}
Tanggal: {job['tanggal_display']}"""

    for attempt in range(3):  # retry 3x kalau gagal
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.85,
                max_tokens=800,
                response_format={"type": "json_object"},
                timeout=30,
            )
            gpt = json.loads(resp.choices[0].message.content)
            
            return {
                "id": str(uuid.uuid4())[:8],
                "judul": gpt.get("judul", job["topik"]),
                "subjudul": gpt.get("subjudul", ""),
                "isi": gpt.get("isi", ""),
                "kutipan_utama": gpt.get("kutipan_utama", ""),
                "narasumber": gpt.get("narasumber", ""),
                "jabatan_narasumber": gpt.get("jabatan_narasumber", ""),
                "kategori": job["kat_name"],
                "provinsi": job["provinsi"],
                "lokasi": job["lokasi"],
                "reporter": job["reporter"],
                "published_at": job["pub_iso"],
                "tanggal_display": job["tanggal_display"],
                "tags": [job["kat_name"].lower(), job["provinsi"].lower().replace(" ", "-")],
                "image_local": None,
                # hidden metadata
                "is_synthetic": True,
                "generated_by": "gpt-4o-mini",
            }
        except Exception as e:
            if attempt == 2:
                print(f"  [FAIL idx={job['idx']}] {e}")
                return None
            time.sleep(2 ** attempt)  # exponential backoff


def write_jsonl(articles, out_dir):
    path = Path(out_dir) / "dataset.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for a in articles:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")
    print(f"Dataset saved: {path} ({len(articles)} artikel)")


def main():
    random.seed(SEED)
    faker = Faker("id_ID")
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    out_dir = Path(OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Generate {COUNT} artikel dengan {GPT_WORKERS} parallel workers...")
    print(f"Estimasi waktu: ~{COUNT // GPT_WORKERS * 3 // 60} menit")
    print(f"Estimasi cost GPT-4o-mini: ~${COUNT * 0.001:.2f}\n")
    
    # Build semua job specs
    jobs = [build_job(faker, i) for i in range(COUNT)]
    
    # Load existing articles kalau ada
    articles = []
    jsonl_path = out_dir / "dataset.jsonl"
    if jsonl_path.exists():
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    articles.append(json.loads(line))
        print(f"Loaded {len(articles)} artikel existing, nambahin {COUNT} lagi...\n")
    else:
        print(f"Fresh start, generate {COUNT} artikel...\n")

    failed = 0
    start = time.time()
    
    with ThreadPoolExecutor(max_workers=GPT_WORKERS) as executor:
        futures = {executor.submit(process_job, client, job): job for job in jobs}
        
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            if result:
                articles.append(result)
                # Save checkpoint tiap 50 artikel
                if len(articles) % 50 == 0:
                    write_jsonl(articles, out_dir)
                    elapsed = time.time() - start
                    rate = len(articles) / elapsed
                    eta = (COUNT - len(articles)) / rate
                    print(f"Progress: {len(articles)}/{COUNT} | {rate:.1f} art/s | ETA {eta/60:.1f} mnt")
            else:
                failed += 1
    
    # Final save
    write_jsonl(articles, out_dir)
    
    elapsed = time.time() - start
    print(f"\nSelesai! {len(articles)} artikel dalam {elapsed/60:.1f} menit")
    print(f"Gagal: {failed} artikel")
    print(f"Output: {out_dir}/dataset.jsonl")


if __name__ == "__main__":
    main()