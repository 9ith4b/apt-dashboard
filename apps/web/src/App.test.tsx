import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it } from "vitest"

import App from "./App"

describe("APT Hunter application shell", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/feed")
  })

  it("renders the intelligence feed and selected event evidence", () => {
    render(<App />)

    expect(screen.getByRole("heading", { name: "情报流" })).toBeInTheDocument()
    expect(
      screen.getAllByText("Lazarus 利用虚假技术面试向开发者投递恶意 NPM 包")
    ).toHaveLength(2)
    expect(screen.getByText("关键证据")).toBeInTheDocument()
  })

  it("updates the inspector when a feed item is selected", async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(
      screen.getByRole("button", {
        name: /APT28 针对政府外交机构的凭据窃取活动/,
      })
    )

    expect(screen.getByText(/研究人员观察到针对政府与外交机构/)).toBeInTheDocument()
  })
})
