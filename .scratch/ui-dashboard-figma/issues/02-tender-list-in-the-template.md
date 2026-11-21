# 02: Tender list in the template

**What to build:** The tender list becomes a "Recent Transactions"-style table in a white card, with Object, Reference, Public buyer and Deadline columns and an outlined Download button per row that saves the tender's DCE archive without opening it. Clicking elsewhere on the row opens the tender. Previous/Next paging shows 20 tenders per page and keeps the page in the URL as `?page=N`. See `.scratch/ui-dashboard-figma/spec.md` (frames `105:0` and `181:279`).

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Columns: Object (shortened, full text in hover title, "Untitled tender" when missing), Reference, Public buyer, Deadline (pass-through), Download; missing values show a muted "—"; no round per-row icon
- [ ] Download is an outlined pill link to `dceArchiveUrl(id)`, separate from the row link, which doesn't cover it; it downloads without navigating
- [ ] The rest of the row is a real link to `/tenders/:id`; Tab reaches the row link and Download separately
- [ ] `?page=N` (1-based; missing/invalid/<1 means 1) drives `limit=20, offset=(N−1)×20`
- [ ] Previous disabled on page 1; Next disabled when fewer than 20 come back; an empty page beyond 1 shows "No more tenders." with Previous enabled
- [ ] Pager styled like the template's, without page numbers
- [ ] Loading, empty and error messages keep their wording, restyled
- [ ] No cards/expense panels, filter tabs, search or page numbers
- [ ] API unchanged; existing API tests pass; `npm run build` passes
- [ ] Manually verified against frame `105:0` and at phone width against `181:279`
