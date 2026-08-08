export type UserRole = "viewer" | "analyst" | "admin"

export type CurrentUser = {
  id: string
  username: string
  display_name: string
  role: UserRole
  enabled: boolean
  last_login_at: string | null
  created_at: string
}

export type AuthSession = {
  user: CurrentUser
  expires_at: string
}
