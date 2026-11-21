# 01: Design tokens and layout shell

**What to build:** The operator opens the dashboard and it now has the design canvas's look (https://claude.ai/artifact/1WrXRR8ZyfXNqpw4rD6PMj): a slate page background and a restyled sidebar. The sidebar shows the product name at the top, a design-style "Tenders" entry highlighted on the active page, and a drawn toggle that collapses and expands it. The design's colours, radii and spacing are defined once as CSS custom properties, which every later page uses. The sidebar still lists only pages that exist. See `.scratch/ui-dashboard-design/spec.md`.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Design values (accent `#6A4BE0` and its hover shade, slate background, card surface, border and muted-text greys, text colour, card/button/pill radii, spacing) defined once as CSS custom properties on the root; components reference them, not raw values
- [x] Plain CSS only; system sans stack; no web font, styling or component library, no dark mode
- [x] Sidebar shows the product name, design-style nav entries with an active state, and only "Tenders"; the single nav-entry list stays the one place a page is registered
- [x] The `«`/`»` toggle is replaced by an inline stroke SVG icon, keeping `aria-label` and `aria-expanded`; decorative SVGs are `aria-hidden`
- [x] Collapsed sidebar still shows a recognisable mark per entry
- [x] Main area is fluid inside a max-width container; at phone width the sidebar collapses or stacks and nothing scrolls the page sideways
- [x] Text meets 4.5:1 contrast (muted labels included); touch targets at least 44 px
- [x] No status or last status shown; no design-only sidebar items (Overview, Recommendations, Saved, Alerts, Company profile), promo card or avatar
- [x] API unchanged; existing API tests pass; UI TypeScript build passes
- [x] Manually verified: both servers running, shell matches the canvas side by side, toggle works, holds up at phone width
