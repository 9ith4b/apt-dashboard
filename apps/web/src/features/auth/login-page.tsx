import { EyeIcon, EyeOffIcon, RadarIcon, ShieldCheckIcon } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"

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
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[radial-gradient(circle_at_top_left,var(--color-secondary),transparent_36%),linear-gradient(135deg,var(--color-background),var(--color-muted))] p-5">
      <div className="pointer-events-none absolute inset-0 [background-image:linear-gradient(to_right,var(--color-border)_1px,transparent_1px),linear-gradient(to_bottom,var(--color-border)_1px,transparent_1px)] [background-size:38px_38px] opacity-30" />
      <div className="relative grid w-full max-w-5xl overflow-hidden rounded-3xl border bg-card shadow-2xl lg:grid-cols-[1.1fr_0.9fr]">
        <section className="hidden flex-col justify-between bg-primary p-10 text-primary-foreground lg:flex">
          <div className="flex items-center gap-3 text-xl font-semibold">
            <span className="flex size-10 items-center justify-center rounded-xl bg-primary-foreground/10">
              <RadarIcon aria-hidden="true" />
            </span>
            APT Hunter
          </div>
          <div className="max-w-md space-y-5">
            <p className="text-sm font-medium tracking-[0.2em] text-primary-foreground/60 uppercase">
              Threat Intelligence Workspace
            </p>
            <h1 className="text-4xl leading-tight font-semibold tracking-tight">
              从公开信号到可追溯的攻击事件
            </h1>
            <p className="leading-7 text-primary-foreground/70">
              聚合安全报道与官方社交来源，以钻石模型组织证据，并持续跟踪 APT
              组织变化。
            </p>
          </div>
          <div className="flex items-center gap-2 text-sm text-primary-foreground/65">
            <ShieldCheckIcon className="size-4" />
            HttpOnly 会话 · CSRF 防护 · 操作审计
          </div>
        </section>
        <section className="flex min-h-[34rem] items-center justify-center p-6 sm:p-10">
          <Card className="w-full max-w-sm border-0 bg-transparent shadow-none">
            <CardHeader className="px-0">
              <CardTitle className="text-2xl">登录工作台</CardTitle>
              <CardDescription>
                使用由系统管理员创建的本地账户继续。
              </CardDescription>
            </CardHeader>
            <CardContent className="px-0">
              <form
                className="space-y-5"
                onSubmit={(event) => {
                  event.preventDefault()
                  onLogin(username.trim(), password)
                }}
              >
                <FieldGroup>
                  <Field>
                    <FieldLabel htmlFor="login-username">用户名</FieldLabel>
                    <Input
                      id="login-username"
                      autoComplete="username"
                      autoFocus
                      value={username}
                      onChange={(event) => setUsername(event.target.value)}
                    />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="login-password">密码</FieldLabel>
                    <div className="relative">
                      <Input
                        className="pr-10"
                        id="login-password"
                        autoComplete="current-password"
                        type={showPassword ? "text" : "password"}
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                      />
                      <Button
                        aria-label={showPassword ? "隐藏密码" : "显示密码"}
                        className="absolute top-1/2 right-1 -translate-y-1/2"
                        size="icon-sm"
                        type="button"
                        variant="ghost"
                        onClick={() => setShowPassword((value) => !value)}
                      >
                        {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                      </Button>
                    </div>
                    <FieldError>{error}</FieldError>
                  </Field>
                </FieldGroup>
                <Button
                  className="w-full"
                  disabled={
                    pending || username.trim().length < 2 || password.length < 8
                  }
                  size="lg"
                  type="submit"
                >
                  {pending ? "正在验证…" : "安全登录"}
                </Button>
              </form>
            </CardContent>
          </Card>
        </section>
      </div>
    </main>
  )
}
