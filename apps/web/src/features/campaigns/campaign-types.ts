export type CampaignStatus = "active" | "inactive" | "closed"

export type CampaignStage =
  | "unknown"
  | "reconnaissance"
  | "resource-development"
  | "initial-access"
  | "execution"
  | "persistence"
  | "privilege-escalation"
  | "defense-evasion"
  | "credential-access"
  | "discovery"
  | "lateral-movement"
  | "collection"
  | "command-and-control"
  | "exfiltration"
  | "impact"

export type CampaignSummary = {
  id: string
  name: string
  description: string
  first_seen: string | null
  last_seen: string | null
  status: CampaignStatus
  event_count: number
  actor_names: string[]
  stages: string[]
  version: number
  created_at: string
  updated_at: string
}

export type CampaignDetail = CampaignSummary & {
  events: Array<{
    event_id: string
    event_title: string
    event_summary: string
    event_first_seen: string | null
    event_last_seen: string | null
    stage: CampaignStage
    confidence: number
    evidence_note: string
    reviewed_at: string
    reviewed_by: string
    actor_names: string[]
  }>
}

export type CampaignAutomationStatus = {
  automation_enabled: boolean
  unattended_mode: boolean
  model_configured: boolean
  ready: boolean
  confirmed_event_count: number
  eligible_event_count: number
  assigned_event_count: number
  unassigned_event_count: number
  campaign_count: number
  pending_job_count: number
  last_job_status: string | null
  last_job_at: string | null
  last_job_result: Record<string, unknown>
  last_job_error: string | null
}

export type CampaignBackfillRead = {
  queued: number
  job_ids: string[]
}
