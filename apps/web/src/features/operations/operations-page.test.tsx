import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import App from "@/App"

const failedJob = {
  id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  task_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  job_type: "source_poll",
  subject_type: "source",
  subject_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  status: "failed",
  progress: 10,
  attempt: 1,
  payload: { source_name: "Vendor RSS" },
  result: {},
  error: "Feed request timed out",
  requested_by: "scheduler",
  started_at: "2026-08-08T08:00:00Z",
  finished_at: "2026-08-08T08:01:00Z",
  parent_job_id: null,
  version: 3,
  created_at: "2026-08-08T08:00:00Z",
  updated_at: "2026-08-08T08:01:00Z",
}

const queuedJob = {
  ...failedJob,
  id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
  task_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
  job_type: "report_enrichment",
  status: "queued",
  progress: 0,
  error: null,
  payload: { report_title: "APT29 phishing report" },
  version: 1,
}

function response(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    headers: { "Content-Type": "application/json" },
  })
}

describe("operations page", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/operations")
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input)
        if (url === "/api/v1/notifications?limit=50") {
          return Promise.resolve(response({ unread_count: 0, items: [] }))
        }
        if (url.startsWith("/api/v1/operations/jobs?")) {
          return Promise.resolve(response([failedJob, queuedJob]))
        }
        if (url.endsWith(`/operations/jobs/${failedJob.id}/retry`)) {
          return Promise.resolve(
            response({
              ...failedJob,
              id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
              status: "queued",
              attempt: 2,
            })
          )
        }
        if (url.includes(`/operations/jobs/${queuedJob.id}/cancel`)) {
          return Promise.resolve(
            response({ ...queuedJob, status: "canceled", version: 2 })
          )
        }
        return Promise.resolve(response({ detail: "Not found" }))
      })
    )
  })

  it("shows persistent failures and allows retry and safe cancellation", async () => {
    const user = userEvent.setup()
    render(<App />)

    expect(await screen.findByText("Vendor RSS")).toBeInTheDocument()
    expect(screen.getByText("Feed request timed out")).toBeInTheDocument()
    expect(screen.getByText("APT29 phishing report")).toBeInTheDocument()
    expect(screen.getByTestId("operations-workspace")).toHaveClass(
      "overflow-hidden"
    )
    expect(screen.getByTestId("operation-list-scroll")).toHaveClass(
      "overflow-auto"
    )
    await user.click(screen.getByRole("button", { name: "重试" }))
    await user.click(screen.getByRole("button", { name: "取消" }))

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        `/api/v1/operations/jobs/${failedJob.id}/retry`,
        expect.objectContaining({ method: "POST" })
      )
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/operations/jobs/${queuedJob.id}/cancel`),
        expect.objectContaining({ method: "POST" })
      )
    })
  })
})
