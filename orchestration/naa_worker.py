from __future__ import annotations

import json
from typing import Any, Dict, List

import networkx as nx
from networkx.algorithms.community import louvain_communities

from orchestration.config import PengaturanRuntime
from orchestration.logging_utils import logger_dengan_trace
from orchestration.mcp import McpGateway
from orchestration.openai_stack import LayananOpenAI
from orchestration.schema import (
    HasilVerifikasiRelasi,
    InterpretasiCluster,
    MetadataEvent,
    NaaClusterAlertEvent,
    NaaGraphEvent,
    NaaGraphPayload,
    RelasiSPO,
    TiaThreatEvent,
)
from orchestration.transport import TransportRuntime


class PekerjaNAA:
    nama_grup = "naa_group"

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
        self.transport.pastikan_grup_stream(pengaturan.aliran_tia_keluar, self.nama_grup)

    def _hitung_influence_scores(self, graf: nx.Graph) -> Dict[str, Dict[str, float]]:
        if graf.number_of_nodes() == 0:
            return {"pagerank": {}, "betweenness": {}, "eigenvector": {}, "bridge_score": {}}

        try:
            pagerank = nx.pagerank(graf)
        except Exception:
            pagerank = {}
        try:
            betweenness = nx.betweenness_centrality(graf)
        except Exception:
            betweenness = {}
        try:
            eigenvector = nx.eigenvector_centrality(graf, max_iter=300)
        except Exception:
            eigenvector = {}

        bridge_score = {}
        for node in graf.nodes:
            tetangga = list(graf.neighbors(node))
            bridge_score[node] = round(len(set(tetangga)) / max(graf.number_of_nodes(), 1), 6)
        return {
            "pagerank": pagerank,
            "betweenness": betweenness,
            "eigenvector": eigenvector,
            "bridge_score": bridge_score,
        }

    def _hitung_clusters(self, graf: nx.Graph) -> List[Dict[str, Any]]:
        if graf.number_of_nodes() == 0:
            return []
        komunitas = louvain_communities(graf, seed=42)
        hasil = []
        for indeks, komunitas_item in enumerate(komunitas, start=1):
            hasil.append(
                {
                    "cluster_id": f"cluster-{indeks}",
                    "anggota": sorted(list(komunitas_item)),
                    "ukuran": len(komunitas_item),
                }
            )
        return hasil

    def _deteksi_anomali_struktur(
        self,
        graf: nx.Graph,
        scores: Dict[str, Dict[str, float]],
        clusters: List[Dict[str, Any]],
    ) -> List[str]:
        alerts: List[str] = []
        if graf.number_of_nodes() == 0:
            return alerts
        densitas = nx.density(graf)
        if densitas >= 0.35:
            alerts.append("kepadatan_relasi_meningkat")
        cluster_besar = [item for item in clusters if item["ukuran"] >= 5]
        if cluster_besar:
            alerts.append("cluster_baru_berukuran_signifikan")
        bridge_kuat = [nilai for nilai in scores.get("bridge_score", {}).values() if nilai >= 0.15]
        if bridge_kuat:
            alerts.append("node_jembatan_mencolok")
        return alerts

    def _peta_cluster(self, clusters: List[Dict[str, Any]]) -> Dict[str, str]:
        pemetaan = {}
        for item in clusters:
            for anggota in item["anggota"]:
                pemetaan[anggota] = item["cluster_id"]
        return pemetaan

    def _peta_interpretasi(self, interpretasi_cluster: List[InterpretasiCluster]) -> Dict[str, InterpretasiCluster]:
        return {item.cluster_id: item for item in interpretasi_cluster}

    def _tentukan_peran_node(
        self,
        node: str,
        scores: Dict[str, Dict[str, float]],
        cluster_id: str | None,
        peta_interpretasi: Dict[str, InterpretasiCluster],
    ) -> str:
        jika_bridge = scores.get("bridge_score", {}).get(node, 0.0) >= 0.15
        jika_leader = scores.get("pagerank", {}).get(node, 0.0) >= 0.1
        jika_penghubung = scores.get("betweenness", {}).get(node, 0.0) >= 0.08
        if jika_bridge or jika_penghubung:
            return "broker"
        if jika_leader:
            return "leader"
        if cluster_id and node in peta_interpretasi.get(cluster_id, InterpretasiCluster(cluster_id="", alasan_penting="")).entitas_kunci:
            return "aktor_kunci"
        return "anggota"

    def _serialisasi_graf(
        self,
        graf: nx.Graph,
        scores: Dict[str, Dict[str, float]],
        clusters: List[Dict[str, Any]],
        interpretasi_cluster: List[InterpretasiCluster],
    ) -> Dict[str, Any]:
        pemetaan_cluster = self._peta_cluster(clusters)
        peta_interpretasi = self._peta_interpretasi(interpretasi_cluster)

        nodes = []
        for node in graf.nodes:
            cluster_id = pemetaan_cluster.get(node)
            role = self._tentukan_peran_node(node, scores, cluster_id, peta_interpretasi)
            broker_flag = role == "broker"
            nodes.append(
                {
                    "id": node,
                    "label": node,
                    "cluster_id": cluster_id,
                    "pagerank": scores.get("pagerank", {}).get(node, 0.0),
                    "betweenness": scores.get("betweenness", {}).get(node, 0.0),
                    "eigenvector": scores.get("eigenvector", {}).get(node, 0.0),
                    "bridge_score": scores.get("bridge_score", {}).get(node, 0.0),
                    "peran_node": role,
                    "broker_flag": broker_flag,
                    "alasan_cluster": peta_interpretasi.get(cluster_id).alasan_penting if cluster_id in peta_interpretasi else "",
                }
            )

        edges = []
        for sumber, tujuan, atribut in graf.edges(data=True):
            edges.append(
                {
                    "source": sumber,
                    "target": tujuan,
                    "label": atribut.get("relasi", "TERKAIT"),
                    "confidence": atribut.get("confidence", 0.0),
                    "evidence_summary": atribut.get("evidence_text", ""),
                }
            )
        return {"nodes": nodes, "edges": edges}

    def _geo_overlays(self, trace_id: str, profil_ids: List[str]) -> List[Dict[str, Any]]:
        hasil: List[Dict[str, Any]] = []
        for id_profil in profil_ids:
            hasil.extend(self.mcp.ambil_histori_lokasi(trace_id, id_profil)[:10])
        return hasil

    def _ringkas_bukti_tia(self, event_tia: TiaThreatEvent) -> List[str]:
        return [item.ringkasan for item in event_tia.payload.evidence_ranked.items[:8]]

    def proses_event(self, event_tia: TiaThreatEvent) -> NaaGraphEvent:
        trace_id = event_tia.metadata.trace_id
        logger = logger_dengan_trace(__name__, trace_id)
        ringkasan_relasi = event_tia.payload.briefing.ringkasan_eksekutif + "\n" + "\n".join(
            event_tia.payload.briefing.kronologi
        )

        relasi_kandidat = self.layanan_openai.ekstrak_relasi_kandidat(
            ringkasan=ringkasan_relasi,
            entitas=[item.model_dump() for item in event_tia.payload.entitas],
            paket_bukti=event_tia.payload.evidence_ranked.model_dump(),
        )
        hasil_verifikasi_relasi = self.layanan_openai.verifikasi_relasi(
            relasi=[item.model_dump() for item in relasi_kandidat],
            ringkasan=ringkasan_relasi,
            konteks={
                "penilaian_ancaman": event_tia.payload.penilaian_ancaman.model_dump(),
                "hasil_kritik_ancaman": event_tia.payload.hasil_kritik_ancaman.model_dump(),
                "status_review": event_tia.payload.status_review,
            },
        )
        relasi_valid = [item.model_dump() for item in hasil_verifikasi_relasi.relasi_valid]
        if not relasi_valid:
            self.transport.terbitkan_dead_letter(
                self.pengaturan.aliran_naa_keluar,
                {
                    "trace_id": trace_id,
                    "tahap": "verifikasi_relasi",
                    "alasan": "Tidak ada relasi valid yang lolos verifikasi.",
                    "payload": hasil_verifikasi_relasi.model_dump(mode="json"),
                },
            )

        self.mcp.upsert_relasi_graf(trace_id, relasi_valid)
        nama_entitas = [item.nilai for item in event_tia.payload.entitas]
        graf = self.mcp.ambil_subgraf_entitas(trace_id, nama_entitas)
        scores = self._hitung_influence_scores(graf)
        clusters = self._hitung_clusters(graf)
        alerts = self._deteksi_anomali_struktur(graf, scores, clusters)
        graf_json_sementara = self._serialisasi_graf(graf, scores, clusters, [])
        interpretasi_cluster = self.layanan_openai.interpretasi_cluster(
            clusters=clusters,
            scores=scores,
            alerts=alerts,
            nodes=graf_json_sementara["nodes"],
        )
        graf_json = self._serialisasi_graf(graf, scores, clusters, interpretasi_cluster)
        profil_ids = [item.id_profil for item in event_tia.payload.hit_watchlist]
        geo_overlays = self._geo_overlays(trace_id, profil_ids)

        event_naa = NaaGraphEvent(
            metadata=MetadataEvent(
                trace_id=trace_id,
                parent_event_id=event_tia.metadata.event_id,
                source_type="NETWORK",
                severity=event_tia.payload.penilaian_ancaman.level_ancaman,
            ),
            payload=NaaGraphPayload(
                id_berita=event_tia.payload.id_berita,
                id_profil_terkait=profil_ids,
                relasi=[RelasiSPO.model_validate(item) for item in relasi_valid],
                hasil_verifikasi_relasi=HasilVerifikasiRelasi.model_validate(
                    hasil_verifikasi_relasi.model_dump()
                ),
                clusters=clusters,
                interpretasi_cluster=interpretasi_cluster,
                scores=scores,
                geo_overlays=geo_overlays,
                alerts=alerts,
                evidence_summary=self._ringkas_bukti_tia(event_tia),
                nodes=graf_json["nodes"],
                edges=graf_json["edges"],
            ),
        )

        self.transport.terbitkan_redis_stream(
            self.pengaturan.aliran_naa_keluar,
            event_naa.model_dump(mode="json"),
        )
        if alerts:
            alert_event = NaaClusterAlertEvent(
                metadata=MetadataEvent(
                    trace_id=trace_id,
                    parent_event_id=event_naa.metadata.event_id,
                    source_type="NETWORK",
                    severity=event_tia.payload.penilaian_ancaman.level_ancaman,
                ),
                payload={
                    "id_berita": event_tia.payload.id_berita,
                    "alerts": alerts,
                    "clusters": clusters,
                    "interpretasi_cluster": [item.model_dump() for item in interpretasi_cluster],
                },
            )
            self.transport.terbitkan_redis_stream(
                self.pengaturan.aliran_alert_klaster,
                alert_event.model_dump(mode="json"),
            )

        try:
            from orchestration.pta_tasks import analisis_pta_tertunda

            analisis_pta_tertunda.delay(event_naa.model_dump(mode="json"))
        except Exception as exc:
            logger.info("Dispatch PTA belum dikirim", extra={"extra_payload": {"alasan": str(exc)}})

        return event_naa

    def jalankan(self, nama_konsumen: str = "naa-worker-1") -> None:
        logger = logger_dengan_trace(__name__, nama_konsumen)
        while True:
            batch = self.transport.baca_stream_grup(
                self.pengaturan.aliran_tia_keluar,
                self.nama_grup,
                nama_konsumen,
                count=10,
                block_ms=5000,
            )
            for _, messages in batch:
                ids_terproses: List[str] = []
                for message_id, fields in messages:
                    trace_id = nama_konsumen
                    try:
                        payload = json.loads(fields["payload"])
                        event_tia = TiaThreatEvent.model_validate(payload)
                        trace_id = event_tia.metadata.trace_id
                        self.proses_event(event_tia)
                        logger_dengan_trace(__name__, trace_id).info("NAA selesai memproses event TIA")
                    except Exception as exc:
                        logger_dengan_trace(__name__, trace_id).exception("NAA gagal memproses event TIA")
                        self.transport.terbitkan_dead_letter(
                            self.pengaturan.aliran_tia_keluar,
                            {
                                "trace_id": trace_id,
                                "tahap": "konsumer_naa",
                                "alasan": str(exc),
                                "payload": fields.get("payload"),
                            },
                        )
                    ids_terproses.append(message_id)
                self.transport.akui_stream(self.pengaturan.aliran_tia_keluar, self.nama_grup, *ids_terproses)
