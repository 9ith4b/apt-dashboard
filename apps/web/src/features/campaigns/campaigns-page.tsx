import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  AlertCircleIcon,
  BellPlusIcon,
  BellRingIcon,
  BotIcon,
  CalendarRangeIcon,
  FlagTriangleRightIcon,
  GitBranchPlusIcon,
  ListChecksIcon,
  PlusIcon,
  RefreshCwIcon,
  ShieldUserIcon,
  TargetIcon,
  Trash2Icon,
} from "lucide-react"
import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
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
import {
  assignCampaignEvent,
  backfillCampaigns,
  campaignAutomationQueryKey,
  campaignQueryKey,
  createCampaign,
  getCampaign,
  getCampaignAutomationStatus,
  listCampaigns,
  removeCampaignEvent,
} from "@/features/campaigns/campaign-api"
import type {
  CampaignDetail,
  CampaignStage,
  CampaignStatus,
  CampaignSummary,
} from "@/features/campaigns/campaign-types"
import {
  eventQueryKey,
  listThreatEvents,
} from "@/features/intelligence/intelligence-api"
import { formatDateTime } from "@/features/intelligence/intelligence-format"
import type { ThreatEventSummary } from "@/features/intelligence/intelligence-types"
import {
  createWatchRule,
  listWatchRules,
  watchRuleQueryKey,
} from "@/features/watch-rules/watch-api"
import { cn } from "@/lib/utils"

const STAGE_LABELS: Record<CampaignStage, string> = {
  unknown: "未映射阶段",
  reconnaissance: "侦察",
  "resource-development": "资源开发",
  "initial-access": "初始访问",
  execution: "执行",
  persistence: "持久化",
  "privilege-escalation": "权限提升",
  "defense-evasion": "防御规避",
  "credential-access": "凭据访问",
  discovery: "发现",
  "lateral-movement": "横向移动",
  collection: "收集",
  "command-and-control": "命令与控制",
  exfiltration: "数据外传",
  impact: "影响",
}

const STATUS_LABELS: Record<CampaignStatus, string> = {
  active: "进行中",
  inactive: "不活跃",
  closed: "已关闭",
}

function CampaignRow({
  campaign,
  selected,
  onSelect,
}: {
  campaign: CampaignSummary
  selected: boolean
  onSelect: (id: string) => void
}) {
  return (
    <button
      className={cn(
        "w-full border-b border-border p-4 text-left transition-colors last:border-b-0 hover:bg-accent/40 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
        selected && "bg-accent/55 ring-1 ring-primary ring-inset"
      )}
      onClick={() => onSelect(campaign.id)}
      type="button"
    >
      <div className="flex items-start justify-between gap-3">
        <Badge
          variant={campaign.status === "active" ? "confirmed" : "secondary"}
        >
          {STATUS_LABELS[campaign.status]}
        </Badge>
        <Badge variant="outline">{campaign.event_count} 起事件</Badge>
      </div>
      <h3 className="mt-2 line-clamp-2 text-sm leading-6 font-semibold">
        {campaign.name}
      </h3>
      <p className="mt-2 truncate text-xs text-primary">
        {campaign.actor_names.join(" · ") || "尚未关联攻击者"}
      </p>
      <div className="mt-3 flex flex-wrap gap-1">
        {campaign.stages.slice(0, 3).map((stage) => (
          <Badge key={stage} variant="secondary">
            {STAGE_LABELS[stage as CampaignStage] ?? stage}
          </Badge>
        ))}
      </div>
      <p className="mt-3 text-xs text-muted-foreground">
        最近活动 {formatDateTime(campaign.last_seen)}
      </p>
    </button>
  )
}

function CreateCampaignDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated: (campaignId: string) => void
}) {
  const queryClient = useQueryClient()
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [status, setStatus] = useState<CampaignStatus>("active")
  const mutation = useMutation({
    mutationFn: () =>
      createCampaign({
        name: name.trim(),
        description: description.trim(),
        status,
      }),
    onSuccess: (campaign) => {
      toast.success("Campaign 已创建")
      void queryClient.invalidateQueries({ queryKey: campaignQueryKey })
      onCreated(campaign.id)
      onOpenChange(false)
      setName("")
      setDescription("")
    },
    onError: (error: Error) => toast.error(error.message),
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>人工补录攻击活动</DialogTitle>
          <DialogDescription>
            仅用于补充系统尚未覆盖的历史活动。日常攻击活动会由 AI
            从已确认事件中持续归纳。
          </DialogDescription>
        </DialogHeader>
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="campaign-name">名称</FieldLabel>
            <Input
              id="campaign-name"
              onChange={(event) => setName(event.target.value)}
              placeholder="例如：Operation Dream Job"
              value={name}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="campaign-description">说明</FieldLabel>
            <Textarea
              id="campaign-description"
              onChange={(event) => setDescription(event.target.value)}
              placeholder="记录命名来源、时间范围和分析假设"
              value={description}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="campaign-status">状态</FieldLabel>
            <select
              className="h-8 rounded-lg border border-input bg-background px-2.5 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
              id="campaign-status"
              onChange={(event) =>
                setStatus(event.target.value as CampaignStatus)
              }
              value={status}
            >
              {Object.entries(STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
        </FieldGroup>
        <DialogFooter>
          <Button
            disabled={name.trim().length < 3 || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            <PlusIcon data-icon="inline-start" />
            保存补录
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function AssignEventDialog({
  campaign,
  events,
  open,
  onOpenChange,
}: {
  campaign: CampaignDetail
  events: ThreatEventSummary[]
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const queryClient = useQueryClient()
  const availableEvents = useMemo(
    () =>
      events.filter(
        (event) => !campaign.events.some((item) => item.event_id === event.id)
      ),
    [campaign.events, events]
  )
  const [eventId, setEventId] = useState("")
  const [stage, setStage] = useState<CampaignStage>("unknown")
  const [confidence, setConfidence] = useState("80")
  const [note, setNote] = useState("")

  const selectedEventId = availableEvents.some((event) => event.id === eventId)
    ? eventId
    : (availableEvents[0]?.id ?? "")

  const mutation = useMutation({
    mutationFn: () =>
      assignCampaignEvent(campaign.id, {
        event_id: selectedEventId,
        stage,
        confidence: Number(confidence),
        evidence_note: note.trim(),
        expected_version: campaign.version,
      }),
    onSuccess: () => {
      toast.success("事件已加入 Campaign 时间线")
      void queryClient.invalidateQueries({ queryKey: campaignQueryKey })
      void queryClient.invalidateQueries({
        queryKey: ["campaign", campaign.id],
      })
      onOpenChange(false)
      setNote("")
    },
    onError: (error: Error) => toast.error(error.message),
  })
  const parsedConfidence = Number(confidence)
  const valid =
    Boolean(selectedEventId) &&
    note.trim().length >= 3 &&
    Number.isInteger(parsedConfidence) &&
    parsedConfidence >= 0 &&
    parsedConfidence <= 100

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>确认 Campaign 事件归属</DialogTitle>
          <DialogDescription>
            时间接近不会自动确认归属。请选择阶段并写明能够复核的判断依据。
          </DialogDescription>
        </DialogHeader>
        {availableEvents.length ? (
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="campaign-event">已确认事件</FieldLabel>
              <select
                className="h-8 w-full rounded-lg border border-input bg-background px-2.5 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                id="campaign-event"
                onChange={(event) => setEventId(event.target.value)}
                value={selectedEventId}
              >
                {availableEvents.map((event) => (
                  <option key={event.id} value={event.id}>
                    {event.title}
                  </option>
                ))}
              </select>
            </Field>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field>
                <FieldLabel htmlFor="campaign-stage">攻击阶段</FieldLabel>
                <select
                  className="h-8 w-full rounded-lg border border-input bg-background px-2.5 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                  id="campaign-stage"
                  onChange={(event) =>
                    setStage(event.target.value as CampaignStage)
                  }
                  value={stage}
                >
                  {Object.entries(STAGE_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </Field>
              <Field>
                <FieldLabel htmlFor="campaign-confidence">
                  归属置信度
                </FieldLabel>
                <Input
                  id="campaign-confidence"
                  max={100}
                  min={0}
                  onChange={(event) => setConfidence(event.target.value)}
                  type="number"
                  value={confidence}
                />
              </Field>
            </div>
            <Field>
              <FieldLabel htmlFor="campaign-note">归属依据</FieldLabel>
              <Textarea
                id="campaign-note"
                onChange={(event) => setNote(event.target.value)}
                placeholder="例如：文章明确使用该行动名，且攻击者、基础设施与阶段一致"
                value={note}
              />
            </Field>
          </FieldGroup>
        ) : (
          <Empty className="min-h-48 border-0">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <ListChecksIcon />
              </EmptyMedia>
              <EmptyTitle>没有可加入的已确认事件</EmptyTitle>
              <EmptyDescription>
                等待AI生成更多事件，或当前全部事件已经属于该 Campaign。
              </EmptyDescription>
            </EmptyHeader>
            <Button asChild variant="outline">
              <Link to="/reviews">查看AI分析</Link>
            </Button>
          </Empty>
        )}
        {availableEvents.length > 0 && (
          <DialogFooter>
            <Button
              disabled={!valid || mutation.isPending}
              onClick={() => mutation.mutate()}
            >
              <GitBranchPlusIcon data-icon="inline-start" />
              确认加入时间线
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  )
}

function CampaignDetailPanel({
  campaign,
  events,
  isWatched,
}: {
  campaign: CampaignDetail
  events: ThreatEventSummary[]
  isWatched: boolean
}) {
  const queryClient = useQueryClient()
  const [assignOpen, setAssignOpen] = useState(false)
  const watchMutation = useMutation({
    mutationFn: () =>
      createWatchRule({
        name: `关注：${campaign.name}`,
        description: `持续关注攻击活动“${campaign.name}”的新确认事件。规则由活动详情生成，无需重复维护关键词。`,
        conditions: {
          campaign_ids: [campaign.id],
          keywords: [],
          actor_names: [],
          observable_types: [],
          technique_ids: [],
          min_confidence: null,
        },
        severity: "high",
        enabled: true,
        created_by: "analyst",
      }),
    onSuccess: () => {
      toast.success("已关注此攻击活动")
      void queryClient.invalidateQueries({ queryKey: watchRuleQueryKey })
    },
    onError: (error: Error) => toast.error(error.message),
  })
  const removeMutation = useMutation({
    mutationFn: (eventId: string) =>
      removeCampaignEvent(campaign.id, eventId, campaign.version),
    onSuccess: () => {
      toast.success("事件已从 Campaign 中移除")
      void queryClient.invalidateQueries({ queryKey: campaignQueryKey })
      void queryClient.invalidateQueries({
        queryKey: ["campaign", campaign.id],
      })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-5 overflow-x-hidden overflow-y-auto overscroll-contain p-4 sm:p-6 [&>*]:shrink-0">
      <div className="flex flex-col justify-between gap-4 xl:flex-row xl:items-start">
        <div className="max-w-4xl">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <Badge
              variant={campaign.status === "active" ? "confirmed" : "secondary"}
            >
              {STATUS_LABELS[campaign.status]}
            </Badge>
            <Badge variant="outline">AI 持续归纳</Badge>
          </div>
          <h2 className="text-2xl leading-9 font-semibold">{campaign.name}</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {campaign.description || "暂无 Campaign 说明。"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {isWatched ? (
            <Button asChild variant="outline">
              <Link to="/watch-rules">
                <BellRingIcon data-icon="inline-start" />
                已关注 · 查看规则
              </Link>
            </Button>
          ) : (
            <Button
              disabled={watchMutation.isPending}
              onClick={() => watchMutation.mutate()}
            >
              <BellPlusIcon data-icon="inline-start" />
              {watchMutation.isPending ? "正在关注…" : "关注此活动"}
            </Button>
          )}
          <Button onClick={() => setAssignOpen(true)} variant="outline">
            <GitBranchPlusIcon data-icon="inline-start" />
            调整事件归属
          </Button>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {[
          {
            label: "已确认事件",
            value: campaign.event_count,
            icon: ListChecksIcon,
          },
          {
            label: "攻击组织",
            value: campaign.actor_names.length,
            icon: ShieldUserIcon,
          },
          {
            label: "覆盖阶段",
            value: campaign.stages.length,
            icon: TargetIcon,
          },
        ].map(({ label, value, icon: Icon }) => (
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
          <CardTitle>攻击活动阶段时间线</CardTitle>
          <CardDescription>
            {formatDateTime(campaign.first_seen)} 至{" "}
            {formatDateTime(campaign.last_seen)}
            ；系统持续沉淀，人工可修正事件归属。
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {campaign.events.length ? (
            campaign.events.map((event, index) => (
              <div className="relative pl-8" key={event.event_id}>
                {index < campaign.events.length - 1 && (
                  <span className="absolute top-7 bottom-[-0.75rem] left-3.5 w-px bg-border" />
                )}
                <span className="absolute top-4 left-1.5 flex size-4 items-center justify-center rounded-full border-2 border-primary bg-background" />
                <div className="rounded-lg border border-border p-4">
                  <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="confirmed">
                          {STAGE_LABELS[event.stage]}
                        </Badge>
                        <Badge variant="outline">
                          归属置信度 {event.confidence}%
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {formatDateTime(event.event_first_seen)}
                        </span>
                      </div>
                      <h3 className="mt-2 text-sm leading-6 font-semibold">
                        {event.event_title}
                      </h3>
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">
                        {event.event_summary || "暂无事件摘要。"}
                      </p>
                      <div className="mt-3 rounded-md bg-muted/60 p-3">
                        <p className="text-xs font-medium">归属依据</p>
                        <p className="mt-1 text-xs leading-5 text-muted-foreground">
                          {event.evidence_note}
                        </p>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-1">
                        {event.actor_names.map((actor) => (
                          <Badge key={actor} variant="secondary">
                            {actor}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    <Button
                      aria-label={`从 Campaign 移除 ${event.event_title}`}
                      disabled={removeMutation.isPending}
                      onClick={() => removeMutation.mutate(event.event_id)}
                      size="icon-sm"
                      variant="ghost"
                    >
                      <Trash2Icon />
                    </Button>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <Empty className="min-h-56 border-0">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <FlagTriangleRightIcon />
                </EmptyMedia>
                <EmptyTitle>Campaign 还没有事件</EmptyTitle>
                <EmptyDescription>
                  AI
                  归纳到该活动的新事件会显示在这里；你也可以在发现错误或缺失时人工修正。
                </EmptyDescription>
              </EmptyHeader>
              <Button onClick={() => setAssignOpen(true)}>人工补充事件</Button>
            </Empty>
          )}
        </CardContent>
      </Card>

      <AssignEventDialog
        key={campaign.id}
        campaign={campaign}
        events={events}
        onOpenChange={setAssignOpen}
        open={assignOpen}
      />
    </div>
  )
}

export function CampaignsPage() {
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const campaignsQuery = useQuery({
    queryKey: campaignQueryKey,
    queryFn: listCampaigns,
  })
  const eventsQuery = useQuery({
    queryKey: eventQueryKey,
    queryFn: listThreatEvents,
  })
  const watchRulesQuery = useQuery({
    queryKey: watchRuleQueryKey,
    queryFn: listWatchRules,
  })
  const automationQuery = useQuery({
    queryKey: campaignAutomationQueryKey,
    queryFn: getCampaignAutomationStatus,
    refetchInterval: 15_000,
  })
  const backfillMutation = useMutation({
    mutationFn: () => backfillCampaigns({ limit: 200, force: true }),
    onSuccess: (result) => {
      toast.success(
        result.queued
          ? `已将 ${result.queued} 个事件加入AI聚类队列`
          : "当前没有需要重新扫描的事件"
      )
      void queryClient.invalidateQueries({
        queryKey: campaignAutomationQueryKey,
      })
      void queryClient.invalidateQueries({ queryKey: campaignQueryKey })
    },
    onError: (error: Error) => toast.error(error.message),
  })
  const campaigns = campaignsQuery.data ?? []
  const selected =
    campaigns.find((campaign) => campaign.id === selectedId) ?? campaigns[0]
  const detailQuery = useQuery({
    queryKey: ["campaign", selected?.id],
    queryFn: () => getCampaign(selected!.id),
    enabled: Boolean(selected),
  })

  return (
    <div className="grid min-h-0 flex-1 grid-rows-[auto_minmax(0,1fr)]">
      <header className="border-b border-border bg-surface px-4 py-4 sm:px-6">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
          <div>
            <div className="flex items-center gap-2">
              <CalendarRangeIcon className="size-5 text-primary" />
              <h1 className="text-xl font-semibold">攻击活动</h1>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              AI 将相关事件归纳为持续行动；人工只在阅读时纠正或补充
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge
              variant={automationQuery.data?.ready ? "confirmed" : "outline"}
            >
              {automationQuery.data?.ready ? "AI聚类运行中" : "AI聚类未就绪"}
            </Badge>
            <Button
              disabled={
                !automationQuery.data?.ready || backfillMutation.isPending
              }
              onClick={() => backfillMutation.mutate()}
              variant="outline"
            >
              <RefreshCwIcon data-icon="inline-start" />
              {backfillMutation.isPending ? "正在排队" : "重新扫描"}
            </Button>
            <Button onClick={() => setCreateOpen(true)} variant="outline">
              <PlusIcon data-icon="inline-start" />
              人工补录
            </Button>
          </div>
        </div>
        <Alert className="mt-4 max-w-3xl">
          <BotIcon />
          <AlertTitle>事实由 AI 沉淀，关注由你决定</AlertTitle>
          <AlertDescription>
            {automationQuery.data ? (
              <>
                共 {automationQuery.data.confirmed_event_count}{" "}
                个已确认事件，其中 {automationQuery.data.eligible_event_count}{" "}
                个具备聚类证据；已自动归类{" "}
                {automationQuery.data.assigned_event_count} 个，剩余{" "}
                {automationQuery.data.unassigned_event_count} 个待发现稳定关联
                {automationQuery.data.pending_job_count
                  ? `，${automationQuery.data.pending_job_count} 个正在排队处理`
                  : ""}
                。需要持续跟踪时，在活动详情点击“关注此活动”，系统会自动生成监控规则。
              </>
            ) : (
              "这里记录已经发生的攻击活动。系统会自动发现稳定关联，人工只需在阅读时纠错。"
            )}
          </AlertDescription>
        </Alert>
      </header>

      {campaignsQuery.isPending ? (
        <div className="grid min-h-0 gap-4 p-6 lg:grid-cols-[22rem_minmax(0,1fr)]">
          <Skeleton className="h-[34rem]" />
          <Skeleton className="h-[34rem]" />
        </div>
      ) : campaignsQuery.isError ? (
        <Empty className="border-0">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <AlertCircleIcon />
            </EmptyMedia>
            <EmptyTitle>Campaign 加载失败</EmptyTitle>
            <EmptyDescription>{campaignsQuery.error.message}</EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : !campaigns.length ? (
        <Empty className="border-0">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <FlagTriangleRightIcon />
            </EmptyMedia>
            <EmptyTitle>AI 尚未归纳出攻击活动</EmptyTitle>
            <EmptyDescription>
              当多个确认事件在攻击者、基础设施、技术或时间窗口上形成稳定关联后，将自动沉淀在这里。
            </EmptyDescription>
          </EmptyHeader>
          <div className="flex flex-wrap justify-center gap-2">
            <Button asChild>
              <Link to="/events">
                <ListChecksIcon data-icon="inline-start" />
                查看已确认事件
              </Link>
            </Button>
            <Button onClick={() => setCreateOpen(true)} variant="outline">
              <PlusIcon data-icon="inline-start" />
              补录历史活动
            </Button>
          </div>
        </Empty>
      ) : (
        <div className="grid min-h-0 lg:grid-cols-[22rem_minmax(0,1fr)]">
          <aside className="max-h-80 overflow-y-auto border-b border-border bg-card lg:max-h-none lg:border-r lg:border-b-0">
            {campaigns.map((campaign) => (
              <CampaignRow
                campaign={campaign}
                key={campaign.id}
                onSelect={setSelectedId}
                selected={selected?.id === campaign.id}
              />
            ))}
          </aside>
          <main className="flex min-h-0 min-w-0 flex-col">
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
                  <EmptyTitle>Campaign 详情加载失败</EmptyTitle>
                  <EmptyDescription>
                    {detailQuery.error?.message}
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            ) : (
              <CampaignDetailPanel
                campaign={detailQuery.data}
                events={eventsQuery.data ?? []}
                isWatched={Boolean(
                  watchRulesQuery.data?.some((rule) =>
                    rule.conditions.campaign_ids.includes(detailQuery.data.id)
                  )
                )}
              />
            )}
          </main>
        </div>
      )}

      <CreateCampaignDialog
        onCreated={setSelectedId}
        onOpenChange={setCreateOpen}
        open={createOpen}
      />
    </div>
  )
}
