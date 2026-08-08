import {
  AlertCircleIcon,
  Clock3Icon,
  FileTextIcon,
  GitBranchIcon,
  InfoIcon,
  SlidersHorizontalIcon,
  XIcon,
} from "lucide-react"
import { useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { cn } from "@/lib/utils"

import { feedItems, type FeedItem } from "./feed-data"

const metrics = [
  { label: "新增材料", value: 17, note: "近 24 小时", icon: FileTextIcon },
  {
    label: "高相关事件",
    value: 5,
    note: "需要优先查看",
    icon: AlertCircleIcon,
  },
  { label: "待审核", value: 8, note: "等待人工确认", icon: Clock3Icon },
  { label: "采集异常", value: 0, note: "所有数据源正常", icon: InfoIcon },
] as const

function relevanceVariant(score: number) {
  if (score >= 90) return "relevance" as const
  if (score >= 70) return "candidate" as const
  return "confirmed" as const
}

function FeedRow({
  item,
  selected,
  onSelect,
}: {
  item: FeedItem
  selected: boolean
  onSelect: (item: FeedItem) => void
}) {
  const Icon = item.icon

  return (
    <button
      className={cn(
        "grid w-full grid-cols-[3.5rem_minmax(0,1fr)_13rem] items-center gap-3 border-b border-border px-4 py-4 text-left transition-colors hover:bg-accent/40 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
        selected ? "bg-accent/55 ring-1 ring-primary ring-inset" : ""
      )}
      onClick={() => onSelect(item)}
      type="button"
    >
      <span className="flex size-12 items-center justify-center rounded-xl bg-secondary text-primary">
        <Icon aria-hidden="true" />
      </span>
      <span className="flex min-w-0 flex-col gap-2">
        <span className="truncate text-base font-medium">{item.title}</span>
        <span className="flex flex-wrap items-center gap-2">
          <Badge variant={relevanceVariant(item.relevance)}>
            相关性 {item.relevance}
          </Badge>
          <Badge variant="secondary">{item.actor}</Badge>
          <Badge variant="outline">{item.technique}</Badge>
        </span>
        <span className="truncate text-sm text-muted-foreground">
          {item.reason}
        </span>
      </span>
      <span className="flex min-w-0 items-start gap-3 self-start pt-1">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-secondary text-xs font-semibold">
          {item.sourceInitials}
        </span>
        <span className="flex min-w-0 flex-col gap-1">
          <span className="truncate text-sm">{item.source}</span>
          <span className="text-sm text-muted-foreground">{item.age}</span>
        </span>
      </span>
    </button>
  )
}

function EventInspector({ item }: { item: FeedItem }) {
  return (
    <aside className="hidden min-w-0 border-l border-border bg-card xl:flex xl:flex-col">
      <div className="flex items-center justify-between px-5 py-4">
        <h2 className="text-lg font-semibold">事件速览</h2>
        <Button aria-label="关闭事件速览" size="icon-sm" variant="ghost">
          <XIcon />
        </Button>
      </div>
      <Separator />
      <div className="flex flex-col gap-5 overflow-y-auto p-5">
        <div className="flex items-start gap-3">
          <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-malicious/12 text-malicious">
            <item.icon aria-hidden="true" />
          </span>
          <h3 className="text-lg leading-7 font-semibold">{item.title}</h3>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant={relevanceVariant(item.relevance)}>
            相关性 {item.relevance}
          </Badge>
          <Badge variant="secondary">{item.actor}</Badge>
          <Badge variant="outline">{item.technique}</Badge>
        </div>
        <section className="flex flex-col gap-2">
          <h4 className="font-medium">简要描述</h4>
          <p className="text-sm leading-6 text-muted-foreground">
            {item.summary}
          </p>
        </section>
        <section className="flex flex-col gap-3">
          <h4 className="font-medium">威胁钻石模型</h4>
          <div className="grid grid-cols-4 gap-2 text-center text-xs">
            {[
              ["对手", item.actor],
              ["能力", item.technique],
              ["基础设施", "NPM / GitHub"],
              ["受害者", "开发者"],
            ].map(([label, value]) => (
              <div className="flex min-w-0 flex-col gap-1.5" key={label}>
                <span className="font-medium text-primary">{label}</span>
                <span className="truncate text-muted-foreground">{value}</span>
              </div>
            ))}
          </div>
        </section>
        <Separator />
        <section className="flex flex-col gap-3">
          <h4 className="font-medium">关键证据</h4>
          <ul className="flex flex-col gap-2 text-sm text-muted-foreground">
            <li>恶意 NPM 包与投递代码片段 · L28</li>
            <li>GitHub 仓库伪装页面片段 · L56</li>
            <li>Telegram 沟通记录样例 · L104</li>
            <li>受害者环境指纹信息样例 · L152</li>
          </ul>
          <Button className="self-start" variant="link">
            查看全部证据（6）
          </Button>
        </section>
      </div>
      <div className="mt-auto border-t border-border p-5">
        <Button className="w-full">
          <GitBranchIcon data-icon="inline-start" />
          打开事件图谱
        </Button>
      </div>
    </aside>
  )
}

export function IntelligenceFeedPage() {
  const [filter, setFilter] = useState("all")
  const [selectedItem, setSelectedItem] = useState(feedItems[0])

  const visibleItems =
    filter === "high"
      ? feedItems.filter((item) => item.relevance >= 80)
      : filter === "watched"
        ? feedItems.filter((item) => item.actor !== "未归因")
        : feedItems

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <section className="grid shrink-0 grid-cols-2 border-b border-border lg:grid-cols-4">
        {metrics.map((metric) => (
          <div
            className="flex min-w-0 items-center gap-4 border-r border-border px-7 py-5 last:border-r-0"
            key={metric.label}
          >
            <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-secondary text-primary">
              <metric.icon aria-hidden="true" />
            </span>
            <span className="min-w-0">
              <span className="flex items-baseline gap-2">
                <strong className="text-2xl font-semibold text-primary">
                  {metric.value}
                </strong>
                <span className="truncate font-medium">{metric.label}</span>
              </span>
              <span className="text-sm text-muted-foreground">
                {metric.note}
              </span>
            </span>
          </div>
        ))}
      </section>
      <div className="grid min-h-0 flex-1 grid-cols-1 xl:grid-cols-[minmax(0,1fr)_25.5rem]">
        <main className="flex min-w-0 flex-col px-5 py-4">
          <div className="mb-3 flex items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <h2 className="text-lg font-semibold">今日高相关</h2>
              <Tabs value={filter} onValueChange={setFilter}>
                <TabsList>
                  <TabsTrigger value="all">全部</TabsTrigger>
                  <TabsTrigger value="high">高相关</TabsTrigger>
                  <TabsTrigger value="watched">关注对象</TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
            <Button variant="outline">
              <SlidersHorizontalIcon data-icon="inline-start" />
              最新优先
            </Button>
          </div>
          <div className="min-h-0 overflow-y-auto rounded-lg border border-border bg-card">
            {visibleItems.map((item) => (
              <FeedRow
                item={item}
                key={item.id}
                onSelect={setSelectedItem}
                selected={selectedItem.id === item.id}
              />
            ))}
          </div>
        </main>
        <EventInspector item={selectedItem} />
      </div>
    </div>
  )
}
