import { ChevronLeft, ChevronRight, ShieldAlert, Search, Activity, CheckCircle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { IncidentWithMeta } from '../types'

type Props = { incidents: IncidentWithMeta[] }

export default function IncidentTopBar({ incidents }: Props) {
  const nav = useNavigate()

  const total = incidents.length
  const kritis = incidents.filter(i => i.skor?.label_risiko === 'tinggi').length
  const diAnalisis = incidents.filter(i => i.runtimeStatus === 'analisis').length
  const selesai = incidents.filter(i => i.runtimeStatus === 'selesai').length

  return (
    <div className="iq-topbar">
      <button className="iq-back-btn" onClick={() => nav('/alert-center')}>
        <ChevronLeft size={13} />
        Alert Center
      </button>

      <div className="iq-breadcrumb">
        Incident Queue
        <span>— Manajemen Insiden Aktif</span>
      </div>

      <div className="ac-summary-stats">
        <div className="ac-stat-pill total">
          {total} Insiden
        </div>
        {kritis > 0 && (
          <div className="ac-stat-pill kritis">
            <ShieldAlert size={11} />
            {kritis} Risiko Tinggi
          </div>
        )}
        {diAnalisis > 0 && (
          <div className="ac-stat-pill menengah">
            <Search size={11} />
            {diAnalisis} Analisis
          </div>
        )}
        <div className="ac-stat-pill" style={{ background: 'rgba(76,175,80,.08)', borderColor: 'rgba(76,175,80,.2)', color: 'rgba(129,199,132,.6)' }}>
          <CheckCircle size={11} />
          {selesai} Selesai
        </div>
      </div>

      <div className="iq-next-hint">
        <Activity size={10} />
        Map Intel
        <ChevronRight size={10} />
      </div>
    </div>
  )
}
