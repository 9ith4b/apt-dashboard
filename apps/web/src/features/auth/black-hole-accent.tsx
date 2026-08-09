import { lazy, Suspense, useEffect, useRef, useState } from "react"

import { useTheme } from "@/components/theme-provider"

const DARK_SCHEME_QUERY = "(prefers-color-scheme: dark)"
const DESKTOP_QUERY = "(min-width: 1280px)"
const REDUCED_DATA_QUERY = "(prefers-reduced-data: reduce)"
const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)"
const LOOP_DURATION = 60_000

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

type Point = { x: number; y: number }

const STARS = Array.from({ length: 72 }, (_, index) => ({
  x: ((index * 47 + 13) % 101) / 100,
  y: ((index * 71 + 29) % 103) / 102,
  size: 0.35 + ((index * 17) % 9) / 10,
  alpha: 0.12 + ((index * 31) % 13) / 100,
}))

function getPosition(time: number, width: number, height: number): Point {
  const phase = (time / LOOP_DURATION) * Math.PI * 2
  return {
    x:
      width *
      (0.8 + Math.sin(phase) * 0.055 + Math.sin(phase * 2.3 + 0.8) * 0.015),
    y:
      height *
      (0.35 +
        Math.sin(phase * 0.73 + 1.4) * 0.085 +
        Math.sin(phase * 1.9) * 0.02),
  }
}

function lensPoint(point: Point, hole: Point, radius: number): Point {
  const dx = point.x - hole.x
  const dy = point.y - hole.y
  const distanceSquared = dx * dx + dy * dy
  const influence = (radius * radius) / (distanceSquared + radius * radius)
  const bend = influence * 0.52
  return { x: hole.x + dx * (1 + bend), y: hole.y + dy * (1 + bend) }
}

function traceLensedLine(
  context: CanvasRenderingContext2D,
  hole: Point,
  radius: number,
  points: number,
  getPoint: (progress: number) => Point
) {
  context.beginPath()
  for (let index = 0; index <= points; index += 1) {
    const point = lensPoint(getPoint(index / points), hole, radius)
    if (index === 0) context.moveTo(point.x, point.y)
    else context.lineTo(point.x, point.y)
  }
  context.stroke()
}

