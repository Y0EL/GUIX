import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'

import AlertTopBar from '../components/AlertTopBar'
import AlertListPanel from '../components/AlertListPanel'
import AlertDetailPanel from '../components/AlertDetailPanel'
import AlertInsightPanel from '../components/AlertInsightPanel'

import type { Peringatan, Kasus, AlertWithTriage, GroupMode, TriageStatus, SkorRisiko, Entitas, Lokasi } from '../types'
import { muatJson } from '../utils'
import { useArrowNav } from '../hooks/useArrowNav'

export default function AlertCenter() {
  useArrowNav()
  const [peringatan, setPeringatan] = useState<Peringatan[]>([])
  const [kasus, setKasus] = useState<Kasus[]>([])
  const [skorRisiko, setSkorRisiko] = useState<SkorRisiko[]>([])
  const [entitas, setEntitas] = useState<Entitas[]>([])
  const [lokasi, setLokasi] = useState<Lokasi[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  /* Triage state — keyed by id_peringatan */
  const [triageMap, setTriageMap] = useState<Record<string, {
    status: TriageStatus
    note?: string
    tags?: string[]
    assignee?: string
  }>>({})

  /* UI state */
  const [selected, setSelected] = useState<string | null>(null)
  const [filterSeverity, setFilterSeverity] = useState<string[]>([])
  const [filterTipe] = useState<string[]>([])
  const [groupMode, setGroupMode] = useState<GroupMode>('kasus')

  /* Load data */
  useEffect(() => {
    async function muat() {
      try {
        const [pData, kData, srData, entData, lokData] = await Promise.all([
          muatJson<Peringatan[]>('/data/peringatan.json'),
          muatJson<Kasus[]>('/data/kasus.json'),
          muatJson<SkorRisiko[]>('/data/skor_risiko.json'),
          muatJson<Entitas[]>('/data/entitas.json'),
          muatJson<Lokasi[]>('/data/lokasi.json'),
        ])
        setPeringatan(pData)
        setKasus(kData)
        setSkorRisiko(srData)
        setEntitas(entData)
        setLokasi(lokData)
        // Auto-select first alert
        if (pData.length > 0) setSelected(pData[0].id_peringatan)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Gagal memuat data')
      } finally {
        setLoading(false)
      }
    }
    muat()
  }, [])

  /* Merge triage state into alerts */
  const alertsWithTriage = useMemo<AlertWithTriage[]>(
    () =>
      peringatan.map(p => ({
        ...p,
        triage: triageMap[p.id_peringatan]?.status ?? 'baru',
        note: triageMap[p.id_peringatan]?.note,
        tags: triageMap[p.id_peringatan]?.tags,
        assignee: triageMap[p.id_peringatan]?.assignee,
      })),
    [peringatan, triageMap],
  )

  const selectedAlert = alertsWithTriage.find(a => a.id_peringatan === selected) ?? null

  /* Triage action handlers */
  function handleTriage(id: string, status: TriageStatus) {
    setTriageMap(prev => ({
      ...prev,
      [id]: { ...prev[id], status },
    }))
  }

  function handleNote(id: string, note: string) {
    setTriageMap(prev => ({
      ...prev,
      [id]: { ...prev[id], note },
    }))
  }

  function handleTag(id: string, tag: string) {
    setTriageMap(prev => {
      const existing = prev[id]?.tags ?? []
      if (existing.includes(tag)) return prev
      return {
        ...prev,
        [id]: { ...prev[id], tags: [...existing, tag] },
      }
    })
  }

  function handleToggleSeverity(s: string) {
    setFilterSeverity(prev =>
      prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s],
    )
  }

  if (loading) {
    return (
      <div className="halaman-alert" style={{ display: 'grid', placeContent: 'center' }}>
        <div className="overlay-tengah" style={{ position: 'relative', background: 'none' }}>
          <div className="spinner" />
          <h1>Memuat Alert Center...</h1>
          <p>Mengambil data peringatan</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="halaman-alert" style={{ display: 'grid', placeContent: 'center' }}>
        <div className="overlay-tengah overlay-error" style={{ position: 'relative', background: 'none' }}>
          <AlertTriangle size={36} />
          <h1>Gagal Memuat Data</h1>
          <p>{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="halaman-alert">
      <AlertTopBar peringatan={peringatan} />

      <div className="ac-body">
        <AlertListPanel
          alerts={alertsWithTriage}
          kasus={kasus}
          selected={selected}
          groupMode={groupMode}
          filterSeverity={filterSeverity}
          filterTipe={filterTipe}
          onSelect={setSelected}
          onGroupMode={setGroupMode}
          onToggleSeverity={handleToggleSeverity}
        />

        <AlertDetailPanel
          alert={selectedAlert}
          kasus={kasus}
          skorRisiko={skorRisiko}
          entitas={entitas}
          onTriage={handleTriage}
          onNote={handleNote}
          onTag={handleTag}
        />

        <AlertInsightPanel
          alerts={alertsWithTriage}
          kasus={kasus}
          skorRisiko={skorRisiko}
          lokasi={lokasi}
        />
      </div>

      {/* Footer nav hint */}
      <div style={{
        flexShrink: 0, display: 'flex', justifyContent: 'flex-end',
        padding: '6px 16px', borderTop: '1px solid rgba(179,24,24,.06)',
        background: 'rgba(4,1,1,.5)',
      }}>
        <Link to="/incident-queue" className="nav-ac-link">
          Incident Queue
          <ChevronRight size={10} />
        </Link>
      </div>
    </div>
  )
}
