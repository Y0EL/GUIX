from __future__ import annotations

import argparse

from orchestration.analisis_kasus import MesinAnalisisKasus
from orchestration.config import muat_pengaturan_runtime
from orchestration.logging_utils import konfigurasikan_logging
from orchestration.mcp import McpGateway
from orchestration.naa_worker import PekerjaNAA
from orchestration.openai_stack import LayananOpenAI
from orchestration.seed_data import PenyiapData
from orchestration.tia_graph import MesinTIA
from orchestration.transport import TransportRuntime


def _buat_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CLI backend TIA / NAA / PTA")
    sub = parser.add_subparsers(dest="perintah", required=True)
    sub.add_parser("seed", help="Siapkan skema PostgreSQL dan seed Neo4j")
    parser_publish = sub.add_parser("publish-osint", help="Terbitkan berita uji ke Kafka")
    parser_publish.add_argument("--id", dest="id_berita", help="Terbitkan hanya satu berita berdasarkan id_berita")
    parser_publish.add_argument("--limit", dest="limit", type=int, help="Batasi jumlah berita yang diterbitkan")
    parser_analisis = sub.add_parser("analisis-kasus", help="Analisis satu kasus dan hasilkan artefak analisa")
    parser_analisis.add_argument("--id", dest="id_kasus", required=True, help="ID kasus dari dataset/kasus.json")
    sub.add_parser("run-tia", help="Jalankan worker TIA")
    sub.add_parser("run-naa", help="Jalankan worker NAA")
    sub.add_parser("run-pta-worker", help="Jalankan worker Celery PTA")
    return parser


def main() -> None:
    parser = _buat_parser()
    args = parser.parse_args()
    pengaturan = muat_pengaturan_runtime()
    konfigurasikan_logging(pengaturan.level_log)

    if args.perintah == "seed":
        penyiap = PenyiapData(pengaturan)
        penyiap.seed_relational()
        penyiap.seed_neo4j()
        penyiap.tutup()
        return

    if args.perintah == "publish-osint":
        penyiap = PenyiapData(pengaturan)
        penyiap.terbitkan_berita_ke_kafka(limit=args.limit, id_berita=args.id_berita)
        penyiap.tutup()
        return

    if args.perintah == "analisis-kasus":
        mcp = McpGateway(pengaturan)
        layanan_openai = LayananOpenAI(pengaturan)
        mesin = MesinAnalisisKasus(pengaturan, mcp, layanan_openai)
        hasil = mesin.analisis(args.id_kasus)
        print(hasil["artefak"]["direktori"])
        print(hasil["artefak"]["fingerprint_sha256"])
        return

    if args.perintah == "run-tia":
        transport = TransportRuntime(pengaturan)
        mcp = McpGateway(pengaturan)
        layanan_openai = LayananOpenAI(pengaturan)
        mesin = MesinTIA(pengaturan, transport, mcp, layanan_openai)
        mesin.jalankan_konsumer()
        return

    if args.perintah == "run-naa":
        transport = TransportRuntime(pengaturan)
        mcp = McpGateway(pengaturan)
        layanan_openai = LayananOpenAI(pengaturan)
        pekerja = PekerjaNAA(pengaturan, transport, mcp, layanan_openai)
        pekerja.jalankan()
        return

    if args.perintah == "run-pta-worker":
        from orchestration.pta_tasks import aplikasi_celery

        aplikasi_celery.worker_main(
            argv=[
                "worker",
                "--loglevel=INFO",
                "--pool=solo",
            ]
        )


if __name__ == "__main__":
    main()
