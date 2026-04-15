import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Radio } from 'lucide-react'
import type { Kasus } from '../types'
import { formatTanggal } from '../utils'

type Props = { kasus: Kasus[] }

export default function PanelKasus({ kasus }: Props) {
  const [idx, setIdx] = useState(0)
  const posRef = useRef({ x: 18, y: window.innerHeight - 260 })
  const [pos, setPos] = useState(posRef.current)
  const drag = useRef({ aktif: false, ox: 0, oy: 0 })

  /* Rotasi otomatis */
  useEffect(() => {
    if (!kasus.length) return
    const t = setInterval(() => setIdx(p => (p + 1) % kasus.length), 12000)
    return () => clearInterval(t)
  }, [kasus.length])

  /* Drag */
  useEffect(() => {
    function onMove(e: MouseEvent) {
      if (!drag.current.aktif) return
      setPos({
        x: Math.max(0, Math.min(window.innerWidth - 344, e.clientX - drag.current.ox)),
        y: Math.max(0, Math.min(window.innerHeight - 120, e.clientY - drag.current.oy)),
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

  const aktif = kasus[idx]

  return (
    <section className="panel-info" style={{ left: pos.x, top: pos.y }}>
      <div className="panel-header" onMouseDown={mulaiGeser}>
        <Radio size={12} className="pulse-icon" />
        <span>Kasus Aktif</span>
        <span className="drag-hint">⋮⋮</span>
      </div>
      <AnimatePresence mode="wait">
        {aktif && (
          <motion.div
            key={aktif.id_kasus}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.3 }}
            className="panel-konten"
          >
            <h3>{aktif.judul}</h3>
            <div className="panel-tags">
              <span className="tag">{aktif.tipe_kasus}</span>
              <span className="tag">{aktif.kota}, {aktif.provinsi}</span>
              <span className="tag">{aktif.status}</span>
            </div>
            <div className="panel-sub">
              <span>{aktif.jumlah_aktor} aktor</span>
              <span>{formatTanggal(aktif.waktu_insiden)}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  )
}
