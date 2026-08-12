import { useState } from 'react'
import type { AuditResult, CatalogInfo } from '../types'
import { computeReadiness } from '../score'

// ── Plain-language, no-jargon copy ────────────────────────────────────────────
// Her checklist maddesi için müşterinin anlayacağı başlık + sonuç cümlesi.
// Ham "evidence" metni yalnızca en alttaki "Teknik detaylar" bölümünde durur.
type CheckKey = 'llms_txt' | 'product_content' | 'schema_org' | 'robots_txt'

const CHECK_COPY: Record<CheckKey, { title: string; pass: string; fail: string }> = {
  llms_txt: {
    title: 'Yapay zekâ için hazır ürün listesi',
    pass: 'Var — asistanlar mağazanızı tek seferde okuyabiliyor.',
    fail: 'Yok — asistanlar ürünlerinizi bulmak için tüm siteyi taramak zorunda.',
  },
  product_content: {
    title: 'Ürün fiyatları ve bilgileri okunabilir',
    pass: 'Fiyat ve ürün bilgileri sayfada net görünüyor.',
    fail: 'Fiyat ve ürün bilgileri sayfada yapay zekânın okuyabileceği biçimde değil.',
  },
  schema_org: {
    title: 'Ürünler yapay zekânın anlayacağı şekilde etiketli',
    pass: 'Ürün etiketleri mevcut — asistanlar fiyatı doğru okuyor.',
    fail: 'Ürün etiketleri eksik — asistanlar fiyatı tahmin etmek zorunda.',
  },
  robots_txt: {
    title: 'Yapay zekâ botları engellenmemiş',
    pass: 'Asistanların erişimi açık.',
    fail: 'Bazı yapay zekâ botları engelli — müşteri getirenleri kaçırıyor olabilirsiniz.',
  },
}

const CHECK_ORDER: CheckKey[] = ['llms_txt', 'product_content', 'schema_org', 'robots_txt']

const CARD: React.CSSProperties = {
  background: '#fff', border: '1px solid #e4e4e7', borderRadius: '10px', padding: '22px 26px',
}

// ── Section 1 · Tek sonuç: hazırlık skoru ─────────────────────────────────────
function ScoreHero({ result }: { result: AuditResult }) {
  const { value, label, color } = computeReadiness(result)
  const catalog = result.catalog
  const headline =
    catalog && catalog.sample.length > 0
      ? `Yapay zekâ asistanları ${catalog.total_count} ürününüzden ${catalog.visible_to_agent} tanesini görebiliyor.`
      : 'Mağazanızın yapay zekâ asistanlarına ne kadar hazır olduğunu ölçtük.'

  return (
    <div style={{ ...CARD, padding: '32px 34px' }}>
      <div style={{ fontSize: '12px', fontWeight: 600, color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
        Yapay Zekâ Hazırlığı
      </div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '14px', marginTop: '10px' }}>
        <span style={{ fontSize: '64px', fontWeight: 800, lineHeight: 0.9, color, letterSpacing: '-0.03em' }}>{value}</span>
        <span style={{ fontSize: '20px', fontWeight: 600, color: '#a1a1aa', paddingBottom: '8px' }}>/ 100</span>
        <span style={{
          marginLeft: 'auto', fontSize: '13px', fontWeight: 700, color,
          background: `${color}14`, border: `1px solid ${color}33`, borderRadius: '999px', padding: '6px 14px',
        }}>{label}</span>
      </div>
      <div style={{ height: '10px', borderRadius: '5px', background: '#f4f4f5', overflow: 'hidden', marginTop: '18px' }}>
        <div style={{ width: `${Math.min(value, 100)}%`, height: '100%', background: color, transition: 'width 400ms ease-out' }} />
      </div>
      <p style={{ fontSize: '14px', color: '#3f3f46', margin: '18px 0 0', lineHeight: 1.55 }}>{headline}</p>
    </div>
  )
}

