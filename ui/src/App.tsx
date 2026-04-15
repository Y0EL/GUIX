import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import Overview from './halaman/Overview'
import AlertCenter from './halaman/AlertCenter'
import IncidentQueue from './halaman/IncidentQueue'
import MapIntelligence from './halaman/MapIntelligence'
import SearchDiscovery from './halaman/SearchDiscovery'
import LinkAnalysis from './halaman/LinkAnalysis'
import Timeline from './halaman/Timeline'
import KanvasInvestigasi from './halaman/KanvasInvestigasi'

const JUDUL_HALAMAN: Record<string, string> = {
  '/':               'Ikhtisar — UIX',
  '/alert-center':   'Pusat Peringatan — UIX',
  '/incident-queue': 'Antrean Insiden — UIX',
  '/map-intelligence': 'Intelijen Peta — UIX',
  '/search':         'Pencarian & Penemuan — UIX',
  '/timeline':       'Timeline Kejadian — UIX',
  '/canvas':         'Kanvas Investigasi — UIX',
}

function PengaturJudul() {
  const loc = useLocation()
  useEffect(() => {
    document.title = JUDUL_HALAMAN[loc.pathname] ?? 'UIX — Sistem Intelijen Operasional'
  }, [loc.pathname])
  return null
}

export default function App() {
  return (
    <BrowserRouter>
      <PengaturJudul />
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/alert-center" element={<AlertCenter />} />
        <Route path="/incident-queue" element={<IncidentQueue />} />
        <Route path="/map-intelligence" element={<MapIntelligence />} />
        <Route path="/search" element={<SearchDiscovery />} />
        <Route path="/link-analysis" element={<LinkAnalysis />} />
        <Route path="/timeline" element={<Timeline />} />
        <Route path="/canvas" element={<KanvasInvestigasi />} />
      </Routes>
    </BrowserRouter>
  )
}
