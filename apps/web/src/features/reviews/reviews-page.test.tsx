import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import App from "@/App"

const report = {
  id: "33333333-3333-4333-8333-333333333333",
  source_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  source_name: "Microsoft Security Blog",
  title: "Lazarus uses fake interviews to target developers",
  canonical_url: "https://example.com/lazarus",
  language: "en",
  summary: "A fake interview campaign.",
  relevance_score: 94,
  relevance_reasons: ["命中攻击组织：lazarus"],
  status: "candidate",
  published_at: "2026-08-08T04:00:00Z",
  created_at: "2026-08-08T04:00:00Z",
  extraction_status: "ready",
  review_status: "pending",
  confidence_auto: 96,
}

const analysis = {
  extraction_status: "ready",
  review_status: "pending",
  content_text:
    "Lazarus Group used fake interviews and malicious coding tasks to target software developers.",
  final_url: report.canonical_url,
  content_type: "text/html",
  fetched_at: "2026-08-08T05:00:00Z",
  extraction_error: null,
  actors: [
    {
      name: "Lazarus Group",
      type: "threat-actor",
      confidence: 90,
      evidence: "Lazarus Group used fake interviews.",
    },
  ],
  capabilities: [
    {
      name: "Social engineering",
      type: "capability",
      confidence: 78,
      evidence: "The attackers used fake interviews.",
    },
  ],
  infrastructure: [],
  victims: [
    {
      name: "Technology companies",
      type: "victim-sector",
      confidence: 76,
      evidence: "The campaign targeted software developers.",
    },
  ],
  evidence: [],
  confidence_auto: 96,
  method_version: "rules-v1",
  analyst_note: null,
  reviewed_at: null,
  reviewed_by: null,
  version: 1,
  updated_at: "2026-08-08T05:00:00Z",
}

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  })
}

describe("analyst review workbench", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/reviews")
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        if (url === "/api/v1/reviews?review_status=pending&limit=200") {
          return Promise.resolve(jsonResponse([report]))
        }
        if (url === `/api/v1/reports/${report.id}`) {
          return Promise.resolve(jsonResponse({ ...report, analysis }))
        }
        if (
          url === `/api/v1/reviews/${report.id}/decision` &&
          init?.method === "POST"
        ) {
          return Promise.resolve(
            jsonResponse({
              ...report,
              status: "approved",
              review_status: "approved",
              analysis: { ...analysis, review_status: "approved", version: 2 },
            })
          )
        }
        return Promise.resolve(jsonResponse({ detail: "Not found" }, 404))
      })
    )
  })

  it("shows all diamond dimensions and preserves unknown infrastructure", async () => {
    render(<App />)

    expect(await screen.findByText(report.title)).toBeInTheDocument()
    expect(await screen.findByText("Lazarus Group")).toBeInTheDocument()
    expect(screen.getByText("Social engineering")).toBeInTheDocument()
    expect(screen.getByText("Technology companies")).toBeInTheDocument()
    expect(
      screen.getByText("未从正文中提取到，可由分析员手动补充。")
    ).toBeInTheDocument()
  })

  it("submits the analyst note with an approval decision", async () => {
    const user = userEvent.setup()
    render(<App />)
    await screen.findByText("Lazarus Group")

    await user.type(screen.getByLabelText("分析员备注"), "证据链完整。")
    await user.click(screen.getByRole("button", { name: "通过审核" }))

    expect(await screen.findByText("材料已通过审核")).toBeInTheDocument()
    const fetchMock = vi.mocked(fetch)
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/v1/reviews/${report.id}/decision`,
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining("证据链完整"),
      })
    )
  })
})
