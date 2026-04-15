import { useState } from 'react'
import { User, AlertTriangle, Users, FileText, Activity, Bookmark, BookmarkCheck } from 'lucide-react'
import type { Profil } from '../types'
import { highlightMatch } from '../hooks/useSearch'
import PlatformIcon from './PlatformIcon'
import EntityProfileModal from './EntityProfileModal'
import { useWatchlist } from '../hooks/useWatchlist'

type Props = {
  profil: Profil
  query: string
  matchedFields: string[]
  koneksiCount?: number
  kasusMap?: Record<string, string>
}

export default function ProfilCard({ profil: p, query, matchedFields: _m, koneksiCount = 0, kasusMap = {} }: Props) {
  const [imgError, setImgError]     = useState(false)
  const [modalOpen, setModalOpen]   = useState(false)
  const { toggle, isWatched }       = useWatchlist()
  const watched                     = isWatched(p.id_profil)

  const hasRisiko    = p.tag_risiko.length > 0
  const akun         = p.profil_terekstrak?.akun ?? []
  const jumlahPosting = p.profil_terekstrak?.statistik?.jumlah_posting ?? 0
  const jumlahKasus  = p.tautan_kasus.length

  function hl(text: string) {
    return <span dangerouslySetInnerHTML={{ __html: highlightMatch(text, query) }} />
  }

  return (
    <>
      <div className={`sd-card sd-profil-card ${hasRisiko ? 'has-risiko' : ''} ${watched ? 'is-watched' : ''}`}>

        {/* Avatar */}
        <div className="sd-profil-avatar-wrap">
          {!imgError && p.url_avatar ? (
            <img
              src={p.url_avatar}
              alt={p.nama_lengkap}
              className="sd-profil-avatar"
              onError={() => setImgError(true)}
            />
          ) : (
            <div className="sd-profil-avatar-fallback">
              <User size={22} />
            </div>
          )}
          {hasRisiko && <div className="sd-profil-avatar-ring" />}
          {watched && <div className="sd-profil-watched-dot" />}
        </div>

        {/* Info */}
        <div className="sd-profil-info">
          <div className="sd-profil-nama">{hl(p.nama_lengkap)}</div>
          <div className="sd-profil-meta">
            <span className="sd-profil-id">{p.id_profil.slice(0, 14)}…</span>
            <span className="sd-profil-sep">·</span>
            <span className="sd-profil-kota">{p.kota}</span>
          </div>

          {/* Platform badges — real icons */}
          {akun.length > 0 && (
            <div className="sd-profil-platforms">
              {akun.slice(0, 6).map((a, i) => (
                <span
                  key={i}
                  className="sd-platform-badge-icon"
                  title={`${a.platform}: @${a.username}`}
                >
                  <PlatformIcon platform={a.platform} size={13} />
                </span>
              ))}
              {akun.length > 6 && (
                <span className="sd-platform-badge-icon sd-platform-more">
                  +{akun.length - 6}
                </span>
              )}
            </div>
          )}

          {p.bio && (
            <div className="sd-profil-bio">
              {hl(p.bio.length > 90 ? p.bio.slice(0, 90) + '…' : p.bio)}
            </div>
          )}

          {/* Stats */}
          <div className="sd-profil-stats">
            <span className="sd-profil-stat"><Activity size={9} />{jumlahPosting} postingan</span>
            <span className="sd-profil-stat-sep">·</span>
            <span className="sd-profil-stat"><Users size={9} />{koneksiCount} koneksi</span>
            <span className="sd-profil-stat-sep">·</span>
            <span className="sd-profil-stat"><FileText size={9} />{jumlahKasus} kasus</span>
          </div>

          {/* Risiko */}
          {hasRisiko && (
            <div className="sd-profil-tags">
              {p.tag_risiko.slice(0, 3).map(t => (
                <span key={t} className="sd-profil-risiko-badge">
                  <AlertTriangle size={8} />
                  {t.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          )}

          {/* Kasus terkait */}
          {jumlahKasus > 0 && (
            <div className="sd-profil-kasus-row">
              <span className="sd-profil-kasus-label">Terkait:</span>
              {p.tautan_kasus.slice(0, 2).map(k => (
                <span key={k.id_kasus} className="sd-profil-kasus-chip" title={kasusMap[k.id_kasus] ?? k.id_kasus}>
                  {kasusMap[k.id_kasus]
                    ? kasusMap[k.id_kasus].slice(0, 24) + (kasusMap[k.id_kasus].length > 24 ? '…' : '')
                    : k.id_kasus.slice(0, 14) + '…'}
                </span>
              ))}
              {jumlahKasus > 2 && (
                <span className="sd-profil-kasus-chip more">+{jumlahKasus - 2}</span>
              )}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="sd-card-action">
          {/* Watchlist toggle */}
          <button
            className={`sd-watch-btn ${watched ? 'watched' : ''}`}
            onClick={() => toggle({ id: p.id_profil, tipe: 'profil', label: p.nama_lengkap })}
            title={watched ? 'Hapus dari watchlist' : 'Pantau profil ini'}
          >
            {watched ? <BookmarkCheck size={11} /> : <Bookmark size={11} />}
          </button>

          {/* Open fullscreen profile */}
          <button
            className="sd-drill-btn"
            onClick={() => setModalOpen(true)}
            title="Lihat profil lengkap"
          >
            Analisis
          </button>
        </div>
      </div>

      {/* Entity Profile Modal */}
      {modalOpen && (
        <EntityProfileModal
          profil={p}
          onClose={() => setModalOpen(false)}
        />
      )}
    </>
  )
}
