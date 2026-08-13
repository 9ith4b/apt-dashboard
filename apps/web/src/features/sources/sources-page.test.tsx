import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import App from "@/App"

const source = {
  id: "11111111-1111-4111-8111-111111111111",
  type: "rss",
  name: "Microsoft Security Blog",
  url: "https://www.microsoft.com/en-us/security/blog/feed/",
  config: {},
  credential_configured: false,
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

describe("source connector management", () => {
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
          const payload = JSON.parse(String(init?.body))
          return Promise.resolve(
            jsonResponse(
              {
                ...source,
                id:
                  payload.type === "x"
                    ? "33333333-3333-4333-8333-333333333333"
                    : "22222222-2222-4222-8222-222222222222",
                name: payload.name,
                type: payload.type,
                url: payload.url,
                config: payload.config,
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
    expect(screen.getByTestId("sources-workspace")).toHaveClass(
      "overflow-hidden"
    )
    expect(screen.getByTestId("source-list-scroll")).toHaveClass(
      "overflow-auto"
    )
    expect(screen.getByTestId("source-detail-scroll")).toHaveClass(
      "overflow-y-auto",
      "[&>*]:shrink-0"
    )
    expect(screen.getByRole("button", { name: "立即采集" })).toBeInTheDocument()
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

  it("creates an X connector without sending credential values", async () => {
    const user = userEvent.setup()
    render(<App />)
    await screen.findAllByText("Microsoft Security Blog")

    await user.click(screen.getByRole("button", { name: "添加数据源" }))
    await user.selectOptions(screen.getByLabelText("连接器类型"), "x")
    await user.type(screen.getByLabelText("名称"), "APT28 on X")
    await user.type(
      screen.getByLabelText("X API 查询语句"),
      '(APT28 OR "Fancy Bear") -is:retweet'
    )
    await user.click(screen.getByRole("button", { name: "保存数据源" }))

    const postCall = vi
      .mocked(fetch)
      .mock.calls.find(([, init]) => init?.method === "POST")
    expect(postCall).toBeDefined()
    const payload = JSON.parse(String(postCall?.[1]?.body))
    expect(payload).toMatchObject({
      type: "x",
      url: null,
      secret_ref: "APT_HUNTER_X_BEARER_TOKEN",
      config: {
        query: '(APT28 OR "Fancy Bear") -is:retweet',
        max_results: 50,
      },
    })
    expect(JSON.stringify(payload)).not.toContain("Bearer")
  })
})
