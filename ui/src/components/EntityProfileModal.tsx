/**
 * EntityProfileModal — fullscreen overlay profil entitas.
 * Load data sendiri: postingan (by id_profil), pertemanan, kasus.
 * Dibuka dari ProfilCard "Analisis" button.
 */
import '../styles/epm.css'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  X, User, MapPin, AlertTriangle, Users, Activity,
  MessageSquare, Link2, FileText, Bookmark, BookmarkCheck,
  ExternalLink, Calendar, Globe,
} from 'lucide-react'
import type { Profil, Postingan, Pertemanan, Kasus } from '../types'
import { muatJson } from '../utils'
import PlatformIcon from './PlatformIcon'
import LiveIntelFeed from './LiveIntelFeed'
import { useWatchlist } from '../hooks/useWatchlist'

type Tab = 'posts' | 'koneksi' | 'kasus' | 'intel'

type Props = {
  profil: Profil
  onClose: () => void
}

function relTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const secs = diff / 1000
  if (secs < 60)    return 'baru saja'
  if (secs < 3600)  return `${Math.floor(secs/60)}m lalu`
  if (secs < 86400) return `${Math.floor(secs/3600)}j lalu`
  const d = Math.floor(secs/86400)
  return d < 30 ? `${d}h lalu` : new Date(iso).toLocaleDateString('id-ID', { day:'numeric', month:'short' })
}

function engSum(p: Postingan): number {
  return p.engagement.suka + p.engagement.komentar + p.engagement.bagikan
}

