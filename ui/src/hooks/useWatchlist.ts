/**
 * useWatchlist — localStorage-backed watchlist untuk profil dan kasus.
 * Data disimpan di key "uix_watchlist" di localStorage.
 */
import { useCallback, useEffect, useState } from 'react'

export type WatchlistTipe = 'profil' | 'kasus'

export type WatchlistItem = {
  id: string
  tipe: WatchlistTipe
  label: string        // nama/judul untuk display
  addedAt: number      // timestamp ms
}

const STORAGE_KEY = 'uix_watchlist'

function load(): WatchlistItem[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    return JSON.parse(raw) as WatchlistItem[]
  } catch {
    return []
  }
}

function save(items: WatchlistItem[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  } catch { /* quota exceeded etc */ }
}

export function useWatchlist() {
  const [items, setItems] = useState<WatchlistItem[]>(load)

  /* Sync ke localStorage setiap ada perubahan */
  useEffect(() => { save(items) }, [items])

  const add = useCallback((item: Omit<WatchlistItem, 'addedAt'>) => {
    setItems(prev => {
      if (prev.some(w => w.id === item.id)) return prev   // sudah ada
      return [{ ...item, addedAt: Date.now() }, ...prev]
    })
  }, [])

  const remove = useCallback((id: string) => {
    setItems(prev => prev.filter(w => w.id !== id))
  }, [])

  const toggle = useCallback((item: Omit<WatchlistItem, 'addedAt'>) => {
    setItems(prev => {
      if (prev.some(w => w.id === item.id)) {
        return prev.filter(w => w.id !== item.id)
      }
      return [{ ...item, addedAt: Date.now() }, ...prev]
    })
  }, [])

  const isWatched = useCallback(
    (id: string) => items.some(w => w.id === id),
    [items],
  )

  const clear = useCallback(() => setItems([]), [])

  return { items, add, remove, toggle, isWatched, clear }
}
