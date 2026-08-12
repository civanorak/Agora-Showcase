import { VERDICT_ORDER, VERDICT_STYLE } from '../verdicts'
import type { HourlyBucket } from '../types'

export function TimeSeriesChart({ buckets }: { buckets: HourlyBucket[] }) {
  if (buckets.length === 0) {
    return (
      <div style={{ height: 140, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontSize: 12, color: '#a1a1aa' }}>Collecting data…</span>
      </div>
    )
  }

  const byHour = new Map<string, Record<string, number>>()
  for (const b of buckets) {
    if (!byHour.has(b.hour)) byHour.set(b.hour, {})
    byHour.get(b.hour)![b.verdict] = b.count
  }

  const hours  = [...byHour.keys()].sort()
  const maxVal = Math.max(...hours.map(h => Object.values(byHour.get(h)!).reduce((a, c) => a + c, 0)), 1)

  const W = 1000, H = 160
  const PL = 38, PR = 12, PT = 12, PB = 28
  const innerW = W - PL - PR
  const innerH = H - PT - PB
  const slotW  = innerW / Math.max(hours.length, 1)
  const barW   = Math.max(slotW * 0.72, 2)
  const barGap = (slotW - barW) / 2
  const labelEvery = Math.ceil(hours.length / 6)

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 160, display: 'block' }}>
      {[0, 0.25, 0.5, 0.75, 1].map(frac => {
        const y = PT + innerH * (1 - frac)
        return (
          <g key={frac}>
            <line x1={PL} x2={W - PR} y1={y} y2={y} stroke="#f4f4f5" strokeWidth={1} />
            <text x={PL - 6} y={y + 4} textAnchor="end" fontSize={9} fill="#a1a1aa">
              {Math.round(maxVal * frac)}
            </text>
          </g>
        )
      })}

      {hours.map((h, i) => {
        const x    = PL + i * slotW + barGap
        const data = byHour.get(h)!
        let bottom = PT + innerH
        const segs: Array<{ v: string; y: number; h: number }> = []
        for (const v of VERDICT_ORDER) {
          const count = data[v] ?? 0
          if (count === 0) continue
          const bh = (count / maxVal) * innerH
          bottom -= bh
          segs.push({ v, y: bottom, h: bh })
        }
        return (
          <g key={h}>
            {segs.map(s => (
              <rect key={s.v} x={x} y={s.y} width={barW} height={s.h}
                fill={VERDICT_STYLE[s.v]?.color ?? '#a1a1aa'} opacity={0.82} rx={1} />
            ))}
            {i % labelEvery === 0 && (
              <text x={x + barW / 2} y={H - 6} textAnchor="middle" fontSize={9} fill="#a1a1aa">
                {h.slice(11, 16)}
              </text>
            )}
          </g>
        )
      })}

      <line x1={PL} x2={W - PR} y1={PT + innerH} y2={PT + innerH} stroke="#e4e4e7" strokeWidth={1} />
    </svg>
  )
}