export default function EntityProfileModal({ profil: p, onClose }: Props) {
  const navigate = useNavigate()
  const [tab, setTab]             = useState<Tab>('posts')
  const [posts, setPosts]         = useState<Postingan[]>([])
  const [koneksi, setKoneksi]     = useState<Profil[]>([])
  const [_allProfil, setAllProfil] = useState<Profil[]>([])
  const [kasus, setKasus]         = useState<Kasus[]>([])
  const [imgErr, setImgErr]       = useState(false)
  const [loading, setLoading]     = useState(true)
  const overlayRef                = useRef<HTMLDivElement>(null)
  const { toggle, isWatched }     = useWatchlist()

  const watched = isWatched(p.id_profil)

  /* Load data */
  useEffect(() => {
    async function load() {
      try {
        const [postData, pertData, profilData, kasusData] = await Promise.all([
          muatJson<Postingan[]>('/data/postingan.json'),
          muatJson<Pertemanan[]>('/data/pertemanan.json'),
          muatJson<Profil[]>('/data/profil.json'),
          muatJson<Kasus[]>('/data/kasus.json'),
        ])

        /* Posts by this profil — sort by engagement desc */
        const myPosts = postData
          .filter(x => x.id_profil === p.id_profil)
          .sort((a, b) => engSum(b) - engSum(a))
        setPosts(myPosts)

        /* Koneksi dari pertemanan */
        const connectedIds = pertData
          .filter(f => f.profil_a === p.id_profil || f.profil_b === p.id_profil)
          .map(f => f.profil_a === p.id_profil ? f.profil_b : f.profil_a)
        const connectedProfil = profilData.filter(pr => connectedIds.includes(pr.id_profil))
        setKoneksi(connectedProfil)
        setAllProfil(profilData)

        setKasus(kasusData)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [p.id_profil])

  /* Close on Escape (fullscreen — tidak ada overlay click) */
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  const linkedKasus = kasus.filter(k =>
    p.tautan_kasus.some(t => t.id_kasus === k.id_kasus)
  )

  const hasRisiko = p.tag_risiko.length > 0
  const akun = p.profil_terekstrak?.akun ?? []
  const stats = p.profil_terekstrak?.statistik ?? null

  return (
    <div
      ref={overlayRef}
      className="epm-overlay"
    >
      <div className="epm-modal">
        {/* ── Header ── */}
        <div className="epm-header">
          <div className="epm-header-left">
            {/* Avatar */}
            <div className="epm-avatar-wrap">
              {!imgErr && p.url_avatar ? (
                <img
                  src={p.url_avatar}
                  alt={p.nama_lengkap}
                  className="epm-avatar"
                  onError={() => setImgErr(true)}
                />
              ) : (
                <div className="epm-avatar-fallback">
                  <User size={28} />
                </div>
              )}
              {hasRisiko && <div className="epm-avatar-ring epm-avatar-ring-danger" />}
            </div>

            {/* Name + meta */}
            <div className="epm-header-meta">
              <div className="epm-nama">{p.nama_lengkap}</div>
              <div className="epm-sub">
                <span className="epm-id">{p.id_profil}</span>
                <span className="epm-sep">·</span>
                <MapPin size={10} />
                <span>{p.kota}, {p.provinsi}</span>
                {p.jenis_kelamin && (
                  <><span className="epm-sep">·</span><span style={{ textTransform: 'capitalize' }}>{p.jenis_kelamin}</span></>
                )}
              </div>

              {/* Platform accounts */}
              <div className="epm-platforms">
                {akun.map((a, i) => (
                  <div key={i} className="epm-platform-item" title={`@${a.username} (${a.platform})`}>
                    <PlatformIcon platform={a.platform} size={14} />
                    <span className="epm-platform-username">@{a.username}</span>
                  </div>
                ))}
              </div>

              {/* Risk tags */}
              {hasRisiko && (
                <div className="epm-risk-tags">
                  {p.tag_risiko.map(t => (
                    <span key={t} className="epm-risk-tag">
                      <AlertTriangle size={9} />
                      {t.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="epm-header-actions">
            <button
              className={`epm-btn ${watched ? 'watched' : ''}`}
              onClick={() => toggle({ id: p.id_profil, tipe: 'profil', label: p.nama_lengkap })}
              title={watched ? 'Hapus dari watchlist' : 'Tambah ke watchlist'}
            >
              {watched ? <BookmarkCheck size={14} /> : <Bookmark size={14} />}
              {watched ? 'Dipantau' : 'Pantau'}
            </button>
            <button className="epm-btn secondary" onClick={onClose}>
              <X size={14} /> Tutup
            </button>
          </div>
        </div>

        {/* Bio */}
        {p.bio && (
          <div className="epm-bio">{p.bio}</div>
        )}

        {/* Stats bar */}
        <div className="epm-stats-bar">
          <div className="epm-stat">
            <span className="epm-stat-val">{stats?.jumlah_posting ?? posts.length}</span>
            <span className="epm-stat-lbl">Postingan</span>
          </div>
          <div className="epm-stat">
            <span className="epm-stat-val">{koneksi.length}</span>
            <span className="epm-stat-lbl">Koneksi</span>
          </div>
          <div className="epm-stat">
            <span className="epm-stat-val">{stats?.jumlah_akun ?? akun.length}</span>
            <span className="epm-stat-lbl">Akun</span>
          </div>
          <div className="epm-stat">
            <span className="epm-stat-val">{linkedKasus.length}</span>
            <span className="epm-stat-lbl">Kasus Terkait</span>
          </div>
          <div className="epm-stat">
            <span className="epm-stat-val">{p.tag_risiko.length}</span>
            <span className="epm-stat-lbl">Sinyal Risiko</span>
          </div>
        </div>

        {/* ── Tabs ── */}
        <div className="epm-tabs">
          {(['posts', 'koneksi', 'kasus', 'intel'] as Tab[]).map(t => (
            <button
              key={t}
              className={`epm-tab ${tab === t ? 'aktif' : ''}`}
              onClick={() => setTab(t)}
            >
              {t === 'posts' && <><MessageSquare size={11} /> Postingan ({posts.length})</>}
              {t === 'koneksi' && <><Users size={11} /> Koneksi ({koneksi.length})</>}
              {t === 'kasus' && <><FileText size={11} /> Kasus ({linkedKasus.length})</>}
              {t === 'intel' && <><Activity size={11} /> Intel Stream</>}
            </button>
          ))}
        </div>

        {/* ── Tab Body ── */}
        <div className="epm-body">
          {loading ? (
            <div className="epm-loading">
              <div className="spinner" style={{ width: 20, height: 20 }} />
              <span>Memuat data profil…</span>
            </div>
          ) : (
            <>
              {/* POSTS TAB */}
              {tab === 'posts' && (
                <div className="epm-posts-grid">
                  {posts.length === 0 && (
                    <div className="epm-empty">Tidak ada postingan terindeks untuk profil ini.</div>
                  )}
                  {posts.map(post => (
                    <div key={post.id_posting} className="epm-post-card">
                      <div className="epm-post-header">
                        <PlatformIcon platform={post.platform} size={14} showLabel />
                        <span className="epm-post-time">{relTime(post.timestamp)}</span>
                        <span className="epm-post-tipe">{post.tipe_konten}</span>
                      </div>
                      <div className="epm-post-konten">{post.konten}</div>
                      {post.hashtag.length > 0 && (
                        <div className="epm-post-hashtags">
                          {post.hashtag.slice(0, 5).map(h => (
                            <span key={h} className="epm-hashtag">{h}</span>
                          ))}
                        </div>
                      )}
                      <div className="epm-post-eng">
                        <span>❤ {post.engagement.suka}</span>
                        <span>💬 {post.engagement.komentar}</span>
                        <span>🔁 {post.engagement.bagikan}</span>
                        <span className="epm-post-loc">
                          <MapPin size={9} /> {post.kota}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* KONEKSI TAB */}
              {tab === 'koneksi' && (
                <div className="epm-koneksi-list">
                  {koneksi.length === 0 && (
                    <div className="epm-empty">Tidak ada koneksi terdeteksi.</div>
                  )}
                  {koneksi.map(k => {
                    const kAkun = k.profil_terekstrak?.akun ?? []
                    const kImgOk = !!k.url_avatar
                    return (
                      <div key={k.id_profil} className="epm-koneksi-item">
                        <div className="epm-kon-avatar-wrap">
                          {kImgOk ? (
                            <img src={k.url_avatar} alt={k.nama_lengkap} className="epm-kon-avatar" />
                          ) : (
                            <div className="epm-kon-avatar epm-kon-avatar-fallback">
                              <User size={14} />
                            </div>
                          )}
                          {k.tag_risiko.length > 0 && <div className="epm-kon-risk-dot" />}
                        </div>
                        <div className="epm-kon-info">
                          <div className="epm-kon-nama">{k.nama_lengkap}</div>
                          <div className="epm-kon-meta">
                            <MapPin size={9} /> {k.kota}
                            {kAkun.length > 0 && (
                              <span className="epm-kon-platforms">
                                {kAkun.slice(0, 3).map((a, i) => (
                                  <PlatformIcon key={i} platform={a.platform} size={11} />
                                ))}
                              </span>
                            )}
                          </div>
                          {k.tag_risiko.length > 0 && (
                            <div className="epm-kon-risiko">
                              <AlertTriangle size={9} /> {k.tag_risiko[0].replace(/_/g, ' ')}
                            </div>
                          )}
                        </div>
                        <button
                          className="epm-btn mini"
                          onClick={() => toggle({ id: k.id_profil, tipe: 'profil', label: k.nama_lengkap })}
                        >
                          {isWatched(k.id_profil)
                            ? <><BookmarkCheck size={11} /> Dipantau</>
                            : <><Bookmark size={11} /> Pantau</>
                          }
                        </button>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* KASUS TAB */}
              {tab === 'kasus' && (
                <div className="epm-kasus-list">
                  {linkedKasus.length === 0 && (
                    <div className="epm-empty">
                      Tidak ada kasus langsung terhubung ke profil ini.
                      <br />
                      <span style={{ fontSize: 10, color: 'rgba(243,234,234,.25)', marginTop: 4, display: 'block' }}>
                        Keterkaitan mungkin ada di jaringan koneksi.
                      </span>
                    </div>
                  )}
                  {p.tautan_kasus.map(tk => {
                    const k = kasus.find(c => c.id_kasus === tk.id_kasus)
                    return (
                      <div key={tk.id_kasus} className="epm-kasus-item">
                        <div className="epm-kasus-title">{k?.judul ?? tk.id_kasus}</div>
                        <div className="epm-kasus-meta">
                          <span className="epm-kasus-peran">{tk.peran}</span>
                          <span className="epm-sep">·</span>
                          <span>{k?.kota ?? ''}</span>
                          {tk.sinyal && (
                            <><span className="epm-sep">·</span>
                            <span style={{ color: '#E04B4B' }}>{tk.sinyal}</span></>
                          )}
                        </div>
                        <button
                          className="epm-btn mini"
                          onClick={() => toggle({ id: tk.id_kasus, tipe: 'kasus', label: k?.judul ?? tk.id_kasus })}
                        >
                          {isWatched(tk.id_kasus)
                            ? <><BookmarkCheck size={11} /> Di Antrian</>
                            : <><Link2 size={11} /> Tambah ke Antrian</>
                          }
                        </button>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* INTEL STREAM TAB */}
              {tab === 'intel' && (
                <div style={{ padding: '4px 0' }}>
                  <LiveIntelFeed
                    idKasus={p.tautan_kasus[0]?.id_kasus ?? 'kasus-kebakaran-gudang'}
                    kasusKota={p.kota}
                    kasusProvinsi={p.provinsi}
                  />
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="epm-footer">
          <span style={{ fontSize: 9, color: 'rgba(243,234,234,.2)' }}>
            <Calendar size={9} /> Dibuat {new Date(p.dibuat_pada).toLocaleDateString('id-ID')}
          </span>
          <span style={{ fontSize: 9, color: 'rgba(243,234,234,.2)' }}>
            <Globe size={9} /> {p.bahasa.join(', ')}
          </span>
          <button
            className="epm-btn mini"
            onClick={() => {
              onClose()
              navigate(`/link-analysis?profil=${p.id_profil}`)
            }}
            title="Buka profil ini di Link Analysis"
          >
            <ExternalLink size={11} /> Lihat di Link Analysis
          </button>
        </div>
      </div>
    </div>
  )
}
