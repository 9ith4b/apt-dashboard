import {
  ActivityIcon,
  BellRingIcon,
  BotIcon,
  CircleDotDashedIcon,
  DatabaseIcon,
  FileCheck2Icon,
  GitBranchIcon,
  ListTodoIcon,
  PanelLeftCloseIcon,
  PanelLeftOpenIcon,
  RadarIcon,
  SendIcon,
  ShieldCheckIcon,
  ShieldUserIcon,
} from "lucide-react"
import { NavLink, useLocation } from "react-router-dom"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar"
import { useAuth } from "@/features/auth/auth-context"

const navigation = [
  { title: "情报流", url: "/feed", icon: ActivityIcon },
  { title: "事件图谱", url: "/events", icon: GitBranchIcon },
  { title: "攻击者", url: "/actors", icon: ShieldUserIcon },
  { title: "攻击活动", url: "/campaigns", icon: SendIcon },
  { title: "IOC 狩猎", url: "/hunt", icon: CircleDotDashedIcon },
  { title: "关注规则", url: "/watch-rules", icon: BellRingIcon },
  { title: "数据源", url: "/sources", icon: DatabaseIcon },
  { title: "AI 分析纠错", url: "/reviews", icon: FileCheck2Icon },
  { title: "作业中心", url: "/operations", icon: ListTodoIcon },
  {
    title: "AI 自动化",
    url: "/automation",
    icon: BotIcon,
    adminOnly: true,
  },
  {
    title: "身份与审计",
    url: "/security",
    icon: ShieldCheckIcon,
    adminOnly: true,
  },
] as const

function SidebarCollapseButton() {
  const { state, toggleSidebar } = useSidebar()
  const isCollapsed = state === "collapsed"
  const label = isCollapsed ? "展开侧边栏" : "收起侧边栏"

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <SidebarMenuButton
          aria-controls="app-sidebar-navigation"
          aria-expanded={!isCollapsed}
          aria-label={label}
          className="group-data-[collapsible=icon]:justify-center"
          onClick={toggleSidebar}
          size="lg"
          tooltip={label}
          type="button"
        >
          {isCollapsed ? (
            <PanelLeftOpenIcon aria-hidden="true" />
          ) : (
            <PanelLeftCloseIcon aria-hidden="true" />
          )}
          <span className="group-data-[collapsible=icon]:hidden">{label}</span>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}

export function AppSidebar() {
  const location = useLocation()
  const auth = useAuth()

  return (
    <Sidebar collapsible="icon" id="app-sidebar-navigation" variant="sidebar">
      <SidebarHeader className="h-16 justify-center border-b border-sidebar-border px-3 group-data-[collapsible=icon]:px-1.5">
        <NavLink
          aria-label="APT Hunter 首页"
          className="flex items-center gap-3 group-data-[collapsible=icon]:justify-center"
          to="/feed"
        >
          <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground shadow-xs">
            <RadarIcon aria-hidden="true" />
          </span>
          <span className="min-w-0 group-data-[collapsible=icon]:hidden">
            <span className="block truncate text-sm font-semibold tracking-tight">
              APT Hunter
            </span>
            <span className="block truncate text-[0.65rem] tracking-[0.12em] text-sidebar-foreground/70 uppercase">
              Intelligence Desk
            </span>
          </span>
        </NavLink>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup className="px-2 py-4">
          <SidebarGroupLabel className="px-2 text-[0.65rem] tracking-[0.12em] uppercase">
            工作台
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-1">
              {navigation
                .filter((item) => !("adminOnly" in item) || auth.canAdmin)
                .map((item) => {
                  const isActive = location.pathname.startsWith(item.url)
                  return (
                    <SidebarMenuItem key={item.url}>
                      <SidebarMenuButton
                        asChild
                        className="group-data-[collapsible=icon]:justify-center"
                        isActive={isActive}
                        size="lg"
                        tooltip={item.title}
                      >
                        <NavLink aria-label={item.title} to={item.url}>
                          <item.icon aria-hidden="true" />
                          <span className="group-data-[collapsible=icon]:hidden">
                            {item.title}
                          </span>
                        </NavLink>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  )
                })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="gap-2 p-3 group-data-[collapsible=icon]:p-2">
        <SidebarCollapseButton />
        <div className="flex items-center gap-2 rounded-lg border border-sidebar-border bg-sidebar-accent/55 px-3 py-2.5 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0">
          <span className="relative flex size-2.5 shrink-0">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-confirmed opacity-35" />
            <span className="relative inline-flex size-2.5 rounded-full bg-confirmed" />
          </span>
          <span className="min-w-0 flex-1 group-data-[collapsible=icon]:hidden">
            <span className="block text-xs font-medium">系统运行正常</span>
            <span className="block truncate text-[0.65rem] text-sidebar-foreground/70">
              4/4 基础服务就绪
            </span>
          </span>
        </div>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
