import { useEffect, useState } from "react"

const SKETCHFAB_EMBED_URL =
  "https://sketchfab.com/models/e410da98b1e5445eae2acafaaa53587d/embed?autostart=1&autospin=0.12&camera=0&dnt=1&annotations_visible=0&ui_controls=0&ui_hint=0&ui_infos=0&ui_stop=0&ui_theme=dark&ui_watermark=0"

export function BlackHoleScene() {
  const [state, setState] = useState<"loading" | "ready" | "fallback">(() =>
    window.matchMedia("(prefers-reduced-data: reduce)").matches
      ? "fallback"
      : "loading"
  )

  useEffect(() => {
    if (state !== "loading") return

    const fallbackTimer = window.setTimeout(() => setState("fallback"), 20000)
    return () => window.clearTimeout(fallbackTimer)
  }, [state])

  return (
    <div
      aria-hidden="true"
      className="black-hole-scene"
      data-state={state}
      data-testid="black-hole-scene"
    >
      <div className="black-hole-fallback" />
      {state !== "fallback" ? (
        <iframe
          allow="autoplay; fullscreen; xr-spatial-tracking"
          allowFullScreen
          aria-hidden="true"
          loading="eager"
          referrerPolicy="strict-origin-when-cross-origin"
          sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
          src={SKETCHFAB_EMBED_URL}
          tabIndex={-1}
          title="Black Hole by Nestaeric on Sketchfab"
          onError={() => setState("fallback")}
          onLoad={() => setState("ready")}
        />
      ) : null}
    </div>
  )
}
