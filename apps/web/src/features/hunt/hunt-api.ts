import { apiRequest } from "@/lib/api"

import type {
  Indicator,
  IndicatorPromotion,
  ObservableDetail,
  ObservableEnrichment,
  ObservableSummary,
} from "./hunt-types"

export const observableQueryKey = ["observables"] as const
export const indicatorQueryKey = ["indicators"] as const
export const observableCountQueryKey = ["observables", "count"] as const
export const indicatorCountQueryKey = ["indicators", "count"] as const

export function listObservables(filters: { q?: string; type?: string }) {
  const params = new URLSearchParams({ limit: "200" })
  if (filters.q) params.set("q", filters.q)
  if (filters.type) params.set("observable_type", filters.type)
  return apiRequest<ObservableSummary[]>(`/observables?${params}`)
}

export function countObservables(filters: { q?: string; type?: string }) {
  const params = new URLSearchParams()
  if (filters.q) params.set("q", filters.q)
  if (filters.type) params.set("observable_type", filters.type)
  const query = params.toString()
  return apiRequest<number>(`/observables/count${query ? `?${query}` : ""}`)
}

export function getObservable(observableId: string) {
  return apiRequest<ObservableDetail>(`/observables/${observableId}`)
}

export function enrichObservable(observableId: string) {
  return apiRequest<ObservableEnrichment>(
    `/observables/${observableId}/enrich`,
    { method: "POST" }
  )
}

export function promoteObservable(
  observableId: string,
  payload: IndicatorPromotion
) {
  return apiRequest<Indicator>(`/observables/${observableId}/promote`, {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function listIndicators(filters: {
  q?: string
  type?: string
  revoked?: boolean
}) {
  const params = new URLSearchParams({ limit: "200" })
  if (filters.q) params.set("q", filters.q)
  if (filters.type) params.set("observable_type", filters.type)
  if (filters.revoked !== undefined) {
    params.set("revoked", String(filters.revoked))
  }
  return apiRequest<Indicator[]>(`/indicators?${params}`)
}

export function countIndicators(filters: {
  q?: string
  type?: string
  revoked?: boolean
}) {
  const params = new URLSearchParams()
  if (filters.q) params.set("q", filters.q)
  if (filters.type) params.set("observable_type", filters.type)
  if (filters.revoked !== undefined) {
    params.set("revoked", String(filters.revoked))
  }
  const query = params.toString()
  return apiRequest<number>(`/indicators/count${query ? `?${query}` : ""}`)
}

export function updateIndicator(
  indicatorId: string,
  payload: {
    expected_version: number
    revoked?: boolean
    confidence?: number
    severity?: Indicator["severity"]
    valid_until?: string
  }
) {
  return apiRequest<Indicator>(`/indicators/${indicatorId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  })
}
