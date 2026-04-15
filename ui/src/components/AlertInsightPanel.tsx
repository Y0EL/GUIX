import { useEffect, useRef, useState } from 'react'
import {
  BarChart2, MapPin, Zap, Activity, Globe,
  GripVertical, Map as MapIcon, Menu, X, Plus,
} from 'lucide-react'
import type { AlertWithTriage, Kasus, SkorRisiko, Lokasi } from '../types'
import InsightMiniMap from './InsightMiniMap'

type Props = {
  alerts: AlertWithTriage[]
  kasus: Kasus[]
  skorRisiko: SkorRisiko[]
  lokasi: Lokasi[]
}

type WidgetId =
  | 'minimap'
  | 'severity'
  | 'topkasus'
  | 'tipesinyal'
  | 'confidence'
  | 'shift'
  | 'wilayah'
  | 'riskscore'

const WIDGET_META: Record<WidgetId, { label: string; icon: React.ReactNode }> = {
  minimap:    { label: 'Peta Lokasi Aktual',        icon: <MapIcon size={11} /> },
  severity:   { label: 'Distribusi Severity',        icon: <Activity size={11} /> },
  topkasus:   { label: 'Kasus Paling Banyak Alert',  icon: <MapPin size={11} /> },
  tipesinyal: { label: 'Tipe Sinyal Dominan',        icon: <Zap size={11} /> },
  confidence: { label: 'Confidence Rata-Rata',       icon: <BarChart2 size={11} /> },
  shift:      { label: 'Statistik Shift',            icon: <Activity size={11} /> },
  wilayah:    { label: 'Wilayah Paling Aktif',       icon: <Globe size={11} /> },
  riskscore:  { label: 'Risk Score per Kasus',       icon: <Activity size={11} /> },
}

const ALL_WIDGETS = Object.keys(WIDGET_META) as WidgetId[]
const MAX_ACTIVE  = 2

function topN<T>(arr: T[], keyFn: (item: T) => string, n = 5) {
  const map = new globalThis.Map<string, number>()
  for (const item of arr) {
    const k = keyFn(item)
    map.set(k, (map.get(k) ?? 0) + 1)
  }
  return Array.from(map.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, n)
    .map(([label, count]) => ({ label, count }))
}

