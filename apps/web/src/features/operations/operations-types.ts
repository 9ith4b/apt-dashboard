export type OperationJob = {
  id: string
  task_id: string
  job_type: "source_poll" | "report_enrichment" | "campaign_clustering"
  subject_type: string
  subject_id: string
  status: "queued" | "running" | "succeeded" | "failed" | "canceled"
  progress: number
  attempt: number
  payload: Record<string, unknown>
  result: Record<string, unknown>
  error: string | null
  requested_by: string
  started_at: string | null
  finished_at: string | null
  parent_job_id: string | null
  version: number
  created_at: string
  updated_at: string
}
