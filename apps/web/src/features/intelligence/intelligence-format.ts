export function formatDateTime(value: string | null) {
  if (!value) return "时间未知"
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value))
}

export function formatRelativeTime(value: string | null) {
  if (!value) return "时间未知"
  const elapsedMinutes = Math.max(
    0,
    Math.round((Date.now() - new Date(value).getTime()) / 60_000)
  )
  if (elapsedMinutes < 60) return `${elapsedMinutes} 分钟前`
  const hours = Math.round(elapsedMinutes / 60)
  if (hours < 24) return `${hours} 小时前`
  return `${Math.round(hours / 24)} 天前`
}

export function sourceInitials(value: string) {
  const words = value.match(/[A-Za-z0-9]+/g)
  if (words?.length) {
    return words
      .slice(0, 2)
      .map((word) => word[0])
      .join("")
      .toUpperCase()
  }
  return value.slice(0, 2)
}

export function extractionLabel(value: string | null) {
  if (value === "ready") return "已富化"
  if (value === "processing") return "提取中"
  if (value === "queued") return "排队中"
  if (value === "failed") return "提取失败"
  return "待富化"
}
