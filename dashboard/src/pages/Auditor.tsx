import { useState } from 'react'
import type { AuditResult, CatalogInfo } from '../types'
import { ChecklistItemView } from '../components/shared'
import { API } from '../api'

const SOURCE_LABEL: Record<string, string> = {
  products_json: 'Shopify /products.json',
  sitemap: 'sitemap.xml',
}

function CatalogRealityCard({ catalog }: { catalog: CatalogInfo }) {
  const hasNames = catalog.sample.length > 0
  const coverageColor = catalog.coverage_pct >= 70 ? '#166534' : catalog.coverage_pct >= 30 ? '#b45309' : '#b91c1c'
  return (
    <div style={{ background: '#fff', border: '1px solid #e4e4e7', borderRadius: '8px', padding: '20px 24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: '8px' }}>
        <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#09090b', margin: 0 }}>
          Catalog Reality vs Agent View
        </h3>
        <span style={{ fontSize: '11px', color: '#a1a1aa', fontFamily: 'ui-monospace, monospace' }}>
          source: {SOURCE_LABEL[catalog.source] ?? catalog.source}
        </span>
      </div>

      <div style={{ display: 'flex', gap: '32px', marginTop: '16px', flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: '11px', fontWeight: 600, color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
            Products in catalog
          </div>
          <div style={{ fontSize: '26px', fontWeight: 700, color: '#09090b', marginTop: '4px' }}>
            {catalog.total_count}
          </div>
        </div>
        {hasNames && (
          <>
            <div>
              <div style={{ fontSize: '11px', fontWeight: 600, color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
                Visible to agents
              </div>
              <div style={{ fontSize: '26px', fontWeight: 700, color: coverageColor, marginTop: '4px' }}>
                {catalog.visible_to_agent}
              </div>
            </div>
            <div style={{ flex: 1, minWidth: '220px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ fontSize: '11px', fontWeight: 600, color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
                  Agent coverage
                </span>
                <span style={{ fontSize: '12px', fontWeight: 700, color: coverageColor }}>
                  {catalog.coverage_pct}%
                </span>
              </div>
              <div style={{ height: '8px', borderRadius: '4px', background: '#f4f4f5', overflow: 'hidden' }}>
                <div style={{ width: `${Math.min(catalog.coverage_pct, 100)}%`, height: '100%', background: coverageColor, opacity: 0.85 }} />
              </div>
              <div style={{ fontSize: '11.5px', color: '#71717a', marginTop: '8px', lineHeight: 1.5 }}>
                {catalog.coverage_pct < 100
                  ? `An agent reading this page can quote only ${catalog.visible_to_agent} of your ${catalog.total_count} products. The generated /llms.txt below closes that gap with your full catalog.`
                  : 'Agents can find every catalog product on this page.'}
              </div>
            </div>
          </>
        )}
        {!hasNames && (
          <div style={{ flex: 1, minWidth: '220px', fontSize: '11.5px', color: '#71717a', alignSelf: 'center', lineHeight: 1.5 }}>
            Catalog size proven via {SOURCE_LABEL[catalog.source] ?? catalog.source}. Product names and prices
            were not exposed in a structured endpoint, so agent coverage cannot be measured.
          </div>
        )}
      </div>
    </div>
  )
}

function EmailCaptureCard({ url, coveragePct }: { url: string; coveragePct: number | null }) {
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle')

  const handleSubmit = () => {
    if (!email.trim()) return
    setStatus('submitting')
    fetch(`${API}/leads`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, url, coverage_pct: coveragePct }),
    })
      .then(r => { if (!r.ok) throw new Error(); setStatus('success') })
      .catch(() => setStatus('error'))
  }

  if (status === 'success') {
    return (
      <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '8px', padding: '16px 24px', fontSize: '13px', color: '#166534' }}>
        Kaydedildi — bu raporu inceleyip size dönüş yapacağız.
      </div>
    )
  }

  return (
    <div style={{ background: '#fff', border: '1px solid #e4e4e7', borderRadius: '8px', padding: '20px 24px' }}>
      <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#09090b', margin: '0 0 4px' }}>
        Bu raporu kaydedelim
      </h3>
      <p style={{ fontSize: '12.5px', color: '#71717a', margin: '0 0 14px', lineHeight: 1.5 }}>
        Email'inizi bırakın, bu audit sonucunu ve mağazanızı AI agent'lara açmak için gereken adımları gönderelim.
      </p>
      <div style={{ display: 'flex', gap: '10px' }}>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@company.com"
          style={{ flex: 1, padding: '9px 12px', borderRadius: '6px', border: '1px solid #e4e4e7', fontSize: '13px' }}
        />
        <button
          className="vbtn"
          onClick={handleSubmit}
          disabled={status === 'submitting'}
          style={{ padding: '9px 18px', borderRadius: '6px', fontSize: '13px', fontWeight: 600, background: '#09090b', color: '#fff', border: 'none', cursor: 'pointer' }}
        >
          {status === 'submitting' ? 'Gönderiliyor…' : 'Kaydet'}
        </button>
      </div>
      {status === 'error' && (
        <p style={{ fontSize: '12px', color: '#b91c1c', margin: '8px 0 0' }}>Bir şeyler ters gitti, tekrar deneyin.</p>
      )}
    </div>
  )
}

interface AuditorProps {
  auditUrl: string
  onAuditUrlChange: (url: string) => void
  onAudit: (url: string) => void
  isAuditLoading: boolean
  auditError: string | null
  auditResult: AuditResult | null
}

export function Auditor({ auditUrl, onAuditUrlChange, onAudit, isAuditLoading, auditError, auditResult }: AuditorProps) {
  const [activeView, setActiveView] = useState<'llms' | 'markdown'>('llms')
  const [copied, setCopied] = useState(false)

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    }).catch(() => {})
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      <div>
        <h1 style={{ fontSize: '20px', fontWeight: 700, color: '#09090b', margin: 0, letterSpacing: '-0.02em' }}>
          AI Storefront Auditor
        </h1>
        <p style={{ fontSize: '13px', color: '#71717a', margin: '5px 0 0', lineHeight: 1.5 }}>
          Crawl any URL to audit machine-readability, token efficiency, and AI bot agent friendliness.
        </p>
      </div>

      {/* Audit input */}
      <div style={{ background: '#fff', border: '1px solid #e4e4e7', borderRadius: '8px', padding: '20px 24px' }}>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <input
            type="text"
            value={auditUrl}
            onChange={(e) => onAuditUrlChange(e.target.value)}
            placeholder="https://your-store.com"
            style={{
              flex: 1, padding: '10px 14px', borderRadius: '6px', border: '1px solid #e4e4e7', fontSize: '13px',
              fontFamily: 'ui-monospace, monospace',
            }}
          />
          <button
            className="vbtn"
            onClick={() => onAudit(auditUrl)}
            disabled={isAuditLoading}
            style={{
              padding: '10px 20px', borderRadius: '6px', fontSize: '13px', fontWeight: 600,
              background: '#09090b', color: '#fff', border: 'none', cursor: 'pointer',
              minWidth: '150px', textAlign: 'center',
            }}
          >
            {isAuditLoading ? 'Auditing…' : 'Analyze URL'}
          </button>
        </div>

        <div style={{ display: 'flex', gap: '8px', marginTop: '12px', alignItems: 'center' }}>
          <span style={{ fontSize: '11px', color: '#a1a1aa' }}>Quick targets:</span>
          <button className="qbtn" onClick={() => { onAuditUrlChange('http://localhost:8000'); onAudit('http://localhost:8000') }}>
            Local API (Host)
          </button>
          <button className="qbtn" onClick={() => { onAuditUrlChange('http://localhost:8000/llms.txt'); onAudit('http://localhost:8000/llms.txt') }}>
            Local /llms.txt
          </button>
        </div>
      </div>

      {auditError && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c', padding: '14px 18px', borderRadius: '8px', fontSize: '13px' }}>
          <strong>Error:</strong> {auditError}
        </div>
      )}

      {auditResult && (
        <>
          {auditResult.catalog && (
            <CatalogRealityCard catalog={auditResult.catalog} />
          )}

          <div id="lead-capture">
            <EmailCaptureCard url={auditResult.url} coveragePct={auditResult.catalog?.coverage_pct ?? null} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', alignItems: 'start' }}>

            {/* Left: metrics + checklist */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

              <div style={{ background: '#fff', border: '1px solid #e4e4e7', borderRadius: '8px', padding: '20px 24px' }}>
                <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#09090b', marginTop: 0, marginBottom: '16px' }}>
                  Computed Crawl Metrics
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', borderBottom: '1px dashed #f4f4f5', paddingBottom: '8px' }}>
                    <span style={{ color: '#71717a' }}>Total Download Size</span>
                    <strong style={{ color: '#09090b' }}>{(auditResult.total_bytes / 1024).toFixed(1)} KB ({auditResult.total_bytes} bytes)</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', borderBottom: '1px dashed #f4f4f5', paddingBottom: '8px' }}>
                    <span style={{ color: '#71717a' }}>Script-to-Content Ratio</span>
                    <strong style={{ color: '#09090b' }}>{auditResult.script_ratio}%</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                    <span style={{ color: '#71717a' }}>Extractable-Text %</span>
                    <strong style={{ color: '#09090b' }}>{auditResult.extractable_text_pct}%</strong>
                  </div>
                </div>
              </div>

              <div style={{ background: '#fff', border: '1px solid #e4e4e7', borderRadius: '8px', padding: '20px 24px' }}>
                <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#09090b', marginTop: 0, marginBottom: '16px' }}>
                  AI Readiness Checklist
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <ChecklistItemView
                    label="/llms.txt exists and serves your catalog"
                    pass={auditResult.checklist.llms_txt.pass_status}
                    evidence={auditResult.checklist.llms_txt.evidence}
                  />
                  <ChecklistItemView
                    label="Product pricing & metadata parsed"
                    pass={auditResult.checklist.product_content.pass_status}
                    evidence={auditResult.checklist.product_content.evidence}
                  />
                  <ChecklistItemView
                    label="schema.org Product metadata tags found"
                    pass={auditResult.checklist.schema_org.pass_status}
                    evidence={auditResult.checklist.schema_org.evidence}
                  />
                  <ChecklistItemView
                    label="robots.txt does not block LLM/AI agents"
                    pass={auditResult.checklist.robots_txt.pass_status}
                    evidence={auditResult.checklist.robots_txt.evidence}
                  />
                </div>
              </div>

              {/* Install instructions — the takeaway */}
              <div style={{ background: '#09090b', border: '1px solid #27272a', borderRadius: '8px', padding: '20px 24px' }}>
                <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#fafafa', marginTop: 0, marginBottom: '10px' }}>
                  Fix it in two steps
                </h3>
                <ol style={{ margin: 0, padding: '0 0 0 18px', fontSize: '12.5px', color: '#d4d4d8', lineHeight: 1.7 }}>
                  <li>
                    Host the full generated file at{' '}
                    <code style={{ background: '#27272a', padding: '1px 6px', borderRadius: '3px', fontSize: '11.5px' }}>
                      your-store.com/llms.txt
                    </code>
                    {' '}— delivered with the install package (preview at right)
                  </li>
                  <li>
                    Add the AGORA collector to see which agents read it:{' '}
                    <code style={{ background: '#27272a', padding: '1px 6px', borderRadius: '3px', fontSize: '11.5px', display: 'inline-block', marginTop: '4px' }}>
                      app = AGORACollector(app, api_url=…, api_key=…)
                    </code>
                  </li>
                </ol>
              </div>
            </div>

            {/* Right: generated llms.txt / markdown view */}
            <div style={{ background: '#fff', border: '1px solid #e4e4e7', borderRadius: '8px', overflow: 'hidden', height: '100%', display: 'flex', flexDirection: 'column' }}>
              <div style={{ padding: '10px 14px', borderBottom: '1px solid #e4e4e7', background: '#fafafa', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
                <div style={{ display: 'flex', gap: '4px' }}>
                  <button
                    className="vbtn"
                    onClick={() => setActiveView('llms')}
                    style={{
                      padding: '5px 12px', borderRadius: '5px', fontSize: '12px', fontWeight: 600, cursor: 'pointer',
                      border: '1px solid', borderColor: activeView === 'llms' ? '#09090b' : '#e4e4e7',
                      background: activeView === 'llms' ? '#09090b' : '#fff',
                      color: activeView === 'llms' ? '#fff' : '#71717a',
                    }}
                  >
                    Generated /llms.txt
                  </button>
                  <button
                    className="vbtn"
                    onClick={() => setActiveView('markdown')}
                    style={{
                      padding: '5px 12px', borderRadius: '5px', fontSize: '12px', fontWeight: 600, cursor: 'pointer',
                      border: '1px solid', borderColor: activeView === 'markdown' ? '#09090b' : '#e4e4e7',
                      background: activeView === 'markdown' ? '#09090b' : '#fff',
                      color: activeView === 'markdown' ? '#fff' : '#71717a',
                    }}
                  >
                    Agent's-eye view
                  </button>
                </div>
                {activeView === 'markdown' && (
                  <button
                    className="vbtn"
                    onClick={() => handleCopy(auditResult.markdown)}
                    style={{ padding: '5px 12px', borderRadius: '5px', fontSize: '12px', fontWeight: 600, border: '1px solid #e4e4e7', background: '#fff', color: '#3f3f46', cursor: 'pointer' }}
                  >
                    {copied ? '✓ Copied' : 'Copy'}
                  </button>
                )}
                {activeView === 'llms' && auditResult.llms_txt_truncated && (
                  <span style={{ fontSize: '11px', fontWeight: 600, color: '#b45309', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: '4px', padding: '3px 8px' }}>
                    Preview
                  </span>
                )}
              </div>
              <pre style={{
                margin: 0, padding: '20px', overflow: 'auto', background: '#fafafa', flex: 1, maxHeight: '560px',
                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace', fontSize: '12px',
                lineHeight: 1.5, color: '#27272a', whiteSpace: 'pre-wrap', wordBreak: 'break-word',
              }}>
                {activeView === 'llms'
                  ? (auditResult.generated_llms_txt || '(Empty llms.txt generated)')
                  : (auditResult.markdown || '(Empty markdown generated)')}
              </pre>
              {activeView === 'llms' && auditResult.llms_txt_truncated && (
                <div style={{ borderTop: '1px solid #fde68a', background: '#fffbeb', padding: '14px 18px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                  <p style={{ margin: 0, fontSize: '12.5px', color: '#92400e', lineHeight: 1.5, flex: 1, minWidth: '220px' }}>
                    Bu bir önizleme
                    {auditResult.catalog && auditResult.catalog.total_count > 10
                      ? ` — tam dosyada ${auditResult.catalog.total_count - 10} ürün daha var.`
                      : ' — dosyanın tamamı gizlendi.'}{' '}
                    Tam dosya, kurulum paketiyle birlikte teslim edilir.
                  </p>
                  <button
                    className="vbtn"
                    onClick={() => document.getElementById('lead-capture')?.scrollIntoView({ behavior: 'smooth', block: 'center' })}
                    style={{ padding: '8px 16px', borderRadius: '6px', fontSize: '12.5px', fontWeight: 600, border: 'none', background: '#09090b', color: '#fff', cursor: 'pointer' }}
                  >
                    Tam dosyayı isteyin
                  </button>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
