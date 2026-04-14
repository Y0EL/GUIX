from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


LevelRisiko = Literal["RENDAH", "SEDANG", "TINGGI", "KRITIS"]
JenisSumber = Literal["NEWS", "PROFILE", "NETWORK", "TRANSACTION", "LOCATION", "CAMPAIGN"]
StatusReview = Literal["siap_hitl", "perlu_perbaikan", "eskalasi_manual"]


def buat_id_awal(awalan: str) -> str:
    return f"{awalan}-{uuid4().hex}"


def ubah_ke_teks(nilai: Any) -> str:
    if nilai is None:
        return ""
    if isinstance(nilai, str):
        return nilai
    if isinstance(nilai, list):
        return " ".join(str(item).strip() for item in nilai if str(item).strip()).strip()
    if isinstance(nilai, dict):
        return "; ".join(f"{k}: {v}" for k, v in nilai.items())
    return str(nilai)


class MetadataEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: buat_id_awal("evt"))
    trace_id: str = Field(default_factory=lambda: buat_id_awal("trace"))
    parent_event_id: Optional[str] = None
    idempotency_key: str = Field(default_factory=lambda: buat_id_awal("idem"))
    source_type: JenisSumber
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    schema_version: str = "1.0.0"
    severity: Optional[LevelRisiko] = None


class EntitasTerekstrak(BaseModel):
    nilai: str
    tipe: Literal["PERSON", "ORG", "LOCATION", "DATE", "DEVICE", "CHANNEL", "ACCOUNT", "OTHER"]
    confidence: float
    alias: List[str] = Field(default_factory=list)


class DaftarEntitas(BaseModel):
    items: List[EntitasTerekstrak]


class EntitasDitolak(BaseModel):
    nilai: str
    alasan: str


class HitWatchlist(BaseModel):
    id_profil: str
    nama_lengkap: str
    skor_kecocokan: float
    alasan_kecocokan: List[str] = Field(default_factory=list)


class ToolCallRencana(BaseModel):
    nama_tool: str
    parameter: Dict[str, Any] = Field(default_factory=dict)
    alasan: str
    prioritas: int = 1


class RencanaRetrieval(BaseModel):
    tujuan: str
    calls: List[ToolCallRencana] = Field(default_factory=list)
    butuh_retrieval_tambahan: bool = False
    catatan_planner: str = ""
    confidence_reasoning: str = ""

    _normalisasi_catatan_planner = field_validator("catatan_planner", mode="before")(ubah_ke_teks)
    _normalisasi_confidence_reasoning = field_validator("confidence_reasoning", mode="before")(ubah_ke_teks)


class BuktiIntelijen(BaseModel):
    sumber: str
    kategori: str
    ringkasan: str
    skor_penting: float
    keterkaitan_entitas: List[str] = Field(default_factory=list)
    confidence: float


class PaketBukti(BaseModel):
    items: List[BuktiIntelijen] = Field(default_factory=list)
    prioritas_bukti: List[str] = Field(default_factory=list)
    celah_bukti: List[str] = Field(default_factory=list)


class HasilVerifikasiEntitas(BaseModel):
    entitas_valid: List[EntitasTerekstrak] = Field(default_factory=list)
    entitas_ditolak: List[EntitasDitolak] = Field(default_factory=list)
    konflik_tipe: List[str] = Field(default_factory=list)
    alias_duplikat: List[str] = Field(default_factory=list)
    butuh_retrieval_tambahan: bool = False
    confidence_reasoning: str = ""
    catatan_verifikator: str = ""

    _normalisasi_confidence_reasoning = field_validator("confidence_reasoning", mode="before")(ubah_ke_teks)
    _normalisasi_catatan_verifikator = field_validator("catatan_verifikator", mode="before")(ubah_ke_teks)


class PenilaianAncaman(BaseModel):
    level_ancaman: LevelRisiko
    indikator: List[str]
    alasan: str
    confidence: float
    entitas_kunci: List[str]
    risk_rationale: List[str] = Field(default_factory=list)
    _normalisasi_alasan = field_validator("alasan", mode="before")(ubah_ke_teks)


