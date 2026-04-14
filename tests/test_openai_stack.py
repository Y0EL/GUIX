from __future__ import annotations

import json
from pathlib import Path

from orchestration.config import PengaturanRuntime
from orchestration.openai_stack import LayananOpenAI
from orchestration.schema import DossierSindikat


def _buat_pengaturan_uji(timeout_openai: int = 45) -> PengaturanRuntime:
    return PengaturanRuntime(
        kunci_openai="sk-uji",
        model_openai="gpt-5-nano",
        timeout_openai=timeout_openai,
        maksimal_retry_openai=1,
        kafka_bootstrap_servers="localhost:9092",
        topik_osint_raw="osint-raw",
        grup_konsumen_tia="tia-uji",
        url_redis="redis://localhost:6379/0",
        aliran_tia_keluar="tia-keluar",
        aliran_naa_keluar="naa-keluar",
        aliran_alert_klaster="alert-klaster",
        aliran_hitl_review="hitl-review",
        aliran_pta_hasil="pta-hasil",
        broker_celery="redis://localhost:6379/1",
        backend_hasil_celery="redis://localhost:6379/2",
        dsn_postgres="postgresql://uji:uji@localhost:5432/uix",
        uri_neo4j="bolt://localhost:7687",
        pengguna_neo4j="neo4j",
        sandi_neo4j="123",
        token_mcp="token-uji",
        akar_data=Path("."),
        ambang_relevansi=0.35,
        ambang_tinggi=75,
        ambang_kritis=90,
        jendela_pta_hari=30,
        level_log="INFO",
    )


def test_ringkasan_payload_analisis_kasus_memangkas_duplikasi_besar() -> None:
    layanan = LayananOpenAI(_buat_pengaturan_uji())
    profil = [
        {
            "id_profil": "prof-1",
            "nama_lengkap": "Adi Supriyanto",
            "nama_tampil": "Adi",
            "kota": "Karawang",
            "provinsi": "Jawa Barat",
            "bio": "Operator lapangan dengan riwayat aktivitas panjang.",
            "isi_json": {
                "tag_risiko": ["sinyal_pendanaan"],
                "id_klaster": ["klaster-2"],
                "tautan_kasus": [{"id_kasus": "kasus-1", "peran": "aktor_pendanaan"}],
                "profil_terekstrak": {
                    "sinopsis": "Aktif lintas platform dan sering muncul di simpul jaringan.",
                    "statistik": {"jumlah_akun": 4, "jumlah_posting": 80},
                    "akun": [{"platform": "telegram", "username": "adi-utama"}],
                    "postingan": [{"konten": "x" * 5000}],
                    "lokasi": [{"label": "lokasi-a"} for _ in range(20)],
                },
            },
        }
    ]
    postingan = [
        {
            "id_posting": f"post-{indeks}",
            "id_profil": "prof-1",
            "konten": "konten koordinasi " + ("penting " * 20),
            "timestamp": f"2026-04-{(indeks % 9) + 1:02d}T10:00:00+07:00",
            "isi_json": {
                "id_posting": f"post-{indeks}",
                "id_profil": "prof-1",
                "konten": "konten koordinasi " + ("penting " * 20),
                "platform": "telegram",
                "timestamp": f"2026-04-{(indeks % 9) + 1:02d}T10:00:00+07:00",
                "tipe_sumber": "terkoordinasi" if indeks == 39 else "organik",
                "tipe_konten": "teks",
                "kota": "Karawang",
                "provinsi": "Jawa Barat",
                "kata_kunci": ["drop", "jalur"],
                "referensi_mention": ["prof-2"] if indeks == 39 else [],
                "referensi_skenario": ["kasus-1"] if indeks == 39 else [],
                "engagement": {"suka": 50, "komentar": 10, "bagikan": 4},
            },
        }
        for indeks in range(40)
    ]
    payload_mentah = {
        "kasus": {"id_kasus": "kasus-1", "judul": "Kasus Uji"},
        "laporan": [{"id_laporan": "lap-1"}],
        "skor_risiko": [{"id_profil": "prof-1", "level_risiko": "TINGGI"}],
        "transaksi": [{"id_transaksi": "trx-1", "jumlah_idr": 1000000}],
        "kampanye": [],
        "profil": profil,
        "lokasi": [{"id_profil": "prof-1", "label": "lokasi-utama"} for _ in range(25)],
        "postingan": postingan,
        "graf": {"nodes": [{"id_profil": "prof-1", "nama": "Adi"}], "edges": []},
    }

    payload_ringkas = layanan._ringkas_payload_analisis_kasus(**payload_mentah)
    teks_mentah = json.dumps(payload_mentah, ensure_ascii=False, default=str)
    teks_ringkas = json.dumps(payload_ringkas, ensure_ascii=False, default=str)

    assert len(teks_ringkas) < len(teks_mentah) / 2
    assert "\"isi_json\"" not in teks_ringkas
    assert len(payload_ringkas["postingan"]) == 30
    assert payload_ringkas["postingan"][0]["tipe_sumber"] == "terkoordinasi"


def test_analisis_kasus_sindikat_memakai_timeout_khusus(monkeypatch) -> None:
    layanan = LayananOpenAI(_buat_pengaturan_uji(timeout_openai=45))
    rekaman: dict[str, object] = {}

    def jalankan_tiruan(nama_prompt, model_output, payload, timeout_detik=None):
        rekaman["nama_prompt"] = nama_prompt
        rekaman["payload"] = payload
        rekaman["timeout_detik"] = timeout_detik
        return DossierSindikat(
            id_kasus="kasus-1",
            judul_kasus="Kasus Uji",
            ringkasan_eksekutif="Ringkas",
            indikasi_sindikat=True,
            confidence=0.81,
        )

    monkeypatch.setattr(layanan, "_jalankan_terstruktur", jalankan_tiruan)

    hasil = layanan.analisis_kasus_sindikat(
        kasus={"id_kasus": "kasus-1", "judul": "Kasus Uji"},
        laporan=[],
        skor_risiko=[],
        transaksi=[],
        kampanye=[],
        profil=[{"id_profil": "prof-1", "nama_lengkap": "Adi"}],
        lokasi=[],
        postingan=[],
        graf={"nodes": [], "edges": []},
    )

    assert hasil.id_kasus == "kasus-1"
    assert rekaman["nama_prompt"] == "analisis_kasus_sindikat"
    assert rekaman["timeout_detik"] == 180
    assert rekaman["payload"]["profil"][0]["id_profil"] == "prof-1"
