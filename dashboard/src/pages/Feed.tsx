import { useState } from 'react'
import type { AgoraEvent, StatsData } from '../types'
import { AI_VERDICTS, VERDICT_STYLE } from '../verdicts'
import { AgentBadge, EvidenceChips, StatCard, StatusChip, TrafficBar } from '../components/shared'
import { TimeSeriesChart } from '../components/TimeSeriesChart'
import { DemoBadge } from '../components/DemoBadge'
import { useI18n } from '../i18n'

interface FeedProps {
  events: AgoraEvent[]
  stats: StatsData | null
  isLoading: boolean
  streamMode: 'sse' | 'poll'
  newIds: Set<number>
  onSimulate: (agent: string) => void
}

export function Feed({ events, stats, isLoading, streamMode, newIds, onSimulate }: FeedProps) {
  const { t } = useI18n()
  const [hoveredRow, setHoveredRow] = useState<number | null>(null)
  const [filterVerdicts, setFilterVerdicts] = useState<Set<string>>(new Set())
  const [pathQuery, setPathQuery] = useState('')

  // Stats always computed from full event set (not from filtered view)
  const total      = events.length
  const aiCount    = events.filter(e => AI_VERDICTS.has(e.verdict ?? '')).length
  const assistants = events.filter(e => e.verdict === 'assistant_browse').length
  const crawlers   = events.filter(e => e.verdict === 'crawler_search' || e.verdict === 'crawler_training').length

  const filteredEvents = events.filter(e => {
    if (filterVerdicts.size > 0 && !filterVerdicts.has(e.verdict ?? 'unknown')) return false
    if (pathQuery && !e.path.toLowerCase().includes(pathQuery.toLowerCase())) return false
    return true
  })

  const toggleVerdict = (v: string) =>
    setFilterVerdicts(prev => {
      const next = new Set(prev)
      next.has(v) ? next.delete(v) : next.add(v)
      return next
    })

  const hasFilter = filterVerdicts.size > 0 || pathQuery.length > 0

  return (
    <>
      <div style={{ marginBottom: '28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <h1 style={{ fontSize: '20px', fontWeight: 700, color: '#09090b', margin: 0, letterSpacing: '-0.02em' }}>
            {t('Live Request Feed', 'Canlı İstek Akışı')}
          </h1>
          <DemoBadge />
        </div>
        <p style={{ fontSize: '13px', color: '#71717a', margin: '5px 0 0', lineHeight: 1.5 }}>
          {t('Classifier v1 active', 'Sınıflandırıcı v1 aktif')}
          {streamMode === 'sse' ? t(' · Live stream', ' · Canlı akış') : t(' · Polling every 3s', ' · 3 sn’de bir yoklama')}
          {total > 0 && t(` · ${total} events in window`, ` · pencerede ${total} olay`)}
        </p>
      </div>

      {/* ── Demo controls (sandbox) ── */}
      <div style={{
        background: '#fff', border: '1px solid #e4e4e7', borderRadius: '8px',
        padding: '16px 20px', marginBottom: '24px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px',
      }}>
        <div>
          <div style={{ fontSize: '13.5px', fontWeight: 700, color: '#09090b' }}>{t('AI Agent Simulator (Sandbox)', 'AI Ajan Simülatörü (Deneme)')}</div>
          <div style={{ fontSize: '11.5px', color: '#71717a', marginTop: '3px' }}>{t('Simulate AI bots visiting your store to test live detection in real-time.', 'Canlı tespiti gerçek zamanlı test etmek için mağazanızı ziyaret eden AI botlarını simüle edin.')}</div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {['chatgpt', 'claude', 'perplexity'].map(agent => (
            <button key={agent} className="vbtn" onClick={() => onSimulate(agent)} style={{
              padding: '6px 14px', borderRadius: '6px', fontSize: '12px', fontWeight: 600,
              background: '#09090b', color: '#fff', border: 'none', display: 'inline-flex', alignItems: 'center', gap: '4px',
            }}>
              🤖 {agent.charAt(0).toUpperCase() + agent.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* ── Stat cards ── */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '24px', flexWrap: 'wrap' }}>
        <StatCard label={t('Total Requests', 'Toplam İstek')}   value={total} />
        <StatCard label={t('AI Traffic', 'AI Trafiği')}       value={aiCount}
          note={total ? t(`${Math.round(aiCount / total * 100)}% of all traffic`, `tüm trafiğin %${Math.round(aiCount / total * 100)}’i`) : undefined} />
        <StatCard label={t('Assistant Browse', 'Asistan Gezinme')} value={assistants}
          note={total ? `${Math.round(assistants / total * 100)}%` : undefined} />
        <StatCard label={t('Crawlers', 'Tarayıcılar')}         value={crawlers}
          note={total ? `${Math.round(crawlers / total * 100)}%` : undefined} />
      </div>

      <TrafficBar events={events} />

      {/* ── Time-series chart ── */}
      <div style={{ background: '#fff', border: '1px solid #e4e4e7', borderRadius: '8px', padding: '18px 20px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '12px' }}>
          <span style={{ fontSize: '13px', fontWeight: 600, color: '#09090b' }}>{t('Hourly Traffic', 'Saatlik Trafik')}</span>
          <span style={{ fontSize: '11px', color: '#a1a1aa' }}>{t('last 24 h · refreshes every 30 s', 'son 24 sa · 30 sn’de bir yenilenir')}</span>
        </div>
        <TimeSeriesChart buckets={stats?.hourly_buckets ?? []} />
      </div>

      {/* ── Request table ── */}
      <div style={{ background: '#fff', border: '1px solid #e4e4e7', borderRadius: '8px', overflow: 'hidden' }}>

        <div style={{ padding: '14px 20px', borderBottom: '1px solid #e4e4e7' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <span style={{ fontSize: '13px', fontWeight: 600, color: '#09090b' }}>{t('Requests', 'İstekler')}</span>
            <span style={{ fontSize: '11px', color: '#a1a1aa', fontVariantNumeric: 'tabular-nums' }}>
              {hasFilter ? t(`${filteredEvents.length} of ${total} shown`, `${total} olaydan ${filteredEvents.length} tanesi`) : t(`${total} events`, `${total} olay`)}
            </span>
          </div>

          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
            {Object.entries(VERDICT_STYLE).map(([v, s]) => {
              const active = filterVerdicts.has(v)
              return (
                <button key={v} className="vbtn" onClick={() => toggleVerdict(v)} style={{
                  padding: '3px 10px', borderRadius: '4px', fontSize: '11px', fontWeight: 600,
                  border: `1px solid ${active ? s.border : '#e4e4e7'}`,
                  background: active ? s.bg : 'transparent',
                  color: active ? s.color : '#a1a1aa',
                }}>
                  {s.label}
                </button>
              )
            })}

            <input
              type="text"
              placeholder={t('Filter path…', 'Yol filtrele…')}
              value={pathQuery}
              onChange={e => setPathQuery(e.target.value)}
              style={{
                padding: '3px 10px', borderRadius: '4px', fontSize: '11px',
                border: '1px solid #e4e4e7', background: '#fafafa', color: '#09090b',
                fontFamily: 'ui-monospace, monospace', width: '160px',
              }}
            />

            {hasFilter && (
              <button className="vbtn" onClick={() => { setFilterVerdicts(new Set()); setPathQuery('') }}
                style={{ padding: '3px 8px', borderRadius: '4px', fontSize: '11px', border: '1px solid #e4e4e7', background: 'transparent', color: '#71717a' }}>
                {t('Clear', 'Temizle')}
              </button>
            )}
          </div>
        </div>

        {isLoading ? (
          <div style={{ padding: '56px', textAlign: 'center', color: '#a1a1aa', fontSize: '13px' }}>{t('Loading…', 'Yükleniyor…')}</div>
        ) : total === 0 ? (
          <div style={{ padding: '48px 24px', textAlign: 'center' }}>
            <div style={{ fontSize: '14px', fontWeight: 600, color: '#09090b', marginBottom: '6px' }}>{t('No requests recorded yet', 'Henüz istek kaydedilmedi')}</div>
            <div style={{ fontSize: '12.5px', color: '#71717a', marginBottom: '16px' }}>
              {t('Simulate AI agents visiting your store in real-time using the buttons below:', 'Aşağıdaki butonlarla mağazanızı ziyaret eden AI ajanlarını gerçek zamanlı simüle edin:')}
            </div>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
              {['chatgpt', 'claude', 'perplexity'].map(agent => (
                <button key={agent} className="vbtn" onClick={() => onSimulate(agent)} style={{
                  padding: '8px 16px', borderRadius: '6px', fontSize: '12px', fontWeight: 600,
                  background: '#09090b', color: '#fff', border: 'none', cursor: 'pointer',
                  display: 'inline-flex', alignItems: 'center', gap: '5px',
                }}>
                  🤖 {t('Simulate', 'Simüle et:')} {agent.charAt(0).toUpperCase() + agent.slice(1)}
                </button>
              ))}
            </div>
          </div>
        ) : filteredEvents.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: '#a1a1aa', fontSize: '13px' }}>
            {t('No results match the current filters.', 'Mevcut filtrelerle eşleşen sonuç yok.')}
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12.5px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #e4e4e7' }}>
                  {[t('Time', 'Zaman'), t('Method', 'Metot'), t('Path', 'Yol'), t('UA', 'UA'), t('Verdict', 'Karar'), t('Evidence', 'Kanıt'), t('Conf.', 'Güven'), t('Status', 'Durum')].map(h => (
                    <th key={h} style={{
                      padding: '9px 16px', textAlign: 'left',
                      fontSize: '11px', fontWeight: 600, color: '#71717a',
                      textTransform: 'uppercase', letterSpacing: '0.06em',
                      background: '#fafafa', whiteSpace: 'nowrap',
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredEvents.map((e, i) => {
                  const isNew = newIds.has(e.id)
                  return (
                    <tr
                      key={e.id}
                      className={`row-hover${isNew ? ' row-new' : ''}`}
                      onMouseEnter={() => setHoveredRow(e.id)}
                      onMouseLeave={() => setHoveredRow(null)}
                      style={{
                        borderBottom: i < filteredEvents.length - 1 ? '1px solid #f4f4f5' : 'none',
                        background: hoveredRow === e.id ? '#fafafa' : '#fff',
                        transition: 'background 120ms',
                      }}
                    >
                      <td style={{ padding: '10px 16px', color: '#71717a', whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums', fontFamily: 'ui-monospace, monospace', fontSize: '12px' }}>
                        {new Date(e.ts.endsWith('Z') ? e.ts : e.ts + 'Z').toLocaleTimeString('en-GB')}
                      </td>
                      <td style={{ padding: '10px 16px', fontFamily: 'ui-monospace, monospace', fontWeight: 700, fontSize: '11px', color: '#09090b', letterSpacing: '0.04em' }}>
                        {e.method}
                      </td>
                      <td style={{ padding: '10px 16px', fontFamily: 'ui-monospace, monospace', color: '#3f3f46', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '12px' }} title={e.path}>
                        {e.path}
                      </td>
                      <td style={{ padding: '10px 16px', maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={e.ua}>
                        <span style={{ fontFamily: 'ui-monospace, monospace', fontSize: '11px', color: '#52525b' }}>
                          {e.ua || <span style={{ color: '#a1a1aa' }}>—</span>}
                        </span>
                      </td>
                      <td style={{ padding: '10px 16px', whiteSpace: 'nowrap' }}>
                        <AgentBadge verdict={e.verdict} />
                      </td>
                      <td style={{ padding: '10px 16px', minWidth: '150px' }}>
                        <EvidenceChips evidence={e.evidence} />
                      </td>
                      <td style={{ padding: '10px 16px', color: '#71717a', fontSize: '12px', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
                        {e.confidence != null ? `${Math.round(e.confidence * 100)}%` : '—'}
                      </td>
                      <td style={{ padding: '10px 16px', whiteSpace: 'nowrap' }}>
                        <StatusChip code={e.status} />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  )
}
