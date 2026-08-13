import { useEffect, useRef, useState } from 'react'
import type { AgoraEvent, AuditResult, BenchmarkData, DemandData, StatsData } from './types'
import { Landing } from './pages/Landing'
import { Feed } from './pages/Feed'
import { Auditor } from './pages/Auditor'
import { Intelligence } from './pages/Intelligence'
import { Admin } from './pages/Admin'
import { AgoraMark } from './components/AgoraMark'
import { API } from './api'

type Tab = 'landing' | 'feed' | 'auditor' | 'intelligence' | 'admin'

const TABS: Array<{ id: Tab; label: string }> = [
  { id: 'landing', label: 'Overview' },
  { id: 'feed', label: 'Live Request Feed' },
  { id: 'auditor', label: 'AI Storefront Auditor' },
  { id: 'intelligence', label: 'Agent Intelligence' },
  { id: 'admin', label: 'Leads' },
]

const SITE_ID = 'demo-site'

export default function App() {
  const [currentTab, setCurrentTab] = useState<Tab>('landing')

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
          if (!r.ok) throw new Error(`Server error (${r.status}). Please try again.`)
          throw new Error('Invalid JSON response from server')
        }
        if (!r.ok) {
          throw new Error(data?.detail || 'Failed to crawl page')
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
      es = new EventSource('/events/stream')
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
    <div style={{ fontFamily: "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif", background: '#fafafa', minHeight: '100vh', color: '#09090b' }}>

      <style>{`
        .row-hover:hover { background: #fafafa !important; }
        .row-new { animation: flash 1.4s ease-out; }
        @keyframes flash { 0% { background: #f0fdf4; } 100% { background: transparent; } }
        .vbtn { transition: all 120ms; cursor: pointer; }
        .vbtn:hover { opacity: 0.85; }
        .vbtn:disabled { opacity: 0.55; cursor: wait; }
        .qbtn {
          padding: 4px 10px; font-size: 11px; color: #52525b; cursor: pointer;
          border: 1px solid #e4e4e7; background: #fff; border-radius: 4px;
          transition: all 120ms;
        }
        .qbtn:hover { border-color: #09090b; color: #09090b; }
        .stepcard { transition: border-color 150ms, transform 150ms, box-shadow 150ms; }
        .stepcard:hover { border-color: #a1a1aa !important; box-shadow: 0 4px 12px rgba(0,0,0,0.04); }
        input:focus { outline: 2px solid #3b82f6; outline-offset: 1px; }
      `}</style>

      {/* ── App bar: brand left, nav right ── */}
      <header style={{ background: '#09090b', position: 'sticky', top: 0, zIndex: 10 }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '0 32px', height: '56px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '24px' }}>
          {/* brand */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '11px', flexShrink: 0 }}>
            <AgoraMark size={24} />
            <span style={{ fontSize: '15px', fontWeight: 700, color: '#fafafa', letterSpacing: '-0.02em' }}>AGORA</span>
            <span style={{ width: '1px', height: '15px', background: '#27272a' }} />
            <span style={{ fontSize: '12px', color: '#71717a', letterSpacing: '0.01em' }}>AI Traffic Analytics</span>
          </div>
          {/* nav */}
          <nav style={{ display: 'flex', alignItems: 'center', gap: '4px', overflowX: 'auto' }}>
            {TABS.map(tab => {
              const isActive = currentTab === tab.id
              return (
                <button
                  key={tab.id}
                  onClick={() => setCurrentTab(tab.id)}
                  style={{
                    padding: '7px 12px', fontSize: '13px', fontWeight: 600, whiteSpace: 'nowrap',
                    border: 'none', borderRadius: '7px', cursor: 'pointer', transition: 'color 120ms, background 120ms',
                    background: isActive ? '#27272a' : 'transparent',
                    color: isActive ? '#fafafa' : '#a1a1aa',
                  }}
                  onMouseEnter={e => { if (!isActive) e.currentTarget.style.color = '#fafafa' }}
                  onMouseLeave={e => { if (!isActive) e.currentTarget.style.color = '#a1a1aa' }}
                >
                  {tab.label}
                </button>
              )
            })}
          </nav>
        </div>
      </header>

      <main style={{ maxWidth: '1280px', margin: '0 auto', padding: '16px 32px' }}>
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
      </main>
    </div>
  )
}
