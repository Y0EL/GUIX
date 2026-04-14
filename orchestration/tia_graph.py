from __future__ import annotations

import re
from typing import Any, Dict, List, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from orchestration.config import PengaturanRuntime
from orchestration.hitl import bentuk_payload_hitl, route_review
from orchestration.logging_utils import logger_dengan_trace
from orchestration.mcp import McpGateway
from orchestration.openai_stack import LayananOpenAI
from orchestration.schema import (
    BuktiIntelijen,
    EntitasTerekstrak,
    HasilKritikAncaman,
    HasilReviewBriefing,
    HasilVerifikasiEntitas,
    HitWatchlist,
    MetadataEvent,
    OsintRawEvent,
    PenilaianAncaman,
    PaketBukti,
    RencanaRetrieval,
    TiaThreatEvent,
    TiaThreatPayload,
    ToolCallRencana,
)
from orchestration.tools import jalankan_rencana_retrieval
from orchestration.transport import TransportRuntime


class StatusTIA(TypedDict, total=False):
    event_raw: Dict[str, Any]
    trace_id: str
    skor_relevansi: float
    aturan_terpicu: List[str]
    kata_kunci_terdeteksi: List[str]
    kandidat_entitas: List[str]
    kandidat_bukti: List[Dict[str, Any]]
    putusan_planner: Dict[str, Any]
    hasil_retrieval: Dict[str, Any]
    tool_calls_terpakai: List[Dict[str, Any]]
    jumlah_putaran_retrieval: int
    entitas: List[Dict[str, Any]]
    hasil_verifikasi_entitas: Dict[str, Any]
    hit_watchlist: List[Dict[str, Any]]
    penilaian_awal: Dict[str, Any]
    hasil_kritik_ancaman: Dict[str, Any]
    penilaian_ancaman: Dict[str, Any]
    skor_agregat: float
    konteks_bundle: Dict[str, Any]
    evidence_ranked: Dict[str, Any]
    briefing: Dict[str, Any]
    review_briefing: Dict[str, Any]
    event_tia: Dict[str, Any]
    status_review: str
    stop: bool
    alasan_stop: str


