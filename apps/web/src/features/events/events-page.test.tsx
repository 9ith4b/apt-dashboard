import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import App from "@/App"

const event = {
  id: "44444444-4444-4444-8444-444444444444",
  title: "Lazarus fake interview campaign",
  summary: "A confirmed campaign used fake interviews to target developers.",
  status: "confirmed",
  confidence_auto: 91,
  confidence_analyst: 95,
  first_seen: "2026-08-08T04:00:00Z",
  last_seen: "2026-08-08T04:00:00Z",
  report_count: 1,
  actor_names: ["Lazarus Group"],
  observable_count: 1,
  technique_ids: ["T1566.002"],
  superseded_by_id: null,
  created_at: "2026-08-08T05:00:00Z",
  updated_at: "2026-08-08T05:00:00Z",
}

const mergeCandidate = {
  id: "55555555-5555-4555-8555-555555555555",
  source_event: {
    id: "66666666-6666-4666-8666-666666666666",
    title: "Lazarus developer recruitment activity",
    first_seen: "2026-08-07T04:00:00Z",
    report_count: 1,
  },
  target_event: {
    id: event.id,
    title: event.title,
    first_seen: event.first_seen,
    report_count: 1,
  },
  score: 72,
  features: {
    actor_overlap: 1,
    observable_overlap: 1,
    technique_overlap: 1,
    date_distance_days: 1,
  },
  status: "pending",
  decision_reason: null,
  moved_report_ids: [],
  reviewed_at: null,
  version: 1,
  created_at: "2026-08-08T05:00:00Z",
}

const report = {
  id: "33333333-3333-4333-8333-333333333333",
  source_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  source_name: "Security Research",
  title: "Lazarus uses fake interviews to target developers",
  canonical_url: "https://example.com/lazarus",
  language: "en",
  summary: "A fake interview campaign.",
  relevance_score: 94,
  relevance_reasons: ["actor"],
  status: "approved",
  published_at: "2026-08-08T04:00:00Z",
  created_at: "2026-08-08T04:00:00Z",
  extraction_status: "ready",
  review_status: "approved",
  confidence_auto: 91,
}

function jsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    headers: { "Content-Type": "application/json" },
  })
}

describe("threat events", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/events")
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        if (url === "/api/v1/events?limit=200") {
          return Promise.resolve(jsonResponse([event]))
        }
        if (url === `/api/v1/events/${event.id}`) {
          return Promise.resolve(
            jsonResponse({
              ...event,
              diamond: {
                actors: [
                  {
                    name: "Lazarus Group",
                    type: "threat-actor",
                    confidence: 95,
                    evidence: "The report attributes the activity to Lazarus.",
                  },
                ],
                capabilities: [
                  {
                    name: "Fake interview",
                    type: "social-engineering",
                    confidence: 90,
                    evidence: "Targets received fake interview tasks.",
                  },
                ],
                infrastructure: [],
                victims: [],
              },
              reports: [report],
              observables: [
                {
                  id: "77777777-7777-4777-8777-777777777777",
                  type: "domain",
                  value_original: "interview.example.com",
                  value_normalized: "interview.example.com",
                  scope: "public",
                  confidence: 92,
                  evidence_id: "88888888-8888-4888-8888-888888888888",
                  evidence: "The payload was hosted at interview.example.com.",
                  first_seen: event.first_seen,
                  last_seen: event.last_seen,
                },
              ],
              attack_techniques: [
                {
                  technique_id: "T1566.002",
                  name: "Spearphishing Link",
                  tactic: "initial-access",
                  confidence: 90,
                  evidence_id: "99999999-9999-4999-8999-999999999999",
                  evidence: "The report explicitly references T1566.002.",
                },
              ],
            })
          )
        }
        if (
          url ===
          "/api/v1/events/merge-candidates?candidate_status=pending&limit=100"
        ) {
          return Promise.resolve(jsonResponse([mergeCandidate]))
        }
        if (
          url ===
          "/api/v1/events/merge-candidates?candidate_status=approved&limit=100"
        ) {
          return Promise.resolve(jsonResponse([]))
        }
        if (
          url ===
            `/api/v1/events/merge-candidates/${mergeCandidate.id}/decision` &&
          init?.method === "POST"
        ) {
          return Promise.resolve(
            jsonResponse({
              ...mergeCandidate,
              status: "approved",
              decision_reason: "同一基础设施与技术",
              moved_report_ids: [report.id],
              version: 2,
            })
          )
        }
        return Promise.resolve(jsonResponse({ detail: "Not found" }))
      })
    )
  })

  it("renders confirmed event fields and linked evidence", async () => {
    render(<App />)

    expect(await screen.findByText(event.title)).toBeInTheDocument()
    expect(await screen.findByText("Lazarus Group")).toBeInTheDocument()
    expect(screen.getByText("Fake interview")).toBeInTheDocument()
    expect(screen.getByText("interview.example.com")).toBeInTheDocument()
    expect(screen.getAllByText("T1566.002").length).toBeGreaterThan(0)
    expect(screen.getByText("Spearphishing Link")).toBeInTheDocument()
    expect(screen.getByText(report.title)).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "原文" })).toHaveAttribute(
      "href",
      report.canonical_url
    )
    expect(screen.getByTestId("events-workspace")).toHaveClass(
      "overflow-hidden"
    )
    expect(screen.getByTestId("event-list-scroll")).toHaveClass(
      "overflow-y-auto"
    )
    expect(screen.getByTestId("event-detail-scroll")).toHaveClass(
      "overflow-y-auto",
      "overflow-x-hidden",
      "[&>*]:shrink-0"
    )

    fireEvent.click(await screen.findByRole("button", { name: "查看合并建议" }))
    expect(
      await screen.findByRole("heading", { name: "审核事件合并" })
    ).toBeInTheDocument()
    expect(screen.getByText("共同攻击者")).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText("审核说明（可选）"), {
      target: { value: "同一基础设施与技术" },
    })
    fireEvent.click(screen.getByRole("button", { name: "确认合并" }))

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        `/api/v1/events/merge-candidates/${mergeCandidate.id}/decision`,
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            decision: "approved",
            reason: "同一基础设施与技术",
            expected_version: 1,
          }),
        })
      )
    )
  })
})
