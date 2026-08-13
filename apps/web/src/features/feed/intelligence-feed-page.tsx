import { useQuery } from "@tanstack/react-query"
import {
  AlertCircleIcon,
  Clock3Icon,
  ExternalLinkIcon,
  FileSearchIcon,
  FileTextIcon,
  InfoIcon,
  SlidersHorizontalIcon,
} from "lucide-react"
import { useState } from "react"
import { Link } from "react-router-dom"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { Separator } from "@/components/ui/separator"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import {
  getReport,
  listReports,
  reportQueryKey,
} from "@/features/intelligence/intelligence-api"
import {
  extractionLabel,
  formatRelativeTime,
  sourceInitials,
} from "@/features/intelligence/intelligence-format"
import type {
  DiamondEntity,
  ReportDetail,
  ReportSummary,
} from "@/features/intelligence/intelligence-types"
import { cn } from "@/lib/utils"

function relevanceVariant(score: number) {
  if (score >= 90) return "relevance" as const
  if (score >= 70) return "candidate" as const
  return "confirmed" as const
}

function analysisVariant(status: string | null) {
  if (status === "ready") return "confirmed" as const
  if (status === "failed") return "destructive" as const
  return "secondary" as const
}

function Metric({
  icon: Icon,
  label,
  value,
  note,
}: {
  icon: typeof FileTextIcon
  label: string
  value: number
  note: string
}) {
  return (
    <div className="flex min-w-0 items-center gap-3 border-r border-border px-4 py-4 last:border-r-0 sm:px-6">
      <span className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-border bg-card text-muted-foreground">
        <Icon aria-hidden="true" />
      </span>
      <span className="min-w-0">
        <span className="flex items-baseline gap-2">
          <strong className="text-2xl font-semibold tracking-tight">
            {value}
          </strong>
          <span className="truncate text-sm font-medium">{label}</span>
        </span>
        <span className="block truncate text-xs text-muted-foreground">
          {note}
        </span>
      </span>
    </div>
  )
}

function FeedRow({
  report,
  selected,
  onSelect,
}: {
  report: ReportSummary
  selected: boolean
  onSelect: (reportId: string) => void
}) {
  return (
    <button
      aria-controls={selected ? "intelligence-inspector" : undefined}
      aria-expanded={selected}
      aria-haspopup="dialog"
      className={cn(
        "relative grid w-full grid-cols-[2.75rem_minmax(0,1fr)] items-center gap-3 border-b border-border px-4 py-4 text-left transition-colors last:border-b-0 hover:bg-accent/40 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none lg:grid-cols-[2.75rem_minmax(0,1fr)_11rem]",
        selected &&
          "bg-accent/65 before:absolute before:inset-y-3 before:left-0 before:w-0.5 before:rounded-full before:bg-foreground"
      )}
      onClick={() => onSelect(report.id)}
      type="button"
    >
      <span className="flex size-10 items-center justify-center rounded-lg border border-border bg-background text-muted-foreground">
        <FileSearchIcon aria-hidden="true" />
      </span>
      <span className="flex min-w-0 flex-col gap-2">
        <span className="line-clamp-2 text-sm font-medium sm:text-base">
          {report.title}
        </span>
        <span className="flex flex-wrap items-center gap-1.5">
          <Badge variant={relevanceVariant(report.relevance_score)}>
            相关性 {report.relevance_score}
          </Badge>
          <Badge variant={analysisVariant(report.extraction_status)}>
            {extractionLabel(report.extraction_status)}
          </Badge>
          {report.review_status === "approved" && (
            <Badge variant="confirmed">已确认</Badge>
          )}
        </span>
        <span className="line-clamp-1 text-xs text-muted-foreground sm:text-sm">
          {report.relevance_reasons.join(" · ") || report.summary || "暂无摘要"}
        </span>
      </span>
      <span className="col-start-2 flex min-w-0 items-start gap-2.5 self-start pt-1 lg:col-start-auto">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-secondary text-[0.65rem] font-semibold">
          {sourceInitials(report.source_name)}
        </span>
        <span className="flex min-w-0 flex-col gap-0.5">
          <span className="truncate text-xs font-medium">
            {report.source_name}
          </span>
          <span className="text-xs text-muted-foreground">
            {formatRelativeTime(report.published_at)}
          </span>
        </span>
      </span>
    </button>
  )
}