class MesinTIA:
    batas_putaran_retrieval = 2

    def __init__(
        self,
        pengaturan: PengaturanRuntime,
        transport: TransportRuntime,
        mcp: McpGateway,
        layanan_openai: LayananOpenAI,
    ):
        self.pengaturan = pengaturan
        self.transport = transport
        self.mcp = mcp
        self.layanan_openai = layanan_openai
        self.graph = self._bangun_graf()

    def _bangun_graf(self):
        builder = StateGraph(StatusTIA)
        builder.add_node("consume_kafka_osint", self.consume_kafka_osint)
        builder.add_node("deteksi_sinyal_awal", self.deteksi_sinyal_awal)
        builder.add_node("planner_retrieval", self.planner_retrieval)
        builder.add_node("retrieval_mcp", self.retrieval_mcp)
        builder.add_node("ekstraksi_entitas_putaran_1", self.ekstraksi_entitas_putaran_1)
        builder.add_node("verifikasi_entitas", self.verifikasi_entitas)
        builder.add_node("watchlist_correlation", self.watchlist_correlation)
        builder.add_node("threat_assessment_awal", self.threat_assessment_awal)
        builder.add_node("critic_threat_assessment", self.critic_threat_assessment)
        builder.add_node("penilaian_akhir", self.penilaian_akhir)
        builder.add_node("rag_evidence_ranking", self.rag_evidence_ranking)
        builder.add_node("draft_briefing", self.draft_briefing)
        builder.add_node("node_review_briefing", self.review_briefing)
        builder.add_node("publish_tia", self.publish_tia)

        builder.set_entry_point("consume_kafka_osint")
        builder.add_edge("consume_kafka_osint", "deteksi_sinyal_awal")
        builder.add_conditional_edges(
            "deteksi_sinyal_awal",
            self._rute_relevansi,
            {"lanjut": "planner_retrieval", "berhenti": END},
        )
        builder.add_edge("planner_retrieval", "retrieval_mcp")
        builder.add_edge("retrieval_mcp", "ekstraksi_entitas_putaran_1")
        builder.add_edge("ekstraksi_entitas_putaran_1", "verifikasi_entitas")
        builder.add_conditional_edges(
            "verifikasi_entitas",
            self._rute_verifikasi_entitas,
            {"ulang": "planner_retrieval", "lanjut": "watchlist_correlation", "berhenti": END},
        )
        builder.add_edge("watchlist_correlation", "threat_assessment_awal")
        builder.add_edge("threat_assessment_awal", "critic_threat_assessment")
        builder.add_conditional_edges(
            "critic_threat_assessment",
            self._rute_kritik_ancaman,
            {"ulang": "planner_retrieval", "lanjut": "penilaian_akhir", "berhenti": END},
        )
        builder.add_edge("penilaian_akhir", "rag_evidence_ranking")
        builder.add_edge("rag_evidence_ranking", "draft_briefing")
        builder.add_edge("draft_briefing", "node_review_briefing")
        builder.add_conditional_edges(
            "node_review_briefing",
            self._rute_review_briefing,
            {"ulang": "planner_retrieval", "lanjut": "publish_tia", "berhenti": END},
        )
        builder.add_edge("publish_tia", END)
        return builder.compile(checkpointer=MemorySaver())

    def _rute_relevansi(self, state: StatusTIA) -> str:
        if state.get("stop"):
            return "berhenti"
        return "lanjut" if state.get("skor_relevansi", 0.0) >= self.pengaturan.ambang_relevansi else "berhenti"

    def _rute_verifikasi_entitas(self, state: StatusTIA) -> str:
        if state.get("stop"):
            return "berhenti"
        hasil = HasilVerifikasiEntitas.model_validate(state.get("hasil_verifikasi_entitas", {}))
        if hasil.butuh_retrieval_tambahan and state.get("jumlah_putaran_retrieval", 0) < self.batas_putaran_retrieval:
            return "ulang"
        return "lanjut"

    def _rute_kritik_ancaman(self, state: StatusTIA) -> str:
        if state.get("stop"):
            return "berhenti"
        hasil = HasilKritikAncaman.model_validate(state.get("hasil_kritik_ancaman", {}))
        if hasil.butuh_retrieval_tambahan and state.get("jumlah_putaran_retrieval", 0) < self.batas_putaran_retrieval:
            return "ulang"
        return "lanjut"

    def _rute_review_briefing(self, state: StatusTIA) -> str:
        if state.get("stop"):
            return "berhenti"
        hasil = HasilReviewBriefing.model_validate(state.get("review_briefing", {}))
        if (
            hasil.status_review == "perlu_perbaikan"
            and hasil.butuh_retrieval_tambahan
            and state.get("jumlah_putaran_retrieval", 0) < self.batas_putaran_retrieval
        ):
            return "ulang"
        return "lanjut"

    def _turunkan_level(self, level: str) -> str:
        urutan = ["RENDAH", "SEDANG", "TINGGI", "KRITIS"]
        if level not in urutan:
            return "SEDANG"
        indeks = max(0, urutan.index(level) - 1)
        return urutan[indeks]

    def _buat_dead_letter(self, trace_id: str, tahap: str, alasan: str, payload: dict[str, Any]) -> None:
        self.transport.terbitkan_dead_letter(
            self.pengaturan.aliran_tia_keluar,
            {
                "trace_id": trace_id,
                "tahap": tahap,
                "alasan": alasan,
                "payload": payload,
            },
        )

    def _kandidat_entitas_awal(self, isi: str) -> List[str]:
        kandidat_nama = re.findall(r"\b[A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+){0,2}\b", isi)
        kandidat_akun = re.findall(r"@[A-Za-z0-9_\.]+", isi)
        kandidat_email = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", isi)
        return list(dict.fromkeys((kandidat_nama + kandidat_akun + kandidat_email)[:30]))

    def _buat_bukti_aturan(
        self,
        aturan_terpicu: List[str],
        kata_kunci: List[str],
        kandidat_entitas: List[str],
    ) -> List[Dict[str, Any]]:
        hasil: List[Dict[str, Any]] = []
        for aturan in aturan_terpicu:
            hasil.append(
                BuktiIntelijen(
                    sumber="deteksi_sinyal_awal",
                    kategori="aturan",
                    ringkasan=f"Aturan {aturan} terpicu oleh kata kunci: {', '.join(kata_kunci[:6])}",
                    skor_penting=0.55,
                    keterkaitan_entitas=kandidat_entitas[:6],
                    confidence=0.62,
                ).model_dump()
            )
        return hasil

    def _buat_bukti_watchlist(self, hit_watchlist: List[Dict[str, Any]], entitas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        bukti: List[Dict[str, Any]] = []
        nama_entitas = [item["nilai"] for item in entitas][:6]
        for item in hit_watchlist[:10]:
            bukti.append(
                BuktiIntelijen(
                    sumber="watchlist_correlation",
                    kategori="watchlist",
                    ringkasan=(
                        f"Kecocokan watchlist pada {item['nama_lengkap']} "
                        f"dengan skor {round(item['skor_kecocokan'], 2)}"
                    ),
                    skor_penting=min(1.0, 0.6 + (item["skor_kecocokan"] * 0.4)),
                    keterkaitan_entitas=nama_entitas,
                    confidence=min(1.0, item["skor_kecocokan"]),
                ).model_dump()
            )
        return bukti

    def _buat_bukti_kritik(self, hasil_kritik: HasilKritikAncaman, entitas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        nama_entitas = [item["nilai"] for item in entitas][:6]
        bukti: List[Dict[str, Any]] = []
        for celah in hasil_kritik.celah_bukti[:5]:
            bukti.append(
                BuktiIntelijen(
                    sumber="critic_threat_assessment",
                    kategori="celah_bukti",
                    ringkasan=celah,
                    skor_penting=0.45,
                    keterkaitan_entitas=nama_entitas,
                    confidence=0.6,
                ).model_dump()
            )
        for kontradiksi in hasil_kritik.kontradiksi_ditemukan[:5]:
            bukti.append(
                BuktiIntelijen(
                    sumber="critic_threat_assessment",
                    kategori="kontradiksi",
                    ringkasan=kontradiksi,
                    skor_penting=0.7,
                    keterkaitan_entitas=nama_entitas,
                    confidence=0.75,
                ).model_dump()
            )
        return bukti

    def _gabungkan_konteks(self, state: StatusTIA, hasil_retrieval: dict[str, Any]) -> dict[str, Any]:
        konteks = dict(state.get("konteks_bundle", {}))
        for kunci, nilai in hasil_retrieval.items():
            jika_lama = konteks.get(kunci)
            if isinstance(jika_lama, list) and isinstance(nilai, list):
                konteks[kunci] = jika_lama + nilai
            elif isinstance(jika_lama, dict) and isinstance(nilai, dict):
                gabungan = dict(jika_lama)
                gabungan.update(nilai)
                konteks[kunci] = gabungan
            else:
                konteks[kunci] = nilai
        return konteks

    def consume_kafka_osint(self, state: StatusTIA) -> StatusTIA:
        return state

    def deteksi_sinyal_awal(self, state: StatusTIA) -> StatusTIA:
        event = OsintRawEvent.model_validate(state["event_raw"])
        logger = logger_dengan_trace(__name__, state["trace_id"])
        teks = f"{event.payload.judul} {event.payload.subjudul} {event.payload.isi}".lower()

        peta_aturan = {
            "kekerasan_langsung": ["serangan", "penembakan", "penyerangan", "ledakan"],
            "ancaman_eksplisit": ["ancaman", "bom", "senjata", "sabotase"],
            "lokasi_sensitif": ["gudang", "pelabuhan", "bandara", "markas", "pemerintah"],
            "urgensi_temporal": ["hari ini", "malam ini", "segera", "mendadak"],
            "narasi_terkoordinasi": ["seragam", "sinkron", "amplifikasi", "berulang"],
        }
        bobot_aturan = {
            "kekerasan_langsung": 0.35,
            "ancaman_eksplisit": 0.25,
            "lokasi_sensitif": 0.15,
            "urgensi_temporal": 0.1,
            "narasi_terkoordinasi": 0.15,
        }

        aturan_terpicu: List[str] = []
        kata_kunci_terdeteksi: List[str] = []
        bobot_total = 0.0
        for nama_aturan, daftar_kata in peta_aturan.items():
            terdeteksi = [kata for kata in daftar_kata if kata in teks]
            if terdeteksi:
                aturan_terpicu.append(nama_aturan)
                kata_kunci_terdeteksi.extend(terdeteksi)
                bobot_total += bobot_aturan[nama_aturan]

        jika_kategori_tinggi = event.payload.kategori in {"Keamanan", "Hukum & Kriminal"}
        jika_portal_aktif = bool(event.payload.portal)
        skor_relevansi = min(
            1.0,
            bobot_total + (0.1 if jika_kategori_tinggi else 0.0) + (0.05 if jika_portal_aktif else 0.0),
        )
        kandidat_entitas = self._kandidat_entitas_awal(event.payload.isi)
        kandidat_bukti = self._buat_bukti_aturan(aturan_terpicu, kata_kunci_terdeteksi, kandidat_entitas)
        logger.info(
            "TIA deteksi_sinyal_awal selesai",
            extra={
                "extra_payload": {
                    "skor_relevansi": skor_relevansi,
                    "aturan": aturan_terpicu,
                    "jumlah_kandidat_entitas": len(kandidat_entitas),
                }
            },
        )
        return {
            "skor_relevansi": skor_relevansi,
            "aturan_terpicu": aturan_terpicu,
            "kata_kunci_terdeteksi": kata_kunci_terdeteksi,
            "kandidat_entitas": kandidat_entitas,
            "kandidat_bukti": kandidat_bukti,
            "jumlah_putaran_retrieval": state.get("jumlah_putaran_retrieval", 0),
        }

    def planner_retrieval(self, state: StatusTIA) -> StatusTIA:
        event = OsintRawEvent.model_validate(state["event_raw"])
        retrieval_sebelumnya = state.get("tool_calls_terpakai", [])
        rencana = self.layanan_openai.rencanakan_retrieval_tia(
            judul=event.payload.judul,
            isi=event.payload.isi,
            sinyal_awal={
                "skor_relevansi": state.get("skor_relevansi", 0.0),
                "aturan_terpicu": state.get("aturan_terpicu", []),
                "kata_kunci_terdeteksi": state.get("kata_kunci_terdeteksi", []),
            },
            entitas_kandidat=state.get("kandidat_entitas", []),
            retrieval_sebelumnya=retrieval_sebelumnya,
        )
        if not rencana.calls:
            rencana = RencanaRetrieval(
                tujuan="Ambil konteks awal untuk memperkuat pemahaman ancaman.",
                calls=[
                    ToolCallRencana(
                        nama_tool="ambil_konteks_rag",
                        parameter={"daftar_entitas": state.get("kandidat_entitas", [])[:8]},
                        alasan="Konteks dasar dibutuhkan sebagai retrieval awal.",
                        prioritas=1,
                    )
                ],
                butuh_retrieval_tambahan=False,
                catatan_planner="Planner memasang retrieval dasar agar jalur tidak kosong.",
                confidence_reasoning="Retrieval awal difokuskan pada konteks laporan dan postingan.",
            )
        return {
            "putusan_planner": rencana.model_dump(),
            "jumlah_putaran_retrieval": state.get("jumlah_putaran_retrieval", 0) + 1,
        }

    def retrieval_mcp(self, state: StatusTIA) -> StatusTIA:
        rencana = RencanaRetrieval.model_validate(state["putusan_planner"])
        hasil_retrieval, tool_calls, kandidat_bukti_baru = jalankan_rencana_retrieval(
            self.mcp,
            state["trace_id"],
            rencana,
            entitas=[item["nilai"] for item in state.get("entitas", [])] or state.get("kandidat_entitas", []),
            hit_watchlist=state.get("hit_watchlist", []),
        )
        kandidat_bukti = list(state.get("kandidat_bukti", [])) + kandidat_bukti_baru
        semua_tool_calls = list(state.get("tool_calls_terpakai", [])) + [
            item.model_dump() for item in tool_calls
        ]
        return {
            "hasil_retrieval": self._gabungkan_konteks(state, hasil_retrieval),
            "konteks_bundle": self._gabungkan_konteks(state, hasil_retrieval),
            "tool_calls_terpakai": semua_tool_calls,
            "kandidat_bukti": kandidat_bukti,
        }

    def ekstraksi_entitas_putaran_1(self, state: StatusTIA) -> StatusTIA:
        event = OsintRawEvent.model_validate(state["event_raw"])
        entitas = self.layanan_openai.ekstrak_entitas(
            event.payload.judul,
            event.payload.isi,
            state.get("kandidat_entitas", []),
            {"items": state.get("kandidat_bukti", [])[:20]},
        )
        return {"entitas": [item.model_dump() for item in entitas]}

    def verifikasi_entitas(self, state: StatusTIA) -> StatusTIA:
        event = OsintRawEvent.model_validate(state["event_raw"])
        hasil = self.layanan_openai.verifikasi_entitas(
            event.payload.judul,
            event.payload.isi,
            state.get("entitas", []),
            {"items": state.get("kandidat_bukti", [])[:25]},
        )
        if not hasil.entitas_valid and state.get("jumlah_putaran_retrieval", 0) >= self.batas_putaran_retrieval:
            self._buat_dead_letter(
                state["trace_id"],
                "verifikasi_entitas",
                "Tidak ada entitas valid setelah batas retrieval tercapai.",
                {"entitas": state.get("entitas", []), "hasil_verifikasi": hasil.model_dump()},
            )
            return {"hasil_verifikasi_entitas": hasil.model_dump(), "stop": True, "alasan_stop": "entitas_tidak_valid"}
        return {
            "hasil_verifikasi_entitas": hasil.model_dump(),
            "entitas": [item.model_dump() for item in hasil.entitas_valid],
        }

    def watchlist_correlation(self, state: StatusTIA) -> StatusTIA:
        hasil: List[Dict[str, Any]] = []
        for entitas in state.get("entitas", []):
            kandidat = self.mcp.ambil_watchlist_profile(state["trace_id"], entitas["nilai"])
            for item in kandidat:
                hasil.append(
                    HitWatchlist(
                        id_profil=item["id_profil"],
                        nama_lengkap=item["nama_lengkap"],
                        skor_kecocokan=item["skor_kecocokan"],
                        alasan_kecocokan=item["alasan_kecocokan"],
                    ).model_dump()
                )
        hasil.sort(key=lambda item: item["skor_kecocokan"], reverse=True)
        hit_watchlist = hasil[:15]
        kandidat_bukti = list(state.get("kandidat_bukti", [])) + self._buat_bukti_watchlist(
            hit_watchlist, state.get("entitas", [])
        )
        return {"hit_watchlist": hit_watchlist, "kandidat_bukti": kandidat_bukti}

    def threat_assessment_awal(self, state: StatusTIA) -> StatusTIA:
        event = OsintRawEvent.model_validate(state["event_raw"])
        penilaian = self.layanan_openai.nilai_ancaman_awal(
            judul=event.payload.judul,
            isi=event.payload.isi,
            entitas=state.get("entitas", []),
            hit_watchlist=state.get("hit_watchlist", []),
            paket_bukti={"items": state.get("kandidat_bukti", [])[:30]},
        )
        return {"penilaian_awal": penilaian.model_dump()}

    def critic_threat_assessment(self, state: StatusTIA) -> StatusTIA:
        event = OsintRawEvent.model_validate(state["event_raw"])
        hasil = self.layanan_openai.kritik_ancaman(
            judul=event.payload.judul,
            penilaian_awal=state.get("penilaian_awal", {}),
            paket_bukti={"items": state.get("kandidat_bukti", [])[:30]},
        )
        kandidat_bukti = list(state.get("kandidat_bukti", [])) + self._buat_bukti_kritik(
            hasil, state.get("entitas", [])
        )
        jika_kritis_tapi_lemah = (
            len(hasil.kontradiksi_ditemukan) >= 3
            and len(hasil.celah_bukti) >= 2
            and not state.get("hit_watchlist")
            and state.get("jumlah_putaran_retrieval", 0) >= self.batas_putaran_retrieval
        )
        if jika_kritis_tapi_lemah:
            self._buat_dead_letter(
                state["trace_id"],
                "critic_threat_assessment",
                "Klaim ancaman tidak cukup kuat setelah kritik ancaman.",
                {"hasil_kritik": hasil.model_dump(), "penilaian_awal": state.get("penilaian_awal", {})},
            )
            return {
                "hasil_kritik_ancaman": hasil.model_dump(),
                "kandidat_bukti": kandidat_bukti,
                "stop": True,
                "alasan_stop": "kritik_ancaman_menolak_klaim",
            }
        return {"hasil_kritik_ancaman": hasil.model_dump(), "kandidat_bukti": kandidat_bukti}

    def penilaian_akhir(self, state: StatusTIA) -> StatusTIA:
        penilaian_akhir = self.layanan_openai.finalisasi_ancaman(
            penilaian_awal=state.get("penilaian_awal", {}),
            hasil_kritik=state.get("hasil_kritik_ancaman", {}),
            paket_bukti={"items": state.get("kandidat_bukti", [])[:35]},
        )
        hasil_kritik = HasilKritikAncaman.model_validate(state.get("hasil_kritik_ancaman", {}))
        skor_watchlist = min(len(state.get("hit_watchlist", [])) * 4, 20)
        skor_entitas = min(len(state.get("entitas", [])) * 2, 12)
        skor_relevansi = state.get("skor_relevansi", 0.0) * 25
        skor_confidence = penilaian_akhir.confidence * 0.15
        penalti_kontradiksi = min(len(hasil_kritik.kontradiksi_ditemukan) * 3, 12)
        bobot_level = {"RENDAH": 10, "SEDANG": 25, "TINGGI": 40, "KRITIS": 55}
        skor_agregat = min(
            100.0,
            max(
                0.0,
                bobot_level.get(penilaian_akhir.level_ancaman, 10)
                + skor_watchlist
                + skor_entitas
                + skor_relevansi
                + skor_confidence
                - penalti_kontradiksi,
            ),
        )
        return {
            "penilaian_ancaman": penilaian_akhir.model_dump(),
            "skor_agregat": round(skor_agregat, 2),
        }

    def rag_evidence_ranking(self, state: StatusTIA) -> StatusTIA:
        evidence_ranked = self.layanan_openai.ranking_bukti(
            kandidat_bukti=state.get("kandidat_bukti", []),
            entitas=state.get("entitas", []),
            hit_watchlist=state.get("hit_watchlist", []),
        )
        return {"evidence_ranked": evidence_ranked.model_dump()}

    def draft_briefing(self, state: StatusTIA) -> StatusTIA:
        event = OsintRawEvent.model_validate(state["event_raw"])
        briefing = self.layanan_openai.buat_briefing(
            judul=event.payload.judul,
            isi=event.payload.isi,
            skor_agregat=state["skor_agregat"],
            penilaian=state.get("penilaian_ancaman", {}),
            paket_bukti=state.get("evidence_ranked", {}),
            konteks=state.get("konteks_bundle", {}),
        )
        return {"briefing": briefing.model_dump()}

    def review_briefing(self, state: StatusTIA) -> StatusTIA:
        hasil = self.layanan_openai.review_briefing(
            briefing=state.get("briefing", {}),
            paket_bukti=state.get("evidence_ranked", {}),
            hasil_kritik=state.get("hasil_kritik_ancaman", {}),
        )
        return {"review_briefing": hasil.model_dump(), "status_review": hasil.status_review}

    def publish_tia(self, state: StatusTIA) -> StatusTIA:
        event = OsintRawEvent.model_validate(state["event_raw"])
        penilaian = PenilaianAncaman.model_validate(state["penilaian_ancaman"])
        hasil_kritik = HasilKritikAncaman.model_validate(state["hasil_kritik_ancaman"])
        hasil_verifikasi = HasilVerifikasiEntitas.model_validate(state["hasil_verifikasi_entitas"])
        evidence_ranked = PaketBukti.model_validate(state["evidence_ranked"])
        briefing = self.layanan_openai.buat_briefing(
            judul=event.payload.judul,
            isi=event.payload.isi,
            skor_agregat=state["skor_agregat"],
            penilaian=penilaian.model_dump(),
            paket_bukti=evidence_ranked.model_dump(),
            konteks=state.get("konteks_bundle", {}),
        )
        review_briefing = HasilReviewBriefing.model_validate(state["review_briefing"])

        jika_perlu_diturunkan = (
            review_briefing.status_review != "siap_hitl"
            and len(review_briefing.bukti_lemah) >= 2
            and penilaian.level_ancaman in {"KRITIS", "TINGGI"}
        )
        if jika_perlu_diturunkan:
            penilaian.level_ancaman = self._turunkan_level(penilaian.level_ancaman)
            penilaian.confidence = max(0.0, penilaian.confidence - 8.0)

        event_tia = TiaThreatEvent(
            metadata=MetadataEvent(
                trace_id=state["trace_id"],
                parent_event_id=event.metadata.event_id,
                source_type="NEWS",
                severity=penilaian.level_ancaman,
            ),
            payload=TiaThreatPayload(
                id_berita=event.payload.id_berita,
                skor_relevansi=state["skor_relevansi"],
                penilaian_ancaman=penilaian,
                skor_agregat=state["skor_agregat"],
                entitas=[EntitasTerekstrak.model_validate(item) for item in state.get("entitas", [])],
                hit_watchlist=[HitWatchlist.model_validate(item) for item in state.get("hit_watchlist", [])],
                konteks_ringkas=state.get("konteks_bundle", {}),
                putusan_planner=RencanaRetrieval.model_validate(state["putusan_planner"]),
                tool_calls_terpakai=[ToolCallRencana.model_validate(item) for item in state.get("tool_calls_terpakai", [])],
                hasil_verifikasi_entitas=hasil_verifikasi,
                hasil_kritik_ancaman=hasil_kritik,
                evidence_ranked=evidence_ranked,
                briefing=briefing,
                review_briefing=review_briefing,
                status_review=review_briefing.status_review,
            ),
        )

        self.mcp.simpan_briefing_tia(
            state["trace_id"],
            {
                "trace_id": state["trace_id"],
                "id_berita": event.payload.id_berita,
                "skor_agregat": state["skor_agregat"],
                "level_ancaman": event_tia.payload.penilaian_ancaman.level_ancaman,
                "briefing": event_tia.payload.briefing.model_dump(),
                "evidence_ranked": event_tia.payload.evidence_ranked.model_dump(),
                "hasil_kritik_ancaman": event_tia.payload.hasil_kritik_ancaman.model_dump(),
                "review_briefing": event_tia.payload.review_briefing.model_dump(),
            },
        )
        self.transport.terbitkan_redis_stream(
            self.pengaturan.aliran_tia_keluar,
            event_tia.model_dump(mode="json"),
        )

        hitl_event = bentuk_payload_hitl(
            trace_id=state["trace_id"],
            sumber_event=event_tia.payload.id_berita,
            level_risiko=event_tia.payload.penilaian_ancaman.level_ancaman,
            confidence_score=event_tia.payload.penilaian_ancaman.confidence,
            briefing_summary=event_tia.payload.briefing.ringkasan_eksekutif,
            recommended_action=event_tia.payload.briefing.rekomendasi_awal,
            evidence=[item.ringkasan for item in event_tia.payload.evidence_ranked.items[:6]],
            bukti_lemah=event_tia.payload.review_briefing.bukti_lemah,
            confidence_reasoning=event_tia.payload.briefing.confidence_reasoning,
        )
        route_review(self.pengaturan, self.transport, self.mcp, hitl_event)
        return {"briefing": briefing.model_dump(), "event_tia": event_tia.model_dump(mode="json")}

    def proses_event(self, event: dict) -> Dict[str, Any]:
        trace_id = event["metadata"]["trace_id"]
        hasil = self.graph.invoke({"event_raw": event, "trace_id": trace_id}, {"configurable": {"thread_id": trace_id}})
        return hasil

    def jalankan_konsumer(self) -> None:
        logger = logger_dengan_trace(__name__, "kafka-tia")
        konsumer = self.transport.buat_konsumer_kafka(
            self.pengaturan.topik_osint_raw,
            self.pengaturan.grup_konsumen_tia,
        )
        for pesan in konsumer:
            trace_id = "trace-tidak-diketahui"
            try:
                event = OsintRawEvent.model_validate(pesan.value)
                trace_id = event.metadata.trace_id
                self.proses_event(event.model_dump(mode="json"))
                try:
                    konsumer.commit()
                except Exception:
                    logger_dengan_trace(__name__, trace_id).exception("TIA gagal commit offset Kafka")
                logger_dengan_trace(__name__, trace_id).info("TIA selesai memproses event Kafka")
            except Exception as exc:
                logger_dengan_trace(__name__, trace_id).exception("TIA gagal memproses event Kafka")
                self.transport.terbitkan_dead_letter(
                    self.pengaturan.topik_osint_raw,
                    {
                        "trace_id": trace_id,
                        "tahap": "konsumer_tia",
                        "alasan": str(exc),
                        "payload": pesan.value,
                    },
                )
                try:
                    konsumer.commit()
                except Exception:
                    logger_dengan_trace(__name__, trace_id).exception("TIA gagal commit offset Kafka setelah error")
