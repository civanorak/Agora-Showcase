type Tone = 'dark' | 'light'

type Props = {
  size?: number
  /** 'dark' = for dark backgrounds (app bar), 'light' = for light backgrounds (hero). */
  tone?: Tone
}

// Column/architrave color flips with the background; the accent (pediment + base)
// stays the same periwinkle so the mark keeps one brand identity everywhere.
const STRUCTURE: Record<Tone, string> = {
  dark: '#e4e4e7',
  light: '#18181b',
}
const ACCENT: Record<Tone, string> = {
  dark: '#a5b4fc',
  light: '#818cf8',
}

/**
 * AGORA brand mark — a classical stoa/temple facade (pediment + columns + base)
 * evoking the ancient agora (public marketplace). Reads as both a civic building
 * and an abstract monogram.
 */
export function AgoraMark({ size = 24, tone = 'dark' }: Props) {
  const structure = STRUCTURE[tone]
  const accent = ACCENT[tone]
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 28 28"
      fill="none"
      role="img"
      aria-label="AGORA"
    >
      {/* pediment (roof) */}
      <path d="M14 3 L24.5 10.5 H3.5 Z" fill={accent} />
      {/* architrave */}
      <rect x="3.5" y="11.4" width="21" height="2" rx="0.6" fill={structure} />
      {/* columns */}
      <rect x="6" y="14.6" width="2.2" height="8" rx="0.6" fill={structure} />
      <rect x="10.9" y="14.6" width="2.2" height="8" rx="0.6" fill={structure} />
      <rect x="15.8" y="14.6" width="2.2" height="8" rx="0.6" fill={structure} />
      <rect x="20.7" y="14.6" width="2.2" height="8" rx="0.6" fill={structure} />
      {/* stylobate (base) */}
      <rect x="3" y="23.2" width="22" height="2.4" rx="0.7" fill={accent} />
    </svg>
  )
}
