import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, expect, it, vi } from "vitest"

import { ThemeProvider } from "@/components/theme-provider"

import { LoginPage } from "./login-page"

vi.mock("@/components/visuals/black-hole-renderer", () => ({
  BlackHoleHeroSection: () => <div data-testid="black-hole-renderer" />,
}))

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

function renderLogin(onLogin = vi.fn()) {
  render(
    <ThemeProvider defaultTheme="light" storageKey="login-page-test-theme">
      <LoginPage error={null} pending={false} onLogin={onLogin} />
    </ThemeProvider>
  )
  return onLogin
}

it("submits a local account without exposing the password by default", async () => {
  const user = userEvent.setup()
  const onLogin = renderLogin()

  const password = screen.getByLabelText("密码")
  expect(password).toHaveAttribute("type", "password")
  await user.type(screen.getByLabelText("用户名"), "admin")
  await user.type(password, "a secure local password")
  await user.click(screen.getByRole("button", { name: "安全登录" }))

  expect(onLogin).toHaveBeenCalledWith("admin", "a secure local password")
})

it("renders the lightweight intelligence identity and toggles password visibility", async () => {
  const user = userEvent.setup()
  renderLogin()

  expect(
    screen.getByRole("heading", { name: /把散落的信号/ })
  ).toBeInTheDocument()
  expect(
    screen.getByRole("heading", { name: "登录情报工作台" })
  ).toBeInTheDocument()
  expect(
    screen.getByRole("button", { name: "切换到深色主题" })
  ).toBeInTheDocument()
  expect(document.querySelector("iframe")).not.toBeInTheDocument()
  expect(document.querySelector("canvas")).not.toBeInTheDocument()
  expect(document.querySelector("video")).not.toBeInTheDocument()
  expect(screen.queryByTestId("black-hole-accent")).not.toBeInTheDocument()

  const password = screen.getByLabelText("密码")
  await user.click(screen.getByRole("button", { name: "显示密码" }))
  expect(password).toHaveAttribute("type", "text")
  expect(screen.getByRole("button", { name: "隐藏密码" })).toBeInTheDocument()
})

it("loads the wandering lens scene only after dark desktop becomes idle", async () => {
  vi.stubGlobal(
    "requestIdleCallback",
    vi.fn((callback: IdleRequestCallback) => {
      callback({ didTimeout: false, timeRemaining: () => 10 })
      return 1
    })
  )
  vi.spyOn(window, "matchMedia").mockImplementation(
    (query) =>
      ({
        matches:
          query === "(min-width: 1280px)" ||
          query === "(prefers-color-scheme: dark)",
        media: query,
        onchange: null,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
        addListener: () => undefined,
        removeListener: () => undefined,
        dispatchEvent: () => false,
      }) as MediaQueryList
  )

  render(
    <ThemeProvider defaultTheme="dark" storageKey="login-accent-test-theme">
      <LoginPage error={null} pending={false} onLogin={vi.fn()} />
    </ThemeProvider>
  )

  expect(await screen.findByTestId("black-hole-accent")).toBeInTheDocument()
  expect(
    await screen.findByTestId("black-hole-lensing-field")
  ).toBeInTheDocument()
  expect(
    await screen.findByTestId("black-hole-event-horizon")
  ).toBeInTheDocument()
  expect(await screen.findByTestId("black-hole-renderer")).toBeInTheDocument()
  expect(document.querySelector("#black-hole-dom-lens")).toBeInTheDocument()
  expect(screen.getByTestId("black-hole-wander-scene")).toHaveAttribute(
    "data-tone",
    "dark"
  )
})

it("loads the light-theme gravitational lens on an eligible desktop", async () => {
  vi.stubGlobal(
    "requestIdleCallback",
    vi.fn((callback: IdleRequestCallback) => {
      callback({ didTimeout: false, timeRemaining: () => 10 })
      return 1
    })
  )
  vi.spyOn(window, "matchMedia").mockImplementation(
    (query) =>
      ({
        matches: query === "(min-width: 1280px)",
        media: query,
        onchange: null,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
        addListener: () => undefined,
        removeListener: () => undefined,
        dispatchEvent: () => false,
      }) as MediaQueryList
  )

  renderLogin()

  expect(await screen.findByTestId("black-hole-accent")).toBeInTheDocument()
  expect(screen.getByTestId("black-hole-wander-scene")).toHaveAttribute(
    "data-tone",
    "light"
  )
})
