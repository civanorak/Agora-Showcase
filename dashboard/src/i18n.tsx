import { createContext, useCallback, useContext, useState } from 'react'
import type { ReactNode } from 'react'

/**
 * Lightweight i18n for AGORA.
 *
 * Design: the source UI is written in English, so instead of maintaining a
 * separate key dictionary we expose a `t(en, tr)` picker bound to the active
 * language. Each call site reads naturally and is trivial to review:
 *
 *   const { t } = useI18n()
 *   t('Run Agent Audit', 'Ajan Denetimini Başlat')
 *
 * Technical values that come from the backend (verdict ids, evidence strings)
 * are intentionally NOT translated — they are stable machine labels.
 */

export type Lang = 'en' | 'tr'

const STORAGE_KEY = 'agora_lang'

interface I18nContextValue {
  lang: Lang
  setLang: (lang: Lang) => void
}

const I18nContext = createContext<I18nContextValue>({ lang: 'en', setLang: () => {} })

function detectInitialLang(): Lang {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'tr' || saved === 'en') return saved
  } catch { /* localStorage may be unavailable */ }
  const nav = typeof navigator !== 'undefined' ? navigator.language?.toLowerCase() : ''
  return nav?.startsWith('tr') ? 'tr' : 'en'
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(detectInitialLang)

  const setLang = useCallback((next: Lang) => {
    setLangState(next)
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch { /* ignore persistence failure */ }
    if (typeof document !== 'undefined') {
      document.documentElement.lang = next
    }
  }, [])

  return <I18nContext.Provider value={{ lang, setLang }}>{children}</I18nContext.Provider>
}

export function useI18n() {
  const { lang, setLang } = useContext(I18nContext)
  const t = useCallback((en: string, tr: string) => (lang === 'tr' ? tr : en), [lang])
  return { lang, setLang, t }
}
