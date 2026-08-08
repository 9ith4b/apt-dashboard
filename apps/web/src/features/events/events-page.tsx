import { useQuery } from "@tanstack/react-query"
import {
  ActivityIcon,
  AlertCircleIcon,
  Building2Icon,
  ExternalLinkIcon,
  FileCheck2Icon,
  GitBranchIcon,
  NetworkIcon,
  ShieldCheckIcon,
  TargetIcon,
  ZapIcon,
} from "lucide-react"
import { useState } from "react"
import { Link } from "react-router-dom"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import {
  eventQueryKey,
  getThreatEvent,
  listThreatEvents,
} from "@/features/intelligence/intelligence-api"
import { formatDateTime } from "@/features/intelligence/intelligence-format"
import type {
  DiamondEntity,
  ThreatEventDetail,
  ThreatEventSummary,
} from "@/features/intelligence/intelligence-types"
import { cn } from "@/lib/utils"

function EventRow({
  event,
  selected,
  onSelect,
}: {
  event: ThreatEventSummary
  selected: boolean
  onSelect: (eventId: string) => void
}) {
  return (
    <button
      className={cn(
        "w-full border-b border-border p-4 text-left transition-colors last:border-b-0 hover:bg-accent/40 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
        selected && "bg-accent/55 ring-1 ring-primary ring-inset"
      )}
      onClick={() => onSelect(event.id)}
      type="button"
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <Badge variant="confirmed">已确认</Badge>
        <span className="text-xs text-muted-foreground">
          {event.confidence_analyst ?? event.confidence_auto ?? "—"}%
        </span>
      </div>
      <h3 className="line-clamp-2 text-sm leading-6 font-medium">
        {event.title}
      </h3>
      <p className="mt-2 truncate text-xs text-primary">
        {event.actor_names.join(" · ") || "未归因"}
      </p>
      <div className="mt-3 flex items-center justify-between gap-3 text-xs text-muted-foreground">
        <span>{event.report_count} 篇证据材料</span>
        <span>{formatDateTime(event.first_seen)}</span>
      </div>
    </button>
  )
}

