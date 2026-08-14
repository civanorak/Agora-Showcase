import type { BenchmarkData, DemandData } from '../types'
import { verdictStyle } from '../verdicts'
import { StatCard } from '../components/shared'
import { useI18n } from '../i18n'

interface IntelligenceProps {
  demand: DemandData | null
  benchmark: BenchmarkData | null
  isLoading: boolean
}

/** 2xx answer-rate color: healthy green, weak amber, failing red. */
function rateColor(rate: number): { color: string; bg: string; border: string } {
  if (rate >= 0.9) return { color: '#166534', bg: '#f0fdf4', border: '#bbf7d0' }
  if (rate >= 0.5) return { color: '#92400e', bg: '#fffbeb', border: '#fde68a' }
  return { color: '#991b1b', bg: '#fef2f2', border: '#fecaca' }
}

function fmtPct(rate: number): string {
  return `${Math.round(rate * 100)}%`
}

function fmtTime(ts: string): string {
  const d = new Date(ts.endsWith('Z') ? ts : ts + 'Z')
  return d.toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export function Intelligence({ demand, benchmark, isLoading }: IntelligenceProps) {
  const { t } = useI18n()
  return (
    <>
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ fontSize: '20px', fontWeight: 700, color: '#09090b', margin: 0, letterSpacing: '-0.02em' }}>
          {t('Agent Intelligence', 'Ajan İstihbaratı')}
        </h1>
        <p style={{ fontSize: '13px', color: '#71717a', margin: '5px 0 0', lineHeight: 1.5 }}>
          {t(
            'What agents ask for, and where you rank against your category — the layer only measured stores can see.',
            'Ajanların ne istediği ve kategorinizdeki sıralamanız — yalnızca ölçülen mağazaların görebildiği katman.',
          )}
        </p>
      </div>

      <DemandPanel demand={demand} isLoading={isLoading} />
      <BenchmarkPanel benchmark={benchmark} isLoading={isLoading} />
    </>
  )
}

