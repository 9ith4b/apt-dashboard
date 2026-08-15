import { apiRequest } from "@/lib/api"

import type {
  CampaignAutomationStatus,
  CampaignBackfillRead,
  CampaignDetail,
  CampaignStage,
  CampaignStatus,
  CampaignSummary,
} from "./campaign-types"

export const campaignQueryKey = ["campaigns"] as const
export const campaignAutomationQueryKey = [
  "campaign-automation-status",
] as const

export function listCampaigns() {
  return apiRequest<CampaignSummary[]>("/campaigns?limit=200")
}

export function getCampaign(campaignId: string) {
  return apiRequest<CampaignDetail>(`/campaigns/${campaignId}`)
}

export function getCampaignAutomationStatus() {
  return apiRequest<CampaignAutomationStatus>("/campaigns/automation/status")
}

export function backfillCampaigns(
  payload: { limit?: number; force?: boolean } = {}
) {
  return apiRequest<CampaignBackfillRead>("/campaigns/automation/backfill", {
    method: "POST",
    body: JSON.stringify({ limit: 200, force: false, ...payload }),
  })
}

export function createCampaign(payload: {
  name: string
  description: string
  status: CampaignStatus
}) {
  return apiRequest<CampaignDetail>("/campaigns", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function assignCampaignEvent(
  campaignId: string,
  payload: {
    event_id: string
    stage: CampaignStage
    confidence: number
    evidence_note: string
    expected_version: number
  }
) {
  return apiRequest<CampaignDetail>(`/campaigns/${campaignId}/events`, {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function removeCampaignEvent(
  campaignId: string,
  eventId: string,
  expectedVersion: number
) {
  return apiRequest<void>(
    `/campaigns/${campaignId}/events/${eventId}?expected_version=${expectedVersion}`,
    { method: "DELETE" }
  )
}
