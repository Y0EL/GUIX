import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Newspaper } from 'lucide-react'
import type { Berita } from '../types'
import { formatTanggal } from '../utils'

type Props = { berita: Berita[] }

export default function PanelBerita({ berita }: Props) {
  const [idx, setIdx] = useState(0)
  const [pos, setPos] = useState({ x: window.innerWidth - 362, y: window.innerHeight - 240 })
  const drag = useRef({ aktif: false, ox: 0, oy: 0 })

  /* Rotasi otomatis */
  useEffect(() => {
    if (!berita.length) return
    const t = setInterval(() => setIdx(p => (p + 1) % berita.length), 15000)
    return () => clearInterval(t)
  }, [berita.length])

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

  const aktif = berita[idx]

  return (
    <section className="panel-info" style={{ left: pos.x, top: pos.y }}>
      <div className="panel-header" onMouseDown={mulaiGeser}>
        <Newspaper size={12} />
        <span>Intelijen Berita</span>
        <span className="drag-hint">⋮⋮</span>
      </div>
      <AnimatePresence mode="wait">
        {aktif && (
          <motion.div
            key={aktif.id}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.3 }}
            className="panel-konten"
          >
            <h3>{aktif.judul}</h3>
            <div className="panel-tags">
              <span className="tag">{aktif.kategori}</span>
              <span className="tag">{aktif.lokasi}</span>
            </div>
            <div className="panel-sub">
              <span>{formatTanggal(aktif.published_at)}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  )
}
