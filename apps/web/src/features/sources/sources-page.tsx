import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  AlertTriangleIcon,
  CheckCircle2Icon,
  Clock3Icon,
  DatabaseIcon,
  FileTextIcon,
  PlusIcon,
  RefreshCwIcon,
  RssIcon,
  SendIcon,
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
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"

import {
  createSource,
  listSources,
  pollSource,
  sourceQueryKey,
  updateSource,
} from "./source-api"
import type { Source, SourceCreate, SourceHealth } from "./source-types"

const EMPTY_SOURCE_FORM: SourceCreate = {
  name: "",
  url: "",
  enabled: true,
  poll_interval_minutes: 60,
}

const HEALTH_LABELS: Record<SourceHealth, string> = {
  pending: "待首次采集",
  healthy: "正常",
  degraded: "异常",
  disabled: "已停用",
}

function formatDateTime(value: string | null) {
  if (!value) return "—"
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value))
}

function validateSource(payload: SourceCreate) {
  const errors: { name?: string; url?: string } = {}
  if (payload.name.trim().length < 2) {
    errors.name = "名称至少需要 2 个字符。"
  }
  try {
    const parsed = new URL(payload.url)
    if (!["http:", "https:"].includes(parsed.protocol)) {
      errors.url = "Feed URL 必须使用 HTTP 或 HTTPS。"
    }
  } catch {
    errors.url = "请输入完整的 RSS 或 Atom 地址。"
  }
  return errors
}

function HealthBadge({ status }: { status: SourceHealth }) {
  const variant =
    status === "healthy"
      ? "confirmed"
      : status === "degraded"
        ? "destructive"
        : status === "pending"
          ? "candidate"
          : "secondary"
  return <Badge variant={variant}>{HEALTH_LABELS[status]}</Badge>
}

function MetricCard({
  icon: Icon,
  label,
  value,
  note,
}: {
  icon: typeof DatabaseIcon
  label: string
  value: number
  note: string
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-4">
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
      </CardContent>
    </Card>
  )
}

