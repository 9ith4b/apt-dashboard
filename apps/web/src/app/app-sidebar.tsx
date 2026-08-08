import {
  BellRingIcon,
  BotIcon,
  CircleDotDashedIcon,
  DatabaseIcon,
  FileCheck2Icon,
  GitBranchIcon,
  HouseIcon,
  RadarIcon,
  SendIcon,
  ShieldUserIcon,
} from "lucide-react"
import { NavLink, useLocation } from "react-router-dom"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar"

const navigation = [
  { title: "情报流", url: "/feed", icon: BotIcon },
  { title: "事件图谱", url: "/events", icon: GitBranchIcon },
  { title: "攻击者", url: "/actors", icon: ShieldUserIcon },
  { title: "Campaign", url: "/campaigns", icon: SendIcon },
  { title: "IOC", url: "/hunt", icon: CircleDotDashedIcon },
  { title: "关注规则", url: "/watch-rules", icon: HouseIcon },
  { title: "数据源", url: "/sources", icon: DatabaseIcon },
  { title: "待审核", url: "/reviews", icon: FileCheck2Icon },
] as const

export function AppSidebar() {
  const location = useLocation()

  return (
    <Sidebar collapsible="icon" variant="sidebar">
      <SidebarHeader className="h-18 justify-center border-b border-sidebar-border px-4">
        <NavLink className="flex items-center gap-3" to="/feed">
          <span className="flex size-8 items-center justify-center rounded-md bg-sidebar-primary/15 text-sidebar-primary">
            <RadarIcon aria-hidden="true" />
          </span>
          <span className="text-lg font-semibold tracking-tight group-data-[collapsible=icon]:hidden">
            APT Hunter
          </span>
        </NavLink>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup className="px-2 py-4">
          <SidebarGroupContent>
            <SidebarMenu className="gap-1.5">
              {navigation.map((item) => {
                const isActive = location.pathname.startsWith(item.url)
                return (
                  <SidebarMenuItem key={item.url}>
                    <SidebarMenuButton
                      asChild
                      isActive={isActive}
                      size="lg"
                      tooltip={item.title}
                    >
                      <NavLink to={item.url}>
                        <item.icon aria-hidden="true" />
                        <span>{item.title}</span>
                      </NavLink>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="p-3">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              className="border border-sidebar-border"
              size="lg"
            >
              <span className="size-2 rounded-full bg-confirmed" />
              <span>4/4 基础服务就绪</span>
              <BellRingIcon aria-hidden="true" />
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
