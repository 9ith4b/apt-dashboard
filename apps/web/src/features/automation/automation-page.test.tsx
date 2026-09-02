import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import App from "@/App"

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  })
}

const policy = {
  automation_enabled: false,
  unattended_mode: true,
  require_verification: true,
  auto_create_events: true,
  auto_manage_indicators: true,
  indicator_auto_threshold: 80,
  relevance_threshold: 60,
  auto_approve_threshold: 85,
  auto_reject_threshold: 20,
  minimum_evidence_coverage: 70,
  max_article_chars: 60000,
  updated_by: "system",
  updated_at: "2026-08-09T00:00:00Z",
}

describe("AI automation settings", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/automation")
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        if (url === "/api/v1/ai/configs" && init?.method === "POST") {
          const payload = JSON.parse(String(init.body))
          return Promise.resolve(
            jsonResponse(
              {
                ...payload,
                id: "11111111-1111-4111-8111-111111111111",
                has_api_key: true,
                api_key: undefined,
                updated_by: "admin",
                last_test_status: null,
                last_test_error: null,
                last_tested_at: null,
                created_at: "2026-08-09T00:00:00Z",
                updated_at: "2026-08-09T00:00:00Z",
              },
              201
            )
          )
        }
        if (url === "/api/v1/ai/configs")
          return Promise.resolve(jsonResponse([]))
        if (url === "/api/v1/ai/policy")
          return Promise.resolve(jsonResponse(policy))
        if (url === "/api/v1/ai/status") {
          return Promise.resolve(
            jsonResponse({
              automation_enabled: false,
              active_model_name: null,
              active_model: null,
              open_exceptions: 0,
              processed_24h: 0,
              auto_approved_24h: 0,
              needs_review_24h: 0,
              failed_24h: 0,
            })
          )
        }
        return Promise.resolve(jsonResponse({ detail: "Not found" }, 404))
      })
    )
  })

  it("stores a configurable model without rendering the secret back", async () => {
    const user = userEvent.setup()
    render(<App />)

    expect(await screen.findByText("还没有模型配置")).toBeInTheDocument()
    await user.type(screen.getByLabelText("配置名称"), "主分析模型")
    await user.type(screen.getByLabelText("模型名称"), "gpt-5-mini")
    await user.type(screen.getByLabelText(/API Key/), "sk-sensitive-value")
    await user.click(screen.getByRole("button", { name: "保存配置" }))

    const postCall = vi
      .mocked(fetch)
      .mock.calls.find(([, init]) => init?.method === "POST")
    expect(JSON.parse(String(postCall?.[1]?.body))).toMatchObject({
      name: "主分析模型",
      provider: "openai",
      model: "gpt-5-mini",
      api_key: "sk-sensitive-value",
    })
    expect(
      screen.queryByDisplayValue("sk-sensitive-value")
    ).not.toBeInTheDocument()
  })

  it("makes unattended operation and AI Indicator management explicit", async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(await screen.findByRole("tab", { name: "自动化策略" }))
    expect(screen.getByText("无人值守运营")).toBeInTheDocument()
    expect(screen.getByText("AI自动维护 Indicator")).toBeInTheDocument()
    expect(
      screen.getByText(
        "满足APT范围、置信度、证据与验证门禁后自动发布；非APT自动排除，边界材料等待自动重试。"
      )
    ).toBeInTheDocument()
  })
})
