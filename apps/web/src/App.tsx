import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { lazy, Suspense } from "react"
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"

import { AppShell } from "@/app/app-shell"
import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import { IntelligenceFeedPage } from "@/features/feed/intelligence-feed-page"
import { PlaceholderPage } from "@/features/shared/placeholder-page"
import { SourcesPage } from "@/features/sources/sources-page"

const EventsPage = lazy(() =>
  import("@/features/events/events-page").then((module) => ({
    default: module.EventsPage,
  }))
)
const ActorsPage = lazy(() =>
  import("@/features/actors/actors-page").then((module) => ({
    default: module.ActorsPage,
  }))
)
const ReviewsPage = lazy(() =>
  import("@/features/reviews/reviews-page").then((module) => ({
    default: module.ReviewsPage,
  }))
)

function PageFallback() {
  return (
    <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
      正在加载工作台…
    </div>
  )
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
})

const placeholderRoutes = [
  ["/campaigns", "Campaign", "Campaign 时间线将在事件聚类能力完成后接入。"],
  ["/hunt", "IOC 狩猎", "Observable 检索与富化将在 M3 阶段接入。"],
  ["/watch-rules", "关注规则", "关注条件和命中预览将在 M4 阶段接入。"],
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
              <Route path="/sources" element={<SourcesPage />} />
              <Route
                path="/reviews"
                element={
                  <Suspense fallback={<PageFallback />}>
                    <ReviewsPage />
                  </Suspense>
                }
              />
              <Route
                path="/events"
                element={
                  <Suspense fallback={<PageFallback />}>
                    <EventsPage />
                  </Suspense>
                }
              />
              <Route
                path="/actors"
                element={
                  <Suspense fallback={<PageFallback />}>
                    <ActorsPage />
                  </Suspense>
                }
              />
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
        <Toaster position="top-right" richColors />
      </TooltipProvider>
    </QueryClientProvider>
  )
}

export default App
