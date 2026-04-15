import { useEffect, useMemo, useState, useRef } from 'react'
import { AlertTriangle } from 'lucide-react'

import SearchTopBar from '../components/SearchTopBar'
import SearchBar from '../components/SearchBar'
import SearchFilterBar from '../components/SearchFilterBar'
import SearchResultsPanel from '../components/SearchResultsPanel'
import SearchSuggestions from '../components/SearchSuggestions'
import SkeletonResults from '../components/SkeletonResults'
import PanelPetaLokasi from '../components/PanelPetaLokasi'

import { useSearch, saveRecentSearch } from '../hooks/useSearch'
import { useArrowNav } from '../hooks/useArrowNav'
import { muatJson } from '../utils'

import type { Profil, Kasus, Lokasi, Postingan, Pertemanan } from '../types'

export default function SearchDiscovery() {
  useArrowNav()

  const [profil, setProfil] = useState<Profil[]>([])
  const [kasus, setKasus] = useState<Kasus[]>([])
  const [lokasi, setLokasi] = useState<Lokasi[]>([])
  const [postingan, setPostingan] = useState<Postingan[]>([])
  const [pertemanan, setPertemanan] = useState<Pertemanan[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showSkeleton, setShowSkeleton] = useState(false)
  const skeletonTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Panel peta lokasi
  const [lokasiDipilih, setLokasiDipilih] = useState<Lokasi | null>(null)

  useEffect(() => {
    async function muat() {
      try {
        const [pData, kData, lData, postData, pertData] = await Promise.all([
          muatJson<Profil[]>('/data/profil.json'),
          muatJson<Kasus[]>('/data/kasus.json'),
          muatJson<Lokasi[]>('/data/lokasi.json'),
          muatJson<Postingan[]>('/data/postingan.json'),
          muatJson<Pertemanan[]>('/data/pertemanan.json'),
        ])
        setProfil(pData)
        setKasus(kData)
        setLokasi(lData)
        setPostingan(postData)
        setPertemanan(pertData)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Gagal memuat data')
      } finally {
        setLoading(false)
      }
    }
    muat()
  }, [])

  const search = useSearch({ profil, kasus, lokasi, postingan })

  // Precompute koneksi count per profil dari pertemanan
  const koneksiPerProfil = useMemo(() => {
    const m = new Map<string, number>()
    pertemanan.forEach(p => {
      m.set(p.profil_a, (m.get(p.profil_a) ?? 0) + 1)
      m.set(p.profil_b, (m.get(p.profil_b) ?? 0) + 1)
    })
    return m
  }, [pertemanan])

  // Map id_kasus → judul untuk ProfilCard
  const kasusMap = useMemo(() =>
    Object.fromEntries(kasus.map(k => [k.id_kasus, k.judul])),
  [kasus])

  // Skeleton demo effect: tampilkan 600ms saat query berubah >= 2 chars
  useEffect(() => {
    const q = search.query.trim()
    if (q.length >= 2) {
      setShowSkeleton(true)
      skeletonTimer.current = setTimeout(() => setShowSkeleton(false), 600)
    } else {
      setShowSkeleton(false)
    }
    return () => {
      if (skeletonTimer.current) clearTimeout(skeletonTimer.current)
    }
  }, [search.query])

  function handleConfirm(q: string) {
    saveRecentSearch(q)
    search.confirmSearch(q)
  }

  function handleClear() {
    search.setQuery('')
    search.setActiveFilter('all')
  }

  function handleRecentClick(q: string) {
    search.setQuery(q)
    handleConfirm(q)
  }

  if (loading) {
    return (
      <div className="halaman-sd" style={{ display: 'grid', placeContent: 'center' }}>
        <div className="overlay-tengah" style={{ position: 'relative', background: 'none' }}>
          <div className="spinner" />
          <h1>Memuat Search & Discovery...</h1>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="halaman-sd" style={{ display: 'grid', placeContent: 'center' }}>
        <div className="overlay-tengah overlay-error" style={{ position: 'relative', background: 'none' }}>
          <AlertTriangle size={36} />
          <h1>Gagal Memuat Data</h1>
          <p>{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="halaman-sd">
      <SearchTopBar query={search.query} counts={search.counts} />

      <div className="sd-search-area">
        <SearchBar
          query={search.query}
          isSearching={search.isSearching}
          onChange={search.setQuery}
          onConfirm={handleConfirm}
          onClear={handleClear}
        />
        <SearchFilterBar
          activeFilter={search.activeFilter}
          sortMode={search.sortMode}
          counts={search.counts}
          hasQuery={search.query.trim().length >= 2}
          onFilter={search.setActiveFilter}
          onSort={search.setSortMode}
        />
      </div>

      {showSkeleton ? (
        <SkeletonResults />
      ) : (
        <SearchResultsPanel
          results={search.filteredResults}
          query={search.query}
          activeFilter={search.activeFilter}
          recentSearches={search.recentSearches}
          onRecentClick={handleRecentClick}
          onRemoveRecent={search.removeRecent}
          koneksiPerProfil={koneksiPerProfil}
          kasusMap={kasusMap}
          onLokasiClick={setLokasiDipilih}
          initialContent={
            <SearchSuggestions onSelect={q => {
              search.setQuery(q)
              handleConfirm(q)
            }} />
          }
        />
      )}

      {/* Panel peta lokasi — slide-in dari kanan */}
      {lokasiDipilih && (
        <PanelPetaLokasi
          lokasi={lokasiDipilih}
          onClose={() => setLokasiDipilih(null)}
        />
      )}

      <div className="sd-footer">
        <span>← Map Intelligence</span>
        <span className="sd-footer-current">Search & Discovery</span>
        <span>Link Analysis →</span>
      </div>
    </div>
  )
}
