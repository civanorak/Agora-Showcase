import { AgoraMark } from '../components/AgoraMark'
import { useI18n } from '../i18n'

interface LandingProps {
  auditUrl: string
  onAuditUrlChange: (url: string) => void
  onAudit: (url: string) => void
  isAuditLoading: boolean
  auditError: string | null
  onOpenFeed: () => void
  onOpenAuditor: () => void
}

// Real signature coverage — every name here exists in server/signatures/*.yaml.
const DETECTED_AGENTS = [
  'ChatGPT-User', 'ClaudeBot', 'Claude-User', 'PerplexityBot', 'GPTBot',
  'OAI-SearchBot', 'Googlebot', 'Amazonbot', 'CCBot', 'Bytespider', 'DuckAssistBot',
]

export function Landing({
  auditUrl, onAuditUrlChange, onAudit, isAuditLoading, auditError, onOpenFeed, onOpenAuditor,
}: LandingProps) {
  const { t } = useI18n()

  const pipelineSteps = [
    {
      num: '01',
      title: t('Detect', 'Tespit Et'),
      body: t(
        'A 3-line server-side middleware classifies every request — assistant, crawler, shopping agent or human — with confidence and evidence. No JavaScript, no cookies, no PII.',
        'Sunucu tarafında 3 satırlık bir ara katman her isteği sınıflandırır — asistan, tarayıcı, alışveriş ajanı ya da insan — güven skoru ve kanıtla. JavaScript yok, çerez yok, kişisel veri yok.',
      ),
    },
    {
      num: '02',
      title: t('Audit', 'Denetle'),
      body: t(
        'AGORA crawls your storefront exactly the way an agent does: measures token cost, script-to-content ratio, schema.org coverage and robots.txt rules — and shows you what the agent actually read.',
        'AGORA mağazanızı tıpkı bir ajan gibi tarar: token maliyetini, script-içerik oranını, schema.org kapsamını ve robots.txt kurallarını ölçer — ve ajanın gerçekte ne okuduğunu gösterir.',
      ),
    },
    {
      num: '03',
      title: t('Serve', 'Sun'),
      body: t(
        'From the audit, AGORA generates a ready-to-host /llms.txt — a clean, machine-readable catalog agents load in a single request instead of parsing your JavaScript bundle.',
        'Denetimden yola çıkarak AGORA, yayına hazır bir /llms.txt üretir — ajanların JavaScript paketinizi ayrıştırmak yerine tek istekte yüklediği, temiz ve makinece okunabilir bir katalog.',
      ),
    },
  ]

  const checklistFeatures = [
    { title: t('/llms.txt discovery', '/llms.txt keşfi'), desc: t('Lets assistants find your store structure in one request instead of crawling dozens of pages.', 'Asistanların onlarca sayfayı taramak yerine mağaza yapınızı tek istekte bulmasını sağlar.') },
    { title: t('Schema.org metadata', 'Schema.org meta verisi'), desc: t('Structured product markup that agents parse without guessing prices from layout.', 'Ajanların fiyatları düzenden tahmin etmeden ayrıştırdığı yapılandırılmış ürün işaretlemesi.') },
    { title: t('Text-to-HTML density', 'Metin-HTML yoğunluğu'), desc: t("Script-heavy pages burn an agent's token budget before it reaches your products.", 'Script ağırlıklı sayfalar, ajanın token bütçesini ürünlerinize ulaşmadan tüketir.') },
    { title: t('robots.txt configuration', 'robots.txt yapılandırması'), desc: t('Verifies you are not accidentally blocking the exact agents that bring buyers.', 'Alıcı getiren ajanları yanlışlıkla engellemediğinizi doğrular.') },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '88px' }}>

      {/* ── Hero ── */}
      <section style={{
        display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: '48px',
        alignItems: 'center', minHeight: '440px', position: 'relative',
      }}>
        <div>
          <div style={{ marginBottom: '24px' }}>
            <AgoraMark size={44} tone="light" />
          </div>

          <h1 style={{ fontSize: '48px', fontWeight: 800, color: '#09090b', lineHeight: 1.05, margin: '0 0 20px', letterSpacing: '-0.03em' }}>
            {t('Your next customer', 'Bir sonraki müşteriniz')}<br />{t("isn't human.", 'insan değil.')}
          </h1>

          <p style={{ fontSize: '16px', color: '#52525b', lineHeight: 1.65, margin: '0 0 32px', maxWidth: '480px' }}>
            {t(
              "AI assistants are already browsing your store — and your analytics can't see them. AGORA detects every agent visit at the request level and turns your catalog into something agents can actually read.",
              'AI asistanları mağazanızı çoktan geziyor — ve analitiğiniz onları göremiyor. AGORA her ajan ziyaretini istek düzeyinde tespit eder ve kataloğunuzu ajanların gerçekten okuyabileceği bir şeye dönüştürür.',
            )}
          </p>

          {/* Live audit input — the demo starts here */}
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', maxWidth: '520px', marginBottom: '14px' }}>
            <input
              type="text"
              value={auditUrl}
              onChange={(e) => onAuditUrlChange(e.target.value)}
              placeholder="https://your-store.com"
              style={{
                flex: 1, padding: '13px 16px', borderRadius: '8px', border: '1px solid #e4e4e7',
                fontSize: '13px', fontFamily: 'ui-monospace, monospace', background: '#fff',
              }}
            />
            <button
              className="vbtn"
              onClick={() => onAudit(auditUrl)}
              disabled={isAuditLoading}
              style={{
                padding: '13px 24px', borderRadius: '8px', fontSize: '13px', fontWeight: 600,
                background: '#09090b', color: '#fff', border: 'none', cursor: 'pointer',
                minWidth: '150px', textAlign: 'center',
              }}
            >
              {isAuditLoading ? t('Auditing…', 'Denetleniyor…') : t('Run Agent Audit', 'Ajan Denetimini Başlat')}
            </button>
          </div>

          {auditError && (
            <div style={{
              background: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c',
              padding: '10px 14px', borderRadius: '6px', fontSize: '12px',
              maxWidth: '520px', marginBottom: '14px',
            }}>
              {auditError}
            </div>
          )}

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', color: '#a1a1aa' }}>{t('See it live:', 'Canlı görün:')}</span>
            <button className="qbtn" onClick={onOpenFeed}>{t('Open live feed →', 'Canlı akışı aç →')}</button>
            <button className="qbtn" onClick={onOpenAuditor}>{t('Try the auditor →', 'Denetleyiciyi dene →')}</button>
          </div>
        </div>

        {/* Before / after mockup */}
        <div style={{ position: 'relative' }}>
          <div style={{
            border: '1px solid #e4e4e7', borderRadius: '12px', background: '#ffffff', overflow: 'hidden',
            boxShadow: '0 20px 25px -5px rgba(0,0,0,0.05), 0 10px 10px -5px rgba(0,0,0,0.04)',
          }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: '6px', padding: '10px 16px',
              borderBottom: '1px solid #f4f4f5', background: '#fafafa',
            }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#e4e4e7' }} />
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#e4e4e7' }} />
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#e4e4e7' }} />
              <span style={{ margin: '0 auto', fontSize: '10px', color: '#a1a1aa', fontFamily: 'ui-monospace, monospace' }}>
                {t('what the agent sees', 'ajanın gördüğü')}
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', height: '240px', background: '#fff' }}>
              <div style={{ borderRight: '1px solid #f4f4f5', padding: '16px', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                <div style={{ fontSize: '10px', fontWeight: 700, color: '#b91c1c', textTransform: 'uppercase', marginBottom: '8px' }}>
                  {t('Without AGORA', 'AGORA olmadan')}
                </div>
                <pre style={{ margin: 0, fontSize: '9.5px', color: '#a1a1aa', fontFamily: 'ui-monospace, monospace', lineHeight: 1.4, overflow: 'hidden' }}>
{`<!DOCTYPE html>
<html>
<head>
  <script src="/js/react.js"></script>
  <script src="/js/vendor.js"></script>
  <style>.header{display:flex}</style>
</head>
<body>
  <div id="root">
    <!-- 480 KB of JavaScript
         renders your products.
         The agent never runs it. -->
  </div>
</body>
</html>`}
                </pre>
              </div>

              <div style={{ padding: '16px', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                <div style={{ fontSize: '10px', fontWeight: 700, color: '#166534', textTransform: 'uppercase', marginBottom: '8px' }}>
                  {t('With AGORA /llms.txt', 'AGORA /llms.txt ile')}
                </div>
                <pre style={{ margin: 0, fontSize: '9.5px', color: '#3f3f46', fontFamily: 'ui-monospace, monospace', lineHeight: 1.4, overflow: 'hidden' }}>
{`# Demo Store

## Products
- Wireless Headphones Pro
  ANC over-ear, 30h battery.
  Price: $299

- Leather Wallet Slim
  RFID protection.
  Price: $49

- Mechanical Keyboard TKL
  Tactile switches, RGB.
  Price: $129`}
                </pre>
              </div>
            </div>
          </div>

          <div style={{
            position: 'absolute', bottom: '-16px', left: '-16px', background: '#fff',
            border: '1px solid #e4e4e7', borderRadius: '10px', padding: '10px 14px',
            display: 'flex', alignItems: 'center', gap: '10px',
            boxShadow: '0 10px 15px -3px rgba(0,0,0,0.05)',
          }}>
            <span style={{ fontSize: '18px' }}>⚡</span>
            <div>
              <div style={{ fontSize: '11px', fontWeight: 700, color: '#09090b' }}>{t('Live audit', 'Canlı denetim')}</div>
              <div style={{ fontSize: '9px', color: '#71717a' }}>{t('runs in seconds, no signup', 'saniyeler içinde, kayıt gerekmez')}</div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Real signature coverage strip ── */}
      <section style={{ background: '#ffffff', padding: '24px 0', borderTop: '1px solid #e4e4e7', borderBottom: '1px solid #e4e4e7' }}>
        <p style={{
          textTransform: 'uppercase', fontSize: '10px', fontWeight: 700, color: '#a1a1aa',
          textAlign: 'center', letterSpacing: '0.15em', margin: '0 0 16px',
        }}>
          {t('Agent signatures detected out of the box', 'Kutudan çıktığı gibi tespit edilen ajan imzaları')}
        </p>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', alignItems: 'center', flexWrap: 'wrap', padding: '0 32px' }}>
          {DETECTED_AGENTS.map(a => (
            <span key={a} style={{
              fontSize: '11.5px', fontWeight: 600, color: '#3f3f46', fontFamily: 'ui-monospace, monospace',
              border: '1px solid #e4e4e7', background: '#fafafa', borderRadius: '5px', padding: '4px 10px',
            }}>
              {a}
            </span>
          ))}
        </div>
      </section>

      {/* ── How it works ── */}
      <section>
        <div style={{ textAlign: 'center', marginBottom: '48px' }}>
          <span style={{ fontSize: '10px', fontWeight: 700, color: '#09090b', textTransform: 'uppercase', letterSpacing: '0.15em', display: 'block', marginBottom: '8px' }}>
            {t('How it works', 'Nasıl çalışır')}
          </span>
          <h2 style={{ fontSize: '28px', fontWeight: 800, color: '#09090b', margin: 0, letterSpacing: '-0.02em' }}>
            {t('See. Be readable. Then sell.', 'Gör. Okunabilir ol. Sonra sat.')}
          </h2>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '24px' }}>
          {pipelineSteps.map(step => (
            <div key={step.num} className="stepcard" style={{ border: '1px solid #e4e4e7', borderRadius: '12px', background: '#fff', padding: '28px' }}>
              <div style={{ fontSize: '32px', fontWeight: 800, color: '#e4e4e7', lineHeight: 1, marginBottom: '16px', fontFamily: 'ui-monospace, monospace' }}>
                {step.num}
              </div>
              <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#09090b', margin: '0 0 8px' }}>{step.title}</h3>
              <p style={{ fontSize: '12.5px', color: '#71717a', margin: 0, lineHeight: 1.55 }}>{step.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Readiness checklist ── */}
      <section style={{ background: '#fafafa', border: '1px solid #e4e4e7', borderRadius: '16px', padding: '40px 48px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.8fr', gap: '48px', alignItems: 'center' }}>
          <div>
            <span style={{ fontSize: '10px', fontWeight: 700, color: '#09090b', textTransform: 'uppercase', letterSpacing: '0.15em', marginBottom: '8px', display: 'inline-block' }}>
              {t('The audit checklist', 'Denetim kontrol listesi')}
            </span>
            <h2 style={{ fontSize: '26px', fontWeight: 800, color: '#09090b', margin: '0 0 16px', letterSpacing: '-0.02em', lineHeight: 1.2 }}>
              {t('Ready for the next generation of search?', 'Yeni nesil aramaya hazır mısınız?')}
            </h2>
            <p style={{ fontSize: '13px', color: '#71717a', lineHeight: 1.6, margin: 0 }}>
              {t(
                "Agents don't render your JavaScript and don't scroll. They fetch raw HTML with a fixed token budget. Every audit scores your storefront against the four signals that decide whether an agent can quote your products — with evidence, not a grade.",
                'Ajanlar JavaScript’inizi çalıştırmaz ve sayfayı kaydırmaz. Sabit bir token bütçesiyle ham HTML çeker. Her denetim, bir ajanın ürünlerinizi alıntılayıp alıntılayamayacağını belirleyen dört sinyale göre mağazanızı puanlar — not değil, kanıtla.',
              )}
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            {checklistFeatures.map(f => (
              <div key={f.title} className="stepcard" style={{ border: '1px solid #e4e4e7', borderRadius: '8px', background: '#fff', padding: '16px 20px' }}>
                <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#09090b', margin: '0 0 6px', fontFamily: 'ui-monospace, monospace' }}>{f.title}</h4>
                <p style={{ fontSize: '11.5px', color: '#71717a', margin: 0, lineHeight: 1.45 }}>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Early access (honest — no fake pricing) ── */}
      <section>
        <div style={{ textAlign: 'center', marginBottom: '48px' }}>
          <span style={{ fontSize: '10px', fontWeight: 700, color: '#09090b', textTransform: 'uppercase', letterSpacing: '0.15em', display: 'block', marginBottom: '8px' }}>
            {t('Early access', 'Erken erişim')}
          </span>
          <h2 style={{ fontSize: '28px', fontWeight: 800, color: '#09090b', margin: 0, letterSpacing: '-0.02em' }}>
            {t('Free while we build it with you', 'Sizinle geliştirirken ücretsiz')}
          </h2>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '32px', maxWidth: '800px', margin: '0 auto' }}>
          <div style={{ border: '1px solid #e4e4e7', borderRadius: '12px', background: '#fff', padding: '36px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#09090b', margin: '0 0 8px' }}>{t('Sandbox', 'Deneme Alanı')}</h3>
              <p style={{ fontSize: '12.5px', color: '#71717a', margin: '0 0 24px' }}>{t('Everything on this page, right now, no signup.', 'Bu sayfadaki her şey, hemen şimdi, kayıt gerekmez.')}</p>
              <ul style={{ padding: 0, margin: '0 0 24px', listStyle: 'none', fontSize: '12.5px', color: '#52525b', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <li>{t('✓ Live storefront audit on any URL', '✓ Herhangi bir URL’de canlı mağaza denetimi')}</li>
                <li>{t('✓ Generated /llms.txt you can host today', '✓ Bugün yayınlayabileceğiniz üretilmiş /llms.txt')}</li>
                <li>{t('✓ Real-time agent detection feed', '✓ Gerçek zamanlı ajan tespit akışı')}</li>
                <li>{t('✓ Agent traffic simulator', '✓ Ajan trafiği simülatörü')}</li>
              </ul>
            </div>
            <button
              className="vbtn"
              onClick={onOpenAuditor}
              style={{ width: '100%', padding: '10px 0', border: '1px solid #09090b', background: 'transparent', color: '#09090b', borderRadius: '6px', fontWeight: 600, fontSize: '12.5px', cursor: 'pointer' }}
            >
              {t('Open the sandbox', 'Deneme alanını aç')}
            </button>
          </div>

          <div style={{ border: '2px solid #09090b', borderRadius: '12px', background: '#fff', padding: '36px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', position: 'relative' }}>
            <span style={{ position: 'absolute', top: '-12px', right: '20px', background: '#09090b', color: '#fff', fontSize: '9px', fontWeight: 700, padding: '3px 10px', borderRadius: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {t('Design partner', 'Tasarım ortağı')}
            </span>
            <div>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#09090b', margin: '0 0 8px' }}>{t('Pilot program', 'Pilot program')}</h3>
              <p style={{ fontSize: '12.5px', color: '#71717a', margin: '0 0 24px' }}>
                {t(
                  'For stores that want agent analytics on real traffic. Free during the pilot — you get the data, we get the feedback.',
                  'Gerçek trafik üzerinde ajan analitiği isteyen mağazalar için. Pilot süresince ücretsiz — veriyi siz alırsınız, geri bildirimi biz.',
                )}
              </p>
              <ul style={{ padding: 0, margin: '0 0 24px', listStyle: 'none', fontSize: '12.5px', color: '#52525b', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <li>{t('✓ Server-side collector on your stack', '✓ Altyapınıza sunucu tarafı toplayıcı')}</li>
                <li>{t('✓ Weekly AI traffic report (PDF)', '✓ Haftalık AI trafik raporu (PDF)')}</li>
                <li>{t('✓ Hosted /llms.txt kept in sync', '✓ Senkron tutulan barındırılan /llms.txt')}</li>
                <li>{t('✓ Direct line to the team', '✓ Ekiple doğrudan iletişim')}</li>
              </ul>
            </div>
            <a
              className="vbtn"
              href="mailto:hello@agora.dev?subject=AGORA%20pilot%20program"
              style={{ width: '100%', padding: '10px 0', border: 'none', background: '#09090b', color: '#fff', borderRadius: '6px', fontWeight: 600, fontSize: '12.5px', cursor: 'pointer', textAlign: 'center', textDecoration: 'none', display: 'inline-block', boxSizing: 'border-box' }}
            >
              {t('Talk to us', 'Bize ulaşın')}
            </a>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer style={{ borderTop: '1px solid #e4e4e7', padding: '40px 0', marginTop: '8px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '12px', color: '#71717a' }}>{t('AGORA — the analytics & storefront layer for AI agents.', 'AGORA — AI ajanları için analitik ve mağaza katmanı.')}</span>
          <span style={{ fontSize: '12px', color: '#a1a1aa' }}>© 2026 AGORA</span>
        </div>
      </footer>
    </div>
  )
}
