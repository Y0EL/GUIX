import { useState, useEffect, useCallback, useRef } from 'react'
import type { Profil, Kasus, Lokasi, Postingan, SearchResult } from '../types'

type Datasets = {
  profil: Profil[]
  kasus: Kasus[]
  lokasi: Lokasi[]
  postingan: Postingan[]
}

const RECENT_KEY = 'h5_recent_searches'
const RECENT_MAX = 8

/** Wrap substring match dengan <mark> */
export function highlightMatch(text: string, query: string): string {
  if (!query || !text) return text
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const re = new RegExp(`(${escaped})`, 'gi')
  return text.replace(re, '<mark>$1</mark>')
}

/** Cek apakah string mengandung query (case-insensitive) */
function match(value: unknown, q: string): boolean {
  if (value === null || value === undefined) return false
  if (Array.isArray(value)) return value.some(v => match(v, q))
  return String(value).toLowerCase().includes(q)
}

/** Cari di semua dataset dan return hasil terurut */
export function searchAll(query: string, datasets: Datasets): SearchResult[] {
  const q = query.toLowerCase().trim()
  if (q.length < 2) return []

  const results: SearchResult[] = []

  /* Profil */
  for (const p of datasets.profil) {
    const fields = ['nama_lengkap', 'id_profil', 'kota', 'provinsi', 'bio', 'tag_risiko'] as const
    const matched = fields.filter(f => match(p[f], q))
    // Juga match di tautan_kasus.id_kasus
    const kasusMatch = p.tautan_kasus.some(t => t.id_kasus.toLowerCase().includes(q))
    if (kasusMatch && !matched.includes('id_profil')) matched.push('tautan_kasus' as never)
    if (matched.length > 0) {
      results.push({
        tipe: 'profil',
        id: p.id_profil,
        matchScore: matched.length,
        matchedFields: matched,
        data: p,
      })
    }
  }

  /* Kasus */
  for (const k of datasets.kasus) {
    const fields = ['id_kasus', 'judul', 'tipe_kasus', 'status', 'kota', 'provinsi'] as const
    const matched = fields.filter(f => match(k[f], q))
    if (matched.length > 0) {
      results.push({
        tipe: 'kasus',
        id: k.id_kasus,
        matchScore: matched.length,
        matchedFields: matched,
        data: k,
      })
    }
  }

  /* Lokasi */
  for (const l of datasets.lokasi) {
    const fields = ['label', 'kota', 'provinsi', 'tipe_lokasi'] as const
    const matched = fields.filter(f => match(l[f], q))
    if (matched.length > 0) {
      results.push({
        tipe: 'lokasi',
        id: l.id_lokasi,
        matchScore: matched.length,
        matchedFields: matched,
        data: l,
      })
    }
  }

  /* Postingan */
  for (const p of datasets.postingan) {
    const fields = ['konten', 'platform', 'id_profil', 'kota'] as const
    const matched = fields.filter(f => match(p[f], q))
    const hashMatch = p.hashtag.some(h => h.toLowerCase().includes(q))
    const kwMatch = p.kata_kunci.some(k => k.toLowerCase().includes(q))
    if (hashMatch) matched.push('hashtag' as never)
    if (kwMatch && !matched.includes('kata_kunci' as never)) matched.push('kata_kunci' as never)
    if (matched.length > 0) {
      results.push({
        tipe: 'postingan',
        id: p.id_posting,
        matchScore: matched.length,
        matchedFields: matched,
        data: p,
      })
    }
  }

  return results.sort((a, b) => b.matchScore - a.matchScore)
}

/** Sort by terbaru — pakai field waktu dari data */
function sortByTerbaru(results: SearchResult[]): SearchResult[] {
  return [...results].sort((a, b) => {
    const getWaktu = (r: SearchResult): string => {
      const d = r.data as Record<string, unknown>
      return String(d.timestamp ?? d.dibuat_pada ?? d.waktu_insiden ?? d.diamati_pada ?? '')
    }
    return getWaktu(b).localeCompare(getWaktu(a))
  })
}

/* ── Recent searches ── */

export function loadRecentSearches(): string[] {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) ?? '[]')
  } catch { return [] }
}

export function saveRecentSearch(query: string): void {
  const prev = loadRecentSearches().filter(q => q !== query)
  localStorage.setItem(RECENT_KEY, JSON.stringify([query, ...prev].slice(0, RECENT_MAX)))
}

export function removeRecentSearch(query: string): string[] {
  const next = loadRecentSearches().filter(q => q !== query)
  localStorage.setItem(RECENT_KEY, JSON.stringify(next))
  return next
}

/* ── Hook utama ── */

export type FilterTipe = 'all' | 'profil' | 'kasus' | 'lokasi' | 'postingan'
export type SortMode = 'relevansi' | 'terbaru'

interface UseSearchResult {
  query: string
  setQuery: (q: string) => void
  isSearching: boolean
  results: SearchResult[]
  filteredResults: SearchResult[]
  activeFilter: FilterTipe
  setActiveFilter: (f: FilterTipe) => void
  sortMode: SortMode
  setSortMode: (s: SortMode) => void
  recentSearches: string[]
  removeRecent: (q: string) => void
  confirmSearch: (q: string) => void
  counts: Record<FilterTipe, number>
}

export function useSearch(datasets: Datasets): UseSearchResult {
  const [query, setQueryRaw] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [results, setResults] = useState<SearchResult[]>([])
  const [activeFilter, setActiveFilter] = useState<FilterTipe>('all')
  const [sortMode, setSortMode] = useState<SortMode>('relevansi')
  const [recentSearches, setRecentSearches] = useState<string[]>(loadRecentSearches)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const datasetsRef = useRef(datasets)
  datasetsRef.current = datasets

  function setQuery(q: string) {
    setQueryRaw(q)
    setIsSearching(q.trim().length >= 2)
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      setDebouncedQuery(q)
      setIsSearching(false)
    }, 300)
  }

  useEffect(() => {
    const r = searchAll(debouncedQuery, datasetsRef.current)
    setResults(sortMode === 'terbaru' ? sortByTerbaru(r) : r)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQuery, sortMode])

  function confirmSearch(q: string) {
    if (q.trim().length >= 2) {
      saveRecentSearch(q.trim())
      setRecentSearches(loadRecentSearches())
    }
  }

  const removeRecent = useCallback((q: string) => {
    setRecentSearches(removeRecentSearch(q))
  }, [])

  const filteredResults =
    activeFilter === 'all' ? results : results.filter(r => r.tipe === activeFilter)

  const counts: Record<FilterTipe, number> = {
    all: results.length,
    profil:    results.filter(r => r.tipe === 'profil').length,
    kasus:     results.filter(r => r.tipe === 'kasus').length,
    lokasi:    results.filter(r => r.tipe === 'lokasi').length,
    postingan: results.filter(r => r.tipe === 'postingan').length,
  }

  return {
    query, setQuery, isSearching,
    results, filteredResults,
    activeFilter, setActiveFilter,
    sortMode, setSortMode,
    recentSearches, removeRecent, confirmSearch,
    counts,
  }
}
