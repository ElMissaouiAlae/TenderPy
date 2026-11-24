# 02: Every discovered tender is visible

**What to build:** A business user sees every discovered tender in the tender list and can open any of them, whether or not its DCE archive has been downloaded. On the detail page, the "Download DCE archive" button appears only when the tender has a DCE archive. This deliberately reverses the `ui-dashboard` rule that hid tenders without an archive. See `.scratch/insights-dashboard/spec.md`.

**Blocked by:** None (can start immediately). Doing it after 01 avoids merge conflicts in the lookup and API responses.

**Status:** ready-for-agent

- [ ] The tender lookup lists and fetches tenders in every status, keeping the ordering (newest publication first, then id)
- [ ] List and detail responses include a boolean `has_dce_archive`, computed with the existing persistence rule (it is not copied)
- [ ] `GET /tenders/{id}/dce-archive` still returns 404 for a tender without a DCE archive
- [ ] The detail page hides the download button when `has_dce_archive` is false
- [ ] Status and last status are still never exposed by the API or shown in the UI
- [ ] The lookup is renamed now that it no longer filters by archive (e.g. `list` / `get` rather than `..._with_dce_archive`)
- [ ] Unit tests for the API, using the in-memory lookup, are updated: a tender with no archive is listed and fetched, and its download returns 404
- [ ] The tender-lookup integration test is updated: tenders in every status are returned, each with the correct `has_dce_archive`
- [ ] The **DCE archive** entry in `CONTEXT.md` still holds, and nothing in it implies that archive presence controls visibility
