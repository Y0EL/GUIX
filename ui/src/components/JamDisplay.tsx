import { useEffect, useState } from 'react'
import { waktuJam, tanggalHariIni } from '../utils'

export default function JamDisplay() {
  const [waktu, setWaktu] = useState(waktuJam)

  useEffect(() => {
    const t = setInterval(() => setWaktu(waktuJam()), 1000)
    return () => clearInterval(t)
  }, [])

  return (
    <section className="jam-display">
      <strong>{waktu}</strong>
      <span>{tanggalHariIni()}</span>
    </section>
  )
}
