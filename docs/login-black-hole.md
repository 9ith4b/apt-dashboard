# Black-hole login experience

## Rendering decision

The login page embeds Nestaeric's **Black Hole** model with Sketchfab's official iframe viewer. This preserves the author's materials, camera, and post-processing instead of shipping the visibly degraded, mesh-compressed FBX conversion.

- Model: `e410da98b1e5445eae2acafaaa53587d`
- Source credit: [Black Hole by Nestaeric on Sketchfab](https://sketchfab.com/3d-models/black-hole-e410da98b1e5445eae2acafaaa53587d)
- Privacy: the embed uses `dnt=1`.
- Interaction isolation: the iframe is decorative, removed from the tab order, and cannot intercept pointer input from the login form.
- Viewer presentation: autostart and slow autospin are enabled; viewer controls, hints, annotations, information chrome, and watermark are suppressed where the model owner's plan permits it. A visible source-credit link remains in the APT Hunter UI.

## Resilience and performance

- The Sketchfab viewer loads only on the unauthenticated login route and does not add JavaScript or model bytes to the application bundle.
- A local CSS starfield and black-hole treatment is visible while the iframe loads.
- A viewer error, reduced-data preference, or a 20-second timeout switches to the local fallback rather than leaving an empty background.
- The original ZIP remains outside the repository. The experimental Three.js runtime and compressed GLB were removed.

## Verification

- Desktop visual QA: 1440 × 900
- Mobile visual QA: 390 × 844
- No page overflow at either viewport
- Password visibility toggle verified in a real browser
- Browser console checked for warnings and errors
- Frontend lint, 17 unit tests, type checking, production build, and bundle budget passed

The login UI deliberately differs from the rest of the authenticated workspace: it uses an immersive warm-gold space composition, violet focus states, and a dark glass authentication panel while preserving the existing authentication contract.
