import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { lazy, Suspense } from "react"
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"

import { AppShell } from "@/app/app-shell"
import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import { IntelligenceFeedPage } from "@/features/feed/intelligence-feed-page"
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
const HuntPage = lazy(() =>
  import("@/features/hunt/hunt-page").then((module) => ({
    default: module.HuntPage,
  }))
)
const CampaignsPage = lazy(() =>
  import("@/features/campaigns/campaigns-page").then((module) => ({
    default: module.CampaignsPage,
  }))
)
const WatchRulesPage = lazy(() =>
  import("@/features/watch-rules/watch-rules-page").then((module) => ({
    default: module.WatchRulesPage,
  }))
)
const OperationsPage = lazy(() =>
  import("@/features/operations/operations-page").then((module) => ({
    default: module.OperationsPage,
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
              <Route
                path="/hunt"
                element={
                  <Suspense fallback={<PageFallback />}>
                    <HuntPage />
                  </Suspense>
                }
              />
              <Route
                path="/campaigns"
                element={
                  <Suspense fallback={<PageFallback />}>
                    <CampaignsPage />
                  </Suspense>
                }
              />
              <Route
                path="/watch-rules"
                element={
                  <Suspense fallback={<PageFallback />}>
                    <WatchRulesPage />
                  </Suspense>
                }
              />
              <Route
                path="/operations"
                element={
                  <Suspense fallback={<PageFallback />}>
                    <OperationsPage />
                  </Suspense>
                }
              />
            </Route>
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" richColors />
      </TooltipProvider>
    </QueryClientProvider>
  )
}

export default App