// ── Section 2 · Ürün görünürlüğü ──────────────────────────────────────────────
function ProductVisibility({ catalog }: { catalog: CatalogInfo }) {
  const measurable = catalog.sample.length > 0
  const color = catalog.coverage_pct >= 70 ? '#166534' : catalog.coverage_pct >= 30 ? '#b45309' : '#b91c1c'

  return (
    <div style={CARD}>
      <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#09090b', margin: 0 }}>
        Ürünlerinizin kaçını görebiliyorlar?
      </h3>

      <div style={{ display: 'flex', gap: '36px', marginTop: '18px', flexWrap: 'wrap' }}>
        <Stat label="Mağazanızdaki ürün" value={String(catalog.total_count)} />
        {measurable && <Stat label="Yapay zekânın görebildiği" value={String(catalog.visible_to_agent)} color={color} />}
        {measurable && (
          <div style={{ flex: 1, minWidth: '240px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <span style={{ fontSize: '11px', fontWeight: 600, color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '0.07em' }}>Görünürlük</span>
              <span style={{ fontSize: '13px', fontWeight: 700, color }}>{catalog.coverage_pct}%</span>
            </div>
            <div style={{ height: '8px', borderRadius: '4px', background: '#f4f4f5', overflow: 'hidden' }}>
              <div style={{ width: `${Math.min(catalog.coverage_pct, 100)}%`, height: '100%', background: color, opacity: 0.9 }} />
            </div>
            <p style={{ fontSize: '12.5px', color: '#71717a', marginTop: '10px', lineHeight: 1.5 }}>
              {catalog.coverage_pct < 100
                ? `Bir yapay zekâ bu sayfayı okuduğunda ${catalog.total_count} ürününüzden yalnızca ${catalog.visible_to_agent} tanesini müşteriye önerebiliyor. Aşağıda hazırladığımız liste bu farkı kapatır.`
                : 'Yapay zekâ asistanları tüm ürünlerinizi bu sayfada bulabiliyor.'}
            </p>
          </div>
        )}
        {!measurable && (
          <p style={{ flex: 1, minWidth: '240px', fontSize: '12.5px', color: '#71717a', alignSelf: 'center', lineHeight: 1.5 }}>
            Ürün sayınızı doğruladık, ancak ürün adları/fiyatları yapılandırılmış bir listeden gelmediği için
            görünürlük yüzdesi ölçülemedi.
          </p>
        )}
      </div>
    </div>
  )
}

function Stat({ label, value, color = '#09090b' }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <div style={{ fontSize: '11px', fontWeight: 600, color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '0.07em' }}>{label}</div>
      <div style={{ fontSize: '30px', fontWeight: 700, color, marginTop: '4px', lineHeight: 1 }}>{value}</div>
    </div>
  )
}

// ── Section 3 · Sade kontrol listesi ──────────────────────────────────────────
function PlainChecklist({ result }: { result: AuditResult }) {
  return (
    <div style={CARD}>
      <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#09090b', margin: '0 0 18px' }}>Neler yolunda, neler değil?</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {CHECK_ORDER.map(key => {
          const pass = result.checklist[key].pass_status
          const copy = CHECK_COPY[key]
          return (
            <div key={key} style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
              <span style={{
                flexShrink: 0, width: '22px', height: '22px', borderRadius: '50%', marginTop: '1px',
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '13px', fontWeight: 700, color: '#fff',
                background: pass ? '#22c55e' : '#ef4444',
              }}>{pass ? '✓' : '✕'}</span>
              <div>
                <div style={{ fontSize: '13.5px', fontWeight: 600, color: '#09090b' }}>{copy.title}</div>
                <div style={{ fontSize: '12.5px', color: '#71717a', marginTop: '2px', lineHeight: 1.45 }}>
                  {pass ? copy.pass : copy.fail}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Section 4 · Düzeltme adımları ─────────────────────────────────────────────
function FixSteps() {
  return (
    <div style={{ ...CARD, background: '#09090b', border: '1px solid #27272a' }}>
      <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#fafafa', margin: '0 0 12px' }}>İki adımda düzeltin</h3>
      <ol style={{ margin: 0, padding: '0 0 0 20px', fontSize: '13px', color: '#d4d4d8', lineHeight: 1.7 }}>
        <li>Aşağıda hazırladığımız ürün listesini mağazanıza ekleyin — tüm ürünlerinizi asistanlara tek seferde açar.</li>
        <li>Kısa bir kurulumla, hangi asistanların mağazanızı ziyaret ettiğini canlı görmeye başlarsınız.</li>
      </ol>
    </div>
  )
}

// ── Section 5 · Hazırlanan ürün listesi (deliverable) ─────────────────────────
function GeneratedList({ result, onRequestFull }: { result: AuditResult; onRequestFull: () => void }) {
  const [view, setView] = useState<'list' | 'agent'>('list')
  const [copied, setCopied] = useState(false)

  const copy = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    }).catch(() => {})
  }

  const tabBtn = (active: boolean): React.CSSProperties => ({
    padding: '6px 13px', borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer',
    border: `1px solid ${active ? '#09090b' : '#e4e4e7'}`,
    background: active ? '#09090b' : '#fff', color: active ? '#fff' : '#71717a',
  })

  return (
    <div style={{ ...CARD, padding: 0, overflow: 'hidden' }}>
      <div style={{ padding: '14px 18px', borderBottom: '1px solid #e4e4e7', background: '#fafafa', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: '13.5px', fontWeight: 700, color: '#09090b' }}>Yapay zekâ için hazırlanmış ürün listesi</div>
          <div style={{ fontSize: '11.5px', color: '#a1a1aa', marginTop: '2px' }}>
            {view === 'list' ? 'Mağazanıza eklenecek dosyanın önizlemesi' : 'Bir asistanın şu an sayfanızda gördüğü içerik'}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '5px', alignItems: 'center' }}>
          <button className="vbtn" onClick={() => setView('list')} style={tabBtn(view === 'list')}>Hazır liste</button>
          <button className="vbtn" onClick={() => setView('agent')} style={tabBtn(view === 'agent')}>Asistanın gördüğü</button>
          {view === 'agent' && (
            <button className="vbtn" onClick={() => copy(result.markdown)} style={{ padding: '6px 13px', borderRadius: '6px', fontSize: '12px', fontWeight: 600, border: '1px solid #e4e4e7', background: '#fff', color: '#3f3f46', cursor: 'pointer' }}>
              {copied ? '✓ Kopyalandı' : 'Kopyala'}
            </button>
          )}
        </div>
      </div>

      <pre style={{
        margin: 0, padding: '20px', overflow: 'auto', background: '#fafafa', maxHeight: '460px',
        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace', fontSize: '12px',
        lineHeight: 1.5, color: '#27272a', whiteSpace: 'pre-wrap', wordBreak: 'break-word',
      }}>
        {view === 'list'
          ? (result.generated_llms_txt || '(Liste oluşturulamadı)')
          : (result.markdown || '(İçerik okunamadı)')}
      </pre>

      {view === 'list' && result.llms_txt_truncated && (
        <div style={{ borderTop: '1px solid #fde68a', background: '#fffbeb', padding: '14px 18px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <p style={{ margin: 0, fontSize: '12.5px', color: '#92400e', lineHeight: 1.5, flex: 1, minWidth: '220px' }}>
            Bu bir önizleme
            {result.catalog && result.catalog.total_count > 10
              ? ` — tam listede ${result.catalog.total_count - 10} ürün daha var.`
              : ' — listenin tamamı gizlendi.'}{' '}
            Tam liste, kurulum paketiyle birlikte teslim edilir.
          </p>
          <button className="vbtn" onClick={onRequestFull} style={{ padding: '8px 16px', borderRadius: '6px', fontSize: '12.5px', fontWeight: 600, border: 'none', background: '#09090b', color: '#fff', cursor: 'pointer' }}>
            Tam listeyi isteyin
          </button>
        </div>
      )}
    </div>
  )
}

// ── Section 6 · E-posta yakalama ──────────────────────────────────────────────
function EmailCapture({ url, coveragePct }: { url: string; coveragePct: number | null }) {
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle')

  const submit = () => {
    if (!email.trim()) return
    setStatus('submitting')
    fetch('/leads', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, url, coverage_pct: coveragePct }),
    })
      .then(r => { if (!r.ok) throw new Error(); setStatus('success') })
      .catch(() => setStatus('error'))
  }

  if (status === 'success') {
    return (
      <div style={{ ...CARD, background: '#f0fdf4', border: '1px solid #bbf7d0', color: '#166534', fontSize: '13px' }}>
        Kaydedildi — bu raporu inceleyip size dönüş yapacağız.
      </div>
    )
  }

  return (
    <div id="lead-capture" style={CARD}>
      <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#09090b', margin: '0 0 4px' }}>Tam listeyi ve kurulum adımlarını gönderelim</h3>
      <p style={{ fontSize: '12.5px', color: '#71717a', margin: '0 0 14px', lineHeight: 1.5 }}>
        E-postanızı bırakın; bu raporu, tam ürün listesini ve mağazanızı asistanlara açmak için gereken adımları iletelim.
      </p>
      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
        <input
          type="email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          placeholder="siz@sirketiniz.com"
          style={{ flex: 1, minWidth: '220px', padding: '10px 13px', borderRadius: '7px', border: '1px solid #e4e4e7', fontSize: '13px' }}
        />
        <button className="vbtn" onClick={submit} disabled={status === 'submitting'}
          style={{ padding: '10px 20px', borderRadius: '7px', fontSize: '13px', fontWeight: 600, background: '#09090b', color: '#fff', border: 'none', cursor: 'pointer' }}>
          {status === 'submitting' ? 'Gönderiliyor…' : 'Gönder'}
        </button>
      </div>
      {status === 'error' && <p style={{ fontSize: '12px', color: '#b91c1c', margin: '8px 0 0' }}>Bir şeyler ters gitti, tekrar deneyin.</p>}
    </div>
  )
}