function AddSourceDialog({
  open,
  onOpenChange,
  onCreate,
  pending,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreate: (payload: SourceCreate) => void
  pending: boolean
}) {
  const [form, setForm] = useState<SourceCreate>(() => ({
    ...EMPTY_SOURCE_FORM,
  }))
  const [submitted, setSubmitted] = useState(false)
  const errors = submitted ? validateSource(form) : {}

  function changeOpen(nextOpen: boolean) {
    onOpenChange(nextOpen)
    if (!nextOpen) {
      setForm({ ...EMPTY_SOURCE_FORM })
      setSubmitted(false)
    }
  }

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitted(true)
    if (Object.keys(validateSource(form)).length > 0) return
    onCreate({ ...form, name: form.name.trim(), url: form.url.trim() })
  }

  return (
    <Dialog open={open} onOpenChange={changeOpen}>
      <DialogTrigger asChild>
        <Button>
          <PlusIcon data-icon="inline-start" />
          添加数据源
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <form className="flex flex-col gap-5" onSubmit={submit}>
          <DialogHeader>
            <DialogTitle>添加 RSS 数据源</DialogTitle>
            <DialogDescription>
              系统将按计划拉取 RSS/Atom，规范化链接并进行 APT 相关性初筛。
            </DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <Field data-invalid={Boolean(errors.name)}>
              <FieldLabel htmlFor="source-name">名称</FieldLabel>
              <Input
                id="source-name"
                aria-invalid={Boolean(errors.name)}
                autoComplete="off"
                placeholder="例如 Microsoft Security Blog"
                value={form.name}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    name: event.target.value,
                  }))
                }
              />
              <FieldError>{errors.name}</FieldError>
            </Field>
            <Field data-invalid={Boolean(errors.url)}>
              <FieldLabel htmlFor="source-url">Feed URL</FieldLabel>
              <Input
                id="source-url"
                aria-invalid={Boolean(errors.url)}
                autoComplete="url"
                placeholder="https://example.com/security/feed.xml"
                type="url"
                value={form.url}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    url: event.target.value,
                  }))
                }
              />
              <FieldDescription>
                支持 RSS 2.0 与 Atom，必须使用 HTTP(S)。
              </FieldDescription>
              <FieldError>{errors.url}</FieldError>
            </Field>
            <Field>
              <FieldLabel htmlFor="poll-interval">采集间隔（分钟）</FieldLabel>
              <Input
                id="poll-interval"
                max={1440}
                min={5}
                type="number"
                value={form.poll_interval_minutes}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    poll_interval_minutes: Number(event.target.value),
                  }))
                }
              />
              <FieldDescription>
                最短 5 分钟，默认每小时采集一次。
              </FieldDescription>
            </Field>
            <Field orientation="horizontal">
              <FieldLabel htmlFor="source-enabled">创建后立即启用</FieldLabel>
              <Switch
                id="source-enabled"
                checked={form.enabled}
                onCheckedChange={(enabled) =>
                  setForm((current) => ({ ...current, enabled }))
                }
              />
            </Field>
          </FieldGroup>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => changeOpen(false)}
            >
              取消
            </Button>
            <Button disabled={pending} type="submit">
              {pending ? "正在保存…" : "保存数据源"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function SourceInspector({
  source,
  onPoll,
  pollPending,
}: {
  source: Source | undefined
  onPoll: (source: Source) => void
  pollPending: boolean
}) {
  return (
    <aside className="hidden min-w-0 border-l border-border bg-card xl:flex xl:flex-col">
      <div className="p-5">
        <h2 className="text-lg font-semibold">数据源详情</h2>
      </div>
      <Separator />
      {source ? (
        <div className="flex flex-1 flex-col gap-5 overflow-y-auto p-5">
          <div className="flex items-start gap-3">
            <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-secondary text-primary">
              <RssIcon aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h3 className="truncate font-semibold">{source.name}</h3>
              <div className="mt-2 flex items-center gap-2">
                <Badge variant="outline">RSS/Atom</Badge>
                <HealthBadge status={source.health_status} />
              </div>
            </div>
          </div>
          <dl className="grid grid-cols-[7rem_minmax(0,1fr)] gap-x-3 gap-y-3 text-sm">
            <dt className="text-muted-foreground">Feed URL</dt>
            <dd className="truncate" title={source.url ?? undefined}>
              {source.url ?? "—"}
            </dd>
            <dt className="text-muted-foreground">采集间隔</dt>
            <dd>每 {source.poll_interval_minutes} 分钟</dd>
            <dt className="text-muted-foreground">最近成功</dt>
            <dd>{formatDateTime(source.last_success_at)}</dd>
            <dt className="text-muted-foreground">下次运行</dt>
            <dd>{formatDateTime(source.next_poll_at)}</dd>
            <dt className="text-muted-foreground">已收报告</dt>
            <dd>{source.report_count}</dd>
            <dt className="text-muted-foreground">连续失败</dt>
            <dd>{source.consecutive_failures}</dd>
          </dl>
          {source.last_error ? (
            <Card className="border-destructive/30 bg-destructive/5">
              <CardHeader>
                <CardTitle className="text-sm">最近错误</CardTitle>
                <CardDescription>{source.last_error}</CardDescription>
              </CardHeader>
            </Card>
          ) : null}
          <div className="mt-auto">
            <Button
              className="w-full"
              disabled={pollPending}
              onClick={() => onPoll(source)}
            >
              <SendIcon data-icon="inline-start" />
              {pollPending ? "正在加入队列…" : "立即采集"}
            </Button>
          </div>
        </div>
      ) : (
        <Empty className="border-0">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <DatabaseIcon />
            </EmptyMedia>
            <EmptyTitle>尚未选择数据源</EmptyTitle>
            <EmptyDescription>选择左侧来源查看采集状态。</EmptyDescription>
          </EmptyHeader>
        </Empty>
      )}
    </aside>
  )
}

export function SourcesPage() {
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [addOpen, setAddOpen] = useState(false)
  const sourcesQuery = useQuery({
    queryKey: sourceQueryKey,
    queryFn: listSources,
  })
  const sources = sourcesQuery.data ?? []
  const selectedSource =
    sources.find((source) => source.id === selectedId) ?? sources[0]

  const createMutation = useMutation({
    mutationFn: createSource,
    onSuccess: (created) => {
      queryClient.setQueryData<Source[]>(sourceQueryKey, (current = []) => [
        created,
        ...current,
      ])
      setSelectedId(created.id)
      setAddOpen(false)
      toast.success("数据源已创建", {
        description: "定时调度器将在下一轮开始采集。",
      })
    },
    onError: (error: Error) =>
      toast.error("创建失败", { description: error.message }),
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      updateSource(id, { enabled }),
    onSuccess: (updated) => {
      queryClient.setQueryData<Source[]>(sourceQueryKey, (current = []) =>
        current.map((source) => (source.id === updated.id ? updated : source))
      )
    },
    onError: (error: Error) =>
      toast.error("状态更新失败", { description: error.message }),
  })
  const pollMutation = useMutation({
    mutationFn: pollSource,
    onSuccess: () => toast.success("采集任务已加入队列"),
    onError: (error: Error) =>
      toast.error("无法启动采集", { description: error.message }),
  })

  const healthy = sources.filter(
    (source) => source.health_status === "healthy"
  ).length
  const attention = sources.filter(
    (source) => source.health_status === "degraded"
  ).length
  const reports = sources.reduce(
    (total, source) => total + source.report_count,
    0
  )
  const pending = sources.filter(
    (source) => source.health_status === "pending"
  ).length

  return (
    <div className="grid min-h-0 flex-1 grid-cols-1 xl:grid-cols-[minmax(0,1fr)_24rem]">
      <main className="flex min-w-0 flex-col gap-4 overflow-y-auto p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">采集连接器</h2>
            <p className="text-sm text-muted-foreground">
              管理 RSS/Atom 来源、轮询状态与入库报告。
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => sourcesQuery.refetch()}>
              <RefreshCwIcon data-icon="inline-start" />
              刷新
            </Button>
            <AddSourceDialog
              open={addOpen}
              onOpenChange={setAddOpen}
              onCreate={(payload) => createMutation.mutate(payload)}
              pending={createMutation.isPending}
            />
          </div>
        </div>
        <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <MetricCard
            icon={DatabaseIcon}
            label="数据源"
            value={sources.length}
            note="当前已配置"
          />
          <MetricCard
            icon={CheckCircle2Icon}
            label="正常"
            value={healthy}
            note="最近采集成功"
          />
          <MetricCard
            icon={Clock3Icon}
            label="待首次采集"
            value={pending}
            note="等待调度器"
          />
          <MetricCard
            icon={FileTextIcon}
            label="已收报告"
            value={reports}
            note={`${attention} 个来源需关注`}
          />
        </section>
        <Card className="min-h-0 flex-1">
          <CardHeader className="border-b">
            <CardTitle>RSS 数据源</CardTitle>
            <CardDescription>
              启用后由 Celery Beat 按间隔调度；也可选择来源立即采集。
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {sourcesQuery.isLoading ? (
              <div className="flex flex-col gap-3 p-5">
                {[0, 1, 2].map((item) => (
                  <Skeleton className="h-14 w-full" key={item} />
                ))}
              </div>
            ) : sourcesQuery.isError ? (
              <Empty>
                <EmptyHeader>
                  <EmptyMedia variant="icon">
                    <AlertTriangleIcon />
                  </EmptyMedia>
                  <EmptyTitle>无法读取数据源</EmptyTitle>
                  <EmptyDescription>
                    {sourcesQuery.error.message}
                  </EmptyDescription>
                </EmptyHeader>
                <EmptyContent>
                  <Button onClick={() => sourcesQuery.refetch()}>重试</Button>
                </EmptyContent>
              </Empty>
            ) : sources.length === 0 ? (
              <Empty>
                <EmptyHeader>
                  <EmptyMedia variant="icon">
                    <RssIcon />
                  </EmptyMedia>
                  <EmptyTitle>还没有 RSS 数据源</EmptyTitle>
                  <EmptyDescription>
                    添加第一个安全厂商或平台 Feed，开始建立采集闭环。
                  </EmptyDescription>
                </EmptyHeader>
                <EmptyContent>
                  <Button onClick={() => setAddOpen(true)}>添加数据源</Button>
                </EmptyContent>
              </Empty>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>名称</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>最近成功</TableHead>
                    <TableHead>下次运行</TableHead>
                    <TableHead className="text-right">报告</TableHead>
                    <TableHead className="text-right">启用</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sources.map((source) => (
                    <TableRow
                      className={cn(
                        "cursor-pointer",
                        selectedSource?.id === source.id && "bg-accent/55"
                      )}
                      key={source.id}
                      onClick={() => setSelectedId(source.id)}
                    >
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <span className="flex size-8 items-center justify-center rounded-lg bg-secondary text-primary">
                            <RssIcon />
                          </span>
                          <div className="min-w-0">
                            <div className="font-medium">{source.name}</div>
                            <div className="max-w-72 truncate text-xs text-muted-foreground">
                              {source.url}
                            </div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <HealthBadge status={source.health_status} />
                      </TableCell>
                      <TableCell>
                        {formatDateTime(source.last_success_at)}
                      </TableCell>
                      <TableCell>
                        {formatDateTime(source.next_poll_at)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {source.report_count}
                      </TableCell>
                      <TableCell className="text-right">
                        <Switch
                          aria-label={`${source.enabled ? "停用" : "启用"} ${source.name}`}
                          checked={source.enabled}
                          disabled={updateMutation.isPending}
                          onClick={(event) => event.stopPropagation()}
                          onCheckedChange={(enabled) =>
                            updateMutation.mutate({ id: source.id, enabled })
                          }
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </main>
      <SourceInspector
        source={selectedSource}
        onPoll={(source) => pollMutation.mutate(source.id)}
        pollPending={pollMutation.isPending}
      />
    </div>
  )
}