function DiamondPanel({
  title,
  description,
  icon: Icon,
  entities,
}: {
  title: string
  description: string
  icon: typeof TargetIcon
  entities: DiamondEntity[]
}) {
  return (
    <Card className="min-w-0 gap-3 py-4">
      <CardHeader className="px-4">
        <div className="flex items-start gap-3">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/12 text-primary">
            <Icon aria-hidden="true" />
          </span>
          <div>
            <CardTitle className="text-sm">{title}</CardTitle>
            <CardDescription>{description}</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-2 px-4">
        {entities.length ? (
          entities.slice(0, 8).map((entity) => (
            <div
              className="rounded-md border border-border bg-background/45 p-3"
              key={`${entity.type}-${entity.name}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="min-w-0 truncate text-sm font-medium">
                  {entity.name}
                </span>
                <Badge variant="outline">{entity.confidence}%</Badge>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {entity.type}
              </p>
              {entity.evidence && (
                <p className="mt-2 line-clamp-3 text-xs leading-5 text-muted-foreground">
                  {entity.evidence}
                </p>
              )}
            </div>
          ))
        ) : (
          <p className="rounded-md border border-dashed border-border p-3 text-sm text-muted-foreground">
            当前事件未确认该维度实体。
          </p>
        )}
      </CardContent>
    </Card>
  )
}

function EventDetail({ event }: { event: ThreatEventDetail }) {
  return (
    <div className="flex-1 space-y-6 overflow-y-auto p-4 sm:p-6">
      <div className="flex flex-col justify-between gap-4 xl:flex-row xl:items-start">
        <div className="max-w-4xl">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <Badge variant="confirmed">
              <ShieldCheckIcon data-icon="inline-start" />
              已确认事件
            </Badge>
            <Badge variant="outline">
              人工置信度 {event.confidence_analyst ?? "—"}
            </Badge>
            <Badge variant="secondary">{event.report_count} 篇证据</Badge>
          </div>
          <h2 className="text-xl leading-8 font-semibold sm:text-2xl">
            {event.title}
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            首次观测 {formatDateTime(event.first_seen)} · 最近更新{" "}
            {formatDateTime(event.updated_at)}
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>事件摘要</CardTitle>
          <CardDescription>
            由已通过人工审核的材料及字段快照生成。
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-7 text-muted-foreground">
            {event.summary || "暂无事件摘要。"}
          </p>
        </CardContent>
      </Card>

      <section>
        <div className="mb-3">
          <h3 className="font-semibold">事件钻石模型</h3>
          <p className="text-sm text-muted-foreground">
            展示审核后的最终实体，不混入被分析员排除的自动结果。
          </p>
        </div>
        <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-4">
          <DiamondPanel
            title="对手"
            description="归因组织与别名"
            icon={TargetIcon}
            entities={event.diamond.actors}
          />
          <DiamondPanel
            title="能力"
            description="战术、技术与工具"
            icon={ZapIcon}
            entities={event.diamond.capabilities}
          />
          <DiamondPanel
            title="基础设施"
            description="域名、IP 与 URL"
            icon={NetworkIcon}
            entities={event.diamond.infrastructure}
          />
          <DiamondPanel
            title="受害者"
            description="行业、角色与区域"
            icon={Building2Icon}
            entities={event.diamond.victims}
          />
        </div>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>证据材料</CardTitle>
          <CardDescription>
            保留来源、发布时间与审核置信度，可回到原文继续研判。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {event.reports.map((report) => (
            <div
              className="flex flex-col justify-between gap-3 rounded-lg border border-border p-4 sm:flex-row sm:items-center"
              key={report.id}
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="secondary">{report.source_name}</Badge>
                  <span className="text-xs text-muted-foreground">
                    {formatDateTime(report.published_at)}
                  </span>
                </div>
                <p className="mt-2 line-clamp-2 text-sm font-medium">
                  {report.title}
                </p>
              </div>
              <Button asChild size="sm" variant="outline">
                <a href={report.canonical_url} rel="noreferrer" target="_blank">
                  <ExternalLinkIcon data-icon="inline-start" />
                  原文
                </a>
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

export function EventsPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const eventsQuery = useQuery({
    queryKey: eventQueryKey,
    queryFn: listThreatEvents,
  })
  const events = eventsQuery.data ?? []
  const selected = events.find((event) => event.id === selectedId) ?? events[0]
  const detailQuery = useQuery({
    queryKey: ["event", selected?.id],
    queryFn: () => getThreatEvent(selected!.id),
    enabled: Boolean(selected),
  })
  const totalReports = events.reduce(
    (total, event) => total + event.report_count,
    0
  )
  const attributed = events.filter(
    (event) => event.actor_names.length > 0
  ).length

  if (eventsQuery.isPending) {
    return (
      <div className="flex-1 space-y-5 p-6">
        <Skeleton className="h-24" />
        <div className="grid gap-4 lg:grid-cols-[22rem_minmax(0,1fr)]">
          <Skeleton className="h-[34rem]" />
          <Skeleton className="h-[34rem]" />
        </div>
      </div>
    )
  }

  if (eventsQuery.isError) {
    return (
      <Empty className="border-0">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <AlertCircleIcon />
          </EmptyMedia>
          <EmptyTitle>威胁事件加载失败</EmptyTitle>
          <EmptyDescription>{eventsQuery.error.message}</EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }

  if (!events.length) {
    return (
      <Empty className="border-0">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <GitBranchIcon />
          </EmptyMedia>
          <EmptyTitle>还没有已确认的威胁事件</EmptyTitle>
          <EmptyDescription>
            在人工复核队列中修正钻石模型字段并通过审核，系统会在这里生成事件。
          </EmptyDescription>
        </EmptyHeader>
        <Button asChild>
          <Link to="/reviews">
            <FileCheck2Icon data-icon="inline-start" />
            前往人工复核
          </Link>
        </Button>
      </Empty>
    )
  }

  return (
    <div className="grid min-h-0 flex-1 grid-rows-[auto_minmax(0,1fr)]">
      <header className="border-b border-border bg-card px-4 py-4 sm:px-6">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
          <div>
            <h1 className="text-xl font-semibold">威胁事件</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              由人工确认的情报材料持续沉淀而成
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <span className="flex items-center gap-2 text-muted-foreground">
              <ShieldCheckIcon className="size-4 text-confirmed" />
              {events.length} 个已确认事件
            </span>
            <Separator className="hidden h-4 sm:block" orientation="vertical" />
            <span className="flex items-center gap-2 text-muted-foreground">
              <ActivityIcon className="size-4 text-primary" />
              {totalReports} 篇证据 · {attributed} 个已归因
            </span>
          </div>
        </div>
      </header>
      <div className="grid min-h-0 lg:grid-cols-[22rem_minmax(0,1fr)]">
        <aside className="max-h-80 overflow-y-auto border-b border-border bg-card lg:max-h-none lg:border-r lg:border-b-0">
          {events.map((event) => (
            <EventRow
              event={event}
              key={event.id}
              onSelect={setSelectedId}
              selected={selected?.id === event.id}
            />
          ))}
        </aside>
        <main className="flex min-h-0 min-w-0 flex-col">
          {detailQuery.isPending ? (
            <div className="space-y-5 p-6">
              <Skeleton className="h-20 w-3/4" />
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                {[0, 1, 2, 3].map((item) => (
                  <Skeleton className="h-48" key={item} />
                ))}
              </div>
              <Skeleton className="h-56" />
            </div>
          ) : detailQuery.isError || !detailQuery.data ? (
            <Empty className="border-0">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <AlertCircleIcon />
                </EmptyMedia>
                <EmptyTitle>事件详情加载失败</EmptyTitle>
                <EmptyDescription>
                  {detailQuery.error?.message}
                </EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : (
            <EventDetail event={detailQuery.data} />
          )}
        </main>
      </div>
    </div>
  )
}
