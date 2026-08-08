import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import App from "@/App"

const admin = {
  id: "11111111-1111-4111-8111-111111111111",
  username: "admin",
  display_name: "Security Admin",
  role: "admin",
  enabled: true,
  last_login_at: "2026-08-08T12:00:00Z",
  created_at: "2026-08-08T10:00:00Z",
}

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  })
}

describe("identity and audit administration", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/security")
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        if (String(input) === "/api/v1/auth/users" && !init?.method) {
          return Promise.resolve(jsonResponse([admin]))
        }
        if (String(input) === "/api/v1/audit-logs?limit=100") {
          return Promise.resolve(
            jsonResponse([
              {
                id: "22222222-2222-4222-8222-222222222222",
                actor_user_id: admin.id,
                actor_username: "admin",
                action: "POST sources",
                object_type: "sources",
                object_id: null,
                result: "succeeded",
                request_id: "request-1",
                ip_address: "127.0.0.1",
                details: { status_code: 201 },
                created_at: "2026-08-08T12:01:00Z",
              },
            ])
          )
        }
        if (String(input) === "/api/v1/auth/users" && init?.method === "POST") {
          const payload = JSON.parse(String(init.body))
          return Promise.resolve(
            jsonResponse(
              {
                ...admin,
                id: "33333333-3333-4333-8333-333333333333",
                username: payload.username,
                display_name: payload.display_name,
                role: payload.role,
                last_login_at: null,
              },
              201
            )
          )
        }
        return Promise.resolve(jsonResponse({ detail: "Not found" }, 404))
      })
    )
  })

  it("shows accounts and audit records and creates a role-scoped user", async () => {
    const user = userEvent.setup()
    render(<App />)

    expect(await screen.findByText("Security Admin")).toBeInTheDocument()
    expect(screen.getByText("POST sources")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "创建账户" }))
    await user.click(screen.getByRole("button", { name: "创建账户" }))
    expect(screen.getByText("用户名至少需要 2 个字符。")).toBeInTheDocument()
    await user.type(screen.getByLabelText("用户名"), "hunter")
    await user.type(screen.getByLabelText("显示名称"), "Threat Hunter")
    await user.type(
      screen.getByLabelText("初始密码"),
      "a long initial password"
    )
    await user.selectOptions(screen.getByLabelText("角色"), "analyst")
    await user.click(screen.getByRole("button", { name: "创建账户" }))

    expect(await screen.findByText("Threat Hunter")).toBeInTheDocument()
    const postCall = vi
      .mocked(fetch)
      .mock.calls.find(([, init]) => init?.method === "POST")
    expect(JSON.parse(String(postCall?.[1]?.body))).toMatchObject({
      username: "hunter",
      role: "analyst",
      enabled: true,
    })
  })
})
