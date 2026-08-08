import { render, screen, waitFor } from "@testing-library/react"
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

function jsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    headers: { "Content-Type": "application/json" },
  })
}

describe("threat actor tracking", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/actors")
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input)
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
    expect(await screen.findByText("2026 年 7 月")).toBeInTheDocument()

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
    })
  })
})
