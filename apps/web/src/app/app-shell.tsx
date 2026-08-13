import {
  BookOpenIcon,
  CalendarDaysIcon,
  CircleUserRoundIcon,
  FlaskConicalIcon,
} from "lucide-react"
import type { CSSProperties } from "react"
import { Outlet, useLocation } from "react-router-dom"

import { AppSidebar } from "@/app/app-sidebar"
import { ThemeToggle } from "@/components/theme-toggle"
import { Button } from "@/components/ui/button"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import { useAuth } from "@/features/auth/auth-context"
import { GlobalSearch } from "@/features/system/global-search"
import { NotificationCenter } from "@/features/system/notification-center"

const routeTitles: Record<string, string> = {
  "/feed": "情报流",
  "/events": "事件图谱",
  "/actors": "攻击者",
  "/campaigns": "攻击活动",
  "/hunt": "IOC 狩猎",
  "/watch-rules": "关注规则",
  "/sources": "数据源",
  "/reviews": "异常研判",
  "/operations": "作业中心",
  "/automation": "AI 自动化",
  "/security": "身份与审计",
}

const dateFormatter = new Intl.DateTimeFormat("zh-CN", {
  year: "numeric",
  month: "long",
  day: "numeric",
  weekday: "short",
})

export function AppShell() {
  const location = useLocation()
  const auth = useAuth()
  const title = routeTitles[location.pathname] ?? "APT Hunter"

  return (
    <SidebarProvider
      className="h-svh min-h-0 overflow-hidden"
      defaultOpen
      style={
        {
          "--sidebar-width": "14rem",
          "--sidebar-width-mobile": "17rem",
        } as CSSProperties
      }
    >
      <AppSidebar />
      <SidebarInset className="h-svh min-h-0 min-w-0 overflow-hidden bg-background">
        <header className="flex h-16 shrink-0 items-center gap-3 border-b border-border bg-card/95 px-3 backdrop-blur-sm sm:px-6">
          <SidebarTrigger className="md:hidden" />
          <div className="flex min-w-0 items-center gap-5">
            <h1 className="truncate text-xl font-semibold tracking-tight sm:text-2xl">
              {title}
            </h1>
            <span className="hidden items-center gap-2 text-xs text-muted-foreground lg:flex">
              <CalendarDaysIcon aria-hidden="true" />
              {dateFormatter.format(new Date())}
            </span>
          </div>

          <div className="ml-auto flex min-w-0 items-center gap-1.5 sm:gap-2">
            <GlobalSearch />
            <ThemeToggle />
            <NotificationCenter />
            <Button
              aria-label="打开知识库"
              className="hidden sm:inline-flex"
              size="icon"
              variant="ghost"
            >
              <BookOpenIcon />
            </Button>
            <Button
              aria-label={`账户 ${auth.user.display_name}，点击退出`}
              className="hidden md:inline-flex"
              title={`${auth.user.role} · 点击退出`}
              variant="ghost"
              onClick={() => void auth.logout()}
            >
              <CircleUserRoundIcon data-icon="inline-start" />
              <span className="hidden xl:inline">{auth.user.display_name}</span>
            </Button>
            <Button className="hidden lg:inline-flex">
              <FlaskConicalIcon data-icon="inline-start" />
              开始研判
            </Button>
          </div>
        </header>
        <Outlet />
      </SidebarInset>
    </SidebarProvider>
  )
}
