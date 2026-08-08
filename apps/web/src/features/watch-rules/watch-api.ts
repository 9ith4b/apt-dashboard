import { apiRequest } from "@/lib/api"

import type {
  WatchEvaluation,
  WatchPreview,
  WatchRule,
  WatchRuleHit,
  WatchRuleInput,
} from "./watch-types"

export const watchRuleQueryKey = ["watch-rules"] as const

export function listWatchRules() {
  return apiRequest<WatchRule[]>("/watch-rules")
}

export function createWatchRule(payload: WatchRuleInput) {
  return apiRequest<WatchRule>("/watch-rules", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function previewNewWatchRule(payload: WatchRuleInput) {
  return apiRequest<WatchPreview>("/watch-rules/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function updateWatchRule(
  ruleId: string,
  payload: Partial<WatchRuleInput> & { expected_version: number }
) {
  return apiRequest<WatchRule>(`/watch-rules/${ruleId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  })
}

export function listWatchRuleHits(ruleId: string) {
  return apiRequest<WatchRuleHit[]>(`/watch-rules/${ruleId}/hits?limit=100`)
}

export function previewWatchRule(ruleId: string) {
  return apiRequest<WatchPreview>(`/watch-rules/${ruleId}/preview`, {
    method: "POST",
  })
}

export function evaluateWatchRule(ruleId: string) {
  return apiRequest<WatchEvaluation>(`/watch-rules/${ruleId}/evaluate`, {
    method: "POST",
  })
}
