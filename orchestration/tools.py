from __future__ import annotations

from typing import Any, Dict, Iterable, List

from langchain_core.tools import tool

from orchestration.mcp import McpGateway
from orchestration.schema import BuktiIntelijen, RencanaRetrieval, ToolCallRencana


def buat_toolset_mcp(mcp: McpGateway, trace_id: str):
    @tool("ambil_histori_entitas")
    def ambil_histori_entitas(id_profil: str) -> dict:
        """Ambil profil, akun, dan postingan historis berdasarkan id_profil."""
        return mcp.ambil_histori_entitas(trace_id, id_profil)

    @tool("ambil_histori_lokasi")
    def ambil_histori_lokasi(id_profil: str) -> list:
        """Ambil histori lokasi sebuah profil."""
        return mcp.ambil_histori_lokasi(trace_id, id_profil)

    @tool("ambil_histori_transaksi")
    def ambil_histori_transaksi(id_profil: str) -> list:
        """Ambil histori transaksi masuk dan keluar sebuah profil."""
        return mcp.ambil_histori_transaksi(trace_id, id_profil)

    @tool("ambil_histori_kampanye")
    def ambil_histori_kampanye(id_profil: str) -> list:
        """Ambil histori kampanye yang terkait dengan sebuah profil."""
        return mcp.ambil_histori_kampanye(trace_id, id_profil)

    @tool("ambil_konteks_rag")
    def ambil_konteks_rag(daftar_entitas: list[str]) -> dict:
        """Ambil ringkasan laporan, skor risiko, dan postingan untuk kebutuhan retrieval."""
        return mcp.ambil_konteks_rag(trace_id, daftar_entitas)

    @tool("cari_watchlist_entitas")
    def cari_watchlist_entitas(entitas: str) -> list:
        """Cari kecocokan watchlist berdasarkan nilai entitas."""
        return mcp.ambil_watchlist_profile(trace_id, entitas)

    return {
        "ambil_histori_entitas": ambil_histori_entitas,
        "ambil_histori_lokasi": ambil_histori_lokasi,
        "ambil_histori_transaksi": ambil_histori_transaksi,
        "ambil_histori_kampanye": ambil_histori_kampanye,
        "ambil_konteks_rag": ambil_konteks_rag,
        "cari_watchlist_entitas": cari_watchlist_entitas,
    }


def _pastikan_list(nilai: Any) -> List[Any]:
    if nilai is None:
        return []
    if isinstance(nilai, list):
        return nilai
    return [nilai]


def _ringkas_item(nilai: Any) -> str:
    if isinstance(nilai, dict):
        potongan = []
        for kunci in ("nama_lengkap", "nama_tampil", "judul", "ringkasan", "konten", "kota", "provinsi", "tujuan"):
            if nilai.get(kunci):
                potongan.append(str(nilai[kunci]))
        if potongan:
            return " | ".join(potongan[:3])
        return str({kunci: nilai[kunci] for kunci in list(nilai.keys())[:4]})
    return str(nilai)


def _bangun_bukti_dari_hasil(nama_tool: str, hasil: Any, entitas_terkait: Iterable[str]) -> List[BuktiIntelijen]:
    bukti: List[BuktiIntelijen] = []
    daftar_item = _pastikan_list(hasil)
    if isinstance(hasil, dict):
        daftar_item = []
        for nilai in hasil.values():
            daftar_item.extend(_pastikan_list(nilai))

    for item in daftar_item[:15]:
        bukti.append(
            BuktiIntelijen(
                sumber=nama_tool,
                kategori=nama_tool,
                ringkasan=_ringkas_item(item),
                skor_penting=0.6,
                keterkaitan_entitas=list(entitas_terkait)[:6],
                confidence=0.65,
            )
        )
    return bukti


def _ambil_id_profil(parameter: Dict[str, Any], hit_watchlist: List[dict[str, Any]]) -> List[str]:
    jika_list = parameter.get("id_profil") or parameter.get("id_profil_list") or parameter.get("id_profil_terkait")
    if isinstance(jika_list, list):
        return [str(item) for item in jika_list if item]
    if isinstance(jika_list, str) and jika_list:
        return [jika_list]
    return list(dict.fromkeys([item["id_profil"] for item in hit_watchlist if item.get("id_profil")]))


def jalankan_rencana_retrieval(
    mcp: McpGateway,
    trace_id: str,
    rencana: RencanaRetrieval,
    entitas: List[str] | None = None,
    hit_watchlist: List[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], List[ToolCallRencana], List[dict[str, Any]]]:
    entitas = entitas or []
    hit_watchlist = hit_watchlist or []
    hasil_retrieval: dict[str, Any] = {}
    tool_calls_terpakai: List[ToolCallRencana] = []
    kandidat_bukti: List[dict[str, Any]] = []

    for call in rencana.calls:
        parameter = dict(call.parameter)
        nama_tool = call.nama_tool

        if nama_tool == "ambil_konteks_rag":
            daftar_entitas = parameter.get("daftar_entitas") or entitas
            hasil = mcp.ambil_konteks_rag(trace_id, daftar_entitas)
        elif nama_tool == "cari_watchlist_entitas":
            daftar_entitas = parameter.get("daftar_entitas") or entitas
            hasil = []
            for entitas_item in daftar_entitas[:12]:
                hasil.extend(mcp.ambil_watchlist_profile(trace_id, entitas_item))
        elif nama_tool == "ambil_histori_entitas":
            hasil = []
            for id_profil in _ambil_id_profil(parameter, hit_watchlist):
                hasil.append(mcp.ambil_histori_entitas(trace_id, id_profil))
        elif nama_tool == "ambil_histori_lokasi":
            hasil = []
            for id_profil in _ambil_id_profil(parameter, hit_watchlist):
                hasil.extend(mcp.ambil_histori_lokasi(trace_id, id_profil))
        elif nama_tool == "ambil_histori_transaksi":
            hasil = []
            for id_profil in _ambil_id_profil(parameter, hit_watchlist):
                hasil.extend(mcp.ambil_histori_transaksi(trace_id, id_profil))
        elif nama_tool == "ambil_histori_kampanye":
            hasil = []
            for id_profil in _ambil_id_profil(parameter, hit_watchlist):
                hasil.extend(mcp.ambil_histori_kampanye(trace_id, id_profil))
        else:
            continue

        hasil_retrieval[nama_tool] = hasil
        tool_calls_terpakai.append(call)
        kandidat_bukti.extend(
            item.model_dump() for item in _bangun_bukti_dari_hasil(nama_tool, hasil, entitas)
        )

    return hasil_retrieval, tool_calls_terpakai, kandidat_bukti
