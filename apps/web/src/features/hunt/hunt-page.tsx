import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  AlertCircleIcon,
  ArrowUpCircleIcon,
  BinocularsIcon,
  DatabaseZapIcon,
  FileSearchIcon,
  HistoryIcon,
  RotateCcwIcon,
  SearchIcon,
  ShieldAlertIcon,
  ShieldCheckIcon,
} from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"
import { formatDateTime } from "@/features/intelligence/intelligence-format"
import {
  enrichObservable,
  getObservable,
  indicatorQueryKey,
  listIndicators,
  listObservables,
  observableQueryKey,
  promoteObservable,
  updateIndicator,
} from "@/features/hunt/hunt-api"
import type {
  Indicator,
  IndicatorPromotion,
  ObservableDetail,
  ObservableSummary,
} from "@/features/hunt/hunt-types"
import { cn } from "@/lib/utils"

const OBSERVABLE_TYPES = [
  ["", "全部类型"],
  ["domain", "域名"],
  ["ipv4", "IPv4"],
  ["url", "URL"],
  ["email", "邮箱"],
  ["md5", "MD5"],
  ["sha1", "SHA-1"],
  ["sha256", "SHA-256"],
  ["cve", "CVE"],
] as const

const SEVERITY_LABELS: Record<Indicator["severity"], string> = {
  info: "信息",
  low: "低",
  medium: "中",
  high: "高",
  critical: "严重",
}

const AI_DISPOSITION_LABELS: Record<
  NonNullable<ObservableSummary["ai_disposition"]>,
  string
> = {
  malicious: "AI判定恶意",
  suspicious: "AI判定可疑",
  benign: "AI判定良性",
  context: "AI判定上下文",
}

function aiDispositionVariant(
  disposition: ObservableSummary["ai_disposition"]
): "confirmed" | "candidate" | "secondary" {
  if (disposition === "malicious") return "confirmed"
  if (disposition === "suspicious") return "candidate"
  return "secondary"
}

function dateInput(value: Date) {
  return value.toISOString().slice(0, 10)
}

const DEFAULT_VALID_FROM = dateInput(new Date())
const DEFAULT_VALID_UNTIL = dateInput(
  new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)
)

function ObservableRow({
  observable,
  selected,
  onSelect,
}: {
  observable: ObservableSummary
  selected: boolean
  onSelect: (id: string) => void
}) {
  return (
    <button
      className={cn(
        "w-full border-b border-border p-4 text-left transition-colors last:border-b-0 hover:bg-accent/40 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
        selected && "bg-accent/55 ring-1 ring-primary ring-inset"
      )}
      onClick={() => onSelect(observable.id)}
      type="button"
    >
      <div className="flex items-start justify-between gap-3">
        <Badge variant="outline">{observable.type.toUpperCase()}</Badge>
        {observable.indicator ? (
          <Badge
            variant={observable.indicator.revoked ? "secondary" : "confirmed"}
          >
            {observable.indicator.revoked
              ? "已撤销 Indicator"
              : observable.indicator.reviewed_by === "ai-automation"
                ? "AI维护 Indicator"
                : "人工纠正 Indicator"}
          </Badge>
        ) : observable.ai_disposition ? (
          <Badge variant={aiDispositionVariant(observable.ai_disposition)}>
            {AI_DISPOSITION_LABELS[observable.ai_disposition]}
          </Badge>
        ) : (
          <Badge variant="candidate">等待AI判断</Badge>
        )}
      </div>
      <p className="mt-2 line-clamp-2 font-mono text-xs break-all">
        {observable.value_normalized}
      </p>
      <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
        <span>{observable.report_count} 篇报告</span>
        <span>{observable.event_count} 个事件</span>
        <span>最近 {formatDateTime(observable.last_seen)}</span>
      </div>
    </button>
  )
}

