"""
atlas_data.py — Pembaca Dataset UIX untuk Atlas Voice Assistant

Memuat semua dataset internal UIX ke memori dan menyediakan fungsi
kueri untuk navigasi, pencarian kasus, profil, berita, dan peringatan.
"""

import json
import re
from pathlib import Path

DATASET_DIR = Path(__file__).parent.parent / "dataset"
NEWS_FILE   = Path(__file__).parent.parent / "news" / "dataset.jsonl"

_FILE_DATASET = [
    "kasus", "peringatan", "profil", "laporan", "skor_risiko",
    "transaksi", "postingan", "akun", "klaster_pesan",
    "pertemanan", "entitas", "lokasi", "kontak", "foto",
    "crawling", "jaringan", "kampanye", "preferensi",
    "peringatan_dana",
]


class AtlasData:
    """Pengelola semua data internal UIX — dimuat sekali saat startup."""

    def __init__(self, verbose: bool = True) -> None:
        self.db: dict[str, list] = {}
        self.berita: list[dict] = []
        self._muat_semua(verbose)

    # ------------------------------------------------------------------
    # INISIALISASI
    # ------------------------------------------------------------------

    def _muat_semua(self, verbose: bool) -> None:
        for nama in _FILE_DATASET:
            path = DATASET_DIR / f"{nama}.json"
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    self.db[nama] = json.load(f)
                if verbose:
                    print(f"  [OK] {nama}.json — {len(self.db[nama])} record")
            else:
                self.db[nama] = []
                if verbose:
                    print(f"  [--] {nama}.json tidak ditemukan, dilewati")

        if NEWS_FILE.exists():
            with open(NEWS_FILE, encoding="utf-8") as f:
                self.berita = [json.loads(ln) for ln in f if ln.strip()]
            if verbose:
                print(f"  [OK] news/dataset.jsonl — {len(self.berita)} berita")
        else:
            if verbose:
                print(f"  [--] news/dataset.jsonl tidak ditemukan")

    # ------------------------------------------------------------------
    # RINGKASAN SISTEM
    # ------------------------------------------------------------------

    def ringkas_sistem(self) -> str:
        jml = {k: len(v) for k, v in self.db.items()}
        kasus_list = self.db.get("kasus", [])
        status_kasus = ", ".join(
            f"{k['judul'][:30]} ({k.get('status', '?')})" for k in kasus_list
        ) or "tidak ada"
        return (
            f"Sistem UIX aktif. "
            f"{jml.get('kasus', 0)} kasus, "
            f"{jml.get('profil', 0)} profil, "
            f"{jml.get('peringatan', 0)} peringatan, "
            f"{jml.get('transaksi', 0)} transaksi, "
            f"{jml.get('postingan', 0)} postingan, "
            f"dan {len(self.berita)} berita tersedia. "
            f"Kasus aktif: {status_kasus}."
        )

    def ringkasan_untuk_llm(self) -> str:
        """Context ringkas untuk dikirim ke Ollama sebagai system prompt enrichment."""
        kasus_list = self.db.get("kasus", [])
        lines = [
            "Data internal UIX yang tersedia:",
            f"- {len(self.db.get('profil', []))} profil target",
            f"- {len(self.db.get('peringatan', []))} peringatan aktif",
            f"- {len(self.db.get('transaksi', []))} transaksi finansial",
            f"- {len(self.berita)} artikel berita",
            "",
            "Kasus aktif di sistem:",
        ]
        for k in kasus_list:
            sr = next(
                (s for s in self.db.get("skor_risiko", []) if s["id_kasus"] == k["id_kasus"]),
                None,
            )
            risiko = f"risiko {sr['skor_risiko']}/100" if sr else "risiko ?"
            lines.append(
                f"- [{k['id_kasus']}] {k['judul']} "
                f"(status: {k.get('status', '?')}, {risiko}, lokasi: {k.get('kota', '?')})"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # KASUS
    # ------------------------------------------------------------------

    def daftar_kasus(self) -> list[dict]:
        return self.db.get("kasus", [])

    def cari_kasus(self, query: str, top_k: int = 3) -> list[dict]:
        q = query.lower()
        skor_hasil: list[tuple[int, dict]] = []
        for k in self.db.get("kasus", []):
            s = 0
            if q in k.get("id_kasus", "").lower():   s += 3
            if q in k.get("judul", "").lower():       s += 2
            if q in k.get("tipe_kasus", "").lower():  s += 2
            if q in k.get("kota", "").lower():        s += 1
            if q in k.get("provinsi", "").lower():    s += 1
            if s > 0:
                skor_hasil.append((s, k))
        skor_hasil.sort(key=lambda x: -x[0])
        return [h[1] for h in skor_hasil[:top_k]]

    def baca_detail_kasus(self, id_kasus_atau_query: str) -> str:
        # Exact match dulu
        kasus = next(
            (k for k in self.db.get("kasus", []) if k["id_kasus"] == id_kasus_atau_query),
            None,
        )
        # Fuzzy fallback
        if not kasus:
            hasil = self.cari_kasus(id_kasus_atau_query, 1)
            if not hasil:
                return f"Kasus '{id_kasus_atau_query}' tidak ditemukan di dataset."
            kasus = hasil[0]
        id_k = kasus["id_kasus"]

        bag = [
            f"Kasus: {kasus['judul']}",
            f"ID: {id_k}",
            f"Tipe: {kasus.get('tipe_kasus', '-')} | Status: {kasus.get('status', '-')}",
            f"Lokasi: {kasus.get('kota', '-')}, {kasus.get('provinsi', '-')}",
            f"Waktu insiden: {str(kasus.get('waktu_insiden', '-'))[:10]}",
            f"Jumlah aktor terlibat: {kasus.get('jumlah_aktor', '?')}",
        ]

        # Skor risiko
        sr = next(
            (s for s in self.db.get("skor_risiko", []) if s["id_kasus"] == id_k), None
        )
        if sr:
            bag.append(
                f"Skor risiko: {sr['skor_risiko']}/100 ({sr['label_risiko']}). "
                f"Probabilitas sabotase terorganisir: "
                f"{sr.get('probabilitas_sabotase_terorganisir', 0):.0%}."
            )

        # Laporan
        laporan_list = [l for l in self.db.get("laporan", []) if l.get("id_kasus") == id_k]
        if laporan_list:
            l0 = laporan_list[0]
            bag.append(f"Ringkasan laporan: {l0.get('ringkasan', '-')}")
            for i, t in enumerate(l0.get("temuan", [])[:3], 1):
                bag.append(f"  Temuan {i}: {t}")
            rek = l0.get("rekomendasi", [])
            if rek:
                bag.append(f"  Rekomendasi: {rek[0]}")

        # Peringatan
        peringatan = [p for p in self.db.get("peringatan", []) if p.get("id_kasus") == id_k]
        if peringatan:
            tinggi = [p for p in peringatan if p.get("tingkat_keparahan") == "tinggi"]
            bag.append(
                f"Total peringatan: {len(peringatan)}, "
                f"keparahan tinggi: {len(tinggi)}."
            )
            if tinggi:
                bag.append(f"  Peringatan utama: {tinggi[0].get('deskripsi', '-')}")

        # Transaksi (jika ada)
        txn = [t for t in self.db.get("transaksi", []) if t.get("id_kasus") == id_k]
        if txn:
            total_idr = sum(t.get("jumlah_idr", 0) for t in txn)
            bag.append(
                f"Transaksi terkait: {len(txn)} transaksi, "
                f"total Rp {total_idr:,.0f}."
            )

        return "\n".join(bag)

    # ------------------------------------------------------------------
    # PROFIL
    # ------------------------------------------------------------------

    def cari_profil(self, nama: str, top_k: int = 3) -> list[dict]:
        q = nama.lower()
        skor_hasil = []
        for p in self.db.get("profil", []):
            s = 0
            if q in p.get("nama_lengkap", "").lower():  s += 3
            if q in p.get("nama_tampil", "").lower():   s += 2
            if q in p.get("kota", "").lower():          s += 1
            if q in p.get("bio", "").lower():           s += 1
            if s > 0:
                skor_hasil.append((s, p))
        skor_hasil.sort(key=lambda x: -x[0])
        return [h[1] for h in skor_hasil[:top_k]]

    def baca_detail_profil(self, id_profil: str) -> str:
        p = next(
            (x for x in self.db.get("profil", []) if x["id_profil"] == id_profil), None
        )
        if not p:
            return f"Profil ID '{id_profil}' tidak ditemukan di dataset."

        bag = [
            f"Nama: {p['nama_lengkap']} (tampil: {p.get('nama_tampil', '-')})",
            f"Lokasi: {p.get('kota', '-')}, {p.get('provinsi', '-')}",
            f"Bio: {p.get('bio', '-')}",
        ]

        akun = [a for a in self.db.get("akun", []) if a.get("id_profil") == id_profil]
        if akun:
            platform_set = {a.get("platform", "") for a in akun if a.get("platform")}
            bag.append(f"Platform aktif: {', '.join(sorted(platform_set))}")

        post = [x for x in self.db.get("postingan", []) if x.get("id_profil") == id_profil]
        bag.append(f"Jumlah postingan: {len(post)}")

        kasus_list = p.get("tautan_kasus", [])
        if kasus_list:
            bag.append(f"Terkait kasus: {', '.join(kasus_list)}")

        risk = p.get("tag_risiko", [])
        if risk:
            bag.append(f"Tag risiko: {', '.join(risk)}")
        else:
            bag.append("Tidak ada tag risiko tercatat.")

        return "\n".join(bag)

    # ------------------------------------------------------------------
    # BERITA
    # ------------------------------------------------------------------

    def baca_berita_terbaru(self, n: int = 5) -> list[dict]:
        return sorted(
            self.berita, key=lambda x: x.get("published_at", ""), reverse=True
        )[:n]

    def cari_berita(self, query: str, top_k: int = 5) -> list[dict]:
        q = query.lower()
        skor_hasil = []
        for b in self.berita:
            s = 0
            if q in b.get("judul", "").lower():        s += 3
            if q in b.get("subjudul", "").lower():     s += 2
            if q in b.get("isi", "").lower()[:400]:    s += 1
            if q in b.get("kategori", "").lower():     s += 2
            if q in b.get("lokasi", "").lower():       s += 1
            if any(q in t for t in b.get("tags", [])): s += 2
            if s > 0:
                skor_hasil.append((s, b))
        skor_hasil.sort(key=lambda x: -x[0])
        return [h[1] for h in skor_hasil[:top_k]]

    # ------------------------------------------------------------------
    # PERINGATAN
    # ------------------------------------------------------------------

    def baca_peringatan_aktif(self, limit: int = 5) -> list[dict]:
        urutan_prio = {"kritis": 4, "tinggi": 3, "menengah": 2, "rendah": 1}
        return sorted(
            self.db.get("peringatan", []),
            key=lambda x: urutan_prio.get(x.get("tingkat_keparahan", "rendah"), 0),
            reverse=True,
        )[:limit]

    # ------------------------------------------------------------------
    # KLASTER PESAN
    # ------------------------------------------------------------------

    def baca_klaster_kritis(self, top_k: int = 3) -> list[dict]:
        return sorted(
            self.db.get("klaster_pesan", []),
            key=lambda x: x.get("kemiripan_copy", 0),
            reverse=True,
        )[:top_k]


# ------------------------------------------------------------------
# TEST STANDALONE
# ------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 55)
    print("Atlas Data — Test Standalone")
    print("=" * 55)
    data = AtlasData(verbose=True)

    print()
    print("[RINGKASAN SISTEM]")
    print(data.ringkas_sistem())

    print()
    print("[DAFTAR KASUS]")
    for k in data.daftar_kasus():
        print(f"  - {k['id_kasus']}: {k['judul']}")

    print()
    print("[DETAIL KASUS PERTAMA]")
    kl = data.daftar_kasus()
    if kl:
        print(data.baca_detail_kasus(kl[0]["id_kasus"]))

    print()
    print("[BERITA TERBARU x3]")
    for b in data.baca_berita_terbaru(3):
        print(f"  - [{b.get('kategori', '-')}] {b['judul']}")

    print()
    print("[PERINGATAN AKTIF x3]")
    for p in data.baca_peringatan_aktif(3):
        print(f"  - [{p.get('tingkat_keparahan', '-')}] {p.get('deskripsi', '')[:70]}")

    print()
    print("[KLASTER PESAN KRITIS x3]")
    for kp in data.baca_klaster_kritis(3):
        print(
            f"  - {kp['frasa_kanonik'][:50]} "
            f"(kemiripan: {kp['kemiripan_copy']:.0%})"
        )
