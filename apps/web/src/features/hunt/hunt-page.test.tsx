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
  ai_disposition: "malicious",
  ai_role: "钓鱼投递基础设施",
  ai_confidence: 94,
  ai_decision_reason: "原文明确说明该域名用于投递恶意软件。",
  ai_decided_at: "2026-08-02T08:10:00Z",
  indicator: null,
}

const evidenceId = "22222222-2222-4222-8222-222222222222"

const indicator = {
  id: "55555555-5555-4555-8555-555555555555",
  observable_id: observable.id,
  observable_type: observable.type,
  value_normalized: observable.value_normalized,
  purpose: "Credential phishing infrastructure",
  pattern: "[domain-name:value = 'interview-example.com']",
  valid_from: "2026-08-08T00:00:00Z",
  valid_until: "2026-09-07T23:59:59Z",
  confidence: 94,
  severity: "high",
  revoked: false,
  reviewed_at: "2026-08-08T08:00:00Z",
  reviewed_by: "ai-automation",
  evidence_ids: [evidenceId],
  version: 1,
}

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
          return Promise.resolve(jsonResponse([indicator]))
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

  it("shows the AI verdict and keeps manual promotion as a correction", async () => {
    render(<App />)

    expect(
      await screen.findAllByText("interview-example.com")
    ).not.toHaveLength(0)
    expect(screen.getAllByText("AI判定恶意").length).toBeGreaterThan(0)
    expect(
      await screen.findByText("原文明确说明该域名用于投递恶意软件。")
    ).toBeInTheDocument()
    expect(
      await screen.findAllByText("Lazarus fake interview campaign")
    ).toHaveLength(2)
    expect(screen.getByTestId("hunt-workspace")).toHaveClass("overflow-hidden")
    expect(screen.getByTestId("observable-list-scroll")).toHaveClass(
      "overflow-y-auto"
    )
    expect(screen.getByTestId("observable-detail-scroll")).toHaveClass(
      "overflow-y-auto",
      "overflow-x-hidden",
      "[&>*]:shrink-0"
    )
    fireEvent.click(screen.getByRole("button", { name: "纠正为 Indicator" }))
    expect(
      await screen.findByRole("heading", { name: "人工纠正为恶意 Indicator" })
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
    fireEvent.click(screen.getByRole("button", { name: "保存人工纠正" }))

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

  it("shows Indicators in a scrollable table and opens a detail drawer", async () => {
    render(<App />)

    fireEvent.click(
      await screen.findByRole("button", { name: "Indicator（1）" })
    )

    expect(await screen.findByRole("table")).toBeVisible()
    expect(screen.getByText(indicator.value_normalized)).toBeVisible()
    expect(screen.getByText(indicator.purpose)).toBeVisible()
    expect(screen.getByText("94%")).toBeVisible()
    expect(
      screen.queryByTestId("indicator-list-scroll")
    ).not.toBeInTheDocument()
    expect(screen.getByTestId("indicator-table-scroll")).toHaveClass(
      "overflow-hidden"
    )

    fireEvent.click(
      screen.getByRole("row", {
        name: `查看 Indicator ${indicator.value_normalized}`,
      })
    )

    expect(
      await screen.findByRole("dialog", { name: "Indicator 详情" })
    ).toBeVisible()
    expect(
      screen.getByRole("region", { name: "Indicator 详情内容" })
    ).toHaveClass("overflow-y-auto", "overflow-x-hidden")
    expect(screen.getByText("AI 自动维护")).toBeVisible()
    expect(screen.getByText(indicator.pattern)).toBeVisible()
    expect(screen.getByRole("button", { name: "撤销 Indicator" })).toBeVisible()
  })

  it("keeps the IOC search controls at one consistent height", async () => {
    render(<App />)

    await screen.findByTestId("hunt-search-input")

    expect(screen.getByTestId("hunt-search-input")).toHaveClass("h-10")
    expect(screen.getByTestId("hunt-type-select")).toHaveClass("h-10")
    expect(screen.getByTestId("hunt-search-submit")).toHaveClass("h-10")
  })
})
