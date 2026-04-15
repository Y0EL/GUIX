import { Play, ExternalLink } from 'lucide-react'
import type { Postingan } from '../types'
import { highlightMatch } from '../hooks/useSearch'
import { formatTanggal } from '../utils'

type Props = {
  postingan: Postingan
  query: string
}

const PLATFORM_COLOR: Record<string, { bg: string; color: string }> = {
  twitter:   { bg: 'rgba(29,161,242,.15)',   color: '#1da1f2' },
  instagram: { bg: 'rgba(193,53,132,.15)',   color: '#c13584' },
  youtube:   { bg: 'rgba(255,0,0,.15)',      color: '#ff4444' },
  facebook:  { bg: 'rgba(24,119,242,.15)',   color: '#1877f2' },
  tiktok:    { bg: 'rgba(105,201,208,.15)',  color: '#69c9d0' },
}

export default function PostinganCard({ postingan: p, query }: Props) {
  const platStyle = PLATFORM_COLOR[p.platform.toLowerCase()] ?? { bg: 'rgba(255,255,255,.08)', color: '#8A8A8A' }
  const cuplikan = p.konten.length > 120 ? p.konten.slice(0, 120) + '…' : p.konten

  function hl(text: string) {
    return <span dangerouslySetInnerHTML={{ __html: highlightMatch(text, query) }} />
  }

  return (
    <div className="sd-card sd-post-card">
      <div className="sd-card-type-icon post">
        <Play size={12} />
      </div>
      <div className="sd-post-info">
        <div className="sd-post-header">
          <span
            className="sd-post-platform"
            style={{ background: platStyle.bg, color: platStyle.color }}
          >
            {p.platform}
          </span>
          <span className="sd-post-profil">{p.id_profil}</span>
          <span className="sd-sep">·</span>
          <span className="sd-post-ts">{formatTanggal(p.timestamp)}</span>
        </div>
        <div className="sd-post-konten">{hl(cuplikan)}</div>
        {p.hashtag.length > 0 && (
          <div className="sd-post-hashtags">
            {p.hashtag.slice(0, 4).map(h => (
              <span key={h} className="sd-post-hashtag">{h}</span>
            ))}
          </div>
        )}
      </div>
      <div className="sd-card-action">
        <button
          className="sd-drill-btn disabled"
          disabled
          title="Tersedia setelah H10 selesai"
        >
          <ExternalLink size={11} />
          Lihat Konten
        </button>
      </div>
    </div>
  )
}
