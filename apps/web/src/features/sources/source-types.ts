export type SourceHealth = "pending" | "healthy" | "degraded" | "disabled"
export type SourceType = "rss" | "web" | "x" | "telegram"

export type Source = {
  id: string
  type: SourceType
  name: string
  url: string | null
  config: Record<string, unknown>
  credential_configured: boolean
  enabled: boolean
  health_status: SourceHealth
  poll_interval_minutes: number
  last_checked_at: string | null
  last_success_at: string | null
  next_poll_at: string | null
  last_error: string | null
  consecutive_failures: number
  report_count: number
  created_at: string
  updated_at: string
}

export type SourceCreate = {
  type: SourceType
  name: string
  url: string | null
  config: Record<string, unknown>
  secret_ref: string | null
  enabled: boolean
  poll_interval_minutes: number
}

export type SourceUpdate = Partial<
  Pick<
    SourceCreate,
    | "name"
    | "url"
    | "config"
    | "secret_ref"
    | "enabled"
    | "poll_interval_minutes"
  >
>

export type PollTask = {
  task_id: string
  source_id: string
  status: "queued"
}
