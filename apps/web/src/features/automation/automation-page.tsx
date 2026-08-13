import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  BotIcon,
  CheckCircle2Icon,
  CircleAlertIcon,
  FlaskConicalIcon,
  KeyRoundIcon,
  PlusIcon,
  RefreshCcwIcon,
  SaveIcon,
  Settings2Icon,
  ShieldCheckIcon,
  SparklesIcon,
  Trash2Icon,
  type LucideIcon,
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
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
  FieldSet,
  FieldTitle,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { useAuth } from "@/features/auth/auth-context"
import { formatDateTime } from "@/features/intelligence/intelligence-format"

import {
  automationQueryKey,
  backfillFilteredReports,
  createModelConfig,
  deleteModelConfig,
  getAutomationStatus,
  getProcessingPolicy,
  listModelConfigs,
  testModelConfig,
  updateModelConfig,
  updateProcessingPolicy,
} from "./automation-api"
import type {
  AIModelConfig,
  AIModelConfigInput,
  AIProcessingPolicy,
  AIProvider,
} from "./automation-types"

const providerLabels: Record<AIProvider, string> = {
  openai: "OpenAI",
  deepseek: "DeepSeek",
  dashscope: "阿里云百炼",
  siliconflow: "SiliconFlow",
  ollama: "Ollama",
  custom: "兼容接口",
}

const providerDefaults: Record<AIProvider, string> = {
  openai: "https://api.openai.com/v1",
  deepseek: "https://api.deepseek.com/v1",
  dashscope: "https://dashscope.aliyuncs.com/compatible-mode/v1",
  siliconflow: "https://api.siliconflow.cn/v1",
  ollama: "http://host.docker.internal:11434/v1",
  custom: "https://example.com/v1",
}

const emptyModel: AIModelConfigInput = {
  name: "",
  provider: "openai",
  base_url: providerDefaults.openai,
  model: "",
  api_key: "",
  enabled: true,
  is_default: true,
  timeout_seconds: 90,
  temperature: 0.1,
}

function modelFormValue(selected: AIModelConfig | null): AIModelConfigInput {
  return selected
    ? {
        name: selected.name,
        provider: selected.provider,
        base_url: selected.base_url,
        model: selected.model,
        api_key: "",
        enabled: selected.enabled,
        is_default: selected.is_default,
        timeout_seconds: selected.timeout_seconds,
        temperature: selected.temperature,
      }
    : emptyModel
}

