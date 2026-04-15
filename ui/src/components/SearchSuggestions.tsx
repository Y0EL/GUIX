import { useEffect, useState } from 'react'
import { Search } from 'lucide-react'

type Skenario = {
  id: string
  label: string
  warna: string
  warnaGlow: string
  terms: string[]
  intervalMs: number
}

const SKENARIO: Skenario[] = [
  {
    id: 'kebakaran',
    label: 'Kebakaran Gudang · Bekasi',
    warna: '#E5282A',
    warnaGlow: 'rgba(229,40,42,.15)',
    terms: ['kebakaran', 'Bekasi', 'gudang logistik', 'sabotase', 'klaster-1', 'aktor_teramati'],
    intervalMs: 3000,
  },
  {
    id: 'pendanaan',
    label: 'Pendanaan Mencurigakan · Jakarta',
    warna: '#F5A623',
    warnaGlow: 'rgba(245,166,35,.15)',
    terms: ['pendanaan', 'Jakarta', 'finansial', 'klaster-2', 'koordinasi'],
    intervalMs: 4000,
  },
  {
    id: 'propaganda',
    label: 'Propaganda Burst · Cikarang',
    warna: '#818cf8',
    warnaGlow: 'rgba(129,140,248,.15)',
    terms: ['propaganda', 'Cikarang', 'narasi', 'klaster-3', 'amplifikasi'],
    intervalMs: 5000,
  },
]

type Props = {
  onSelect: (term: string) => void
}

function SkenarioChips({ skenario, onSelect }: { skenario: Skenario; onSelect: (t: string) => void }) {
  const [activeIdx, setActiveIdx] = useState(0)

  useEffect(() => {
    const t = setInterval(() => {
      setActiveIdx(i => (i + 1) % skenario.terms.length)
    }, skenario.intervalMs)
    return () => clearInterval(t)
  }, [skenario.intervalMs, skenario.terms.length])

  return (
    <div className="sg-skenario-card">
      <div className="sg-skenario-label" style={{ color: skenario.warna, borderColor: skenario.warna + '44' }}>
        <span className="sg-skenario-dot" style={{ background: skenario.warna }} />
        {skenario.label}
      </div>
      <div className="sg-chips">
        {skenario.terms.map((term, i) => (
          <button
            key={term}
            className={`sg-chip ${i === activeIdx ? 'aktif' : ''}`}
            style={i === activeIdx ? {
              background: skenario.warnaGlow,
              borderColor: skenario.warna + '88',
              color: skenario.warna,
            } : {}}
            onClick={() => onSelect(term)}
          >
            <Search size={9} />
            {term}
          </button>
        ))}
      </div>
    </div>
  )
}

export default function SearchSuggestions({ onSelect }: Props) {
  return (
    <div className="sg-wrap">
      <div className="sg-title">Skenario aktif — klik untuk cari</div>
      <div className="sg-grid">
        {SKENARIO.map(s => (
          <SkenarioChips key={s.id} skenario={s} onSelect={onSelect} />
        ))}
      </div>
    </div>
  )
}
