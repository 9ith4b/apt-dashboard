import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import App from "@/App"

const observable = {
  id: "11111111-1111-4111-8111-111111111111",
  type: "domain",
  value_original: "interview-example.com",
  value_normalized: "interview-example.com",
  scope: "public",
  validation_status: "valid",
  first_seen: "2026-08-01T08:00:00Z",
  last_seen: "2026-08-02T08:00:00Z",
  report_count: 1,
  event_count: 1,
  evidence_count: 1,
  indicator: null,
}

const evidenceId = "22222222-2222-4222-8222-222222222222"

function jsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    headers: { "Content-Type": "application/json" },
  })
}

describe("IOC hunting", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/hunt")
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        if (url === "/api/v1/observables?limit=200") {
          return Promise.resolve(jsonResponse([observable]))
        }
        if (url === "/api/v1/indicators?limit=200") {
          return Promise.resolve(jsonResponse([]))
        }
        if (url === `/api/v1/observables/${observable.id}`) {
          return Promise.resolve(
            jsonResponse({
              ...observable,
              reports: [
                {
                  report_id: "33333333-3333-4333-8333-333333333333",
                  report_title: "Lazarus fake interview campaign",
                  source_name: "Vendor Research",
                  published_at: observable.first_seen,
                  confidence: 98,
                  evidence_id: evidenceId,
                  evidence:
                    "Lazarus used interview-example.com to deliver malware.",
                },
              ],
              events: [
                {
                  event_id: "44444444-4444-4444-8444-444444444444",
                  event_title: "Lazarus fake interview campaign",
                  first_seen: observable.first_seen,
                  confidence: 98,
                  evidence_id: evidenceId,
                  evidence:
                    "Lazarus used interview-example.com to deliver malware.",
                },
              ],
              enrichments: [],
            })
          )
        }
        if (
          url === `/api/v1/observables/${observable.id}/promote` &&
          init?.method === "POST"
        ) {
          return Promise.resolve(
            jsonResponse({
              id: "55555555-5555-4555-8555-555555555555",
              observable_id: observable.id,
              observable_type: observable.type,
              value_normalized: observable.value_normalized,
              purpose: "Credential phishing infrastructure",
              pattern: "[domain-name:value = 'interview-example.com']",
              valid_from: "2026-08-08T00:00:00Z",
              valid_until: "2026-09-07T23:59:59Z",
              confidence: 90,
              severity: "high",
              revoked: false,
              reviewed_at: "2026-08-08T08:00:00Z",
              reviewed_by: "local-analyst",
              evidence_ids: [evidenceId],
              version: 1,
            })
          )
        }
        return Promise.resolve(jsonResponse([]))
      })
    )
  })

  it("separates an Observable from a human-confirmed Indicator promotion", async () => {
    render(<App />)

    expect(
      await screen.findAllByText("interview-example.com")
    ).not.toHaveLength(0)
    expect(screen.getByText("仅 Observable")).toBeInTheDocument()
    expect(
      await screen.findAllByText("Lazarus fake interview campaign")
    ).toHaveLength(2)
    fireEvent.click(screen.getByRole("button", { name: "提升为 Indicator" }))
    expect(
      await screen.findByRole("heading", { name: "提升为恶意 Indicator" })
    ).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText("恶意用途"), {
      target: { value: "Credential phishing infrastructure" },
    })
    fireEvent.change(screen.getByLabelText("人工置信度"), {
      target: { value: "90" },
    })
    fireEvent.change(screen.getByLabelText("严重度"), {
      target: { value: "high" },
    })
    fireEvent.click(screen.getByRole("button", { name: "确认提升" }))

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        `/api/v1/observables/${observable.id}/promote`,
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining("Credential phishing infrastructure"),
        })
      )
    )
    const promotionCall = vi
      .mocked(fetch)
      .mock.calls.find(([url]) => String(url).endsWith("/promote"))
    expect(promotionCall).toBeDefined()
    expect(JSON.parse(String(promotionCall?.[1]?.body))).toEqual(
      expect.objectContaining({
        confidence: 90,
        severity: "high",
        evidence_ids: [evidenceId],
      })
    )
  })
})
