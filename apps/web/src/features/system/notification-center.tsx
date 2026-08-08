import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { BellIcon, CheckCheckIcon } from "lucide-react"
import { Link } from "react-router-dom"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { formatDateTime } from "@/features/intelligence/intelligence-format"
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  notificationQueryKey,
} from "@/features/system/system-api"

function notificationTarget(targetType: string, targetId: string | null) {
  if (!targetId) return "/watch-rules"
  if (targetType === "event") return `/events?event=${targetId}`
  if (targetType === "observable") return `/hunt?observable=${targetId}`
  return "/watch-rules"
}

export function NotificationCenter() {
  const queryClient = useQueryClient()
  const notifications = useQuery({
    queryKey: notificationQueryKey,
    queryFn: listNotifications,
    refetchInterval: 30_000,
  })
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: notificationQueryKey })
  const markOne = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: invalidate,
  })
  const markAll = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: invalidate,
  })
  const unread = notifications.data?.unread_count ?? 0

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button
          aria-label={`通知${unread ? `，${unread} 条未读` : ""}`}
          className="relative"
          size="icon"
          variant="outline"
        >
          <BellIcon />
          {unread ? (
            <span className="text-destructive-foreground absolute -top-1.5 -right-1.5 flex min-w-5 items-center justify-center rounded-full bg-destructive px-1 text-[10px] leading-5">
              {unread > 99 ? "99+" : unread}
            </span>
          ) : null}
        </Button>
      </SheetTrigger>
      <SheetContent className="sm:max-w-md">
        <SheetHeader className="border-b border-border">
          <div className="flex items-start justify-between gap-4 pr-10">
            <div>
              <SheetTitle>站内通知</SheetTitle>
              <SheetDescription>{unread} 条未读规则命中</SheetDescription>
            </div>
            <Button
              disabled={!unread || markAll.isPending}
              onClick={() => markAll.mutate()}
              size="sm"
              variant="ghost"
            >
              <CheckCheckIcon data-icon="inline-start" />
              全部已读
            </Button>
          </div>
        </SheetHeader>
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-3">
          {notifications.isPending ? (
            <p className="p-3 text-sm text-muted-foreground">正在加载通知…</p>
          ) : notifications.isError ? (
            <p className="p-3 text-sm text-destructive">
              {notifications.error.message}
            </p>
          ) : notifications.data?.items?.length ? (
            notifications.data.items.map((item) => (
              <Link
                className="rounded-lg border border-border p-3 hover:bg-accent"
                key={item.id}
                onClick={() => {
                  if (!item.read_at) markOne.mutate(item.id)
                }}
                to={notificationTarget(item.target_type, item.target_id)}
              >
                <div className="flex items-center justify-between gap-2">
                  <Badge variant={item.read_at ? "outline" : "default"}>
                    {item.severity}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {formatDateTime(item.created_at)}
                  </span>
                </div>
                <p className="mt-2 text-sm font-medium">{item.title}</p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  {item.message}
                </p>
              </Link>
            ))
          ) : (
            <p className="p-3 text-sm text-muted-foreground">
              目前没有规则命中通知。
            </p>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
