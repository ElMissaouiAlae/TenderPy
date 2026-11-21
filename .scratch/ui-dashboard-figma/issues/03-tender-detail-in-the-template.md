# 03: Tender detail in the template

**What to build:** The tender detail page is restyled to match the template: back link, category and procurement-type tags, the object as title, a muted buyer/reference/publication line, a filled blue "Download DCE archive" button, and a white "Key facts" card. See `.scratch/ui-dashboard-figma/spec.md`.

**Blocked by:** 01

**Status:** ready-for-human

- [x] "← Back to tenders" link, tags (empty tag omitted), object as title, muted "public buyer · Ref. reference number · Published publication date" line
- [x] "Download DCE archive" stays a plain link to `dceArchiveUrl(id)`, styled as the template's filled blue button
- [x] "Key facts" card with muted labels: tender ID, organization acronym, location, tender end date
- [x] Every detail field appears exactly once; nulls show a muted "—"
- [x] Loading, not-found and error states restyled
- [x] API unchanged; existing API tests pass; `npm run build` passes
- [ ] Manually verified: matches the template's card and button styles; download saves a valid zip

## Comments

**2026-11-21 (agent):** Code shipped. Every box is ticked except the manual check. No browser was connected and the database wasn't reachable, so the agent rendered the page in headless Chrome against a stub API. It checked a full tender, an all-null tender, a not-found id and a 500 error at 1280 px, and a full tender at 375 px, then compared them by eye with frame `78:351`. The stub's archive link returned a valid zip, but no real download was clicked.
- "Key facts" sits above its card as a 22 px section title, as the template does with "My Cards". The spec now records this.
- The download is the template's "Send" pill: 50 px high and `#1814F3`. At phone width it spans the full width.
- `.card` lost its 1 px border to match the template's borderless cards. This also applies to the tender list's card.
- A missing object shows a muted "—" as the title, as the spec says. The list shows "Untitled tender" in the same case, so decide whether the two should match.

To finish: run `python -m api` and `npm run dev` in `ui/` with the database reachable. Open a tender, compare it with `78:351`, and check that "Download DCE archive" saves a valid zip. Then tick the last box and set the status to `done`.
