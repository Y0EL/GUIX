from __future__ import annotations

import time
from difflib import SequenceMatcher
from typing import Any, Callable, Dict, Iterable, List

import networkx as nx
import psycopg
from neo4j import GraphDatabase
from psycopg.rows import dict_row
from psycopg.types.json import Json

from orchestration.config import PengaturanRuntime


class McpGateway:
    """Gerbang tunggal akses data dan graph untuk seluruh agent."""

    def __init__(self, pengaturan: PengaturanRuntime):
        self.pengaturan = pengaturan
        self._driver_neo4j = GraphDatabase.driver(
            pengaturan.uri_neo4j,
            auth=(pengaturan.pengguna_neo4j, pengaturan.sandi_neo4j),
        )

    def _koneksi_postgres(self) -> psycopg.Connection:
        return psycopg.connect(self.pengaturan.dsn_postgres, row_factory=dict_row)

    def catat_audit_tool_call(
        self,
        trace_id: str,
        agent: str,
        tool_name: str,
        latency_ms: int,
        status: str,
        ringkasan_parameter: Dict[str, Any],
    ) -> None:
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                kursor.execute(
                    """
                    INSERT INTO audit_tool_call
                    (trace_id, agent, tool_name, latency_ms, status, ringkasan_parameter)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        trace_id,
                        agent,
                        tool_name,
                        latency_ms,
                        status,
                        Json(ringkasan_parameter),
                    ),
                )
            koneksi.commit()

    def _audit_wrap(
        self,
        trace_id: str,
        agent: str,
        tool_name: str,
        parameter: Dict[str, Any],
        fungsi: Callable[[], Any],
    ) -> Any:
        waktu_awal = time.perf_counter()
        status = "OK"
        try:
            return fungsi()
        except Exception:
            status = "ERROR"
            raise
        finally:
            latency = int((time.perf_counter() - waktu_awal) * 1000)
            self.catat_audit_tool_call(trace_id, agent, tool_name, latency, status, parameter)

    def ambil_osint_batch(self, trace_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        return self._audit_wrap(
            trace_id,
            "MCP",
            "ambil_osint_batch",
            {"limit": limit},
            lambda: self._ambil_osint_batch_impl(limit),
        )

    def ambil_bundle_kasus(self, trace_id: str, id_kasus: str) -> Dict[str, Any]:
        return self._audit_wrap(
            trace_id,
            "MCP",
            "ambil_bundle_kasus",
            {"id_kasus": id_kasus},
            lambda: self._ambil_bundle_kasus_impl(id_kasus),
        )

    def _ambil_bundle_kasus_impl(self, id_kasus: str) -> Dict[str, Any]:
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                kursor.execute("SELECT * FROM kasus_intelijen WHERE id_kasus = %s", (id_kasus,))
                kasus = kursor.fetchone()
                if not kasus:
                    raise ValueError(f"Kasus {id_kasus} tidak ditemukan.")

                kursor.execute("SELECT * FROM laporan_kasus WHERE id_kasus = %s ORDER BY id_laporan", (id_kasus,))
                laporan = list(kursor.fetchall())

                kursor.execute("SELECT * FROM skor_risiko WHERE id_kasus = %s", (id_kasus,))
                skor_risiko = list(kursor.fetchall())

                kursor.execute(
                    """
                    SELECT
                        t.*,
                        ps.nama_lengkap AS nama_sumber,
                        pt.nama_lengkap AS nama_tujuan
                    FROM transaksi_histori t
                    LEFT JOIN profil_watchlist ps ON ps.id_profil = t.id_profil_sumber
                    LEFT JOIN profil_watchlist pt ON pt.id_profil = t.id_profil_tujuan
                    WHERE t.id_kasus = %s
                    ORDER BY t.timestamp
                    """,
                    (id_kasus,),
                )
                transaksi = list(kursor.fetchall())

                kursor.execute(
                    """
                    SELECT
                        k.*,
                        p.nama_lengkap AS nama_profil_pusat
                    FROM kampanye_histori k
                    LEFT JOIN profil_watchlist p ON p.id_profil = k.id_profil_pusat
                    WHERE k.id_kasus = %s
                    ORDER BY k.mulai_pada
                    """,
                    (id_kasus,),
                )
                kampanye = list(kursor.fetchall())

                id_profil_terkait = set()
                for item in transaksi:
                    if item.get("id_profil_sumber"):
                        id_profil_terkait.add(item["id_profil_sumber"])
                    if item.get("id_profil_tujuan"):
                        id_profil_terkait.add(item["id_profil_tujuan"])
                for item in kampanye:
                    if item.get("id_profil_pusat"):
                        id_profil_terkait.add(item["id_profil_pusat"])

                profil = []
                lokasi = []
                postingan = []
                if id_profil_terkait:
                    daftar = sorted(id_profil_terkait)
                    kursor.execute(
                        "SELECT * FROM profil_watchlist WHERE id_profil = ANY(%s) ORDER BY nama_lengkap",
                        (daftar,),
                    )
                    profil = list(kursor.fetchall())
                    kursor.execute(
                        """
                        SELECT *
                        FROM lokasi_histori
                        WHERE id_profil = ANY(%s)
                        ORDER BY diamati_pada DESC NULLS LAST
                        LIMIT 200
                        """,
                        (daftar,),
                    )
                    lokasi = list(kursor.fetchall())
                    kursor.execute(
                        """
                        SELECT *
                        FROM postingan_histori
                        WHERE id_profil = ANY(%s)
                        ORDER BY timestamp DESC NULLS LAST
                        LIMIT 200
                        """,
                        (daftar,),
                    )
                    postingan = list(kursor.fetchall())

        graf = self._ambil_graf_kasus(id_kasus, sorted(id_profil_terkait))
        return {
            "kasus": kasus,
            "laporan": laporan,
            "skor_risiko": skor_risiko,
            "transaksi": transaksi,
            "kampanye": kampanye,
            "profil": profil,
            "lokasi": lokasi,
            "postingan": postingan,
            "graf": graf,
        }

    def _ambil_graf_kasus(self, id_kasus: str, id_profil_terkait: List[str]) -> Dict[str, Any]:
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        if not id_profil_terkait:
            return {"nodes": nodes, "edges": edges}
        with self._driver_neo4j.session() as sesi:
            hasil_nodes = sesi.run(
                """
                MATCH (p:Profil)
                WHERE p.id_profil IN $ids
                RETURN p.id_profil AS id_profil, p.nama AS nama, labels(p) AS labels
                """,
                ids=id_profil_terkait,
            )
            for record in hasil_nodes:
                nodes.append(
                    {
                        "id_profil": record["id_profil"],
                        "nama": record["nama"],
                        "labels": record["labels"],
                    }
                )

            hasil_transaksi = sesi.run(
                """
                MATCH (s:Profil)-[r:MENTRANSFER]->(t:Profil)
                WHERE s.id_profil IN $ids OR t.id_profil IN $ids
                RETURN s.id_profil AS sumber_id,
                       s.nama AS sumber,
                       t.id_profil AS target_id,
                       t.nama AS target,
                       type(r) AS jenis_relasi,
                       r.jumlah_idr AS jumlah_idr,
                       r.kanal AS kanal
                LIMIT 300
                """,
                ids=id_profil_terkait,
            )
            for record in hasil_transaksi:
                edges.append(
                    {
                        "sumber_id": record["sumber_id"],
                        "sumber": record["sumber"],
                        "target_id": record["target_id"],
                        "target": record["target"],
                        "jenis_relasi": record["jenis_relasi"],
                        "jumlah_idr": record["jumlah_idr"],
                        "kanal": record["kanal"],
                    }
                )

            hasil_kampanye = sesi.run(
                """
                MATCH (p:Profil)-[r:MENGAMPLIFIKASI]->(k:Kasus {id_kasus: $id_kasus})
                RETURN p.id_profil AS sumber_id,
                       p.nama AS sumber,
                       k.id_kasus AS target_id,
                       k.judul AS target,
                       type(r) AS jenis_relasi
                """,
                id_kasus=id_kasus,
            )
            for record in hasil_kampanye:
                edges.append(
                    {
                        "sumber_id": record["sumber_id"],
                        "sumber": record["sumber"],
                        "target_id": record["target_id"],
                        "target": record["target"],
                        "jenis_relasi": record["jenis_relasi"],
                    }
                )
        return {"nodes": nodes, "edges": edges}

    def _ambil_osint_batch_impl(self, limit: int) -> List[Dict[str, Any]]:
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                kursor.execute(
                    """
                    SELECT *
                    FROM osint_news
                    ORDER BY published_at DESC NULLS LAST
                    LIMIT %s
                    """,
                    (limit,),
                )
                return list(kursor.fetchall())

    def ambil_watchlist_profile(self, trace_id: str, entitas: str) -> List[Dict[str, Any]]:
        return self._audit_wrap(
            trace_id,
            "MCP",
            "ambil_watchlist_profile",
            {"entitas": entitas},
            lambda: self._ambil_watchlist_profile_impl(entitas),
        )

    def _ambil_watchlist_profile_impl(self, entitas: str) -> List[Dict[str, Any]]:
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                kursor.execute(
                    """
                    SELECT
                        p.id_profil,
                        p.nama_lengkap,
                        p.nama_tampil,
                        p.kota,
                        p.provinsi,
                        COALESCE(json_agg(DISTINCT a.isi_json) FILTER (WHERE a.id_akun IS NOT NULL), '[]'::json) AS akun,
                        COALESCE(json_agg(DISTINCT k.isi_json) FILTER (WHERE k.id_kontak IS NOT NULL), '[]'::json) AS kontak
                    FROM profil_watchlist p
                    LEFT JOIN akun_watchlist a ON a.id_profil = p.id_profil
                    LEFT JOIN kontak_watchlist k ON k.id_profil = p.id_profil
                    GROUP BY p.id_profil, p.nama_lengkap, p.nama_tampil, p.kota, p.provinsi
                    """
                )
                kandidat = list(kursor.fetchall())

        entitas_lower = entitas.lower()
        hasil: List[Dict[str, Any]] = []
        for item in kandidat:
            daftar_banding = [
                item.get("nama_lengkap") or "",
                item.get("nama_tampil") or "",
            ]
            for akun in item.get("akun") or []:
                daftar_banding.append(str((akun or {}).get("username", "")))
            for kontak in item.get("kontak") or []:
                daftar_banding.append(str((kontak or {}).get("email", "")))
                daftar_banding.append(str((kontak or {}).get("telepon_lokal", "")))
                daftar_banding.append(str((kontak or {}).get("telepon_e164", "")))

            skor_terbaik = 0.0
            alasan = []
            for kandidat_teks in daftar_banding:
                if not kandidat_teks:
                    continue
                skor = SequenceMatcher(None, entitas_lower, kandidat_teks.lower()).ratio()
                if entitas_lower in kandidat_teks.lower() or kandidat_teks.lower() in entitas_lower:
                    skor = max(skor, 0.88)
                if skor > skor_terbaik:
                    skor_terbaik = skor
                    alasan = [kandidat_teks]
            if skor_terbaik >= 0.58:
                hasil.append(
                    {
                        "id_profil": item["id_profil"],
                        "nama_lengkap": item["nama_lengkap"],
                        "nama_tampil": item["nama_tampil"],
                        "kota": item["kota"],
                        "provinsi": item["provinsi"],
                        "skor_kecocokan": round(skor_terbaik, 4),
                        "alasan_kecocokan": alasan,
                    }
                )
        hasil.sort(key=lambda nilai: nilai["skor_kecocokan"], reverse=True)
        return hasil[:10]

    def ambil_histori_entitas(self, trace_id: str, id_profil: str) -> Dict[str, Any]:
        return self._audit_wrap(
            trace_id,
            "MCP",
            "ambil_histori_entitas",
            {"id_profil": id_profil},
            lambda: self._ambil_histori_entitas_impl(id_profil),
        )

    def _ambil_histori_entitas_impl(self, id_profil: str) -> Dict[str, Any]:
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                kursor.execute("SELECT * FROM profil_watchlist WHERE id_profil = %s", (id_profil,))
                profil = kursor.fetchone()
                kursor.execute(
                    "SELECT * FROM akun_watchlist WHERE id_profil = %s ORDER BY terakhir_aktif_pada DESC NULLS LAST",
                    (id_profil,),
                )
                akun = list(kursor.fetchall())
                kursor.execute(
                    "SELECT * FROM postingan_histori WHERE id_profil = %s ORDER BY timestamp DESC NULLS LAST LIMIT 50",
                    (id_profil,),
                )
                postingan = list(kursor.fetchall())
        return {"profil": profil, "akun": akun, "postingan": postingan}

    def ambil_histori_lokasi(self, trace_id: str, id_profil: str) -> List[Dict[str, Any]]:
        return self._audit_wrap(
            trace_id,
            "MCP",
            "ambil_histori_lokasi",
            {"id_profil": id_profil},
            lambda: self._ambil_histori_lokasi_impl(id_profil),
        )

    def _ambil_histori_lokasi_impl(self, id_profil: str) -> List[Dict[str, Any]]:
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                kursor.execute(
                    """
                    SELECT *
                    FROM lokasi_histori
                    WHERE id_profil = %s
                    ORDER BY diamati_pada DESC NULLS LAST
                    LIMIT 100
                    """,
                    (id_profil,),
                )
                return list(kursor.fetchall())

    def ambil_histori_transaksi(self, trace_id: str, id_profil: str) -> List[Dict[str, Any]]:
        return self._audit_wrap(
            trace_id,
            "MCP",
            "ambil_histori_transaksi",
            {"id_profil": id_profil},
            lambda: self._ambil_histori_transaksi_impl(id_profil),
        )

    def _ambil_histori_transaksi_impl(self, id_profil: str) -> List[Dict[str, Any]]:
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                kursor.execute(
                    """
                    SELECT *
                    FROM transaksi_histori
                    WHERE id_profil_sumber = %s OR id_profil_tujuan = %s
                    ORDER BY timestamp DESC NULLS LAST
                    LIMIT 100
                    """,
                    (id_profil, id_profil),
                )
                return list(kursor.fetchall())

    def ambil_histori_kampanye(self, trace_id: str, id_profil: str) -> List[Dict[str, Any]]:
        return self._audit_wrap(
            trace_id,
            "MCP",
            "ambil_histori_kampanye",
            {"id_profil": id_profil},
            lambda: self._ambil_histori_kampanye_impl(id_profil),
        )

    def _ambil_histori_kampanye_impl(self, id_profil: str) -> List[Dict[str, Any]]:
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                kursor.execute(
                    """
                    SELECT *
                    FROM kampanye_histori
                    WHERE id_profil_pusat = %s
                    ORDER BY mulai_pada DESC NULLS LAST
                    LIMIT 50
                    """,
                    (id_profil,),
                )
                return list(kursor.fetchall())

    def ambil_konteks_rag(self, trace_id: str, entitas: Iterable[str]) -> Dict[str, Any]:
        daftar_entitas = [str(item).strip() for item in entitas if str(item).strip()]
        return self._audit_wrap(
            trace_id,
            "MCP",
            "ambil_konteks_rag",
            {"jumlah_entitas": len(daftar_entitas)},
            lambda: self._ambil_konteks_rag_impl(daftar_entitas),
        )

    def _ambil_konteks_rag_impl(self, daftar_entitas: List[str]) -> Dict[str, Any]:
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                kursor.execute("SELECT * FROM laporan_kasus ORDER BY id_laporan LIMIT 40")
                laporan = list(kursor.fetchall())
                kursor.execute("SELECT * FROM skor_risiko ORDER BY skor_risiko DESC LIMIT 40")
                skor_risiko = list(kursor.fetchall())
                kursor.execute(
                    "SELECT * FROM postingan_histori ORDER BY timestamp DESC NULLS LAST LIMIT 80"
                )
                postingan = list(kursor.fetchall())

        if not daftar_entitas:
            return {"laporan": laporan[:20], "skor_risiko": skor_risiko[:20], "postingan": postingan[:30]}

        daftar_entitas_lower = [item.lower() for item in daftar_entitas]

        def cocok_dengan_entitas(item: Dict[str, Any], bidang: List[str]) -> bool:
            gabungan = " ".join(str(item.get(bidang_item, "")) for bidang_item in bidang).lower()
            return any(entitas in gabungan for entitas in daftar_entitas_lower)

        laporan_terpilih = [item for item in laporan if cocok_dengan_entitas(item, ["judul", "ringkasan", "analisis"])]
        postingan_terpilih = [item for item in postingan if cocok_dengan_entitas(item, ["konten", "kota", "provinsi"])]
        skor_terpilih = [
            item for item in skor_risiko if cocok_dengan_entitas(item, ["id_kasus", "label_risiko"])
        ]

        return {
            "laporan": (laporan_terpilih or laporan)[:20],
            "skor_risiko": (skor_terpilih or skor_risiko)[:20],
            "postingan": (postingan_terpilih or postingan)[:30],
        }

    def upsert_relasi_graf(self, trace_id: str, relasi: List[Dict[str, Any]]) -> None:
        self._audit_wrap(
            trace_id,
            "MCP",
            "upsert_relasi_graf",
            {"jumlah_relasi": len(relasi)},
            lambda: self._upsert_relasi_graf_impl(relasi),
        )

    def _upsert_relasi_graf_impl(self, relasi: List[Dict[str, Any]]) -> None:
        with self._driver_neo4j.session() as sesi:
            for item in relasi:
                label_subjek = item.get("tipe_subjek", "Entitas").title().replace(" ", "")
                label_objek = item.get("tipe_objek", "Entitas").title().replace(" ", "")
                query = f"""
                MERGE (s:{label_subjek} {{nama: $subjek}})
                MERGE (o:{label_objek} {{nama: $objek}})
                MERGE (s)-[r:{item["predikat"].upper().replace(" ", "_")}]->(o)
                SET r.evidence_text = $evidence_text,
                    r.confidence = $confidence
                """
                sesi.run(
                    query,
                    subjek=item["subjek"],
                    objek=item["objek"],
                    evidence_text=item.get("evidence_text", ""),
                    confidence=float(item.get("confidence", 0.0)),
                )

    def ambil_subgraf_entitas(self, trace_id: str, entitas: List[str]) -> nx.Graph:
        return self._audit_wrap(
            trace_id,
            "MCP",
            "ambil_subgraf_entitas",
            {"jumlah_entitas": len(entitas)},
            lambda: self._ambil_subgraf_entitas_impl(entitas),
        )

    def _ambil_subgraf_entitas_impl(self, entitas: List[str]) -> nx.Graph:
        graf = nx.Graph()
        if not entitas:
            return graf
        with self._driver_neo4j.session() as sesi:
            hasil = sesi.run(
                """
                UNWIND $entitas AS nama
                MATCH (a)-[r]-(b)
                WHERE a.nama = nama OR b.nama = nama
                RETURN a.nama AS sumber, b.nama AS tujuan, type(r) AS relasi, r.confidence AS confidence
                LIMIT 500
                """,
                entitas=entitas,
            )
            for record in hasil:
                graf.add_edge(
                    record["sumber"],
                    record["tujuan"],
                    relasi=record["relasi"],
                    confidence=record["confidence"] or 0.0,
                )
        return graf

    def simpan_briefing_tia(self, trace_id: str, payload: Dict[str, Any]) -> None:
        self._audit_wrap(
            trace_id,
            "MCP",
            "simpan_briefing_tia",
            {"id_berita": payload.get("id_berita")},
            lambda: self._simpan_briefing_tia_impl(payload),
        )

    def _simpan_briefing_tia_impl(self, payload: Dict[str, Any]) -> None:
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                kursor.execute(
                    """
                    INSERT INTO tia_briefings
                    (trace_id, id_berita, skor_agregat, level_ancaman, briefing_json)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id_berita) DO UPDATE
                    SET trace_id = EXCLUDED.trace_id,
                        skor_agregat = EXCLUDED.skor_agregat,
                        level_ancaman = EXCLUDED.level_ancaman,
                        briefing_json = EXCLUDED.briefing_json,
                        diperbarui_pada = NOW()
                    """,
                    (
                        payload["trace_id"],
                        payload["id_berita"],
                        payload["skor_agregat"],
                        payload["level_ancaman"],
                        Json(payload),
                    ),
                )
            koneksi.commit()

    def simpan_hasil_pta(self, trace_id: str, payload: Dict[str, Any]) -> None:
        self._audit_wrap(
            trace_id,
            "MCP",
            "simpan_hasil_pta",
            {"trace_id": trace_id},
            lambda: self._simpan_hasil_pta_impl(payload),
        )

    def _simpan_hasil_pta_impl(self, payload: Dict[str, Any]) -> None:
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                kursor.execute(
                    """
                    INSERT INTO pta_results
                    (trace_id, skor_ensemble, probabilitas_eskalasi, confidence_score, hasil_json)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        payload["trace_id"],
                        payload["skor_ensemble"],
                        payload["probabilitas_eskalasi"],
                        payload["confidence_score"],
                        Json(payload),
                    ),
                )
            koneksi.commit()

    def simpan_review_hitl(self, trace_id: str, payload: Dict[str, Any]) -> None:
        self._audit_wrap(
            trace_id,
            "MCP",
            "simpan_review_hitl",
            {"risk_level": payload.get("risk_level") or (payload.get("payload") or {}).get("risk_level")},
            lambda: self._simpan_review_hitl_impl(payload),
        )

    def _simpan_review_hitl_impl(self, payload: Dict[str, Any]) -> None:
        payload_review = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        trace_id = payload_review.get("trace_id") or payload.get("trace_id") or metadata.get("trace_id")
        with self._koneksi_postgres() as koneksi:
            with koneksi.cursor() as kursor:
                kursor.execute(
                    """
                    INSERT INTO hitl_reviews
                    (trace_id, risk_level, approver_role, payload_json)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        trace_id,
                        payload_review.get("risk_level"),
                        payload_review.get("approver_role"),
                        Json(payload),
                    ),
                )
            koneksi.commit()

    def tutup(self) -> None:
        self._driver_neo4j.close()