function ModelForm({
  selected,
  pending,
  onCancel,
  onSave,
}: {
  selected: AIModelConfig | null
  pending: boolean
  onCancel: () => void
  onSave: (payload: AIModelConfigInput) => void
}) {
  const [form, setForm] = useState<AIModelConfigInput>(() =>
    modelFormValue(selected)
  )

  const valid =
    form.name.trim().length > 0 &&
    form.model.trim().length > 0 &&
    form.base_url.trim().length > 0 &&
    (selected?.has_api_key ||
      form.provider === "ollama" ||
      Boolean(form.api_key?.trim()))

  return (
    <Card>
      <CardHeader>
        <CardTitle>{selected ? "编辑模型配置" : "添加模型配置"}</CardTitle>
        <CardDescription>
          支持 OpenAI Chat Completions 兼容接口；API Key
          只会加密保存，页面不会回显。
        </CardDescription>
      </CardHeader>
      <CardContent>
        <FieldSet>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="model-name">配置名称</FieldLabel>
              <Input
                id="model-name"
                placeholder="例如：主分析模型"
                value={form.name}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    name: event.target.value,
                  }))
                }
              />
            </Field>
            <Field>
              <FieldLabel>供应商</FieldLabel>
              <ToggleGroup
                aria-label="模型供应商"
                className="flex-wrap justify-start"
                type="single"
                value={form.provider}
                variant="outline"
                onValueChange={(value) => {
                  if (!value) return
                  const provider = value as AIProvider
                  setForm((current) => ({
                    ...current,
                    provider,
                    base_url: providerDefaults[provider],
                  }))
                }}
              >
                {(Object.keys(providerLabels) as AIProvider[]).map(
                  (provider) => (
                    <ToggleGroupItem key={provider} value={provider}>
                      {providerLabels[provider]}
                    </ToggleGroupItem>
                  )
                )}
              </ToggleGroup>
            </Field>
            <div className="grid gap-5 md:grid-cols-2">
              <Field>
                <FieldLabel htmlFor="base-url">API Base URL</FieldLabel>
                <Input
                  id="base-url"
                  placeholder="https://api.example.com/v1"
                  value={form.base_url}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      base_url: event.target.value,
                    }))
                  }
                />
                <FieldDescription>
                  填写到 /v1，系统会调用 /chat/completions。
                </FieldDescription>
              </Field>
              <Field>
                <FieldLabel htmlFor="model-id">模型名称</FieldLabel>
                <Input
                  id="model-id"
                  placeholder="例如：gpt-5-mini 或 qwen3:32b"
                  value={form.model}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      model: event.target.value,
                    }))
                  }
                />
              </Field>
            </div>
            <Field>
              <FieldLabel htmlFor="api-key">
                <KeyRoundIcon aria-hidden="true" /> API Key
              </FieldLabel>
              <Input
                autoComplete="new-password"
                id="api-key"
                placeholder={
                  selected?.has_api_key
                    ? "已安全保存；留空表示保持不变"
                    : form.provider === "ollama"
                      ? "本地 Ollama 可留空"
                      : "输入供应商 API Key"
                }
                type="password"
                value={form.api_key}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    api_key: event.target.value,
                  }))
                }
              />
            </Field>
            <div className="grid gap-5 md:grid-cols-2">
              <Field>
                <FieldLabel htmlFor="model-timeout">超时时间（秒）</FieldLabel>
                <Input
                  id="model-timeout"
                  max={300}
                  min={5}
                  type="number"
                  value={form.timeout_seconds}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      timeout_seconds: Number(event.target.value),
                    }))
                  }
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="model-temperature">Temperature</FieldLabel>
                <Input
                  id="model-temperature"
                  max={2}
                  min={0}
                  step={0.1}
                  type="number"
                  value={form.temperature}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      temperature: Number(event.target.value),
                    }))
                  }
                />
                <FieldDescription>情报抽取建议保持在 0～0.2。</FieldDescription>
              </Field>
            </div>
            <Field orientation="horizontal">
              <Switch
                checked={form.enabled}
                id="model-enabled"
                onCheckedChange={(enabled) =>
                  setForm((current) => ({ ...current, enabled }))
                }
              />
              <FieldLabel htmlFor="model-enabled">启用这个配置</FieldLabel>
            </Field>
            <Field orientation="horizontal">
              <Switch
                checked={form.is_default}
                id="model-default"
                onCheckedChange={(isDefault) =>
                  setForm((current) => ({ ...current, is_default: isDefault }))
                }
              />
              <FieldLabel htmlFor="model-default">设为系统默认模型</FieldLabel>
            </Field>
          </FieldGroup>
        </FieldSet>
      </CardContent>
      <CardFooter className="justify-end gap-2">
        {selected ? (
          <Button onClick={onCancel} type="button" variant="outline">
            取消编辑
          </Button>
        ) : null}
        <Button
          disabled={!valid || pending}
          onClick={() => onSave(form)}
          type="button"
        >
          <SaveIcon data-icon="inline-start" />
          {selected ? "保存修改" : "保存配置"}
        </Button>
      </CardFooter>
    </Card>
  )
}

