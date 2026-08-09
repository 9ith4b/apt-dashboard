import { expect, test } from "@playwright/test"

import { credentials, login } from "./helpers"

test("login page visual baseline", async ({ page }, testInfo) => {
  test.skip(
    !testInfo.project.name.startsWith("desktop"),
    "Desktop visual baseline"
  )
  credentials()
  await page.addInitScript(() => {
    localStorage.setItem("apt-hunter-theme", "dark")
  })
  await page.goto("/login?visual-test=1")
  await expect(page.getByRole("button", { name: "安全登录" })).toBeVisible()
  await expect(page.getByTestId("black-hole-accent")).toBeVisible()
  await expect(page).toHaveScreenshot("login-page.png", { fullPage: true })
})

test("authenticated shell visual baseline", async ({ page }, testInfo) => {
  test.skip(
    !testInfo.project.name.startsWith("desktop"),
    "Desktop visual baseline"
  )
  await login(page)
  await expect(page.getByRole("button", { name: /基础服务就绪/ })).toBeVisible()
  await expect(page).toHaveScreenshot("app-shell.png", {
    fullPage: true,
    mask: [page.locator('[data-slot="sidebar-inset"] > :not(header)')],
    maskColor: "#0b111b",
  })
})