class HasilKritikAncaman(BaseModel):
    kontradiksi_ditemukan: List[str] = Field(default_factory=list)
    celah_bukti: List[str] = Field(default_factory=list)
    klaim_berlebihan: List[str] = Field(default_factory=list)
    butuh_retrieval_tambahan: bool = False
    confidence_reasoning: str = ""
    risk_rationale: List[str] = Field(default_factory=list)

    _normalisasi_confidence_reasoning = field_validator("confidence_reasoning", mode="before")(ubah_ke_teks)


class HasilReviewBriefing(BaseModel):
    status_review: StatusReview
    bukti_lemah: List[str] = Field(default_factory=list)
    catatan_review: str = ""
    butuh_retrieval_tambahan: bool = False

    _normalisasi_catatan_review = field_validator("catatan_review", mode="before")(ubah_ke_teks)


class RingkasanIntelijen(BaseModel):
    judul_brief: str
    ringkasan_eksekutif: str
    kronologi: List[str] = Field(default_factory=list)
    entitas_utama: List[str] = Field(default_factory=list)
    sinyal_penguat: List[str] = Field(default_factory=list)
    korelasi_awal: List[str] = Field(default_factory=list)
    rekomendasi_awal: List[str] = Field(default_factory=list)
    confidence: float
    confidence_reasoning: str = ""
    bukti_lemah: List[str] = Field(default_factory=list)

    _normalisasi_judul_brief = field_validator("judul_brief", mode="before")(ubah_ke_teks)
    _normalisasi_ringkasan_eksekutif = field_validator("ringkasan_eksekutif", mode="before")(ubah_ke_teks)
    _normalisasi_confidence_reasoning = field_validator("confidence_reasoning", mode="before")(ubah_ke_teks)


class RelasiSPO(BaseModel):
    subjek: str
    predikat: str
    objek: str
    tipe_subjek: str
    tipe_objek: str
    evidence_text: str
    confidence: float


class DaftarRelasi(BaseModel):
    items: List[RelasiSPO]


class RelasiDitolak(BaseModel):
    subjek: str
    predikat: str
    objek: str
    alasan: str


class HasilVerifikasiRelasi(BaseModel):
    relasi_valid: List[RelasiSPO] = Field(default_factory=list)
    relasi_ditolak: List[RelasiDitolak] = Field(default_factory=list)
    confidence_reasoning: str = ""
    butuh_tinjauan_manusia: bool = False

    _normalisasi_confidence_reasoning = field_validator("confidence_reasoning", mode="before")(ubah_ke_teks)


class InterpretasiCluster(BaseModel):
    cluster_id: str
    alasan_penting: str
    broker_utama: List[str] = Field(default_factory=list)
    perubahan_struktural: List[str] = Field(default_factory=list)
    entitas_kunci: List[str] = Field(default_factory=list)
    confidence_reasoning: str = ""

    _normalisasi_alasan_penting = field_validator("alasan_penting", mode="before")(ubah_ke_teks)
    _normalisasi_confidence_reasoning = field_validator("confidence_reasoning", mode="before")(ubah_ke_teks)


class InterpretasiKetidakpastian(BaseModel):
    confidence_score: float
    confidence_band: str
    confidence_reasoning: str
    driver_features: List[str] = Field(default_factory=list)
    counter_signals: List[str] = Field(default_factory=list)

    _normalisasi_confidence_band = field_validator("confidence_band", mode="before")(ubah_ke_teks)
    _normalisasi_confidence_reasoning = field_validator("confidence_reasoning", mode="before")(ubah_ke_teks)


class HasilKritikRekomendasi(BaseModel):
    rekomendasi_selaras: bool
    kontra_indikasi: List[str] = Field(default_factory=list)
    jarak_dari_evidence: str = ""
    catatan_kritik: str = ""

    _normalisasi_jarak_dari_evidence = field_validator("jarak_dari_evidence", mode="before")(ubah_ke_teks)
    _normalisasi_catatan_kritik = field_validator("catatan_kritik", mode="before")(ubah_ke_teks)


