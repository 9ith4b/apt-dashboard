import { MoonIcon, SunIcon } from "lucide-react"
import { useEffect, useState } from "react"

import { type Theme, useOptionalTheme } from "@/components/theme-provider"
import { Button } from "@/components/ui/button"

const DARK_SCHEME_QUERY = "(prefers-color-scheme: dark)"

export function ThemeToggle({ className }: { className?: string }) {
  const themeContext = useOptionalTheme()
  const [standaloneTheme, setStandaloneTheme] = useState<Theme>("system")
  const [systemDark, setSystemDark] = useState(
    () => window.matchMedia(DARK_SCHEME_QUERY).matches
  )

  useEffect(() => {
    const query = window.matchMedia(DARK_SCHEME_QUERY)
    const handleChange = (event: MediaQueryListEvent) =>
      setSystemDark(event.matches)

    query.addEventListener("change", handleChange)
    return () => query.removeEventListener("change", handleChange)
  }, [])

  const theme = themeContext?.theme ?? standaloneTheme
  const setTheme =
    themeContext?.setTheme ??
    ((nextTheme: Theme) => {
      setStandaloneTheme(nextTheme)
      const resolvedTheme =
        nextTheme === "system"
          ? window.matchMedia(DARK_SCHEME_QUERY).matches
            ? "dark"
            : "light"
          : nextTheme
      document.documentElement.classList.remove("light", "dark")
      document.documentElement.classList.add(resolvedTheme)
    })
  const isDark = theme === "dark" || (theme === "system" && systemDark)
  const label = isDark ? "切换到浅色主题" : "切换到深色主题"

  return (
    <Button
      aria-label={label}
      className={className}
      onClick={() => setTheme(isDark ? "light" : "dark")}
      size="icon"
      title={label}
      variant="ghost"
    >
      {isDark ? (
        <SunIcon aria-hidden="true" />
      ) : (
        <MoonIcon aria-hidden="true" />
      )}
    </Button>
  )
}
