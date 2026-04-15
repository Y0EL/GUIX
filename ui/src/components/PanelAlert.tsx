import { useEffect, useRef, useState } from 'react'
import { Bell, CheckCheck, ChevronUp, Info, ShieldAlert } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import type { Peringatan } from '../types'

type Props = { peringatan: Peringatan[] }

const LEVEL_CONFIG = {
  tinggi:   { label: 'KRITIS', warna: '#DC2626', bg: 'rgba(220,38,38,0.12)', Ikon: ShieldAlert },
  menengah: { label: 'PERINGATAN', warna: '#F97316', bg: 'rgba(249,115,22,0.10)', Ikon: ChevronUp },
  rendah:   { label: 'INFO', warna: '#3B82F6', bg: 'rgba(59,130,246,0.08)', Ikon: Info },
}

export default function PanelAlert({ peringatan }: Props) {
  const [pos, setPos] = useState(() => ({ x: window.innerWidth - 362, y: 70 }))
  const [acked, setAcked] = useState<Set<string>>(new Set())
  const drag = useRef({ aktif: false, ox: 0, oy: 0 })

  useEffect(() => {
    function onMove(e: MouseEvent) {
      if (!drag.current.aktif) return
      setPos({
        x: Math.max(0, Math.min(window.innerWidth - 344, e.clientX - drag.current.ox)),
        y: Math.max(0, Math.min(window.innerHeight - 80, e.clientY - drag.current.oy)),
      })
    }
    function onUp() { drag.current.aktif = false }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [])

  function mulaiGeser(e: React.MouseEvent<HTMLElement>) {
    e.preventDefault()
    drag.current = { aktif: true, ox: e.clientX - pos.x, oy: e.clientY - pos.y }
  }

  function acknowledge(id: string) {
    setAcked(prev => new Set([...prev, id]))
  }

  /* Urutkan: tinggi dulu lalu menengah lalu rendah */
  const urutan = { tinggi: 0, menengah: 1, rendah: 2 }
  const tampil = peringatan
    .filter(p => !acked.has(p.id_peringatan))
    .sort((a, b) => urutan[a.tingkat_keparahan] - urutan[b.tingkat_keparahan])

  const jumlahKritis = tampil.filter(p => p.tingkat_keparahan === 'tinggi').length

  return (
    <aside className="panel-info panel-alert" style={{ left: pos.x, top: pos.y }}>
      <div className="panel-header" onMouseDown={mulaiGeser}>
        <Bell size={12} className={jumlahKritis > 0 ? 'pulse-icon' : ''} />
        <span>Triage Alert</span>
        {jumlahKritis > 0 && (
          <span className="alert-badge-kritis">{jumlahKritis}</span>
        )}
        <span className="drag-hint">⋮⋮</span>
      </div>

      <div className="alert-list">
        <AnimatePresence>
          {tampil.length === 0 && (
            <motion.div
              key="bersih"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="alert-bersih"
            >
              <CheckCheck size={14} />
              <span>Semua alert telah di-acknowledge</span>
            </motion.div>
          )}
          {tampil.map(p => {
            const cfg = LEVEL_CONFIG[p.tingkat_keparahan]
            const Ikon = cfg.Ikon
            return (
              <motion.div
                key={p.id_peringatan}
                layout
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20, height: 0, padding: 0, margin: 0 }}
                transition={{ duration: 0.25 }}
                className="alert-item"
                style={{ background: cfg.bg, borderLeft: `3px solid ${cfg.warna}` }}
              >
                <div className="alert-item-header">
                  <Ikon size={11} style={{ color: cfg.warna, flexShrink: 0 }} />
                  <span className="alert-level" style={{ color: cfg.warna }}>{cfg.label}</span>
                  <span className="alert-sinyal">{p.tipe_sinyal.replace(/_/g, ' ')}</span>
                  <button
                    className="alert-ack-btn"
                    title="Acknowledge"
                    onClick={() => acknowledge(p.id_peringatan)}
                  >✕</button>
                </div>
                <p className="alert-deskripsi">{p.deskripsi}</p>
                <div className="alert-meta">
                  <span>Kasus: {p.id_kasus}</span>
                  <span>{Math.round(p.kepercayaan * 100)}% kepercayaan</span>
                </div>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </aside>
  )
}
