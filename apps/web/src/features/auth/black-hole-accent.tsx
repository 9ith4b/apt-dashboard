import { lazy, Suspense, useEffect, useRef, useState } from "react"

import { useTheme } from "@/components/theme-provider"

const DARK_SCHEME_QUERY = "(prefers-color-scheme: dark)"
const DESKTOP_QUERY = "(min-width: 1280px)"
const REDUCED_DATA_QUERY = "(prefers-reduced-data: reduce)"
const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)"
const LOOP_DURATION = 120_000

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
type ThemeTone = "dark" | "light"

const WANDER_PATH: Point[] = [
  { x: 0.8, y: 0.22 },
  { x: 0.54, y: 0.14 },
  { x: 0.24, y: 0.18 },
  { x: 0.14, y: 0.44 },
  { x: 0.23, y: 0.68 },
  { x: 0.52, y: 0.72 },
  { x: 0.82, y: 0.66 },
  { x: 0.88, y: 0.4 },
]

const STARS = Array.from({ length: 72 }, (_, index) => ({
  x: ((index * 47 + 13) % 101) / 100,
  y: ((index * 71 + 29) % 103) / 102,
  size: 0.35 + ((index * 17) % 9) / 10,
  alpha: 0.12 + ((index * 31) % 13) / 100,
}))

function catmullRom(
  before: number,
  start: number,
  end: number,
  after: number,
  progress: number
) {
  const squared = progress * progress
  const cubed = squared * progress
  return (
    0.5 *
    (2 * start +
      (-before + end) * progress +
      (2 * before - 5 * start + 4 * end - after) * squared +
      (-before + 3 * start - 3 * end + after) * cubed)
  )
}

function getPosition(time: number, width: number, height: number): Point {
  const pathProgress =
    (((time % LOOP_DURATION) + LOOP_DURATION) % LOOP_DURATION) / LOOP_DURATION
  const scaled = pathProgress * WANDER_PATH.length
  const index = Math.floor(scaled) % WANDER_PATH.length
  const progress = scaled - Math.floor(scaled)
  const point = (offset: number) =>
    WANDER_PATH[(index + offset + WANDER_PATH.length) % WANDER_PATH.length]!
  const before = point(-1)
  const start = point(0)
  const end = point(1)
  const after = point(2)
  const normalizedX = Math.max(
    0.13,
    Math.min(0.87, catmullRom(before.x, start.x, end.x, after.x, progress))
  )
  const normalizedY = Math.max(
    0.13,
    Math.min(0.73, catmullRom(before.y, start.y, end.y, after.y, progress))
  )

  return {
    x: width * normalizedX,
    y: height * normalizedY,
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

function createRadialDisplacementMap(size = 192) {
  const map = document.createElement("canvas")
  map.width = size
  map.height = size
  const context = map.getContext("2d")
  if (!context) return null

  const image = context.createImageData(size, size)
  const center = size / 2
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const normalizedX = (x + 0.5 - center) / center
      const normalizedY = (y + 0.5 - center) / center
      const radius = Math.hypot(normalizedX, normalizedY)
      const offset = (y * size + x) * 4
      let red = 128
      let green = 128

      if (radius > 0.025 && radius < 1) {
        const ring = Math.pow(Math.sin(radius * Math.PI), 0.72)
        const falloff = 1 - radius * 0.18
        const strength = ring * falloff * 118
        red += (normalizedX / radius) * strength
        green += (normalizedY / radius) * strength
      }

      image.data[offset] = Math.max(0, Math.min(255, Math.round(red)))
      image.data[offset + 1] = Math.max(0, Math.min(255, Math.round(green)))
      image.data[offset + 2] = 128
      image.data[offset + 3] = 255
    }
  }
  context.putImageData(image, 0, 0)
  return map.toDataURL("image/png")
}

