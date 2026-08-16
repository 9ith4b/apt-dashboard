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
  getReportCollectionSummary,
  listReports,
  reportQueryKey,
  reportSummaryQueryKey,
} from "@/features/intelligence/intelligence-api"
import {
  extractionLabel,
  formatRelativeTime,
  sourceInitials,
} from "@/features/intelligence/intelligence-format"
import type {
  DiamondEntity,
  ReportDetail,
  ReportScope,
  ReportSummary,
} from "@/features/intelligence/intelligence-types"
import { cn } from "@/lib/utils"

function relevanceVariant(score: number) {
  if (score >= 90) return "relevance" as const
  if (score >= 70) return "candidate" as const
  return "confirmed" as const
}

const classificationLabels: Record<string, string> = {
  apt_event: "APT事件",
  actor_research: "组织研究",
  malware_analysis: "恶意软件",
  vulnerability_activity: "漏洞动态",
  security_news: "安全新闻",
  irrelevant: "非APT",
}

const viewLabels: Record<ReportScope, string> = {
  apt: "APT 情报",
  raw: "原始材料",
  excluded: "AI 已排除",
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
  const relevanceScore = report.ai_relevance_score ?? report.relevance_score
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
          <Badge variant={relevanceVariant(relevanceScore)}>
            APT相关性 {relevanceScore}
          </Badge>
          <Badge variant={analysisVariant(report.extraction_status)}>
            {extractionLabel(report.extraction_status)}
          </Badge>
          {report.review_status === "approved" && (
            <Badge variant="confirmed">已确认</Badge>
          )}
          {report.ai_classification && (
            <Badge variant="outline">
              {classificationLabels[report.ai_classification] ??
                report.ai_classification}
            </Badge>
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
  const relevanceScore = report
    ? (report.ai_relevance_score ?? report.relevance_score)
    : 0
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
                <Badge variant={relevanceVariant(relevanceScore)}>
                  APT相关性 {relevanceScore}
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
                {report.ai_classification && (
                  <Badge variant="outline">
                    {classificationLabels[report.ai_classification] ??
                      report.ai_classification}
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
                <Link
                  to={`/reviews?report=${encodeURIComponent(report.id)}&status=${encodeURIComponent(report.review_status ?? "pending")}`}
                >
                  查看AI分析
                </Link>
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
  const [scope, setScope] = useState<ReportScope>("apt")
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [inspectorOpen, setInspectorOpen] = useState(false)
  const reportsQuery = useQuery({
    queryKey: [...reportQueryKey, scope],
    queryFn: () => listReports(scope),
  })
  const summaryQuery = useQuery({
    queryKey: reportSummaryQueryKey,
    queryFn: getReportCollectionSummary,
  })
  const reports = reportsQuery.data ?? []
  const selected = reports.find((report) => report.id === selectedId)
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

  const summary = summaryQuery.data
  const metrics = [
    {
      icon: FileTextIcon,
      label: "APT 情报",
      value: summary?.apt ?? 0,
      note: "严格门禁后确认",
    },
    {
      icon: Clock3Icon,
      label: "待处理",
      value: summary?.pending ?? 0,
      note: "未进入APT知识库",
    },
    {
      icon: InfoIcon,
      label: "AI 排除",
      value: summary?.excluded ?? 0,
      note: "非APT或低置信度",
    },
    {
      icon: AlertCircleIcon,
      label: "提取异常",
      value: summary?.extraction_failed ?? 0,
      note: "等待自动重试",
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
                <h2 className="mt-1 text-lg font-semibold">
                  {viewLabels[scope]}
                </h2>
              </div>
              <ToggleGroup
                aria-label="切换情报材料视图"
                type="single"
                value={scope}
                variant="outline"
                spacing={0}
                onValueChange={(value) => {
                  if (value) {
                    setScope(value as ReportScope)
                    setSelectedId(null)
                    setInspectorOpen(false)
                  }
                }}
              >
                <ToggleGroupItem value="apt">
                  APT 情报 {summary?.apt ?? 0}
                </ToggleGroupItem>
                <ToggleGroupItem value="raw">
                  原始材料 {summary?.total ?? 0}
                </ToggleGroupItem>
                <ToggleGroupItem value="excluded">
                  AI 已排除 {summary?.excluded ?? 0}
                </ToggleGroupItem>
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
            ) : reports.length === 0 ? (
              <Empty className="min-h-72 border-0">
                <EmptyHeader>
                  <EmptyMedia variant="icon">
                    <FileSearchIcon />
                  </EmptyMedia>
                  <EmptyTitle>当前视图没有材料</EmptyTitle>
                  <EmptyDescription>
                    {scope === "apt"
                      ? "材料通过严格的APT语义、证据和验证门禁后会出现在这里。"
                      : "RSS文章会在采集后自动进入原始材料层。"}
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            ) : (
              reports.map((report) => (
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
