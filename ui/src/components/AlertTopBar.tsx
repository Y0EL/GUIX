import { ChevronLeft, ShieldAlert, AlertTriangle, Info } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { Peringatan } from '../types'

type Props = {
  peringatan: Peringatan[]
}

export default function AlertTopBar({ peringatan }: Props) {
  const nav = useNavigate()

  const kritis = peringatan.filter(p => p.tingkat_keparahan === 'tinggi').length
  const menengah = peringatan.filter(p => p.tingkat_keparahan === 'menengah').length
  const rendah = peringatan.filter(p => p.tingkat_keparahan === 'rendah').length

  return (
    <div className="ac-topbar">
      <button className="ac-back-btn" onClick={() => nav('/')}>
        <ChevronLeft size={13} />
        Kembali
      </button>

      <div className="ac-breadcrumb">
        Alert Center
        <span>— Triage &amp; Eskalasi</span>
      </div>

      <div className="ac-summary-stats">
        {kritis > 0 && (
          <div className="ac-stat-pill kritis">
            <ShieldAlert size={11} />
            {kritis} Kritis
          </div>
        )}
        {menengah > 0 && (
          <div className="ac-stat-pill menengah">
            <AlertTriangle size={11} />
            {menengah} Menengah
          </div>
        )}
        {rendah > 0 && (
          <div className="ac-stat-pill rendah">
            <Info size={11} />
            {rendah} Rendah
          </div>
        )}
        <div className="ac-stat-pill total">
          {peringatan.length} Total
        </div>
      </div>
    </div>
  )
}
