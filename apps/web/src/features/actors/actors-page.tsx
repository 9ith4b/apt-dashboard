import { useMutation, useQuery } from "@tanstack/react-query"
import {
  ActivityIcon,
  AlertCircleIcon,
  CalendarDaysIcon,
  Clock3Icon,
  FileCheck2Icon,
  FlagIcon,
  ShieldUserIcon,
  TagsIcon,
  TargetIcon,
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
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { ActorTrackingPanel } from "@/features/actors/actor-tracking-panel"
import {
  actorTrackingExportUrl,
  actorTrackingQueryKey,
  actorQueryKey,
  generateActorTrackingSummary,
  getActorTracking,
  getThreatActor,
  listThreatActors,
} from "@/features/intelligence/intelligence-api"
import { formatDateTime } from "@/features/intelligence/intelligence-format"
import type {
  ThreatActorDetail,
  ThreatActorSummary,
} from "@/features/intelligence/intelligence-types"
import { cn } from "@/lib/utils"

type RangePreset =
  "custom" | "month" | "three_months" | "six_months" | "year" | "all"

function isoDate(value: Date) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, "0")
  const day = String(value.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}

function presetRange(
  preset: RangePreset,
  customFrom: string,
  customTo: string
): { dateFrom?: string; dateTo?: string } {
  const today = new Date()
  if (preset === "all") return {}
  if (preset === "custom") return { dateFrom: customFrom, dateTo: customTo }
  const start =
    preset === "month"
      ? new Date(today.getFullYear(), today.getMonth(), 1)
      : preset === "three_months"
        ? new Date(today.getFullYear(), today.getMonth() - 2, 1)
        : preset === "six_months"
          ? new Date(today.getFullYear(), today.getMonth() - 5, 1)
          : new Date(today.getFullYear(), 0, 1)
  return { dateFrom: isoDate(start), dateTo: isoDate(today) }
}

function ActorRow({
  actor,
  selected,
  onSelect,
}: {
  actor: ThreatActorSummary
  selected: boolean
  onSelect: (actorId: string) => void
}) {
  return (
    <button
      className={cn(
        "w-full border-b border-border p-4 text-left transition-colors last:border-b-0 hover:bg-accent/40 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
        selected && "bg-accent/55 ring-1 ring-primary ring-inset"
      )}
      onClick={() => onSelect(actor.id)}
      type="button"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold">
            {actor.canonical_name}
          </h3>
          <p className="mt-1 truncate text-xs text-primary">
            {actor.aliases.slice(0, 3).join(" · ") || "暂无别名"}
          </p>
        </div>
        <Badge variant="secondary">{actor.event_count} 起</Badge>
      </div>
      <p className="mt-3 line-clamp-2 text-xs leading-5 text-muted-foreground">
        {actor.latest_event_title || "所选时间内暂无事件标题"}
      </p>
      <div className="mt-3 flex items-center justify-between gap-3 text-xs text-muted-foreground">
        <span>{actor.origin_country || "来源未知"}</span>
        <span>{formatDateTime(actor.last_seen)}</span>
      </div>
    </button>
  )
}

function MetricCard({
  title,
  value,
  description,
  icon: Icon,
}: {
  title: string
  value: string
  description: string
  icon: typeof ActivityIcon
}) {
  return (
    <Card className="gap-3 py-4">
      <CardHeader className="flex-row items-start justify-between px-4">
        <div>
          <CardDescription>{title}</CardDescription>
          <CardTitle className="mt-1 text-2xl">{value}</CardTitle>
        </div>
        <span className="flex size-9 items-center justify-center rounded-lg bg-primary/12 text-primary">
          <Icon aria-hidden="true" />
        </span>
      </CardHeader>
      <CardContent className="px-4 text-xs text-muted-foreground">
        {description}
      </CardContent>
    </Card>
  )
}

