# 03: Tender detail in the template

**What to build:** The tender detail page is restyled to match the template: back link, category and procurement-type tags, the object as title, a muted buyer/reference/publication line, a filled blue "Download DCE archive" button, and a white "Key facts" card. See `.scratch/ui-dashboard-figma/spec.md`.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] "← Back to tenders" link, tags (empty tag omitted), object as title, muted "public buyer · Ref. reference number · Published publication date" line
- [ ] "Download DCE archive" stays a plain link to `dceArchiveUrl(id)`, styled as the template's filled blue button
- [ ] "Key facts" card with muted labels: tender ID, organization acronym, location, tender end date
- [ ] Every detail field appears exactly once; nulls show a muted "—"
- [ ] Loading, not-found and error states restyled
- [ ] API unchanged; existing API tests pass; `npm run build` passes
- [ ] Manually verified: matches the template's card and button styles; download saves a valid zip
