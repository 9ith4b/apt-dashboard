import { useQuery } from "@tanstack/react-query"
import { SearchIcon } from "lucide-react"
import { useDeferredValue, useState } from "react"
import { Link, useNavigate } from "react-router-dom"

import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { globalSearch, searchQueryKey } from "@/features/system/system-api"

const kindLabels = {
  actor: "攻击者",
  event: "事件",
  observable: "Observable",
  report: "报告",
} as const

export function GlobalSearch() {
  const navigate = useNavigate()
  const [query, setQuery] = useState("")
  const [focused, setFocused] = useState(false)
  const deferredQuery = useDeferredValue(query.trim())
  const resultQuery = useQuery({
    queryKey: [...searchQueryKey, deferredQuery],
    queryFn: () => globalSearch(deferredQuery),
    enabled: deferredQuery.length >= 2,
  })
  const results = resultQuery.data?.results ?? []
  const open = focused && query.trim().length >= 2

  return (
    <div className="relative hidden w-86 xl:block">
      <SearchIcon className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        aria-label="全局搜索"
        className="pl-9"
        onBlur={() => window.setTimeout(() => setFocused(false), 120)}
        onChange={(event) => setQuery(event.target.value)}
        onFocus={() => setFocused(true)}
        onKeyDown={(event) => {
          if (event.key === "Escape") setFocused(false)
          if (event.key === "Enter" && results[0]) {
            navigate(results[0].url)
            setFocused(false)
          }
        }}
        placeholder="搜索事件、IOC、攻击者、报告…"
        value={query}
      />
      {open ? (
        <div className="absolute top-12 right-0 z-40 max-h-[28rem] w-[30rem] overflow-y-auto rounded-xl border border-border bg-popover p-2 shadow-xl">
          {resultQuery.isPending ? (
            <p className="p-3 text-sm text-muted-foreground">正在检索知识库…</p>
          ) : resultQuery.isError ? (
            <p className="p-3 text-sm text-destructive">
              {resultQuery.error.message}
            </p>
          ) : results.length ? (
            results.map((result) => (
              <Link
                className="block rounded-lg p-3 hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                key={`${result.kind}-${result.id}`}
                onClick={() => setFocused(false)}
                to={result.url}
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="truncate text-sm font-medium">{result.title}</p>
                  <Badge variant="secondary">{kindLabels[result.kind]}</Badge>
                </div>
                <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                  {result.subtitle || "暂无摘要"}
                </p>
              </Link>
            ))
          ) : (
            <p className="p-3 text-sm text-muted-foreground">
              没有找到匹配结果。
            </p>
          )}
        </div>
      ) : null}
    </div>
  )
}
