import { apiRequest } from "@/lib/api"

import type {
  ReportDetail,
  ReportSummary,
  ReportTask,
  ReviewDecision,
  ThreatEventDetail,
  ThreatEventSummary,
} from "./intelligence-types"

export const reportQueryKey = ["reports"] as const
export const reviewQueueKey = ["reviews"] as const
export const eventQueryKey = ["events"] as const

export function listReports() {
  return apiRequest<ReportSummary[]>("/reports?limit=200")
}

export function getReport(reportId: string) {
  return apiRequest<ReportDetail>(`/reports/${reportId}`)
}

export function listReviewQueue(reviewStatus = "pending") {
  return apiRequest<ReportSummary[]>(
    `/reviews?review_status=${encodeURIComponent(reviewStatus)}&limit=200`
  )
}

export function enrichReport(reportId: string) {
  return apiRequest<ReportTask>(`/reports/${reportId}/enrich`, {
    method: "POST",
  })
}

export function decideReview(reportId: string, payload: ReviewDecision) {
  return apiRequest<ReportDetail>(`/reviews/${reportId}/decision`, {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function listThreatEvents() {
  return apiRequest<ThreatEventSummary[]>("/events?limit=200")
}

export function getThreatEvent(eventId: string) {
  return apiRequest<ThreatEventDetail>(`/events/${eventId}`)
}
