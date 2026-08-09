import { lazy, Suspense, useEffect, useState } from "react"

import { useTheme } from "@/components/theme-provider"

const DARK_SCHEME_QUERY = "(prefers-color-scheme: dark)"
const DESKTOP_QUERY = "(min-width: 1280px)"
const REDUCED_DATA_QUERY = "(prefers-reduced-data: reduce)"
const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)"

const BlackHoleRenderer = lazy(() =>
  import("@/components/visuals/black-hole-renderer").then((module) => ({
    default: module.BlackHoleHeroSection,
  }))
)

type IdleCapableWindow = Window & {
  cancelIdleCallback?: (handle: number) => void
  requestIdleCallback?: (
    callback: () => void,
    options?: { timeout: number }
  ) => number
}

export function BlackHoleAccent() {
  const { theme } = useTheme()
  const [enabled, setEnabled] = useState(false)

  useEffect(() => {
    const colorScheme = window.matchMedia(DARK_SCHEME_QUERY)
    const desktop = window.matchMedia(DESKTOP_QUERY)
    const reducedData = window.matchMedia(REDUCED_DATA_QUERY)
    const reducedMotion = window.matchMedia(REDUCED_MOTION_QUERY)
    const idleWindow = window as IdleCapableWindow

    let idleHandle: number | undefined
    let timeoutHandle: number | undefined

    const cancelPendingMount = () => {
      if (idleHandle !== undefined) {
        idleWindow.cancelIdleCallback?.(idleHandle)
        idleHandle = undefined
      }
      if (timeoutHandle !== undefined) {
        window.clearTimeout(timeoutHandle)
        timeoutHandle = undefined
      }
    }

    const updateEligibility = () => {
      cancelPendingMount()

      const dark =
        theme === "dark" || (theme === "system" && colorScheme.matches)
      const eligible =
        dark &&
        desktop.matches &&
        !reducedData.matches &&
        !reducedMotion.matches

      if (!eligible) {
        setEnabled(false)
        return
      }

      if (idleWindow.requestIdleCallback) {
        idleHandle = idleWindow.requestIdleCallback(
          () => setEnabled(true),
          { timeout: 1_200 }
        )
        return
      }

      timeoutHandle = window.setTimeout(() => setEnabled(true), 650)
    }

    const queries = [colorScheme, desktop, reducedData, reducedMotion]
    for (const query of queries) {
      query.addEventListener("change", updateEligibility)
    }
    updateEligibility()

    return () => {
      cancelPendingMount()
      for (const query of queries) {
        query.removeEventListener("change", updateEligibility)
      }
    }
  }, [theme])

  if (!enabled) {
    return null
  }

  return (
    <div
      aria-hidden="true"
      className="black-hole-accent"
      data-testid="black-hole-accent"
    >
      <Suspense fallback={null}>
        <BlackHoleRenderer
          brightness={0.9}
          coolColor="#593316"
          distance={24}
          doppler={0.24}
          elevation={-5}
          exposure={0.9}
          focus={[0.5, 0.52]}
          fov={38}
          glow={0.62}
          hotColor="#fff1d6"
          maxDpr={1}
          midColor="#d9a064"
          resolution={0.45}
          roll={-18}
          spinSpeed={0.025}
          starBrightness={0}
          steps={150}
          vignette={0.34}
        />
      </Suspense>
    </div>
  )
}
