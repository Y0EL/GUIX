/** Skeleton loading card — ditampilkan selama 600ms setelah query berubah */
export function SkeletonProfilCard() {
  return (
    <div className="sd-card sd-skeleton-card">
      <div className="sk-avatar" />
      <div className="sk-body">
        <div className="sk-line w80" />
        <div className="sk-line w50" />
        <div className="sk-line w95 mt8" />
        <div className="sk-line w70" />
        <div className="sk-row mt8">
          <div className="sk-chip" />
          <div className="sk-chip" />
          <div className="sk-chip" />
        </div>
      </div>
    </div>
  )
}

export function SkeletonListCard() {
  return (
    <div className="sd-card sd-skeleton-card">
      <div className="sk-icon" />
      <div className="sk-body">
        <div className="sk-row">
          <div className="sk-line w30" />
          <div className="sk-chip small" />
        </div>
        <div className="sk-line w80 mt6" />
        <div className="sk-line w55 mt4" />
      </div>
    </div>
  )
}

/** Grid 4 profil + 2 list — ditampilkan saat isLoading=true */
export default function SkeletonResults() {
  return (
    <div className="sd-results-panel">
      <div className="sd-section">
        <div className="sd-section-header" style={{ pointerEvents: 'none' }}>
          <span className="sd-section-label">
            <span className="sk-line w20" style={{ display: 'inline-block', borderRadius: 4 }} />
          </span>
        </div>
        <div className="sd-section-body grid">
          {[0, 1, 2, 3].map(i => <SkeletonProfilCard key={i} />)}
        </div>
      </div>
      <div className="sd-section" style={{ marginTop: 20 }}>
        <div className="sd-section-header" style={{ pointerEvents: 'none' }}>
          <span className="sd-section-label">
            <span className="sk-line w15" style={{ display: 'inline-block', borderRadius: 4 }} />
          </span>
        </div>
        <div className="sd-section-body list">
          {[0, 1].map(i => <SkeletonListCard key={i} />)}
        </div>
      </div>
    </div>
  )
}
