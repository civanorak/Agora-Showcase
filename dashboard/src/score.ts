import type { AuditResult } from './types'

export interface ReadinessScore {
  /** 0–100, computed only from measured signals (no estimates). */
  value: number
  /** Plain-language band label (Turkish). */
  label: string
  /** Band color. */
  color: string
}

/**
 * Yapay Zekâ Hazırlık Skoru — tamamen ölçülen değerlerden türetilir:
 *   • 4 checklist maddesinin kaçı geçti (her biri backend'de ölçülür)
 *   • kataloğun ajana görünürlük yüzdesi (yalnızca yapılandırılmış katalog varsa)
 *
 * Katalog kapsamı ölçülebiliyorsa: checklist %60 + kapsama %40 ağırlıklı.
 * Ölçülemiyorsa (ürün adları yapılandırılmış bir uçtan gelmiyorsa): checklist %100.
 * Bu bir tahmin değil, ölçülen olguların tek sayıya indirgenmiş halidir.
 */
export function computeReadiness(result: AuditResult): ReadinessScore {
  const c = result.checklist
  const passed = [c.llms_txt, c.product_content, c.schema_org, c.robots_txt]
    .filter(item => item.pass_status).length
  const checklistScore = passed / 4 // 0..1

  const catalog = result.catalog
  const hasCoverage = catalog != null && catalog.sample.length > 0

  const value = hasCoverage
    ? Math.round(checklistScore * 60 + (catalog!.coverage_pct / 100) * 40)
    : Math.round(checklistScore * 100)

  return { value, ...band(value) }
}

function band(value: number): { label: string; color: string } {
  if (value >= 80) return { label: 'Çok iyi', color: '#166534' }
  if (value >= 60) return { label: 'Geliştirilebilir', color: '#b45309' }
  if (value >= 40) return { label: 'Zayıf', color: '#c2410c' }
  return { label: 'Kritik', color: '#b91c1c' }
}
