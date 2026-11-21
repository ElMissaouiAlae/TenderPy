# 02: Tender list in the design

**What to build:** The operator opens the Tenders page and sees the list in the design canvas's "Best matches" style. A heading and a one-line description say the list holds every tender whose DCE archive is available. Below them, a card holds a two-column table. The **Tender** column shows the tender object, with "public buyer · reference number" in muted text beneath. The **Deadline** column shows the tender end date exactly as recorded. Rows react on hover. Loading, empty and error messages match the design. No backend change. See `.scratch/ui-dashboard-design/spec.md`.

**Blocked by:** 01 (Design tokens and layout shell)

**Status:** done

- [x] Page heading "Tenders" with a one-line description of what is listed
- [x] List sits in a card, as a table styled like the design's "Best matches" table
- [x] Exactly two columns: Tender (object, shortened when long with the full text in a hover title, with "public buyer · reference number" muted beneath) and Deadline (tender end date passed through unchanged, no parsing or countdown)
- [x] Rows have a hover state, styled so the whole row reads as one target. If the detail route already exists (tracer-bullet `ui-dashboard/02`), the whole row is a real link to it; otherwise that ticket adds the link
- [x] Loading, empty and error messages keep their wording and use the design's styling
- [x] At phone width the table scrolls inside its card, not the page
- [x] Not shown: category column, budget, match score, days-left countdown, category filter tabs, KPI tiles, side panels, "Showing N of M" footer, status
- [x] Styles use the custom properties from 01, not raw values
- [x] API and API client types unchanged; existing API tests pass; UI TypeScript build passes
- [x] Manually verified against the real database: real tenders in two columns, long objects shortened, all three message states (stop the API for the error state), phone width, side by side with the canvas
