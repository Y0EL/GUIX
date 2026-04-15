/**
 * PlatformIcon — ikon platform nyata dari cdn.simpleicons.org
 * Fallback ke colored text badge jika gambar gagal load.
 */
import { useState } from 'react'

/* Mapping slug → hex warna brand + label singkat */
const PLATFORM_CFG: Record<string, { slug: string; color: string; label: string }> = {
  youtube:   { slug: 'youtube',   color: 'FF0000', label: 'YT' },
  instagram: { slug: 'instagram', color: 'E1306C', label: 'IG' },
  facebook:  { slug: 'facebook',  color: '1877F2', label: 'FB' },
  twitter:   { slug: 'x',        color: '000000', label: 'X'  },
  x:         { slug: 'x',        color: '000000', label: 'X'  },
  tiktok:    { slug: 'tiktok',   color: '000000', label: 'TK' },
  telegram:  { slug: 'telegram', color: '26A5E4', label: 'TG' },
  whatsapp:  { slug: 'whatsapp', color: '25D366', label: 'WA' },
  linkedin:  { slug: 'linkedin', color: '0A66C2', label: 'LI' },
  reddit:    { slug: 'reddit',   color: 'FF4500', label: 'RD' },
  discord:   { slug: 'discord',  color: '5865F2', label: 'DC' },
}

type Props = {
  platform: string
  size?: number
  showLabel?: boolean   // tampilkan teks di samping ikon
  className?: string
}

export default function PlatformIcon({ platform, size = 16, showLabel = false, className = '' }: Props) {
  const [imgErr, setImgErr] = useState(false)
  const key = platform.toLowerCase().trim()
  const cfg = PLATFORM_CFG[key]

  const iconUrl = cfg
    ? `https://cdn.simpleicons.org/${cfg.slug}/${cfg.color}`
    : null

  if (!iconUrl || imgErr) {
    /* Fallback: colored text badge */
    const fallbackCfg = cfg ?? { color: '6B7280', label: key.slice(0, 2).toUpperCase() }
    return (
      <span
        className={`platform-icon-fallback ${className}`}
        style={{
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          width: size, height: size,
          borderRadius: 3,
          background: `#${fallbackCfg.color}22`,
          border: `1px solid #${fallbackCfg.color}55`,
          color: `#${fallbackCfg.color}`,
          fontSize: Math.max(8, size * 0.55),
          fontWeight: 700,
          letterSpacing: '-.02em',
          flexShrink: 0,
        }}
        title={platform}
      >
        {fallbackCfg.label}
      </span>
    )
  }

  return (
    <span
      className={`platform-icon-wrap ${className}`}
      style={{ display: 'inline-flex', alignItems: 'center', gap: 4, flexShrink: 0 }}
    >
      <img
        src={iconUrl}
        alt={platform}
        width={size}
        height={size}
        style={{ display: 'block', objectFit: 'contain' }}
        onError={() => setImgErr(true)}
        title={platform}
      />
      {showLabel && (
        <span style={{ fontSize: size * 0.7, color: 'rgba(243,234,234,.6)' }}>
          {platform}
        </span>
      )}
    </span>
  )
}
