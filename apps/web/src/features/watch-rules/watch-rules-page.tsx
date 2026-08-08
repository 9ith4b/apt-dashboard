import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  BellRingIcon,
  EyeIcon,
  FilterIcon,
  PlusIcon,
  RadarIcon,
  ShieldCheckIcon,
} from "lucide-react"
import { useState } from "react"
import { Link } from "react-router-dom"
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
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { formatDateTime } from "@/features/intelligence/intelligence-format"
import { notificationQueryKey } from "@/features/system/system-api"
import {
  createWatchRule,
  evaluateWatchRule,
  listWatchRuleHits,
  listWatchRules,
  previewNewWatchRule,
  previewWatchRule,
  updateWatchRule,
  watchRuleQueryKey,
} from "@/features/watch-rules/watch-api"
import type {
  WatchRule,
  WatchRuleInput,
} from "@/features/watch-rules/watch-types"
import { cn } from "@/lib/utils"

function splitValues(value: string) {
  return value
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function RuleForm({
  onSubmit,
  onPreview,
  isSubmitting,
  previewCount,
}: {
  onSubmit: (payload: WatchRuleInput) => void
  onPreview: (payload: WatchRuleInput) => void
  isSubmitting: boolean
  previewCount: number | undefined
}) {
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [keywords, setKeywords] = useState("")
  const [actors, setActors] = useState("")
  const [observableTypes, setObservableTypes] = useState("")
  const [techniques, setTechniques] = useState("")
  const [minConfidence, setMinConfidence] = useState("80")
  const [severity, setSeverity] = useState<WatchRule["severity"]>("medium")

  const payload = (): WatchRuleInput => ({
    name: name.trim(),
    description: description.trim(),
    conditions: {
      keywords: splitValues(keywords),
      actor_names: splitValues(actors),
      observable_types: splitValues(observableTypes),
      technique_ids: splitValues(techniques),
      min_confidence: minConfidence ? Number(minConfidence) : null,
    },
    severity,
    enabled: true,
    created_by: "analyst",
  })
  const valid =
    name.trim().length >= 2 &&
    Boolean(
      keywords.trim() ||
      actors.trim() ||
      observableTypes.trim() ||
      techniques.trim() ||
      minConfidence
    )

  return (
    <FieldGroup>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field className="sm:col-span-2">
          <FieldLabel htmlFor="rule-name">规则名称</FieldLabel>
          <Input
            id="rule-name"
            onChange={(event) => setName(event.target.value)}
            value={name}
          />
        </Field>
        <Field className="sm:col-span-2">
          <FieldLabel htmlFor="rule-description">研判目的</FieldLabel>
          <Textarea
            id="rule-description"
            onChange={(event) => setDescription(event.target.value)}
            placeholder="说明为什么需要跟踪这组条件"
            value={description}
          />
        </Field>
        <Field>
          <FieldLabel htmlFor="rule-keywords">关键词</FieldLabel>
          <Input
            id="rule-keywords"
            onChange={(event) => setKeywords(event.target.value)}
            placeholder="fake interview, phishing"
            value={keywords}
          />
        </Field>
        <Field>
          <FieldLabel htmlFor="rule-actors">攻击组织</FieldLabel>
          <Input
            id="rule-actors"
            onChange={(event) => setActors(event.target.value)}
            placeholder="Lazarus, APT29"
            value={actors}
          />
        </Field>
        <Field>
          <FieldLabel htmlFor="rule-observable-types">
            Observable 类型
          </FieldLabel>
          <Input
            id="rule-observable-types"
            onChange={(event) => setObservableTypes(event.target.value)}
            placeholder="domain, ipv4"
            value={observableTypes}
          />
        </Field>
        <Field>
          <FieldLabel htmlFor="rule-techniques">ATT&CK 技术</FieldLabel>
          <Input
            id="rule-techniques"
            onChange={(event) => setTechniques(event.target.value)}
            placeholder="T1566.001, T1059"
            value={techniques}
          />
        </Field>
        <Field>
          <FieldLabel htmlFor="rule-confidence">最低置信度</FieldLabel>
          <Input
            id="rule-confidence"
            max={100}
            min={0}
            onChange={(event) => setMinConfidence(event.target.value)}
            type="number"
            value={minConfidence}
          />
        </Field>
        <Field>
          <FieldLabel htmlFor="rule-severity">通知级别</FieldLabel>
          <select
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            id="rule-severity"
            onChange={(event) =>
              setSeverity(event.target.value as WatchRule["severity"])
            }
            value={severity}
          >
            <option value="info">信息</option>
            <option value="low">低</option>
            <option value="medium">中</option>
            <option value="high">高</option>
            <option value="critical">严重</option>
          </select>
        </Field>
      </div>
      <p className="text-xs leading-5 text-muted-foreground">
        不同字段之间按 AND 匹配，同一字段内多个值按 OR
        匹配。规则只读取已确认事件。
      </p>
      {previewCount !== undefined ? (
        <Badge variant="secondary">预览匹配 {previewCount} 起现有事件</Badge>
      ) : null}
      <DialogFooter>
        <Button
          disabled={!valid}
          onClick={() => onPreview(payload())}
          type="button"
          variant="outline"
        >
          <EyeIcon data-icon="inline-start" />
          预览
        </Button>
        <Button
          disabled={!valid || isSubmitting}
          onClick={() => onSubmit(payload())}
          type="button"
        >
          {isSubmitting ? "创建中…" : "创建规则"}
        </Button>
      </DialogFooter>
    </FieldGroup>
  )
}

function ConditionBadges({ rule }: { rule: WatchRule }) {
  const items = [
    ...rule.conditions.keywords.map((value) => `关键词 · ${value}`),
    ...rule.conditions.actor_names.map((value) => `组织 · ${value}`),
    ...rule.conditions.observable_types.map((value) => `类型 · ${value}`),
    ...rule.conditions.technique_ids.map((value) => `ATT&CK · ${value}`),
    ...(rule.conditions.min_confidence === null
      ? []
      : [`置信度 ≥ ${rule.conditions.min_confidence}`]),
  ]
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <Badge key={item} variant="outline">
          {item}
        </Badge>
      ))}
    </div>
  )
}

