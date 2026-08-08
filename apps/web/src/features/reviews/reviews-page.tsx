import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  AlertCircleIcon,
  Building2Icon,
  CheckIcon,
  ExternalLinkIcon,
  FileCheck2Icon,
  NetworkIcon,
  RefreshCwIcon,
  ShieldAlertIcon,
  SparklesIcon,
  TargetIcon,
  XIcon,
  ZapIcon,
} from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
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
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import {
  decideReview,
  enrichReport,
  getReport,
  listReviewQueue,
  reportQueryKey,
  reviewQueueKey,
} from "@/features/intelligence/intelligence-api"
import {
  extractionLabel,
  formatDateTime,
  sourceInitials,
} from "@/features/intelligence/intelligence-format"
import type {
  DiamondEntity,
  ReportDetail,
  ReportSummary,
} from "@/features/intelligence/intelligence-types"
import { cn } from "@/lib/utils"

const REVIEW_LABELS = {
  pending: "待审核",
  approved: "已通过",
  rejected: "已驳回",
} as const

function QueueRow({
  report,
  selected,
  onSelect,
}: {
  report: ReportSummary
  selected: boolean
  onSelect: (id: string) => void
}) {
  return (
    <button
      className={cn(
        "w-full border-b border-border p-4 text-left transition-colors last:border-b-0 hover:bg-accent/40 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
        selected && "bg-accent/55 ring-1 ring-primary ring-inset"
      )}
      onClick={() => onSelect(report.id)}
      type="button"
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="flex min-w-0 items-center gap-2 text-xs text-muted-foreground">
          <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-secondary font-semibold text-foreground">
            {sourceInitials(report.source_name)}
          </span>
          <span className="truncate">{report.source_name}</span>
        </span>
        <Badge
          variant={
            report.extraction_status === "failed" ? "destructive" : "secondary"
          }
        >
          {extractionLabel(report.extraction_status)}
        </Badge>
      </div>
      <h3 className="line-clamp-2 text-sm leading-6 font-medium">
        {report.title}
      </h3>
      <div className="mt-3 flex items-center justify-between gap-3 text-xs text-muted-foreground">
        <span>相关性 {report.relevance_score}</span>
        <span>{formatDateTime(report.published_at)}</span>
      </div>
    </button>
  )
}

function DiamondCard({
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
          <div className="min-w-0">
            <CardTitle className="text-sm">{title}</CardTitle>
            <CardDescription>{description}</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-2 px-4">
        {entities.length ? (
          entities.slice(0, 6).map((entity) => (
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
              {entity.evidence && (
                <p className="mt-2 line-clamp-3 text-xs leading-5 text-muted-foreground">
                  {entity.evidence}
                </p>
              )}
            </div>
          ))
        ) : (
          <p className="rounded-md border border-dashed border-border p-3 text-sm text-muted-foreground">
            未从正文中提取到，不作推断。
          </p>
        )}
      </CardContent>
    </Card>
  )
}

function EnrichmentState({
  report,
  onEnrich,
  pending,
}: {
  report: ReportDetail
  onEnrich: () => void
  pending: boolean
}) {
  const failed = report.analysis?.extraction_status === "failed"
  return (
    <div className="flex flex-1 items-center justify-center p-6">
      <Alert className="max-w-xl" variant={failed ? "destructive" : "default"}>
        <AlertCircleIcon />
        <AlertTitle>{failed ? "正文提取失败" : "正在生成钻石模型"}</AlertTitle>
        <AlertDescription>
          <p>
            {report.analysis?.extraction_error ??
              "任务已进入后台队列，页面会自动刷新。正文抓取完成后即可人工复核。"}
          </p>
          {failed && (
            <Button
              className="mt-4"
              disabled={pending}
              onClick={onEnrich}
              size="sm"
            >
              <RefreshCwIcon
                className={cn(pending && "animate-spin")}
                data-icon="inline-start"
              />
              重新富化
            </Button>
          )}
        </AlertDescription>
      </Alert>
    </div>
  )
}

