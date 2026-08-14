import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import App from "@/App"

const actorId = "55555555-5555-4555-8555-555555555555"
const actor = {
  id: actorId,
  canonical_name: "Midnight Blizzard",
  aliases: ["APT29", "Cozy Bear", "NOBELIUM"],
  origin_country: "Russia",
  event_count: 2,
  first_seen: "2026-01-15T08:00:00Z",
  last_seen: "2026-07-20T08:00:00Z",
  latest_event_id: "77777777-7777-4777-8777-777777777777",
  latest_event_title: "APT29 targets diplomatic organizations",
}

const actorDetail = {
  ...actor,
  description: "A Russia-linked espionage actor tracked under several aliases.",
  timeline: [
    { key: "2026-01", label: "2026 年 1 月", event_count: 1 },
    { key: "2026-07", label: "2026 年 7 月", event_count: 1 },
  ],
  events: [
    {
      id: actor.latest_event_id,
      title: actor.latest_event_title,
      summary:
        "The campaign targeted diplomatic organizations with spearphishing.",
      status: "confirmed",
      confidence: 94,
      first_seen: "2026-07-20T08:00:00Z",
      last_seen: "2026-07-20T08:00:00Z",
      reported_name: "APT29",
    },
    {
      id: "66666666-6666-4666-8666-666666666666",
      title: "Cozy Bear cloud credential campaign",
      summary: "The actor abused cloud credentials for espionage.",
      status: "confirmed",
      confidence: 88,
      first_seen: "2026-01-15T08:00:00Z",
      last_seen: "2026-01-16T08:00:00Z",
      reported_name: "Cozy Bear",
    },
  ],
}

const actorTracking = {
  actor_id: actorId,
  canonical_name: actor.canonical_name,
  period: {
    date_from: "2026-01-01",
    date_to: "2026-08-08",
    previous_from: "2025-05-26",
    previous_to: "2025-12-31",
    day_count: 220,
    bucket: "month",
  },
  comparison: {
    current_event_count: 2,
    previous_event_count: 1,
    absolute_change: 1,
    percentage_change: 100,
  },
  trend: actorDetail.timeline,
  changes: [
    {
      category: "malware",
      current_values: ["Cloud Credential Tool"],
      previous_values: [],
      new_values: ["Cloud Credential Tool"],
      disappeared_values: [],
    },
    {
      category: "infrastructure",
      current_values: [],
      previous_values: [],
      new_values: [],
      disappeared_values: [],
    },
    {
      category: "techniques",
      current_values: ["T1566.001 · Spearphishing Attachment"],
      previous_values: [],
      new_values: ["T1566.001 · Spearphishing Attachment"],
      disappeared_values: [],
    },
    {
      category: "targets",
      current_values: ["Diplomatic organizations"],
      previous_values: [],
      new_values: ["Diplomatic organizations"],
      disappeared_values: [],
    },
  ],
  events: actorDetail.events,
}

const trackingSummary = {
  actor_id: actorId,
  status: "draft",
  title: "Midnight Blizzard · 2026-01-01 至 2026-08-08 跟踪摘要",
  summary: "所选周期共有 2 起已确认事件。",
  highlights: ["较上一等长周期增加 1 起。"],
  caveats: ["必须由分析员核对原始证据。"],
  supporting_event_ids: actorDetail.events.map((event) => event.id),
  supporting_evidence_ids: ["88888888-8888-4888-8888-888888888888"],
  generated_at: "2026-08-08T08:00:00Z",
  method_version: "tracking-rules-v1",
}

function jsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    headers: { "Content-Type": "application/json" },
  })
}

function isoDate(value: Date) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, "0")
  const day = String(value.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}

describe("threat actor tracking", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/actors")
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.startsWith(`/api/v1/actors/${actorId}/tracking/summary`)) {
          return Promise.resolve(jsonResponse(trackingSummary))
        }
        if (url.startsWith(`/api/v1/actors/${actorId}/tracking?`)) {
          return Promise.resolve(jsonResponse(actorTracking))
        }
        if (url.startsWith(`/api/v1/actors/${actorId}?`)) {
          return Promise.resolve(jsonResponse(actorDetail))
        }
        if (url.startsWith("/api/v1/actors?")) {
          return Promise.resolve(jsonResponse([actor]))
        }
        return Promise.resolve(jsonResponse({ detail: "Not found" }))
      })
    )
  })

  it("shows normalized aliases, monthly activity, and custom date filtering", async () => {
    const user = userEvent.setup()
    render(<App />)

    expect(await screen.findByText("Midnight Blizzard")).toBeInTheDocument()
    expect((await screen.findAllByText("APT29")).length).toBeGreaterThan(0)
    expect(
      (await screen.findAllByText(actor.latest_event_title)).length
    ).toBeGreaterThan(0)
    expect((await screen.findAllByText("2026 年 7 月")).length).toBeGreaterThan(
      0
    )
    expect(await screen.findByText("等长周期对比")).toBeInTheDocument()
    expect(screen.getByText("新增 · Cloud Credential Tool")).toBeInTheDocument()
    expect(screen.getByTestId("actor-page-header")).toHaveClass("py-3")
    expect(screen.getByTestId("actor-date-filter")).toHaveClass(
      "lg:w-[23.25rem]"
    )
    expect(
      screen.getByRole("complementary", { name: "攻击组织列表" })
    ).toHaveAttribute("data-testid", "actor-list-scroll")
    expect(screen.queryByText("规范化组织")).not.toBeInTheDocument()
    expect(screen.getByRole("link", { name: "JSON" })).toHaveAttribute(
      "href",
      expect.stringContaining("/tracking/export")
    )

    await user.click(screen.getByRole("button", { name: "生成摘要草稿" }))
    expect(await screen.findByText(trackingSummary.title)).toBeInTheDocument()
    expect(screen.getByText("2 个事件、1 条 Evidence 支撑")).toBeInTheDocument()

    const rangeControls = within(
      screen.getByRole("radiogroup", { name: "日期范围" })
    )
    expect(
      rangeControls.getAllByRole("radio").map((control) => control.textContent)
    ).toEqual(["自定义", "本月", "3个月", "6个月", "本年", "全部"])

    const today = new Date()
    const threeMonthStart = new Date(
      today.getFullYear(),
      today.getMonth() - 2,
      1
    )
    await user.click(rangeControls.getByRole("radio", { name: "3个月" }))
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        `/api/v1/actors?date_from=${isoDate(threeMonthStart)}&date_to=${isoDate(today)}&limit=200`,
        expect.anything()
      )
    })

    await user.click(screen.getByRole("radio", { name: "自定义" }))
    await user.clear(screen.getByLabelText("开始日期"))
    await user.type(screen.getByLabelText("开始日期"), "2026-06-01")
    await user.clear(screen.getByLabelText("结束日期"))
    await user.type(screen.getByLabelText("结束日期"), "2026-07-31")

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/api/v1/actors?date_from=2026-06-01&date_to=2026-07-31&limit=200",
        expect.anything()
      )
      expect(fetch).toHaveBeenCalledWith(
        `/api/v1/actors/${actorId}/tracking?date_from=2026-06-01&date_to=2026-07-31`,
        expect.anything()
      )
    })
  })
})
