# 04: Coverage, period selector, open-only toggle and New this week

**What to build:** At the top of the Insights page, a business user sees "Based on N tenders published between X and Y", plus "N tenders without a deadline" when there are any. They can choose the period (7 days, 30 days by default, 90 days, all time) and toggle "Open only"; both apply to the period-aware sections. A "New this week" section lists tenders published in the last 7 days, newest first, linking to their detail pages. See `.scratch/insights-dashboard/spec.md`.

**Blocked by:** 03 (the Insights page, insights module and clock)

**Status:** ready-for-agent

- [ ] Period and open-only filtering is built in one shared place in the insights module, so a later business-profile filter can be added there once
- [ ] A period is based on publication date: the last N days up to "now", intersected with the range the data covers. `all` means the full coverage range
- [ ] `GET /insights/coverage?period=&open_only=` returns the tender count, the earliest and latest publication date, and the count without a deadline
- [ ] `GET /insights/new-this-week` returns tenders published in the last 7 days, newest first (id, reference number, tender object, public buyer, publication date, deadline)
- [ ] Invalid `period` values are rejected with 422
- [ ] The Insights page has a period selector (default 30 days) and an "Open only" toggle. The coverage banner and the "New this week" section each have their own loading, empty and error states
- [ ] Integration test against real Postgres with a fixed clock: coverage for each period, a period capped to the data's range, `open_only`, the count without a deadline, and the "New this week" boundary (exactly 7 days ago)
- [ ] Manually verified against real data
