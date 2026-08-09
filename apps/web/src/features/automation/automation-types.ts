export type AIProvider =
  "openai" | "deepseek" | "dashscope" | "siliconflow" | "ollama" | "custom"

export type AIModelConfig = {
  id: string
  name: string
  provider: AIProvider
  base_url: string
  model: string
  has_api_key: boolean
  enabled: boolean
  is_default: boolean
  timeout_seconds: number
  temperature: number
  updated_by: string
  last_test_status: "succeeded" | "failed" | null
  last_test_error: string | null
  last_tested_at: string | null
  created_at: string
  updated_at: string
}

export type AIModelConfigInput = {
  name: string
  provider: AIProvider
  base_url: string
  model: string
  api_key?: string
  enabled: boolean
  is_default: boolean
  timeout_seconds: number
  temperature: number
}

export type AIProcessingPolicy = {
  automation_enabled: boolean
  require_verification: boolean
  auto_create_events: boolean
  relevance_threshold: number
  auto_approve_threshold: number
  auto_reject_threshold: number
  minimum_evidence_coverage: number
  max_article_chars: number
  updated_by: string
  updated_at: string
}

export type AutomationStatus = {
  automation_enabled: boolean
  active_model_name: string | null
  active_model: string | null
  open_exceptions: number
  processed_24h: number
  auto_approved_24h: number
  needs_review_24h: number
  failed_24h: number
}

export type AIModelTestResult = {
  ok: boolean
  message: string
  latency_ms: number
  model: string
}

export type BackfillResult = {
  promoted: number
}