export default function AlertInsightPanel({ alerts: rawAlerts, kasus, skorRisiko, lokasi }: Props) {
  const [active, setActive]       = useState<WidgetId[]>(['minimap', 'severity'])
  const [menuOpen, setMenuOpen]   = useState(false)
  const [menuPos, setMenuPos]     = useState<{ top: number; right: number } | null>(null)
  const menuRef    = useRef<HTMLDivElement>(null)
  const menuBtnRef = useRef<HTMLButtonElement>(null)

  /* Close dropdown on outside click */
  useEffect(() => {
    if (!menuOpen) return
    function handler(e: MouseEvent) {
      const btn = menuBtnRef.current
      const men = menuRef.current
      if (btn && btn.contains(e.target as Node)) return
      if (men && men.contains(e.target as Node)) return
      setMenuOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [menuOpen])

  /* Drag-to-swap between the 2 slots */
  const dragSrc = useRef<WidgetId | null>(null)

  function removeWidget(id: WidgetId) {
    setActive(prev => prev.filter(w => w !== id))
  }
  function addWidget(id: WidgetId) {
    setActive(prev => {
      if (prev.includes(id)) return prev
      if (prev.length >= MAX_ACTIVE) return prev   // already full — user must remove first
      return [...prev, id]
    })
    setMenuOpen(false)
  }
  function replaceWith(id: WidgetId) {
    /* If full, replace oldest (first) slot */
    setActive(prev => {
      if (prev.includes(id)) return prev
      if (prev.length < MAX_ACTIVE) return [...prev, id]
      return [prev[1], id]   // drop oldest, keep newest + incoming
    })
    setMenuOpen(false)
  }

  /* Drag swap */
  function onDragStart(id: WidgetId) { dragSrc.current = id }
  function onDragOver(e: React.DragEvent) { e.preventDefault() }
  function onDrop(targetId: WidgetId) {
    const src = dragSrc.current
    if (!src || src === targetId) return
    setActive(prev => {
      const arr = [...prev]
      const si = arr.indexOf(src)
      const ti = arr.indexOf(targetId)
      ;[arr[si], arr[ti]] = [arr[ti], arr[si]]
      return arr
    })
    dragSrc.current = null
  }

  /* ── Data computations ── */
  const alerts = rawAlerts.filter(
    a => a.triage !== 'diabaikan' && a.triage !== 'false_positive',
  )
  const kasusMap = new globalThis.Map(kasus.map(k => [k.id_kasus, k]))

  const kritis   = rawAlerts.filter(a => a.tingkat_keparahan === 'tinggi').length
  const menengah = rawAlerts.filter(a => a.tingkat_keparahan === 'menengah').length
  const rendah   = rawAlerts.filter(a => a.tingkat_keparahan === 'rendah').length
  const totalRaw = rawAlerts.length
  const ditindak = rawAlerts.filter(a => a.triage === 'valid' || a.triage === 'dilihat').length
  const eskalasi = rawAlerts.filter(a => a.triage === 'eskalasi').length
  const diabaikan = rawAlerts.filter(
    a => a.triage === 'diabaikan' || a.triage === 'false_positive',
  ).length

  const topKasus   = topN(alerts, a => a.id_kasus.replace('kasus-', ''))
  const topTipe    = topN(alerts, a => a.tipe_sinyal.replace(/_/g, ' '))
  const maxKasus   = topKasus[0]?.count ?? 1
  const maxTipe    = topTipe[0]?.count ?? 1
  const avgConf    = alerts.length > 0
    ? alerts.reduce((s, a) => s + (a.kepercayaan ?? 0), 0) / alerts.length : 0

  const wilayahMap = new globalThis.Map<string, number>()
  for (const a of alerts) {
    const prov = kasusMap.get(a.id_kasus)?.provinsi ?? 'Tidak Diketahui'
    wilayahMap.set(prov, (wilayahMap.get(prov) ?? 0) + 1)
  }
  const topWilayah = Array.from(wilayahMap.entries()).sort((a, b) => b[1] - a[1])
  const maxWilayah = topWilayah[0]?.[1] ?? 1

  const activeProvinsi = Array.from(new globalThis.Set(
    alerts.map(a => kasusMap.get(a.id_kasus)?.provinsi).filter(Boolean) as string[]
  ))

  /* ── Widget body renderer ── */
  function renderBody(id: WidgetId) {
    switch (id) {
      case 'minimap':
        return (
          <InsightMiniMap lokasi={lokasi} kasus={kasus} activeProvinsi={activeProvinsi} />
        )

      case 'severity':
        return (
          <>
            <div className="ac-severity-dist">
              {kritis > 0 && <div className="ac-sev-seg tinggi" style={{ flex: kritis }} title={`Kritis: ${kritis}`} />}
              {menengah > 0 && <div className="ac-sev-seg menengah" style={{ flex: menengah }} title={`Menengah: ${menengah}`} />}
              {rendah > 0 && <div className="ac-sev-seg rendah" style={{ flex: rendah }} title={`Rendah: ${rendah}`} />}
            </div>
            <div className="ac-sev-legend">
              <div className="ac-sev-legend-item"><div className="ac-sev-legend-dot" style={{ background: '#DC2626' }} />{kritis} Kritis</div>
              <div className="ac-sev-legend-item"><div className="ac-sev-legend-dot" style={{ background: '#DD6B20' }} />{menengah} Menengah</div>
              <div className="ac-sev-legend-item"><div className="ac-sev-legend-dot" style={{ background: '#4CAF50' }} />{rendah} Rendah</div>
            </div>
          </>
        )

      case 'topkasus':
        return (
          <>
            {topKasus.map(({ label, count }) => (
              <div key={label} className="ac-insight-row">
                <span className="ac-insight-row-label">{label}</span>
                <div className="ac-insight-row-bar"><div className="ac-insight-row-fill" style={{ width: `${(count / maxKasus) * 100}%` }} /></div>
                <span className="ac-insight-row-count">{count}</span>
              </div>
            ))}
            {topKasus.length === 0 && <div style={{ fontSize: 11, color: 'rgba(243,234,234,.2)' }}>Tidak ada data</div>}
          </>
        )

      case 'tipesinyal':
        return (
          <>
            {topTipe.map(({ label, count }) => (
              <div key={label} className="ac-insight-row">
                <span className="ac-insight-row-label">{label}</span>
                <div className="ac-insight-row-bar"><div className="ac-insight-row-fill" style={{ width: `${(count / maxTipe) * 100}%` }} /></div>
                <span className="ac-insight-row-count">{count}</span>
              </div>
            ))}
          </>
        )

      case 'confidence':
        return (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ flex: 1, height: 6, background: 'rgba(179,24,24,.1)', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{
                  height: '100%', borderRadius: 3, transition: 'width .5s',
                  background: avgConf >= 0.8 ? '#DC2626' : avgConf >= 0.6 ? '#DD6B20' : '#4CAF50',
                  width: `${avgConf * 100}%`,
                }} />
              </div>
              <span style={{ fontFamily: 'var(--font-j)', fontSize: 16, fontWeight: 700, color: avgConf >= 0.8 ? '#ff8a8a' : avgConf >= 0.6 ? '#f0a060' : '#81c784' }}>
                {Math.round(avgConf * 100)}%
              </span>
            </div>
            <div style={{ fontSize: 10, color: 'rgba(243,234,234,.25)', marginTop: 4 }}>dari {alerts.length} alert aktif</div>
          </>
        )

      case 'shift':
        return (
          <div className="ac-shift-grid">
            <div className="ac-shift-cell"><span className="ac-shift-num baru">{totalRaw}</span><span className="ac-shift-lbl">Total</span></div>
            <div className="ac-shift-cell"><span className="ac-shift-num ditindak">{ditindak}</span><span className="ac-shift-lbl">Ditindak</span></div>
            <div className="ac-shift-cell"><span className="ac-shift-num eskalasi">{eskalasi}</span><span className="ac-shift-lbl">Eskalasi</span></div>
            <div className="ac-shift-cell"><span className="ac-shift-num diabaikan">{diabaikan}</span><span className="ac-shift-lbl">Diabaikan</span></div>
          </div>
        )

      case 'wilayah':
        return (
          <>
            {topWilayah.map(([prov, count]) => (
              <div key={prov} className="ac-insight-row">
                <span className="ac-insight-row-label">{prov}</span>
                <div className="ac-insight-row-bar"><div className="ac-insight-row-fill" style={{ width: `${(count / maxWilayah) * 100}%`, background: '#818CF8' }} /></div>
                <span className="ac-insight-row-count">{count}</span>
              </div>
            ))}
          </>
        )

      case 'riskscore':
        return (
          <>
            {skorRisiko.map(sr => (
              <div key={sr.id_kasus} className="ac-insight-row">
                <span className="ac-insight-row-label" style={{ flex: 1.4 }}>
                  {sr.id_kasus.replace('kasus-', '').replace(/-/g, ' ')}
                </span>
                <div className="ac-insight-row-bar">
                  <div className="ac-insight-row-fill" style={{
                    width: `${sr.skor_risiko}%`,
                    background: sr.skor_risiko >= 70 ? '#DC2626' : sr.skor_risiko >= 50 ? '#DD6B20' : '#4CAF50',
                  }} />
                </div>
                <span className="ac-insight-row-count">{sr.skor_risiko}</span>
              </div>
            ))}
          </>
        )
    }
  }

  const inactive = ALL_WIDGETS.filter(w => !active.includes(w))

  return (
    <div className="ac-col-right">

      {/* Panel header */}
      <div className="ac-insight-header">
        <span>Insight &amp; Statistik Shift</span>
        <div style={{ display: 'flex', gap: 4, alignItems: 'center', position: 'relative' }}>
          {/* slot count pill */}
          <span className="ac-wi-slot-pill">
            {active.length}/{MAX_ACTIVE}
          </span>

          {/* Hamburger menu button */}
          <button
            ref={menuBtnRef}
            className="ac-wi-menu-btn"
            onClick={() => {
              if (!menuOpen && menuBtnRef.current) {
                const r = menuBtnRef.current.getBoundingClientRect()
                setMenuPos({ top: r.bottom + 6, right: window.innerWidth - r.right })
              }
              setMenuOpen(v => !v)
            }}
            title="Pilih widget"
          >
            {menuOpen ? <X size={13} /> : <Menu size={13} />}
          </button>

          {/* Dropdown — fixed position agar tidak terhalang map/scroll */}
          {menuOpen && menuPos && (
            <div
              ref={menuRef}
              className="ac-wi-dropdown"
              style={{ position: 'fixed', top: menuPos.top, right: menuPos.right }}
            >
              <div className="ac-wi-dropdown-label">Tambah Widget</div>
              {inactive.map(id => {
                const meta = WIDGET_META[id]
                const isFull = active.length >= MAX_ACTIVE
                return (
                  <button
                    key={id}
                    className="ac-wi-dropdown-item"
                    onClick={() => isFull ? replaceWith(id) : addWidget(id)}
                    title={isFull ? 'Akan mengganti slot pertama' : undefined}
                  >
                    <span className="ac-wi-dropdown-icon">{meta.icon}</span>
                    <span>{meta.label}</span>
                    {isFull
                      ? <span className="ac-wi-dropdown-replace">ganti</span>
                      : <Plus size={10} style={{ color: 'rgba(179,24,24,.5)', marginLeft: 'auto' }} />
                    }
                  </button>
                )
              })}
              {inactive.length === 0 && (
                <div style={{ fontSize: 10, color: 'rgba(243,234,234,.25)', padding: '6px 10px' }}>
                  Semua widget aktif
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Active widgets — maks 2 */}
      <div className="ac-insight-body">
        {active.length === 0 && (
          <div style={{ fontSize: 11, color: 'rgba(243,234,234,.2)', padding: '20px 0', textAlign: 'center' }}>
            Tidak ada widget aktif.
            <br />Klik <Menu size={10} /> untuk memilih.
          </div>
        )}

        {active.map((id, idx) => {
          const meta = WIDGET_META[id]
          return (
            <div
              key={id}
              className="ac-insight-card ac-wi-card"
              draggable
              onDragStart={() => onDragStart(id)}
              onDragOver={onDragOver}
              onDrop={() => onDrop(id)}
            >
              {/* Widget header */}
              <div className="ac-insight-card-header ac-wi-header">
                <span className="ac-wi-grip"><GripVertical size={11} /></span>
                {meta.icon}
                <span style={{ flex: 1 }}>{meta.label}</span>
                <span className="ac-wi-slot-idx">{idx + 1}</span>
                <button
                  className="ac-wi-close"
                  onClick={() => removeWidget(id)}
                  title="Hapus dari watchlist"
                >
                  <X size={11} />
                </button>
              </div>

              {/* Widget body */}
              <div className="ac-insight-card-body">
                {renderBody(id)}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
