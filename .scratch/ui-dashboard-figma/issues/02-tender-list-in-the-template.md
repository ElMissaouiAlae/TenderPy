# 02: Tender list in the template

**What to build:** The tender list becomes a "Recent Transactions"-style table in a white card, with Object, Reference, Public buyer and Deadline columns and an outlined Download button per row that saves the tender's DCE archive without opening it. Clicking elsewhere on the row opens the tender. Previous/Next paging shows 20 tenders per page and keeps the page in the URL as `?page=N`. See `.scratch/ui-dashboard-figma/spec.md` (frames `105:0` and `181:279`).

**Blocked by:** 01

**Status:** ready-for-human

- [x] Columns: Object (shortened, full text in hover title, "Untitled tender" when missing), Reference, Public buyer, Deadline (pass-through), Download; missing values show a muted "—"; no round per-row icon
- [x] Download is an outlined pill link to `dceArchiveUrl(id)`, separate from the row link, which doesn't cover it; it downloads without navigating
- [x] The rest of the row is a real link to `/tenders/:id`; Tab reaches the row link and Download separately
- [x] `?page=N` (1-based; missing/invalid/<1 means 1) drives `limit=20, offset=(N−1)×20`
- [x] Previous disabled on page 1; Next disabled when fewer than 20 come back; an empty page beyond 1 shows "No more tenders." with Previous enabled
- [x] Pager styled like the template's, without page numbers
- [x] Loading, empty and error messages keep their wording, restyled
- [x] No cards/expense panels, filter tabs, search or page numbers
- [x] API unchanged; existing API tests pass; `npm run build` passes
- [ ] Manually verified against frame `105:0` and at phone width against `181:279`

## Comments

**2026-11-21 (agent):** Code shipped. Every box is ticked except the manual check against the frames. No browser was connected, so the agent rendered the page in headless Chrome against a stub API with 45 fake tenders. It checked page 1, page 3 (partial page, Next disabled), page 4 ("No more tenders.", Previous enabled) and `?page=abc` at 375 px, then compared them by eye with `105:0` and `181:279`. Clicking, downloading and Tab order were not exercised.
- Frame `105:0` shows the outlined Download pills in navy `#123288`, with `#1814F3` on one row. The code uses `#123288` at rest and `#1814F3` on hover, and the spec records this.
- At phone width the table becomes a stacked list, as in `181:279`. The object comes first, then "Ref.", "Buyer" and "Deadline" lines in muted text, with Download on the right.
- Changing page scrolls the window to the top, because the pager sits below the table.

To finish: run `python -m api` and `npm run dev` in `ui/` with the database reachable. Then check that a row click opens the tender, that Download saves a zip without navigating, that Tab goes from the row link to Download, and the phone width. Then tick the last box and set the status to `done`.
