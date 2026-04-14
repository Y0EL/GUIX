from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


class KesalahanKonfigurasi(RuntimeError):
    """Dilempar saat variabel lingkungan wajib belum siap."""


def _ambil_wajib(nama_variabel: str) -> str:
    nilai = os.getenv(nama_variabel, "").strip()
    if not nilai:
        raise KesalahanKonfigurasi(f"Variabel lingkungan {nama_variabel} wajib diisi.")
    return nilai


def _ambil_float(nama_variabel: str, bawaan: float) -> float:
    return float(os.getenv(nama_variabel, str(bawaan)))


def _ambil_int(nama_variabel: str, bawaan: int) -> int:
    return int(os.getenv(nama_variabel, str(bawaan)))


@dataclass(frozen=True)
class PengaturanRuntime:
    kunci_openai: str
    model_openai: str
    timeout_openai: int
    maksimal_retry_openai: int
    kafka_bootstrap_servers: str
    topik_osint_raw: str
    grup_konsumen_tia: str
    url_redis: str
    aliran_tia_keluar: str
    aliran_naa_keluar: str
    aliran_alert_klaster: str
    aliran_hitl_review: str
    aliran_pta_hasil: str
    broker_celery: str
    backend_hasil_celery: str
    dsn_postgres: str
    uri_neo4j: str
    pengguna_neo4j: str
    sandi_neo4j: str
    token_mcp: str
    akar_data: Path
    ambang_relevansi: float
    ambang_tinggi: int
    ambang_kritis: int
    jendela_pta_hari: int
    level_log: str

    @property
    def jalur_dataset_berita(self) -> Path:
        return self.akar_data / "news" / "dataset.jsonl"

    @property
    def direktori_dataset(self) -> Path:
        return self.akar_data / "dataset"


def muat_pengaturan_runtime() -> PengaturanRuntime:
    """Muat konfigurasi backend dan gagal cepat bila ada komponen inti yang belum siap."""
    load_dotenv(Path(".env"))

    kunci_openai = _ambil_wajib("OPENAI_API_KEY")
    if kunci_openai in {"isi_kunci_openai_di_sini", "sk-placeholder", "sk-ganti-dengan-kunci-valid"}:
        raise KesalahanKonfigurasi("OPENAI_API_KEY belum diganti dengan kunci yang valid.")

    return PengaturanRuntime(
        kunci_openai=kunci_openai,
        model_openai=os.getenv("OPENAI_MODEL", "gpt-5-nano"),
        timeout_openai=_ambil_int("OPENAI_TIMEOUT_SECONDS", 60),
        maksimal_retry_openai=_ambil_int("OPENAI_MAX_RETRIES", 3),
        kafka_bootstrap_servers=_ambil_wajib("KAFKA_BOOTSTRAP_SERVERS"),
        topik_osint_raw=_ambil_wajib("KAFKA_TOPIC_OSINT_RAW"),
        grup_konsumen_tia=_ambil_wajib("KAFKA_CONSUMER_GROUP_TIA"),
        url_redis=_ambil_wajib("REDIS_URL"),
        aliran_tia_keluar=_ambil_wajib("REDIS_STREAM_TIA_OUT"),
        aliran_naa_keluar=_ambil_wajib("REDIS_STREAM_NAA_OUT"),
        aliran_alert_klaster=_ambil_wajib("REDIS_STREAM_CLUSTER_ALERT"),
        aliran_hitl_review=_ambil_wajib("REDIS_STREAM_HITL_REVIEW"),
        aliran_pta_hasil=_ambil_wajib("REDIS_STREAM_PTA_RESULT"),
        broker_celery=_ambil_wajib("CELERY_BROKER_URL"),
        backend_hasil_celery=_ambil_wajib("CELERY_RESULT_BACKEND"),
        dsn_postgres=_ambil_wajib("POSTGRES_DSN"),
        uri_neo4j=_ambil_wajib("NEO4J_URI"),
        pengguna_neo4j=_ambil_wajib("NEO4J_USERNAME"),
        sandi_neo4j=_ambil_wajib("NEO4J_PASSWORD"),
        token_mcp=_ambil_wajib("MCP_SHARED_TOKEN"),
        akar_data=Path(os.getenv("DATA_ROOT", ".")).resolve(),
        ambang_relevansi=_ambil_float("AMBANG_RELEVANSI", 0.35),
        ambang_tinggi=_ambil_int("AMBANG_TINGGI", 75),
        ambang_kritis=_ambil_int("AMBANG_KRITIS", 90),
        jendela_pta_hari=_ambil_int("JENDELA_PTA_HARI", 30),
        level_log=os.getenv("LOG_LEVEL", "INFO"),
    )
