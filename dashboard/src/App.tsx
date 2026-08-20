import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import type { AgoraEvent, AuditResult, BenchmarkData, DemandData, StatsData } from './types'
import { Landing } from './pages/Landing'

// Only Landing paints on first load. The rest are split into their own chunks
// so the initial mobile download and parse stay small.
const Feed = lazy(() => import('./pages/Feed').then(m => ({ default: m.Feed })))
const Auditor = lazy(() => import('./pages/Auditor').then(m => ({ default: m.Auditor })))
const Intelligence = lazy(() => import('./pages/Intelligence').then(m => ({ default: m.Intelligence })))
const Admin = lazy(() => import('./pages/Admin').then(m => ({ default: m.Admin })))
import { BrandBadge } from './components/BrandBadge'
import { LanguageToggle } from './components/LanguageToggle'
import { useI18n } from './i18n'
import { API } from './api'

type Tab = 'landing' | 'feed' | 'auditor' | 'intelligence' | 'admin'

const SITE_ID = 'demo-site'

type Translate = (en: string, tr: string) => string
type AuditErrorDetail = { code?: string; message?: string; status?: number }

/**
 * Turn the backend's structured {code, message} audit error into a friendly,
 * localized sentence. The user should never see a raw technical string such as
 * "Target server returned error status 403".
 */
function friendlyAuditError(detail: unknown, status: number, t: Translate): string {
  const d = (detail && typeof detail === 'object' ? detail : {}) as AuditErrorDetail
  switch (d.code) {
    case 'blocked':
      return t(
        "This site blocks automated audits — it sits behind bot protection (like Cloudflare) that refuses our servers. Sites without that protection audit fine.",
        'Bu site otomatik denetimleri engelliyor — sunucularımızı reddeden bir bot koruması (ör. Cloudflare) arkasında. Bu koruması olmayan siteler sorunsuz denetlenir.',
      )
    case 'not_found':
      return t(
        'No page was found at that URL (404). Check the address and try the homepage.',
        'Bu adreste sayfa bulunamadı (404). Adresi kontrol edip ana sayfayı deneyin.',
      )
    case 'unreachable':
      return t(
        "The site didn't respond in time or refused the connection. It may be slow or blocking our servers.",
        'Site zamanında yanıt vermedi ya da bağlantıyı reddetti. Yavaş olabilir veya sunucularımızı engelliyor olabilir.',
      )
    case 'too_large':
      return t(
        'This page is too large to audit (over 2 MB).',
        'Bu sayfa denetlenemeyecek kadar büyük (2 MB üzeri).',
      )
    case 'server_error':
      return t(
        'The site returned a server error. Try again in a moment.',
        'Site bir sunucu hatası döndürdü. Birazdan tekrar deneyin.',
      )
    case 'refused':
      return t(
        'That URL was refused for security reasons.',
        'Bu URL güvenlik nedeniyle reddedildi.',
      )
    case 'client_error':
      return t(
        "The site didn't return a readable page.",
        'Site okunabilir bir sayfa döndürmedi.',
      )
  }
  if (typeof detail === 'string' && detail) return detail
  if (typeof d.message === 'string' && d.message) return d.message
  if (!status || status >= 500) {
    return t('Something went wrong on our side. Please try again.', 'Tarafımızda bir sorun oluştu. Lütfen tekrar deneyin.')
  }
  return t('We couldn’t audit that URL.', 'Bu URL denetlenemedi.')
}

