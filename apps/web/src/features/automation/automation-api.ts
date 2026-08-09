import { apiRequest } from "@/lib/api"

import type {
  AIModelConfig,
  AIModelConfigInput,
  AIModelTestResult,
  AIProcessingPolicy,
  AutomationStatus,
  BackfillResult,
} from "./automation-types"

export const automationQueryKey = ["ai-automation"] as const

export function listModelConfigs() {
  return apiRequest<AIModelConfig[]>("/ai/configs")
}

export function createModelConfig(payload: AIModelConfigInput) {
  return apiRequest<AIModelConfig>("/ai/configs", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function updateModelConfig(
  configId: string,
  payload: Partial<AIModelConfigInput> & { clear_api_key?: boolean }
) {
  return apiRequest<AIModelConfig>(`/ai/configs/${configId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  })
}

export function deleteModelConfig(configId: string) {
  return apiRequest<void>(`/ai/configs/${configId}`, { method: "DELETE" })
}

export function testModelConfig(configId: string) {
  return apiRequest<AIModelTestResult>(`/ai/configs/${configId}/test`, {
    method: "POST",
  })
}

export function getProcessingPolicy() {
  return apiRequest<AIProcessingPolicy>("/ai/policy")
}

export function updateProcessingPolicy(
  payload: Omit<AIProcessingPolicy, "updated_by" | "updated_at">
) {
  return apiRequest<AIProcessingPolicy>("/ai/policy", {
    method: "PUT",
    body: JSON.stringify(payload),
  })
}

export function getAutomationStatus() {
  return apiRequest<AutomationStatus>("/ai/status")
}

export function backfillFilteredReports() {
  return apiRequest<BackfillResult>("/ai/backfill", { method: "POST" })
}