function ActorDetailPanel({
  actor,
  granularity,
  onGranularityChange,
  tracking,
  trackingPending,
  trackingError,
  summary,
  summaryPending,
  onGenerateSummary,
  jsonExportUrl,
  csvExportUrl,
}: {
  actor: ThreatActorDetail
  granularity: "month" | "year"
  onGranularityChange: (value: "month" | "year") => void
  tracking: Awaited<ReturnType<typeof getActorTracking>> | undefined
  trackingPending: boolean
  trackingError: string | undefined
  summary: Awaited<ReturnType<typeof generateActorTrackingSummary>> | undefined
  summaryPending: boolean
  onGenerateSummary: () => void
  jsonExportUrl: string
  csvExportUrl: string
}) {
  return (
    <div className="flex flex-1 flex-col gap-6 overflow-y-auto p-4 sm:p-6">
      <div className="flex flex-col justify-between gap-4 xl:flex-row xl:items-start">
        <div className="max-w-4xl">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <Badge variant="confirmed">
              <ShieldUserIcon data-icon="inline-start" />
              标准化攻击组织
            </Badge>
            {actor.origin_country ? (
              <Badge variant="outline">
                <FlagIcon data-icon="inline-start" />
                {actor.origin_country}
              </Badge>
            ) : null}
          </div>
          <h2 className="text-2xl leading-9 font-semibold sm:text-3xl">
            {actor.canonical_name}
          </h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {actor.description ||
              "该组织由已确认事件中的归因字段自动建立档案。"}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {actor.aliases.map((alias) => (
              <Badge key={alias} variant="secondary">
                {alias}
              </Badge>
            ))}
          </div>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <MetricCard
          description="当前日期范围内的已确认事件"
          icon={ActivityIcon}
          title="攻击事件"
          value={String(actor.event_count)}
        />
        <MetricCard
          description="首次进入已确认事件时间线"
          icon={CalendarDaysIcon}
          title="首次观测"
          value={formatDateTime(actor.first_seen).split(" ")[0]}
        />
        <MetricCard
          description="最近一次已确认活动"
          icon={Clock3Icon}
          title="最近活动"
          value={formatDateTime(actor.last_seen).split(" ")[0]}
        />
      </div>

      <ActorTrackingPanel
        csvExportUrl={csvExportUrl}
        error={trackingError}
        isGenerating={summaryPending}
        isPending={trackingPending}
        jsonExportUrl={jsonExportUrl}
        onGenerateSummary={onGenerateSummary}
        summary={summary}
        tracking={tracking}
      />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,0.72fr)_minmax(0,1.28fr)]">
        <Card>
          <CardHeader className="flex-row items-start justify-between gap-3">
            <div>
              <CardTitle>事件统计</CardTitle>
              <CardDescription>按月或按年查看攻击事件数量</CardDescription>
            </div>
            <ToggleGroup
              aria-label="统计粒度"
              onValueChange={(value) => {
                if (value === "month" || value === "year") {
                  onGranularityChange(value)
                }
              }}
              size="sm"
              spacing={0}
              type="single"
              value={granularity}
              variant="outline"
            >
              <ToggleGroupItem value="month">月</ToggleGroupItem>
              <ToggleGroupItem value="year">年</ToggleGroupItem>
            </ToggleGroup>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>周期</TableHead>
                  <TableHead className="text-right">事件数</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {actor.timeline.map((bucket) => (
                  <TableRow key={bucket.key}>
                    <TableCell className="font-medium">
                      {bucket.label}
                    </TableCell>
                    <TableCell className="text-right">
                      <Badge variant="secondary">{bucket.event_count}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>攻击事件时间线</CardTitle>
            <CardDescription>
              {actor.events.length} 起已确认事件，按最近观测时间排序
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {actor.events.map((event) => (
              <div
                className="rounded-lg border border-border bg-background/45 p-4"
                key={event.id}
              >
                <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="confirmed">已确认</Badge>
                      <Badge variant="outline">
                        置信度 {event.confidence ?? "—"}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {formatDateTime(event.first_seen)}
                      </span>
                    </div>
                    <h3 className="mt-2 text-sm leading-6 font-semibold">
                      {event.title}
                    </h3>
                    <p className="mt-2 line-clamp-3 text-sm leading-6 text-muted-foreground">
                      {event.summary || "暂无事件摘要。"}
                    </p>
                  </div>
                  <Badge variant="secondary">
                    报告名：{event.reported_name}
                  </Badge>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export function ActorsPage() {
  const today = new Date()
  const [preset, setPreset] = useState<RangePreset>("year")
  const [customFrom, setCustomFrom] = useState(
    isoDate(new Date(today.getFullYear(), 0, 1))
  )
  const [customTo, setCustomTo] = useState(isoDate(today))
  const [granularity, setGranularity] = useState<"month" | "year">("month")
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const range = presetRange(preset, customFrom, customTo)
  const rangeIsValid =
    preset !== "custom" ||
    (Boolean(customFrom) && Boolean(customTo) && customFrom <= customTo)
  const actorsQuery = useQuery({
    queryKey: [...actorQueryKey, range.dateFrom, range.dateTo],
    queryFn: () => listThreatActors(range),
    enabled: rangeIsValid,
  })
  const actors = actorsQuery.data ?? []
  const selected = actors.find((actor) => actor.id === selectedId) ?? actors[0]
  const detailQuery = useQuery({
    queryKey: [
      "actor",
      selected?.id,
      range.dateFrom,
      range.dateTo,
      granularity,
    ],
    queryFn: () => getThreatActor(selected!.id, { ...range, granularity }),
    enabled: Boolean(selected) && rangeIsValid,
  })
  const trackingQuery = useQuery({
    queryKey: [
      ...actorTrackingQueryKey,
      selected?.id,
      range.dateFrom,
      range.dateTo,
    ],
    queryFn: () => getActorTracking(selected!.id, range),
    enabled: Boolean(selected) && rangeIsValid,
  })
  const summaryMutation = useMutation({
    mutationFn: () => generateActorTrackingSummary(selected!.id, range),
  })
  const totalEvents = actors.reduce(
    (total, actor) => total + actor.event_count,
    0
  )

  return (
    <div className="grid min-h-0 flex-1 grid-rows-[auto_minmax(0,1fr)]">
      <header className="border-b border-border bg-surface px-4 py-4 sm:px-6">
        <div className="flex flex-col justify-between gap-4 2xl:flex-row 2xl:items-end">
          <div>
            <div className="flex items-center gap-2">
              <ShieldUserIcon className="size-5 text-primary" />
              <h1 className="text-xl font-semibold">攻击组织持续跟踪</h1>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              合并组织别名，按自定义日期和常用时间范围查看已确认攻击事件
            </p>
          </div>
          <FieldGroup
            className="w-full gap-3 2xl:max-w-[58rem]"
            data-testid="actor-date-filter"
          >
            <div className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-end">
              {preset === "custom" ? (
                <FieldGroup className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:w-96 xl:shrink-0">
                  <Field data-invalid={!rangeIsValid || undefined}>
                    <FieldLabel
                      className="h-5 items-center"
                      htmlFor="actor-date-from"
                    >
                      开始日期
                    </FieldLabel>
                    <Input
                      aria-invalid={!rangeIsValid || undefined}
                      id="actor-date-from"
                      onChange={(event) => {
                        setCustomFrom(event.target.value)
                        setSelectedId(null)
                        summaryMutation.reset()
                      }}
                      type="date"
                      value={customFrom}
                    />
                  </Field>
                  <Field data-invalid={!rangeIsValid || undefined}>
                    <FieldLabel
                      className="h-5 items-center"
                      htmlFor="actor-date-to"
                    >
                      结束日期
                    </FieldLabel>
                    <Input
                      aria-invalid={!rangeIsValid || undefined}
                      id="actor-date-to"
                      onChange={(event) => {
                        setCustomTo(event.target.value)
                        setSelectedId(null)
                        summaryMutation.reset()
                      }}
                      type="date"
                      value={customTo}
                    />
                  </Field>
                </FieldGroup>
              ) : null}
              <Field className="xl:w-auto xl:shrink-0">
                <FieldLabel className="h-5 items-center">日期范围</FieldLabel>
                <ToggleGroup
                  aria-label="日期范围"
                  className="w-full flex-wrap justify-start xl:w-auto xl:flex-nowrap"
                  onValueChange={(value) => {
                    if (value) {
                      setPreset(value as RangePreset)
                      setSelectedId(null)
                      summaryMutation.reset()
                    }
                  }}
                  type="single"
                  value={preset}
                  variant="outline"
                >
                  <ToggleGroupItem className="h-10" value="custom">
                    自定义
                  </ToggleGroupItem>
                  <ToggleGroupItem className="h-10" value="month">
                    本月
                  </ToggleGroupItem>
                  <ToggleGroupItem className="h-10" value="three_months">
                    3个月
                  </ToggleGroupItem>
                  <ToggleGroupItem className="h-10" value="six_months">
                    6个月
                  </ToggleGroupItem>
                  <ToggleGroupItem className="h-10" value="year">
                    本年
                  </ToggleGroupItem>
                  <ToggleGroupItem className="h-10" value="all">
                    全部
                  </ToggleGroupItem>
                </ToggleGroup>
              </Field>
            </div>
            {!rangeIsValid ? (
              <FieldError className="text-right">
                开始日期不能晚于结束日期。
              </FieldError>
            ) : null}
          </FieldGroup>
        </div>
        {actors.length ? (
          <div className="mt-4 flex flex-wrap gap-2 text-xs text-muted-foreground">
            <Badge variant="secondary">{actors.length} 个攻击组织</Badge>
            <Badge variant="secondary">{totalEvents} 条组织—事件关联</Badge>
          </div>
        ) : null}
      </header>

      {!rangeIsValid ? (
        <Empty className="border-0">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <CalendarDaysIcon />
            </EmptyMedia>
            <EmptyTitle>日期范围无效</EmptyTitle>
            <EmptyDescription>
              请修正开始日期和结束日期后再查看事件。
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : actorsQuery.isPending ? (
        <div className="grid min-h-0 gap-4 p-4 sm:p-6 lg:grid-cols-[22rem_minmax(0,1fr)]">
          <Skeleton className="h-[34rem]" />
          <Skeleton className="h-[34rem]" />
        </div>
      ) : actorsQuery.isError ? (
        <Empty className="border-0">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <AlertCircleIcon />
            </EmptyMedia>
            <EmptyTitle>攻击组织加载失败</EmptyTitle>
            <EmptyDescription>{actorsQuery.error.message}</EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : !actors.length ? (
        <Empty className="border-0">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <TargetIcon />
            </EmptyMedia>
            <EmptyTitle>所选日期内没有已确认攻击组织</EmptyTitle>
            <EmptyDescription>
              审核通过带有攻击组织归因的材料后，标准化组织档案和时间线会自动出现在这里。
            </EmptyDescription>
          </EmptyHeader>
          <Button asChild>
            <Link to="/reviews">
              <FileCheck2Icon data-icon="inline-start" />
              前往人工复核
            </Link>
          </Button>
        </Empty>
      ) : (
        <div className="grid min-h-0 lg:grid-cols-[22rem_minmax(0,1fr)]">
          <aside className="max-h-80 overflow-y-auto border-b border-border bg-card lg:max-h-none lg:border-r lg:border-b-0">
            <div className="border-b border-border p-4">
              <div className="flex items-center gap-2 text-sm font-medium">
                <TagsIcon className="size-4 text-primary" />
                规范化组织
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                同一组织的常见厂商命名已合并
              </p>
            </div>
            {actors.map((actor) => (
              <ActorRow
                actor={actor}
                key={actor.id}
                onSelect={(actorId) => {
                  setSelectedId(actorId)
                  summaryMutation.reset()
                }}
                selected={selected?.id === actor.id}
              />
            ))}
          </aside>
          <main className="flex min-h-0 min-w-0 flex-col">
            {detailQuery.isPending ? (
              <div className="flex flex-col gap-5 p-6">
                <Skeleton className="h-24 w-3/4" />
                <div className="grid gap-3 md:grid-cols-3">
                  {[0, 1, 2].map((item) => (
                    <Skeleton className="h-32" key={item} />
                  ))}
                </div>
                <Skeleton className="h-80" />
              </div>
            ) : detailQuery.isError || !detailQuery.data ? (
              <Empty className="border-0">
                <EmptyHeader>
                  <EmptyMedia variant="icon">
                    <AlertCircleIcon />
                  </EmptyMedia>
                  <EmptyTitle>组织详情加载失败</EmptyTitle>
                  <EmptyDescription>
                    {detailQuery.error?.message}
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            ) : (
              <ActorDetailPanel
                actor={detailQuery.data}
                csvExportUrl={
                  selected
                    ? actorTrackingExportUrl(selected.id, range, "csv")
                    : "#"
                }
                granularity={granularity}
                jsonExportUrl={
                  selected
                    ? actorTrackingExportUrl(selected.id, range, "json")
                    : "#"
                }
                onGenerateSummary={() => summaryMutation.mutate()}
                onGranularityChange={setGranularity}
                summary={summaryMutation.data}
                summaryPending={summaryMutation.isPending}
                tracking={trackingQuery.data}
                trackingError={trackingQuery.error?.message}
                trackingPending={trackingQuery.isPending}
              />
            )}
          </main>
        </div>
      )}
    </div>
  )
}
