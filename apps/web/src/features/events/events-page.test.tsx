import { render, screen } from "@testing-library/react"
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
  created_at: "2026-08-08T05:00:00Z",
  updated_at: "2026-08-08T05:00:00Z",
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
      vi.fn((input: RequestInfo | URL) => {
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
    expect(screen.getByText(report.title)).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "原文" })).toHaveAttribute(
      "href",
      report.canonical_url
    )
  })
})
