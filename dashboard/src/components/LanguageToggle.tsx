import { useI18n } from '../i18n'
import type { Lang } from '../i18n'

/** Segmented EN | TR switch that lives in the dark app bar. */
export function LanguageToggle() {
  const { lang, setLang } = useI18n()
  const options: Lang[] = ['en', 'tr']

  return (
    <div
      role="group"
      aria-label="Language"
      style={{
        display: 'flex', flexShrink: 0, border: '1px solid #27272a',
        borderRadius: '7px', overflow: 'hidden', background: '#18181b',
      }}
    >
      {options.map(opt => {
        const isActive = lang === opt
        return (
          <button
            key={opt}
            onClick={() => setLang(opt)}
            aria-pressed={isActive}
            style={{
              padding: '5px 11px', fontSize: '11.5px', fontWeight: 700, letterSpacing: '0.03em',
              border: 'none', cursor: 'pointer', transition: 'color 120ms, background 120ms',
              background: isActive ? '#fafafa' : 'transparent',
              color: isActive ? '#09090b' : '#a1a1aa',
            }}
            onMouseEnter={e => { if (!isActive) e.currentTarget.style.color = '#fafafa' }}
            onMouseLeave={e => { if (!isActive) e.currentTarget.style.color = '#a1a1aa' }}
          >
            {opt.toUpperCase()}
          </button>
        )
      })}
    </div>
  )
}
