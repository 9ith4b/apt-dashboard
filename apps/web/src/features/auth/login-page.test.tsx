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
