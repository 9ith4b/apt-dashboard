import {
  ArrowDownRightIcon,
  ArrowRightIcon,
  ArrowUpRightIcon,
  DownloadIcon,
  FileTextIcon,
  SparklesIcon,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import type {
  ActorTracking,
  ActorTrackingSummary,
} from "@/features/intelligence/intelligence-types"

const changeLabels = {
  malware: "能力 / 恶意软件",
  infrastructure: "基础设施",
  techniques: "ATT&CK 技术",
  targets: "受害目标",
} as const

function ChangeIcon({ value }: { value: number }) {
  if (value > 0)
    return <ArrowUpRightIcon className="size-4" aria-hidden="true" />
  if (value < 0)
    return <ArrowDownRightIcon className="size-4" aria-hidden="true" />
  return <ArrowRightIcon className="size-4" aria-hidden="true" />
}

export function ActorTrackingPanel({
  tracking,
  summary,
  isPending,
  isGenerating,
  error,
  onGenerateSummary,
  jsonExportUrl,
  csvExportUrl,
}: {
  tracking: ActorTracking | undefined
  summary: ActorTrackingSummary | undefined
  isPending: boolean
  isGenerating: boolean
  error: string | undefined
  onGenerateSummary: () => void
  jsonExportUrl: string
  csvExportUrl: string
}) {
  if (isPending) {
    return (
      <div className="grid gap-4 xl:grid-cols-2">
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
      </div>
    )
  }
  if (!tracking) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>周期洞察暂不可用</CardTitle>
          <CardDescription>{error || "请稍后重试。"}</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  const comparison = tracking.comparison
  const percent =
    comparison.percentage_change === null
      ? "上一周期为 0，无法计算百分比"
      : `${comparison.percentage_change > 0 ? "+" : ""}${comparison.percentage_change}%`
  const hasChanges = tracking.changes.some(
    (item) => item.new_values.length || item.disappeared_values.length
  )

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,0.72fr)_minmax(0,1.28fr)]">
        <Card>
          <CardHeader>
            <CardTitle>等长周期对比</CardTitle>
            <CardDescription>
              {tracking.period.date_from} 至 {tracking.period.date_to}
              ，与紧邻的上一
              {tracking.period.day_count} 天比较
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-end justify-between gap-4 rounded-lg border border-border bg-background/45 p-4">
              <div>
                <p className="text-xs text-muted-foreground">本期已确认事件</p>
                <p className="mt-1 text-3xl font-semibold">
                  {comparison.current_event_count}
                </p>
              </div>
              <div className="text-right">
                <Badge
                  variant={
                    comparison.absolute_change > 0 ? "default" : "secondary"
                  }
                >
                  <ChangeIcon value={comparison.absolute_change} />
                  {comparison.absolute_change > 0 ? "+" : ""}
                  {comparison.absolute_change} 起
                </Badge>
                <p className="mt-2 text-xs text-muted-foreground">{percent}</p>
              </div>
            </div>
            <p className="mt-3 text-xs text-muted-foreground">
              上期 {tracking.period.previous_from} 至{" "}
              {tracking.period.previous_to} 共 {comparison.previous_event_count}{" "}
              起。自动采用
              {tracking.period.bucket === "day"
                ? "日"
                : tracking.period.bucket === "week"
                  ? "周"
                  : "月"}
              粒度。
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>本期趋势</CardTitle>
            <CardDescription>
              自定义日期同时约束趋势、事件、变化和导出
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>时间桶</TableHead>
                  <TableHead className="text-right">事件数</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tracking.trend.length ? (
                  tracking.trend.map((bucket) => (
                    <TableRow key={bucket.key}>
                      <TableCell>{bucket.label}</TableCell>
                      <TableCell className="text-right">
                        <Badge variant="secondary">{bucket.event_count}</Badge>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell className="text-muted-foreground" colSpan={2}>
                      所选周期没有已确认事件。
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>较上一周期的变化</CardTitle>
          <CardDescription>
            “未再出现”不等于失效，只表示本期已确认事件没有再次观测
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          {tracking.changes.map((item) => (
            <div
              className="rounded-lg border border-border p-4"
              key={item.category}
            >
              <p className="text-sm font-medium">
                {changeLabels[item.category]}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {item.new_values.map((value) => (
                  <Badge key={`new-${value}`} variant="confirmed">
                    新增 · {value}
                  </Badge>
                ))}
                {item.disappeared_values.map((value) => (
                  <Badge key={`gone-${value}`} variant="outline">
                    未再出现 · {value}
                  </Badge>
                ))}
                {!item.new_values.length && !item.disappeared_values.length ? (
                  <span className="text-xs text-muted-foreground">无变化</span>
                ) : null}
              </div>
            </div>
          ))}
          {!hasChanges ? (
            <p className="text-xs text-muted-foreground md:col-span-2">
              四类跟踪对象均未观察到集合变化。
            </p>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-start justify-between gap-4">
          <div>
            <CardTitle>分析摘要与导出</CardTitle>
            <CardDescription>
              摘要是可追溯草稿，必须经分析员核对后才能发布
            </CardDescription>
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <Button asChild size="sm" variant="outline">
              <a download href={jsonExportUrl}>
                <DownloadIcon data-icon="inline-start" />
                JSON
              </a>
            </Button>
            <Button asChild size="sm" variant="outline">
              <a download href={csvExportUrl}>
                <DownloadIcon data-icon="inline-start" />
                CSV
              </a>
            </Button>
            <Button
              disabled={isGenerating}
              onClick={onGenerateSummary}
              size="sm"
              type="button"
            >
              <SparklesIcon data-icon="inline-start" />
              {isGenerating ? "生成中…" : "生成摘要草稿"}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {summary ? (
            <div className="rounded-lg border border-primary/25 bg-primary/5 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">草稿</Badge>
                <Badge variant="outline">{summary.method_version}</Badge>
              </div>
              <h3 className="mt-3 text-sm font-semibold">{summary.title}</h3>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {summary.summary}
              </p>
              <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
                {summary.highlights.map((highlight) => (
                  <li key={highlight}>{highlight}</li>
                ))}
              </ul>
              <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
                <FileTextIcon className="size-4" aria-hidden="true" />
                {summary.supporting_event_ids.length} 个事件、
                {summary.supporting_evidence_ids.length} 条 Evidence 支撑
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              点击生成后，系统只依据当前日期范围内的已确认事件和证据创建草稿。
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
