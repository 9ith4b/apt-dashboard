import AxeBuilder from "@axe-core/playwright"
import { expect, test } from "@playwright/test"

import { login, routes } from "./helpers"

test("requires authentication and creates an HttpOnly session", async ({
  context,
  page,
}) => {
  await page.goto("/feed")
  await expect(page).toHaveURL(/\/login$/)
  await login(page)
  const cookies = await context.cookies()
  const session = cookies.find((cookie) => cookie.name === "apt_hunter_session")
  expect(session?.httpOnly).toBe(true)
  expect(session?.sameSite).toBe("Lax")
})

test("renders every product page without browser errors or body overflow", async ({
  page,
}, testInfo) => {
  const browserErrors: string[] = []
  page.on("console", (message) => {
    if (message.type() === "error") browserErrors.push(message.text())
  })
  page.on("pageerror", (error) => browserErrors.push(error.message))
  await login(page)
  browserErrors.length = 0

  for (const [path, title] of routes) {
    await page.goto(path)
    await expect(
      page.getByRole("heading", { name: title, level: 1 })
    ).toBeVisible()
    await expect
      .poll(() =>
        page.evaluate(() => document.body.scrollWidth <= window.innerWidth + 1)
      )
      .toBe(true)
    await page.screenshot({
      path: testInfo.outputPath(`${path.slice(1)}.png`),
      fullPage: true,
    })
  }
  expect(browserErrors).toEqual([])
})

test("mobile navigation exposes all primary destinations", async ({
  page,
}, testInfo) => {
  test.skip(
    !testInfo.project.name.startsWith("mobile"),
    "Mobile-only navigation check"
  )
  await login(page)
  await page.getByRole("button", { name: "Toggle Sidebar" }).click()
  for (const [, title] of routes) {
    await expect(
      page.getByRole("link", { name: title === "IOC 狩猎" ? "IOC" : title })
    ).toBeVisible()
  }
})

test("all product pages meet automated WCAG A and AA rules", async ({
  page,
}, testInfo) => {
  test.skip(
    !testInfo.project.name.startsWith("desktop"),
    "One deterministic accessibility pass"
  )
  await page.goto("/login")
  await expect(
    page.getByRole("button", { name: "安全登录", exact: true })
  ).toBeVisible()
  const loginResults = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze()
  expect(
    loginResults.violations,
    "/login has accessibility violations"
  ).toEqual([])
  await login(page)
  for (const [path, title] of routes) {
    await page.goto(path)
    await expect(
      page.getByRole("heading", { name: title, level: 1 })
    ).toBeVisible()
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze()
    expect(
      results.violations.map(({ id, impact, nodes }) => ({
        id,
        impact,
        nodes: nodes.map(({ target, html, failureSummary }) => ({
          target,
          html,
          failureSummary,
        })),
      })),
      `${path} has accessibility violations`
    ).toEqual([])
  }
})

test("navigation performance stays within the interactive budget", async ({
  page,
}, testInfo) => {
  test.skip(
    !testInfo.project.name.startsWith("desktop"),
    "One deterministic performance pass"
  )
  await login(page)
  await page.goto("/feed")
  await expect(
    page.getByRole("heading", { name: "情报流", level: 1 })
  ).toBeVisible()
  const timing = await page.evaluate(() => {
    const navigation = performance.getEntriesByType(
      "navigation"
    )[0] as PerformanceNavigationTiming
    return {
      domInteractive: navigation.domInteractive,
      loaded: navigation.loadEventEnd,
    }
  })
  expect(timing.domInteractive).toBeLessThan(3_000)
  expect(timing.loaded).toBeLessThan(5_000)
  console.log(
    `performance domInteractive=${timing.domInteractive.toFixed(1)}ms load=${timing.loaded.toFixed(1)}ms`
  )
})