export function WatchRulesPage() {
  const queryClient = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const rulesQuery = useQuery({
    queryKey: watchRuleQueryKey,
    queryFn: listWatchRules,
  })
  const rules = rulesQuery.data ?? []
  const selected = rules.find((rule) => rule.id === selectedId) ?? rules[0]
  const hitsQuery = useQuery({
    queryKey: [...watchRuleQueryKey, selected?.id, "hits"],
    queryFn: () => listWatchRuleHits(selected!.id),
    enabled: Boolean(selected),
  })
  const previewNew = useMutation({ mutationFn: previewNewWatchRule })
  const previewExisting = useMutation({ mutationFn: previewWatchRule })
  const createMutation = useMutation({
    mutationFn: createWatchRule,
    onSuccess: async (rule) => {
      await queryClient.invalidateQueries({ queryKey: watchRuleQueryKey })
      setSelectedId(rule.id)
      setDialogOpen(false)
      previewNew.reset()
      toast.success("关注规则已创建")
    },
  })
  const updateMutation = useMutation({
    mutationFn: ({ rule, enabled }: { rule: WatchRule; enabled: boolean }) =>
      updateWatchRule(rule.id, { enabled, expected_version: rule.version }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: watchRuleQueryKey }),
  })
  const evaluateMutation = useMutation({
    mutationFn: evaluateWatchRule,
    onSuccess: async (result) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: watchRuleQueryKey }),
        queryClient.invalidateQueries({ queryKey: notificationQueryKey }),
      ])
      toast.success(`评估完成，新建 ${result.created_hit_count} 条命中`)
    },
  })

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <header className="flex flex-col justify-between gap-4 border-b border-border bg-card px-4 py-4 sm:flex-row sm:items-center sm:px-6">
        <div>
          <div className="flex items-center gap-2">
            <RadarIcon className="size-5 text-primary" />
            <h1 className="text-xl font-semibold">关注规则</h1>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            用结构化条件持续监测已确认事件，并生成可追溯站内通知
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <PlusIcon data-icon="inline-start" />
              新建规则
            </Button>
          </DialogTrigger>
          <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
            <DialogHeader>
              <DialogTitle>新建关注规则</DialogTitle>
              <DialogDescription>
                先预览历史命中，再决定是否启用持续监测。
              </DialogDescription>
            </DialogHeader>
            <RuleForm
              isSubmitting={createMutation.isPending}
              onPreview={(payload) => previewNew.mutate(payload)}
              onSubmit={(payload) => createMutation.mutate(payload)}
              previewCount={previewNew.data?.match_count}
            />
          </DialogContent>
        </Dialog>
      </header>

      {rulesQuery.isPending ? (
        <div className="grid gap-4 p-6 lg:grid-cols-[20rem_minmax(0,1fr)]">
          <Skeleton className="h-[32rem]" />
          <Skeleton className="h-[32rem]" />
        </div>
      ) : rulesQuery.isError ? (
        <Empty>
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <FilterIcon />
            </EmptyMedia>
            <EmptyTitle>规则加载失败</EmptyTitle>
            <EmptyDescription>{rulesQuery.error.message}</EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : !rules.length ? (
        <Empty>
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <BellRingIcon />
            </EmptyMedia>
            <EmptyTitle>还没有关注规则</EmptyTitle>
            <EmptyDescription>
              创建规则后可先预览历史事件，再持续接收新命中通知。
            </EmptyDescription>
          </EmptyHeader>
          <Button onClick={() => setDialogOpen(true)}>
            <PlusIcon data-icon="inline-start" />
            创建第一个规则
          </Button>
        </Empty>
      ) : (
        <div className="grid min-h-0 flex-1 lg:grid-cols-[20rem_minmax(0,1fr)]">
          <aside className="max-h-80 overflow-y-auto border-b border-border bg-card lg:max-h-none lg:border-r lg:border-b-0">
            {rules.map((rule) => (
              <button
                className={cn(
                  "w-full border-b border-border p-4 text-left hover:bg-accent/40",
                  selected?.id === rule.id &&
                    "bg-accent/55 ring-1 ring-primary ring-inset"
                )}
                key={rule.id}
                onClick={() => {
                  setSelectedId(rule.id)
                  previewExisting.reset()
                }}
                type="button"
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="truncate text-sm font-semibold">{rule.name}</p>
                  <span
                    className={cn(
                      "size-2 rounded-full",
                      rule.enabled ? "bg-confirmed" : "bg-muted-foreground"
                    )}
                  />
                </div>
                <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">
                  {rule.description || "暂无说明"}
                </p>
                <div className="mt-3 flex gap-2">
                  <Badge variant="secondary">{rule.hit_count} 次命中</Badge>
                  <Badge variant="outline">{rule.severity}</Badge>
                </div>
              </button>
            ))}
          </aside>
          {selected ? (
            <main className="flex min-h-0 flex-col gap-4 overflow-y-auto p-4 sm:p-6">
              <Card>
                <CardHeader className="flex-row items-start justify-between gap-4">
                  <div>
                    <CardTitle>{selected.name}</CardTitle>
                    <CardDescription className="mt-1">
                      {selected.description || "暂无研判目的说明"}
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">
                      {selected.enabled ? "已启用" : "已停用"}
                    </span>
                    <Switch
                      aria-label="启用规则"
                      checked={selected.enabled}
                      disabled={updateMutation.isPending}
                      onCheckedChange={(enabled) =>
                        updateMutation.mutate({ rule: selected, enabled })
                      }
                    />
                  </div>
                </CardHeader>
                <CardContent>
                  <ConditionBadges rule={selected} />
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button
                      onClick={() => previewExisting.mutate(selected.id)}
                      size="sm"
                      variant="outline"
                    >
                      <EyeIcon data-icon="inline-start" />
                      预览现有匹配
                    </Button>
                    <Button
                      disabled={evaluateMutation.isPending}
                      onClick={() => evaluateMutation.mutate(selected.id)}
                      size="sm"
                    >
                      <ShieldCheckIcon data-icon="inline-start" />
                      运行并记录命中
                    </Button>
                    {previewExisting.data ? (
                      <Badge variant="secondary">
                        预览 {previewExisting.data.match_count} 起
                      </Badge>
                    ) : null}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>命中记录</CardTitle>
                  <CardDescription>
                    规则运行和新事件确认都会在这里保留唯一命中
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex flex-col gap-3">
                  {hitsQuery.data?.length ? (
                    hitsQuery.data.map((hit) => (
                      <Link
                        className="rounded-lg border border-border p-4 hover:bg-accent/40"
                        key={hit.id}
                        to={`/events?event=${hit.subject_id}`}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-sm font-medium">
                            {hit.subject_title}
                          </p>
                          <span className="text-xs text-muted-foreground">
                            {formatDateTime(hit.created_at)}
                          </span>
                        </div>
                        <p className="mt-2 text-xs text-muted-foreground">
                          匹配字段：{Object.keys(hit.matched_on).join("、")}
                        </p>
                      </Link>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      尚未记录命中。预览不会写入通知。
                    </p>
                  )}
                </CardContent>
              </Card>
            </main>
          ) : null}
        </div>
      )}
    </div>
  )
}
