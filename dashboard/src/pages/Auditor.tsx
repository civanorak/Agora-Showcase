import { useState } from 'react'
import type { AuditResult, CatalogInfo } from '../types'
import { ChecklistItemView } from '../components/shared'
import { API } from '../api'
import { useI18n } from '../i18n'

const SOURCE_LABEL: Record<string, string> = {
  products_json: 'Shopify /products.json',
  sitemap: 'sitemap.xml',
}

function CatalogRealityCard({ catalog }: { catalog: CatalogInfo }) {
  const { t } = useI18n()
  const hasNames = catalog.sample.length > 0
  const coverageColor = catalog.coverage_pct >= 70 ? '#166534' : catalog.coverage_pct >= 30 ? '#b45309' : '#b91c1c'
  return (
    <div style={{ background: '#fff', border: '1px solid #e4e4e7', borderRadius: '8px', padding: '20px 24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: '8px' }}>
        <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#09090b', margin: 0 }}>
          {t('Catalog Reality vs Agent View', 'Katalog Gerçeği vs Ajan Görünümü')}
        </h3>
        <span style={{ fontSize: '11px', color: '#a1a1aa', fontFamily: 'ui-monospace, monospace' }}>
          {t('source:', 'kaynak:')} {SOURCE_LABEL[catalog.source] ?? catalog.source}
        </span>
      </div>

      <div style={{ display: 'flex', gap: '32px', marginTop: '16px', flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: '11px', fontWeight: 600, color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
            {t('Products in catalog', 'Kataloğdaki ürünler')}
          </div>
          <div style={{ fontSize: '26px', fontWeight: 700, color: '#09090b', marginTop: '4px' }}>
            {catalog.total_count}
          </div>
        </div>
        {hasNames && (
          <>
            <div>
              <div style={{ fontSize: '11px', fontWeight: 600, color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
                {t('Visible to agents', 'Ajanlara görünür')}
              </div>
              <div style={{ fontSize: '26px', fontWeight: 700, color: coverageColor, marginTop: '4px' }}>
                {catalog.visible_to_agent}
              </div>
            </div>
            <div style={{ flex: 1, minWidth: '220px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ fontSize: '11px', fontWeight: 600, color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
                  {t('Agent coverage', 'Ajan kapsamı')}
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
                  ? t(
                      `An agent reading this page can quote only ${catalog.visible_to_agent} of your ${catalog.total_count} products. The generated /llms.txt below closes that gap with your full catalog.`,
                      `Bu sayfayı okuyan bir ajan, ${catalog.total_count} ürününüzden yalnızca ${catalog.visible_to_agent} tanesini alıntılayabilir. Aşağıda üretilen /llms.txt bu açığı tam kataloğunuzla kapatır.`,
                    )
                  : t('Agents can find every catalog product on this page.', 'Ajanlar bu sayfadaki her katalog ürününü bulabilir.')}
              </div>
            </div>
          </>
        )}
        {!hasNames && (
          <div style={{ flex: 1, minWidth: '220px', fontSize: '11.5px', color: '#71717a', alignSelf: 'center', lineHeight: 1.5 }}>
            {t(
              `Catalog size proven via ${SOURCE_LABEL[catalog.source] ?? catalog.source}. Product names and prices were not exposed in a structured endpoint, so agent coverage cannot be measured.`,
              `Katalog boyutu ${SOURCE_LABEL[catalog.source] ?? catalog.source} üzerinden kanıtlandı. Ürün adları ve fiyatları yapılandırılmış bir uç noktada sunulmadığından ajan kapsamı ölçülemez.`,
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function RoadmapTag() {
  const { t } = useI18n()
  return (
    <span
      title={t('Planned capability — not running on this audit yet.', 'Planlanan yetenek — bu denetimde henüz çalışmıyor.')}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: '5px',
        fontSize: '10.5px', fontWeight: 700, letterSpacing: '0.04em',
        textTransform: 'uppercase', whiteSpace: 'nowrap',
        color: '#3730a3', background: '#eef2ff', border: '1px solid #c7d2fe',
        borderRadius: '5px', padding: '2px 8px', cursor: 'default',
      }}
    >
      <span aria-hidden style={{ fontSize: '9px' }}>◆</span>
      {t('Roadmap', 'Yol haritası')}
    </span>
  )
}

/**
 * Freshness value proposition. A copied static /llms.txt drifts out of sync the
 * moment a price or product changes on the store. This card frames AGORA's
 * continuous re-scan as the reason the relationship is ongoing — using the real
 * audited catalog numbers, and honestly tagged Roadmap since scheduled re-scan
 * is not yet shipped.
 */
function FreshnessCard({ catalog }: { catalog: CatalogInfo | null }) {
  const { t } = useI18n()
  const count = catalog?.total_count ?? null
  const sourceLabel = catalog ? (SOURCE_LABEL[catalog.source] ?? catalog.source) : null

  const problem = count !== null && sourceLabel
    ? t(
        `Your ${count} products live in ${sourceLabel}. Prices and stock change there constantly — a file you copied once keeps quoting yesterday's numbers to agents.`,
        `${count} ürününüz ${sourceLabel} içinde yaşıyor. Fiyatlar ve stok orada sürekli değişir — bir kez kopyaladığınız dosya ajanlara dünün rakamlarını söylemeye devam eder.`,
      )
    : t(
        'A file you copy once drifts out of date the moment a price or product changes on your store — and agents keep quoting the stale version.',
        'Bir kez kopyaladığınız dosya, mağazanızda bir fiyat veya ürün değiştiği an eskir — ve ajanlar bayat sürümü söylemeye devam eder.',
      )

  return (
    <div style={{ background: '#fff', border: '1px solid #e4e4e7', borderRadius: '8px', padding: '20px 24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
        <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#09090b', margin: 0 }}>
          {t('Stays fresh — you never redo it', 'Güncel kalır — bir daha uğraşmazsınız')}
        </h3>
        <RoadmapTag />
      </div>
      <p style={{ fontSize: '12.5px', color: '#71717a', margin: '0 0 14px', lineHeight: 1.55 }}>
        {problem}
      </p>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', fontSize: '12px', color: '#3f3f46' }}>
        <span style={{ background: '#f4f4f5', borderRadius: '5px', padding: '4px 9px', fontWeight: 600 }}>
          {t('Re-scan catalog', 'Kataloğu tekrar tara')}
        </span>
        <span aria-hidden style={{ color: '#a1a1aa' }}>→</span>
        <span style={{ background: '#f4f4f5', borderRadius: '5px', padding: '4px 9px', fontWeight: 600 }}>
          {t('Detect price / product changes', 'Fiyat / ürün değişimini yakala')}
        </span>
        <span aria-hidden style={{ color: '#a1a1aa' }}>→</span>
        <span style={{ background: '#ecfdf5', color: '#166534', border: '1px solid #bbf7d0', borderRadius: '5px', padding: '4px 9px', fontWeight: 600 }}>
          {t('Regenerate /llms.txt', '/llms.txt yeniden üret')}
        </span>
      </div>
      <p style={{ fontSize: '11.5px', color: '#a1a1aa', margin: '12px 0 0', lineHeight: 1.5 }}>
        {t(
          'AGORA re-checks your store on a schedule and refreshes the file automatically, so the agent view always matches reality — no manual re-export.',
          'AGORA mağazanızı düzenli aralıklarla yeniden denetler ve dosyayı otomatik tazeler; böylece ajan görünümü her zaman gerçekle örtüşür — elle yeniden dışa aktarma yok.',
        )}
      </p>
    </div>
  )
}

function EmailCaptureCard({ url, coveragePct }: { url: string; coveragePct: number | null }) {
  const { t } = useI18n()
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
        {t('Saved — we’ll review this report and get back to you.', 'Kaydedildi — bu raporu inceleyip size dönüş yapacağız.')}
      </div>
    )
  }

  return (
    <div style={{ background: '#fff', border: '1px solid #e4e4e7', borderRadius: '8px', padding: '20px 24px' }}>
      <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#09090b', margin: '0 0 4px' }}>
        {t('Save this report', 'Bu raporu kaydedelim')}
      </h3>
      <p style={{ fontSize: '12.5px', color: '#71717a', margin: '0 0 14px', lineHeight: 1.5 }}>
        {t(
          'Leave your email and we’ll send you this audit result plus the steps to open your store to AI agents.',
          'E-postanızı bırakın; bu denetim sonucunu ve mağazanızı AI ajanlarına açmak için gereken adımları gönderelim.',
        )}
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
          {status === 'submitting' ? t('Sending…', 'Gönderiliyor…') : t('Save', 'Kaydet')}
        </button>
      </div>
      {status === 'error' && (
        <p style={{ fontSize: '12px', color: '#b91c1c', margin: '8px 0 0' }}>{t('Something went wrong, please try again.', 'Bir şeyler ters gitti, tekrar deneyin.')}</p>
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
  const { t } = useI18n()
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
          {t('AI Storefront Auditor', 'AI Mağaza Denetleyici')}
        </h1>
        <p style={{ fontSize: '13px', color: '#71717a', margin: '5px 0 0', lineHeight: 1.5 }}>
          {t(
            'Crawl any URL to audit machine-readability, token efficiency, and AI bot agent friendliness.',
            'Makinece okunabilirliği, token verimliliğini ve AI ajan dostluğunu denetlemek için herhangi bir URL’yi tarayın.',
          )}
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
            {isAuditLoading ? t('Auditing…', 'Denetleniyor…') : t('Analyze URL', 'URL’yi Analiz Et')}
          </button>
        </div>

        <div style={{ display: 'flex', gap: '8px', marginTop: '12px', alignItems: 'center' }}>
          <span style={{ fontSize: '11px', color: '#a1a1aa' }}>{t('Quick targets:', 'Hızlı hedefler:')}</span>
          <button className="qbtn" onClick={() => { onAuditUrlChange('https://books.toscrape.com'); onAudit('https://books.toscrape.com') }}>
            {t('Books to Scrape (Demo Store)', 'Books to Scrape (Demo Mağaza)')}
          </button>
          <button className="qbtn" onClick={() => { onAuditUrlChange('https://example.com'); onAudit('https://example.com') }}>
            {t('Example Domain', 'Örnek Alan Adı')}
          </button>
        </div>
      </div>

      {auditError && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c', padding: '14px 18px', borderRadius: '8px', fontSize: '13px' }}>
          <strong>{t('Error:', 'Hata:')}</strong> {auditError}
        </div>
      )}

      {!auditResult && !isAuditLoading && !auditError && (
        <div style={{
          background: '#fff', border: '1px solid #e4e4e7', borderRadius: '12px',
          padding: '40px 32px', textAlign: 'center', maxWidth: '720px', margin: '16px auto 0',
        }}>
          <div style={{ fontSize: '32px', marginBottom: '12px' }}>🔍</div>
          <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#09090b', margin: '0 0 8px' }}>
            {t('Ready to audit your storefront', 'Mağazanızı denetlemeye hazır')}
          </h3>
          <p style={{ fontSize: '13.5px', color: '#71717a', lineHeight: 1.6, margin: '0 0 24px', maxWidth: '540px', marginLeft: 'auto', marginRight: 'auto' }}>
            {t('Enter your storefront URL above or select a quick demo target. AGORA will crawl the site, measure token efficiency, test schema.org markup, check robots.txt bot rules, and generate a machine-readable', 'Yukarıya mağaza URL’nizi girin veya hızlı bir demo hedefi seçin. AGORA siteyi tarar, token verimliliğini ölçer, schema.org işaretlemesini test eder, robots.txt bot kurallarını denetler ve makinece okunabilir bir')} <code>/llms.txt</code> {t('file.', 'dosyası üretir.')}
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <button
              className="vbtn"
              onClick={() => { onAuditUrlChange('https://books.toscrape.com'); onAudit('https://books.toscrape.com') }}
              style={{
                padding: '10px 20px', borderRadius: '6px', fontSize: '13px', fontWeight: 600,
                background: '#09090b', color: '#fff', border: 'none', cursor: 'pointer',
              }}
            >
              🚀 {t('Run Demo Audit (Books to Scrape)', 'Demo Denetimi Çalıştır (Books to Scrape)')}
            </button>
            <button
              className="vbtn"
              onClick={() => { onAuditUrlChange('https://example.com'); onAudit('https://example.com') }}
              style={{
                padding: '10px 20px', borderRadius: '6px', fontSize: '13px', fontWeight: 600,
                background: '#f4f4f5', color: '#09090b', border: '1px solid #e4e4e7', cursor: 'pointer',
              }}
            >
              📄 {t('Try Example Domain', 'Örnek Alan Adını Dene')}
            </button>
          </div>
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
                  {t('Computed Crawl Metrics', 'Hesaplanan Tarama Metrikleri')}
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', borderBottom: '1px dashed #f4f4f5', paddingBottom: '8px' }}>
                    <span style={{ color: '#71717a' }}>{t('Total Download Size', 'Toplam İndirme Boyutu')}</span>
                    <strong style={{ color: '#09090b' }}>{(auditResult.total_bytes / 1024).toFixed(1)} KB ({auditResult.total_bytes} {t('bytes', 'bayt')})</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', borderBottom: '1px dashed #f4f4f5', paddingBottom: '8px' }}>
                    <span style={{ color: '#71717a' }}>{t('Script-to-Content Ratio', 'Script-İçerik Oranı')}</span>
                    <strong style={{ color: '#09090b' }}>{auditResult.script_ratio}%</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                    <span style={{ color: '#71717a' }}>{t('Extractable-Text %', 'Çıkarılabilir Metin %')}</span>
                    <strong style={{ color: '#09090b' }}>{auditResult.extractable_text_pct}%</strong>
                  </div>
                </div>
              </div>

              <div style={{ background: '#fff', border: '1px solid #e4e4e7', borderRadius: '8px', padding: '20px 24px' }}>
                <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#09090b', marginTop: 0, marginBottom: '16px' }}>
                  {t('AI Readiness Checklist', 'AI Hazırlık Kontrol Listesi')}
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <ChecklistItemView
                    label={t('/llms.txt exists and serves your catalog', '/llms.txt mevcut ve kataloğunuzu sunuyor')}
                    pass={auditResult.checklist.llms_txt.pass_status}
                    evidence={auditResult.checklist.llms_txt.evidence}
                  />
                  <ChecklistItemView
                    label={t('Product pricing & metadata parsed', 'Ürün fiyatı ve meta verisi ayrıştırıldı')}
                    pass={auditResult.checklist.product_content.pass_status}
                    evidence={auditResult.checklist.product_content.evidence}
                  />
                  <ChecklistItemView
                    label={t('schema.org Product metadata tags found', 'schema.org Ürün meta veri etiketleri bulundu')}
                    pass={auditResult.checklist.schema_org.pass_status}
                    evidence={auditResult.checklist.schema_org.evidence}
                  />
                  <ChecklistItemView
                    label={t('robots.txt does not block LLM/AI agents', 'robots.txt LLM/AI ajanlarını engellemiyor')}
                    pass={auditResult.checklist.robots_txt.pass_status}
                    evidence={auditResult.checklist.robots_txt.evidence}
                  />
                </div>
              </div>

              {/* Install instructions — the takeaway */}
              <div style={{ background: '#09090b', border: '1px solid #27272a', borderRadius: '8px', padding: '20px 24px' }}>
                <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#fafafa', marginTop: 0, marginBottom: '10px' }}>
                  {t('Fix it in two steps', 'İki adımda çözün')}
                </h3>
                <ol style={{ margin: 0, padding: '0 0 0 18px', fontSize: '12.5px', color: '#d4d4d8', lineHeight: 1.7 }}>
                  <li>
                    {t('Host the full generated file at', 'Üretilen tam dosyayı şurada barındırın:')}{' '}
                    <code style={{ background: '#27272a', padding: '1px 6px', borderRadius: '3px', fontSize: '11.5px' }}>
                      your-store.com/llms.txt
                    </code>
                    {' '}— {t('delivered with the install package (preview at right)', 'kurulum paketiyle teslim edilir (önizleme sağda)')}
                  </li>
                  <li>
                    {t('Add the AGORA collector to see which agents read it:', 'Hangi ajanların okuduğunu görmek için AGORA toplayıcısını ekleyin:')}{' '}
                    <code style={{ background: '#27272a', padding: '1px 6px', borderRadius: '3px', fontSize: '11.5px', display: 'inline-block', marginTop: '4px' }}>
                      app = AGORACollector(app, api_url=…, api_key=…)
                    </code>
                  </li>
                </ol>
              </div>

              {/* Freshness / recurring-value story */}
              <FreshnessCard catalog={auditResult.catalog} />
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
                    {t('Generated /llms.txt', 'Üretilen /llms.txt')}
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
                    {t("Agent's-eye view", 'Ajanın gözünden')}
                  </button>
                </div>
                {activeView === 'markdown' && (
                  <button
                    className="vbtn"
                    onClick={() => handleCopy(auditResult.markdown)}
                    style={{ padding: '5px 12px', borderRadius: '5px', fontSize: '12px', fontWeight: 600, border: '1px solid #e4e4e7', background: '#fff', color: '#3f3f46', cursor: 'pointer' }}
                  >
                    {copied ? t('✓ Copied', '✓ Kopyalandı') : t('Copy', 'Kopyala')}
                  </button>
                )}
                {activeView === 'llms' && auditResult.llms_txt_truncated && (
                  <span style={{ fontSize: '11px', fontWeight: 600, color: '#b45309', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: '4px', padding: '3px 8px' }}>
                    {t('Preview', 'Önizleme')}
                  </span>
                )}
              </div>
              <pre style={{
                margin: 0, padding: '20px', overflow: 'auto', background: '#fafafa', flex: 1, maxHeight: '560px',
                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace', fontSize: '12px',
                lineHeight: 1.5, color: '#27272a', whiteSpace: 'pre-wrap', wordBreak: 'break-word',
              }}>
                {activeView === 'llms'
                  ? (auditResult.generated_llms_txt || t('(Empty llms.txt generated)', '(Boş llms.txt üretildi)'))
                  : (auditResult.markdown || t('(Empty markdown generated)', '(Boş markdown üretildi)'))}
              </pre>
              {activeView === 'llms' && auditResult.llms_txt_truncated && (
                <div style={{ borderTop: '1px solid #fde68a', background: '#fffbeb', padding: '14px 18px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                  <p style={{ margin: 0, fontSize: '12.5px', color: '#92400e', lineHeight: 1.5, flex: 1, minWidth: '220px' }}>
                    {t('This is a preview', 'Bu bir önizleme')}
                    {auditResult.catalog && auditResult.catalog.total_count > 10
                      ? t(` — the full file has ${auditResult.catalog.total_count - 10} more products.`, ` — tam dosyada ${auditResult.catalog.total_count - 10} ürün daha var.`)
                      : t(' — the rest of the file is hidden.', ' — dosyanın tamamı gizlendi.')}{' '}
                    {t('The full file is delivered with the install package.', 'Tam dosya, kurulum paketiyle birlikte teslim edilir.')}
                  </p>
                  <button
                    className="vbtn"
                    onClick={() => document.getElementById('lead-capture')?.scrollIntoView({ behavior: 'smooth', block: 'center' })}
                    style={{ padding: '8px 16px', borderRadius: '6px', fontSize: '12.5px', fontWeight: 600, border: 'none', background: '#09090b', color: '#fff', cursor: 'pointer' }}
                  >
                    {t('Request the full file', 'Tam dosyayı isteyin')}
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
