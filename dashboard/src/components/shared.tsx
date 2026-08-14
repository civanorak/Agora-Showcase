import { verdictStyle } from '../verdicts'
import type { AgoraEvent } from '../types'
import { useI18n } from '../i18n'

export function AgentBadge({ verdict }: { verdict: string | null }) {
  const s = verdictStyle(verdict)
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center',
      padding: '2px 8px', borderRadius: '4px', fontSize: '11px',
      fontWeight: 600, letterSpacing: '0.03em', whiteSpace: 'nowrap',
      color: s.color, background: s.bg, border: `1px solid ${s.border}`,
    }}>
      {s.label}
    </span>
  )
}

export function StatusChip({ code }: { code: number }) {
  const color  = code < 300 ? '#166534' : code < 400 ? '#92400e' : '#991b1b'
  const bg     = code < 300 ? '#f0fdf4' : code < 400 ? '#fffbeb' : '#fef2f2'
  const border = code < 300 ? '#bbf7d0' : code < 400 ? '#fde68a' : '#fecaca'
  return (
    <span style={{
      display: 'inline-block', padding: '2px 7px', borderRadius: '4px',
      fontSize: '11px', fontWeight: 700, fontVariantNumeric: 'tabular-nums',
      color, background: bg, border: `1px solid ${border}`,
    }}>
      {code}
    </span>
  )
}

export function StatCard({ label, value, note }: { label: string; value: number | string; note?: string }) {
  return (
    <div style={{
      flex: 1, minWidth: '140px',
      background: '#fff', border: '1px solid #e4e4e7',
      borderRadius: '8px', padding: '20px 22px',
    }}>
      <div style={{ fontSize: '11px', fontWeight: 600, color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
        {label}
      </div>
      <div style={{ fontSize: '30px', fontWeight: 700, color: '#09090b', marginTop: '8px', lineHeight: 1, letterSpacing: '-0.02em' }}>
        {value}
      </div>
      {note && <div style={{ fontSize: '12px', color: '#71717a', marginTop: '6px' }}>{note}</div>}
    </div>
  )
}

export function TrafficBar({ events }: { events: AgoraEvent[] }) {
  const { t } = useI18n()
  if (events.length === 0) return null
  const counts: Record<string, number> = {}
  for (const e of events) {
    const v = e.verdict ?? 'unknown'
    counts[v] = (counts[v] ?? 0) + 1
  }
  const total = events.length
  const segments = Object.entries(counts)
    .filter(([, n]) => n > 0)
    .map(([v, n]) => ({ v, pct: (n / total) * 100, s: verdictStyle(v) }))
  return (
    <div style={{ marginBottom: '28px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
        <span style={{ fontSize: '12px', fontWeight: 600, color: '#52525b' }}>{t('Traffic Breakdown', 'Trafik Dağılımı')}</span>
        <span style={{ fontSize: '12px', color: '#a1a1aa' }}>{total} {t('requests', 'istek')}</span>
      </div>
      <div style={{ display: 'flex', height: '8px', borderRadius: '4px', overflow: 'hidden', background: '#f4f4f5', gap: '1px' }}>
        {segments.map(({ v, pct, s }) => (
          <div key={v} style={{ width: `${pct}%`, background: s.color, opacity: 0.85 }} />
        ))}
      </div>
      <div style={{ display: 'flex', gap: '16px', marginTop: '10px', flexWrap: 'wrap' }}>
        {segments.map(({ v, pct, s }) => (
          <div key={v} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '2px', background: s.color, opacity: 0.85 }} />
            <span style={{ fontSize: '11px', color: '#52525b' }}>
              {s.label} <span style={{ color: '#a1a1aa' }}>{Math.round(pct)}%</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// Parses "ua_match:sig_id:token" → short display label; truncates other strings.
function fmtEvidence(e: string): string {
  if (e.startsWith('ua_match:')) {
    const token = e.split(':')[2] ?? e
    return token.length > 22 ? token.slice(0, 22) + '…' : token
  }
  if (e.startsWith('probe_path:')) return 'probe:' + e.slice(11)
  if (e.startsWith('ip_verified:')) return 'verified:' + e.slice(12)
  if (e === 'ua_ip_mismatch') return 'ip_mismatch'
  return e.length > 24 ? e.slice(0, 24) + '…' : e
}

export function EvidenceChips({ evidence }: { evidence: string[] }) {
  if (evidence.length === 0) return <span style={{ color: '#a1a1aa', fontSize: '11px' }}>—</span>
  const visible = evidence.slice(0, 2)
  const rest    = evidence.slice(2)
  return (
    <div style={{ display: 'flex', gap: '4px', alignItems: 'center', flexWrap: 'wrap' }}>
      {visible.map(e => (
        <span key={e} title={e} style={{
          display: 'inline-block', padding: '1px 6px', borderRadius: '3px',
          fontSize: '10px', fontFamily: 'ui-monospace, monospace',
          background: '#f4f4f5', border: '1px solid #e4e4e7', color: '#52525b',
          maxWidth: '130px', overflow: 'hidden', textOverflow: 'ellipsis',
          whiteSpace: 'nowrap', cursor: 'default',
        }}>
          {fmtEvidence(e)}
        </span>
      ))}
      {rest.length > 0 && (
        <span title={rest.join('\n')} style={{
          fontSize: '10px', color: '#a1a1aa', cursor: 'default',
          padding: '1px 5px', border: '1px solid #e4e4e7',
          borderRadius: '3px', background: '#fafafa',
        }}>
          +{rest.length}
        </span>
      )}
    </div>
  )
}

export function ChecklistItemView({ label, pass, evidence }: { label: string; pass: boolean; evidence: string }) {
  return (
    <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
      <span style={{
        fontSize: '14px',
        color: pass ? '#22c55e' : '#ef4444',
        fontWeight: 'bold',
        display: 'inline-block',
        marginTop: '1px',
      }}>
        {pass ? '✓' : '✗'}
      </span>
      <div>
        <div style={{ fontSize: '12.5px', fontWeight: 600, color: '#09090b' }}>{label}</div>
        <div style={{ fontSize: '11px', color: '#71717a', marginTop: '2px' }}>{evidence}</div>
      </div>
    </div>
  )
}
