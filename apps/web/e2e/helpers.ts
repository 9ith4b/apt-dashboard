import { expect, type Page } from "@playwright/test"

export const routes = [
  ["/feed", "情报流"],
  ["/events", "事件图谱"],
  ["/actors", "攻击者"],
  ["/campaigns", "Campaign"],
  ["/hunt", "IOC 狩猎"],
  ["/watch-rules", "关注规则"],
  ["/sources", "数据源"],
  ["/reviews", "异常研判"],
  ["/operations", "作业中心"],
  ["/automation", "AI 自动化"],
  ["/security", "身份与审计"],
] as const

export function credentials() {
  const username = process.env.APT_HUNTER_E2E_USERNAME
  const password = process.env.APT_HUNTER_E2E_PASSWORD
  if (!username || !password) {
    throw new Error(
      "APT_HUNTER_E2E_USERNAME and APT_HUNTER_E2E_PASSWORD are required"
    )
  }
  return { username, password }
}

export async function login(page: Page) {
  const { username, password } = credentials()
  await page.goto("/login")
  await page.locator("#login-username").fill(username)
  await page.locator("#login-password").fill(password)
  await page.getByRole("button", { name: "安全登录", exact: true }).click()
  await expect(
    page.getByRole("heading", { name: "情报流", level: 1 })
  ).toBeVisible()
}
