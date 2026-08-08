import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import App from "@/App"

const campaign = {
  id: "11111111-1111-4111-8111-111111111111",
  name: "Operation Dream Job",
  description: "Lazarus recruitment-themed activity.",
  first_seen: "2026-08-01T08:00:00Z",
  last_seen: "2026-08-02T08:00:00Z",
  status: "active",
  event_count: 1,
  actor_names: ["Lazarus Group"],
  stages: ["initial-access"],
  version: 2,
  created_at: "2026-08-08T08:00:00Z",
  updated_at: "2026-08-08T08:00:00Z",
}

const linkedEvent = {
  id: "22222222-2222-4222-8222-222222222222",
  title: "Lazarus fake interview campaign",
  summary: "Developers received malicious coding exercises.",
  status: "confirmed",
  confidence_auto: 90,
  confidence_analyst: 95,
  first_seen: "2026-08-01T08:00:00Z",
  last_seen: "2026-08-01T08:00:00Z",
  report_count: 1,
  actor_names: ["Lazarus Group"],
  observable_count: 1,
  technique_ids: ["T1566.002"],
  superseded_by_id: null,
  created_at: "2026-08-08T08:00:00Z",
  updated_at: "2026-08-08T08:00:00Z",
}

const availableEvent = {
  ...linkedEvent,
  id: "33333333-3333-4333-8333-333333333333",
  title: "Lazarus recruiter follow-up activity",
  first_seen: "2026-08-02T08:00:00Z",
}

function jsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    headers: { "Content-Type": "application/json" },
  })
}

describe("Campaign timeline", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/campaigns")
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        if (url === "/api/v1/campaigns?limit=200") {
          return Promise.resolve(jsonResponse([campaign]))
        }
        if (url === "/api/v1/events?limit=200") {
          return Promise.resolve(jsonResponse([linkedEvent, availableEvent]))
        }
        if (url === `/api/v1/campaigns/${campaign.id}`) {
          return Promise.resolve(
            jsonResponse({
              ...campaign,
              events: [
                {
                  event_id: linkedEvent.id,
                  event_title: linkedEvent.title,
                  event_summary: linkedEvent.summary,
                  event_first_seen: linkedEvent.first_seen,
                  event_last_seen: linkedEvent.last_seen,
                  stage: "initial-access",
                  confidence: 94,
                  evidence_note:
                    "The report explicitly uses the operation name.",
                  reviewed_at: "2026-08-08T08:00:00Z",
                  reviewed_by: "local-analyst",
                  actor_names: ["Lazarus Group"],
                },
              ],
            })
          )
        }
        if (
          url === `/api/v1/campaigns/${campaign.id}/events` &&
          init?.method === "POST"
        ) {
          return Promise.resolve(
            jsonResponse({ ...campaign, version: 3, events: [] })
          )
        }
        return Promise.resolve(jsonResponse([]))
      })
    )
  })

  it("shows analyst evidence and assigns another confirmed event to a stage", async () => {
    render(<App />)

    expect(await screen.findByText("Operation Dream Job")).toBeInTheDocument()
    expect(screen.getByText("初始访问")).toBeInTheDocument()
    expect(
      await screen.findByText("The report explicitly uses the operation name.")
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "加入事件" }))
    expect(
      await screen.findByRole("heading", { name: "确认 Campaign 事件归属" })
    ).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText("攻击阶段"), {
      target: { value: "execution" },
    })
    fireEvent.change(screen.getByLabelText("归属置信度"), {
      target: { value: "88" },
    })
    fireEvent.change(screen.getByLabelText("归属依据"), {
      target: { value: "Shared infrastructure and explicit operation naming." },
    })
    fireEvent.click(screen.getByRole("button", { name: "确认加入时间线" }))

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        `/api/v1/campaigns/${campaign.id}/events`,
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            event_id: availableEvent.id,
            stage: "execution",
            confidence: 88,
            evidence_note:
              "Shared infrastructure and explicit operation naming.",
            expected_version: campaign.version,
          }),
        })
      )
    )
  })
})
