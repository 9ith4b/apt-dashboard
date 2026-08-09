export type DiamondEntity = {
  name: string
  type: string
  confidence: number
  evidence: string
}

export type ObservableCandidate = {
  type: string
  value: string
  normalized: string
  scope: string
  confidence: number
  evidence: string
  start_offset: number
  end_offset: number
}

export type AttackTechniqueCandidate = {
  technique_id: string
  name: string
  tactic: string | null
  confidence: number
  evidence: string
  start_offset: number
  end_offset: number
}

export type ReportSummary = {
  id: string
  source_id: string
  source_name: string
  title: string
  canonical_url: string
  language: string
  summary: string
  relevance_score: number
  relevance_reasons: string[]
  status: string
  published_at: string | null
  created_at: string
  extraction_status: "queued" | "processing" | "ready" | "failed" | null
  review_status: "pending" | "approved" | "rejected" | null
  confidence_auto: number | null
}

export type ReportAnalysis = {
  extraction_status: "queued" | "processing" | "ready" | "failed"
  review_status: "pending" | "approved" | "rejected"
  content_text: string
  final_url: string | null
  content_type: string | null
  fetched_at: string | null
  extraction_error: string | null
  actors: DiamondEntity[]
  capabilities: DiamondEntity[]
  infrastructure: DiamondEntity[]
  victims: DiamondEntity[]
  evidence: Array<{ dimension?: string; entity?: string; quote?: string }>
  observables: ObservableCandidate[]
  attack_techniques: AttackTechniqueCandidate[]
  reviewed_actors: DiamondEntity[] | null
  reviewed_capabilities: DiamondEntity[] | null
  reviewed_infrastructure: DiamondEntity[] | null
  reviewed_victims: DiamondEntity[] | null
  confidence_auto: number | null
  method_version: string
  automation_status:
    | "not_configured"
    | "processing"
    | "auto_approved"
    | "needs_review"
    | "auto_rejected"
    | "fallback"
  ai_relevance_score: number | null
  ai_classification: string | null
  ai_summary: string | null
  ai_claims: Array<Record<string, unknown>>
  ai_verification: Record<string, unknown>
  evidence_coverage: number | null
  decision_reason: string | null
  model_config_id: string | null
  analyst_note: string | null
  reviewed_at: string | null
  reviewed_by: string | null
  version: number
  updated_at: string
}

export type ReportDetail = ReportSummary & {
  analysis: ReportAnalysis | null
}

export type ReviewDecision = {
  decision: "approved" | "rejected"
  analyst_note: string | null
  expected_version: number
  actors: DiamondEntity[]
  capabilities: DiamondEntity[]
  infrastructure: DiamondEntity[]
  victims: DiamondEntity[]
  event_title: string
  confidence_analyst: number | null
}

export type ReportTask = {
  task_id: string
  report_id: string
  status: "queued"
}

export type ThreatEventSummary = {
  id: string
  title: string
  summary: string
  status: string
  confidence_auto: number | null
  confidence_analyst: number | null
  first_seen: string | null
  last_seen: string | null
  report_count: number
  actor_names: string[]
  observable_count: number
  technique_ids: string[]
  superseded_by_id: string | null
  created_at: string
  updated_at: string
}

export type ThreatEventDetail = ThreatEventSummary & {
  diamond: {
    actors: DiamondEntity[]
    capabilities: DiamondEntity[]
    infrastructure: DiamondEntity[]
    victims: DiamondEntity[]
  }
  reports: ReportSummary[]
  observables: Array<{
    id: string
    type: string
    value_original: string
    value_normalized: string
    scope: string
    confidence: number
    evidence_id: string
    evidence: string
    first_seen: string | null
    last_seen: string | null
  }>
  attack_techniques: Array<{
    technique_id: string
    name: string
    tactic: string | null
    confidence: number
    evidence_id: string
    evidence: string
  }>
}

export type EventMergeCandidate = {
  id: string
  source_event: {
    id: string
    title: string
    first_seen: string | null
    report_count: number
  }
  target_event: {
    id: string
    title: string
    first_seen: string | null
    report_count: number
  }
  score: number
  features: Record<string, unknown>
  status: "pending" | "approved" | "rejected" | "undone"
  decision_reason: string | null
  moved_report_ids: string[]
  reviewed_at: string | null
  version: number
  created_at: string
}

export type ThreatActorSummary = {
  id: string
  canonical_name: string
  aliases: string[]
  origin_country: string | null
  event_count: number
  first_seen: string | null
  last_seen: string | null
  latest_event_id: string | null
  latest_event_title: string | null
}

export type ActorEvent = {
  id: string
  title: string
  summary: string
  status: string
  confidence: number | null
  first_seen: string | null
  last_seen: string | null
  reported_name: string
}

export type ThreatActorDetail = ThreatActorSummary & {
  description: string
  events: ActorEvent[]
  timeline: Array<{
    key: string
    label: string
    event_count: number
  }>
}

export type ActorTracking = {
  actor_id: string
  canonical_name: string
  period: {
    date_from: string
    date_to: string
    previous_from: string
    previous_to: string
    day_count: number
    bucket: "day" | "week" | "month"
  }
  comparison: {
    current_event_count: number
    previous_event_count: number
    absolute_change: number
    percentage_change: number | null
  }
  trend: Array<{
    key: string
    label: string
    event_count: number
  }>
  changes: Array<{
    category: "malware" | "infrastructure" | "techniques" | "targets"
    current_values: string[]
    previous_values: string[]
    new_values: string[]
    disappeared_values: string[]
  }>
  events: ActorEvent[]
}

export type ActorTrackingSummary = {
  actor_id: string
  status: "draft"
  title: string
  summary: string
  highlights: string[]
  caveats: string[]
  supporting_event_ids: string[]
  supporting_evidence_ids: string[]
  generated_at: string
  method_version: string
}