export default function App() {
  const { t } = useI18n()
  const [currentTab, setCurrentTab] = useState<Tab>('landing')

  // Top bar turns to translucent glass once the page is scrolled past the top.
  const [isScrolled, setIsScrolled] = useState(false)
  useEffect(() => {
    const onScroll = () => setIsScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const tabs: Array<{ id: Tab; label: string }> = [
    { id: 'landing', label: t('Overview', 'Genel Bakış') },
    { id: 'feed', label: t('Live Request Feed', 'Canlı İstek Akışı') },
    { id: 'auditor', label: t('AI Storefront Auditor', 'AI Mağaza Denetleyici') },
    { id: 'intelligence', label: t('Agent Intelligence', 'Ajan İstihbaratı') },
    { id: 'admin', label: t('Leads', 'Kayıtlar') },
  ]

  // Audit state — shared between Landing (hero input) and Auditor (results)
  const [auditUrl, setAuditUrl] = useState('')
  const [auditResult, setAuditResult] = useState<AuditResult | null>(null)
  const [isAuditLoading, setIsAuditLoading] = useState(false)
  const [auditError, setAuditError] = useState<string | null>(null)

  // Live feed state
  const [events, setEvents] = useState<AgoraEvent[]>([])
  const [stats, setStats] = useState<StatsData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [streamMode, setStreamMode] = useState<'sse' | 'poll'>('sse')
  const [newIds, setNewIds] = useState<Set<number>>(new Set())
  const prevCount = useRef(0)

  // Agent Intelligence state (demand feed + category benchmark)
  const [demand, setDemand] = useState<DemandData | null>(null)
  const [benchmark, setBenchmark] = useState<BenchmarkData | null>(null)
  const [isIntelLoading, setIsIntelLoading] = useState(true)

  const applyNewEvents = (incoming: AgoraEvent[]) => {
    const ids = new Set(incoming.map(e => e.id))
    setEvents(prev => [...incoming, ...prev.filter(e => !ids.has(e.id))].slice(0, 200))
    setNewIds(new Set(incoming.map(e => e.id)))
    setTimeout(() => setNewIds(new Set()), 1500)
  }

  const handleAudit = (url: string) => {
    let targetUrl = url.trim()
    if (!targetUrl) return
    if (!targetUrl.startsWith('http://') && !targetUrl.startsWith('https://')) {
      targetUrl = 'https://' + targetUrl
    }
    setAuditUrl(targetUrl)
    setIsAuditLoading(true)
    setAuditError(null)
    setAuditResult(null)
    fetch(`${API}/report/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: targetUrl }),
    })
      .then(async r => {
        const text = await r.text()
        let data: any
        try {
          data = JSON.parse(text)
        } catch {
          throw new Error(
            t(
              `The server returned an unexpected response (${r.status}). Please try again.`,
              `Sunucu beklenmeyen bir yanıt döndürdü (${r.status}). Lütfen tekrar deneyin.`,
            ),
          )
        }
        if (!r.ok) {
          throw new Error(friendlyAuditError(data?.detail, r.status, t))
        }
        return data as AuditResult
      })
      .then((d: AuditResult) => {
        setAuditResult(d)
        setCurrentTab('auditor')
      })
      .catch(e => {
        setAuditError(e.message || 'Crawl request failed.')
      })
      .finally(() => {
        setIsAuditLoading(false)
      })
  }

  const fetchEvents = () => {
    fetch(`${API}/events?limit=200`)
      .then(r => { if (!r.ok) throw new Error(); return r.json() })
      .then((d: AgoraEvent[]) => {
        setEvents(d)
        if (prevCount.current > 0 && d.length > prevCount.current) {
          const fresh = new Set(d.slice(0, d.length - prevCount.current).map(e => e.id))
          setNewIds(fresh)
          setTimeout(() => setNewIds(new Set()), 1500)
        }
        prevCount.current = d.length
      })
      .catch(() => {})
      .finally(() => setIsLoading(false))
  }

  const fetchStats = () => {
    fetch(`${API}/stats?site_id=${SITE_ID}&window=24h`)
      .then(r => r.ok ? r.json() : null)
      .then((d: StatsData | null) => { if (d) setStats(d) })
      .catch(() => {})
  }

  const fetchIntel = () => {
    Promise.allSettled([
      fetch(`${API}/stats/demand?site_id=${SITE_ID}&window=24h`).then(r => r.ok ? r.json() : null),
      fetch(`${API}/stats/benchmark?site_id=${SITE_ID}&window=24h`).then(r => r.ok ? r.json() : null),
    ])
      .then(([d, b]) => {
        if (d.status === 'fulfilled' && d.value) setDemand(d.value as DemandData)
        if (b.status === 'fulfilled' && b.value) setBenchmark(b.value as BenchmarkData)
      })
      .finally(() => setIsIntelLoading(false))
  }

  const triggerSimulation = (agent: string) => {
    fetch(`${API}/events/simulate?agent=${agent}`, { method: 'POST' })
      .then(r => {
        if (r.ok) {
          setTimeout(() => {
            fetchStats()
            fetchEvents()
            fetchIntel()
          }, 400)
        }
      })
      .catch(() => {})
  }

  // SSE/polling for live events
  useEffect(() => {
    fetchEvents()

    let es: EventSource | null = null
    let pollId: ReturnType<typeof setInterval> | null = null

    const startSSE = () => {
      es = new EventSource(`${API}/events/stream`)
      es.onmessage = (ev) => {
        try {
          const e: AgoraEvent = JSON.parse(ev.data)
          applyNewEvents([e])
          setIsLoading(false)
        } catch { /* ignore malformed frames */ }
      }
      es.onerror = () => {
        es?.close()
        es = null
        setStreamMode('poll')
        pollId = setInterval(fetchEvents, 3000)
      }
    }

    startSSE()

    return () => {
      es?.close()
      if (pollId != null) clearInterval(pollId)
    }
  }, [])

  // Stats for time-series chart — refreshed every 30 s
  useEffect(() => {
    fetchStats()
    const statsId = setInterval(fetchStats, 30_000)
    return () => clearInterval(statsId)
  }, [])

  // Agent Intelligence — refreshed every 30 s
  useEffect(() => {
    fetchIntel()
    const intelId = setInterval(fetchIntel, 30_000)
    return () => clearInterval(intelId)
  }, [])

  return (
    <div style={{ fontFamily: "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif", background: 'var(--bg)', minHeight: '100vh', color: 'var(--ink)' }}>

      <style>{`
        .row-hover:hover { background: var(--bg) !important; }
        .row-new { animation: flash 1.6s ease-out; }
        @keyframes flash { 0% { background: var(--accent-tint); } 100% { background: transparent; } }
        .vbtn { transition: background 160ms ease, opacity 160ms ease, transform 160ms ease; cursor: pointer; }
        .vbtn:hover { opacity: 0.92; }
        .vbtn:active { transform: translateY(1px); }
        .vbtn:disabled { opacity: 0.55; cursor: wait; }
        .qbtn {
          padding: 4px 10px; font-size: 11px; color: var(--muted); cursor: pointer;
          border: 1px solid var(--border); background: var(--surface); border-radius: 4px;
          transition: border-color 160ms ease, color 160ms ease;
        }
        .qbtn:hover { border-color: var(--accent); color: var(--accent); }
        .stepcard { transition: border-color 180ms ease, transform 180ms ease, box-shadow 180ms ease; }
        .stepcard:hover { border-color: var(--accent) !important; box-shadow: 0 6px 18px rgba(53,133,123,0.10); }
        input:focus { outline: 2px solid var(--accent); outline-offset: 1px; }
      `}</style>

      {/* ── App bar: brand left, nav right ── */}
      <header style={{
        position: 'sticky', top: 0, zIndex: 10,
        background: isScrolled ? 'var(--bar-glass)' : 'var(--bar-bg)',
        backdropFilter: isScrolled ? 'saturate(180%) blur(14px)' : 'none',
        WebkitBackdropFilter: isScrolled ? 'saturate(180%) blur(14px)' : 'none',
        borderBottom: isScrolled ? '1px solid var(--border)' : '1px solid transparent',
        boxShadow: isScrolled ? '0 1px 3px rgba(0,0,0,0.05)' : 'none',
        transition: 'background 240ms ease, box-shadow 240ms ease, border-color 240ms ease',
      }}>
        <div className="app-header-inner">
          {/* brand — click returns to the Overview / landing page */}
          <button
            onClick={() => setCurrentTab('landing')}
            aria-label={t('Go to home', 'Ana sayfaya git')}
            style={{
              display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0,
              background: 'transparent', border: 'none', padding: 0, cursor: 'pointer',
            }}
          >
            <BrandBadge size={28} />
            <span style={{ fontSize: '15px', fontWeight: 600, color: 'var(--ink)', letterSpacing: '-0.01em' }}>AGORA</span>
            <span className="brand-separator" style={{ width: '1px', height: '15px', background: 'var(--border)' }} />
            <span className="brand-subtext" style={{ fontSize: '12px', color: 'var(--muted)', letterSpacing: '0.01em' }}>{t('AI Traffic Analytics', 'AI Trafik Analitiği')}</span>
          </button>

          {/* Language toggle on mobile / desktop */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <LanguageToggle />
          </div>

          {/* nav in responsive wrapper */}
          <div className="app-nav-wrapper" style={{ display: 'flex', alignItems: 'center', minWidth: 0 }}>
            <nav className="app-nav">
              {tabs.map(tab => {
                const isActive = currentTab === tab.id
                return (
                  <button
                    key={tab.id}
                    onClick={() => setCurrentTab(tab.id)}
                    style={{
                      padding: '7px 12px', fontSize: '13px', fontWeight: 600, whiteSpace: 'nowrap',
                      border: 'none', borderRadius: '7px', cursor: 'pointer', transition: 'color 160ms ease, background 160ms ease',
                      background: isActive ? 'var(--accent-tint)' : 'transparent',
                      color: isActive ? 'var(--accent-strong)' : 'var(--muted)',
                    }}
                    onMouseEnter={e => { if (!isActive) e.currentTarget.style.color = 'var(--ink)' }}
                    onMouseLeave={e => { if (!isActive) e.currentTarget.style.color = 'var(--muted)' }}
                  >
                    {tab.label}
                  </button>
                )
              })}
            </nav>
          </div>
        </div>
      </header>

      <main className="app-main">
        <Suspense fallback={<div style={{ padding: '48px 0', textAlign: 'center', color: 'var(--muted)', fontSize: '13px' }}>{t('Loading…', 'Yükleniyor…')}</div>}>
          {currentTab === 'landing' ? (
            <Landing
              auditUrl={auditUrl}
              onAuditUrlChange={setAuditUrl}
              onAudit={handleAudit}
              isAuditLoading={isAuditLoading}
              auditError={auditError}
              onOpenFeed={() => setCurrentTab('feed')}
              onOpenAuditor={() => setCurrentTab('auditor')}
            />
          ) : currentTab === 'feed' ? (
            <Feed
              events={events}
              stats={stats}
              isLoading={isLoading}
              streamMode={streamMode}
              newIds={newIds}
              onSimulate={triggerSimulation}
            />
          ) : currentTab === 'auditor' ? (
            <Auditor
              auditUrl={auditUrl}
              onAuditUrlChange={setAuditUrl}
              onAudit={handleAudit}
              isAuditLoading={isAuditLoading}
              auditError={auditError}
              auditResult={auditResult}
            />
          ) : currentTab === 'intelligence' ? (
            <Intelligence demand={demand} benchmark={benchmark} isLoading={isIntelLoading} />
          ) : (
            <Admin />
          )}
        </Suspense>
      </main>
    </div>
  )
}