function EntityPreview({
  label,
  items,
}: {
  label: string
  items: DiamondEntity[]
}) {
  return (
    <div className="min-w-0 rounded-lg border border-border bg-background p-3">
      <span className="text-[0.65rem] font-medium tracking-wide text-muted-foreground uppercase">
        {label}
      </span>
      <p className="mt-1 truncate text-sm font-medium">
        {items[0]?.name ?? "未提取到"}
      </p>
    </div>
  )
}

function EventInspector({
  open,
  report,
  onOpenChange,
}: {
  open: boolean
  report: ReportDetail | undefined
  onOpenChange: (open: boolean) => void
}) {
  const analysis = report?.analysis
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        aria-describedby="intelligence-inspector-description"
        className="w-full gap-0 overflow-hidden sm:w-[42rem] sm:max-w-[calc(100vw-2rem)]"
        id="intelligence-inspector"
        side="right"
      >
        <SheetHeader className="shrink-0 px-4 py-4 pr-12 sm:px-6">
          <p className="workspace-kicker">Inspector</p>
          <SheetTitle>材料速览</SheetTitle>
          <SheetDescription id="intelligence-inspector-description">
            自动提取仅供研判，审核后生效
          </SheetDescription>
        </SheetHeader>
        <Separator />
        {!report ? (
          <div
            aria-label="材料速览内容"
            className="flex min-h-0 flex-1 flex-col gap-4 overflow-x-hidden overflow-y-auto overscroll-contain p-5"
            role="region"
          >
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-28 w-full" />
            <Skeleton className="h-44 w-full" />
          </div>
        ) : (
          <div
            aria-label="材料速览内容"
            className="flex min-h-0 flex-1 flex-col gap-5 overflow-x-hidden overflow-y-auto overscroll-contain p-5 break-words sm:p-6"
            role="region"
          >
            <div>
              <h3 className="text-base leading-6 font-semibold">
                {report.title}
              </h3>
              <div className="mt-3 flex flex-wrap gap-1.5">
                <Badge variant={relevanceVariant(report.relevance_score)}>
                  相关性 {report.relevance_score}
                </Badge>
                <Badge variant={analysisVariant(report.extraction_status)}>
                  {extractionLabel(report.extraction_status)}
                </Badge>
                {analysis?.confidence_auto !== null &&
                  analysis?.confidence_auto !== undefined && (
                    <Badge variant="outline">
                      置信度 {analysis.confidence_auto}
                    </Badge>
                  )}
              </div>
            </div>
            <section className="flex flex-col gap-2">
              <h4 className="text-sm font-medium">材料摘要</h4>
              <p className="text-sm leading-6 whitespace-pre-line text-muted-foreground">
                {analysis?.content_text ||
                  report.summary ||
                  "正文仍在等待提取。"}
              </p>
            </section>
            <section className="flex flex-col gap-3">
              <h4 className="text-sm font-medium">威胁钻石模型</h4>
              {analysis?.extraction_status === "ready" ? (
                <div className="grid grid-cols-2 gap-2">
                  <EntityPreview label="攻击者" items={analysis.actors} />
                  <EntityPreview label="能力" items={analysis.capabilities} />
                  <EntityPreview
                    label="基础设施"
                    items={analysis.infrastructure}
                  />
                  <EntityPreview label="受害者" items={analysis.victims} />
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {analysis?.extraction_error || "富化任务尚未完成。"}
                </p>
              )}
            </section>
            <Separator />
            <section className="flex flex-col gap-3">
              <h4 className="text-sm font-medium">可追溯证据</h4>
              {analysis?.evidence.length ? (
                <ul className="flex flex-col gap-2 text-sm text-muted-foreground">
                  {analysis.evidence.map((item, index) => (
                    <li key={`${item.entity}-${index}`}>
                      <span className="font-medium text-foreground">
                        {item.entity}
                      </span>{" "}
                      · {item.quote}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted-foreground">
                  暂无字段级证据。
                </p>
              )}
            </section>
          </div>
        )}
        {report ? (
          <>
            <Separator />
            <SheetFooter className="shrink-0 p-4 sm:flex-row sm:px-6">
              <Button asChild>
                <Link to="/reviews">进入人工复核</Link>
              </Button>
              <Button asChild variant="outline">
                <a href={report.canonical_url} rel="noreferrer" target="_blank">
                  <ExternalLinkIcon data-icon="inline-start" />
                  打开原文
                </a>
              </Button>
            </SheetFooter>
          </>
        ) : null}
      </SheetContent>
    </Sheet>
  )
}

export function IntelligenceFeedPage() {
  const [filter, setFilter] = useState("all")
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [inspectorOpen, setInspectorOpen] = useState(false)
  const reportsQuery = useQuery({
    queryKey: reportQueryKey,
    queryFn: listReports,
  })
  const reports = (reportsQuery.data ?? []).filter(
    (report) => report.status !== "filtered"
  )
  const visibleReports = reports.filter((report) => {
    if (filter === "high") return report.relevance_score >= 80
    if (filter === "pending") return report.review_status === "pending"
    return true
  })
  const selected = visibleReports.find((report) => report.id === selectedId)
  const detailQuery = useQuery({
    queryKey: ["report", selected?.id],
    queryFn: () => getReport(selected!.id),
    enabled: Boolean(selected),
    refetchInterval: (query) =>
      ["queued", "processing"].includes(
        query.state.data?.extraction_status ?? ""
      )
        ? 3_000
        : false,
  })

  const metrics = [
    {
      icon: FileTextIcon,
      label: "采集材料",
      value: reports.length,
      note: "当前情报库",
    },
    {
      icon: AlertCircleIcon,
      label: "高相关",
      value: reports.filter((item) => item.relevance_score >= 80).length,
      note: "相关性 ≥ 80",
    },
    {
      icon: Clock3Icon,
      label: "待审核",
      value: reports.filter((item) => item.review_status === "pending").length,
      note: "等待人工确认",
    },
    {
      icon: InfoIcon,
      label: "提取异常",
      value: reports.filter((item) => item.extraction_status === "failed")
        .length,
      note: "可重新富化",
    },
  ]

  return (
    <div
      className="flex min-h-0 flex-1 flex-col overflow-hidden"
      data-testid="intelligence-feed-workspace"
    >
      <section className="grid shrink-0 grid-cols-2 border-b border-border bg-surface lg:grid-cols-4">
        {metrics.map((metric) => (
          <Metric key={metric.label} {...metric} />
        ))}
      </section>
      <div className="flex min-h-0 flex-1 overflow-hidden">
        <main className="mx-auto flex min-h-0 w-full max-w-[90rem] min-w-0 flex-1 flex-col overflow-hidden p-4 sm:p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-4">
              <div>
                <p className="workspace-kicker">Live intelligence</p>
                <h2 className="mt-1 text-lg font-semibold">APT 候选材料</h2>
              </div>
              <ToggleGroup
                type="single"
                value={filter}
                variant="outline"
                spacing={0}
                onValueChange={(value) => {
                  if (value) {
                    setFilter(value)
                    setSelectedId(null)
                    setInspectorOpen(false)
                  }
                }}
              >
                <ToggleGroupItem value="all">全部</ToggleGroupItem>
                <ToggleGroupItem value="high">高相关</ToggleGroupItem>
                <ToggleGroupItem value="pending">待审核</ToggleGroupItem>
              </ToggleGroup>
            </div>
            <Button variant="outline">
              <SlidersHorizontalIcon data-icon="inline-start" />
              最新优先
            </Button>
          </div>
          <div
            aria-label="情报列表"
            className="min-h-0 flex-1 overflow-y-auto overscroll-contain rounded-xl border border-border bg-card"
            role="region"
          >
            {reportsQuery.isPending ? (
              <div className="space-y-3 p-4">
                {[0, 1, 2].map((item) => (
                  <Skeleton className="h-24 w-full" key={item} />
                ))}
              </div>
            ) : reportsQuery.isError ? (
              <Empty className="min-h-72 border-0">
                <EmptyHeader>
                  <EmptyMedia variant="icon">
                    <AlertCircleIcon />
                  </EmptyMedia>
                  <EmptyTitle>情报材料加载失败</EmptyTitle>
                  <EmptyDescription>
                    {reportsQuery.error.message}
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            ) : visibleReports.length === 0 ? (
              <Empty className="min-h-72 border-0">
                <EmptyHeader>
                  <EmptyMedia variant="icon">
                    <FileSearchIcon />
                  </EmptyMedia>
                  <EmptyTitle>当前筛选下没有材料</EmptyTitle>
                  <EmptyDescription>
                    RSS 候选文章会在采集后自动出现在这里。
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            ) : (
              visibleReports.map((report) => (
                <FeedRow
                  key={report.id}
                  report={report}
                  selected={inspectorOpen && selected?.id === report.id}
                  onSelect={(reportId) => {
                    setSelectedId(reportId)
                    setInspectorOpen(true)
                  }}
                />
              ))
            )}
          </div>
        </main>
      </div>
      <EventInspector
        open={inspectorOpen}
        report={detailQuery.data}
        onOpenChange={(open) => {
          setInspectorOpen(open)
          if (!open) setSelectedId(null)
        }}
      />
    </div>
  )
}
