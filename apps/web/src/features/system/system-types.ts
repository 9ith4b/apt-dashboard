export type SearchResult = {
  kind: "actor" | "event" | "observable" | "report"
  id: string
  title: string
  subtitle: string
  url: string
  score: number
}

export type SearchResponse = {
  query: string
  total: number
  results: SearchResult[]
}

export type Notification = {
  id: string
  hit_id: string | null
  title: string
  message: string
  severity: "info" | "low" | "medium" | "high" | "critical"
  target_type: string
  target_id: string | null
  read_at: string | null
  created_at: string
}

export type NotificationList = {
  unread_count: number
  items: Notification[]
}