export function BlackHoleAccent() {
  const { theme } = useTheme()
  const [enabled, setEnabled] = useState(false)
  const [tone, setTone] = useState<ThemeTone>("light")
  const sceneRef = useRef<HTMLDivElement | null>(null)
  const accentRef = useRef<HTMLDivElement | null>(null)
  const horizonRef = useRef<HTMLDivElement | null>(null)
  const lensCanvasRef = useRef<HTMLCanvasElement | null>(null)
  const domLensFilterRef = useRef<SVGFilterElement | null>(null)
  const displacementImageRef = useRef<SVGFEImageElement | null>(null)
  const displacementRef = useRef<SVGFEDisplacementMapElement | null>(null)

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
      setTone(dark ? "dark" : "light")
      const eligible =
        desktop.matches && !reducedData.matches && !reducedMotion.matches

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
    const horizon = horizonRef.current
    const canvas = lensCanvasRef.current
    if (!scene || !accent || !horizon || !canvas) return
    if (import.meta.env.MODE === "test") return

    let context: CanvasRenderingContext2D | null = null
    try {
      context = canvas.getContext("2d")
    } catch {
      return
    }
    if (!context) return

    const lightTone = tone === "light"
    const story = scene.parentElement
    const storyContent = story?.querySelector<HTMLElement>(
      ".login-story-content"
    )
    const domLensFilter = domLensFilterRef.current
    const displacementImage = displacementImageRef.current
    const displacement = displacementRef.current
    const displacementMap = createRadialDisplacementMap()
    const domLensEnabled = Boolean(
      storyContent &&
      domLensFilter &&
      displacementImage &&
      displacement &&
      displacementMap
    )
    if (domLensEnabled) {
      displacementImage!.setAttribute("href", displacementMap!)
      storyContent!.style.filter = "url(#black-hole-dom-lens)"
      storyContent!.style.willChange = "filter"
    }

    const visualTest = new URLSearchParams(window.location.search).has(
      "visual-test"
    )
    const motionFrameParam = new URLSearchParams(window.location.search).get(
      "motion-frame"
    )
    const requestedMotionFrame = Number(motionFrameParam)
    const frozenTime =
      motionFrameParam !== null && Number.isFinite(requestedMotionFrame)
        ? (Math.max(0, Math.min(WANDER_PATH.length - 1, requestedMotionFrame)) /
            WANDER_PATH.length) *
          LOOP_DURATION
        : 8_200
    const pointer = { x: 0, y: 0 }
    const startedAt = performance.now()
    let frame = 0
    let lastPaint = 0
    let visible = true
    let width = 1
    let height = 1
    let dpr = 1
    let contentOffsetX = 0
    let contentOffsetY = 0
    let contentWidth = 1
    let contentHeight = 1

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

      if (domLensEnabled) {
        const contentBounds = storyContent!.getBoundingClientRect()
        contentOffsetX = contentBounds.left - bounds.left
        contentOffsetY = contentBounds.top - bounds.top
        contentWidth = Math.max(1, contentBounds.width)
        contentHeight = Math.max(1, contentBounds.height)
        domLensFilter!.setAttribute("x", "-96")
        domLensFilter!.setAttribute("y", "-96")
        domLensFilter!.setAttribute("width", `${contentWidth + 192}`)
        domLensFilter!.setAttribute("height", `${contentHeight + 192}`)
      }
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

      const elapsed = visualTest ? frozenTime : now - startedAt
      const base = getPosition(elapsed, width, height)
      const hole = {
        x: base.x + pointer.x * 11,
        y: base.y + pointer.y * 8,
      }
      const holeSize = Math.min(230, Math.max(164, width * 0.19))
      const lensRadius = holeSize * 0.72
      const domLensSize = lensRadius * 2.45
      const rotation = Math.sin((elapsed / LOOP_DURATION) * Math.PI * 2) * 3
      const scale =
        0.98 + Math.sin((elapsed / LOOP_DURATION) * Math.PI * 4) * 0.025

      accent.style.width = `${holeSize}px`
      accent.style.transform = `translate3d(${hole.x - holeSize / 2}px, ${hole.y - holeSize / 2}px, 0) rotate(${rotation}deg) scale(${scale})`
      const horizonSize = holeSize * (lightTone ? 0.335 : 0.285)
      horizon.style.width = `${horizonSize}px`
      horizon.style.height = `${horizonSize * 0.94}px`
      horizon.style.transform = `translate3d(${hole.x - horizonSize / 2}px, ${hole.y - horizonSize * 0.45}px, 0) rotate(${rotation}deg) scale(${scale})`

      if (domLensEnabled) {
        displacementImage!.setAttribute(
          "x",
          `${hole.x - contentOffsetX - domLensSize / 2}`
        )
        displacementImage!.setAttribute(
          "y",
          `${hole.y - contentOffsetY - domLensSize / 2}`
        )
        displacementImage!.setAttribute("width", `${domLensSize}`)
        displacementImage!.setAttribute("height", `${domLensSize}`)
        displacement!.setAttribute("scale", `${Math.min(54, holeSize * 0.24)}`)
      }

      context.clearRect(0, 0, width, height)
      const glow = context.createRadialGradient(
        hole.x,
        hole.y,
        holeSize * 0.28,
        hole.x,
        hole.y,
        lensRadius * 1.35
      )
      glow.addColorStop(
        0,
        lightTone ? "rgba(95, 72, 50, 0.09)" : "rgba(211, 150, 88, 0.08)"
      )
      glow.addColorStop(
        0.5,
        lightTone ? "rgba(95, 72, 50, 0.032)" : "rgba(151, 103, 62, 0.025)"
      )
      glow.addColorStop(
        1,
        lightTone ? "rgba(95, 72, 50, 0)" : "rgba(151, 103, 62, 0)"
      )
      context.fillStyle = glow
      context.fillRect(0, 0, width, height)

      context.lineWidth = 1
      context.strokeStyle = lightTone
        ? "rgba(32, 35, 34, 0.12)"
        : "rgba(210, 176, 136, 0.105)"
      traceLensedLine(context, hole, lensRadius, 180, (progress) => {
        const angle = progress * Math.PI * 2
        return {
          x: width * 0.98 + Math.cos(angle) * Math.min(width * 0.37, 330),
          y: height * 0.88 + Math.sin(angle) * Math.min(width * 0.37, 330),
        }
      })

      context.strokeStyle = lightTone
        ? "rgba(32, 35, 34, 0.085)"
        : "rgba(222, 190, 151, 0.075)"
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
        context.fillStyle = lightTone
          ? `rgba(32, 35, 34, ${star.alpha * 0.64 + proximity * 0.12})`
          : `rgba(230, 210, 187, ${star.alpha + proximity * 0.16})`
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
      if (storyContent) {
        storyContent.style.removeProperty("filter")
        storyContent.style.removeProperty("will-change")
      }
    }
  }, [enabled, tone])

  if (!enabled) return null

  const visualTest =
    typeof window !== "undefined" &&
    new URLSearchParams(window.location.search).has("visual-test")

  return (
    <div
      aria-hidden="true"
      className="black-hole-wander-scene"
      data-tone={tone}
      data-testid="black-hole-wander-scene"
      ref={sceneRef}
    >
      <svg
        aria-hidden="true"
        className="black-hole-filter-definitions"
        focusable="false"
      >
        <defs>
          <filter
            colorInterpolationFilters="sRGB"
            filterUnits="userSpaceOnUse"
            id="black-hole-dom-lens"
            primitiveUnits="userSpaceOnUse"
            ref={domLensFilterRef}
          >
            <feFlood floodColor="#808080" result="neutral-map" />
            <feImage
              preserveAspectRatio="none"
              ref={displacementImageRef}
              result="radial-map"
            />
            <feComposite
              in="radial-map"
              in2="neutral-map"
              operator="over"
              result="combined-map"
            />
            <feDisplacementMap
              in="SourceGraphic"
              in2="combined-map"
              ref={displacementRef}
              scale="48"
              xChannelSelector="R"
              yChannelSelector="G"
            />
          </filter>
        </defs>
      </svg>
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
            brightness={tone === "light" ? 0.78 : 0.9}
            coolColor={tone === "light" ? "#405f72" : "#593316"}
            distance={24}
            doppler={0.24}
            elevation={-5}
            exposure={tone === "light" ? 0.82 : 0.9}
            focus={[0.5, 0.52]}
            fov={38}
            glow={tone === "light" ? 0.48 : 0.62}
            hotColor={tone === "light" ? "#c9e6ff" : "#fff1d6"}
            maxDpr={1}
            maxFps={30}
            midColor={tone === "light" ? "#79afd0" : "#d9a064"}
            paused={visualTest}
            resolution={0.45}
            roll={-18}
            spinSpeed={0.025}
            starBrightness={0}
            steps={150}
            vignette={tone === "light" ? 0.18 : 0.34}
          />
        </Suspense>
      </div>
      <div
        className="black-hole-event-horizon"
        data-testid="black-hole-event-horizon"
        ref={horizonRef}
      />
    </div>
  )
}
