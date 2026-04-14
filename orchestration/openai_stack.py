from __future__ import annotations

from typing import Any, List, Type

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from openai import OpenAI
from pydantic import BaseModel

from orchestration.config import PengaturanRuntime
from orchestration.prompt_registry import ambil_prompt
from orchestration.schema import (
    DossierSindikat,
    DaftarEntitas,
    DaftarRelasi,
    EntitasTerekstrak,
    HasilKritikAncaman,
    HasilKritikRekomendasi,
    HasilReviewBriefing,
    HasilVerifikasiEntitas,
    HasilVerifikasiRelasi,
    InterpretasiCluster,
    InterpretasiKetidakpastian,
    PaketBukti,
    PenilaianAncaman,
    RekomendasiAksi,
    RelasiSPO,
    RencanaRetrieval,
    RingkasanIntelijen,
)


class DaftarInterpretasiCluster(BaseModel):
    items: List[InterpretasiCluster]


class LayananOpenAI:
    """Lapisan terpadu untuk klien OpenAI langsung dan runnable LangChain terstruktur."""

    def __init__(self, pengaturan: PengaturanRuntime):
        self.pengaturan = pengaturan
        self.klien = OpenAI(
            api_key=pengaturan.kunci_openai,
            timeout=pengaturan.timeout_openai,
            max_retries=pengaturan.maksimal_retry_openai,
        )
        self.model_chat = self._buat_model_chat()

    def _buat_model_chat(self, timeout_detik: int | None = None) -> ChatOpenAI:
        return ChatOpenAI(
            api_key=self.pengaturan.kunci_openai,
            model=self.pengaturan.model_openai,
            timeout=timeout_detik or self.pengaturan.timeout_openai,
            max_retries=self.pengaturan.maksimal_retry_openai,
            temperature=0.2,
        )

    def _jalankan_terstruktur(
        self,
        nama_prompt: str,
        model_output: Type[BaseModel],
        payload: dict[str, Any],
        timeout_detik: int | None = None,
    ) -> BaseModel:
        template = ambil_prompt(nama_prompt)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", template["system"]),
                ("human", template["human"]),
            ]
        )
        model_chat = self.model_chat if timeout_detik is None else self._buat_model_chat(timeout_detik)
        chain = prompt | model_chat.with_structured_output(
            model_output,
            method="function_calling",
        )
        return chain.invoke(payload)

    def _potong_teks(self, nilai: Any, batas: int = 240) -> str:
        teks = "" if nilai is None else str(nilai)
        if len(teks) <= batas:
            return teks
        return f"{teks[: batas - 3].rstrip()}..."

    def _pilih_field_terisi(self, sumber: dict[str, Any], field: list[str]) -> dict[str, Any]:
        return {
            nama_field: sumber[nama_field]
            for nama_field in field
            if nama_field in sumber and sumber[nama_field] not in (None, "", [], {})
        }

    def _ringkas_profil_kasus(self, item: dict[str, Any]) -> dict[str, Any]:
        isi_json = item.get("isi_json") or {}
        profil_terekstrak = isi_json.get("profil_terekstrak") or {}
        akun = profil_terekstrak.get("akun") or []
        hasil = self._pilih_field_terisi(
            item,
            ["id_profil", "nama_lengkap", "nama_tampil", "kota", "provinsi", "latitude", "longitude"],
        )
        if item.get("bio") or isi_json.get("bio"):
            hasil["bio"] = self._potong_teks(item.get("bio") or isi_json.get("bio"), 180)
        if profil_terekstrak.get("sinopsis") or isi_json.get("sinopsis"):
            hasil["sinopsis"] = self._potong_teks(
                profil_terekstrak.get("sinopsis") or isi_json.get("sinopsis"),
                180,
            )
        if isi_json.get("tag_risiko"):
            hasil["tag_risiko"] = isi_json["tag_risiko"][:6]
        if isi_json.get("id_klaster"):
            hasil["id_klaster"] = isi_json["id_klaster"][:3]
        if isi_json.get("tautan_kasus"):
            hasil["tautan_kasus"] = isi_json["tautan_kasus"][:3]
        if profil_terekstrak.get("statistik") or isi_json.get("statistik"):
            hasil["statistik"] = profil_terekstrak.get("statistik") or isi_json.get("statistik")
        if akun:
            hasil["akun_utama"] = [
                f"{akun_item.get('platform', 'platform')}:{akun_item.get('username', '-')}"
                for akun_item in akun[:4]
            ]
        return hasil

    def _skor_prioritas_postingan(self, item: dict[str, Any]) -> tuple[int, str]:
        sumber = item.get("isi_json") or item
        skor = 0
        if sumber.get("tipe_sumber") and sumber.get("tipe_sumber") != "organik":
            skor += 3
        if sumber.get("referensi_skenario"):
            skor += 2
        if sumber.get("referensi_mention"):
            skor += 2
        if sumber.get("kata_kunci"):
            skor += 1
        return skor, str(sumber.get("timestamp") or item.get("timestamp") or "")

    def _ringkas_payload_analisis_kasus(
        self,
        kasus: dict[str, Any],
        laporan: list[dict[str, Any]],
        skor_risiko: list[dict[str, Any]],
        transaksi: list[dict[str, Any]],
        kampanye: list[dict[str, Any]],
        profil: list[dict[str, Any]],
        lokasi: list[dict[str, Any]],
        postingan: list[dict[str, Any]],
        graf: dict[str, Any],
    ) -> dict[str, Any]:
        postingan_terpilih = sorted(postingan, key=self._skor_prioritas_postingan, reverse=True)[:30]
        lokasi_terpilih = sorted(
            lokasi,
            key=lambda item: (
                1 if item.get("id_kasus") else 0,
                1 if item.get("id_titik_pertemuan") else 0,
                str(item.get("diamati_pada") or ""),
            ),
            reverse=True,
        )[:20]
        return {
            "kasus": kasus,
            "laporan": laporan[:10],
            "skor_risiko": skor_risiko[:10],
            "transaksi": [
                self._pilih_field_terisi(
                    item,
                    [
                        "id_transaksi",
                        "id_profil_sumber",
                        "id_profil_tujuan",
                        "nama_sumber",
                        "nama_tujuan",
                        "jumlah_idr",
                        "kanal",
                        "timestamp",
                    ],
                )
                for item in transaksi[:30]
            ],
            "kampanye": [
                {
                    **self._pilih_field_terisi(
                        item,
                        ["id_kampanye", "id_profil_pusat", "nama_profil_pusat", "platform", "mulai_pada", "selesai_pada"],
                    ),
                    **(
                        {"narasi": self._potong_teks(item.get("narasi"), 220)}
                        if item.get("narasi")
                        else {}
                    ),
                }
                for item in kampanye[:20]
            ],
            "profil": [self._ringkas_profil_kasus(item) for item in profil[:20]],
            "lokasi": [
                self._pilih_field_terisi(
                    item,
                    [
                        "id_profil",
                        "id_kasus",
                        "id_titik_pertemuan",
                        "label",
                        "tipe_lokasi",
                        "kota",
                        "provinsi",
                        "diamati_pada",
                        "kepercayaan",
                    ],
                )
                for item in lokasi_terpilih
            ],
            "postingan": [
                {
                    **self._pilih_field_terisi(
                        item.get("isi_json") or item,
                        [
                            "id_posting",
                            "id_profil",
                            "platform",
                            "timestamp",
                            "tipe_sumber",
                            "tipe_konten",
                            "kota",
                            "provinsi",
                            "kata_kunci",
                            "referensi_mention",
                            "referensi_skenario",
                            "engagement",
                        ],
                    ),
                    **(
                        {"konten": self._potong_teks((item.get("isi_json") or item).get("konten"), 220)}
                        if (item.get("isi_json") or item).get("konten")
                        else {}
                    ),
                }
                for item in postingan_terpilih
            ],
            "graf": {
                "nodes": [
                    self._pilih_field_terisi(item, ["id_profil", "nama", "labels"])
                    for item in (graf.get("nodes") or [])[:20]
                ],
                "edges": [
                    self._pilih_field_terisi(
                        item,
                        ["sumber_id", "sumber", "target_id", "target", "jenis_relasi", "jumlah_idr", "kanal"],
                    )
                    for item in (graf.get("edges") or [])[:40]
                ],
            },
        }

    def rencanakan_retrieval_tia(
        self,
        judul: str,
        isi: str,
        sinyal_awal: dict[str, Any],
        entitas_kandidat: List[str],
        retrieval_sebelumnya: List[dict[str, Any]],
    ) -> RencanaRetrieval:
        return self._jalankan_terstruktur(
            "planner_retrieval_tia",
            RencanaRetrieval,
            {
                "judul": judul,
                "isi": isi[:7000],
                "sinyal_awal": sinyal_awal,
                "entitas_kandidat": entitas_kandidat,
                "retrieval_sebelumnya": retrieval_sebelumnya,
            },
        )

    def ekstrak_entitas(
        self,
        judul: str,
        isi: str,
        kandidat_awal: List[str],
        paket_bukti: dict[str, Any],
    ) -> List[EntitasTerekstrak]:
        hasil = self._jalankan_terstruktur(
            "ekstraksi_entitas",
            DaftarEntitas,
            {
                "judul": judul,
                "isi": isi[:7000],
                "kandidat_awal": ", ".join(kandidat_awal[:30]),
                "paket_bukti": paket_bukti,
            },
        )
        return hasil.items

    def verifikasi_entitas(
        self,
        judul: str,
        isi: str,
        entitas: List[dict[str, Any]],
        paket_bukti: dict[str, Any],
    ) -> HasilVerifikasiEntitas:
        return self._jalankan_terstruktur(
            "verifikasi_entitas",
            HasilVerifikasiEntitas,
            {
                "judul": judul,
                "isi": isi[:7000],
                "entitas": entitas,
                "paket_bukti": paket_bukti,
            },
        )

    def nilai_ancaman_awal(
        self,
        judul: str,
        isi: str,
        entitas: List[dict[str, Any]],
        hit_watchlist: List[dict[str, Any]],
        paket_bukti: dict[str, Any],
    ) -> PenilaianAncaman:
        return self._jalankan_terstruktur(
            "penilaian_ancaman_awal",
            PenilaianAncaman,
            {
                "judul": judul,
                "isi": isi[:7000],
                "entitas": entitas,
                "hit_watchlist": hit_watchlist,
                "paket_bukti": paket_bukti,
            },
        )

    def kritik_ancaman(
        self,
        judul: str,
        penilaian_awal: dict[str, Any],
        paket_bukti: dict[str, Any],
    ) -> HasilKritikAncaman:
        return self._jalankan_terstruktur(
            "kritik_ancaman",
            HasilKritikAncaman,
            {
                "judul": judul,
                "penilaian_awal": penilaian_awal,
                "paket_bukti": paket_bukti,
            },
        )

    def finalisasi_ancaman(
        self,
        penilaian_awal: dict[str, Any],
        hasil_kritik: dict[str, Any],
        paket_bukti: dict[str, Any],
    ) -> PenilaianAncaman:
        return self._jalankan_terstruktur(
            "penilaian_ancaman_akhir",
            PenilaianAncaman,
            {
                "penilaian_awal": penilaian_awal,
                "hasil_kritik": hasil_kritik,
                "paket_bukti": paket_bukti,
            },
        )

    def ranking_bukti(
        self,
        kandidat_bukti: List[dict[str, Any]],
        entitas: List[dict[str, Any]],
        hit_watchlist: List[dict[str, Any]],
    ) -> PaketBukti:
        return self._jalankan_terstruktur(
            "ranking_bukti",
            PaketBukti,
            {
                "kandidat_bukti": kandidat_bukti,
                "entitas": entitas,
                "hit_watchlist": hit_watchlist,
            },
        )

    def buat_briefing(
        self,
        judul: str,
        isi: str,
        skor_agregat: float,
        penilaian: dict[str, Any],
        paket_bukti: dict[str, Any],
        konteks: dict[str, Any],
    ) -> RingkasanIntelijen:
        return self._jalankan_terstruktur(
            "briefing_tia",
            RingkasanIntelijen,
            {
                "judul": judul,
                "isi": isi[:7000],
                "skor_agregat": skor_agregat,
                "penilaian": penilaian,
                "paket_bukti": paket_bukti,
                "konteks": konteks,
            },
        )

    def review_briefing(
        self,
        briefing: dict[str, Any],
        paket_bukti: dict[str, Any],
        hasil_kritik: dict[str, Any],
    ) -> HasilReviewBriefing:
        return self._jalankan_terstruktur(
            "review_briefing",
            HasilReviewBriefing,
            {
                "briefing": briefing,
                "paket_bukti": paket_bukti,
                "hasil_kritik": hasil_kritik,
            },
        )

    def ekstrak_relasi_kandidat(
        self,
        ringkasan: str,
        entitas: List[dict[str, Any]],
        paket_bukti: dict[str, Any],
    ) -> List[RelasiSPO]:
        hasil = self._jalankan_terstruktur(
            "relasi_kandidat",
            DaftarRelasi,
            {
                "ringkasan": ringkasan,
                "entitas": entitas,
                "paket_bukti": paket_bukti,
            },
        )
        return hasil.items

    def verifikasi_relasi(
        self,
        relasi: List[dict[str, Any]],
        ringkasan: str,
        konteks: dict[str, Any],
    ) -> HasilVerifikasiRelasi:
        return self._jalankan_terstruktur(
            "verifikasi_relasi",
            HasilVerifikasiRelasi,
            {
                "relasi": relasi,
                "ringkasan": ringkasan,
                "konteks": konteks,
            },
        )

    def interpretasi_cluster(
        self,
        clusters: List[dict[str, Any]],
        scores: dict[str, Any],
        alerts: List[str],
        nodes: List[dict[str, Any]],
    ) -> List[InterpretasiCluster]:
        hasil = self._jalankan_terstruktur(
            "interpretasi_cluster",
            DaftarInterpretasiCluster,
            {
                "clusters": clusters,
                "scores": scores,
                "alerts": alerts,
                "nodes": nodes,
            },
        )
        return hasil.items

    def rencanakan_scope_pta(
        self,
        profil_ids: List[str],
        alerts: List[str],
        interpretasi_cluster: List[dict[str, Any]],
        retrieval_sebelumnya: List[dict[str, Any]],
    ) -> RencanaRetrieval:
        return self._jalankan_terstruktur(
            "planner_scope_pta",
            RencanaRetrieval,
            {
                "profil_ids": profil_ids,
                "alerts": alerts,
                "interpretasi_cluster": interpretasi_cluster,
                "retrieval_sebelumnya": retrieval_sebelumnya,
            },
        )

    def interpretasi_ketidakpastian(
        self,
        ringkasan_fitur: dict[str, Any],
        prediksi: dict[str, Any],
        faktor_pendorong: List[str],
        counter_signals: List[str],
    ) -> InterpretasiKetidakpastian:
        return self._jalankan_terstruktur(
            "interpretasi_ketidakpastian",
            InterpretasiKetidakpastian,
            {
                "ringkasan_fitur": ringkasan_fitur,
                "prediksi": prediksi,
                "faktor_pendorong": faktor_pendorong,
                "counter_signals": counter_signals,
            },
        )

    def buat_rekomendasi_pta(
        self,
        ringkasan_fitur: dict[str, Any],
        interpretasi: dict[str, Any],
        faktor_pendorong: List[str],
    ) -> RekomendasiAksi:
        return self._jalankan_terstruktur(
            "rekomendasi_pta",
            RekomendasiAksi,
            {
                "ringkasan_fitur": ringkasan_fitur,
                "interpretasi": interpretasi,
                "faktor_pendorong": faktor_pendorong,
            },
        )

    def kritik_rekomendasi(
        self,
        rekomendasi: dict[str, Any],
        ringkasan_fitur: dict[str, Any],
        interpretasi: dict[str, Any],
    ) -> HasilKritikRekomendasi:
        return self._jalankan_terstruktur(
            "kritik_rekomendasi",
            HasilKritikRekomendasi,
            {
                "rekomendasi": rekomendasi,
                "ringkasan_fitur": ringkasan_fitur,
                "interpretasi": interpretasi,
            },
        )

    def analisis_kasus_sindikat(
        self,
        kasus: dict[str, Any],
        laporan: list[dict[str, Any]],
        skor_risiko: list[dict[str, Any]],
        transaksi: list[dict[str, Any]],
        kampanye: list[dict[str, Any]],
        profil: list[dict[str, Any]],
        lokasi: list[dict[str, Any]],
        postingan: list[dict[str, Any]],
        graf: dict[str, Any],
    ) -> DossierSindikat:
        payload = self._ringkas_payload_analisis_kasus(
            kasus=kasus,
            laporan=laporan,
            skor_risiko=skor_risiko,
            transaksi=transaksi,
            kampanye=kampanye,
            profil=profil,
            lokasi=lokasi,
            postingan=postingan,
            graf=graf,
        )
        return self._jalankan_terstruktur(
            "analisis_kasus_sindikat",
            DossierSindikat,
            payload,
            timeout_detik=max(self.pengaturan.timeout_openai, 180),
        )
