import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import App from "@/App"

const source = {
  id: "11111111-1111-4111-8111-111111111111",
  type: "rss",
  name: "Microsoft Security Blog",
  url: "https://www.microsoft.com/en-us/security/blog/feed/",
  enabled: true,
  health_status: "healthy",
  poll_interval_minutes: 60,
  last_checked_at: "2026-08-08T04:00:00Z",
  last_success_at: "2026-08-08T04:00:00Z",
  next_poll_at: "2026-08-08T05:00:00Z",
  last_error: null,
  consecutive_failures: 0,
  report_count: 12,
  created_at: "2026-08-08T03:00:00Z",
  updated_at: "2026-08-08T04:00:00Z",
}

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  })
}

describe("RSS source management", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/sources")
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const method = init?.method ?? "GET"
        if (String(input) === "/api/v1/sources" && method === "GET") {
          return Promise.resolve(jsonResponse([source]))
        }
        if (String(input) === "/api/v1/sources" && method === "POST") {
          return Promise.resolve(
            jsonResponse(
              {
                ...source,
                id: "22222222-2222-4222-8222-222222222222",
                name: "CISA",
              },
              201
            )
          )
        }
        return Promise.resolve(jsonResponse({ detail: "Not found" }, 404))
      })
    )
  })

  it("renders live source status and report counts", async () => {
    render(<App />)

    expect(
      (await screen.findAllByText("Microsoft Security Blog")).length
    ).toBeGreaterThan(0)
    expect(screen.getAllByText("12").length).toBeGreaterThan(0)
    expect(screen.getAllByText("正常").length).toBeGreaterThan(0)
  })

  it("validates and creates an RSS source", async () => {
    const user = userEvent.setup()
    render(<App />)
    await screen.findAllByText("Microsoft Security Blog")

    await user.click(screen.getByRole("button", { name: "添加数据源" }))
    await user.click(screen.getByRole("button", { name: "保存数据源" }))
    expect(screen.getByText("名称至少需要 2 个字符。")).toBeInTheDocument()
    expect(
      screen.getByText("请输入完整的 RSS 或 Atom 地址。")
    ).toBeInTheDocument()

    await user.type(screen.getByLabelText("名称"), "CISA")
    await user.type(
      screen.getByLabelText("Feed URL"),
      "https://www.cisa.gov/cybersecurity-advisories/all.xml"
    )
    await user.click(screen.getByRole("button", { name: "保存数据源" }))

    expect((await screen.findAllByText("CISA")).length).toBeGreaterThan(0)
  })
})