class AktorSindikat(BaseModel):
    id_profil: str = ""
    nama: str
    peran: str
    alasan: str
    confidence: float = 0.0

    _normalisasi_nama = field_validator("nama", mode="before")(ubah_ke_teks)
    _normalisasi_peran = field_validator("peran", mode="before")(ubah_ke_teks)
    _normalisasi_alasan = field_validator("alasan", mode="before")(ubah_ke_teks)


class RelasiSindikat(BaseModel):
    sumber: str
    target: str
    jenis_relasi: str
    alasan: str = ""
    confidence: float = 0.0

    @model_validator(mode="before")
    @classmethod
    def normalisasi_bentuk_awal(cls, nilai: Any) -> Any:
        if not isinstance(nilai, dict):
            return nilai
        sumber = (
            nilai.get("sumber")
            or nilai.get("sumber_nama")
            or nilai.get("nama_sumber")
            or nilai.get("sumber_id")
            or nilai.get("id_sumber")
            or ""
        )
        target = (
            nilai.get("target")
            or nilai.get("target_nama")
            or nilai.get("nama_target")
            or nilai.get("target_id")
            or nilai.get("id_target")
            or ""
        )
        jenis_relasi = (
            nilai.get("jenis_relasi")
            or nilai.get("relasi")
            or nilai.get("tipe_relasi")
            or nilai.get("predikat")
            or ""
        )
        alasan = nilai.get("alasan") or nilai.get("catatan") or nilai.get("ringkasan") or ""
        confidence = nilai.get("confidence")
        if confidence is None:
            confidence = nilai.get("skor_confidence")
        if confidence is None:
            confidence = 0.0
        return {
            **nilai,
            "sumber": sumber,
            "target": target,
            "jenis_relasi": jenis_relasi,
            "alasan": alasan,
            "confidence": confidence,
        }

    _normalisasi_sumber = field_validator("sumber", mode="before")(ubah_ke_teks)
    _normalisasi_target = field_validator("target", mode="before")(ubah_ke_teks)
    _normalisasi_jenis_relasi = field_validator("jenis_relasi", mode="before")(ubah_ke_teks)
    _normalisasi_alasan = field_validator("alasan", mode="before")(ubah_ke_teks)


class DossierSindikat(BaseModel):
    id_kasus: str
    judul_kasus: str
    ringkasan_eksekutif: str
    indikasi_sindikat: bool
    confidence: float
    confidence_reasoning: str = ""
    alasan_utama: List[str] = Field(default_factory=list)
    pola_koordinasi: List[str] = Field(default_factory=list)
    aktor_inti: List[AktorSindikat] = Field(default_factory=list)
    relasi_kunci: List[RelasiSindikat] = Field(default_factory=list)
    bukti_utama: List[str] = Field(default_factory=list)
    bukti_lemah: List[str] = Field(default_factory=list)
    rekomendasi_lanjutan: List[str] = Field(default_factory=list)
    narasi_analisis: str = ""

    _normalisasi_id_kasus = field_validator("id_kasus", mode="before")(ubah_ke_teks)
    _normalisasi_judul_kasus = field_validator("judul_kasus", mode="before")(ubah_ke_teks)
    _normalisasi_ringkasan = field_validator("ringkasan_eksekutif", mode="before")(ubah_ke_teks)
    _normalisasi_confidence_reasoning = field_validator("confidence_reasoning", mode="before")(ubah_ke_teks)
    _normalisasi_narasi = field_validator("narasi_analisis", mode="before")(ubah_ke_teks)


class RekomendasiAksi(BaseModel):
    probabilitas_eskalasi: float
    horizon_hari: int
    confidence_score: float
    confidence_band: str
    lokasi_prioritas: List[str]
    faktor_pendorong: List[str]
    driver_features: List[str] = Field(default_factory=list)
    counter_signals: List[str] = Field(default_factory=list)
    timeline_prediksi: List[str] = Field(default_factory=list)
    rekomendasi_tindak_lanjut: List[str]
    rekomendasi_aksi_bertingkat: List[str] = Field(default_factory=list)
    evidence_pointers: List[str]
    ringkasan_aksi: str

    _normalisasi_confidence_band = field_validator("confidence_band", mode="before")(ubah_ke_teks)
    _normalisasi_ringkasan_aksi = field_validator("ringkasan_aksi", mode="before")(ubah_ke_teks)