// ── Panel 1: Agent Demand ─────────────────────────────────────────────
function DemandPanel({ demand, isLoading }: { demand: DemandData | null; isLoading: boolean }) {
  const { t } = useI18n()
  const products = demand?.top_products ?? []
  const totalHits = demand?.total_agent_hits ?? 0
  const unmet = products.filter(p => p.success_rate < 1).length

  return (
    <section style={{ marginBottom: '32px' }}>
      <SectionHeading
        title={t('Agent Demand', 'Ajan Talebi')}
        subtitle={t(
          'Products agents requested, and whether your store could answer (2xx). Low answer rates are demand you are losing.',
          'Ajanların talep ettiği ürünler ve mağazanızın yanıt verip veremediği (2xx). Düşük yanıt oranları kaybettiğiniz taleptir.',
        )}
      />

      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' }}>
        <StatCard label={t('Agent Requests', 'Ajan İstekleri')} value={totalHits} />
        <StatCard label={t('Products Asked', 'Sorulan Ürünler')} value={products.length} />
        <StatCard
          label={t('Underserved', 'Karşılanmayan')}
          value={unmet}
          note={products.length ? t(`${unmet} of ${products.length} not fully answered`, `${products.length} üründen ${unmet} tanesi tam yanıtlanmadı`) : undefined}
        />
      </div>

      <div style={{ background: '#fff', border: '1px solid #e4e4e7', borderRadius: '8px', overflow: 'hidden' }}>
        {isLoading ? (
          <EmptyRow>{t('Loading…', 'Yükleniyor…')}</EmptyRow>
        ) : products.length === 0 ? (
          <EmptyRow>
            {t(
              'No agent demand in this window yet. Once agents hit your store, the products they ask for surface here.',
              'Bu pencerede henüz ajan talebi yok. Ajanlar mağazanıza ulaştığında, sordukları ürünler burada görünür.',
            )}
          </EmptyRow>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12.5px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #e4e4e7' }}>
                  {[t('Path', 'Yol'), t('Agent Hits', 'Ajan İsabeti'), t('Answered', 'Yanıtlanan'), t('Agent Types', 'Ajan Türleri'), t('Last Seen', 'Son Görülme')].map(h => (
                    <th key={h} style={thStyle}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {products.map((p, i) => {
                  const rc = rateColor(p.success_rate)
                  return (
                    <tr key={p.path} className="row-hover" style={{
                      borderBottom: i < products.length - 1 ? '1px solid #f4f4f5' : 'none',
                    }}>
                      <td style={{ ...tdStyle, fontFamily: 'ui-monospace, monospace', color: '#3f3f46', maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={p.path}>
                        {p.path}
                      </td>
                      <td style={{ ...tdStyle, fontVariantNumeric: 'tabular-nums', fontWeight: 700, color: '#09090b' }}>
                        {p.agent_hits}
                      </td>
                      <td style={tdStyle}>
                        <span style={{
                          display: 'inline-block', padding: '2px 8px', borderRadius: '4px',
                          fontSize: '11px', fontWeight: 700, fontVariantNumeric: 'tabular-nums',
                          color: rc.color, background: rc.bg, border: `1px solid ${rc.border}`,
                        }}>
                          {fmtPct(p.success_rate)}
                        </span>
                      </td>
                      <td style={{ ...tdStyle, minWidth: '160px' }}>
                        <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                          {Object.entries(p.verdicts).map(([v, n]) => {
                            const s = verdictStyle(v)
                            return (
                              <span key={v} title={`${s.label}: ${n}`} style={{
                                display: 'inline-flex', gap: '4px', alignItems: 'center',
                                padding: '1px 7px', borderRadius: '4px', fontSize: '10.5px', fontWeight: 600,
                                color: s.color, background: s.bg, border: `1px solid ${s.border}`,
                              }}>
                                {s.label} <span style={{ opacity: 0.7 }}>{n}</span>
                              </span>
                            )
                          })}
                        </div>
                      </td>
                      <td style={{ ...tdStyle, color: '#71717a', whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums' }}>
                        {fmtTime(p.last_seen)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  )
}

// ── Panel 2: Category Benchmark ───────────────────────────────────────
function BenchmarkPanel({ benchmark, isLoading }: { benchmark: BenchmarkData | null; isLoading: boolean }) {
  const { t } = useI18n()
  const board = benchmark?.leaderboard ?? []
  // In the public sandbox there is no live category traffic, so the leaderboard
  // has no real peers to rank. Rather than show a broken/empty table, present an
  // honest "coming soon — needs live traffic" state. The real table below still
  // renders once a measured store (pilot) produces category data.
  const noLiveData = !isLoading && (benchmark == null || benchmark.category == null || board.length === 0)

  return (
    <section style={{ marginBottom: '32px' }}>
      <SectionHeading
        title={t('Category Benchmark', 'Kategori Kıyaslaması')}
        subtitle={t(
          'How your agent-readability ranks against peers in your category. Competitors are anonymized.',
          'Ajan-okunabilirliğinizin kategorinizdeki emsallere göre sıralaması. Rakipler anonimleştirilir.',
        )}
      />

      {isLoading ? (
        <div style={{ background: '#fff', border: '1px solid #e4e4e7', borderRadius: '8px' }}>
          <EmptyRow>{t('Loading…', 'Yükleniyor…')}</EmptyRow>
        </div>
      ) : noLiveData ? (
        <ComingSoonCard
          title={t('Requires live traffic', 'Canlı trafik gerektirir')}
          body={t(
            'The category leaderboard ranks your store against anonymized peers once the AGORA collector is measuring real agent traffic. Join the pilot to unlock it.',
            'Kategori sıralaması, AGORA toplayıcısı gerçek ajan trafiğini ölçmeye başladığında mağazanızı anonim emsallerle kıyaslar. Açmak için pilota katılın.',
          )}
        />
      ) : (
        <BenchmarkTable benchmark={benchmark} board={board} />
      )}
    </section>
  )
}

function ComingSoonCard({ title, body }: { title: string; body: string }) {
  return (
    <div style={{
      background: '#fff', border: '1px dashed #d4d4d8', borderRadius: '12px',
      padding: '40px 32px', textAlign: 'center', maxWidth: '560px', margin: '0 auto',
    }}>
      <div style={{ fontSize: '28px', marginBottom: '12px' }}>📡</div>
      <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#09090b', margin: '0 0 8px' }}>{title}</h3>
      <p style={{ fontSize: '13px', color: '#71717a', lineHeight: 1.6, margin: 0 }}>{body}</p>
    </div>
  )
}

function BenchmarkTable({ benchmark, board }: { benchmark: BenchmarkData | null; board: BenchmarkData['leaderboard'] }) {
  const { t } = useI18n()
  return (
    <>
      {benchmark?.category && benchmark.your_rank != null && (
        <div style={{
          background: '#fff', border: '1px solid #e4e4e7', borderRadius: '8px',
          padding: '20px 22px', marginBottom: '16px',
        }}>
          <div style={{ fontSize: '11px', fontWeight: 600, color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
            {t('Your Rank', 'Sıralamanız')} · {benchmark.category}
          </div>
          <div style={{ fontSize: '30px', fontWeight: 700, color: '#09090b', marginTop: '8px', lineHeight: 1, letterSpacing: '-0.02em' }}>
            #{benchmark.your_rank}
            <span style={{ fontSize: '16px', color: '#a1a1aa', fontWeight: 600 }}> {t('of', '/')} {benchmark.total_in_category}</span>
          </div>
        </div>
      )}

      <div style={{ background: '#fff', border: '1px solid #e4e4e7', borderRadius: '8px', overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12.5px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #e4e4e7' }}>
                  {[t('Rank', 'Sıra'), t('Store', 'Mağaza'), t('Readiness', 'Hazırlık'), t('Agent Hits', 'Ajan İsabeti'), ''].map((h, idx) => (
                    <th key={idx} style={thStyle}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {board.map((row, i) => {
                  const rc = rateColor(row.agent_success_rate)
                  return (
                    <tr key={row.rank} style={{
                      borderBottom: i < board.length - 1 ? '1px solid #f4f4f5' : 'none',
                      background: row.is_you ? '#f0f9ff' : '#fff',
                    }}>
                      <td style={{ ...tdStyle, fontWeight: 700, fontVariantNumeric: 'tabular-nums', color: '#09090b' }}>
                        #{row.rank}
                      </td>
                      <td style={tdStyle}>
                        <span style={{ fontWeight: row.is_you ? 700 : 500, color: row.is_you ? '#0369a1' : '#3f3f46' }}>
                          {row.label}
                        </span>
                        {row.is_you && (
                          <span style={{
                            marginLeft: '8px', fontSize: '10px', fontWeight: 700, color: '#0369a1',
                            background: '#e0f2fe', border: '1px solid #bae6fd', borderRadius: '4px', padding: '1px 6px',
                          }}>
                            {t('YOU', 'SİZ')}
                          </span>
                        )}
                      </td>
                      <td style={{ ...tdStyle, minWidth: '160px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <div style={{ flex: 1, maxWidth: '110px', height: '6px', borderRadius: '3px', background: '#f4f4f5', overflow: 'hidden' }}>
                            <div style={{ width: `${Math.round(row.agent_success_rate * 100)}%`, height: '100%', background: rc.color, opacity: 0.85 }} />
                          </div>
                          <span style={{ fontSize: '11.5px', fontWeight: 700, color: rc.color, fontVariantNumeric: 'tabular-nums' }}>
                            {fmtPct(row.agent_success_rate)}
                          </span>
                        </div>
                      </td>
                      <td style={{ ...tdStyle, fontVariantNumeric: 'tabular-nums', color: '#71717a' }}>
                        {row.agent_hits}
                      </td>
                      <td style={tdStyle} />
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
      </div>
    </>
  )
}

// ── Small shared bits ─────────────────────────────────────────────────
function SectionHeading({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div style={{ marginBottom: '14px' }}>
      <h2 style={{ fontSize: '15px', fontWeight: 700, color: '#09090b', margin: 0, letterSpacing: '-0.01em' }}>{title}</h2>
      <p style={{ fontSize: '12px', color: '#71717a', margin: '3px 0 0', lineHeight: 1.5, maxWidth: '640px' }}>{subtitle}</p>
    </div>
  )
}

function EmptyRow({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ padding: '40px', textAlign: 'center', color: '#a1a1aa', fontSize: '13px', lineHeight: 1.6, maxWidth: '520px', margin: '0 auto' }}>
      {children}
    </div>
  )
}

const thStyle: React.CSSProperties = {
  padding: '9px 16px', textAlign: 'left',
  fontSize: '11px', fontWeight: 600, color: '#71717a',
  textTransform: 'uppercase', letterSpacing: '0.06em',
  background: '#fafafa', whiteSpace: 'nowrap',
}

const tdStyle: React.CSSProperties = {
  padding: '10px 16px', fontSize: '12.5px', verticalAlign: 'middle',
}
