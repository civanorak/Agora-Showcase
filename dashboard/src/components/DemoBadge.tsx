import { useI18n } from '../i18n'

/**
 * Honest "this is seeded demo data, not live traffic" marker.
 * Used on surfaces that compute real logic over the sandbox seed events
 * (Live Feed, Agent Demand) so visitors don't mistake them for real traffic.
 */
export function DemoBadge() {
  const { t } = useI18n()
  return (
    <span
      title={t('Seeded sandbox data — not live traffic from a real store.', 'Tohumlanmış deneme verisi — gerçek bir mağazadan gelen canlı trafik değil.')}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: '5px',
        fontSize: '10.5px', fontWeight: 700, letterSpacing: '0.04em',
        textTransform: 'uppercase', whiteSpace: 'nowrap',
        color: '#92400e', background: '#fffbeb', border: '1px solid #fde68a',
        borderRadius: '5px', padding: '2px 8px', cursor: 'default',
      }}
    >
      <span aria-hidden style={{ fontSize: '9px' }}>●</span>
      {t('Demo data', 'Demo verisi')}
    </span>
  )
}
