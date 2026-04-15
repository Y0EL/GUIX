import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

/** Urutan halaman — tambahkan rute baru di sini sesuai urutan implementasi */
const URUTAN: string[] = [
  '/',
  '/alert-center',
  '/incident-queue',
  '/map-intelligence',
  '/search',
  '/timeline',
  '/narrative',
  '/canvas',
]

/**
 * Navigasi antar halaman dengan ← → arrow keys.
 * Diabaikan bila fokus ada di input/textarea/select/contenteditable.
 */
export function useArrowNav() {
  const nav = useNavigate()

  useEffect(() => {
    function handler(e: KeyboardEvent) {
      // Jangan intercept kalau user sedang mengetik atau fokus di kontrol interaktif
      const tag = (e.target as HTMLElement).tagName.toLowerCase()
      const isEditable = (e.target as HTMLElement).isContentEditable
      if (['input', 'textarea', 'select'].includes(tag) || isEditable) return

      if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return
      e.preventDefault()

      const path = window.location.pathname
      const idx = URUTAN.indexOf(path)
      if (idx === -1) return

      if (e.key === 'ArrowRight' && idx < URUTAN.length - 1) {
        nav(URUTAN[idx + 1])
      } else if (e.key === 'ArrowLeft' && idx > 0) {
        nav(URUTAN[idx - 1])
      }
    }

    // capture:true agar terpanggil sebelum child components (termasuk Leaflet) bisa stopPropagation
    window.addEventListener('keydown', handler, true)
    return () => window.removeEventListener('keydown', handler, true)
  }, [nav])
}