class OsintRawPayload(BaseModel):
    id_berita: str
    judul: str
    subjudul: str
    isi: str
    kategori: Optional[str] = None
    provinsi: Optional[str] = None
    lokasi: Optional[str] = None
    reporter: Optional[str] = None
    portal: Optional[str] = None
    published_at: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)


class OsintRawEvent(BaseModel):
    metadata: MetadataEvent
    payload: OsintRawPayload


class TiaFilteredPayload(BaseModel):
    id_berita: str
    skor_relevansi: float
    aturan_terpicu: List[str]
    kata_kunci_terdeteksi: List[str]
    judul: str


class TiaFilteredEvent(BaseModel):
    metadata: MetadataEvent
    payload: TiaFilteredPayload


class TiaThreatPayload(BaseModel):
    id_berita: str
    skor_relevansi: float
    penilaian_ancaman: PenilaianAncaman
    skor_agregat: float
    entitas: List[EntitasTerekstrak]
    hit_watchlist: List[HitWatchlist]
    konteks_ringkas: Dict[str, Any]
    putusan_planner: RencanaRetrieval
    tool_calls_terpakai: List[ToolCallRencana] = Field(default_factory=list)
    hasil_verifikasi_entitas: HasilVerifikasiEntitas
    hasil_kritik_ancaman: HasilKritikAncaman
    evidence_ranked: PaketBukti
    briefing: RingkasanIntelijen
    review_briefing: HasilReviewBriefing
    status_review: StatusReview = "siap_hitl"


class TiaThreatEvent(BaseModel):
    metadata: MetadataEvent
    payload: TiaThreatPayload


class NaaGraphPayload(BaseModel):
    id_berita: str
    id_profil_terkait: List[str]
    relasi: List[RelasiSPO]
    hasil_verifikasi_relasi: HasilVerifikasiRelasi
    clusters: List[Dict[str, Any]]
    interpretasi_cluster: List[InterpretasiCluster]
    scores: Dict[str, Dict[str, float]]
    geo_overlays: List[Dict[str, Any]]
    alerts: List[str]
    evidence_summary: List[str] = Field(default_factory=list)
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


class NaaGraphEvent(BaseModel):
    metadata: MetadataEvent
    payload: NaaGraphPayload


class NaaClusterAlertEvent(BaseModel):
    metadata: MetadataEvent
    payload: Dict[str, Any]


class PtaForecastPayload(BaseModel):
    entitas_target: List[str]
    skor_anomali: float
    skor_ensemble: float
    probabilitas_eskalasi: float
    confidence_score: float
    confidence_band: str
    faktor_pendorong: List[str]
    driver_features: List[str] = Field(default_factory=list)
    counter_signals: List[str] = Field(default_factory=list)
    timeline_prediksi: List[str] = Field(default_factory=list)
    interpretasi_ketidakpastian: InterpretasiKetidakpastian
    hasil_kritik_rekomendasi: HasilKritikRekomendasi
    rekomendasi_aksi: RekomendasiAksi
    fitur_ringkas: Dict[str, float]


class PtaForecastEvent(BaseModel):
    metadata: MetadataEvent
    payload: PtaForecastPayload


class HitlReviewPayload(BaseModel):
    trace_id: str
    risk_level: LevelRisiko
    confidence_score: float
    briefing_summary: str
    recommended_action: List[str]
    evidence: List[str]
    bukti_pendukung: List[str] = Field(default_factory=list)
    bukti_lemah: List[str] = Field(default_factory=list)
    confidence_reasoning: str = ""
    alasan_jalur_persetujuan: str = ""
    approver_role: Literal["analis_lead", "supervisor", "review_queue", "auto_log"]
    sumber_event: str


class HitlReviewEvent(BaseModel):
    metadata: MetadataEvent
    payload: HitlReviewPayload