function PolicyForm({
  policy,
  pending,
  onSave,
}: {
  policy: AIProcessingPolicy
  pending: boolean
  onSave: (policy: AIProcessingPolicy) => void
}) {
  const [form, setForm] = useState(policy)

  const numericFields = [
    ["relevance_threshold", "APT相关性阈值", "用于标记需要关注的边界判断。"],
    [
      "auto_approve_threshold",
      "自动确认阈值",
      "低于此值会记录异常；无人值守模式下不阻断AI结论。",
    ],
    ["auto_reject_threshold", "自动排除阈值", "AI明确判断无关时自动排除。"],
    [
      "minimum_evidence_coverage",
      "最低证据覆盖率",
      "低于此值会进入异常关注清单。",
    ],
    [
      "indicator_auto_threshold",
      "Indicator自动维护阈值",
      "达到阈值且被AI判定为恶意时自动创建或更新Indicator。",
    ],
  ] as const

  return (
    <Card>
      <CardHeader>
        <CardTitle>自动化决策策略</CardTitle>
        <CardDescription>
          AI默认完成采集后的判断与沉淀；人工修正作为高优先级覆盖，而不是处理门禁。
        </CardDescription>
      </CardHeader>
      <CardContent>
        <FieldSet>
          <FieldGroup>
            <Field orientation="horizontal">
              <Switch
                checked={form.automation_enabled}
                id="automation-enabled"
                onCheckedChange={(automationEnabled) =>
                  setForm((current) => ({
                    ...current,
                    automation_enabled: automationEnabled,
                  }))
                }
              />
              <FieldLabel htmlFor="automation-enabled">
                <FieldTitle>启用全量AI处理</FieldTitle>
                <FieldDescription>
                  新采集文章不再由关键词决定去留，而是进入AI语义分析。
                </FieldDescription>
              </FieldLabel>
            </Field>
            <Field orientation="horizontal">
              <Switch
                checked={form.unattended_mode}
                id="unattended-mode"
                onCheckedChange={(unattendedMode) =>
                  setForm((current) => ({
                    ...current,
                    unattended_mode: unattendedMode,
                  }))
                }
              />
              <FieldLabel htmlFor="unattended-mode">
                <FieldTitle>无人值守运营</FieldTitle>
                <FieldDescription>
                  AI成功完成后直接发布或排除；低置信度与证据缺口只记录异常，不等待人工放行。
                </FieldDescription>
              </FieldLabel>
            </Field>
            <Field orientation="horizontal">
              <Switch
                checked={form.require_verification}
                id="verification-enabled"
                onCheckedChange={(requireVerification) =>
                  setForm((current) => ({
                    ...current,
                    require_verification: requireVerification,
                  }))
                }
              />
              <FieldLabel htmlFor="verification-enabled">
                <FieldTitle>独立AI验证</FieldTitle>
                <FieldDescription>
                  第二次模型调用只负责检查证据、归因和逻辑冲突。
                </FieldDescription>
              </FieldLabel>
            </Field>
            <Field orientation="horizontal">
              <Switch
                checked={form.auto_create_events}
                id="auto-events"
                onCheckedChange={(autoCreateEvents) =>
                  setForm((current) => ({
                    ...current,
                    auto_create_events: autoCreateEvents,
                  }))
                }
              />
              <FieldLabel htmlFor="auto-events">
                <FieldTitle>自动生成确认事件</FieldTitle>
                <FieldDescription>
                  根据AI结论自动创建事件、组织关系和狩猎知识。
                </FieldDescription>
              </FieldLabel>
            </Field>
            <Field orientation="horizontal">
              <Switch
                checked={form.auto_manage_indicators}
                id="auto-indicators"
                onCheckedChange={(autoManageIndicators) =>
                  setForm((current) => ({
                    ...current,
                    auto_manage_indicators: autoManageIndicators,
                  }))
                }
              />
              <FieldLabel htmlFor="auto-indicators">
                <FieldTitle>AI自动维护 Indicator</FieldTitle>
                <FieldDescription>
                  结合原文语境自动区分Observable与恶意Indicator，并管理置信度、有效期和撤销状态。
                </FieldDescription>
              </FieldLabel>
            </Field>
            <div className="grid gap-5 md:grid-cols-2">
              {numericFields.map(([key, label, description]) => (
                <Field key={key}>
                  <FieldLabel htmlFor={key}>{label}</FieldLabel>
                  <Input
                    id={key}
                    max={100}
                    min={0}
                    type="number"
                    value={form[key]}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        [key]: Number(event.target.value),
                      }))
                    }
                  />
                  <FieldDescription>{description}</FieldDescription>
                </Field>
              ))}
            </div>
            <Field>
              <FieldLabel htmlFor="max-article-chars">
                单篇最大分析字符数
              </FieldLabel>
              <Input
                id="max-article-chars"
                max={200000}
                min={5000}
                step={1000}
                type="number"
                value={form.max_article_chars}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    max_article_chars: Number(event.target.value),
                  }))
                }
              />
            </Field>
          </FieldGroup>
        </FieldSet>
      </CardContent>
      <CardFooter className="justify-between gap-3">
        <p className="text-xs text-muted-foreground">
          上次由 {policy.updated_by} 更新于 {formatDateTime(policy.updated_at)}
        </p>
        <Button disabled={pending} onClick={() => onSave(form)} type="button">
          <SaveIcon data-icon="inline-start" /> 保存策略
        </Button>
      </CardFooter>
    </Card>
  )
}

