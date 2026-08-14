type Props = {
  size?: number
}

/**
 * AGORA app-icon badge — the classical agora colonnade (pediment + columns +
 * base) in white on an indigo gradient tile. Mirrors public/favicon.svg exactly
 * so the browser tab, header, and any share preview read as one brand mark.
 */
export function BrandBadge({ size = 30 }: Props) {
  const gid = 'agoraBadgeGrad'
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      role="img"
      aria-label="AGORA"
      style={{ display: 'block', flexShrink: 0 }}
    >
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#6366f1" />
          <stop offset="1" stopColor="#8b93f8" />
        </linearGradient>
      </defs>
      <rect x="0" y="0" width="100" height="100" rx="24" fill={`url(#${gid})`} />
      {/* pediment (roof) */}
      <path d="M50 24 L74 42 H26 Z" fill="#ffffff" />
      {/* architrave */}
      <rect x="26" y="45" width="48" height="5" rx="1.6" fill="#ffffff" />
      {/* colonnade / analytics columns */}
      <rect x="30.5" y="53" width="5.5" height="20" rx="1.4" fill="#ffffff" />
      <rect x="41.7" y="53" width="5.5" height="20" rx="1.4" fill="#ffffff" />
      <rect x="52.9" y="53" width="5.5" height="20" rx="1.4" fill="#ffffff" />
      <rect x="64.1" y="53" width="5.5" height="20" rx="1.4" fill="#ffffff" />
      {/* stylobate (base) */}
      <rect x="24" y="74.5" width="52" height="6" rx="2" fill="#ffffff" />
    </svg>
  )
}
