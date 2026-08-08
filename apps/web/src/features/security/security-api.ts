import { apiRequest } from "@/lib/api"

import type {
  AuditLog,
  CurrentUser,
  UserCreate,
  UserUpdate,
} from "./security-types"

export const usersQueryKey = ["security-users"] as const
export const auditQueryKey = ["audit-logs"] as const

export function listUsers() {
  return apiRequest<CurrentUser[]>("/auth/users")
}

export function createUser(payload: UserCreate) {
  return apiRequest<CurrentUser>("/auth/users", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function updateUser(userId: string, payload: UserUpdate) {
  return apiRequest<CurrentUser>(`/auth/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  })
}

export function listAuditLogs() {
  return apiRequest<AuditLog[]>("/audit-logs?limit=100")
}
