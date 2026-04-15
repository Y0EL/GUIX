type Props = {
  score: number          // 0–100
  size?: 'sm' | 'lg'    // sm = card, lg = detail panel
}

function gaugeColor(score: number): string {
  if (score >= 70) return '#DC2626'
  if (score >= 50) return '#DD6B20'
  return '#4CAF50'
}

export default function RiskGauge({ score, size = 'sm' }: Props) {
  const isLg = size === 'lg'
  const dim = isLg ? 96 : 44
  const r = isLg ? 38 : 16
  const cx = dim / 2
  const cy = dim / 2

  // 240° arc — starts bottom-left, ends bottom-right
  const arcFrac = 240 / 360
  const dashArray = 2 * Math.PI * r * arcFrac
  const dashOffset = dashArray * (1 - Math.max(0, Math.min(100, score)) / 100)

  const color = gaugeColor(score)
  const strokeWidth = isLg ? 7 : 4
  const fontSize = isLg ? 20 : 9
  const fontY = isLg ? cy + 7 : cy + 3.5
  void fontY

  return (
    <div className="iq-gauge-wrap" style={{ width: dim, height: dim }}>
      <svg
        viewBox={`0 0 ${dim} ${dim}`}
        width={dim}
        height={dim}
        style={{ transform: 'rotate(-210deg)' }}
      >
        {/* Track */}
        <circle
          cx={cx} cy={cy} r={r}
          fill="none"
          stroke="rgba(179,24,24,0.12)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${dashArray} ${2 * Math.PI * r}`}
        />
        {/* Fill */}
        <circle
          cx={cx} cy={cy} r={r}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${dashArray} ${2 * Math.PI * r}`}
          strokeDashoffset={dashOffset}
          style={{ transition: 'stroke-dashoffset 0.6s ease, stroke 0.3s ease' }}
        />
      </svg>
      {/* Label — separate div so it doesn't rotate */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          pointerEvents: 'none',
        }}
      >
        <span
          style={{
            fontFamily: 'var(--font-j)',
            fontSize,
            fontWeight: 700,
            lineHeight: 1,
            color,
          }}
        >
          {score}
        </span>
      </div>
    </div>
  )
}
