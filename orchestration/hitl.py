from __future__ import annotations

from orchestration.config import PengaturanRuntime
from orchestration.mcp import McpGateway
from orchestration.schema import HitlReviewEvent, HitlReviewPayload, MetadataEvent
from orchestration.transport import TransportRuntime


def tentukan_role_persetujuan(level_risiko: str, confidence_score: float) -> str:
    if level_risiko == "KRITIS" or confidence_score >= 90:
        return "analis_lead"
    if level_risiko == "TINGGI" or confidence_score >= 75:
        return "supervisor"
    if level_risiko == "SEDANG":
        return "review_queue"
    return "auto_log"


def jelaskan_jalur_persetujuan(level_risiko: str, confidence_score: float, approver_role: str) -> str:
    return (
        f"Jalur {approver_role} dipilih karena level risiko {level_risiko} "
        f"dengan confidence {round(confidence_score, 2)}."
    )


def bentuk_payload_hitl(
    trace_id: str,
    sumber_event: str,
    level_risiko: str,
    confidence_score: float,
    briefing_summary: str,
    recommended_action: list[str],
    evidence: list[str],
    bukti_lemah: list[str] | None = None,
    confidence_reasoning: str = "",
) -> HitlReviewEvent:
    approver_role = tentukan_role_persetujuan(level_risiko, confidence_score)
    return HitlReviewEvent(
        metadata=MetadataEvent(
            trace_id=trace_id,
            source_type="NEWS",
            severity=level_risiko,
        ),
        payload=HitlReviewPayload(
            trace_id=trace_id,
            risk_level=level_risiko,
            confidence_score=confidence_score,
            briefing_summary=briefing_summary,
            recommended_action=recommended_action,
            evidence=evidence,
            bukti_pendukung=evidence,
            bukti_lemah=bukti_lemah or [],
            confidence_reasoning=confidence_reasoning,
            alasan_jalur_persetujuan=jelaskan_jalur_persetujuan(
                level_risiko, confidence_score, approver_role
            ),
            approver_role=approver_role,
            sumber_event=sumber_event,
        ),
    )


def route_review(
    pengaturan: PengaturanRuntime,
    transport: TransportRuntime,
    mcp: McpGateway,
    event: HitlReviewEvent,
) -> None:
    transport.terbitkan_redis_stream(
        pengaturan.aliran_hitl_review,
        event.model_dump(mode="json"),
    )
    mcp.simpan_review_hitl(event.payload.trace_id, event.model_dump(mode="json"))
