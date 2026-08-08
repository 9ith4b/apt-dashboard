import { apiRequest } from "@/lib/api"

import type {
  PollTask,
  Source,
  SourceCreate,
  SourceUpdate,
} from "./source-types"

export const sourceQueryKey = ["sources"] as const

export function listSources() {
  return apiRequest<Source[]>("/sources")
}

export function createSource(payload: SourceCreate) {
  return apiRequest<Source>("/sources", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function updateSource(sourceId: string, payload: SourceUpdate) {
  return apiRequest<Source>(`/sources/${sourceId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  })
}

export function pollSource(sourceId: string) {
  return apiRequest<PollTask>(`/sources/${sourceId}/poll`, {
    method: "POST",
  })
}
