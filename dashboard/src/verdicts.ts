// Single source of truth for all 7 verdict classes.
// Colors and labels derive from backend verdict only — no frontend UA parsing (D-INT-3).
export interface VerdictStyle {
  color: string
  bg: string
  border: string
  label: string
}

export const VERDICT_STYLE: Record<string, VerdictStyle> = {
  assistant_browse:  { color: '#166534', bg: '#f0fdf4', border: '#bbf7d0', label: 'Assistant Browse' },
  crawler_search:    { color: '#1e40af', bg: '#eff6ff', border: '#bfdbfe', label: 'Search Crawler'   },
  crawler_training:  { color: '#6b21a8', bg: '#faf5ff', border: '#e9d5ff', label: 'Training Crawler' },
  shopping_agent:    { color: '#b45309', bg: '#fffbeb', border: '#fde68a', label: 'Shopping Agent'   },
  automation_other:  { color: '#991b1b', bg: '#fef2f2', border: '#fecaca', label: 'Automation'       },
  human:             { color: '#3f3f46', bg: '#f4f4f5', border: '#e4e4e7', label: 'Human'            },
  unknown:           { color: '#71717a', bg: '#fafafa', border: '#e4e4e7', label: 'Unknown'          },
}

export const AI_VERDICTS = new Set([
  'assistant_browse', 'crawler_search', 'crawler_training', 'shopping_agent', 'automation_other',
])

export const VERDICT_ORDER = [
  'assistant_browse', 'crawler_search', 'crawler_training',
  'shopping_agent', 'automation_other', 'human', 'unknown',
]

export function verdictStyle(v: string | null): VerdictStyle {
  return (v != null && v in VERDICT_STYLE ? VERDICT_STYLE[v] : null) ?? VERDICT_STYLE.unknown
}
