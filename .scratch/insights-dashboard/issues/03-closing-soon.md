# 03: Closing soon on the list and the Insights page

**What to build:** A business user sees a days-left badge on every **open tender** in the tender list, and can switch on a "Closing soon" filter that shows only tenders closing within 14 days, nearest deadline first. A new "Insights" sidebar entry opens the Insights page, whose first section lists closing-soon tenders grouped as less than 3 days, 3–7 days and 7–14 days left. Each entry shows reference number, tender object, public buyer and the deadline's date over its time, and links to the tender's detail page. See `.scratch/insights-dashboard/spec.md`.

**Blocked by:** 01 (typed dates), 02 (every tender has a detail page to link to)

**Status:** ready-for-human

- [x] An injectable clock gives the API "now". Persistence queries take "now" as a parameter and never read the clock themselves
- [x] `GET /tenders` accepts an optional closing-soon filter: open tenders whose deadline falls within the next 14 days, ordered by nearest deadline. Without it, ordering is unchanged
- [x] The list shows a days-left badge for open tenders, and no badge for closed tenders or tenders without a deadline
- [x] The list has a "Closing soon" filter control wired to the API filter
- [x] A read-only persistence **insights** module is created, with closing-soon as its first query
- [x] `GET /insights/closing-soon` returns open tenders in `lt3`, `3to7` and `7to14` buckets. Each item has id, reference number, tender object, public buyer and deadline
- [x] The sidebar gains an "Insights" entry. The Insights page shows the closing-soon section with loading, empty and error states, and each entry links to the tender's detail page
- [x] All new calls go through the typed API client
- [x] Integration test against real Postgres, with a fixed clock, through the FastAPI test client: bucket boundaries (exactly 3, 7 and 14 days left, a tender closing in an hour, an already-closed tender, a tender without a deadline), and the list filter's contents and ordering. Rows are cleaned up afterwards
- [ ] Manually verified against real data: the badge, the filter and the Insights closing-soon section

## Comments

**Implementation (agent):** every code box is done. Only the manual check in a browser is left for a human.

- **Checked against real data through the API only.** `GET /tenders?closing_soon=true` and `GET /insights/closing-soon` were called against the real database on 2026-11-24. Both returned the same 6 open tenders, all in `lt3`, nearest deadline first. The browser extension wasn't connected, so the agent did not see the badge, the filter or the Insights page. To finish: run `python -m api` and `npm run dev`, then check the badge and the "Closing soon" filter on Tenders, and the closing-soon section on Insights.
- **Bucket boundaries.** Exactly 3 days left falls in `3to7`, exactly 7 days in `7to14`, and exactly 14 days is still closing soon. A deadline exactly at "now" counts as closed. The rule is `persistence.models.closing_soon`; the bucketing happens in Python, by instant.
- **The badge counts down from the browser's clock.** The list filter uses the API's clock, so a browser with a wrong clock could show a different count. The badge shows whole days rounded down ("Under 1 day left" below one day), coloured like the buckets: under 3 days, under 7 days, then the rest.
- **Review follow-ups not done (judgement calls):** the 3/7/14-day edges are repeated in `DaysLeft.tsx` and in UI copy; the internal field names `lt3` / `from_3_to_7` don't match each other (the JSON keys follow the spec).
