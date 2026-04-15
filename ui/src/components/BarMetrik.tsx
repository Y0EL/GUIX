import { useEffect, useRef, useState } from 'react'
import { Shield, Activity, Users, MapPin, AlertTriangle } from 'lucide-react'
import type { MetrikData } from '../types'

function useAngkaAnimasi(target: number, durasi = 1200): number {
  const [nilai, setNilai] = useState(0)
  useEffect(() => {
    let id = 0
    const mulai = performance.now()
    function langkah(t: number) {
      const p = Math.min((t - mulai) / durasi, 1)
      setNilai(Math.round((1 - Math.pow(1 - p, 3)) * target))
      if (p < 1) id = requestAnimationFrame(langkah)
    }
    id = requestAnimationFrame(langkah)
    return () => cancelAnimationFrame(id)
  }, [target, durasi])
  return nilai
}

/* Subjek: hitung naik 1 per detik \u2014 efek boot sequence */
function useHitungNaik(target: number): number {
  const [nilai, setNilai] = useState(0)
  const ref = useRef(0)
  useEffect(() => {
    ref.current = 0
    setNilai(0)
    if (target <= 0) return
    const t = setInterval(() => {
      ref.current = ref.current + 1
      setNilai(ref.current)
      if (ref.current >= target) clearInterval(t)
    }, 1000)
    return () => clearInterval(t)
  }, [target])
  return Math.min(nilai, target)
}

type Props = { metrik: MetrikData }

export default function BarMetrik({ metrik }: Props) {
  /* Simulasi fluktuasi live — tiap 30–60 detik angka berubah ±1 */
  const [delta, setDelta] = useState({ kritis: 0, tinggi: 0, sedang: 0 })

  useEffect(() => {
    function fluktuasi() {
      setDelta({
        kritis: Math.floor(Math.random() * 3) - 1,
        tinggi: Math.floor(Math.random() * 3) - 1,
        sedang: Math.floor(Math.random() * 3) - 1,
      })
    }
    const interval = 30000 + Math.random() * 30000
    const t = setTimeout(function tick() {
      fluktuasi()
      setTimeout(tick, 30000 + Math.random() * 30000)
    }, interval)
    return () => clearTimeout(t)
  }, [])

  const kritis  = useAngkaAnimasi(Math.max(0, metrik.kritis  + delta.kritis))
  const tinggi  = useAngkaAnimasi(Math.max(0, metrik.tinggi  + delta.tinggi))
  const sedang  = useAngkaAnimasi(Math.max(0, metrik.sedang  + delta.sedang))
  const subjek  = useHitungNaik(metrik.subjek)
  const wilayah = useAngkaAnimasi(metrik.wilayah)

  return (
    <section className="bar-metrik">
      <article className="m-item bahaya">
        <Shield size={13} />
        <div><span>KRITIS</span><strong>{kritis}</strong></div>
      </article>
      <article className="m-item peringatan">
        <AlertTriangle size={13} />
        <div><span>TINGGI</span><strong>{tinggi}</strong></div>
      </article>
      <article className="m-item">
        <Activity size={13} />
        <div><span>SEDANG</span><strong>{sedang}</strong></div>
      </article>
      <article className="m-item">
        <Users size={13} />
        <div><span>SUBJEK</span><strong>{subjek}</strong></div>
      </article>
      <article className="m-item">
        <MapPin size={13} />
        <div><span>WILAYAH</span><strong>{wilayah}</strong></div>
      </article>
    </section>
  )
}
