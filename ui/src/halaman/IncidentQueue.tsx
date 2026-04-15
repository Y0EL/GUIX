import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle } from 'lucide-react'

import IncidentTopBar from '../components/IncidentTopBar'
import IncidentListPanel from '../components/IncidentListPanel'
import IncidentDetailPanel from '../components/IncidentDetailPanel'

import type {
  Kasus, Peringatan, SkorRisiko,
  IncidentWithMeta, IncidentStatus,
} from '../types'
import { muatJson } from '../utils'
import { useArrowNav } from '../hooks/useArrowNav'

export default function IncidentQueue() {
  useArrowNav()

  /* ── Data dari JSON ── */
  const [kasus, setKasus] = useState<Kasus[]>([])
  const [skorData, setSkorData] = useState<SkorRisiko[]>([])
  const [peringatan, setPeringatan] = useState<Peringatan[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  /* ── Runtime state (in-memory) ── */
  const [statusMap, setStatusMap] = useState<Record<string, IncidentStatus>>({})
  const [analystMap, setAnalystMap] = useState<Record<string, string | null>>({})
  const [briefingMap, setBriefingMap] = useState<Record<string, boolean>>({})

  /* ── UI state ── */
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [filterStatus, setFilterStatus] = useState<IncidentStatus[]>([])
  const [filterTipe, setFilterTipe] = useState<string[]>([])
  const [filterKota] = useState<string[]>([])
  const [sortBy, setSortBy] = useState<'risiko' | 'waktu' | 'alert'>('risiko')

  /* ── Load data ── */
  useEffect(() => {
    async function muat() {
      try {
        const [kData, sData, pData] = await Promise.all([
          muatJson<Kasus[]>('/data/kasus.json'),
          muatJson<SkorRisiko[]>('/data/skor_risiko.json'),
          muatJson<Peringatan[]>('/data/peringatan.json'),
        ])
        setKasus(kData)
        setSkorData(sData)
        setPeringatan(pData)

        // Auto-select incident with highest risk score
        const sorted = [...kData].sort((a, b) => {
          const sa = sData.find(s => s.id_kasus === a.id_kasus)?.skor_risiko ?? 0
          const sb = sData.find(s => s.id_kasus === b.id_kasus)?.skor_risiko ?? 0
          return sb - sa
        })
        if (sorted.length > 0) setSelectedId(sorted[0].id_kasus)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Gagal memuat data')
      } finally {
        setLoading(false)
      }
    }
    muat()
  }, [])

  /* ── Join: Kasus + SkorRisiko + Peringatan + runtime state ── */
  const incidents = useMemo<IncidentWithMeta[]>(() => {
    return kasus.map(k => {
      const skor = skorData.find(s => s.id_kasus === k.id_kasus) ?? null
      const linked = peringatan.filter(p => p.id_kasus === k.id_kasus)
      return {
        ...k,
        skor,
        alertCount: linked.length,
        linkedAlerts: linked,
        runtimeStatus: statusMap[k.id_kasus] ?? (k.status as IncidentStatus) ?? 'monitoring',
        assignedAnalyst: analystMap[k.id_kasus] ?? null,
        flaggedForBriefing: briefingMap[k.id_kasus] ?? false,
      }
    })
  }, [kasus, skorData, peringatan, statusMap, analystMap, briefingMap])

  /* Keep selection valid when filters change */
  useEffect(() => {
    const visible = incidents.filter(i =>
      (filterStatus.length === 0 || filterStatus.includes(i.runtimeStatus)) &&
      (filterTipe.length === 0 || filterTipe.includes(i.tipe_kasus)) &&
      (filterKota.length === 0 || filterKota.includes(i.kota))
    )
    if (selectedId && !visible.find(i => i.id_kasus === selectedId)) {
      setSelectedId(visible[0]?.id_kasus ?? null)
    }
  }, [incidents, filterStatus, filterTipe, filterKota, selectedId])

  const selectedIncident = incidents.find(i => i.id_kasus === selectedId) ?? null

  /* ── Handlers ── */
  function handleStatusUpdate(id: string, status: IncidentStatus) {
    setStatusMap(prev => ({ ...prev, [id]: status }))
  }
  function handleAssign(id: string, analyst: string) {
    setAnalystMap(prev => ({ ...prev, [id]: analyst }))
  }
  function handleToggleBriefing(id: string) {
    setBriefingMap(prev => ({ ...prev, [id]: !prev[id] }))
  }
  function handleResolve(id: string) {
    setStatusMap(prev => ({ ...prev, [id]: 'selesai' }))
  }
  function handleEscalate(id: string) {
    setStatusMap(prev => ({ ...prev, [id]: 'eskalasi' }))
  }

  function handleFilterStatus(s: IncidentStatus) {
    setFilterStatus(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s])
  }
  function handleFilterTipe(t: string) {
    setFilterTipe(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t])
  }

  /* ── Loading / error states ── */
  if (loading) {
    return (
      <div className="halaman-iq" style={{ display: 'grid', placeContent: 'center' }}>
        <div className="overlay-tengah" style={{ position: 'relative', background: 'none' }}>
          <div className="spinner" />
          <h1>Memuat Incident Queue...</h1>
          <p>Mengambil data insiden aktif</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="halaman-iq" style={{ display: 'grid', placeContent: 'center' }}>
        <div className="overlay-tengah overlay-error" style={{ position: 'relative', background: 'none' }}>
          <AlertTriangle size={36} />
          <h1>Gagal Memuat Data</h1>
          <p>{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="halaman-iq">
      <IncidentTopBar incidents={incidents} />

      <div className="iq-body">
        <IncidentListPanel
          incidents={incidents}
          selected={selectedId}
          filterStatus={filterStatus}
          filterTipe={filterTipe}
          filterKota={filterKota}
          sortBy={sortBy}
          onSelect={setSelectedId}
          onFilterStatus={handleFilterStatus}
          onFilterTipe={handleFilterTipe}
          onSort={setSortBy}
        />

        <IncidentDetailPanel
          incident={selectedIncident}
          onStatusUpdate={handleStatusUpdate}
          onAssign={handleAssign}
          onToggleBriefing={handleToggleBriefing}
          onResolve={handleResolve}
          onEscalate={handleEscalate}
        />
      </div>
    </div>
  )
}
