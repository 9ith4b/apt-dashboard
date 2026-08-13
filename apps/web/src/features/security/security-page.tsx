import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  FileClockIcon,
  PlusIcon,
  RefreshCwIcon,
  ShieldCheckIcon,
  UserRoundCheckIcon,
  UsersIcon,
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
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
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

import {
  auditQueryKey,
  createUser,
  listAuditLogs,
  listUsers,
  updateUser,
  usersQueryKey,
} from "./security-api"
import type { CurrentUser, UserCreate, UserRole } from "./security-types"

const ROLE_LABELS: Record<UserRole, string> = {
  viewer: "只读",
  analyst: "分析员",
  admin: "管理员",
}

const EMPTY_USER: UserCreate = {
  username: "",
  display_name: "",
  password: "",
  role: "viewer",
  enabled: true,
}

function validateUser(form: UserCreate) {
  return {
    username:
      form.username.trim().length < 2 ? "用户名至少需要 2 个字符。" : null,
    displayName:
      form.display_name.trim().length < 1 ? "请输入显示名称。" : null,
    password: form.password.length < 12 ? "初始密码至少需要 12 个字符。" : null,
  }
}

type UserFormErrors = ReturnType<typeof validateUser>

const EMPTY_USER_ERRORS: UserFormErrors = {
  username: null,
  displayName: null,
  password: null,
}

function formatTime(value: string | null) {
  if (!value) return "—"
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value))
}

