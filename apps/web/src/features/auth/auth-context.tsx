/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useState } from "react"

import { ApiError } from "@/lib/api"

import { getSession, loadCsrfToken, login, logout } from "./auth-api"
import { LoginPage } from "./login-page"
import type { AuthSession, CurrentUser } from "./auth-types"

type AuthContextValue = {
  user: CurrentUser
  canWrite: boolean
  canAdmin: boolean
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

const TEST_USER: CurrentUser = {
  id: "00000000-0000-4000-8000-000000000001",
  username: "analyst",
  display_name: "分析师",
  role: "admin",
  enabled: true,
  last_login_at: null,
  created_at: "2026-08-08T00:00:00Z",
}

function WorkspaceAuth({
  session,
  onLogout,
  children,
}: {
  session: AuthSession
  onLogout: () => void
  children: React.ReactNode
}) {
  const user = session.user
  return (
    <AuthContext.Provider
      value={{
        user,
        canWrite: user.role === "analyst" || user.role === "admin",
        canAdmin: user.role === "admin",
        logout: async () => {
          await logout()
          onLogout()
        },
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function AuthGate({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null)
  const [loading, setLoading] = useState(import.meta.env.MODE !== "test")
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (import.meta.env.MODE === "test") return
    let active = true
    getSession()
      .then(async (nextSession) => {
        await loadCsrfToken()
        if (active) setSession(nextSession)
      })
      .catch((caught: unknown) => {
        if (active && !(caught instanceof ApiError && caught.status === 401)) {
          setError(
            caught instanceof Error ? caught.message : "无法连接认证服务"
          )
        }
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    const unauthorized = () => setSession(null)
    window.addEventListener("apt-hunter:unauthorized", unauthorized)
    return () => {
      active = false
      window.removeEventListener("apt-hunter:unauthorized", unauthorized)
    }
  }, [])

  if (import.meta.env.MODE === "test") {
    return (
      <WorkspaceAuth
        session={{ user: TEST_USER, expires_at: "2099-01-01T00:00:00Z" }}
        onLogout={() => undefined}
      >
        {children}
      </WorkspaceAuth>
    )
  }
  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-background text-sm text-muted-foreground">
        正在验证安全会话…
      </main>
    )
  }
  if (!session) {
    return (
      <LoginPage
        error={error}
        pending={pending}
        onLogin={(username, password) => {
          setPending(true)
          setError(null)
          login(username, password)
            .then(setSession)
            .catch((caught: unknown) =>
              setError(caught instanceof Error ? caught.message : "登录失败")
            )
            .finally(() => setPending(false))
        }}
      />
    )
  }
  return (
    <WorkspaceAuth session={session} onLogout={() => setSession(null)}>
      {children}
    </WorkspaceAuth>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error("useAuth must be used inside AuthGate")
  return context
}