function PromotionDialog({
  observable,
  open,
  onOpenChange,
}: {
  observable: ObservableDetail
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const queryClient = useQueryClient()
  const [purpose, setPurpose] = useState("")
  const [validFrom, setValidFrom] = useState(DEFAULT_VALID_FROM)
  const [validUntil, setValidUntil] = useState(DEFAULT_VALID_UNTIL)
  const [confidence, setConfidence] = useState("80")
  const [severity, setSeverity] =
    useState<IndicatorPromotion["severity"]>("medium")
  const [evidenceIds, setEvidenceIds] = useState<string[]>(() =>
    observable.reports.map((report) => report.evidence_id)
  )

  const mutation = useMutation({
    mutationFn: () =>
      promoteObservable(observable.id, {
        purpose: purpose.trim(),
        valid_from: `${validFrom}T00:00:00.000Z`,
        valid_until: `${validUntil}T23:59:59.999Z`,
        confidence: Number(confidence),
        severity,
        evidence_ids: evidenceIds,
      }),
    onSuccess: () => {
      toast.success("已记录人工纠正并创建 Indicator")
      void queryClient.invalidateQueries({ queryKey: observableQueryKey })
      void queryClient.invalidateQueries({ queryKey: indicatorQueryKey })
      void queryClient.invalidateQueries({
        queryKey: ["observable", observable.id],
      })
      onOpenChange(false)
    },
    onError: (error: Error) => toast.error(error.message),
  })
  const parsedConfidence = Number(confidence)
  const valid =
    purpose.trim().length >= 3 &&
    validFrom <= validUntil &&
    evidenceIds.length > 0 &&
    Number.isInteger(parsedConfidence) &&
    parsedConfidence >= 0 &&
    parsedConfidence <= 100

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>人工纠正为恶意 Indicator</DialogTitle>
          <DialogDescription>
            仅在AI判断有误或需要补充结论时使用。人工纠正会被审计，并阻止后续AI覆盖该Indicator。
          </DialogDescription>
        </DialogHeader>
        <Card className="gap-2 py-4">
          <CardHeader className="px-4">
            <Badge className="w-fit" variant="outline">
              {observable.type.toUpperCase()}
            </Badge>
            <CardTitle className="font-mono text-sm break-all">
              {observable.value_normalized}
            </CardTitle>
          </CardHeader>
        </Card>
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="indicator-purpose">恶意用途</FieldLabel>
            <Textarea
              id="indicator-purpose"
              onChange={(event) => setPurpose(event.target.value)}
              placeholder="例如：用于窃取凭据的钓鱼基础设施"
              value={purpose}
            />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field>
              <FieldLabel htmlFor="indicator-valid-from">生效日期</FieldLabel>
              <Input
                id="indicator-valid-from"
                onChange={(event) => setValidFrom(event.target.value)}
                type="date"
                value={validFrom}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="indicator-valid-until">失效日期</FieldLabel>
              <Input
                id="indicator-valid-until"
                onChange={(event) => setValidUntil(event.target.value)}
                type="date"
                value={validUntil}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="indicator-confidence">人工置信度</FieldLabel>
              <Input
                id="indicator-confidence"
                max={100}
                min={0}
                onChange={(event) => setConfidence(event.target.value)}
                type="number"
                value={confidence}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="indicator-severity">严重度</FieldLabel>
              <select
                className="h-8 w-full rounded-lg border border-input bg-background px-2.5 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                id="indicator-severity"
                onChange={(event) =>
                  setSeverity(
                    event.target.value as IndicatorPromotion["severity"]
                  )
                }
                value={severity}
              >
                {Object.entries(SEVERITY_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <Field>
            <FieldLabel>支持证据（至少一条）</FieldLabel>
            <div className="flex flex-col gap-2">
              {observable.reports.map((report) => (
                <label
                  className="flex cursor-pointer items-start gap-3 rounded-lg border border-border p-3"
                  key={report.evidence_id}
                >
                  <input
                    checked={evidenceIds.includes(report.evidence_id)}
                    className="mt-1"
                    onChange={(event) =>
                      setEvidenceIds((current) =>
                        event.target.checked
                          ? [...current, report.evidence_id]
                          : current.filter((id) => id !== report.evidence_id)
                      )
                    }
                    type="checkbox"
                  />
                  <span>
                    <span className="block text-sm font-medium">
                      {report.report_title}
                    </span>
                    <span className="mt-1 block text-xs leading-5 text-muted-foreground">
                      {report.evidence}
                    </span>
                  </span>
                </label>
              ))}
            </div>
          </Field>
        </FieldGroup>
        <DialogFooter>
          <Button
            disabled={!valid || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            <ShieldAlertIcon data-icon="inline-start" />
            保存人工纠正
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function ObservableDetailPanel({
  observable,
}: {
  observable: ObservableDetail
}) {
  const queryClient = useQueryClient()
  const [promoteOpen, setPromoteOpen] = useState(false)
  const enrichMutation = useMutation({
    mutationFn: () => enrichObservable(observable.id),
    onSuccess: () => {
      toast.success("本地上下文富化已刷新")
      void queryClient.invalidateQueries({
        queryKey: ["observable", observable.id],
      })
    },
    onError: (error: Error) => toast.error(error.message),
  })
  const metrics = [
    { label: "报告出现", value: observable.report_count, icon: FileSearchIcon },
    { label: "关联事件", value: observable.event_count, icon: BinocularsIcon },
    {
      label: "字段证据",
      value: observable.evidence_count,
      icon: ShieldCheckIcon,
    },
  ]

  return (
    <div
      className="flex min-h-0 flex-1 flex-col gap-5 overflow-x-hidden overflow-y-auto overscroll-contain p-4 sm:p-6 [&>*]:shrink-0"
      data-testid="observable-detail-scroll"
    >
      <div className="flex flex-col justify-between gap-4 xl:flex-row xl:items-start">
        <div className="max-w-4xl min-w-0">
          <div className="mb-2 flex flex-wrap gap-2">
            <Badge variant="outline">{observable.type.toUpperCase()}</Badge>
            <Badge variant="secondary">{observable.scope}</Badge>
            {observable.indicator ? (
              <Badge
                variant={
                  observable.indicator.revoked ? "secondary" : "confirmed"
                }
              >
                <ShieldCheckIcon data-icon="inline-start" />
                {observable.indicator.revoked
                  ? "Indicator 已撤销"
                  : observable.indicator.reviewed_by === "ai-automation"
                    ? "AI维护 Indicator"
                    : "人工纠正 Indicator"}
              </Badge>
            ) : observable.ai_disposition ? (
              <Badge variant={aiDispositionVariant(observable.ai_disposition)}>
                {AI_DISPOSITION_LABELS[observable.ai_disposition]}
              </Badge>
            ) : (
              <Badge variant="candidate">等待AI判断</Badge>
            )}
          </div>
          <h2 className="font-mono text-lg leading-8 font-semibold break-all sm:text-xl">
            {observable.value_normalized}
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            首次出现 {formatDateTime(observable.first_seen)} · 最近出现{" "}
            {formatDateTime(observable.last_seen)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            disabled={enrichMutation.isPending}
            onClick={() => enrichMutation.mutate()}
            variant="outline"
          >
            <DatabaseZapIcon data-icon="inline-start" />
            刷新本地富化
          </Button>
          {!observable.indicator && (
            <Button onClick={() => setPromoteOpen(true)}>
              <ArrowUpCircleIcon data-icon="inline-start" />
              纠正为 Indicator
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {metrics.map(({ label, value, icon: Icon }) => (
          <Card className="gap-2 py-4" key={label}>
            <CardHeader className="flex-row items-center justify-between px-4">
              <div>
                <CardDescription>{label}</CardDescription>
                <CardTitle className="mt-1 text-2xl">{value}</CardTitle>
              </div>
              <Icon className="size-5 text-primary" />
            </CardHeader>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle>AI自动判断</CardTitle>
              <CardDescription>
                模型结合原文语境判断该对象的角色，不以格式匹配直接认定恶意。
              </CardDescription>
            </div>
            {observable.ai_disposition ? (
              <Badge variant={aiDispositionVariant(observable.ai_disposition)}>
                {AI_DISPOSITION_LABELS[observable.ai_disposition]}
                {observable.ai_confidence !== null
                  ? ` · ${observable.ai_confidence}%`
                  : ""}
              </Badge>
            ) : (
              <Badge variant="candidate">待自动处理</Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-[minmax(10rem,0.35fr)_minmax(0,1fr)]">
          <div className="rounded-lg border p-3">
            <p className="text-xs text-muted-foreground">上下文角色</p>
            <p className="mt-1 text-sm">
              {observable.ai_role ?? "等待AI完成上下文判断"}
            </p>
          </div>
          <div className="rounded-lg border p-3">
            <p className="text-xs text-muted-foreground">判断理由</p>
            <p className="mt-1 text-sm leading-6">
              {observable.ai_decision_reason ??
                "该对象尚未经过新版本AI分析；后续采集或历史材料回填会自动补齐。"}
            </p>
            {observable.ai_decided_at ? (
              <p className="mt-2 text-xs text-muted-foreground">
                更新于 {formatDateTime(observable.ai_decided_at)}
              </p>
            ) : null}
          </div>
        </CardContent>
      </Card>

      {observable.indicator && (
        <Card>
          <CardHeader>
            <CardTitle>恶意判断</CardTitle>
            <CardDescription>
              AI默认自动维护用途、有效期和置信度；人工纠正后切换为人工覆盖并保留审计记录。
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-lg border p-3 sm:col-span-2">
              <p className="text-xs text-muted-foreground">用途</p>
              <p className="mt-1 text-sm">{observable.indicator.purpose}</p>
            </div>
            <div className="rounded-lg border p-3">
              <p className="text-xs text-muted-foreground">严重度 / 置信度</p>
              <p className="mt-1 text-sm">
                {SEVERITY_LABELS[observable.indicator.severity]} ·{" "}
                {observable.indicator.confidence}%
              </p>
            </div>
            <div className="rounded-lg border p-3">
              <p className="text-xs text-muted-foreground">有效期</p>
              <p className="mt-1 text-sm">
                {formatDateTime(observable.indicator.valid_until)}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid min-w-0 gap-4 xl:grid-cols-2">
        <Card className="min-w-0 overflow-hidden">
          <CardHeader>
            <CardTitle>报告与原文证据</CardTitle>
            <CardDescription>按最近出现时间排列</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {observable.reports.map((report) => (
              <div className="rounded-lg border p-4" key={report.evidence_id}>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="secondary">{report.source_name}</Badge>
                  <Badge variant="outline">置信度 {report.confidence}%</Badge>
                </div>
                <h3 className="mt-2 text-sm font-medium">
                  {report.report_title}
                </h3>
                <p className="mt-2 text-xs leading-5 text-muted-foreground">
                  {report.evidence}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card className="min-w-0 overflow-hidden">
          <CardHeader>
            <CardTitle>事件时间线</CardTitle>
            <CardDescription>仅展示已确认事件关联</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {observable.events.length ? (
              observable.events.map((event) => (
                <div className="rounded-lg border p-4" key={event.event_id}>
                  <div className="flex items-center gap-2">
                    <Badge variant="confirmed">已确认事件</Badge>
                    <span className="text-xs text-muted-foreground">
                      {formatDateTime(event.first_seen)}
                    </span>
                  </div>
                  <h3 className="mt-2 text-sm font-medium">
                    {event.event_title}
                  </h3>
                  <p className="mt-2 text-xs leading-5 text-muted-foreground">
                    {event.evidence}
                  </p>
                </div>
              ))
            ) : (
              <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
                该 Observable 尚未进入已确认事件。
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>富化结果</CardTitle>
          <CardDescription>
            默认仅计算本地上下文，不把内部或私有 Observable 发送给第三方。
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {observable.enrichments.length ? (
            observable.enrichments.map((enrichment) => (
              <div
                className="flex flex-col justify-between gap-2 rounded-lg border p-3 sm:flex-row sm:items-center"
                key={enrichment.id}
              >
                <div>
                  <p className="text-sm font-medium">{enrichment.provider}</p>
                  <p className="text-xs text-muted-foreground">
                    查询于 {formatDateTime(enrichment.queried_at)} · TTL 至{" "}
                    {formatDateTime(enrichment.expires_at)}
                  </p>
                </div>
                <Badge variant="confirmed">{enrichment.status}</Badge>
              </div>
            ))
          ) : (
            <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
              尚未执行富化。点击“刷新本地富化”生成来源与事件上下文摘要。
            </p>
          )}
        </CardContent>
      </Card>

      <PromotionDialog
        key={observable.id}
        observable={observable}
        onOpenChange={setPromoteOpen}
        open={promoteOpen}
      />
    </div>
  )
}

function IndicatorList({ indicators }: { indicators: Indicator[] }) {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: (indicator: Indicator) =>
      updateIndicator(indicator.id, {
        expected_version: indicator.version,
        revoked: !indicator.revoked,
      }),
    onSuccess: (updated) => {
      toast.success(updated.revoked ? "Indicator 已撤销" : "Indicator 已恢复")
      void queryClient.invalidateQueries({ queryKey: indicatorQueryKey })
      void queryClient.invalidateQueries({ queryKey: observableQueryKey })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  if (!indicators.length) {
    return (
      <Empty className="border-0">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <ShieldAlertIcon />
          </EmptyMedia>
          <EmptyTitle>还没有AI或人工确认的 Indicator</EmptyTitle>
          <EmptyDescription>
            AI会在新材料处理时自动判断并创建；分析员也可以在详情中纠正遗漏。
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }

  return (
    <div
      className="grid min-h-0 auto-rows-max content-start items-start gap-3 overflow-y-auto overscroll-contain p-4 sm:grid-cols-2 sm:p-6 2xl:grid-cols-3"
      data-testid="indicator-list-scroll"
    >
      {indicators.map((indicator) => (
        <Card className="h-fit min-w-0" key={indicator.id}>
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Badge variant="outline">
                {indicator.observable_type.toUpperCase()}
              </Badge>
              <Badge variant={indicator.revoked ? "secondary" : "confirmed"}>
                {indicator.revoked ? "已撤销" : "有效"}
              </Badge>
            </div>
            <CardTitle className="font-mono text-sm break-all">
              {indicator.value_normalized}
            </CardTitle>
            <CardDescription>{indicator.purpose}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <div className="flex flex-wrap gap-2">
              <Badge variant="secondary">
                {SEVERITY_LABELS[indicator.severity]}
              </Badge>
              <Badge variant="outline">置信度 {indicator.confidence}%</Badge>
              <Badge variant="outline">
                {indicator.evidence_ids.length} 条证据
              </Badge>
              <Badge variant="outline">
                {indicator.reviewed_by === "ai-automation"
                  ? "AI自动维护"
                  : "人工覆盖"}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              有效至 {formatDateTime(indicator.valid_until)}
            </p>
            <code className="rounded-md bg-muted p-2 text-xs break-all">
              {indicator.pattern}
            </code>
            <Button
              disabled={mutation.isPending}
              onClick={() => mutation.mutate(indicator)}
              size="sm"
              variant={indicator.revoked ? "outline" : "destructive"}
            >
              {indicator.revoked ? (
                <RotateCcwIcon data-icon="inline-start" />
              ) : (
                <HistoryIcon data-icon="inline-start" />
              )}
              {indicator.revoked ? "恢复 Indicator" : "撤销 Indicator"}
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export function HuntPage() {
  const [mode, setMode] = useState<"observables" | "indicators">("observables")
  const [searchInput, setSearchInput] = useState("")
  const [query, setQuery] = useState("")
  const [type, setType] = useState("")
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const observablesQuery = useQuery({
    queryKey: [...observableQueryKey, query, type],
    queryFn: () =>
      listObservables({ q: query || undefined, type: type || undefined }),
  })
  const indicatorsQuery = useQuery({
    queryKey: [...indicatorQueryKey, query],
    queryFn: () => listIndicators({ q: query || undefined }),
  })
  const observables = observablesQuery.data ?? []
  const indicators = indicatorsQuery.data ?? []
  const selected =
    observables.find((observable) => observable.id === selectedId) ??
    observables[0]
  const detailQuery = useQuery({
    queryKey: ["observable", selected?.id],
    queryFn: () => getObservable(selected!.id),
    enabled: Boolean(selected) && mode === "observables",
  })

  return (
    <div
      className="grid min-h-0 flex-1 grid-rows-[auto_minmax(0,1fr)] overflow-hidden"
      data-testid="hunt-workspace"
    >
      <header className="border-b border-border bg-surface px-4 py-4 sm:px-6">
        <div className="flex flex-col justify-between gap-4 xl:flex-row xl:items-end">
          <div>
            <div className="flex items-center gap-2">
              <BinocularsIcon className="size-5 text-primary" />
              <h1 className="text-xl font-semibold">IOC 狩猎</h1>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              AI结合报告语境自动区分Observable与Indicator；人工只需在阅读时纠错
            </p>
          </div>
          <form
            className="flex w-full flex-col gap-2 sm:flex-row xl:max-w-3xl"
            onSubmit={(event) => {
              event.preventDefault()
              setQuery(searchInput.trim())
              setSelectedId(null)
            }}
          >
            <div className="relative min-w-0 flex-1">
              <SearchIcon className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                aria-label="搜索 Observable 或 Indicator"
                className="pl-9"
                data-testid="hunt-search-input"
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="输入 IP、域名、URL、邮箱或文件哈希"
                value={searchInput}
              />
            </div>
            <select
              aria-label="Observable 类型"
              className="h-10 shrink-0 rounded-lg border border-input bg-background px-3 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
              data-testid="hunt-type-select"
              onChange={(event) => {
                setType(event.target.value)
                setSelectedId(null)
              }}
              value={type}
            >
              {OBSERVABLE_TYPES.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <Button
              className="shrink-0"
              data-testid="hunt-search-submit"
              size="lg"
              type="submit"
            >
              <SearchIcon data-icon="inline-start" />
              查询
            </Button>
          </form>
        </div>
        <div
          aria-label="狩猎对象类型"
          className="mt-4 flex w-fit rounded-lg bg-muted p-[3px]"
          role="group"
        >
          <Button
            aria-pressed={mode === "observables"}
            size="sm"
            type="button"
            variant={mode === "observables" ? "secondary" : "ghost"}
            onClick={() => setMode("observables")}
          >
            Observable（{observables.length}）
          </Button>
          <Button
            aria-pressed={mode === "indicators"}
            size="sm"
            type="button"
            variant={mode === "indicators" ? "secondary" : "ghost"}
            onClick={() => setMode("indicators")}
          >
            Indicator（{indicators.length}）
          </Button>
        </div>
      </header>

      {mode === "indicators" ? (
        indicatorsQuery.isPending ? (
          <div className="grid gap-3 p-6 sm:grid-cols-2 xl:grid-cols-3">
            {[0, 1, 2].map((item) => (
              <Skeleton className="h-72" key={item} />
            ))}
          </div>
        ) : indicatorsQuery.isError ? (
          <Empty className="border-0">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <AlertCircleIcon />
              </EmptyMedia>
              <EmptyTitle>Indicator 加载失败</EmptyTitle>
              <EmptyDescription>
                {indicatorsQuery.error.message}
              </EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : (
          <IndicatorList indicators={indicators} />
        )
      ) : observablesQuery.isPending ? (
        <div className="grid min-h-0 gap-4 p-6 lg:grid-cols-[22rem_minmax(0,1fr)]">
          <Skeleton className="h-[34rem]" />
          <Skeleton className="h-[34rem]" />
        </div>
      ) : observablesQuery.isError ? (
        <Empty className="border-0">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <AlertCircleIcon />
            </EmptyMedia>
            <EmptyTitle>Observable 加载失败</EmptyTitle>
            <EmptyDescription>
              {observablesQuery.error.message}
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : !observables.length ? (
        <Empty className="border-0">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <FileSearchIcon />
            </EmptyMedia>
            <EmptyTitle>没有找到 Observable</EmptyTitle>
            <EmptyDescription>
              新材料完成 rules-v2 富化后，域名、IP、URL、邮箱、哈希和 CVE
              会出现在这里。
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : (
        <div className="grid min-h-0 grid-rows-[minmax(10rem,18rem)_minmax(0,1fr)] overflow-hidden lg:grid-cols-[22rem_minmax(0,1fr)] lg:grid-rows-1">
          <aside
            className="min-h-0 overflow-y-auto overscroll-contain border-b border-border bg-card lg:border-r lg:border-b-0"
            data-testid="observable-list-scroll"
          >
            {observables.map((observable) => (
              <ObservableRow
                key={observable.id}
                observable={observable}
                onSelect={setSelectedId}
                selected={selected?.id === observable.id}
              />
            ))}
          </aside>
          <main className="flex min-h-0 min-w-0 flex-col overflow-hidden">
            {detailQuery.isPending ? (
              <div className="flex flex-col gap-5 p-6">
                <Skeleton className="h-24 w-3/4" />
                <div className="grid gap-3 sm:grid-cols-3">
                  {[0, 1, 2].map((item) => (
                    <Skeleton className="h-28" key={item} />
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
                  <EmptyTitle>Observable 详情加载失败</EmptyTitle>
                  <EmptyDescription>
                    {detailQuery.error?.message}
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            ) : (
              <ObservableDetailPanel observable={detailQuery.data} />
            )}
          </main>
        </div>
      )}
    </div>
  )
}
