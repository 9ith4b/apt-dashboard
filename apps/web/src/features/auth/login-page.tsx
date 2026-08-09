import {
  ActivityIcon,
  DatabaseIcon,
  EyeIcon,
  EyeOffIcon,
  LoaderCircleIcon,
  NetworkIcon,
  RadarIcon,
  ShieldCheckIcon,
} from "lucide-react"
import { useState } from "react"

import { ThemeToggle } from "@/components/theme-toggle"
import { Button } from "@/components/ui/button"
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group"

import { BlackHoleAccent } from "./black-hole-accent"

const telemetry = [
  {
    label: "采集",
    value: "RSS / 社交信号",
    status: "在线",
    icon: DatabaseIcon,
  },
  { label: "解析", value: "实体与关系抽取", status: "就绪", icon: NetworkIcon },
  {
    label: "研判",
    value: "钻石模型富化",
    status: "运行中",
    icon: ActivityIcon,
  },
] as const

export function LoginPage({
  onLogin,
  pending,
  error,
}: {
  onLogin: (username: string, password: string) => void
  pending: boolean
  error: string | null
}) {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)

  return (
    <main className="login-shell grid min-h-dvh text-foreground lg:grid-cols-[minmax(0,1.18fr)_minmax(26rem,0.82fr)]">
      <section className="login-story flex min-h-dvh flex-col px-10 py-8 xl:px-16 xl:py-10">
        <BlackHoleAccent />

        <div className="login-story-content relative z-10 flex min-h-0 flex-1 flex-col">
          <div className="flex items-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-xs">
              <RadarIcon aria-hidden="true" />
            </span>
            <span>
              <span className="block text-sm font-semibold tracking-tight">
                APT Hunter
              </span>
              <span className="block text-[0.65rem] tracking-[0.14em] text-muted-foreground uppercase">
                Threat Intelligence Desk
              </span>
            </span>
          </div>

          <div className="my-auto grid items-center gap-12 2xl:grid-cols-[minmax(0,1fr)_15rem]">
            <div className="max-w-2xl">
              <p className="workspace-kicker mb-5">持续威胁情报工作台</p>
              <h1 className="max-w-2xl text-4xl leading-[1.08] font-semibold tracking-[-0.045em] text-balance xl:text-6xl">
                把散落的信号，
                <br />
                <span className="text-muted-foreground">
                  沉淀为可行动情报。
                </span>
              </h1>
              <p className="mt-6 max-w-xl text-base leading-7 text-muted-foreground xl:text-lg xl:leading-8">
                聚合公开来源，持续追踪 APT
                组织，并以钻石模型拆解攻击者、能力、基础设施与受害者关系。
              </p>
            </div>

            <div
              aria-label="钻石模型关系示意"
              className="relative mx-auto hidden size-56 place-items-center 2xl:grid"
            >
              <div className="login-diamond" />
              <span className="absolute top-0 text-[0.65rem] tracking-wider text-muted-foreground uppercase">
                攻击者
              </span>
              <span className="absolute right-0 text-[0.65rem] tracking-wider text-muted-foreground uppercase">
                能力
              </span>
              <span className="absolute bottom-0 text-[0.65rem] tracking-wider text-muted-foreground uppercase">
                受害者
              </span>
              <span className="absolute left-0 text-[0.65rem] tracking-wider text-muted-foreground uppercase">
                基础设施
              </span>
              <span className="absolute size-2 rotate-45 bg-primary" />
            </div>
          </div>

          <div className="max-w-3xl rounded-xl border border-border bg-card/70 px-5 backdrop-blur-sm">
            {telemetry.map((item) => (
              <div className="login-telemetry-row" key={item.label}>
                <span className="flex items-center gap-2 text-xs font-medium">
                  <item.icon aria-hidden="true" />
                  {item.label}
                </span>
                <div className="login-trace" />
                <span className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span className="size-1.5 rounded-full bg-confirmed" />
                  {item.value} · {item.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="relative flex min-h-dvh items-center justify-center bg-card px-5 py-20 sm:px-10">
        <ThemeToggle className="absolute top-6 right-6" />

        <div className="w-full max-w-[25rem]">
          <div className="mb-9 lg:hidden">
            <div className="mb-8 flex items-center gap-3">
              <span className="flex size-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <RadarIcon aria-hidden="true" />
              </span>
              <span className="font-semibold">APT Hunter</span>
            </div>
          </div>

          <p className="workspace-kicker mb-3">安全访问</p>
          <h2 className="text-3xl font-semibold tracking-[-0.035em]">
            登录情报工作台
          </h2>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            使用本地账户继续访问你的情报、狩猎与跟踪任务。
          </p>

          <form
            className="mt-8 flex flex-col gap-6"
            onSubmit={(event) => {
              event.preventDefault()
              onLogin(username.trim(), password)
            }}
          >
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="login-username">用户名</FieldLabel>
                <InputGroup className="h-11">
                  <InputGroupInput
                    id="login-username"
                    autoComplete="username"
                    autoFocus
                    placeholder="输入用户名"
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                  />
                </InputGroup>
              </Field>

              <Field data-invalid={Boolean(error)}>
                <FieldLabel htmlFor="login-password">密码</FieldLabel>
                <InputGroup className="h-11">
                  <InputGroupInput
                    id="login-password"
                    aria-invalid={Boolean(error)}
                    autoComplete="current-password"
                    placeholder="输入密码"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                  />
                  <InputGroupAddon align="inline-end">
                    <InputGroupButton
                      aria-label={showPassword ? "隐藏密码" : "显示密码"}
                      size="icon-sm"
                      onClick={() => setShowPassword((value) => !value)}
                    >
                      {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                    </InputGroupButton>
                  </InputGroupAddon>
                </InputGroup>
                <FieldError>{error}</FieldError>
              </Field>
            </FieldGroup>

            <Button
              className="h-11 w-full"
              disabled={
                pending || username.trim().length < 2 || password.length < 8
              }
              size="lg"
              type="submit"
            >
              {pending ? (
                <>
                  <LoaderCircleIcon
                    aria-hidden="true"
                    className="animate-spin"
                    data-icon="inline-start"
                  />
                  正在验证…
                </>
              ) : (
                "安全登录"
              )}
            </Button>
          </form>

          <div className="mt-8 flex items-center gap-2 border-t border-border pt-5 text-xs text-muted-foreground">
            <ShieldCheckIcon aria-hidden="true" />
            本地部署 · 安全会话 · 全程审计
          </div>
        </div>
      </section>
    </main>
  )
}