// ── Section 7 · Canlı ziyaretçiler (kurulumdan sonra dolar → kilitli) ─────────
function LiveVisitorsLocked({ onInstall }: { onInstall: () => void }) {
  return (
    <div style={{ ...CARD, position: 'relative', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ fontSize: '15px' }}>🔒</span>
        <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#09090b', margin: 0 }}>Canlı ziyaretçiler</h3>
      </div>
      <p style={{ fontSize: '13px', color: '#71717a', margin: '10px 0 0', lineHeight: 1.55, maxWidth: '560px' }}>
        Kısa kurulumdan sonra <strong style={{ color: '#3f3f46' }}>ChatGPT, Claude, Perplexity</strong> gibi asistanların
        mağazanıza yaptığı ziyaretler tam burada, gerçek zamanlı akmaya başlar — hangi sayfaya baktıklarını ve ne aradıklarını görürsünüz.
      </p>

      {/* Bulanık örnek satırlar — sadece nasıl görüneceğini gösterir */}
      <div style={{ marginTop: '18px', filter: 'blur(3px)', opacity: 0.5, pointerEvents: 'none', userSelect: 'none' }}>
        {[['ChatGPT', '/urunler/kablosuz-kulaklik'], ['Claude', '/llms.txt'], ['Perplexity', '/urunler/mouse-pad']].map(([who, path], i) => (
          <div key={i} style={{ display: 'flex', gap: '12px', alignItems: 'center', padding: '9px 0', borderBottom: '1px solid #f4f4f5', fontSize: '12.5px' }}>
            <span style={{ fontWeight: 700, color: '#166534', width: '90px' }}>{who}</span>
            <span style={{ fontFamily: 'ui-monospace, monospace', color: '#52525b' }}>{path}</span>
          </div>
        ))}
      </div>

      <button className="vbtn" onClick={onInstall}
        style={{ marginTop: '18px', padding: '10px 20px', borderRadius: '7px', fontSize: '13px', fontWeight: 600, background: '#09090b', color: '#fff', border: 'none', cursor: 'pointer' }}>
        Kurulumu başlat
      </button>
    </div>
  )
}

