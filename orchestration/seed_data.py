from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import psycopg
from kafka import KafkaProducer
from neo4j import GraphDatabase
from psycopg.rows import dict_row
from psycopg.types.json import Json

from orchestration.config import PengaturanRuntime
from orchestration.schema import MetadataEvent, OsintRawEvent, OsintRawPayload


class PenyiapData:
    """Menyiapkan skema relasional, isi awal data uji, dan seed graf Neo4j."""

    def __init__(self, pengaturan: PengaturanRuntime):
        self.pengaturan = pengaturan
        self.driver_neo4j = GraphDatabase.driver(
            pengaturan.uri_neo4j,
            auth=(pengaturan.pengguna_neo4j, pengaturan.sandi_neo4j),
        )

    def _koneksi_postgres(self) -> psycopg.Connection:
        return psycopg.connect(self.pengaturan.dsn_postgres, row_factory=dict_row)

    def siapkan_skema_relational(self) -> None:
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                kursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS osint_news (
                        id_berita TEXT PRIMARY KEY,
                        judul TEXT NOT NULL,
                        subjudul TEXT,
                        isi TEXT NOT NULL,
                        kategori TEXT,
                        provinsi TEXT,
                        lokasi TEXT,
                        reporter TEXT,
                        portal TEXT,
                        published_at TIMESTAMPTZ,
                        tags JSONB DEFAULT '[]'::jsonb,
                        isi_json JSONB NOT NULL,
                        dibuat_pada TIMESTAMPTZ DEFAULT NOW()
                    );
                    CREATE TABLE IF NOT EXISTS profil_watchlist (
                        id_profil TEXT PRIMARY KEY,
                        nama_lengkap TEXT,
                        nama_tampil TEXT,
                        kota TEXT,
                        provinsi TEXT,
                        latitude DOUBLE PRECISION,
                        longitude DOUBLE PRECISION,
                        bio TEXT,
                        isi_json JSONB NOT NULL,
                        dibuat_pada TIMESTAMPTZ DEFAULT NOW()
                    );
                    CREATE TABLE IF NOT EXISTS kontak_watchlist (
                        id_kontak TEXT PRIMARY KEY,
                        id_profil TEXT,
                        email TEXT,
                        telepon_lokal TEXT,
                        telepon_e164 TEXT,
                        kota TEXT,
                        provinsi TEXT,
                        isi_json JSONB NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS akun_watchlist (
                        id_akun TEXT PRIMARY KEY,
                        id_profil TEXT,
                        platform TEXT,
                        username TEXT,
                        url_profil TEXT,
                        jumlah_pengikut BIGINT,
                        terakhir_aktif_pada TIMESTAMPTZ,
                        isi_json JSONB NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS lokasi_histori (
                        id_lokasi TEXT PRIMARY KEY,
                        id_profil TEXT,
                        tipe_lokasi TEXT,
                        id_titik_pertemuan TEXT,
                        kota TEXT,
                        provinsi TEXT,
                        latitude DOUBLE PRECISION,
                        longitude DOUBLE PRECISION,
                        diamati_pada TIMESTAMPTZ,
                        isi_json JSONB NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS transaksi_histori (
                        id_transaksi TEXT PRIMARY KEY,
                        id_kasus TEXT,
                        id_profil_sumber TEXT,
                        id_profil_tujuan TEXT,
                        jumlah_idr DOUBLE PRECISION,
                        kanal TEXT,
                        timestamp TIMESTAMPTZ,
                        isi_json JSONB NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS kampanye_histori (
                        id_kampanye TEXT PRIMARY KEY,
                        id_kasus TEXT,
                        id_profil_pusat TEXT,
                        tujuan TEXT,
                        mulai_pada TIMESTAMPTZ,
                        isi_json JSONB NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS postingan_histori (
                        id_posting TEXT PRIMARY KEY,
                        id_profil TEXT,
                        id_akun TEXT,
                        platform TEXT,
                        konten TEXT,
                        kota TEXT,
                        provinsi TEXT,
                        latitude DOUBLE PRECISION,
                        longitude DOUBLE PRECISION,
                        timestamp TIMESTAMPTZ,
                        isi_json JSONB NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS laporan_kasus (
                        id_laporan TEXT PRIMARY KEY,
                        id_kasus TEXT,
                        judul TEXT,
                        ringkasan TEXT,
                        analisis TEXT,
                        isi_json JSONB NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS skor_risiko (
                        id_kasus TEXT PRIMARY KEY,
                        label_risiko TEXT,
                        skor_risiko DOUBLE PRECISION,
                        isi_json JSONB NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS kasus_intelijen (
                        id_kasus TEXT PRIMARY KEY,
                        tipe_kasus TEXT,
                        judul TEXT,
                        kota TEXT,
                        provinsi TEXT,
                        waktu_insiden TIMESTAMPTZ,
                        isi_json JSONB NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS audit_tool_call (
                        id BIGSERIAL PRIMARY KEY,
                        trace_id TEXT NOT NULL,
                        agent TEXT NOT NULL,
                        tool_name TEXT NOT NULL,
                        latency_ms INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        ringkasan_parameter JSONB NOT NULL,
                        dibuat_pada TIMESTAMPTZ DEFAULT NOW()
                    );
                    CREATE TABLE IF NOT EXISTS tia_briefings (
                        id BIGSERIAL PRIMARY KEY,
                        trace_id TEXT NOT NULL,
                        id_berita TEXT NOT NULL UNIQUE,
                        skor_agregat DOUBLE PRECISION NOT NULL,
                        level_ancaman TEXT NOT NULL,
                        briefing_json JSONB NOT NULL,
                        dibuat_pada TIMESTAMPTZ DEFAULT NOW(),
                        diperbarui_pada TIMESTAMPTZ DEFAULT NOW()
                    );
                    CREATE TABLE IF NOT EXISTS pta_results (
                        id BIGSERIAL PRIMARY KEY,
                        trace_id TEXT NOT NULL,
                        skor_ensemble DOUBLE PRECISION NOT NULL,
                        probabilitas_eskalasi DOUBLE PRECISION NOT NULL,
                        confidence_score DOUBLE PRECISION NOT NULL,
                        hasil_json JSONB NOT NULL,
                        dibuat_pada TIMESTAMPTZ DEFAULT NOW()
                    );
                    CREATE TABLE IF NOT EXISTS hitl_reviews (
                        id BIGSERIAL PRIMARY KEY,
                        trace_id TEXT NOT NULL,
                        risk_level TEXT NOT NULL,
                        approver_role TEXT NOT NULL,
                        payload_json JSONB NOT NULL,
                        dibuat_pada TIMESTAMPTZ DEFAULT NOW()
                    );
                    """
                )
            koneksi.commit()

    def _muat_json_array(self, jalur: Path) -> List[Dict[str, Any]]:
        with open(jalur, "r", encoding="utf-8") as file:
            return json.load(file)

    def seed_relational(self) -> None:
        self.siapkan_skema_relational()
        self._seed_berita()
        self._seed_profil()
        self._seed_kontak()
        self._seed_akun()
        self._seed_lokasi()
        self._seed_transaksi()
        self._seed_kampanye()
        self._seed_postingan()
        self._seed_laporan()
        self._seed_skor_risiko()
        self._seed_kasus()

    def _seed_berita(self) -> None:
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                with open(self.pengaturan.jalur_dataset_berita, "r", encoding="utf-8") as file:
                    for garis in file:
                        item = json.loads(garis)
                        kursor.execute(
                            """
                            INSERT INTO osint_news
                            (id_berita, judul, subjudul, isi, kategori, provinsi, lokasi, reporter, portal, published_at, tags, isi_json)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id_berita) DO NOTHING
                            """,
                            (
                                item["id"],
                                item.get("judul"),
                                item.get("subjudul"),
                                item.get("isi"),
                                item.get("kategori"),
                                item.get("provinsi"),
                                item.get("lokasi"),
                                item.get("reporter"),
                                item.get("portal"),
                                item.get("published_at"),
                                Json(item.get("tags", [])),
                                Json(item),
                            ),
                        )
            koneksi.commit()

    def _seed_profil(self) -> None:
        data = self._muat_json_array(self.pengaturan.direktori_dataset / "profil.json")
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                for item in data:
                    kursor.execute(
                        """
                        INSERT INTO profil_watchlist
                        (id_profil, nama_lengkap, nama_tampil, kota, provinsi, latitude, longitude, bio, isi_json)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id_profil) DO NOTHING
                        """,
                        (
                            item["id_profil"],
                            item.get("nama_lengkap"),
                            item.get("nama_tampil"),
                            item.get("kota"),
                            item.get("provinsi"),
                            item.get("latitude"),
                            item.get("longitude"),
                            item.get("bio"),
                            Json(item),
                        ),
                    )
            koneksi.commit()

    def _seed_kontak(self) -> None:
        data = self._muat_json_array(self.pengaturan.direktori_dataset / "kontak.json")
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                for item in data:
                    kursor.execute(
                        """
                        INSERT INTO kontak_watchlist
                        (id_kontak, id_profil, email, telepon_lokal, telepon_e164, kota, provinsi, isi_json)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id_kontak) DO NOTHING
                        """,
                        (
                            item["id_kontak"],
                            item.get("id_profil"),
                            item.get("email"),
                            item.get("telepon_lokal"),
                            item.get("telepon_e164"),
                            item.get("kota"),
                            item.get("provinsi"),
                            Json(item),
                        ),
                    )
            koneksi.commit()

    def _seed_akun(self) -> None:
        data = self._muat_json_array(self.pengaturan.direktori_dataset / "akun.json")
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                for item in data:
                    kursor.execute(
                        """
                        INSERT INTO akun_watchlist
                        (id_akun, id_profil, platform, username, url_profil, jumlah_pengikut, terakhir_aktif_pada, isi_json)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id_akun) DO NOTHING
                        """,
                        (
                            item["id_akun"],
                            item.get("id_profil"),
                            item.get("platform"),
                            item.get("username"),
                            item.get("url_profil"),
                            item.get("jumlah_pengikut"),
                            item.get("terakhir_aktif_pada"),
                            Json(item),
                        ),
                    )
            koneksi.commit()

    def _seed_lokasi(self) -> None:
        data = self._muat_json_array(self.pengaturan.direktori_dataset / "lokasi.json")
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                for item in data:
                    kursor.execute(
                        """
                        INSERT INTO lokasi_histori
                        (id_lokasi, id_profil, tipe_lokasi, id_titik_pertemuan, kota, provinsi, latitude, longitude, diamati_pada, isi_json)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id_lokasi) DO NOTHING
                        """,
                        (
                            item["id_lokasi"],
                            item.get("id_profil"),
                            item.get("tipe_lokasi"),
                            item.get("id_titik_pertemuan"),
                            item.get("kota"),
                            item.get("provinsi"),
                            item.get("latitude"),
                            item.get("longitude"),
                            item.get("diamati_pada"),
                            Json(item),
                        ),
                    )
            koneksi.commit()

    def _seed_transaksi(self) -> None:
        data = self._muat_json_array(self.pengaturan.direktori_dataset / "transaksi.json")
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                for item in data:
                    kursor.execute(
                        """
                        INSERT INTO transaksi_histori
                        (id_transaksi, id_kasus, id_profil_sumber, id_profil_tujuan, jumlah_idr, kanal, timestamp, isi_json)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id_transaksi) DO NOTHING
                        """,
                        (
                            item["id_transaksi"],
                            item.get("id_kasus"),
                            item.get("id_profil_sumber"),
                            item.get("id_profil_tujuan"),
                            item.get("jumlah_idr"),
                            item.get("kanal"),
                            item.get("timestamp"),
                            Json(item),
                        ),
                    )
            koneksi.commit()

    def _seed_kampanye(self) -> None:
        data = self._muat_json_array(self.pengaturan.direktori_dataset / "kampanye.json")
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                for item in data:
                    kursor.execute(
                        """
                        INSERT INTO kampanye_histori
                        (id_kampanye, id_kasus, id_profil_pusat, tujuan, mulai_pada, isi_json)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id_kampanye) DO NOTHING
                        """,
                        (
                            item["id_kampanye"],
                            item.get("id_kasus"),
                            item.get("id_profil_pusat"),
                            item.get("tujuan"),
                            item.get("mulai_pada"),
                            Json(item),
                        ),
                    )
            koneksi.commit()

    def _seed_postingan(self) -> None:
        data = self._muat_json_array(self.pengaturan.direktori_dataset / "postingan.json")
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                for item in data:
                    kursor.execute(
                        """
                        INSERT INTO postingan_histori
                        (id_posting, id_profil, id_akun, platform, konten, kota, provinsi, latitude, longitude, timestamp, isi_json)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id_posting) DO NOTHING
                        """,
                        (
                            item["id_posting"],
                            item.get("id_profil"),
                            item.get("id_akun"),
                            item.get("platform"),
                            item.get("konten"),
                            item.get("kota"),
                            item.get("provinsi"),
                            item.get("latitude"),
                            item.get("longitude"),
                            item.get("timestamp"),
                            Json(item),
                        ),
                    )
            koneksi.commit()

    def _seed_laporan(self) -> None:
        data = self._muat_json_array(self.pengaturan.direktori_dataset / "laporan.json")
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                for item in data:
                    kursor.execute(
                        """
                        INSERT INTO laporan_kasus
                        (id_laporan, id_kasus, judul, ringkasan, analisis, isi_json)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id_laporan) DO NOTHING
                        """,
                        (
                            item["id_laporan"],
                            item.get("id_kasus"),
                            item.get("judul"),
                            item.get("ringkasan"),
                            item.get("analisis"),
                            Json(item),
                        ),
                    )
            koneksi.commit()

    def _seed_skor_risiko(self) -> None:
        data = self._muat_json_array(self.pengaturan.direktori_dataset / "skor_risiko.json")
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                for item in data:
                    kursor.execute(
                        """
                        INSERT INTO skor_risiko
                        (id_kasus, label_risiko, skor_risiko, isi_json)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (id_kasus) DO NOTHING
                        """,
                        (
                            item["id_kasus"],
                            item.get("label_risiko"),
                            item.get("skor_risiko"),
                            Json(item),
                        ),
                    )
            koneksi.commit()

    def _seed_kasus(self) -> None:
        data = self._muat_json_array(self.pengaturan.direktori_dataset / "kasus.json")
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                for item in data:
                    kursor.execute(
                        """
                        INSERT INTO kasus_intelijen
                        (id_kasus, tipe_kasus, judul, kota, provinsi, waktu_insiden, isi_json)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id_kasus) DO NOTHING
                        """,
                        (
                            item["id_kasus"],
                            item.get("tipe_kasus"),
                            item.get("judul"),
                            item.get("kota"),
                            item.get("provinsi"),
                            item.get("waktu_insiden"),
                            Json(item),
                        ),
                    )
            koneksi.commit()

    def seed_neo4j(self) -> None:
        self._seed_neo4j_profil_dan_akun()
        self._seed_neo4j_lokasi()
        self._seed_neo4j_transaksi()
        self._seed_neo4j_kampanye_dan_kasus()

    def _seed_neo4j_profil_dan_akun(self) -> None:
        data_profil = self._muat_json_array(self.pengaturan.direktori_dataset / "profil.json")
        data_akun = self._muat_json_array(self.pengaturan.direktori_dataset / "akun.json")
        with self.driver_neo4j.session() as sesi:
            for profil in data_profil:
                sesi.run(
                    """
                    MERGE (p:Profil {id_profil: $id_profil})
                    SET p.nama_lengkap = $nama_lengkap,
                        p.nama_tampil = $nama_tampil,
                        p.kota = $kota,
                        p.provinsi = $provinsi
                    """,
                    id_profil=profil["id_profil"],
                    nama_lengkap=profil.get("nama_lengkap"),
                    nama_tampil=profil.get("nama_tampil"),
                    kota=profil.get("kota"),
                    provinsi=profil.get("provinsi"),
                )
            for akun in data_akun:
                sesi.run(
                    """
                    MERGE (a:Akun {id_akun: $id_akun})
                    SET a.username = $username, a.platform = $platform
                    WITH a
                    MATCH (p:Profil {id_profil: $id_profil})
                    MERGE (p)-[:MEMILIKI_AKUN]->(a)
                    """,
                    id_akun=akun["id_akun"],
                    id_profil=akun.get("id_profil"),
                    username=akun.get("username"),
                    platform=akun.get("platform"),
                )

    def _seed_neo4j_lokasi(self) -> None:
        data_lokasi = self._muat_json_array(self.pengaturan.direktori_dataset / "lokasi.json")
        with self.driver_neo4j.session() as sesi:
            for lokasi in data_lokasi:
                sesi.run(
                    """
                    MERGE (l:Lokasi {id_lokasi: $id_lokasi})
                    SET l.kota = $kota,
                        l.provinsi = $provinsi,
                        l.latitude = $latitude,
                        l.longitude = $longitude,
                        l.id_titik_pertemuan = $id_titik_pertemuan
                    WITH l
                    MATCH (p:Profil {id_profil: $id_profil})
                    MERGE (p)-[:BERADA_DI]->(l)
                    """,
                    id_lokasi=lokasi["id_lokasi"],
                    id_profil=lokasi.get("id_profil"),
                    kota=lokasi.get("kota"),
                    provinsi=lokasi.get("provinsi"),
                    latitude=lokasi.get("latitude"),
                    longitude=lokasi.get("longitude"),
                    id_titik_pertemuan=lokasi.get("id_titik_pertemuan"),
                )

    def _seed_neo4j_transaksi(self) -> None:
        data_transaksi = self._muat_json_array(self.pengaturan.direktori_dataset / "transaksi.json")
        with self.driver_neo4j.session() as sesi:
            for transaksi in data_transaksi:
                sesi.run(
                    """
                    MATCH (s:Profil {id_profil: $id_profil_sumber})
                    MATCH (t:Profil {id_profil: $id_profil_tujuan})
                    MERGE (s)-[r:MENTRANSFER {id_transaksi: $id_transaksi}]->(t)
                    SET r.jumlah_idr = $jumlah_idr,
                        r.kanal = $kanal,
                        r.timestamp = $timestamp
                    """,
                    id_transaksi=transaksi["id_transaksi"],
                    id_profil_sumber=transaksi.get("id_profil_sumber"),
                    id_profil_tujuan=transaksi.get("id_profil_tujuan"),
                    jumlah_idr=transaksi.get("jumlah_idr"),
                    kanal=transaksi.get("kanal"),
                    timestamp=transaksi.get("timestamp"),
                )

    def _seed_neo4j_kampanye_dan_kasus(self) -> None:
        data_kampanye = self._muat_json_array(self.pengaturan.direktori_dataset / "kampanye.json")
        data_kasus = self._muat_json_array(self.pengaturan.direktori_dataset / "kasus.json")
        with self.driver_neo4j.session() as sesi:
            for kasus in data_kasus:
                sesi.run(
                    """
                    MERGE (k:Kasus {id_kasus: $id_kasus})
                    SET k.judul = $judul, k.tipe_kasus = $tipe_kasus, k.kota = $kota
                    """,
                    id_kasus=kasus["id_kasus"],
                    judul=kasus.get("judul"),
                    tipe_kasus=kasus.get("tipe_kasus"),
                    kota=kasus.get("kota"),
                )
            for kampanye in data_kampanye:
                sesi.run(
                    """
                    MATCH (p:Profil {id_profil: $id_profil_pusat})
                    MATCH (k:Kasus {id_kasus: $id_kasus})
                    MERGE (p)-[:MENGAMPLIFIKASI]->(k)
                    """,
                    id_profil_pusat=kampanye.get("id_profil_pusat"),
                    id_kasus=kampanye.get("id_kasus"),
                )

    def terbitkan_berita_ke_kafka(self, limit: int | None = None, id_berita: str | None = None) -> int:
        producer = KafkaProducer(
            bootstrap_servers=self.pengaturan.kafka_bootstrap_servers.split(","),
            value_serializer=lambda nilai: json.dumps(nilai, ensure_ascii=True).encode("utf-8"),
        )
        jumlah = 0
        with open(self.pengaturan.jalur_dataset_berita, "r", encoding="utf-8") as file:
            for garis in file:
                item = json.loads(garis)
                if id_berita and item.get("id") != id_berita:
                    continue
                event = OsintRawEvent(
                    metadata=MetadataEvent(source_type="NEWS"),
                    payload=OsintRawPayload(
                        id_berita=item["id"],
                        judul=item.get("judul", ""),
                        subjudul=item.get("subjudul", ""),
                        isi=item.get("isi", ""),
                        kategori=item.get("kategori"),
                        provinsi=item.get("provinsi"),
                        lokasi=item.get("lokasi"),
                        reporter=item.get("reporter"),
                        portal=item.get("portal"),
                        published_at=item.get("published_at"),
                        tags=item.get("tags", []),
                    ),
                )
                producer.send(self.pengaturan.topik_osint_raw, event.model_dump(mode="json"))
                jumlah += 1
                if limit is not None and jumlah >= limit:
                    break
        producer.flush()
        producer.close()
        if id_berita and jumlah == 0:
            raise ValueError(f"Berita dengan id {id_berita} tidak ditemukan di dataset.")
        return jumlah

    def tutup(self) -> None:
        self.driver_neo4j.close()
