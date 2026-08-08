import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import App from "./App"

const reports = [
  {
    id: "11111111-1111-4111-8111-111111111111",
    source_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    source_name: "Microsoft Security Blog",
    title: "Midnight Blizzard targets travelers with phishing",
    canonical_url: "https://example.com/one",
    language: "en",
    summary: "A targeted campaign against travelers.",
    relevance_score: 95,
    relevance_reasons: [
      "命中攻击组织：midnight blizzard",
      "命中攻击语义：phishing",
    ],
    status: "candidate",
    published_at: "2026-08-08T04:00:00Z",
    created_at: "2026-08-08T04:00:00Z",
    extraction_status: "ready",
    review_status: "pending",
    confidence_auto: 82,
  },
  {
    id: "22222222-2222-4222-8222-222222222222",
    source_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    source_name: "Security Research",
    title: "APT28 launches a credential theft campaign",
    canonical_url: "https://example.com/two",
    language: "en",
    summary: "Government agencies received malicious messages.",
    relevance_score: 85,
    relevance_reasons: ["命中攻击组织：APT28"],
    status: "candidate",
    published_at: "2026-08-08T03:00:00Z",
    created_at: "2026-08-08T03:00:00Z",
    extraction_status: "queued",
    review_status: "pending",
    confidence_auto: null,
  },
]

const analysis = {
  extraction_status: "ready",
  review_status: "pending",
  content_text:
    "Midnight Blizzard sent credential phishing emails to travelers.",
  final_url: "https://example.com/one",
  content_type: "text/html",
  fetched_at: "2026-08-08T05:00:00Z",
  extraction_error: null,
  actors: [
    {
      name: "Midnight Blizzard / APT29",
      type: "threat-actor",
      confidence: 90,
      evidence: "Midnight Blizzard sent credential phishing emails.",
    },
  ],
  capabilities: [],
  infrastructure: [],
  victims: [],
  evidence: [
    {
      dimension: "adversary",
      entity: "Midnight Blizzard / APT29",
      quote: "Midnight Blizzard sent credential phishing emails.",
    },
  ],
  confidence_auto: 82,
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

describe("APT Hunter intelligence feed", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/feed")
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input)
        if (url === "/api/v1/reports?limit=200") {
          return Promise.resolve(jsonResponse(reports))
        }
        if (url.endsWith(reports[0].id)) {
          return Promise.resolve(jsonResponse({ ...reports[0], analysis }))
        }
        if (url.endsWith(reports[1].id)) {
          return Promise.resolve(
            jsonResponse({ ...reports[1], analysis: null })
          )
        }
        return Promise.resolve(jsonResponse({ detail: "Not found" }, 404))
      })
    )
  })

  it("renders live reports and extracted evidence", async () => {
    render(<App />)

    expect(screen.getByRole("heading", { name: "情报流" })).toBeInTheDocument()
    expect(
      (await screen.findAllByText(reports[0].title)).length
    ).toBeGreaterThan(0)
    expect(
      (await screen.findAllByText("Midnight Blizzard / APT29")).length
    ).toBeGreaterThan(0)
    expect(screen.getByText("可追溯证据")).toBeInTheDocument()
  })

  it("loads the selected report detail", async () => {
    const user = userEvent.setup()
    render(<App />)
    await screen.findAllByText(reports[0].title)

    await user.click(
      screen.getByRole("button", { name: new RegExp(reports[1].title) })
    )

    expect(await screen.findByText(reports[1].summary)).toBeInTheDocument()
    expect(screen.getAllByText("排队中").length).toBeGreaterThan(0)
  })
})
