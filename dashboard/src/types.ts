export interface AgoraEvent {
  id: number
  ts: string
  method: string
  path: string
  status: number
  ua: string
  verdict: string | null
  confidence: number | null
  evidence: string[]
}

export interface HourlyBucket {
  hour: string
  verdict: string
  count: number
}

export interface StatsData {
  verdict_counts: Record<string, number>
  top_paths: Array<{ path: string; count: number }>
  hourly_buckets: HourlyBucket[]
}

export interface DemandProduct {
  path: string
  agent_hits: number
  /** Share of agent requests to this path answered with 2xx (0–1). */
  success_rate: number
  last_seen: string
  verdicts: Record<string, number>
}

export interface DemandData {
  site_id: string
  window: string
  agent_verdicts: string[]
  total_agent_hits: number
  top_products: DemandProduct[]
}

export interface BenchmarkRow {
  rank: number
  is_you: boolean
  /** Own store name for your row; anonymized "Competitor #N" for peers. */
  label: string
  agent_hits: number
  agent_success_rate: number
  score: number
}

export interface BenchmarkData {
  site_id: string
  window: string
  category: string | null
  your_rank: number | null
  total_in_category: number
  leaderboard: BenchmarkRow[]
}

export interface ChecklistItem {
  pass_status: boolean
  evidence: string
}

export interface CatalogProduct {
  name: string
  url: string
  price: number | null
}

export interface CatalogInfo {
  source: string
  total_count: number
  visible_to_agent: number
  coverage_pct: number
  sample: CatalogProduct[]
}

export interface LeadSummary {
  id: number
  email: string
  url: string | null
  coverage_pct: number | null
  created_at: string
}

export interface AuditResult {
  url: string
  total_bytes: number
  script_ratio: number
  extractable_text_pct: number
  raw_html: string
  markdown: string
  /** Preview only — the full file ships with the paid install package. */
  generated_llms_txt: string
  llms_txt_truncated: boolean
  catalog: CatalogInfo | null
  checklist: {
    llms_txt: ChecklistItem
    product_content: ChecklistItem
    schema_org: ChecklistItem
    robots_txt: ChecklistItem
  }
}
