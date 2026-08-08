import type { CurrentUser, UserRole } from "@/features/auth/auth-types"

export type { CurrentUser, UserRole }

export type UserCreate = {
  username: string
  display_name: string
  password: string
  role: UserRole
  enabled: boolean
}

export type UserUpdate = Partial<
  Pick<UserCreate, "display_name" | "password" | "role" | "enabled">
>

export type AuditLog = {
  id: string
  actor_user_id: string | null
  actor_username: string | null
  action: string
  object_type: string | null
  object_id: string | null
  result: string
  request_id: string
  ip_address: string
  details: Record<string, unknown>
  created_at: string
}
