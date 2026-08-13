import { render, screen, within } from "@testing-library/react"
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
        if (url === "/api/v1/notifications?limit=50") {
          return Promise.resolve(jsonResponse({ unread_count: 0, items: [] }))
        }
        if (url === "/api/v1/search?q=APT29&limit=20") {
          return Promise.resolve(
            jsonResponse({
              query: "APT29",
              total: 1,
              results: [
                {
                  kind: "actor",
                  id: "33333333-3333-4333-8333-333333333333",
                  title: "Midnight Blizzard",
                  subtitle: "Alias: APT29",
                  url: "/actors?actor=33333333-3333-4333-8333-333333333333",
                  score: 80,
                },
              ],
            })
          )
        }
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
    const user = userEvent.setup()
    render(<App />)

    expect(screen.getByRole("heading", { name: "情报流" })).toBeInTheDocument()
    expect(
      (await screen.findAllByText(reports[0].title)).length
    ).toBeGreaterThan(0)

    const reportButton = screen.getByRole("button", {
      name: new RegExp(reports[0].title),
    })
    expect(reportButton).toHaveAttribute("aria-expanded", "false")
    await user.click(reportButton)

    const inspector = await screen.findByRole("dialog", { name: "材料速览" })
    expect(
      within(inspector).getAllByText("Midnight Blizzard / APT29").length
    ).toBeGreaterThan(0)
    expect(within(inspector).getByText("可追溯证据")).toBeInTheDocument()
    expect(
      within(inspector).getByRole("region", { name: "材料速览内容" })
    ).toHaveClass("overflow-y-auto")
    expect(
      within(inspector).getByRole("link", { name: "进入人工复核" })
    ).toBeInTheDocument()
    expect(
      within(inspector).getByRole("link", { name: "打开原文" })
    ).toBeInTheDocument()
    expect(reportButton).toHaveAttribute("aria-expanded", "true")
  })

  it("keeps the feed in an independent scroll region", async () => {
    render(<App />)
    await screen.findAllByText(reports[0].title)

    expect(screen.getByTestId("intelligence-feed-workspace")).toHaveClass(
      "overflow-hidden"
    )
    expect(screen.getByRole("region", { name: "情报列表" })).toHaveClass(
      "flex-1",
      "overflow-y-auto"
    )
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

  it("searches across the intelligence knowledge base", async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.type(screen.getByRole("textbox", { name: "全局搜索" }), "APT29")

    expect(
      await screen.findByRole("link", { name: /Midnight Blizzard/ })
    ).toHaveAttribute("href", expect.stringContaining("/actors?actor="))
  })

  it("collapses and expands the desktop sidebar", async () => {
    const user = userEvent.setup()
    render(<App />)

    const sidebar = document.querySelector('[data-slot="sidebar"][data-state]')
    expect(sidebar).toHaveAttribute("data-state", "expanded")

    const collapseButton = screen.getByRole("button", {
      name: "收起侧边栏",
    })
    expect(collapseButton).toHaveAttribute("aria-expanded", "true")
    await user.click(collapseButton)

    expect(sidebar).toHaveAttribute("data-state", "collapsed")
    const expandButton = screen.getByRole("button", {
      name: "展开侧边栏",
    })
    expect(expandButton).toHaveAttribute("aria-expanded", "false")
    await user.click(expandButton)

    expect(sidebar).toHaveAttribute("data-state", "expanded")
    expect(
      screen.getByRole("button", { name: "收起侧边栏" })
    ).toBeInTheDocument()
  })
})
