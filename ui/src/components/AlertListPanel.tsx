import type { AlertWithTriage, GroupMode, Kasus } from '../types'

type Props = {
  alerts: AlertWithTriage[]
  kasus: Kasus[]
  selected: string | null
  groupMode: GroupMode
  filterSeverity: string[]
  filterTipe: string[]
  onSelect: (id: string) => void
  onGroupMode: (mode: GroupMode) => void
  onToggleSeverity: (s: string) => void
}

const SEVERITY_COLOR: Record<string, string> = {
  tinggi: '#DC2626',
  menengah: '#DD6B20',
  rendah: '#4CAF50',
}

const TIPE_LABELS: Record<string, string> = {
  posting_pra_kejadian: 'Pra-Kejadian',
  narasi_copy_paste: 'Copy-Paste',
  co_lokasi: 'Co-Lokasi',
  pola_finansial: 'Finansial',
  posting_tersinkronisasi: 'Sinkronisasi',
  klaster_akun: 'Klaster Akun',
  pergerakan_cepat: 'Mobilitas',
  anomali_jaringan: 'Jaringan',
}

function tipeLabel(tipe: string): string {
  return TIPE_LABELS[tipe] ?? tipe.replace(/_/g, ' ')
}

function groupAlerts(
  alerts: AlertWithTriage[],
  mode: GroupMode,
  kasusList: Kasus[],
): { key: string; label: string; items: AlertWithTriage[] }[] {
  if (mode === 'flat') {
    return [{ key: 'semua', label: 'Semua Alert', items: alerts }]
  }
  const kasusMap = new Map(kasusList.map(k => [k.id_kasus, k]))
  const map = new Map<string, AlertWithTriage[]>()
  for (const a of alerts) {
    let key: string
    if (mode === 'kasus') key = a.id_kasus
    else if (mode === 'tipe') key = a.tipe_sinyal
    else /* wilayah */ key = kasusMap.get(a.id_kasus)?.provinsi ?? 'Tidak Diketahui'
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(a)
  }
  return Array.from(map.entries())
    .sort((a, b) => b[1].length - a[1].length)
    .map(([key, items]) => ({
      key,
      label: mode === 'tipe' ? tipeLabel(key) : mode === 'kasus' ? key.replace('kasus-', '').replace(/-/g, ' ') : key,
      items,
    }))
}

function statusBadge(status: AlertWithTriage['triage']) {
  if (status === 'baru' || status === 'dilihat') return null
  const map: Record<string, { label: string; cls: string }> = {
    valid: { label: 'Valid', cls: 'valid' },
    false_positive: { label: 'FP', cls: 'false_positive' },
    eskalasi: { label: 'Eskalasi', cls: 'eskalasi' },
    diabaikan: { label: 'Abaikan', cls: 'diabaikan' },
  }
  const e = map[status]
  return e ? (
    <span className={`ac-row-status-badge ${e.cls}`}>{e.label}</span>
  ) : null
}

const SEVERITIES = ['tinggi', 'menengah', 'rendah']

export default function AlertListPanel({
  alerts,
  kasus,
  selected,
  groupMode,
  filterSeverity,
  filterTipe,
  onSelect,
  onGroupMode,
  onToggleSeverity,
}: Props) {

  const filtered = alerts.filter(a => {
    const okSev = filterSeverity.length === 0 || filterSeverity.includes(a.tingkat_keparahan)
    const okTipe = filterTipe.length === 0 || filterTipe.includes(a.tipe_sinyal)
    return okSev && okTipe
  })

  const groups = groupAlerts(filtered, groupMode, kasus)

  return (
    <div className="ac-col-left">
      {/* Severity filter chips */}
      <div className="ac-filter-bar">
        <div className="ac-filter-label">Severity</div>
        <div className="ac-filter-chips">
          {SEVERITIES.map(s => (
            <button
              key={s}
              className={`ac-chip ${filterSeverity.includes(s) ? `aktif ${s}` : ''}`}
              onClick={() => onToggleSeverity(s)}
            >
              <span
                style={{
                  display: 'inline-block',
                  width: 6, height: 6,
                  borderRadius: '50%',
                  background: SEVERITY_COLOR[s],
                }}
              />
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Group mode toggle */}
      <div className="ac-group-bar">
        <span>Kelompok</span>
        {(['flat', 'kasus', 'tipe', 'wilayah'] as GroupMode[]).map(m => (
          <button
            key={m}
            className={`ac-group-btn ${groupMode === m ? 'aktif' : ''}`}
            onClick={() => onGroupMode(m)}
          >
            {m === 'flat' ? 'Semua' : m === 'kasus' ? 'Kasus' : m === 'tipe' ? 'Tipe' : 'Wilayah'}
          </button>
        ))}
        <span style={{ marginLeft: 'auto', fontSize: 9, color: 'rgba(243,234,234,.2)' }}>
          {filtered.length} alert
        </span>
      </div>

      {/* Alert list */}
      <div className="ac-alert-list">
        {groups.map(g => (
          <div key={g.key}>
            {groupMode !== 'flat' && (
              <div className="ac-group-header">
                <span title={g.label} style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                  {g.label}
                </span>
                <span className="ac-group-count">{g.items.length}</span>
              </div>
            )}
            {g.items.map(alert => {
              const trCls =
                alert.triage !== 'baru' && alert.triage !== 'dilihat'
                  ? `triage-${alert.triage}`
                  : ''
              return (
                <div
                  key={alert.id_peringatan}
                  className={`ac-alert-row ${selected === alert.id_peringatan ? 'aktif' : ''} ${trCls}`}
                  onClick={() => onSelect(alert.id_peringatan)}
                >
                  <div className="ac-row-header">
                    <span
                      className="ac-severity-dot"
                      style={{ background: SEVERITY_COLOR[alert.tingkat_keparahan] ?? '#888' }}
                    />
                    <span className="ac-row-tipe">{tipeLabel(alert.tipe_sinyal)}</span>
                    {statusBadge(alert.triage)}
                  </div>
                  <div className="ac-row-desc">{alert.deskripsi}</div>
                  <div className="ac-row-meta">
                    <div className="ac-conf-bar">
                      <div
                        className="ac-conf-fill"
                        style={{ width: `${(alert.kepercayaan ?? 0) * 100}%` }}
                      />
                    </div>
                    <span>{Math.round((alert.kepercayaan ?? 0) * 100)}% conf</span>
                    <span style={{ marginLeft: 'auto', fontSize: 9, opacity: 0.6 }}>
                      {alert.id_kasus.replace('kasus-', '')}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        ))}

        {filtered.length === 0 && (
          <div style={{ padding: '28px 16px', textAlign: 'center', fontSize: 12, color: 'rgba(243,234,234,.2)' }}>
            Tidak ada alert yang cocok
          </div>
        )}
      </div>
    </div>
  )
}
