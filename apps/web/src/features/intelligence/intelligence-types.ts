export type DiamondEntity = {
  name: string
  type: string
  confidence: number
  evidence: string
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
  reviewed_actors: DiamondEntity[] | null
  reviewed_capabilities: DiamondEntity[] | null
  reviewed_infrastructure: DiamondEntity[] | null
  reviewed_victims: DiamondEntity[] | null
  confidence_auto: number | null
  method_version: string
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