export function AutomationPage() {
  const { canAdmin } = useAuth()
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [editorVersion, setEditorVersion] = useState(0)
  const configsQuery = useQuery({
    queryKey: [...automationQueryKey, "configs"],
    queryFn: listModelConfigs,
    enabled: canAdmin,
  })
  const policyQuery = useQuery({
    queryKey: [...automationQueryKey, "policy"],
    queryFn: getProcessingPolicy,
    enabled: canAdmin,
  })
  const statusQuery = useQuery({
    queryKey: [...automationQueryKey, "status"],
    queryFn: getAutomationStatus,
    enabled: canAdmin,
    refetchInterval: 10_000,
  })
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: automationQueryKey })
  const saveModel = useMutation({
    mutationFn: (payload: AIModelConfigInput) =>
      selectedId
        ? updateModelConfig(selectedId, {
            ...payload,
            api_key: payload.api_key || undefined,
          })
        : createModelConfig(payload),
    onSuccess: async () => {
      setSelectedId(null)
      setEditorVersion((current) => current + 1)
      await invalidate()
      toast.success("模型配置已保存")
    },
    onError: (error: Error) => toast.error(error.message),
  })
  const testModel = useMutation({
    mutationFn: testModelConfig,
    onSuccess: async (result) => {
      await invalidate()
      toast.success(`连接成功，耗时 ${result.latency_ms}ms`)
    },
    onError: (error: Error) => toast.error(error.message),
  })
  const removeModel = useMutation({
    mutationFn: deleteModelConfig,
    onSuccess: async () => {
      setSelectedId(null)
      await invalidate()
      toast.success("模型配置已删除")
    },
    onError: (error: Error) => toast.error(error.message),
  })
  const savePolicy = useMutation({
    mutationFn: (policy: AIProcessingPolicy) =>
      updateProcessingPolicy({
        automation_enabled: policy.automation_enabled,
        unattended_mode: policy.unattended_mode,
        require_verification: policy.require_verification,
        auto_create_events: policy.auto_create_events,
        auto_manage_indicators: policy.auto_manage_indicators,
        indicator_auto_threshold: policy.indicator_auto_threshold,
        relevance_threshold: policy.relevance_threshold,
        auto_approve_threshold: policy.auto_approve_threshold,
        auto_reject_threshold: policy.auto_reject_threshold,
        minimum_evidence_coverage: policy.minimum_evidence_coverage,
        max_article_chars: policy.max_article_chars,
      }),
    onSuccess: async () => {
      await invalidate()
      toast.success("自动化策略已保存")
    },
    onError: (error: Error) => toast.error(error.message),
  })
  const backfill = useMutation({
    mutationFn: backfillFilteredReports,
    onSuccess: async (result) => {
      await invalidate()
      toast.success(`已将 ${result.promoted} 篇历史材料加入AI处理队列`)
    },
    onError: (error: Error) => toast.error(error.message),
  })

  if (!canAdmin) {
    return (
      <div className="workspace-page">
        <Alert variant="destructive">
          <CircleAlertIcon />
          <AlertTitle>需要管理员权限</AlertTitle>
          <AlertDescription>
            模型凭据和自动化策略只允许管理员配置。
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  const configs = configsQuery.data ?? []
  const selected = configs.find((config) => config.id === selectedId) ?? null
  const automationStatus = statusQuery.data
  const statusCards: Array<{
    label: string
    value: string | number
    icon: LucideIcon
  }> = [
    {
      label: "默认模型",
      value: automationStatus?.active_model_name ?? "未配置",
      icon: BotIcon,
    },
    {
      label: "24小时自动确认",
      value: automationStatus?.auto_approved_24h ?? 0,
      icon: ShieldCheckIcon,
    },
    {
      label: "需关注异常",
      value: automationStatus?.open_exceptions ?? 0,
      icon: CircleAlertIcon,
    },
    {
      label: "24小时处理量",
      value: automationStatus?.processed_24h ?? 0,
      icon: SparklesIcon,
    },
  ]

  return (
    <div className="workspace-page">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <div className="flex items-center gap-2">
            <SparklesIcon className="size-5 text-primary" />
            <h1 className="text-xl font-semibold">AI 自动化</h1>
          </div>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            AI持续完成语义分析、证据验证、事件沉淀与IOC维护；人工只在阅读时纠错或按需关注异常。
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            disabled={
              backfill.isPending || !automationStatus?.automation_enabled
            }
            onClick={() => backfill.mutate()}
            size="sm"
            variant="outline"
          >
            <RefreshCcwIcon data-icon="inline-start" /> 历史材料回填
          </Button>
          <Badge
            variant={
              automationStatus?.automation_enabled ? "confirmed" : "secondary"
            }
          >
            {automationStatus?.automation_enabled
              ? "自动化运行中"
              : "自动化未启用"}
          </Badge>
        </div>
      </div>

      {statusQuery.isPending ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((item) => (
            <Skeleton className="h-28" key={item} />
          ))}
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {statusCards.map(({ label, value, icon: Icon }) => (
            <Card className="gap-2 py-4" key={label}>
              <CardHeader className="px-4">
                <div className="flex items-center justify-between gap-3">
                  <CardDescription>{label}</CardDescription>
                  <Icon className="size-4 text-muted-foreground" />
                </div>
                <CardTitle className="truncate text-2xl">{value}</CardTitle>
              </CardHeader>
            </Card>
          ))}
        </div>
      )}

      <Tabs defaultValue="models">
        <TabsList>
          <TabsTrigger value="models">
            <BotIcon data-icon="inline-start" /> 模型配置
          </TabsTrigger>
          <TabsTrigger value="policy">
            <Settings2Icon data-icon="inline-start" /> 自动化策略
          </TabsTrigger>
        </TabsList>

        <TabsContent className="flex flex-col gap-4" value="models">
          <div className="grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(28rem,1.1fr)]">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <CardTitle>已配置模型</CardTitle>
                    <CardDescription>
                      默认模型承担分析与独立验证调用。
                    </CardDescription>
                  </div>
                  <Button
                    onClick={() => {
                      setSelectedId(null)
                      setEditorVersion((current) => current + 1)
                    }}
                    size="sm"
                    variant="outline"
                  >
                    <PlusIcon data-icon="inline-start" /> 新建
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                {configsQuery.isPending ? (
                  [0, 1].map((item) => <Skeleton className="h-32" key={item} />)
                ) : configs.length ? (
                  configs.map((config) => (
                    <button
                      className="flex w-full flex-col gap-3 rounded-lg border p-4 text-left transition-colors hover:bg-muted/50"
                      key={config.id}
                      onClick={() => setSelectedId(config.id)}
                      type="button"
                    >
                      <span className="flex w-full items-start justify-between gap-3">
                        <span>
                          <span className="block font-medium">
                            {config.name}
                          </span>
                          <span className="mt-1 block text-xs text-muted-foreground">
                            {providerLabels[config.provider]} · {config.model}
                          </span>
                        </span>
                        <span className="flex gap-1">
                          {config.is_default ? <Badge>默认</Badge> : null}
                          <Badge
                            variant={config.enabled ? "confirmed" : "secondary"}
                          >
                            {config.enabled ? "启用" : "停用"}
                          </Badge>
                        </span>
                      </span>
                      <span className="flex w-full items-center justify-between gap-3 text-xs text-muted-foreground">
                        <span className="truncate">{config.base_url}</span>
                        <span>
                          {config.last_test_status === "succeeded"
                            ? "连接正常"
                            : config.last_test_status === "failed"
                              ? "连接失败"
                              : "尚未测试"}
                        </span>
                      </span>
                    </button>
                  ))
                ) : (
                  <Alert>
                    <BotIcon />
                    <AlertTitle>还没有模型配置</AlertTitle>
                    <AlertDescription>
                      添加并测试默认模型后即可启用自动化。
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
              {selected ? (
                <CardFooter className="justify-end gap-2">
                  <Button
                    disabled={testModel.isPending}
                    onClick={() => testModel.mutate(selected.id)}
                    size="sm"
                    variant="outline"
                  >
                    <FlaskConicalIcon data-icon="inline-start" /> 测试连接
                  </Button>
                  <Button
                    disabled={removeModel.isPending}
                    onClick={() => removeModel.mutate(selected.id)}
                    size="sm"
                    variant="destructive"
                  >
                    <Trash2Icon data-icon="inline-start" /> 删除
                  </Button>
                </CardFooter>
              ) : null}
            </Card>
            <ModelForm
              key={`${selectedId ?? "new"}-${editorVersion}`}
              pending={saveModel.isPending}
              selected={selected}
              onCancel={() => setSelectedId(null)}
              onSave={(payload) => saveModel.mutate(payload)}
            />
          </div>
        </TabsContent>

        <TabsContent value="policy">
          {policyQuery.isPending ? (
            <Skeleton className="h-[36rem]" />
          ) : policyQuery.data ? (
            <div className="flex flex-col gap-4">
              <Alert>
                <CheckCircle2Icon />
                <AlertTitle>证据约束持续生效，但不再成为人工门禁</AlertTitle>
                <AlertDescription>
                  无原文证据、归因冲突或验证失败都会留下异常与审计记录；无人值守模式仍会按AI最终判断继续处理。
                </AlertDescription>
              </Alert>
              <PolicyForm
                key={policyQuery.data.updated_at}
                pending={savePolicy.isPending}
                policy={policyQuery.data}
                onSave={(policy) => savePolicy.mutate(policy)}
              />
            </div>
          ) : (
            <Alert variant="destructive">
              <CircleAlertIcon />
              <AlertTitle>策略加载失败</AlertTitle>
              <AlertDescription>{policyQuery.error?.message}</AlertDescription>
            </Alert>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