function CreateUserDialog({
  onCreate,
  pending,
}: {
  onCreate: (payload: UserCreate) => void
  pending: boolean
}) {
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState<UserCreate>({ ...EMPTY_USER })
  const [submitted, setSubmitted] = useState(false)
  const errors: UserFormErrors = submitted
    ? validateUser(form)
    : EMPTY_USER_ERRORS

  function changeOpen(nextOpen: boolean) {
    setOpen(nextOpen)
    if (!nextOpen) {
      setForm({ ...EMPTY_USER })
      setSubmitted(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={changeOpen}>
      <DialogTrigger asChild>
        <Button>
          <PlusIcon data-icon="inline-start" />
          创建账户
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <form
          className="space-y-5"
          onSubmit={(event) => {
            event.preventDefault()
            setSubmitted(true)
            if (Object.values(validateUser(form)).some(Boolean)) return
            onCreate({
              ...form,
              username: form.username.trim().toLowerCase(),
              display_name: form.display_name.trim(),
            })
            changeOpen(false)
          }}
        >
          <DialogHeader>
            <DialogTitle>创建本地账户</DialogTitle>
            <DialogDescription>
              密码经 Argon2id 哈希保存；不同角色由服务端强制授权。
            </DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <Field data-invalid={Boolean(errors.username)}>
              <FieldLabel htmlFor="new-username">用户名</FieldLabel>
              <Input
                id="new-username"
                autoComplete="off"
                value={form.username}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    username: event.target.value,
                  }))
                }
              />
              <FieldError>{errors.username}</FieldError>
            </Field>
            <Field data-invalid={Boolean(errors.displayName)}>
              <FieldLabel htmlFor="new-display-name">显示名称</FieldLabel>
              <Input
                id="new-display-name"
                autoComplete="off"
                value={form.display_name}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    display_name: event.target.value,
                  }))
                }
              />
              <FieldError>{errors.displayName}</FieldError>
            </Field>
            <Field data-invalid={Boolean(errors.password)}>
              <FieldLabel htmlFor="new-password">初始密码</FieldLabel>
              <Input
                id="new-password"
                autoComplete="new-password"
                type="password"
                value={form.password}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    password: event.target.value,
                  }))
                }
              />
              <FieldDescription>
                至少 12 个字符，建议使用密码管理器。
              </FieldDescription>
              <FieldError>{errors.password}</FieldError>
            </Field>
            <Field>
              <FieldLabel htmlFor="new-role">角色</FieldLabel>
              <select
                className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
                id="new-role"
                value={form.role}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    role: event.target.value as UserRole,
                  }))
                }
              >
                {Object.entries(ROLE_LABELS).map(([role, label]) => (
                  <option key={role} value={role}>
                    {label}
                  </option>
                ))}
              </select>
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
              {pending ? "正在创建…" : "创建账户"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export function SecurityPage() {
  const queryClient = useQueryClient()
  const users = useQuery({ queryKey: usersQueryKey, queryFn: listUsers })
  const audit = useQuery({ queryKey: auditQueryKey, queryFn: listAuditLogs })
  const createMutation = useMutation({
    mutationFn: createUser,
    onSuccess: (created) => {
      queryClient.setQueryData<CurrentUser[]>(usersQueryKey, (current = []) => [
        ...current,
        created,
      ])
      toast.success("账户已创建")
    },
    onError: (error: Error) =>
      toast.error("创建失败", { description: error.message }),
  })
  const updateMutation = useMutation({
    mutationFn: ({
      id,
      ...payload
    }: {
      id: string
      role?: UserRole
      enabled?: boolean
    }) => updateUser(id, payload),
    onSuccess: (updated) => {
      queryClient.setQueryData<CurrentUser[]>(usersQueryKey, (current = []) =>
        current.map((user) => (user.id === updated.id ? updated : user))
      )
      void queryClient.invalidateQueries({ queryKey: auditQueryKey })
    },
    onError: (error: Error) =>
      toast.error("更新失败", { description: error.message }),
  })
  const userItems = users.data ?? []
  const auditItems = audit.data ?? []
  const metrics = [
    {
      icon: UsersIcon,
      label: "全部账户",
      value: userItems.length,
      note: "本地身份",
    },
    {
      icon: UserRoundCheckIcon,
      label: "已启用",
      value: userItems.filter((user) => user.enabled).length,
      note: "可建立会话",
    },
    {
      icon: ShieldCheckIcon,
      label: "管理员",
      value: userItems.filter((user) => user.role === "admin" && user.enabled)
        .length,
      note: "至少保留一名",
    },
    {
      icon: FileClockIcon,
      label: "审计记录",
      value: auditItems.length,
      note: "最近 100 条",
    },
  ]

  return (
    <main
      className="workspace-page overflow-hidden"
      data-testid="security-workspace"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">身份与安全审计</h2>
          <p className="text-sm text-muted-foreground">
            管理本地账户、角色和最近的写操作记录。
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => {
              void users.refetch()
              void audit.refetch()
            }}
          >
            <RefreshCwIcon data-icon="inline-start" />
            刷新
          </Button>
          <CreateUserDialog
            pending={createMutation.isPending}
            onCreate={(payload) => createMutation.mutate(payload)}
          />
        </div>
      </div>
      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {metrics.map((metric) => (
          <Card key={metric.label}>
            <CardContent className="flex items-center gap-4 p-4">
              <span className="flex size-10 items-center justify-center rounded-xl bg-secondary text-primary">
                <metric.icon />
              </span>
              <span>
                <strong className="text-2xl text-primary">
                  {metric.value}
                </strong>
                <span className="ml-2 font-medium">{metric.label}</span>
                <span className="block text-sm text-muted-foreground">
                  {metric.note}
                </span>
              </span>
            </CardContent>
          </Card>
        ))}
      </section>
      <div className="grid min-h-0 flex-1 grid-rows-2 gap-4 xl:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] xl:grid-rows-1">
        <Card className="flex min-h-0 min-w-0 flex-col overflow-hidden">
          <CardHeader className="shrink-0">
            <CardTitle>账户与角色</CardTitle>
            <CardDescription>
              管理员可配置来源和作业；分析员可研判；只读角色仅查看。
            </CardDescription>
          </CardHeader>
          <CardContent
            className="min-h-0 flex-1 overflow-auto overscroll-contain p-0"
            data-testid="account-list-scroll"
          >
            {users.isLoading ? (
              <Skeleton className="m-5 h-40" />
            ) : (
              <Table className="min-w-[36rem] table-fixed">
                <TableHeader className="sticky top-0 bg-card">
                  <TableRow>
                    <TableHead className="w-[28%]">账户</TableHead>
                    <TableHead className="w-[28%]">角色</TableHead>
                    <TableHead className="w-[28%]">最近登录</TableHead>
                    <TableHead className="w-[16%] text-right">启用</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {userItems.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell>
                        <div className="font-medium">{user.display_name}</div>
                        <div className="text-xs text-muted-foreground">
                          @{user.username}
                        </div>
                      </TableCell>
                      <TableCell>
                        <select
                          aria-label={`角色 ${user.username}`}
                          className="h-8 rounded-md border bg-background px-2 text-sm"
                          disabled={updateMutation.isPending}
                          value={user.role}
                          onChange={(event) =>
                            updateMutation.mutate({
                              id: user.id,
                              role: event.target.value as UserRole,
                            })
                          }
                        >
                          {Object.entries(ROLE_LABELS).map(([role, label]) => (
                            <option key={role} value={role}>
                              {label}
                            </option>
                          ))}
                        </select>
                      </TableCell>
                      <TableCell>{formatTime(user.last_login_at)}</TableCell>
                      <TableCell className="text-right">
                        <Switch
                          aria-label={`${user.enabled ? "停用" : "启用"} ${user.username}`}
                          checked={user.enabled}
                          disabled={updateMutation.isPending}
                          onCheckedChange={(enabled) =>
                            updateMutation.mutate({ id: user.id, enabled })
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
        <Card className="flex min-h-0 min-w-0 flex-col overflow-hidden">
          <CardHeader className="shrink-0">
            <CardTitle>最近审计</CardTitle>
            <CardDescription>
              登录、拒绝和写操作均保留请求标识与结果。
            </CardDescription>
          </CardHeader>
          <CardContent
            className="min-h-0 flex-1 overflow-auto overscroll-contain p-0"
            data-testid="audit-list-scroll"
          >
            {audit.isLoading ? (
              <Skeleton className="m-5 h-40" />
            ) : (
              <Table className="min-w-[40rem] table-fixed">
                <TableHeader className="sticky top-0 bg-card">
                  <TableRow>
                    <TableHead className="w-[20%]">时间 / 操作者</TableHead>
                    <TableHead className="w-[30%]">操作</TableHead>
                    <TableHead className="w-[34%]">对象</TableHead>
                    <TableHead className="w-[16%]">结果</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {auditItems.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell>
                        <div>{formatTime(item.created_at)}</div>
                        <div className="text-xs text-muted-foreground">
                          {item.actor_username ?? "匿名"}
                        </div>
                      </TableCell>
                      <TableCell className="align-top font-mono text-xs break-all whitespace-normal">
                        {item.action}
                      </TableCell>
                      <TableCell className="align-top text-xs break-all whitespace-normal">
                        {item.object_type ?? "—"}
                        {item.object_id ? ` / ${item.object_id}` : ""}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            item.result === "succeeded"
                              ? "confirmed"
                              : "candidate"
                          }
                        >
                          {item.result}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </main>
  )
}
