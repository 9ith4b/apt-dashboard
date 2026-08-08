import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"

import { AppShell } from "@/app/app-shell"
import { TooltipProvider } from "@/components/ui/tooltip"
import { IntelligenceFeedPage } from "@/features/feed/intelligence-feed-page"
import { PlaceholderPage } from "@/features/shared/placeholder-page"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
})

const placeholderRoutes = [
  ["/events", "事件图谱", "事件钻石画布将在 M2 分析与审核阶段接入。"],
  ["/actors", "攻击者", "攻击组织画像将在实体规范化完成后接入。"],
  ["/campaigns", "Campaign", "Campaign 时间线将在事件聚类能力完成后接入。"],
  ["/hunt", "IOC 狩猎", "Observable 检索与富化将在 M3 阶段接入。"],
  ["/watch-rules", "关注规则", "关注条件和命中预览将在 M4 阶段接入。"],
  ["/sources", "数据源", "RSS、网页与社交媒体连接器将在 M1 阶段接入。"],
  ["/reviews", "待审核", "字段级证据审核将在 M2 阶段接入。"],
] as const

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<AppShell />}>
              <Route index element={<Navigate replace to="/feed" />} />
              <Route path="/feed" element={<IntelligenceFeedPage />} />
              {placeholderRoutes.map(([path, title, description]) => (
                <Route
                  key={path}
                  path={path}
                  element={
                    <PlaceholderPage title={title} description={description} />
                  }
                />
              ))}
            </Route>
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  )
}

export default App
