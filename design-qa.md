# Login black-hole accent design QA

## Comparison target

- Source visual truth: `C:\Users\example\.codex\generated_images\019fdcbd-12f7-7462-9a92-c6eb99d4362f\exec-a9d323d9-05ec-4e28-897d-ea8765dac40b.png`
- Implementation: `http://server.example.com:8180/login`
- Implementation screenshot: `C:\Users\example\Documents\Codex\2026-08-07\twitter\work\remote-ui\qa\login-dark-production.png`
- Motion-focused screenshot: `C:\Users\example\Documents\Codex\2026-08-07\twitter\work\remote-ui\qa\login-wander-final.jpg`
- Wide-path screenshots: `C:\Users\example\Documents\Codex\2026-08-07\twitter\work\remote-ui\qa\login-wide-path-top.jpg` and `C:\Users\example\Documents\Codex\2026-08-07\twitter\work\remote-ui\qa\login-wide-path-bottom.jpg`
- Responsive screenshot: `C:\Users\example\Documents\Codex\2026-08-07\twitter\work\remote-ui\qa\login-mobile-production.png`
- Viewport: 1440 x 900 CSS px, device scale factor 1
- Pixel normalization: source 1440 x 900 px and implementation 1440 x 900 px; no resampling required
- State: unauthenticated login page, dark theme, renderer loaded after the browser became idle

## Full-view comparison evidence

- Fonts and typography: the existing Geist/Noto Sans SC hierarchy, weights, wrapping, and copy remain unchanged. Both the source and implementation keep the headline on two fixed lines and preserve the compact login-form hierarchy.
- Spacing and layout rhythm: the 59/41 split, story copy, login form, telemetry panel, and orbital line remain aligned with the source. The live accent occupies a 244.8 x 212.9 px box at x=554.8, y=252 without intersecting copy or controls.
- Colors and visual tokens: the monochrome neutral theme is unchanged. The black-hole rim uses restrained warm-white and muted amber light and fades into the near-black story panel.
- Image quality and asset fidelity: the user-supplied WebGL ray-marched renderer is used directly. It is masked into the panel rather than replaced by CSS art, a compressed video, an iframe, or a raster approximation.
- Copy and content: all Chinese product copy, labels, telemetry values, and login controls match the selected source.
- Focused-region comparison: a separate crop was not required because the only changed asset is fully visible at more than 200 px in the normalized full-view captures; its edge fade, sharp center, and non-overlap are directly readable.

## Comparison history

### Iteration 1

- Finding: P2 — the first live render was smaller and lower than the selected source, which made it read more like a status glyph than the chosen decorative focal point.
- Fix: changed the camera field of view from 48 to 38, moved the container from 31vh to 28vh, and raised brightness, exposure, glow, and final opacity slightly.
- Post-fix evidence: the final production capture places the 244.8 x 212.9 px accent beside the headline at the same visual scale and vertical band as the source, with no overlap.

### Final pass

- No actionable P0, P1, or P2 mismatches remain.
- P3: the live physical renderer naturally has a slightly cleaner, thinner photon ring than the still concept. This is acceptable because motion and fidelity to the supplied component are intentional.

### Iteration 2 — roaming gravitational lens

- Finding: the static accent did not communicate a moving gravity well, while moving the renderer alone left the background visually unaffected.
- Fix: added a full-story lensing canvas that bends sampled orbit paths, light traces, and star points around the renderer's live center; the renderer now follows a restrained irregular 60-second path with a small pointer perturbation.
- Motion evidence: two live frames 2.6 seconds apart moved the accent by 9.98 CSS px after tuning. The visual-test query freezes the same position exactly across captures, preventing flaky screenshot baselines.
- Composition evidence: at the 1280 x 720 browser viewport, the final accent is 163.4 x 142.4 CSS px inside a 755.2 px story panel. It remains behind the z-indexed copy and outside the login form.
- Accessibility and performance: the scene remains decorative and pointer-transparent, caps both animation layers at 30 fps, pauses offscreen or in a hidden tab, and is not mounted for light theme, mobile width, reduced motion, or reduced data.

### Iteration 3 — full story-panel route

- Reference evidence: the user marked the complete left story panel as the permitted movement region, from the logo band down to the telemetry panel and ending at the center divider.
- Fix: replaced the small harmonic orbit with an eight-point closed Catmull-Rom path spanning the upper-right, upper-left, lower-left, and lower-right portions of the story panel. The full loop is 120 seconds and remains smooth across the loop boundary.
- Boundary evidence at 2048 x 1104: the story panel ends at x=1208.3. Four frozen route frames placed the accent at x/y 853.2/130.2, 172.3/80.3, 165.2/638.0, and 872.4/610.2; every rendered edge remained within x=0..1208.3 and y=0..1104, with no entry into the login panel.
- Interaction evidence: a live 2.2-second sample moved 45.3 CSS px; light theme removed the scene and returning to dark remounted it. Browser console contained no warnings or errors.

## Browser and interaction checks

- Page identity: `APT Hunter` at `/login`.
- Meaningful render: login story, form, telemetry, and live canvas all present.
- Framework overlay: none.
- Console health: no warnings or errors on the production page.
- Password visibility: `password` -> `text` -> `password` verified.
- Theme behavior: switching to light removes the accent; returning to dark remounts it after idle.
- Responsive behavior: at 390 x 844 the story and renderer are not mounted, while the complete login form remains visible.
- Deterministic visual baseline: `/login?visual-test=1` holds the renderer and trajectory at a fixed frame.
- Performance behavior: the renderer is an independent 25.98 kB production chunk (10.36 kB gzip), loaded only on eligible dark desktop sessions; the lensing layer uses no per-frame React state updates.

## Follow-up polish

- Revisit the glow only if user testing shows the moving ring draws too much attention during credential entry.

final result: passed