// ── Section 8 · Teknik detaylar (isteğe bağlı, katlanabilir) ───────────────────
function TechnicalDetails({ result }: { result: AuditResult }) {
  return (
    <details style={{ ...CARD, padding: '16px 22px' }}>
      <summary style={{ fontSize: '13px', fontWeight: 600, color: '#71717a', cursor: 'pointer' }}>
        Teknik detaylar (isteğe bağlı)
      </summary>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '14px', fontSize: '12.5px' }}>
        <Row label="Sayfa boyutu" value={`${(result.total_bytes / 1024).toFixed(1)} KB`} />
        <Row label="Yapay zekânın okuyabildiği içerik oranı" value={`${result.extractable_text_pct}%`} />
        <Row label="Sayfadaki kod ağırlığı" value={`${result.script_ratio}%`} />
        <div style={{ borderTop: '1px dashed #e4e4e7', marginTop: '4px', paddingTop: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {CHECK_ORDER.map(key => (
            <div key={key} style={{ fontSize: '11.5px', color: '#71717a' }}>
              <span style={{ color: result.checklist[key].pass_status ? '#166534' : '#b91c1c', fontWeight: 700 }}>
                {result.checklist[key].pass_status ? '✓' : '✕'}
              </span>{' '}
              <span style={{ fontFamily: 'ui-monospace, monospace' }}>{key}</span> — {result.checklist[key].evidence}
            </div>
          ))}
        </div>
      </div>
    </details>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px' }}>
      <span style={{ color: '#71717a' }}>{label}</span>
      <strong style={{ color: '#09090b', fontVariantNumeric: 'tabular-nums' }}>{value}</strong>
    </div>
  )
}

// ── Consolidated report ───────────────────────────────────────────────────────
export function Report({ result }: { result: AuditResult }) {
  const scrollToLead = () => document.getElementById('lead-capture')?.scrollIntoView({ behavior: 'smooth', block: 'center' })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <ScoreHero result={result} />
      {result.catalog && <ProductVisibility catalog={result.catalog} />}
      <PlainChecklist result={result} />
      <FixSteps />
      <GeneratedList result={result} onRequestFull={scrollToLead} />
      <EmailCapture url={result.url} coveragePct={result.catalog?.coverage_pct ?? null} />
      <LiveVisitorsLocked onInstall={scrollToLead} />
      <TechnicalDetails result={result} />
    </div>
  )
}
