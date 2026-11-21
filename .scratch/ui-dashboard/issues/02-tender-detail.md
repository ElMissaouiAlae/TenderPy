# 02: Tender detail page

**What to build:** Clicking a tender in the list opens its own detail page at its own URL (by database id), showing tender ID, organization acronym, reference number, tender object, public buyer, location, category, procurement type, publication date and tender end date. No status or last status is shown. The URL survives reload. An unknown tender, or one without a DCE archive, shows a clear "not found" message. The operator can go back to the list. See `.scratch/ui-dashboard/spec.md`.

**Blocked by:** 01 (Tender list, end to end), `ui-dashboard-design/01` (Design tokens and layout shell)

**Status:** done

- [x] Tender lookup gets one tender by database id, only if it has a DCE archive
- [x] `GET /tenders/{id}` returns the detail fields; 404 for an unknown id or a tender without a DCE archive
- [x] List rows link to the detail route (the whole row is the link, per `.scratch/ui-dashboard-design/spec.md`)
- [x] Detail page built straight to the design, per the "Tender detail page" decision in `.scratch/ui-dashboard-design/spec.md`: back link, header with category and procurement type pills, object as title and "public buyer · Ref. … · Published …", a Key facts card (tender ID, organization acronym, location, end date); every detail field shown exactly once, nulls as a muted placeholder; no design-only fields or features; holds up at phone width
- [x] Detail page shows loading, not-found, and error states, and a way back to the list
- [x] pytest via the test client: detail fields for a tender with a DCE archive, no status fields, 404 for both not-found cases
- [x] Manually verified: click through list → detail, reload the detail URL
