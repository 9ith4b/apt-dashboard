import { apiRequest } from "@/lib/api"

import type {
  ActorTracking,
  ActorTrackingSummary,
  EventMergeCandidate,
  ReportDetail,
  ReportSummary,
  ReportTask,
  ReviewDecision,
  ThreatEventDetail,
  ThreatEventSummary,
  ThreatActorDetail,
  ThreatActorSummary,
} from "./intelligence-types"

export const reportQueryKey = ["reports"] as const
export const reviewQueueKey = ["reviews"] as const
export const eventQueryKey = ["events"] as const
export const actorQueryKey = ["actors"] as const
export const actorTrackingQueryKey = ["actor-tracking"] as const
export const mergeCandidateQueryKey = ["event-merge-candidates"] as const

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

export function listMergeCandidates(
  status: EventMergeCandidate["status"] = "pending"
) {
  return apiRequest<EventMergeCandidate[]>(
    `/events/merge-candidates?candidate_status=${encodeURIComponent(status)}&limit=100`
  )
}

export function decideEventMerge(
  candidateId: string,
  payload: {
    decision: "approved" | "rejected"
    reason: string | null
    expected_version: number
  }
) {
  return apiRequest<EventMergeCandidate>(
    `/events/merge-candidates/${candidateId}/decision`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  )
}

export function undoEventMerge(candidateId: string, expectedVersion: number) {
  return apiRequest<EventMergeCandidate>(
    `/events/merge-candidates/${candidateId}/undo`,
    {
      method: "POST",
      body: JSON.stringify({ expected_version: expectedVersion }),
    }
  )
}

function actorQuery(
  path: string,
  filters: {
    dateFrom?: string
    dateTo?: string
    granularity?: "month" | "year"
  }
) {
  const params = new URLSearchParams()
  if (filters.dateFrom) params.set("date_from", filters.dateFrom)
  if (filters.dateTo) params.set("date_to", filters.dateTo)
  if (filters.granularity) params.set("granularity", filters.granularity)
  const query = params.toString()
  return `${path}${query ? `?${query}` : ""}`
}

export function listThreatActors(filters: {
  dateFrom?: string
  dateTo?: string
}) {
  const path = actorQuery("/actors", filters)
  const separator = path.includes("?") ? "&" : "?"
  return apiRequest<ThreatActorSummary[]>(`${path}${separator}limit=200`)
}

export function getThreatActor(
  actorId: string,
  filters: {
    dateFrom?: string
    dateTo?: string
    granularity: "month" | "year"
  }
) {
  return apiRequest<ThreatActorDetail>(
    actorQuery(`/actors/${actorId}`, filters)
  )
}

export function getActorTracking(
  actorId: string,
  filters: {
    dateFrom?: string
    dateTo?: string
  }
) {
  return apiRequest<ActorTracking>(
    actorQuery(`/actors/${actorId}/tracking`, filters)
  )
}

export function generateActorTrackingSummary(
  actorId: string,
  filters: {
    dateFrom?: string
    dateTo?: string
  }
) {
  return apiRequest<ActorTrackingSummary>(
    actorQuery(`/actors/${actorId}/tracking/summary`, filters),
    { method: "POST" }
  )
}

export function actorTrackingExportUrl(
  actorId: string,
  filters: { dateFrom?: string; dateTo?: string },
  format: "json" | "csv"
) {
  const path = actorQuery(`/actors/${actorId}/tracking/export`, filters)
  const separator = path.includes("?") ? "&" : "?"
  return `/api/v1${path}${separator}format=${format}`
}
