# APT Hunter UI theme

APT Hunter uses a restrained intelligence-desk visual language based on the
standard shadcn token contract. Every screen must work in both light and dark
mode without component-specific color overrides.

## Principles

- Use neutral black, white, and gray for navigation, hierarchy, controls, and
  surfaces.
- Reserve color for threat meaning: confirmed is cyan-green, candidate is
  amber, malicious or destructive is red.
- Prefer hairline borders and layered surfaces. Shadows are limited to floating
  overlays and a subtle one-pixel card lift.
- Use open lists and tables for primary content. Cards group a complete task or
  metric, not every individual field.
- Keep radii near 10 px and control heights between 36 and 40 px.

## Theme behavior

The root `ThemeProvider` resolves system preference on first visit, persists an
explicit selection in local storage, and exposes a visible theme toggle on the
login screen and application header. The keyboard shortcut `D` remains
available when focus is outside an editable field.

All component colors must reference semantic variables such as `background`,
`card`, `muted`, `accent`, `border`, and `primary`. Do not add literal light or
dark colors inside feature components.

## Page structure

- Application header: 64 px, one border, title and date on the left, global
  actions on the right.
- Sidebar: 224 px expanded, compact icon rail when collapsed, one strong active
  marker, service health in the footer.
- Standard pages use `workspace-page` for consistent responsive padding and
  scrolling.
- Master/detail workflows preserve the list on the left and use a quiet card
  surface for the inspector.

## Login

The login experience is code-native and does not load external iframes, video,
WebGL, or large raster assets. On desktop it pairs a telemetry/diamond-model
story with a compact form. On smaller screens the story collapses so the form
loads immediately and remains the primary task.
