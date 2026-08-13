export type IndicatorSummary = {
  id: string
  purpose: string
  valid_from: string
  valid_until: string
  confidence: number
  severity: "info" | "low" | "medium" | "high" | "critical"
  revoked: boolean
  reviewed_by: string
  version: number
}

export type ObservableSummary = {
  id: string
  type: string
  value_original: string
  value_normalized: string
  scope: string
  validation_status: string
  first_seen: string | null
  last_seen: string | null
  report_count: number
  event_count: number
  evidence_count: number
  ai_disposition: "malicious" | "suspicious" | "benign" | "context" | null
  ai_role: string | null
  ai_confidence: number | null
  ai_decision_reason: string | null
  ai_decided_at: string | null
  indicator: IndicatorSummary | null
}

export type ObservableDetail = ObservableSummary & {
  reports: Array<{
    report_id: string
    report_title: string
    source_name: string
    published_at: string | null
    confidence: number
    evidence_id: string
    evidence: string
  }>
  events: Array<{
    event_id: string
    event_title: string
    first_seen: string | null
    confidence: number
    evidence_id: string
    evidence: string
  }>
  enrichments: ObservableEnrichment[]
}

export type ObservableEnrichment = {
  id: string
  provider: string
  status: string
  queried_at: string
  expires_at: string
  result: Record<string, unknown>
  error: string | null
}

export type Indicator = IndicatorSummary & {
  observable_id: string
  observable_type: string
  value_normalized: string
  pattern: string
  reviewed_at: string
  evidence_ids: string[]
}

export type IndicatorPromotion = {
  purpose: string
  valid_from: string
  valid_until: string
  confidence: number
  severity: Indicator["severity"]
  evidence_ids: string[]
}
