import { BookOpenIcon, CircleUserRoundIcon } from "lucide-react"
import type { CSSProperties } from "react"
import { Outlet, useLocation } from "react-router-dom"

import { AppSidebar } from "@/app/app-sidebar"
import { Button } from "@/components/ui/button"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import { GlobalSearch } from "@/features/system/global-search"
import { NotificationCenter } from "@/features/system/notification-center"

const routeTitles: Record<string, string> = {
  "/feed": "情报流",
  "/events": "事件图谱",
  "/actors": "攻击者",
  "/campaigns": "Campaign",
  "/hunt": "IOC 狩猎",
  "/watch-rules": "关注规则",
  "/sources": "数据源",
  "/reviews": "待审核",
  "/operations": "作业中心",
}

export function AppShell() {
  const location = useLocation()
  const title = routeTitles[location.pathname] ?? "APT Hunter"

  return (
    <SidebarProvider
      defaultOpen
      style={{ "--sidebar-width": "12.5rem" } as CSSProperties}
    >
      <AppSidebar />
      <SidebarInset className="min-w-0 bg-background">
        <header className="flex h-18 shrink-0 items-center gap-2 border-b border-border px-3 sm:gap-4 sm:px-7">
          <SidebarTrigger className="md:hidden" />
          <div className="flex min-w-0 items-center gap-5">
            <h1 className="text-xl font-semibold tracking-tight whitespace-nowrap sm:text-2xl">
              {title}
            </h1>
            <span className="hidden text-sm text-muted-foreground lg:inline">
              2026年8月8日 · 星期六
            </span>
          </div>
          <div className="ml-auto flex items-center gap-2.5">
            <GlobalSearch />
            <NotificationCenter />
            <Button
              aria-label="知识库"
              className="hidden sm:inline-flex"
              size="icon"
              variant="outline"
            >
              <BookOpenIcon />
            </Button>
            <Button className="hidden lg:inline-flex" variant="ghost">
              <CircleUserRoundIcon data-icon="inline-start" />
              分析师
            </Button>
            <Button>开始研判</Button>
          </div>
        </header>
        <Outlet />
      </SidebarInset>
    </SidebarProvider>
  )
}