export function BlackHoleAccent() {
  const { theme } = useTheme()
  const [enabled, setEnabled] = useState(false)
  const sceneRef = useRef<HTMLDivElement | null>(null)
  const accentRef = useRef<HTMLDivElement | null>(null)
  const lensCanvasRef = useRef<HTMLCanvasElement | null>(null)

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
        idleHandle = idleWindow.requestIdleCallback(() => setEnabled(true), {
          timeout: 1_200,
        })
        return
      }
      timeoutHandle = window.setTimeout(() => setEnabled(true), 650)
    }

    const queries = [colorScheme, desktop, reducedData, reducedMotion]
    for (const query of queries)
      query.addEventListener("change", updateEligibility)
    updateEligibility()

    return () => {
      cancelPendingMount()
      for (const query of queries) {
        query.removeEventListener("change", updateEligibility)
      }
    }
  }, [theme])

  useEffect(() => {
    if (!enabled || typeof window.requestAnimationFrame !== "function") return

    const scene = sceneRef.current
    const accent = accentRef.current
    const canvas = lensCanvasRef.current
    if (!scene || !accent || !canvas) return
    if (import.meta.env.MODE === "test") return

    let context: CanvasRenderingContext2D | null = null
    try {
      context = canvas.getContext("2d")
    } catch {
      return
    }
    if (!context) return

    const visualTest = new URLSearchParams(window.location.search).has(
      "visual-test"
    )
    const pointer = { x: 0, y: 0 }
    const startedAt = performance.now()
    let frame = 0
    let lastPaint = 0
    let visible = true
    let width = 1
    let height = 1
    let dpr = 1

    const resize = () => {
      const bounds = scene.getBoundingClientRect()
      width = Math.max(1, Math.round(bounds.width))
      height = Math.max(1, Math.round(bounds.height))
      dpr = Math.min(window.devicePixelRatio || 1, 1.25)
      canvas.width = Math.round(width * dpr)
      canvas.height = Math.round(height * dpr)
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      context.setTransform(dpr, 0, 0, dpr, 0, 0)
    }

    const paint = (now: number) => {
      frame = window.requestAnimationFrame(paint)
      if (
        !visible ||
        document.hidden ||
        (!visualTest && now - lastPaint < 32)
      ) {
        return
      }
      lastPaint = now

      const elapsed = visualTest ? 8_200 : now - startedAt
      const base = getPosition(elapsed, width, height)
      const hole = {
        x: base.x + pointer.x * 11,
        y: base.y + pointer.y * 8,
      }
      const holeSize = Math.min(230, Math.max(164, width * 0.19))
      const lensRadius = holeSize * 0.72
      const rotation = Math.sin((elapsed / LOOP_DURATION) * Math.PI * 2) * 3
      const scale =
        0.98 + Math.sin((elapsed / LOOP_DURATION) * Math.PI * 4) * 0.025

      accent.style.width = `${holeSize}px`
      accent.style.transform = `translate3d(${hole.x - holeSize / 2}px, ${hole.y - holeSize / 2}px, 0) rotate(${rotation}deg) scale(${scale})`

      context.clearRect(0, 0, width, height)
      const glow = context.createRadialGradient(
        hole.x,
        hole.y,
        holeSize * 0.28,
        hole.x,
        hole.y,
        lensRadius * 1.35
      )
      glow.addColorStop(0, "rgba(211, 150, 88, 0.08)")
      glow.addColorStop(0.5, "rgba(151, 103, 62, 0.025)")
      glow.addColorStop(1, "rgba(151, 103, 62, 0)")
      context.fillStyle = glow
      context.fillRect(0, 0, width, height)

      context.lineWidth = 1
      context.strokeStyle = "rgba(210, 176, 136, 0.105)"
      traceLensedLine(context, hole, lensRadius, 180, (progress) => {
        const angle = progress * Math.PI * 2
        return {
          x: width * 0.98 + Math.cos(angle) * Math.min(width * 0.37, 330),
          y: height * 0.88 + Math.sin(angle) * Math.min(width * 0.37, 330),
        }
      })

      context.strokeStyle = "rgba(222, 190, 151, 0.075)"
      for (const offset of [-0.06, 0.08]) {
        traceLensedLine(context, hole, lensRadius, 110, (progress) => ({
          x: width * (0.46 + progress * 0.62),
          y:
            height * (0.21 + offset + progress * 0.47) +
            Math.sin(progress * Math.PI * 2.2) * 16,
        }))
      }

      for (const star of STARS) {
        const point = lensPoint(
          { x: star.x * width, y: star.y * height },
          hole,
          lensRadius
        )
        const dx = point.x - hole.x
        const dy = point.y - hole.y
        const proximity = Math.max(
          0,
          1 - Math.hypot(dx, dy) / (lensRadius * 1.5)
        )
        context.fillStyle = `rgba(230, 210, 187, ${star.alpha + proximity * 0.16})`
        context.beginPath()
        context.arc(
          point.x,
          point.y,
          star.size + proximity * 0.8,
          0,
          Math.PI * 2
        )
        context.fill()
      }

      if (visualTest) window.cancelAnimationFrame(frame)
    }

    const onPointerMove = (event: PointerEvent) => {
      const bounds = scene.getBoundingClientRect()
      pointer.x =
        Math.max(
          -1,
          Math.min(1, (event.clientX - bounds.left) / bounds.width - 0.5)
        ) * 2
      pointer.y =
        Math.max(
          -1,
          Math.min(1, (event.clientY - bounds.top) / bounds.height - 0.5)
        ) * 2
    }
    const resizeObserver = new ResizeObserver(resize)
    const intersectionObserver = new IntersectionObserver((entries) => {
      visible = entries[0]?.isIntersecting ?? true
    })
    resizeObserver.observe(scene)
    intersectionObserver.observe(scene)
    scene.parentElement?.addEventListener("pointermove", onPointerMove, {
      passive: true,
    })
    resize()
    frame = window.requestAnimationFrame(paint)

    return () => {
      window.cancelAnimationFrame(frame)
      resizeObserver.disconnect()
      intersectionObserver.disconnect()
      scene.parentElement?.removeEventListener("pointermove", onPointerMove)
    }
  }, [enabled])

  if (!enabled) return null

  const visualTest =
    typeof window !== "undefined" &&
    new URLSearchParams(window.location.search).has("visual-test")

  return (
    <div
      aria-hidden="true"
      className="black-hole-wander-scene"
      data-testid="black-hole-wander-scene"
      ref={sceneRef}
    >
      <canvas
        className="black-hole-lensing-field"
        data-testid="black-hole-lensing-field"
        ref={lensCanvasRef}
      />
      <div
        className="black-hole-accent"
        data-testid="black-hole-accent"
        ref={accentRef}
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
            maxFps={30}
            midColor="#d9a064"
            paused={visualTest}
            resolution={0.45}
            roll={-18}
            spinSpeed={0.025}
            starBrightness={0}
            steps={150}
            vignette={0.34}
          />
        </Suspense>
      </div>
    </div>
  )
}
