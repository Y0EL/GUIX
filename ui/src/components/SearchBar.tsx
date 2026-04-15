import { useRef, useEffect } from 'react'
import { Search, X, Loader2 } from 'lucide-react'

type Props = {
  query: string
  isSearching: boolean
  onChange: (q: string) => void
  onConfirm: (q: string) => void
  onClear: () => void
}

export default function SearchBar({ query, isSearching, onChange, onConfirm, onClear }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  function handleKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') onConfirm(query)
    if (e.key === 'Escape') onClear()
  }

  return (
    <div className="sd-searchbar-wrap">
      <div className={`sd-searchbar ${query ? 'has-value' : ''}`}>
        <div className="sd-searchbar-icon">
          {isSearching
            ? <Loader2 size={16} className="sd-spin" />
            : <Search size={16} />
          }
        </div>
        <input
          ref={inputRef}
          type="text"
          className="sd-searchbar-input"
          placeholder="Cari nama, id kasus, lokasi, kata kunci..."
          value={query}
          onChange={e => onChange(e.target.value)}
          onKeyDown={handleKey}
          autoComplete="off"
          spellCheck={false}
        />
        {query && (
          <button className="sd-searchbar-clear" onClick={onClear} tabIndex={-1}>
            <X size={14} />
          </button>
        )}
      </div>
      {!query && (
        <div className="sd-searchbar-hint">
          Ketik minimal 2 karakter — profil, kasus, lokasi, atau konten postingan
        </div>
      )}
    </div>
  )
}