function ReviewWorkbench({
  report,
  onCompleted,
}: {
  report: ReportDetail
  onCompleted: () => void
}) {
  const queryClient = useQueryClient()
  const analysis = report.analysis!
  const [note, setNote] = useState(analysis.analyst_note ?? "")
  const decisionMutation = useMutation({
    mutationFn: (decision: "approved" | "rejected") =>
      decideReview(report.id, {
        decision,
        analyst_note: note.trim() || null,
        expected_version: analysis.version,
      }),
    onSuccess: (updated) => {
      toast.success(
        updated.status === "approved" ? "材料已通过审核" : "材料已驳回"
      )
      void queryClient.invalidateQueries({ queryKey: reviewQueueKey })
      void queryClient.invalidateQueries({ queryKey: reportQueryKey })
      void queryClient.invalidateQueries({ queryKey: ["report", report.id] })
      onCompleted()
    },
    onError: (error: Error) => toast.error(error.message),
  })
  const enrichMutation = useMutation({
    mutationFn: () => enrichReport(report.id),
    onSuccess: () => {
      toast.success("已重新加入富化队列")
      void queryClient.invalidateQueries({ queryKey: reviewQueueKey })
      void queryClient.invalidateQueries({ queryKey: ["report", report.id] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex-1 space-y-6 overflow-y-auto p-4 sm:p-6">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
          <div className="max-w-4xl">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Badge variant="candidate">相关性 {report.relevance_score}</Badge>
              <Badge variant="outline">
                自动置信度 {analysis.confidence_auto ?? "—"}
              </Badge>
              <Badge variant="secondary">{analysis.method_version}</Badge>
            </div>
            <h2 className="text-xl leading-8 font-semibold sm:text-2xl">
              {report.title}
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              {report.source_name} · {formatDateTime(report.published_at)} ·{" "}
              {report.language.toUpperCase()}
            </p>
          </div>
          <Button asChild variant="outline">
            <a href={report.canonical_url} rel="noreferrer" target="_blank">
              <ExternalLinkIcon data-icon="inline-start" />
              打开原文
            </a>
          </Button>
        </div>

        <section>
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <h3 className="font-semibold">钻石模型自动拆解</h3>
              <p className="text-sm text-muted-foreground">
                每个字段都附带正文证据，缺失项保持为空。
              </p>
            </div>
            <Button
              disabled={enrichMutation.isPending}
              onClick={() => enrichMutation.mutate()}
              size="sm"
              variant="ghost"
            >
              <SparklesIcon data-icon="inline-start" />
              重新富化
            </Button>
          </div>
          <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-4">
            <DiamondCard
              title="对手"
              description="攻击组织与别名"
              icon={TargetIcon}
              entities={analysis.actors}
            />
            <DiamondCard
              title="能力"
              description="战术、技术与工具"
              icon={ZapIcon}
              entities={analysis.capabilities}
            />
            <DiamondCard
              title="基础设施"
              description="域名、IP 与 URL"
              icon={NetworkIcon}
              entities={analysis.infrastructure}
            />
            <DiamondCard
              title="受害者"
              description="行业、角色与区域"
              icon={Building2Icon}
              entities={analysis.victims}
            />
          </div>
        </section>

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(20rem,0.65fr)]">
          <Card>
            <CardHeader>
              <CardTitle>提取正文</CardTitle>
              <CardDescription>
                抓取于 {formatDateTime(analysis.fetched_at)}
                ，用于证据复核与后续事件沉淀。
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="max-h-96 overflow-y-auto text-sm leading-7 whitespace-pre-line text-muted-foreground">
                {analysis.content_text || "未保存正文。"}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>证据索引</CardTitle>
              <CardDescription>
                {analysis.evidence.length} 条字段级引用
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {analysis.evidence.length ? (
                analysis.evidence.slice(0, 12).map((evidence, index) => (
                  <div
                    className="border-l-2 border-primary/45 pl-3"
                    key={`${evidence.entity}-${index}`}
                  >
                    <div className="text-xs font-medium text-primary">
                      {evidence.dimension} · {evidence.entity}
                    </div>
                    <p className="mt-1 text-xs leading-5 text-muted-foreground">
                      {evidence.quote}
                    </p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">
                  暂无可引用证据。
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        <Field>
          <FieldLabel htmlFor="analyst-note">分析员备注</FieldLabel>
          <Textarea
            id="analyst-note"
            maxLength={5000}
            onChange={(event) => setNote(event.target.value)}
            placeholder="记录归因依据、疑点、需要补充的证据或驳回原因…"
            rows={4}
            value={note}
          />
          <FieldDescription>
            备注将与审核决定一起留存，便于后续追溯。
          </FieldDescription>
        </Field>
      </div>

      <div className="flex flex-col gap-3 border-t border-border bg-card px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <p className="text-sm text-muted-foreground">
          {analysis.review_status === "pending"
            ? "通过后材料进入已确认情报；驳回后仍保留正文与审核记录。"
            : `该材料已${REVIEW_LABELS[analysis.review_status]}，版本 ${analysis.version}。`}
        </p>
        {analysis.review_status === "pending" && (
          <div className="flex gap-2">
            <Button
              disabled={decisionMutation.isPending}
              onClick={() => decisionMutation.mutate("rejected")}
              variant="outline"
            >
              <XIcon data-icon="inline-start" />
              驳回
            </Button>
            <Button
              disabled={decisionMutation.isPending}
              onClick={() => decisionMutation.mutate("approved")}
            >
              <CheckIcon data-icon="inline-start" />
              通过审核
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

export function ReviewsPage() {
  const [reviewStatus, setReviewStatus] =
    useState<keyof typeof REVIEW_LABELS>("pending")
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const queueQuery = useQuery({
    queryKey: [...reviewQueueKey, reviewStatus],
    queryFn: () => listReviewQueue(reviewStatus),
    refetchInterval: reviewStatus === "pending" ? 5_000 : false,
  })
  const queue = queueQuery.data ?? []
  const selected = queue.find((item) => item.id === selectedId) ?? queue[0]
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
  const queryClient = useQueryClient()
  const enrichMutation = useMutation({
    mutationFn: (reportId: string) => enrichReport(reportId),
    onSuccess: (_, reportId) => {
      toast.success("已重新加入富化队列")
      void queryClient.invalidateQueries({ queryKey: ["report", reportId] })
      void queryClient.invalidateQueries({ queryKey: reviewQueueKey })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  return (
    <div className="grid min-h-0 flex-1 grid-rows-[auto_minmax(0,1fr)] lg:grid-cols-[21rem_minmax(0,1fr)] lg:grid-rows-1">
      <aside className="flex min-h-0 flex-col border-b border-border bg-card lg:border-r lg:border-b-0">
        <div className="space-y-3 p-4">
          <div>
            <h2 className="font-semibold">人工复核队列</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              核对正文证据后再沉淀为可信情报
            </p>
          </div>
          <Tabs
            value={reviewStatus}
            onValueChange={(value) => {
              setReviewStatus(value as keyof typeof REVIEW_LABELS)
              setSelectedId(null)
            }}
          >
            <TabsList className="w-full">
              {Object.entries(REVIEW_LABELS).map(([value, label]) => (
                <TabsTrigger className="flex-1" key={value} value={value}>
                  {label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </div>
        <Separator />
        <div className="max-h-72 min-h-0 overflow-y-auto lg:max-h-none lg:flex-1">
          {queueQuery.isPending ? (
            <div className="space-y-3 p-4">
              {[0, 1, 2].map((item) => (
                <Skeleton className="h-28" key={item} />
              ))}
            </div>
          ) : queueQuery.isError ? (
            <Empty className="min-h-56 border-0">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <AlertCircleIcon />
                </EmptyMedia>
                <EmptyTitle>审核队列加载失败</EmptyTitle>
                <EmptyDescription>{queueQuery.error.message}</EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : queue.length === 0 ? (
            <Empty className="min-h-56 border-0">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <FileCheck2Icon />
                </EmptyMedia>
                <EmptyTitle>{REVIEW_LABELS[reviewStatus]}列表为空</EmptyTitle>
                <EmptyDescription>
                  自动富化完成的候选材料会进入待审核列表。
                </EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : (
            queue.map((report) => (
              <QueueRow
                key={report.id}
                report={report}
                selected={selected?.id === report.id}
                onSelect={setSelectedId}
              />
            ))
          )}
        </div>
      </aside>

      <main className="flex min-h-0 min-w-0 flex-col">
        {!selected ? (
          <Empty className="border-0">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <ShieldAlertIcon />
              </EmptyMedia>
              <EmptyTitle>选择一篇材料开始复核</EmptyTitle>
              <EmptyDescription>
                系统会展示正文和钻石模型字段对应的证据。
              </EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : detailQuery.isPending ? (
          <div className="space-y-5 p-6">
            <Skeleton className="h-20 w-3/4" />
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {[0, 1, 2, 3].map((item) => (
                <Skeleton className="h-48" key={item} />
              ))}
            </div>
            <Skeleton className="h-72" />
          </div>
        ) : detailQuery.isError || !detailQuery.data ? (
          <Empty className="border-0">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <AlertCircleIcon />
              </EmptyMedia>
              <EmptyTitle>材料详情加载失败</EmptyTitle>
              <EmptyDescription>{detailQuery.error?.message}</EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : detailQuery.data.analysis?.extraction_status !== "ready" ? (
          <EnrichmentState
            report={detailQuery.data}
            pending={enrichMutation.isPending}
            onEnrich={() => enrichMutation.mutate(detailQuery.data.id)}
          />
        ) : (
          <ReviewWorkbench
            key={`${detailQuery.data.id}-${detailQuery.data.analysis.version}`}
            report={detailQuery.data}
            onCompleted={() => setSelectedId(null)}
          />
        )}
      </main>
    </div>
  )
}
