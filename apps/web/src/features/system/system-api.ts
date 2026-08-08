import { apiRequest } from "@/lib/api"

import type {
  Notification,
  NotificationList,
  SearchResponse,
} from "./system-types"

export const notificationQueryKey = ["notifications"] as const
export const searchQueryKey = ["global-search"] as const

export function globalSearch(query: string) {
  return apiRequest<SearchResponse>(
    `/search?q=${encodeURIComponent(query)}&limit=20`
  )
}

export function listNotifications() {
  return apiRequest<NotificationList>("/notifications?limit=50")
}

export function markNotificationRead(notificationId: string) {
  return apiRequest<Notification>(`/notifications/${notificationId}/read`, {
    method: "PATCH",
  })
}

export function markAllNotificationsRead() {
  return apiRequest<NotificationList>("/notifications/read-all", {
    method: "POST",
  })
}
