from __future__ import annotations

from statistics import mean, pstdev
from typing import Any, Dict, List

import numpy as np
from celery import Celery
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

from orchestration.config import muat_pengaturan_runtime
from orchestration.hitl import bentuk_payload_hitl, route_review
from orchestration.logging_utils import logger_dengan_trace
from orchestration.mcp import McpGateway
from orchestration.openai_stack import LayananOpenAI
from orchestration.schema import (
    HasilKritikRekomendasi,
    InterpretasiKetidakpastian,
    MetadataEvent,
    NaaGraphEvent,
    PtaForecastEvent,
    PtaForecastPayload,
    RencanaRetrieval,
    ToolCallRencana,
)
from orchestration.tools import jalankan_rencana_retrieval
from orchestration.transport import TransportRuntime


pengaturan_runtime = muat_pengaturan_runtime()
aplikasi_celery = Celery(
    "pta_tasks",
    broker=pengaturan_runtime.broker_celery,
    backend=pengaturan_runtime.backend_hasil_celery,
)
aplikasi_celery.conf.task_serializer = "json"
aplikasi_celery.conf.result_serializer = "json"
aplikasi_celery.conf.accept_content = ["json"]


class MesinPTA:
    def __init__(self):
        self.pengaturan = pengaturan_runtime
        self.transport = TransportRuntime(self.pengaturan)
        self.mcp = McpGateway(self.pengaturan)
        self.layanan_openai = LayananOpenAI(self.pengaturan)

    def load_historical_scope(
        self,
        trace_id: str,
        profil_ids: List[str],
        alerts: List[str],
        interpretasi_cluster: List[dict[str, Any]],
    ) -> tuple[Dict[str, Any], RencanaRetrieval, List[ToolCallRencana]]:
        rencana = self.layanan_openai.rencanakan_scope_pta(
            profil_ids=profil_ids,
            alerts=alerts,
            interpretasi_cluster=interpretasi_cluster,
            retrieval_sebelumnya=[],
        )
        if not rencana.calls:
            rencana = RencanaRetrieval(
                tujuan="Ambil konteks historis utama untuk prediksi eskalasi.",
                calls=[
                    ToolCallRencana(
                        nama_tool="ambil_histori_entitas",
                        parameter={"id_profil_list": profil_ids},
                        alasan="Profil dan akun dasar diperlukan.",
                        prioritas=1,
                    ),
                    ToolCallRencana(
                        nama_tool="ambil_histori_lokasi",
                        parameter={"id_profil_list": profil_ids},
                        alasan="Pola spasial dibutuhkan untuk feature builder.",
                        prioritas=2,
                    ),
                    ToolCallRencana(
                        nama_tool="ambil_histori_transaksi",
                        parameter={"id_profil_list": profil_ids},
                        alasan="Pola transaksi dibutuhkan untuk anomali.",
                        prioritas=3,
                    ),
                    ToolCallRencana(
                        nama_tool="ambil_histori_kampanye",
                        parameter={"id_profil_list": profil_ids},
                        alasan="Riwayat kampanye dibutuhkan untuk korelasi relasional.",
                        prioritas=4,
                    ),
                    ToolCallRencana(
                        nama_tool="ambil_konteks_rag",
                        parameter={"daftar_entitas": profil_ids},
                        alasan="Laporan kasus dan skor risiko dibutuhkan untuk konteks prediksi.",
                        prioritas=5,
                    ),
                ],
                butuh_retrieval_tambahan=False,
                catatan_planner="PTA memakai retrieval dasar yang kaya untuk prediksi awal.",
                confidence_reasoning="Semua domain fitur dipenuhi oleh retrieval dasar.",
            )

        histori, tool_calls, _ = jalankan_rencana_retrieval(
            self.mcp,
            trace_id,
            rencana,
            entitas=profil_ids,
            hit_watchlist=[{"id_profil": item} for item in profil_ids],
        )

        hasil = {
            "profil": histori.get("ambil_histori_entitas", []),
            "lokasi": histori.get("ambil_histori_lokasi", []),
            "transaksi": histori.get("ambil_histori_transaksi", []),
            "kampanye": histori.get("ambil_histori_kampanye", []),
        }
        konteks_rag = histori.get("ambil_konteks_rag", {})
        hasil["laporan"] = konteks_rag.get("laporan", [])
        hasil["skor_risiko"] = konteks_rag.get("skor_risiko", [])
        hasil["postingan"] = konteks_rag.get("postingan", [])
        return hasil, rencana, tool_calls

    def build_feature_matrix(
        self,
        event_naa: NaaGraphEvent,
        histori: Dict[str, Any],
    ) -> tuple[list[list[float]], Dict[str, float], Dict[str, List[float]]]:
        jumlah_lokasi = len(histori.get("lokasi", []))
        jumlah_transaksi = len(histori.get("transaksi", []))
        jumlah_kampanye = len(histori.get("kampanye", []))
        jumlah_laporan = len(histori.get("laporan", []))
        jumlah_postingan = len(histori.get("postingan", []))
        jumlah_cluster = len(event_naa.payload.clusters)
        jumlah_node = len(event_naa.payload.nodes)
        jumlah_edge = len(event_naa.payload.edges)
        ukuran_cluster_terbesar = max([item["ukuran"] for item in event_naa.payload.clusters], default=0)

        rerata_pagerank = (
            mean(event_naa.payload.scores.get("pagerank", {}).values())
            if event_naa.payload.scores.get("pagerank")
            else 0.0
        )
        rerata_bridge = (
            mean(event_naa.payload.scores.get("bridge_score", {}).values())
            if event_naa.payload.scores.get("bridge_score")
            else 0.0
        )
        rerata_betweenness = (
            mean(event_naa.payload.scores.get("betweenness", {}).values())
            if event_naa.payload.scores.get("betweenness")
            else 0.0
        )

        nominal_transaksi = [float(item.get("jumlah_idr", 0.0) or 0.0) for item in histori.get("transaksi", [])]
        rerata_transaksi = mean(nominal_transaksi) if nominal_transaksi else 0.0
        deviasi_transaksi = pstdev(nominal_transaksi) if len(nominal_transaksi) > 1 else 0.0

        daftar_kota = [str(item.get("kota", "")) for item in histori.get("lokasi", []) if item.get("kota")]
        jumlah_kota_unik = len(set(daftar_kota))
        hotspot_density = round(jumlah_lokasi / max(jumlah_kota_unik, 1), 4)
        radius_overlap = round(len(event_naa.payload.geo_overlays) / max(jumlah_lokasi, 1), 4)

        fitur_per_domain = {
            "temporal": [
                float(jumlah_postingan),
                float(jumlah_laporan),
                float(jumlah_transaksi),
                float(jumlah_kampanye),
            ],
            "spasial": [
                float(jumlah_lokasi),
                float(jumlah_kota_unik),
                float(hotspot_density),
                float(radius_overlap),
            ],
            "relasional": [
                float(jumlah_cluster),
                float(ukuran_cluster_terbesar),
                float(jumlah_node),
                float(jumlah_edge),
                float(rerata_pagerank),
                float(rerata_bridge),
                float(rerata_betweenness),
            ],
            "transaksional": [
                float(rerata_transaksi),
                float(deviasi_transaksi),
            ],
        }

        ringkasan = {
            "jumlah_lokasi": float(jumlah_lokasi),
            "jumlah_transaksi": float(jumlah_transaksi),
            "jumlah_kampanye": float(jumlah_kampanye),
            "jumlah_laporan": float(jumlah_laporan),
            "jumlah_postingan": float(jumlah_postingan),
            "jumlah_cluster": float(jumlah_cluster),
            "ukuran_cluster_terbesar": float(ukuran_cluster_terbesar),
            "jumlah_node": float(jumlah_node),
            "jumlah_edge": float(jumlah_edge),
            "rerata_pagerank": float(rerata_pagerank),
            "rerata_bridge": float(rerata_bridge),
            "rerata_betweenness": float(rerata_betweenness),
            "jumlah_kota_unik": float(jumlah_kota_unik),
            "hotspot_density": float(hotspot_density),
            "radius_overlap": float(radius_overlap),
            "rerata_transaksi": float(rerata_transaksi),
            "deviasi_transaksi": float(deviasi_transaksi),
        }

        baris_utama = (
            fitur_per_domain["temporal"]
            + fitur_per_domain["spasial"]
            + fitur_per_domain["relasional"]
            + fitur_per_domain["transaksional"]
        )
        matriks = [baris_utama]

        for skor in histori.get("skor_risiko", [])[:10]:
            matriks.append(
                baris_utama[:-2]
                + [
                    float(skor.get("skor_risiko", 0.0)),
                    float(len((skor.get("isi_json") or {}).get("pendorong", [])) if isinstance(skor.get("isi_json"), dict) else 0),
                ]
            )
        if len(matriks) == 1:
            matriks.append([nilai * 0.97 for nilai in baris_utama])
        return matriks, ringkasan, fitur_per_domain

    def run_anomaly_models(self, matriks: List[List[float]]) -> Dict[str, float]:
        array_data = np.array(matriks, dtype=float)
        scaler = StandardScaler()
        scaled = scaler.fit_transform(array_data)

        iso = IsolationForest(random_state=42, contamination="auto")
        iso.fit(scaled)
        skor_iso = float(-iso.score_samples(scaled)[0])

        autoencoder = MLPRegressor(hidden_layer_sizes=(16, 8, 16), max_iter=700, random_state=42)
        autoencoder.fit(scaled, scaled)
        rekonstruksi = autoencoder.predict(scaled)
        galat = np.mean(np.square(scaled - rekonstruksi), axis=1)
        skor_autoencoder = float(galat[0])
        return {"isolation_forest": skor_iso, "autoencoder": skor_autoencoder}

    def compute_ensemble_score(self, skor_model: Dict[str, float]) -> float:
        skor = (skor_model["isolation_forest"] * 55) + (skor_model["autoencoder"] * 45)
        return max(0.0, min(100.0, skor * 100))

    def forecast_escalation(self, matriks: List[List[float]], histori: Dict[str, Any]) -> Dict[str, Any]:
        array_data = np.array(matriks, dtype=float)
        target_histori = [float(item.get("skor_risiko", 50.0)) for item in histori.get("skor_risiko", [])]
        if len(target_histori) < len(array_data):
            target_histori = (target_histori + [55.0] * len(array_data))[: len(array_data)]

        model = RandomForestRegressor(n_estimators=60, random_state=42)
        model.fit(array_data, np.array(target_histori, dtype=float))
        prediksi = float(model.predict(array_data[:1])[0])
        prediksi_per_pohon = [float(pohon.predict(array_data[:1])[0]) for pohon in model.estimators_]
        deviasi = pstdev(prediksi_per_pohon) if len(prediksi_per_pohon) > 1 else 0.0
        confidence = max(0.0, min(100.0, 100 - min(deviasi, 100)))

        probabilitas = max(0.0, min(100.0, prediksi))
        timeline_prediksi = [
            f"H+3: probabilitas eskalasi awal sekitar {round(probabilitas * 0.78, 2)}%",
            f"H+7: probabilitas eskalasi menengah sekitar {round(probabilitas * 0.92, 2)}%",
            f"H+14: probabilitas eskalasi utama sekitar {round(probabilitas, 2)}%",
        ]
        return {
            "prediksi": prediksi,
            "confidence": confidence,
            "deviasi": deviasi,
            "timeline_prediksi": timeline_prediksi,
        }

    def proses(self, event_naa: NaaGraphEvent) -> PtaForecastEvent:
        trace_id = event_naa.metadata.trace_id
        logger = logger_dengan_trace(__name__, trace_id)
        histori, rencana_scope, tool_calls_terpakai = self.load_historical_scope(
            trace_id,
            event_naa.payload.id_profil_terkait,
            event_naa.payload.alerts,
            [item.model_dump() for item in event_naa.payload.interpretasi_cluster],
        )
        matriks, ringkasan, fitur_per_domain = self.build_feature_matrix(event_naa, histori)
        skor_model = self.run_anomaly_models(matriks)
        skor_ensemble = self.compute_ensemble_score(skor_model)
        prediksi = self.forecast_escalation(matriks, histori)

        faktor_pendorong = []
        if ringkasan["jumlah_transaksi"] > 0:
            faktor_pendorong.append("aktivitas_transaksi")
        if ringkasan["jumlah_cluster"] > 1:
            faktor_pendorong.append("fragmentasi_klaster")
        if event_naa.payload.alerts:
            faktor_pendorong.extend(event_naa.payload.alerts)
        if ringkasan["rerata_bridge"] >= 0.1:
            faktor_pendorong.append("node_jembatan_aktif")
        if ringkasan["hotspot_density"] >= 1.5:
            faktor_pendorong.append("hotspot_spasial")

        counter_signals = []
        if ringkasan["jumlah_laporan"] == 0:
            counter_signals.append("histori_laporan_tipis")
        if ringkasan["deviasi_transaksi"] < 100000:
            counter_signals.append("volatilitas_transaksi_rendah")
        if not event_naa.payload.alerts:
            counter_signals.append("tidak_ada_alert_struktural")

        interpretasi_ketidakpastian = self.layanan_openai.interpretasi_ketidakpastian(
            ringkasan_fitur=ringkasan,
            prediksi=prediksi,
            faktor_pendorong=faktor_pendorong,
            counter_signals=counter_signals,
        )
        rekomendasi = self.layanan_openai.buat_rekomendasi_pta(
            ringkasan_fitur=ringkasan,
            interpretasi=interpretasi_ketidakpastian.model_dump(),
            faktor_pendorong=faktor_pendorong,
        )
        hasil_kritik = self.layanan_openai.kritik_rekomendasi(
            rekomendasi=rekomendasi.model_dump(),
            ringkasan_fitur=ringkasan,
            interpretasi=interpretasi_ketidakpastian.model_dump(),
        )

        level_risiko = (
            "KRITIS"
            if skor_ensemble >= self.pengaturan.ambang_kritis
            else "TINGGI"
            if skor_ensemble >= self.pengaturan.ambang_tinggi
            else "SEDANG"
        )
        if not hasil_kritik.rekomendasi_selaras and level_risiko == "KRITIS":
            level_risiko = "TINGGI"

        event_pta = PtaForecastEvent(
            metadata=MetadataEvent(
                trace_id=trace_id,
                parent_event_id=event_naa.metadata.event_id,
                source_type="NETWORK",
                severity=level_risiko,
            ),
            payload=PtaForecastPayload(
                entitas_target=event_naa.payload.id_profil_terkait,
                skor_anomali=max(skor_model.values()) * 100,
                skor_ensemble=skor_ensemble,
                probabilitas_eskalasi=max(0.0, min(1.0, prediksi["prediksi"] / 100.0)),
                confidence_score=interpretasi_ketidakpastian.confidence_score,
                confidence_band=interpretasi_ketidakpastian.confidence_band,
                faktor_pendorong=faktor_pendorong,
                driver_features=interpretasi_ketidakpastian.driver_features,
                counter_signals=interpretasi_ketidakpastian.counter_signals,
                timeline_prediksi=rekomendasi.timeline_prediksi or prediksi["timeline_prediksi"],
                interpretasi_ketidakpastian=InterpretasiKetidakpastian.model_validate(
                    interpretasi_ketidakpastian.model_dump()
                ),
                hasil_kritik_rekomendasi=HasilKritikRekomendasi.model_validate(hasil_kritik.model_dump()),
                rekomendasi_aksi=rekomendasi,
                fitur_ringkas=ringkasan,
            ),
        )

        self.transport.terbitkan_redis_stream(
            self.pengaturan.aliran_pta_hasil,
            event_pta.model_dump(mode="json"),
        )
        self.mcp.simpan_hasil_pta(
            trace_id,
            {
                "trace_id": trace_id,
                "putusan_scope": rencana_scope.model_dump(),
                "tool_calls_terpakai": [item.model_dump() for item in tool_calls_terpakai],
                "fitur_per_domain": fitur_per_domain,
                "skor_model": skor_model,
                "skor_ensemble": skor_ensemble,
                "probabilitas_eskalasi": prediksi["prediksi"],
                "confidence_score": interpretasi_ketidakpastian.confidence_score,
                "confidence_reasoning": interpretasi_ketidakpastian.confidence_reasoning,
                "faktor_pendorong": faktor_pendorong,
                "counter_signals": interpretasi_ketidakpastian.counter_signals,
                "hasil_kritik_rekomendasi": hasil_kritik.model_dump(),
                "rekomendasi_aksi": rekomendasi.model_dump(),
                "fitur_ringkas": ringkasan,
            },
        )

        hitl_event = bentuk_payload_hitl(
            trace_id=trace_id,
            sumber_event=event_naa.payload.id_berita,
            level_risiko=level_risiko,
            confidence_score=interpretasi_ketidakpastian.confidence_score,
            briefing_summary=rekomendasi.ringkasan_aksi,
            recommended_action=rekomendasi.rekomendasi_tindak_lanjut,
            evidence=rekomendasi.evidence_pointers,
            bukti_lemah=hasil_kritik.kontra_indikasi,
            confidence_reasoning=interpretasi_ketidakpastian.confidence_reasoning,
        )
        route_review(self.pengaturan, self.transport, self.mcp, hitl_event)
        logger.info(
            "PTA selesai",
            extra={
                "extra_payload": {
                    "skor_ensemble": skor_ensemble,
                    "probabilitas_eskalasi": prediksi["prediksi"],
                    "confidence_score": interpretasi_ketidakpastian.confidence_score,
                }
            },
        )
        return event_pta


@aplikasi_celery.task(name="pta.analisis_tertunda")
def analisis_pta_tertunda(payload_event_naa: Dict[str, Any]) -> Dict[str, Any]:
    mesin = MesinPTA()
    if isinstance(payload_event_naa, str):
        event = NaaGraphEvent.model_validate_json(payload_event_naa)
    else:
        event = NaaGraphEvent.model_validate(payload_event_naa)
    hasil = mesin.proses(event)
    return hasil.model_dump(mode="json")
