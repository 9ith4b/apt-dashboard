import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { expect, it, vi } from "vitest"

import { LoginPage } from "./login-page"

it("submits a local account without exposing the password by default", async () => {
  const user = userEvent.setup()
  const onLogin = vi.fn()
  render(<LoginPage error={null} pending={false} onLogin={onLogin} />)

  const password = screen.getByLabelText("密码")
  expect(password).toHaveAttribute("type", "password")
  await user.type(screen.getByLabelText("用户名"), "admin")
  await user.type(password, "a secure local password")
  await user.click(screen.getByRole("button", { name: "安全登录" }))

  expect(onLogin).toHaveBeenCalledWith("admin", "a secure local password")
})

it("renders the immersive login identity and toggles password visibility", async () => {
  const user = userEvent.setup()
  render(<LoginPage error={null} pending={false} onLogin={vi.fn()} />)

  expect(
    screen.getByRole("heading", { name: "洞察威胁轨迹" })
  ).toBeInTheDocument()
  expect(screen.getByTestId("black-hole-scene")).toHaveAttribute(
    "aria-hidden",
    "true"
  )
  expect(
    screen.getByTitle("Black Hole by Nestaeric on Sketchfab")
  ).toHaveAttribute("src", expect.stringContaining("dnt=1"))
  expect(
    screen.getByRole("link", { name: "Black Hole by Nestaeric · Sketchfab" })
  ).toHaveAttribute("rel", "nofollow noreferrer")

  const password = screen.getByLabelText("密码")
  await user.click(screen.getByRole("button", { name: "显示密码" }))
  expect(password).toHaveAttribute("type", "text")
  expect(screen.getByRole("button", { name: "隐藏密码" })).toBeInTheDocument()
})
