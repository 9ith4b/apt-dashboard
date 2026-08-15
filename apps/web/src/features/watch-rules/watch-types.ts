export type WatchConditions = {
  campaign_ids: string[]
  keywords: string[]
  actor_names: string[]
  observable_types: string[]
  technique_ids: string[]
  min_confidence: number | null
}

export type WatchRule = {
  id: string
  name: string
  description: string
  conditions: WatchConditions
  severity: "info" | "low" | "medium" | "high" | "critical"
  enabled: boolean
  created_by: string
  version: number
  hit_count: number
  created_at: string
  updated_at: string
}

export type WatchRuleInput = {
  name: string
  description: string
  conditions: WatchConditions
  severity: WatchRule["severity"]
  enabled: boolean
  created_by: string
}

export type WatchRuleHit = {
  id: string
  rule_id: string
  subject_type: string
  subject_id: string
  subject_title: string
  matched_on: Record<string, unknown>
  created_at: string
}

export type WatchPreview = {
  rule_id: string | null
  match_count: number
  matches: WatchRuleHit[]
}

export type WatchEvaluation = {
  rule_id: string
  evaluated_count: number
  created_hit_count: number
  hit_count: number
}
