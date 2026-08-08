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
    <div className="flex min-w-0 items-center gap-4 border-r border-border px-5 py-5 last:border-r-0 sm:px-7">
      <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-secondary text-primary">
        <Icon aria-hidden="true" />
      </span>
      <span className="min-w-0">
        <span className="flex items-baseline gap-2">
          <strong className="text-2xl font-semibold text-primary">
            {value}
          </strong>
          <span className="truncate font-medium">{label}</span>
        </span>
        <span className="text-sm text-muted-foreground">{note}</span>
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
      className={cn(
        "grid w-full grid-cols-[3rem_minmax(0,1fr)] items-center gap-3 border-b border-border px-4 py-4 text-left transition-colors last:border-b-0 hover:bg-accent/40 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none lg:grid-cols-[3rem_minmax(0,1fr)_12rem]",
        selected && "bg-accent/55 ring-1 ring-primary ring-inset"
      )}
      onClick={() => onSelect(report.id)}
      type="button"
    >
      <span className="flex size-11 items-center justify-center rounded-xl bg-secondary text-primary">
        <FileSearchIcon aria-hidden="true" />
      </span>
      <span className="flex min-w-0 flex-col gap-2">
        <span className="line-clamp-2 text-base font-medium">
          {report.title}
        </span>
        <span className="flex flex-wrap items-center gap-2">
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
        <span className="line-clamp-1 text-sm text-muted-foreground">
          {report.relevance_reasons.join(" · ") || report.summary || "暂无摘要"}
        </span>
      </span>
      <span className="col-start-2 flex min-w-0 items-start gap-3 self-start pt-1 lg:col-start-auto">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-secondary text-xs font-semibold">
          {sourceInitials(report.source_name)}
        </span>
        <span className="flex min-w-0 flex-col gap-1">
          <span className="truncate text-sm">{report.source_name}</span>
          <span className="text-sm text-muted-foreground">
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
    <div className="min-w-0 rounded-lg border border-border bg-background/45 p-3">
      <span className="text-xs font-medium text-primary">{label}</span>
      <p className="mt-1 truncate text-sm text-muted-foreground">
        {items[0]?.name ?? "未提取到"}
      </p>
    </div>
  )
}

function EventInspector({ report }: { report: ReportDetail | undefined }) {
  const analysis = report?.analysis
  return (
    <aside className="hidden min-w-0 border-l border-border bg-card xl:flex xl:flex-col">
      <div className="px-5 py-4">
        <h2 className="text-lg font-semibold">材料速览</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          自动提取结果仅供研判，审核后生效
        </p>
      </div>
      <Separator />
      {!report ? (
        <div className="space-y-4 p-5">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-44 w-full" />
        </div>
      ) : (
        <div className="flex flex-1 flex-col gap-5 overflow-y-auto p-5">
          <div>
            <h3 className="text-lg leading-7 font-semibold">{report.title}</h3>
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge variant={relevanceVariant(report.relevance_score)}>
                相关性 {report.relevance_score}
              </Badge>
              <Badge variant={analysisVariant(report.extraction_status)}>
                {extractionLabel(report.extraction_status)}
              </Badge>
              {analysis?.confidence_auto !== null &&
                analysis?.confidence_auto !== undefined && (
                  <Badge variant="outline">
                    提取置信度 {analysis.confidence_auto}
                  </Badge>
                )}
            </div>
          </div>
          <section className="space-y-2">
            <h4 className="font-medium">材料摘要</h4>
            <p className="line-clamp-6 text-sm leading-6 text-muted-foreground">
              {analysis?.content_text || report.summary || "正文仍在等待提取。"}
            </p>
          </section>
          <section className="space-y-3">
            <h4 className="font-medium">威胁钻石模型</h4>
            {analysis?.extraction_status === "ready" ? (
              <div className="grid grid-cols-2 gap-2">
                <EntityPreview label="对手" items={analysis.actors} />
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
          <section className="space-y-3">
            <h4 className="font-medium">可追溯证据</h4>
            {analysis?.evidence.length ? (
              <ul className="space-y-2 text-sm text-muted-foreground">
                {analysis.evidence.slice(0, 4).map((item, index) => (
                  <li className="line-clamp-2" key={`${item.entity}-${index}`}>
                    <span className="text-foreground">{item.entity}</span> ·{" "}
                    {item.quote}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">暂无字段级证据。</p>
            )}
          </section>
          <div className="mt-auto grid gap-2">
            <Button asChild>
              <Link to="/reviews">进入人工复核</Link>
            </Button>
            <Button asChild variant="outline">
              <a href={report.canonical_url} rel="noreferrer" target="_blank">
                <ExternalLinkIcon data-icon="inline-start" />
                打开原文
              </a>
            </Button>
          </div>
        </div>
      )}
    </aside>
  )
}

export function IntelligenceFeedPage() {
  const [filter, setFilter] = useState("all")
  const [selectedId, setSelectedId] = useState<string | null>(null)
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
  const selected =
    visibleReports.find((report) => report.id === selectedId) ??
    visibleReports[0]
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
    <div className="flex min-h-0 flex-1 flex-col">
      <section className="grid shrink-0 grid-cols-2 border-b border-border lg:grid-cols-4">
        {metrics.map((metric) => (
          <Metric key={metric.label} {...metric} />
        ))}
      </section>
      <div className="grid min-h-0 flex-1 grid-cols-1 xl:grid-cols-[minmax(0,1fr)_26rem]">
        <main className="flex min-w-0 flex-col px-4 py-4 sm:px-5">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-4">
              <h2 className="text-lg font-semibold">APT 候选材料</h2>
              <ToggleGroup
                type="single"
                value={filter}
                variant="outline"
                spacing={0}
                onValueChange={(value) => {
                  if (value) setFilter(value)
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
          <div className="min-h-0 overflow-y-auto rounded-lg border border-border bg-card">
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
                  selected={selected?.id === report.id}
                  onSelect={setSelectedId}
                />
              ))
            )}
          </div>
        </main>
        <EventInspector report={detailQuery.data} />
      </div>
    </div>
  )
}
