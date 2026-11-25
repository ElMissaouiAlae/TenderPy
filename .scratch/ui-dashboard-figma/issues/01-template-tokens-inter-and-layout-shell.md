# 01: Template tokens, Inter and layout shell

**What to build:** The operator opens the dashboard and it now has the BankDash template's look: Inter text, the navy/blue palette on a light grey-blue page, a sidebar with the TenderPy name and a single "Tenders" entry marked active with the template's blue bar, and a top bar showing only the page title. At phone width the sidebar becomes a drawer opened from a menu button. See `.scratch/ui-dashboard-figma/spec.md` (frames `78:351` and `169:3352`).

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Purple tokens replaced by the template's values as CSS custom properties on the root (navy `#343C6A`, blue accent `#1814F3`, `#2D60FF`, page `#F5F7FA`, borders `#E6EFF5`, card shadow, muted text darkened to about `#5B6F96`); confirmed against the frames with `get_design_context`
- [x] Inter bundled via `@fontsource-variable/inter`, system sans fallback; no CDN request
- [x] Sidebar: TenderPy name (not the BankDash logo), only "Tenders", active entry with blue bar and blue text, inline stroke SVG icons; the nav-entry list stays the single registration point
- [x] Collapse toggle removed
- [x] Top bar shows only the current page title; no search, settings, notifications or avatar
- [x] Phone width: menu button (`aria-label`, `aria-expanded`) opens the sidebar as a drawer that closes on navigation and on Escape
- [x] 4.5:1 text contrast, 44 px touch targets, visible focus styles
- [x] API unchanged; existing API tests pass; `npm run build` passes
- [x] Manually verified against frames `78:351` and `169:3352`

## Comments

**2026-11-21 (agent):** Code shipped. Every box is ticked except the manual check against the frames, which needs a person with a browser (the agent had no browser connected).
- Frame `78:351` showed the active nav entry uses `#2D60FF` ("Primary 3"), not `#1814F3`. The spec is updated to match.
- Inactive nav and muted text use `#5B6F96` for contrast. Error text keeps `#B42318`.
- The top bar's title is now the page's `h1`, so the list page's own "Tenders" heading was removed and the detail title became an `h2`.

To finish: run `python -m api` and `npm run dev` in `ui/`, then compare the result with `78:351` and `169:3352`. Check the phone-width drawer, including Escape, clicking the backdrop and clicking a link. Then tick the last box and set the status to `done`.
