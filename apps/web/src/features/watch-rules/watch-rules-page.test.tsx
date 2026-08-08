import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import App from "@/App"

const rule = {
  id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  name: "Lazarus fake interview",
  description: "Track confirmed fake interview activity.",
  conditions: {
    keywords: ["fake interview"],
    actor_names: ["Lazarus"],
    observable_types: ["domain"],
    technique_ids: ["T1566.002"],
    min_confidence: 80,
  },
  severity: "high",
  enabled: true,
  created_by: "analyst",
  version: 1,
  hit_count: 1,
  created_at: "2026-08-08T08:00:00Z",
  updated_at: "2026-08-08T08:00:00Z",
}

function response(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    headers: { "Content-Type": "application/json" },
  })
}

describe("watch rules", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/watch-rules")
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        if (url === "/api/v1/notifications?limit=50") {
          return Promise.resolve(response({ unread_count: 0, items: [] }))
        }
        if (url === "/api/v1/watch-rules")
          return Promise.resolve(response([rule]))
        if (url.endsWith(`/watch-rules/${rule.id}/hits?limit=100`)) {
          return Promise.resolve(
            response([
              {
                id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                rule_id: rule.id,
                subject_type: "event",
                subject_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                subject_title:
                  "Lazarus targets developers with fake interviews",
                matched_on: {
                  keywords: ["fake interview"],
                  actor_names: ["Lazarus"],
                },
                created_at: "2026-08-08T09:00:00Z",
              },
            ])
          )
        }
        if (url.endsWith(`/watch-rules/${rule.id}/preview`)) {
          return Promise.resolve(
            response({ rule_id: rule.id, match_count: 1, matches: [] })
          )
        }
        if (url.endsWith(`/watch-rules/${rule.id}/evaluate`)) {
          return Promise.resolve(
            response({
              rule_id: rule.id,
              evaluated_count: 4,
              created_hit_count: 0,
              hit_count: 1,
            })
          )
        }
        if (
          url.endsWith(`/watch-rules/${rule.id}`) &&
          init?.method === "PATCH"
        ) {
          return Promise.resolve(
            response({ ...rule, enabled: false, version: 2 })
          )
        }
        return Promise.resolve(response({ detail: "Not found" }))
      })
    )
  })

  it("previews, evaluates, and toggles a structured rule", async () => {
    const user = userEvent.setup()
    render(<App />)

    expect((await screen.findAllByText(rule.name)).length).toBeGreaterThan(0)
    expect(screen.getByText("关键词 · fake interview")).toBeInTheDocument()
    expect(
      await screen.findByText("Lazarus targets developers with fake interviews")
    ).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "预览现有匹配" }))
    expect(await screen.findByText("预览 1 起")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "运行并记录命中" }))
    await user.click(screen.getByRole("switch", { name: "启用规则" }))

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        `/api/v1/watch-rules/${rule.id}`,
        expect.objectContaining({ method: "PATCH" })
      )
    })

    await user.click(screen.getByRole("button", { name: "新建规则" }))
    expect(screen.getByRole("dialog")).toBeInTheDocument()
    expect(screen.getByLabelText("攻击组织")).toBeInTheDocument()
  })
})
