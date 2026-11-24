# 03: Closing soon on the list and the Insights page

**What to build:** A business user sees a days-left badge on every **open tender** in the tender list, and can switch on a "Closing soon" filter that shows only tenders closing within 14 days, nearest deadline first. A new "Insights" sidebar entry opens the Insights page, whose first section lists closing-soon tenders grouped as less than 3 days, 3–7 days and 7–14 days left. Each entry shows reference number, tender object, public buyer and the deadline's date over its time, and links to the tender's detail page. See `.scratch/insights-dashboard/spec.md`.

**Blocked by:** 01 (typed dates), 02 (every tender has a detail page to link to)

**Status:** ready-for-agent

- [ ] An injectable clock gives the API "now". Persistence queries take "now" as a parameter and never read the clock themselves
- [ ] `GET /tenders` accepts an optional closing-soon filter: open tenders whose deadline falls within the next 14 days, ordered by nearest deadline. Without it, ordering is unchanged
- [ ] The list shows a days-left badge for open tenders, and no badge for closed tenders or tenders without a deadline
- [ ] The list has a "Closing soon" filter control wired to the API filter
- [ ] A read-only persistence **insights** module is created, with closing-soon as its first query
- [ ] `GET /insights/closing-soon` returns open tenders in `lt3`, `3to7` and `7to14` buckets. Each item has id, reference number, tender object, public buyer and deadline
- [ ] The sidebar gains an "Insights" entry. The Insights page shows the closing-soon section with loading, empty and error states, and each entry links to the tender's detail page
- [ ] All new calls go through the typed API client
- [ ] Integration test against real Postgres, with a fixed clock, through the FastAPI test client: bucket boundaries (exactly 3, 7 and 14 days left, a tender closing in an hour, an already-closed tender, a tender without a deadline), and the list filter's contents and ordering. Rows are cleaned up afterwards
- [ ] Manually verified against real data: the badge, the filter and the Insights closing-soon section
