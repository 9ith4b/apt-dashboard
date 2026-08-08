import {
  EyeIcon,
  EyeOffIcon,
  LoaderCircleIcon,
  RadarIcon,
  ShieldCheckIcon,
} from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
} from "@/components/ui/card"
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

import { BlackHoleScene } from "./black-hole-scene"

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
    <main className="login-shell relative min-h-dvh overflow-hidden bg-background text-foreground">
      <BlackHoleScene />

      <header className="absolute top-5 left-5 flex items-center gap-3 sm:top-7 sm:left-8 lg:top-9 lg:left-10">
        <span className="login-brand-mark flex size-10 items-center justify-center rounded-full sm:size-11">
          <RadarIcon aria-hidden="true" />
        </span>
        <span className="text-lg font-semibold tracking-tight sm:text-xl">
          APT Hunter
        </span>
      </header>

      <a
        className="login-attribution"
        href="https://sketchfab.com/3d-models/black-hole-e410da98b1e5445eae2acafaaa53587d"
        rel="nofollow noreferrer"
        target="_blank"
      >
        Black Hole by Nestaeric · Sketchfab
      </a>

      <div className="relative grid min-h-dvh items-end px-4 pt-28 pb-4 sm:px-6 sm:pt-32 sm:pb-6 lg:grid-cols-[minmax(0,1fr)_minmax(26rem,34rem)] lg:items-center lg:px-10 lg:py-10 xl:px-16">
        <div aria-hidden="true" className="hidden lg:block" />

        <Card className="login-panel mx-auto w-full max-w-[32rem] lg:mx-0 lg:justify-self-end">
          <CardHeader className="gap-3 px-6 pt-7 sm:px-8 sm:pt-8">
            <h1 className="login-title text-3xl leading-tight font-semibold tracking-[-0.035em] text-balance sm:text-4xl lg:text-5xl">
              洞察威胁轨迹
            </h1>
            <CardDescription className="max-w-md text-sm leading-6 sm:text-base sm:leading-7">
              汇聚公开信号，沉淀可追溯的攻击情报。
            </CardDescription>
          </CardHeader>

          <CardContent className="flex flex-col gap-5 px-6 sm:px-8">
            <h2 className="text-xl font-medium tracking-tight sm:text-2xl">
              登录工作台
            </h2>
            <form
              className="flex flex-col gap-5"
              onSubmit={(event) => {
                event.preventDefault()
                onLogin(username.trim(), password)
              }}
            >
              <FieldGroup>
                <Field>
                  <FieldLabel htmlFor="login-username">用户名</FieldLabel>
                  <InputGroup className="h-12">
                    <InputGroupInput
                      id="login-username"
                      autoComplete="username"
                      autoFocus
                      placeholder="用户名"
                      value={username}
                      onChange={(event) => setUsername(event.target.value)}
                    />
                  </InputGroup>
                </Field>

                <Field data-invalid={Boolean(error)}>
                  <FieldLabel htmlFor="login-password">密码</FieldLabel>
                  <InputGroup className="h-12">
                    <InputGroupInput
                      id="login-password"
                      aria-invalid={Boolean(error)}
                      autoComplete="current-password"
                      placeholder="密码"
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
                className="h-12 w-full text-primary-foreground!"
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
          </CardContent>

          <CardFooter className="justify-center gap-2 px-6 py-4 text-xs text-muted-foreground sm:text-sm">
            <ShieldCheckIcon aria-hidden="true" className="size-4" />
            安全会话 · 全程审计
          </CardFooter>
        </Card>
      </div>
    </main>
  )
}
