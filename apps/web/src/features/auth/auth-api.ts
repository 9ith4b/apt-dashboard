import { apiRequest, setCsrfToken } from "@/lib/api"

import type { AuthSession } from "./auth-types"

export function getSession() {
  return apiRequest<AuthSession>("/auth/me")
}

export async function loadCsrfToken() {
  const response = await fetch("/api/v1/auth/csrf", {
    credentials: "same-origin",
  })
  if (!response.ok) throw new Error("无法建立安全会话")
  const payload = (await response.json()) as { csrf_token: string }
  setCsrfToken(payload.csrf_token)
}

export async function login(username: string, password: string) {
  const auth = await apiRequest<AuthSession>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  })
  await loadCsrfToken()
  return auth
}

export async function logout() {
  await apiRequest<void>("/auth/logout", { method: "POST" })
  setCsrfToken(null)
}
