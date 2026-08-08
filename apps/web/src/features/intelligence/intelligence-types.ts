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
}

export type ReportTask = {
  task_id: string
  report_id: string
  status: "queued"
}
