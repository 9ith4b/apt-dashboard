import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  BanIcon,
  CheckCircle2Icon,
  CircleDotDashedIcon,
  Clock3Icon,
  RefreshCcwIcon,
  RotateCcwIcon,
  ServerCogIcon,
  TriangleAlertIcon,
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
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { formatDateTime } from "@/features/intelligence/intelligence-format"
import {
  cancelOperationJob,
  listOperationJobs,
  operationJobQueryKey,
  retryOperationJob,
} from "@/features/operations/operations-api"
import type { OperationJob } from "@/features/operations/operations-types"

const statusLabels = {
  queued: "排队中",
  running: "运行中",
  succeeded: "已成功",
  failed: "失败",
  canceled: "已取消",
} as const

const jobLabels = {
  source_poll: "采集数据源",
  report_enrichment: "富化报告",
} as const

function statusVariant(status: OperationJob["status"]) {
  if (status === "succeeded") return "confirmed" as const
  if (status === "failed") return "destructive" as const
  if (status === "running") return "default" as const
  return "secondary" as const
}

export function OperationsPage() {
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState<
    OperationJob["status"] | "all"
  >("all")
  const jobsQuery = useQuery({
    queryKey: [...operationJobQueryKey, statusFilter],
    queryFn: () =>
      listOperationJobs(statusFilter === "all" ? undefined : statusFilter),
    refetchInterval: 5_000,
  })
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: operationJobQueryKey })
  const cancelMutation = useMutation({
    mutationFn: cancelOperationJob,
    onSuccess: async () => {
      await invalidate()
      toast.success("已提交取消请求")
    },
  })
  const retryMutation = useMutation({
    mutationFn: retryOperationJob,
    onSuccess: async () => {
      await invalidate()
      toast.success("重试作业已进入队列")
    },
  })
  const jobs = jobsQuery.data ?? []
  const runningCount = jobs.filter((job) => job.status === "running").length
  const failedCount = jobs.filter((job) => job.status === "failed").length
  const successCount = jobs.filter((job) => job.status === "succeeded").length

  return (
    <div
      className="workspace-page overflow-hidden"
      data-testid="operations-workspace"
    >
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <div className="flex items-center gap-2">
            <ServerCogIcon className="size-5 text-primary" />
            <h1 className="text-xl font-semibold">作业中心</h1>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            持久记录采集与富化任务，查看结果并安全取消或重试
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ToggleGroup
            aria-label="作业状态"
            onValueChange={(value) => {
              if (value) setStatusFilter(value as typeof statusFilter)
            }}
            size="sm"
            type="single"
            value={statusFilter}
            variant="outline"
          >
            <ToggleGroupItem value="all">全部</ToggleGroupItem>
            <ToggleGroupItem value="queued">排队</ToggleGroupItem>
            <ToggleGroupItem value="running">运行</ToggleGroupItem>
            <ToggleGroupItem value="failed">失败</ToggleGroupItem>
          </ToggleGroup>
          <Button
            onClick={() => jobsQuery.refetch()}
            size="sm"
            variant="outline"
          >
            <RefreshCcwIcon data-icon="inline-start" />
            刷新
          </Button>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <Card className="gap-2 py-4">
          <CardHeader className="px-4">
            <CardDescription>运行中</CardDescription>
            <CardTitle className="text-2xl">{runningCount}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="gap-2 py-4">
          <CardHeader className="px-4">
            <CardDescription>当前列表成功</CardDescription>
            <CardTitle className="text-2xl">{successCount}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="gap-2 py-4">
          <CardHeader className="px-4">
            <CardDescription>需要处理</CardDescription>
            <CardTitle className="text-2xl">{failedCount}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <CardHeader className="shrink-0">
          <CardTitle>作业记录</CardTitle>
          <CardDescription>
            页面每 5 秒刷新；取消不强制终止正在执行的代码
          </CardDescription>
        </CardHeader>
        <CardContent
          className="min-h-0 flex-1 overflow-auto overscroll-contain p-0"
          data-testid="operation-list-scroll"
        >
          {jobsQuery.isError ? (
            <Empty>
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <TriangleAlertIcon />
                </EmptyMedia>
                <EmptyTitle>作业加载失败</EmptyTitle>
                <EmptyDescription>{jobsQuery.error.message}</EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : !jobs.length ? (
            <Empty>
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <CircleDotDashedIcon />
                </EmptyMedia>
                <EmptyTitle>还没有作业记录</EmptyTitle>
                <EmptyDescription>
                  手动采集数据源或富化报告后，任务会显示在这里。
                </EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : (
            <Table className="min-w-[48rem]">
              <TableHeader className="sticky top-0 bg-card">
                <TableRow>
                  <TableHead>类型 / 对象</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>进度</TableHead>
                  <TableHead>时间</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {jobs.map((job) => (
                  <TableRow key={job.id}>
                    <TableCell>
                      <p className="font-medium">
                        {jobLabels[job.job_type] || job.job_type}
                      </p>
                      <p className="mt-1 max-w-64 truncate text-xs text-muted-foreground">
                        {String(
                          job.payload.source_name ||
                            job.payload.report_title ||
                            job.subject_id
                        )}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        第 {job.attempt} 次尝试
                      </p>
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusVariant(job.status)}>
                        {statusLabels[job.status]}
                      </Badge>
                      {job.error ? (
                        <p className="mt-2 max-w-64 text-xs text-destructive">
                          {job.error}
                        </p>
                      ) : null}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-24 overflow-hidden rounded-full bg-muted">
                          <div
                            className="h-full bg-primary"
                            style={{ width: `${job.progress}%` }}
                          />
                        </div>
                        <span className="text-xs">{job.progress}%</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Clock3Icon className="size-3.5" />
                        {formatDateTime(job.created_at)}
                      </div>
                    </TableCell>
                    <TableCell>
                      {job.status === "queued" || job.status === "running" ? (
                        <Button
                          disabled={cancelMutation.isPending}
                          onClick={() => cancelMutation.mutate(job)}
                          size="sm"
                          variant="outline"
                        >
                          <BanIcon data-icon="inline-start" />
                          取消
                        </Button>
                      ) : job.status === "failed" ||
                        job.status === "canceled" ? (
                        <Button
                          disabled={retryMutation.isPending}
                          onClick={() => retryMutation.mutate(job.id)}
                          size="sm"
                          variant="outline"
                        >
                          <RotateCcwIcon data-icon="inline-start" />
                          重试
                        </Button>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs text-confirmed">
                          <CheckCircle2Icon className="size-4" />
                          完成
                        </span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
