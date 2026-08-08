import { apiRequest } from "@/lib/api"

import type { OperationJob } from "./operations-types"

export const operationJobQueryKey = ["operation-jobs"] as const

export function listOperationJobs(status?: OperationJob["status"]) {
  const params = new URLSearchParams({ limit: "200" })
  if (status) params.set("job_status", status)
  return apiRequest<OperationJob[]>(`/operations/jobs?${params}`)
}

export function cancelOperationJob(job: OperationJob) {
  return apiRequest<OperationJob>(
    `/operations/jobs/${job.id}/cancel?expected_version=${job.version}`,
    { method: "POST" }
  )
}

export function retryOperationJob(jobId: string) {
  return apiRequest<OperationJob>(`/operations/jobs/${jobId}/retry`, {
    method: "POST",
  })
}
